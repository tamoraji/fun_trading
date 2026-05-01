"""Trading Service — the single API that all UIs consume.

This is the facade between the UI layer and everything below. All UIs
(CLI, TUI, Web, Telegram) call methods on TradingService instead of
importing engine/strategy/data directly.

Usage:
    from trading_framework.service.api import TradingService

    svc = TradingService()
    engine = svc.create_engine(settings, pretty=True)
    results = svc.run_backtest(settings, symbol="AAPL", strategy_name="rsi")
    portfolio = svc.load_portfolio(path="paper_portfolio.json")
    signals = svc.get_signal_history(limit=50)
    strategies = svc.list_strategies()
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..models import AppSettings, MarketDataConfig, StrategySettings

logger = logging.getLogger(__name__)


class TradingService:
    """Facade for all trading framework operations.

    This class is the ONLY thing UIs should import. It orchestrates
    the engine, strategies, data providers, risk, paper trading,
    backtesting, and signal history.
    """

    # --- Strategy Registry ---

    @staticmethod
    def list_strategies() -> Dict[str, Any]:
        """Return all registered strategies with their metadata.

        Returns:
            Dict of strategy_name -> {"class": cls, "display_name": ..., "params": ...}
        """
        # Ensure strategies are registered
        import trading_framework.strategies  # noqa: F401
        from ..infra.plugin import list_strategies as _list
        from ..interactive import STRATEGY_INFO

        registry = _list()
        result = {}
        for name, cls in registry.items():
            info = STRATEGY_INFO.get(name, {})
            result[name] = {
                "class": cls,
                "display_name": info.get("display_name", name),
                "short_desc": info.get("short_desc", ""),
                "plain_desc": info.get("plain_desc", ""),
                "params": info.get("params", []),
            }
        return result

    @staticmethod
    def list_presets() -> Dict[str, Any]:
        """Return all available presets."""
        from ..interactive import PRESETS
        return dict(PRESETS)

    # --- Engine Construction ---

    @staticmethod
    def create_engine(settings: AppSettings, pretty: bool = False):
        """Build a fully configured TradingEngine from settings.

        Args:
            settings: Application configuration.
            pretty: Use human-readable logging (True for interactive, False for JSON).

        Returns:
            A TradingEngine instance ready to run.
        """
        from ..data import create_market_data_provider
        from ..engine import TradingEngine
        from ..history import create_signal_history
        from ..notifiers import create_notifiers
        from ..strategy import create_strategy
        from ..risk import RiskManager, RiskSettings, NullRiskManager
        from ..structlog import StructuredLogger

        # Data provider (with optional cache)
        provider = create_market_data_provider(settings.market_data)
        if settings.cache_enabled:
            from ..cache import CachedDataProvider
            provider = CachedDataProvider(
                upstream=provider,
                cache_dir=settings.cache_dir,
                ttl_seconds=settings.cache_ttl_seconds,
            )

        # Strategies
        strategies = [create_strategy(s) for s in settings.all_strategies]

        # Notifiers + History
        notifiers = create_notifiers(settings.notifiers)
        history = create_signal_history(settings.signal_history)

        # Risk
        if settings.risk:
            risk_manager = RiskManager(RiskSettings(**settings.risk))
        else:
            risk_manager = NullRiskManager()

        # Paper trading
        portfolio = TradingService.load_portfolio(settings) if settings.paper_trading else None

        # Logger
        if pretty:
            from ..prettylog import PrettyLogger
            log = PrettyLogger()
        else:
            log = StructuredLogger()

        return TradingEngine(
            settings=settings,
            provider=provider,
            strategies=strategies,
            notifiers=notifiers,
            history=history,
            logger=log,
            risk_manager=risk_manager,
            portfolio=portfolio,
        )

    # --- Backtesting ---

    @staticmethod
    def run_backtest(
        settings: AppSettings,
        symbol: str | None = None,
        strategy_name: str | None = None,
    ) -> List[Dict[str, Any]]:
        """Run backtest for all symbols × strategies in settings.

        Args:
            settings: App settings (strategies, market data config, symbols).
            symbol: Override to run on a single symbol (default: all in settings).
            strategy_name: Override to run a single strategy (default: all in settings).

        Returns:
            List of result dicts, each with: symbol, strategy, metrics, trades, chart_data.
        """
        from ..data import create_market_data_provider
        from ..backtest import run_backtest
        from ..metrics import compute_metrics
        from ..strategy import create_strategy

        provider = create_market_data_provider(settings.market_data)
        if settings.cache_enabled:
            from ..cache import CachedDataProvider
            provider = CachedDataProvider(
                upstream=provider,
                cache_dir=settings.cache_dir,
                ttl_seconds=settings.cache_ttl_seconds,
            )

        symbols = [symbol.upper()] if symbol else settings.symbols
        if strategy_name:
            strat_settings = [StrategySettings(name=strategy_name, params={})]
        else:
            strat_settings = settings.all_strategies

        strategies = [create_strategy(s) for s in strat_settings]

        results = []
        for sym in symbols:
            try:
                bars = provider.fetch_bars(sym, settings.market_data)
            except Exception as exc:
                logger.error("Failed to fetch data for %s: %s", sym, exc)
                results.append({"symbol": sym, "error": str(exc)})
                continue

            for strat in strategies:
                bt_result = run_backtest(strat, sym, bars)
                metrics = compute_metrics(bt_result.trades, bt_result.bars)
                results.append({
                    "symbol": sym,
                    "strategy_name": strat.name,
                    "metrics": metrics,
                    "trades": bt_result.trades,
                    "signals": bt_result.signals,
                    "bars": bars,
                })

        return results

    # --- Portfolio ---

    @staticmethod
    def load_portfolio(settings: AppSettings):
        """Load or create a paper trading portfolio.

        Returns:
            PaperPortfolio instance, or None if paper trading is disabled.
        """
        if not settings.paper_trading:
            return None

        from ..paper import PaperPortfolio

        path = settings.paper_portfolio_path
        if Path(path).exists():
            logger.info("Loading existing portfolio from %s", path)
            return PaperPortfolio.load(path)

        return PaperPortfolio(
            starting_cash=settings.paper_starting_cash,
            cash=settings.paper_starting_cash,
            position_size_pct=settings.paper_position_size_pct,
        )

    @staticmethod
    def save_portfolio(engine) -> None:
        """Save portfolio and print summary if paper trading is active."""
        if not engine.portfolio:
            return
        print(engine.portfolio.summary())
        path = engine.settings.paper_portfolio_path
        engine.portfolio.save(path)
        print(f"\n  Portfolio saved to {path}")

    # --- Signal History ---

    @staticmethod
    def get_signal_history(path: str = "signal_history.jsonl", limit: int = 50) -> List[Dict]:
        """Load recent signals from history file.

        Args:
            path: Path to the signal history JSONL file.
            limit: Max number of recent signals to return.

        Returns:
            List of signal dicts (most recent last).
        """
        from ..history import JsonLinesHistory
        history = JsonLinesHistory(path)
        records = history.read_all()
        return records[-limit:]

    # --- Configuration ---

    @staticmethod
    def load_config(config_path: str) -> AppSettings:
        """Load settings from a JSON config file."""
        from ..config import load_settings
        return load_settings(config_path)
