from __future__ import annotations

import argparse

from .config import load_settings
from .data import create_market_data_provider
from .engine import TradingEngine
from .notifiers import create_notifiers
from .strategy import create_strategy


def build_engine(config_path: str) -> TradingEngine:
    settings = load_settings(config_path)
    provider = create_market_data_provider(settings.market_data)
    strategy = create_strategy(settings.strategy)
    notifiers = create_notifiers(settings.notifiers)
    return TradingEngine(settings=settings, provider=provider, strategy=strategy, notifiers=notifiers)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Poll market data and emit trading signals.")
    parser.add_argument("--config", default="config.example.json", help="Path to the JSON config file.")
    parser.add_argument("--once", action="store_true", help="Run a single polling cycle and exit.")
    args = parser.parse_args(argv)

    engine = build_engine(args.config)
    if args.once:
        engine.run_cycle()
        return 0

    engine.run_forever()
    return 0
