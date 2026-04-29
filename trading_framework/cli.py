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


def build_engine_from_settings(settings) -> TradingEngine:
    provider = create_market_data_provider(settings.market_data)
    strategy = create_strategy(settings.strategy)
    notifiers = create_notifiers(settings.notifiers)
    history = create_signal_history(settings.signal_history)
    logger = StructuredLogger()
    return TradingEngine(
        settings=settings,
        provider=provider,
        strategy=strategy,
        notifiers=notifiers,
        history=history,
        logger=logger,
    )


def build_engine(config_path: str) -> TradingEngine:
    settings = load_settings(config_path)
    return build_engine_from_settings(settings)


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
        settings = run_interactive_setup()
        engine = build_engine_from_settings(settings)
    else:
        config_path = args.config or "config.example.json"
        engine = build_engine(config_path)

    if args.once:
        engine.run_cycle()
        return 0

    engine.run_forever()
    return 0
