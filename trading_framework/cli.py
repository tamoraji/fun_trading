from __future__ import annotations

import argparse
import sys

from .config import load_settings
from .data import create_market_data_provider
from .engine import TradingEngine
from .history import create_signal_history
from .notifiers import create_notifiers
from .strategy import create_strategy
from .structlog import StructuredLogger


STRATEGY_DISPLAY_NAMES = {
    "moving_average_crossover": "SMA Crossover",
    "rsi": "RSI",
    "breakout": "Breakout",
    "macd": "MACD",
}


def _run_backtest(settings) -> int:
    from .backtest import run_backtest
    from .metrics import compute_metrics, format_report, format_comparison

    provider = create_market_data_provider(settings.market_data)
    strategies_list = [create_strategy(s) for s in settings.all_strategies]

    all_results = []
    for symbol in settings.symbols:
        print(f"  Fetching data for {symbol}...")
        try:
            bars = provider.fetch_bars(symbol, settings.market_data)
        except Exception as exc:
            print(f"  ERROR fetching {symbol}: {exc}")
            continue

        for strategy in strategies_list:
            bt_result = run_backtest(strategy, symbol, bars)
            metrics = compute_metrics(bt_result.trades, bt_result.bars)

            display_name = STRATEGY_DISPLAY_NAMES.get(strategy.name, strategy.name)
            start_date = bars[0].timestamp if bars else None
            end_date = bars[-1].timestamp if bars else None

            report = format_report(
                symbol=symbol,
                strategy_name=display_name,
                metrics=metrics,
                num_signals=len(bt_result.signals),
                num_bars=len(bars),
                start_date=start_date,
                end_date=end_date,
                trades=bt_result.trades,
            )
            print(report)
            all_results.append((f"{symbol}/{display_name}", metrics))

    if len(all_results) > 1:
        print(format_comparison(all_results))

    return 0


def build_engine_from_settings(settings, pretty: bool = False) -> TradingEngine:
    provider = create_market_data_provider(settings.market_data)
    strategies = [create_strategy(s) for s in settings.all_strategies]
    notifiers = create_notifiers(settings.notifiers)
    history = create_signal_history(settings.signal_history)
    if pretty:
        from .prettylog import PrettyLogger
        logger = PrettyLogger()
    else:
        logger = StructuredLogger()
    return TradingEngine(
        settings=settings,
        provider=provider,
        strategies=strategies,
        notifiers=notifiers,
        history=history,
        logger=logger,
    )


def build_engine(config_path: str, pretty: bool = False) -> TradingEngine:
    settings = load_settings(config_path)
    return build_engine_from_settings(settings, pretty=pretty)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Poll market data and emit trading signals.",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to a JSON config file. If omitted, launches interactive setup.",
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Launch interactive setup wizard.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single polling cycle and exit.",
    )
    args = parser.parse_args(argv)

    use_interactive = args.interactive or (args.config is None and sys.stdin.isatty())

    if use_interactive:
        from .interactive import run_interactive_setup
        result = run_interactive_setup()

        if result.backtest:
            return _run_backtest(result.settings)

        engine = build_engine_from_settings(result.settings, pretty=True)
        if result.run_once or args.once:
            engine.run_cycle()
            return 0
        engine.run_forever()
        return 0

    config_path = args.config or "config.example.json"
    engine = build_engine(config_path)

    if args.once:
        engine.run_cycle()
        return 0

    engine.run_forever()
    return 0
