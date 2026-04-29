from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import (
    AppSettings,
    MarketDataConfig,
    MarketSession,
    NotifierSettings,
    SignalHistorySettings,
    StrategySettings,
)

STRATEGY_INFO = {
    "moving_average_crossover": {
        "display_name": "Moving Average Crossover (SMA)",
        "short_desc": "Detects trend changes when a fast moving average crosses a slow one.",
        "params": [
            {"name": "short_window", "prompt": "Short window (fast SMA period)", "default": 5, "type": int},
            {"name": "long_window", "prompt": "Long window (slow SMA period)", "default": 20, "type": int},
        ],
        "bars_needed": lambda p: p.get("long_window", 20) + 1,
    },
    "rsi": {
        "display_name": "Relative Strength Index (RSI)",
        "short_desc": "Signals overbought/oversold conditions based on recent price momentum.",
        "params": [
            {"name": "period", "prompt": "RSI period (number of bars)", "default": 14, "type": int},
            {"name": "oversold", "prompt": "Oversold threshold (BUY below this)", "default": 30, "type": int},
            {"name": "overbought", "prompt": "Overbought threshold (SELL above this)", "default": 70, "type": int},
        ],
        "bars_needed": lambda p: p.get("period", 14) + 2,
    },
}

BAR_INTERVALS = ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo"]

# Approximate number of bars per day for each interval (market hours ~6.5h for stocks, 24h for crypto)
_BARS_PER_DAY = {
    "1m": 390, "2m": 195, "5m": 78, "15m": 26, "30m": 13,
    "60m": 7, "90m": 5, "1h": 7, "1d": 1, "5d": 0.2, "1wk": 0.14, "1mo": 0.033,
}


def _input(prompt: str) -> str:
    """Wrapper around input() for testability."""
    return input(prompt)


def _print(message: str = "") -> None:
    """Wrapper around print() for testability."""
    print(message)


def _ask(prompt: str, default: str = "") -> str:
    if default:
        raw = _input(f"{prompt} [{default}]: ").strip()
        return raw if raw else default
    return _input(f"{prompt}: ").strip()


def _ask_int(prompt: str, default: int) -> int:
    raw = _ask(prompt, str(default))
    try:
        return int(raw)
    except ValueError:
        _print(f"  Invalid number, using default: {default}")
        return default


def _ask_yes_no(prompt: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    raw = _input(f"{prompt} [{hint}]: ").strip().lower()
    if not raw:
        return default
    return raw in ("y", "yes")


def _compute_lookback(bar_interval: str, bars_needed: int) -> str:
    """Calculate the minimum Yahoo Finance lookback range for the required number of bars."""
    bars_per_day = _BARS_PER_DAY.get(bar_interval, 78)
    if bars_per_day <= 0:
        return "max"

    # Add 50% buffer for weekends, holidays, gaps
    days_needed = int((bars_needed / bars_per_day) * 1.5) + 2

    if days_needed <= 5:
        return "5d"
    if days_needed <= 30:
        return f"{days_needed}d"
    if days_needed <= 60:
        return "60d"
    if days_needed <= 180:
        return "6mo"
    if days_needed <= 365:
        return "1y"
    if days_needed <= 730:
        return "2y"
    return "5y"


def _validate_symbol(symbol: str) -> tuple[str, str | None]:
    """Basic symbol validation. Returns (symbol, warning_or_none)."""
    if not symbol:
        return symbol, "empty symbol"

    # Common mistakes
    if symbol in ("ETH", "BTC", "SOL", "DOGE", "XRP", "ADA", "DOT", "MATIC", "AVAX", "LINK"):
        return symbol, f"'{symbol}' may not be valid on Yahoo Finance. Did you mean '{symbol}-USD'?"

    if len(symbol) > 12:
        return symbol, f"'{symbol}' looks unusually long — verify it exists on Yahoo Finance."

    # Single common currency codes that aren't stocks
    currency_codes = {"USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD", "CNY", "INR"}
    if symbol in currency_codes:
        return symbol, f"'{symbol}' is a currency, not a stock symbol. For forex, try a pair like '{symbol}=X' or 'EUR{symbol}=X'."

    return symbol, None


def run_interactive_setup() -> AppSettings:
    """Guide the user through setting up a trading session interactively."""
    _print()
    _print("=" * 60)
    _print("  Trading Framework — Interactive Setup")
    _print("=" * 60)
    _print()

    # --- Symbols ---
    _print("Which symbols would you like to monitor?")
    _print("  Stocks:  AAPL, MSFT, SPY, TSLA, GOOGL")
    _print("  Crypto:  BTC-USD, ETH-USD, SOL-USD")
    _print("  Forex:   EURUSD=X, GBPUSD=X")
    raw_symbols = _ask("Enter symbols (comma-separated)", "AAPL, MSFT, SPY")
    symbols = [s.strip().upper() for s in raw_symbols.split(",") if s.strip()]
    if not symbols:
        symbols = ["AAPL", "MSFT", "SPY"]

    # Validate symbols and warn about suspicious ones
    warnings = []
    for sym in symbols:
        _, warning = _validate_symbol(sym)
        if warning:
            warnings.append(warning)

    _print(f"  -> Monitoring: {', '.join(symbols)}")
    if warnings:
        _print()
        for w in warnings:
            _print(f"  WARNING: {w}")
        _print()
        proceed = _ask_yes_no("Continue with these symbols?", True)
        if not proceed:
            _print("  Tip: Re-run and enter corrected symbols.")
            raise SystemExit(0)
    _print()

    # --- Strategy ---
    _print("Which strategy would you like to use?")
    _print()
    strategy_keys = list(STRATEGY_INFO.keys())
    for i, key in enumerate(strategy_keys, 1):
        info = STRATEGY_INFO[key]
        _print(f"  {i}. {info['display_name']}")
        _print(f"     {info['short_desc']}")
        _print()

    choice = _ask("Choose strategy number", "1")
    try:
        strategy_index = int(choice) - 1
        if strategy_index < 0 or strategy_index >= len(strategy_keys):
            raise ValueError()
    except ValueError:
        strategy_index = 0
        _print(f"  Invalid choice. Enter a number from 1 to {len(strategy_keys)}. Using default: 1")

    strategy_name = strategy_keys[strategy_index]
    strategy_info = STRATEGY_INFO[strategy_name]
    _print(f"  -> Strategy: {strategy_info['display_name']}")
    _print()

    # --- Strategy Parameters ---
    _print("Configure strategy parameters (press Enter for defaults):")
    strategy_params: Dict[str, Any] = {}
    for param in strategy_info["params"]:
        value = _ask_int(f"  {param['prompt']}", param["default"])
        strategy_params[param["name"]] = value
    _print()

    # --- Bar Interval ---
    _print("What bar interval should be used for price data?")
    _print(f"  Options: {', '.join(BAR_INTERVALS)}")
    bar_interval = _ask("Bar interval", "5m")
    if bar_interval not in BAR_INTERVALS:
        _print(f"  Unknown interval, using default: 5m")
        bar_interval = "5m"
    _print()

    # --- Auto-compute lookback ---
    bars_needed_fn = strategy_info.get("bars_needed")
    bars_needed = bars_needed_fn(strategy_params) if bars_needed_fn else 21
    lookback = _compute_lookback(bar_interval, bars_needed)
    _print(f"  Auto-calculated lookback: {lookback} (need ~{bars_needed} bars of {bar_interval} data)")
    _print()

    # --- Poll Interval ---
    poll_seconds = _ask_int("How often to poll for new data (seconds)", 300)
    if poll_seconds < 10:
        _print("  Minimum 10 seconds. Using 10.")
        poll_seconds = 10
    _print()

    # --- Market Session ---
    use_market_session = _ask_yes_no("Restrict to US market hours? (Mon-Fri 9:30-16:00 ET)", True)
    market_session: Optional[MarketSession] = None
    if use_market_session:
        from datetime import time
        market_session = MarketSession(
            timezone_name="America/New_York",
            weekdays=[0, 1, 2, 3, 4],
            start=time(9, 30),
            end=time(16, 0),
        )
    _print()

    # --- Signal History ---
    use_history = _ask_yes_no("Save signal history to file?", True)
    signal_history: Optional[SignalHistorySettings] = None
    if use_history:
        history_path = _ask("History file path", "signal_history.jsonl")
        signal_history = SignalHistorySettings(enabled=True, path=history_path)
    _print()

    # --- Save Config ---
    save_config = _ask_yes_no("Save this configuration to a file for reuse?", False)
    if save_config:
        config_path = _ask("Config file path", "my-config.json")
        _save_config_file(
            config_path,
            symbols=symbols,
            strategy_name=strategy_name,
            strategy_params=strategy_params,
            bar_interval=bar_interval,
            lookback=lookback,
            poll_seconds=poll_seconds,
            use_market_session=use_market_session,
            signal_history_path=signal_history.path if signal_history else None,
        )
        _print(f"  -> Saved to {config_path}")
        _print(f"     Reuse with: python -m trading_framework --config {config_path}")
    _print()

    # --- Summary ---
    _print("-" * 60)
    _print("  Configuration Summary")
    _print("-" * 60)
    _print(f"  Symbols:       {', '.join(symbols)}")
    _print(f"  Strategy:      {strategy_info['display_name']}")
    for param in strategy_info["params"]:
        _print(f"    {param['prompt']}: {strategy_params[param['name']]}")
    _print(f"  Bar interval:  {bar_interval}")
    _print(f"  Lookback:      {lookback}")
    _print(f"  Poll interval: {poll_seconds}s")
    _print(f"  Market hours:  {'US market hours' if use_market_session else 'Always on'}")
    _print(f"  Signal history: {'Enabled' if signal_history else 'Disabled'}")
    _print("-" * 60)
    _print()

    confirm = _ask_yes_no("Start monitoring?", True)
    if not confirm:
        _print("Setup cancelled.")
        raise SystemExit(0)

    _print()
    _print("Starting... (press Ctrl+C to stop)")
    _print()

    return AppSettings(
        symbols=symbols,
        poll_interval_seconds=poll_seconds,
        market_data=MarketDataConfig(
            provider="yahoo",
            bar_interval=bar_interval,
            lookback=lookback,
            timeout_seconds=10,
        ),
        strategy=StrategySettings(name=strategy_name, params=strategy_params),
        notifiers=[NotifierSettings(type="console")],
        market_session=market_session,
        signal_history=signal_history,
    )


def _save_config_file(
    path: str,
    symbols: List[str],
    strategy_name: str,
    strategy_params: Dict[str, Any],
    bar_interval: str,
    lookback: str,
    poll_seconds: int,
    use_market_session: bool,
    signal_history_path: str | None,
) -> None:
    config: Dict[str, Any] = {
        "symbols": symbols,
        "poll_interval_seconds": poll_seconds,
        "market_data": {
            "provider": "yahoo",
            "bar_interval": bar_interval,
            "lookback": lookback,
            "timeout_seconds": 10,
        },
        "strategy": {
            "name": strategy_name,
            "params": strategy_params,
        },
    }

    if use_market_session:
        config["market_session"] = {
            "enabled": True,
            "timezone": "America/New_York",
            "weekdays": [0, 1, 2, 3, 4],
            "start": "09:30",
            "end": "16:00",
        }
    else:
        config["market_session"] = {"enabled": False}

    if signal_history_path:
        config["signal_history"] = {"enabled": True, "path": signal_history_path}

    config["notifiers"] = [{"type": "console"}]

    Path(path).write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
