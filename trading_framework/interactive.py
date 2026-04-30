from __future__ import annotations

import json
from datetime import time
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
    backtest: bool = False
    tui: bool = False
    web: bool = False


# ---------------------------------------------------------------------------
# Strategy metadata
# ---------------------------------------------------------------------------

STRATEGY_INFO = {
    "moving_average_crossover": {
        "display_name": "Moving Average Crossover (SMA)",
        "short_desc": "Detects trend changes when a fast moving average crosses a slow one.",
        "plain_desc": "Buys when short-term price trend crosses above long-term trend",
        "params": [
            {"name": "short_window", "prompt": "Short window (fast SMA period)", "default": 5, "type": int, "help": "Number of recent bars for the fast average. Smaller = more responsive."},
            {"name": "long_window", "prompt": "Long window (slow SMA period)", "default": 20, "type": int, "help": "Number of recent bars for the slow average. Larger = smoother trend."},
        ],
        "bars_needed": lambda p: p.get("long_window", 20) + 1,
    },
    "rsi": {
        "display_name": "Relative Strength Index (RSI)",
        "short_desc": "Signals overbought/oversold conditions based on recent price momentum.",
        "plain_desc": "Buys when price has fallen too fast (oversold), sells when risen too fast",
        "params": [
            {"name": "period", "prompt": "RSI period (number of bars)", "default": 14, "type": int, "help": "How many bars to measure momentum over. Standard is 14."},
            {"name": "oversold", "prompt": "Oversold threshold (BUY below this)", "default": 30, "type": int, "help": "RSI below this = oversold = potential buy. Standard is 30."},
            {"name": "overbought", "prompt": "Overbought threshold (SELL above this)", "default": 70, "type": int, "help": "RSI above this = overbought = potential sell. Standard is 70."},
        ],
        "bars_needed": lambda p: p.get("period", 14) + 2,
    },
    "breakout": {
        "display_name": "Breakout (Channel)",
        "short_desc": "Detects price breaking above/below the recent high/low channel with volume confirmation.",
        "plain_desc": "Buys when price breaks above recent highs with strong volume",
        "params": [
            {"name": "lookback", "prompt": "Lookback window (bars for high/low channel)", "default": 20, "type": int, "help": "How many bars define the price channel. 20 = ~1 month of daily bars."},
            {"name": "volume_factor", "prompt": "Volume factor (0 to disable)", "default": 1.5, "type": float, "help": "Volume must be this multiple of average. 1.5 = 50% above average. 0 = no volume filter."},
        ],
        "bars_needed": lambda p: p.get("lookback", 20) + 1,
    },
    "macd": {
        "display_name": "MACD (Moving Average Convergence Divergence)",
        "short_desc": "Detects trend changes via fast/slow EMA crossover with signal line confirmation.",
        "plain_desc": "Buys when momentum accelerates upward, sells when it slows",
        "params": [
            {"name": "fast_period", "prompt": "Fast EMA period", "default": 12, "type": int, "help": "Fast moving average period. Standard is 12."},
            {"name": "slow_period", "prompt": "Slow EMA period", "default": 26, "type": int, "help": "Slow moving average period. Standard is 26."},
            {"name": "signal_period", "prompt": "Signal line EMA period", "default": 9, "type": int, "help": "Signal smoothing period. Standard is 9."},
        ],
        "bars_needed": lambda p: p.get("slow_period", 26) + p.get("signal_period", 9),
    },
    "goslin_momentum": {
        "display_name": "Goslin Three-Line Momentum",
        "short_desc": "Three-line system: direction (trend), timing (entry), confirming (filter).",
        "plain_desc": "High-conviction signals when trend, timing, and confirmation all agree",
        "params": [
            {"name": "direction_period", "prompt": "Direction line period (trend SMA)", "default": 49, "type": int, "help": "Long-term trend average. Goslin's original is 49 (ten weeks)."},
            {"name": "timing_short", "prompt": "Timing line short SMA", "default": 3, "type": int, "help": "Short-term momentum average."},
            {"name": "timing_long", "prompt": "Timing line long SMA", "default": 10, "type": int, "help": "Medium-term momentum average."},
            {"name": "confirming_period", "prompt": "Confirming line period", "default": 15, "type": int, "help": "Smoothing period for the confirmation filter."},
        ],
        "bars_needed": lambda p: p.get("direction_period", 49) + p.get("confirming_period", 15) + 1,
    },
    "market_profile": {
        "display_name": "Market Profile (Value Area)",
        "short_desc": "Trades price relative to the value area — buy below value, sell above value.",
        "plain_desc": "Buys when price dips below fair value, sells when it rises above",
        "params": [
            {"name": "lookback", "prompt": "Lookback window (bars for value area)", "default": 20, "type": int, "help": "How many bars to compute fair value from. 20 = ~1 month daily."},
            {"name": "value_area_pct", "prompt": "Value area % (volume coverage)", "default": 70.0, "type": float, "help": "Percentage of volume that defines the value area. Standard is 70%."},
        ],
        "bars_needed": lambda p: p.get("lookback", 20) + 1,
    },
}

BAR_INTERVALS = ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo"]

_BARS_PER_DAY = {
    "1m": 390, "2m": 195, "5m": 78, "15m": 26, "30m": 13,
    "60m": 7, "90m": 5, "1h": 7, "1d": 1, "5d": 0.2, "1wk": 0.14, "1mo": 0.033,
}

# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------

PRESETS = {
    "day_trader": {
        "display_name": "Day Trader",
        "desc": "Fast signals on 5-minute bars. MACD + RSI. Paper trading with tight risk controls.",
        "strategies": [
            {"name": "macd", "params": {"fast_period": 12, "slow_period": 26, "signal_period": 9}},
            {"name": "rsi", "params": {"period": 14, "oversold": 30, "overbought": 70}},
        ],
        "bar_interval": "5m",
        "poll_seconds": 300,
        "market_session": True,
        "risk": {"position_aware": True, "stop_loss_pct": 3.0, "take_profit_pct": 5.0, "max_signals_per_day": 5},
        "paper_trading": True,
        "paper_cash": 100_000.0,
        "paper_size_pct": 5.0,
    },
    "swing_trader": {
        "display_name": "Swing Trader",
        "desc": "Daily bars for multi-day holds. SMA crossover + Breakout. Moderate risk.",
        "strategies": [
            {"name": "moving_average_crossover", "params": {"short_window": 10, "long_window": 30}},
            {"name": "breakout", "params": {"lookback": 20, "volume_factor": 1.5}},
        ],
        "bar_interval": "1d",
        "poll_seconds": 3600,
        "market_session": True,
        "risk": {"position_aware": True, "stop_loss_pct": 5.0, "take_profit_pct": 10.0},
        "paper_trading": True,
        "paper_cash": 100_000.0,
        "paper_size_pct": 10.0,
    },
    "crypto": {
        "display_name": "Crypto Trader",
        "desc": "Hourly bars, 24/7 (no market hours). RSI + Breakout + MACD.",
        "strategies": [
            {"name": "rsi", "params": {"period": 14, "oversold": 25, "overbought": 75}},
            {"name": "breakout", "params": {"lookback": 24, "volume_factor": 1.5}},
            {"name": "macd", "params": {"fast_period": 12, "slow_period": 26, "signal_period": 9}},
        ],
        "bar_interval": "1h",
        "poll_seconds": 3600,
        "market_session": False,
        "risk": {"position_aware": True, "stop_loss_pct": 5.0, "take_profit_pct": 8.0},
        "paper_trading": True,
        "paper_cash": 50_000.0,
        "paper_size_pct": 10.0,
    },
    "goslin": {
        "display_name": "Futures / Goslin Method",
        "desc": "Daily bars. Goslin three-line momentum. Conservative, high-conviction.",
        "strategies": [
            {"name": "goslin_momentum", "params": {"direction_period": 49, "timing_short": 3, "timing_long": 10, "confirming_period": 15}},
        ],
        "bar_interval": "1d",
        "poll_seconds": 86400,
        "market_session": True,
        "risk": {"position_aware": True, "stop_loss_pct": 5.0},
        "paper_trading": True,
        "paper_cash": 100_000.0,
        "paper_size_pct": 10.0,
    },
    "value_investor": {
        "display_name": "Value Investor",
        "desc": "Daily bars. Market Profile (fair value). Wide parameters, patient approach.",
        "strategies": [
            {"name": "market_profile", "params": {"lookback": 30, "value_area_pct": 70.0}},
        ],
        "bar_interval": "1d",
        "poll_seconds": 86400,
        "market_session": True,
        "risk": {"position_aware": True, "stop_loss_pct": 8.0, "take_profit_pct": 15.0},
        "paper_trading": True,
        "paper_cash": 100_000.0,
        "paper_size_pct": 15.0,
    },
    "backtest_lab": {
        "display_name": "Backtest Lab",
        "desc": "Compare ALL strategies on historical data. Great for learning.",
        "strategies": [
            {"name": "moving_average_crossover", "params": {"short_window": 5, "long_window": 20}},
            {"name": "rsi", "params": {"period": 14, "oversold": 30, "overbought": 70}},
            {"name": "breakout", "params": {"lookback": 20, "volume_factor": 1.5}},
            {"name": "macd", "params": {"fast_period": 12, "slow_period": 26, "signal_period": 9}},
            {"name": "goslin_momentum", "params": {"direction_period": 49, "timing_short": 3, "timing_long": 10, "confirming_period": 15}},
            {"name": "market_profile", "params": {"lookback": 20, "value_area_pct": 70.0}},
        ],
        "bar_interval": "1d",
        "poll_seconds": 300,
        "market_session": False,
        "risk": None,
        "paper_trading": False,
        "paper_cash": 100_000.0,
        "paper_size_pct": 10.0,
    },
}


# ---------------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------------

def _input(prompt: str) -> str:
    return input(prompt)


def _print(message: str = "") -> None:
    print(message)


def _ask(prompt: str, default: str = "", help_text: str = "") -> str:
    if default:
        raw = _input(f"{prompt} [{default}]: ").strip()
    else:
        raw = _input(f"{prompt}: ").strip()
    if raw == "?" and help_text:
        _print(f"    {help_text}")
        return _ask(prompt, default, help_text)
    if raw == "?" and not help_text:
        _print("    No help available for this option.")
        return _ask(prompt, default, help_text)
    return raw if raw else default


def _ask_number(prompt: str, default, type_fn=int, help_text: str = ""):
    raw = _ask(prompt, str(default), help_text=help_text)
    try:
        return type_fn(raw)
    except ValueError:
        _print(f"  Invalid. Enter a number (e.g. {default}).")
        return default


def _ask_int(prompt: str, default: int, help_text: str = "") -> int:
    return _ask_number(prompt, default, int, help_text=help_text)


def _parse_strategy_choices(raw: str, max_count: int) -> List[int]:
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
    bars_per_day = _BARS_PER_DAY.get(bar_interval, 78)
    if bars_per_day <= 0:
        return "max"
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
    if not symbol:
        return symbol, "empty symbol"
    if symbol in ("ETH", "BTC", "SOL", "DOGE", "XRP", "ADA", "DOT", "MATIC", "AVAX", "LINK"):
        return symbol, f"'{symbol}' may not be valid on Yahoo Finance. Did you mean '{symbol}-USD'?"
    if len(symbol) > 12:
        return symbol, f"'{symbol}' looks unusually long — verify it exists on Yahoo Finance."
    currency_codes = {"USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD", "CNY", "INR"}
    if symbol in currency_codes:
        return symbol, f"'{symbol}' is a currency, not a stock symbol. For forex, try '{symbol}=X'."
    return symbol, None


def _is_crypto(symbols: List[str]) -> bool:
    return any(s.endswith("-USD") or s.endswith("-USDT") for s in symbols)


def _compute_bars_needed(strategies: List[Dict[str, Any]]) -> int:
    bars_needed = 21
    for strat in strategies:
        fn = STRATEGY_INFO.get(strat["name"], {}).get("bars_needed")
        if fn:
            bars_needed = max(bars_needed, fn(strat["params"]))
    return bars_needed


# ---------------------------------------------------------------------------
# Run mode selection
# ---------------------------------------------------------------------------

def _ask_run_mode(poll_seconds: int) -> tuple[bool, bool, bool, bool]:
    """Returns (run_once, backtest, tui, web)."""
    _print("How would you like to run?")
    _print("  1. Run once (analyze now and exit)")
    _print("  2. Monitor continuously (poll every {0}s)".format(poll_seconds))
    _print("  3. Backtest (replay historical data)")
    _print("  4. TUI Dashboard (live visual monitoring)")
    _print("  5. Web Dashboard (browser)")
    _print("  6. Cancel")
    run_choice = _ask("Choose", "1")
    if run_choice == "6":
        _print("Setup cancelled.")
        raise SystemExit(0)
    is_backtest = run_choice == "3"
    is_tui = run_choice == "4"
    is_web = run_choice == "5"
    run_once = run_choice not in ("2", "3", "4", "5")
    return run_once, is_backtest, is_tui, is_web


def _handle_backtest_config() -> tuple[str, str]:
    """Returns (lookback, bar_interval) for backtest mode."""
    _print()
    _print("How much history to backtest?")
    _print("  1. 1 year")
    _print("  2. 2 years")
    _print("  3. 5 years")
    bt_choice = _ask("Choose", "1")
    bt_lookbacks = {"1": "1y", "2": "2y", "3": "5y"}
    lookback = bt_lookbacks.get(bt_choice, "1y")
    _print(f"  -> Backtesting {lookback} of daily bars")
    return lookback, "1d"


# ---------------------------------------------------------------------------
# Symbol input (shared across paths)
# ---------------------------------------------------------------------------

def _ask_symbols() -> List[str]:
    _print("What would you like to trade?")
    _print("  Stocks:  AAPL, MSFT, SPY, TSLA, GOOGL")
    _print("  Crypto:  BTC-USD, ETH-USD, SOL-USD")
    _print("  Forex:   EURUSD=X, GBPUSD=X")
    raw_symbols = _ask("Enter symbol(s)", "AAPL")
    symbols = [s.strip().upper() for s in raw_symbols.split(",") if s.strip()]
    if not symbols:
        symbols = ["AAPL"]

    warnings = []
    for sym in symbols:
        _, warning = _validate_symbol(sym)
        if warning:
            warnings.append(warning)

    _print(f"  -> {', '.join(symbols)}")
    if warnings:
        _print()
        for w in warnings:
            _print(f"  WARNING: {w}")
        _print()
        if not _ask_yes_no("Continue with these symbols?", True):
            _print("  Tip: Re-run and enter corrected symbols.")
            raise SystemExit(0)
    _print()
    return symbols


# ---------------------------------------------------------------------------
# Build AppSettings from preset or manual config
# ---------------------------------------------------------------------------

def _build_settings(
    symbols: List[str],
    strategies: List[Dict[str, Any]],
    bar_interval: str,
    poll_seconds: int,
    use_market_session: bool,
    risk_config: Optional[Dict[str, Any]],
    cache_enabled: bool,
    paper_trading: bool,
    paper_cash: float,
    paper_size_pct: float,
    lookback_override: str | None = None,
) -> AppSettings:
    bars_needed = _compute_bars_needed(strategies)
    lookback = lookback_override or _compute_lookback(bar_interval, bars_needed)

    strategy_settings = [StrategySettings(name=s["name"], params=s["params"]) for s in strategies]

    market_session = None
    if use_market_session:
        market_session = MarketSession(
            timezone_name="America/New_York",
            weekdays=[0, 1, 2, 3, 4],
            start=time(9, 30),
            end=time(16, 0),
        )

    return AppSettings(
        symbols=symbols,
        poll_interval_seconds=poll_seconds,
        market_data=MarketDataConfig(provider="yahoo", bar_interval=bar_interval, lookback=lookback, timeout_seconds=10),
        strategy=strategy_settings[0],
        notifiers=[NotifierSettings(type="console")],
        market_session=market_session,
        signal_history=SignalHistorySettings(enabled=True, path="signal_history.jsonl"),
        strategies=strategy_settings,
        risk=risk_config,
        cache_enabled=cache_enabled,
        cache_dir=".cache",
        cache_ttl_seconds=300,
        paper_trading=paper_trading,
        paper_starting_cash=paper_cash,
        paper_position_size_pct=paper_size_pct,
    )


# ---------------------------------------------------------------------------
# Path 1: Quick Start
# ---------------------------------------------------------------------------

def _quick_start(symbols: List[str]) -> InteractiveResult:
    is_crypto = _is_crypto(symbols)

    # Auto-configure based on asset type
    if is_crypto:
        strategies = [
            {"name": "rsi", "params": {"period": 14, "oversold": 25, "overbought": 75}},
            {"name": "macd", "params": {"fast_period": 12, "slow_period": 26, "signal_period": 9}},
        ]
        bar_interval = "1h"
        poll_seconds = 3600
        use_market_session = False
        _print("  Auto-configured for crypto: RSI + MACD, 1h bars, 24/7 monitoring")
    else:
        strategies = [
            {"name": "moving_average_crossover", "params": {"short_window": 5, "long_window": 20}},
            {"name": "rsi", "params": {"period": 14, "oversold": 30, "overbought": 70}},
        ]
        bar_interval = "5m"
        poll_seconds = 300
        use_market_session = True
        _print("  Auto-configured for stocks: SMA + RSI, 5m bars, US market hours")

    risk_config = {"position_aware": True, "stop_loss_pct": 5.0}
    _print("  Risk: position tracking ON, 5% stop-loss")
    _print("  Paper trading: $100,000 (10% per trade)")
    _print("  Cache: enabled | Signal history: enabled")
    _print()

    run_once, is_backtest, is_tui, is_web = _ask_run_mode(poll_seconds)

    lookback_override = None
    if is_backtest:
        lookback_override, bar_interval = _handle_backtest_config()

    settings = _build_settings(
        symbols=symbols, strategies=strategies, bar_interval=bar_interval,
        poll_seconds=poll_seconds, use_market_session=use_market_session,
        risk_config=risk_config, cache_enabled=True, paper_trading=True,
        paper_cash=100_000.0, paper_size_pct=10.0, lookback_override=lookback_override,
    )
    return InteractiveResult(settings=settings, run_once=run_once, backtest=is_backtest, tui=is_tui, web=is_web)


# ---------------------------------------------------------------------------
# Path 2: Presets
# ---------------------------------------------------------------------------

def _preset_setup(symbols: List[str]) -> InteractiveResult:
    _print("Choose a preset:")
    _print()
    preset_keys = list(PRESETS.keys())
    for i, key in enumerate(preset_keys, 1):
        p = PRESETS[key]
        _print(f"  {i}. {p['display_name']}")
        _print(f"     {p['desc']}")
        _print()

    choice = _ask("Choose preset", "1")
    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(preset_keys):
            raise ValueError()
    except ValueError:
        idx = 0
        _print("  Invalid choice, using: 1")

    preset_key = preset_keys[idx]
    preset = PRESETS[preset_key]
    _print(f"  -> {preset['display_name']}")
    _print()

    strategies = preset["strategies"]
    bar_interval = preset["bar_interval"]
    poll_seconds = preset["poll_seconds"]
    use_market_session = preset["market_session"]
    risk_config = preset["risk"]
    paper_trading = preset["paper_trading"]
    paper_cash = preset["paper_cash"]
    paper_size_pct = preset["paper_size_pct"]

    # Auto-disable market session for crypto symbols
    if _is_crypto(symbols):
        use_market_session = False
        _print("  (Market hours disabled — crypto trades 24/7)")

    # Show what's configured
    strat_names = [STRATEGY_INFO[s["name"]]["display_name"] for s in strategies]
    _print(f"  Strategies:    {', '.join(strat_names)}")
    _print(f"  Bar interval:  {bar_interval}")
    _print(f"  Risk:          {'Enabled' if risk_config else 'Disabled'}")
    _print(f"  Paper trading: {'$' + f'{paper_cash:,.0f}' if paper_trading else 'Disabled'}")
    _print()

    # For backtest lab, force backtest mode
    if preset_key == "backtest_lab":
        run_once = False
        is_backtest = True
        is_tui = False
        is_web = False
        lookback_override, bar_interval = _handle_backtest_config()
    else:
        run_once, is_backtest, is_tui, is_web = _ask_run_mode(poll_seconds)
        lookback_override = None
        if is_backtest:
            lookback_override, bar_interval = _handle_backtest_config()

    settings = _build_settings(
        symbols=symbols, strategies=strategies, bar_interval=bar_interval,
        poll_seconds=poll_seconds, use_market_session=use_market_session,
        risk_config=risk_config, cache_enabled=True, paper_trading=paper_trading,
        paper_cash=paper_cash, paper_size_pct=paper_size_pct,
        lookback_override=lookback_override,
    )
    return InteractiveResult(settings=settings, run_once=run_once, backtest=is_backtest, tui=is_tui, web=is_web)


# ---------------------------------------------------------------------------
# Path 3: Advanced Setup (full control)
# ---------------------------------------------------------------------------

def _advanced_setup(symbols: List[str]) -> InteractiveResult:
    # --- Strategy ---
    _print("Which strategy would you like to use?")
    _print("  Pick multiple: e.g. 1,2  |  Type ? for help on any option")
    _print()
    strategy_keys = list(STRATEGY_INFO.keys())
    for i, key in enumerate(strategy_keys, 1):
        info = STRATEGY_INFO[key]
        _print(f"  {i}. {info['display_name']}")
        _print(f"     {info['plain_desc']}")
        _print()

    choice = _ask("Choose strategy number(s)", "1")
    if choice.strip() == "?":
        _print("  Enter a number (1-6) or multiple separated by commas (e.g. 1,2,4).")
        _print("  Each strategy analyzes the market differently. You can combine them")
        _print("  to get signals from multiple perspectives. See docs/strategy-manual.md")
        _print("  for detailed explanations of each strategy.")
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
    _print(f"  -> {', '.join(names)}")
    _print()

    # --- Strategy Parameters ---
    for strat in selected_strategies:
        info = strat["info"]
        if len(selected_strategies) > 1:
            _print(f"Configure {info['display_name']} (Enter for defaults, ? for help):")
        else:
            _print("Configure strategy parameters (Enter for defaults, ? for help):")
        for param in info["params"]:
            type_fn = param.get("type", int)
            help_text = param.get("help", "")
            value = _ask_number(f"  {param['prompt']}", param["default"], type_fn, help_text=help_text)
            strat["params"][param["name"]] = value
        _print()

    strategies_for_build = [{"name": s["name"], "params": s["params"]} for s in selected_strategies]

    # --- Bar Interval ---
    _print("Bar interval for price data:")
    _print(f"  Options: {', '.join(BAR_INTERVALS)}")
    bar_interval = _ask("Bar interval", "5m",
                        help_text="How often each price bar represents. 5m = 5-minute candles, "
                                  "1h = hourly, 1d = daily. Shorter = more data points but noisier. "
                                  "Day traders use 1m-15m, swing traders use 1d.")
    if bar_interval not in BAR_INTERVALS:
        _print(f"  Unknown interval '{bar_interval}', using: 5m")
        bar_interval = "5m"
    _print()

    # --- Poll Interval ---
    poll_seconds = _ask_int("Poll interval in seconds (e.g. 300 = 5 min)", 300,
                            help_text="How often to check for new data, in seconds. "
                                      "300 = every 5 minutes, 3600 = hourly, 86400 = daily.")
    if poll_seconds < 10:
        _print("  Minimum 10 seconds. Using 10.")
        poll_seconds = 10
    _print()

    # --- Market Session ---
    default_session = not _is_crypto(symbols)
    use_market_session = _ask_yes_no("Restrict to US market hours? (Mon-Fri 9:30-16:00 ET)", default_session)
    _print()

    # --- Risk Management ---
    risk_config: Optional[Dict[str, Any]] = None
    use_risk = _ask_yes_no("Enable risk management?", True)
    if use_risk:
        _print("Configure risk filters (Enter to skip, ? for help):")
        risk_config = {}
        pos = _ask_yes_no("  Track positions (block duplicate signals)?", True)
        if pos:
            risk_config["position_aware"] = True
        sl = _ask_number("  Stop-loss % (0=off)", 5.0, float,
                         help_text="Auto-calculate a stop-loss price on each signal. E.g. 5 = stop-loss 5% below entry for BUY.")
        if sl > 0:
            risk_config["stop_loss_pct"] = sl
        tp = _ask_number("  Take-profit % (0=off)", 10.0, float,
                         help_text="Auto-calculate a take-profit price. E.g. 10 = take profit 10% above entry for BUY.")
        if tp > 0:
            risk_config["take_profit_pct"] = tp
        cd = _ask_int("  Cooldown between signals (seconds, 0=off)", 0,
                      help_text="Minimum time between signals for the same symbol. Prevents rapid-fire signals. 0 = no cooldown.")
        if cd > 0:
            risk_config["cooldown_seconds"] = cd
        dl = _ask_int("  Max signals per symbol per day (0=unlimited)", 0,
                      help_text="Cap the number of signals per symbol per day. Prevents overtrading. 0 = no limit.")
        if dl > 0:
            risk_config["max_signals_per_day"] = dl
        if not risk_config:
            risk_config = None
    _print()

    # --- Paper Trading ---
    paper_trading = _ask_yes_no("Enable paper trading (simulated execution)?", True)
    paper_cash = 100_000.0
    paper_size_pct = 10.0
    if paper_trading:
        paper_cash = _ask_number("  Starting cash ($)", 100_000.0, float,
                                 help_text="How much virtual money to start with.")
        paper_size_pct = _ask_number("  Position size (% per trade)", 10.0, float,
                                     help_text="What percentage of your portfolio to risk per trade. 10 = 10% of total equity per position.")
    _print()

    # --- Save Config ---
    save_config = _ask_yes_no("Save this configuration for reuse?", False)
    if save_config:
        config_path = _ask("Config file path", "my-config.json")
        _save_config_file(
            config_path, symbols=symbols, selected_strategies=selected_strategies,
            bar_interval=bar_interval, lookback=_compute_lookback(bar_interval, _compute_bars_needed(strategies_for_build)),
            poll_seconds=poll_seconds, use_market_session=use_market_session,
            signal_history_path="signal_history.jsonl",
        )
        _print(f"  -> Saved to {config_path}")
    _print()

    # --- Run Mode ---
    run_once, is_backtest, is_tui, is_web = _ask_run_mode(poll_seconds)
    lookback_override = None
    if is_backtest:
        lookback_override, bar_interval = _handle_backtest_config()

    settings = _build_settings(
        symbols=symbols, strategies=strategies_for_build, bar_interval=bar_interval,
        poll_seconds=poll_seconds, use_market_session=use_market_session,
        risk_config=risk_config, cache_enabled=True, paper_trading=paper_trading,
        paper_cash=paper_cash, paper_size_pct=paper_size_pct,
        lookback_override=lookback_override,
    )
    return InteractiveResult(settings=settings, run_once=run_once, backtest=is_backtest, tui=is_tui, web=is_web)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_interactive_setup() -> InteractiveResult:
    """Guide the user through setting up a trading session."""
    _print()
    _print("=" * 60)
    _print("  Trading Framework")
    _print("=" * 60)
    _print()

    # Step 1: Ask for symbols first (shared across all paths)
    symbols = _ask_symbols()

    # Step 2: Choose path
    _print("How would you like to set up?")
    _print()
    _print("  1. Quick Start")
    _print("     Just pick symbols — we configure everything automatically.")
    _print()
    _print("  2. Choose a Preset")
    _print("     Pre-built profiles for day trading, swing trading, crypto, etc.")
    _print()
    _print("  3. Advanced Setup")
    _print("     Full control over every parameter.")
    _print()
    path = _ask("Choose", "1",
                help_text="Quick Start = auto-configure everything (2-3 clicks). "
                          "Presets = choose a trading style. Advanced = full control.")
    # Handle inputs like "1?" by stripping ?
    path = path.replace("?", "").strip() or "1"
    if path not in ("1", "2", "3"):
        _print(f"  Unknown option '{path}', using Quick Start.")
        path = "1"
    _print()

    if path == "2":
        return _preset_setup(symbols)
    elif path == "3":
        return _advanced_setup(symbols)
    else:
        return _quick_start(symbols)


# ---------------------------------------------------------------------------
# Config file save
# ---------------------------------------------------------------------------

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
