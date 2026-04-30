from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from dataclasses import dataclass

from .models import (
    AppSettings,
    MarketDataConfig,
    MarketSession,
    NotifierSettings,
    SignalHistorySettings,
    StrategySettings,
)


@dataclass
class InteractiveResult:
    settings: AppSettings
    run_once: bool

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


def _parse_strategy_choices(raw: str, max_count: int) -> List[int]:
    """Parse comma or space-separated strategy numbers into 0-based indices."""
    indices = []
    for part in raw.replace(",", " ").split():
        try:
            idx = int(part.strip()) - 1
            if 0 <= idx < max_count and idx not in indices:
                indices.append(idx)
        except ValueError:
            continue
    return indices


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


def run_interactive_setup() -> InteractiveResult:
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
    _print("  You can pick multiple: e.g. 1,2")
    _print()
    strategy_keys = list(STRATEGY_INFO.keys())
    for i, key in enumerate(strategy_keys, 1):
        info = STRATEGY_INFO[key]
        _print(f"  {i}. {info['display_name']}")
        _print(f"     {info['short_desc']}")
        _print()

    choice = _ask("Choose strategy number(s)", "1")
    selected_indices = _parse_strategy_choices(choice, len(strategy_keys))
    if not selected_indices:
        selected_indices = [0]
        _print(f"  Invalid choice. Using default: 1")

    selected_strategies: List[Dict[str, Any]] = []
    for idx in selected_indices:
        name = strategy_keys[idx]
        info = STRATEGY_INFO[name]
        selected_strategies.append({"name": name, "info": info, "params": {}})

    names = [s["info"]["display_name"] for s in selected_strategies]
    _print(f"  -> {'Strategy' if len(names) == 1 else 'Strategies'}: {', '.join(names)}")
    _print()

    # --- Strategy Parameters ---
    for strat in selected_strategies:
        info = strat["info"]
        if len(selected_strategies) > 1:
            _print(f"Configure {info['display_name']}:")
        else:
            _print("Configure strategy parameters (press Enter for defaults):")
        for param in info["params"]:
            value = _ask_int(f"  {param['prompt']}", param["default"])
            strat["params"][param["name"]] = value
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
    bars_needed = 21
    for strat in selected_strategies:
        fn = strat["info"].get("bars_needed")
        if fn:
            bars_needed = max(bars_needed, fn(strat["params"]))
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
            selected_strategies=selected_strategies,
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
    for strat in selected_strategies:
        _print(f"  Strategy:      {strat['info']['display_name']}")
        for param in strat["info"]["params"]:
            _print(f"    {param['prompt']}: {strat['params'][param['name']]}")
    _print(f"  Bar interval:  {bar_interval}")
    _print(f"  Lookback:      {lookback}")
    _print(f"  Poll interval: {poll_seconds}s")
    _print(f"  Market hours:  {'US market hours' if use_market_session else 'Always on'}")
    _print(f"  Signal history: {'Enabled' if signal_history else 'Disabled'}")
    _print("-" * 60)
    _print()

    _print("How would you like to run?")
    _print("  1. Run once (analyze now and exit)")
    _print("  2. Monitor continuously (poll every {0}s)".format(poll_seconds))
    _print("  3. Cancel")
    run_choice = _ask("Choose", "1")
    if run_choice == "3":
        _print("Setup cancelled.")
        raise SystemExit(0)
    run_once = run_choice != "2"

    _print()
    if run_once:
        _print("Running analysis...")
    else:
        _print("Starting continuous monitoring... (press Ctrl+C to stop)")
    _print()

    strategy_settings_list = [
        StrategySettings(name=s["name"], params=s["params"])
        for s in selected_strategies
    ]

    settings = AppSettings(
        symbols=symbols,
        poll_interval_seconds=poll_seconds,
        market_data=MarketDataConfig(
            provider="yahoo",
            bar_interval=bar_interval,
            lookback=lookback,
            timeout_seconds=10,
        ),
        strategy=strategy_settings_list[0],
        notifiers=[NotifierSettings(type="console")],
        market_session=market_session,
        signal_history=signal_history,
        strategies=strategy_settings_list,
    )
    return InteractiveResult(settings=settings, run_once=run_once)


def _save_config_file(
    path: str,
    symbols: List[str],
    selected_strategies: List[Dict[str, Any]],
    bar_interval: str,
    lookback: str,
    poll_seconds: int,
    use_market_session: bool,
    signal_history_path: str | None,
) -> None:
    strategy_configs = [
        {"name": s["name"], "params": s["params"]}
        for s in selected_strategies
    ]

    config: Dict[str, Any] = {
        "symbols": symbols,
        "poll_interval_seconds": poll_seconds,
        "market_data": {
            "provider": "yahoo",
            "bar_interval": bar_interval,
            "lookback": lookback,
            "timeout_seconds": 10,
        },
        "strategy": strategy_configs[0],
        "strategies": strategy_configs if len(strategy_configs) > 1 else None,
    }
    if config["strategies"] is None:
        del config["strategies"]

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
