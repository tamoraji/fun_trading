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
    "goslin_momentum": "Goslin Momentum",
    "market_profile": "Market Profile",
}


def _run_backtest(settings) -> int:
    from .backtest import run_backtest
    from .metrics import compute_metrics, format_report, format_comparison

    provider = _create_provider(settings)
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


def _create_portfolio(settings):
    if not settings.paper_trading:
        return None
    from .paper import PaperPortfolio
    from pathlib import Path
    path = settings.paper_portfolio_path
    if Path(path).exists():
        print(f"  Loading existing portfolio from {path}...")
        return PaperPortfolio.load(path)
    return PaperPortfolio(
        starting_cash=settings.paper_starting_cash,
        cash=settings.paper_starting_cash,
        position_size_pct=settings.paper_position_size_pct,
    )


def _create_risk_manager(settings):
    from .risk import RiskManager, RiskSettings, NullRiskManager
    if not settings.risk:
        return NullRiskManager()
    return RiskManager(RiskSettings(**settings.risk))


def _create_provider(settings):
    provider = create_market_data_provider(settings.market_data)
    if settings.cache_enabled:
        from .cache import CachedDataProvider
        provider = CachedDataProvider(
            upstream=provider,
            cache_dir=settings.cache_dir,
            ttl_seconds=settings.cache_ttl_seconds,
        )
    return provider


def build_engine_from_settings(settings, pretty: bool = False) -> TradingEngine:
    provider = _create_provider(settings)
    strategies = [create_strategy(s) for s in settings.all_strategies]
    notifiers = create_notifiers(settings.notifiers)
    history = create_signal_history(settings.signal_history)
    risk_manager = _create_risk_manager(settings)
    portfolio = _create_portfolio(settings)
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
        risk_manager=risk_manager,
        portfolio=portfolio,
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
    parser.add_argument(
        "--tui",
        action="store_true",
        help="Launch TUI dashboard for live visual monitoring.",
    )
    args = parser.parse_args(argv)

    use_interactive = args.interactive or (args.config is None and sys.stdin.isatty())

    if use_interactive:
        from .interactive import run_interactive_setup
        result = run_interactive_setup()

        if result.backtest:
            return _run_backtest(result.settings)

        if result.tui or args.tui:
            from .tui import run_tui
            run_tui(result.settings)
            return 0

        engine = build_engine_from_settings(result.settings, pretty=True)
        if result.run_once or args.once:
            engine.run_cycle()
            _finalize_portfolio(engine)
            return 0
        try:
            engine.run_forever()
        except KeyboardInterrupt:
            pass
        _finalize_portfolio(engine)
        return 0

    config_path = args.config or "config.example.json"

    if args.tui:
        from .tui import run_tui
        settings = load_settings(config_path)
        run_tui(settings)
        return 0

    engine = build_engine(config_path)

    if args.once:
        engine.run_cycle()
        _finalize_portfolio(engine)
        return 0

    try:
        engine.run_forever()
    except KeyboardInterrupt:
        pass
    _finalize_portfolio(engine)
    return 0


def _finalize_portfolio(engine: TradingEngine) -> None:
    """Show portfolio summary and save state if paper trading is active."""
    if not engine.portfolio:
        return
    print(engine.portfolio.summary())
    path = engine.settings.paper_portfolio_path
    engine.portfolio.save(path)
    print(f"\n  Portfolio saved to {path}")
