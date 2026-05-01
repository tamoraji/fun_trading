"""Tests for the TradingService facade."""
from __future__ import annotations

import unittest

from trading_framework.service.api import TradingService
from trading_framework.models import (
    AppSettings, MarketDataConfig, StrategySettings, NotifierSettings,
)


class TradingServiceTests(unittest.TestCase):
    def _basic_settings(self):
        return AppSettings(
            symbols=["AAPL"],
            poll_interval_seconds=300,
            market_data=MarketDataConfig(),
            strategy=StrategySettings(name="moving_average_crossover"),
            notifiers=[NotifierSettings(type="console")],
        )

    def test_list_strategies_returns_all_six(self):
        strategies = TradingService.list_strategies()
        self.assertGreaterEqual(len(strategies), 6)
        for name in ["moving_average_crossover", "rsi", "breakout", "macd", "goslin_momentum", "market_profile"]:
            self.assertIn(name, strategies)
            self.assertIn("display_name", strategies[name])
            self.assertIn("params", strategies[name])

    def test_list_presets(self):
        presets = TradingService.list_presets()
        self.assertIn("day_trader", presets)
        self.assertIn("crypto", presets)
        self.assertIn("backtest_lab", presets)

    def test_create_engine(self):
        settings = self._basic_settings()
        engine = TradingService.create_engine(settings, pretty=False)
        self.assertIsNotNone(engine)
        self.assertEqual(["AAPL"], engine.settings.symbols)
        self.assertEqual(1, len(engine.strategies))

    def test_create_engine_with_paper_trading(self):
        settings = AppSettings(
            symbols=["AAPL"],
            poll_interval_seconds=300,
            market_data=MarketDataConfig(),
            strategy=StrategySettings(name="rsi"),
            notifiers=[NotifierSettings(type="console")],
            paper_trading=True,
            paper_starting_cash=50_000.0,
            paper_portfolio_path="/tmp/test_svc_portfolio.json",
        )
        engine = TradingService.create_engine(settings)
        self.assertIsNotNone(engine.portfolio)
        self.assertEqual(50_000.0, engine.portfolio.cash)

    def test_get_signal_history_empty(self):
        signals = TradingService.get_signal_history(path="/tmp/nonexistent_test.jsonl", limit=10)
        self.assertEqual([], signals)

    def test_load_config(self):
        settings = TradingService.load_config("config.example.json")
        self.assertIn("AAPL", settings.symbols)


if __name__ == "__main__":
    unittest.main()
