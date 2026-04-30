from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest.mock import patch

from trading_framework.interactive import (
    InteractiveResult,
    run_interactive_setup,
    _save_config_file,
    _compute_lookback,
    _validate_symbol,
    _parse_strategy_choices,
    _is_crypto,
    STRATEGY_INFO,
    PRESETS,
)
from trading_framework.models import AppSettings


class _WizardTestCase(unittest.TestCase):
    """Base for wizard tests with mocked input/output."""

    def _run(self, inputs: list[str]) -> InteractiveResult:
        input_iter = iter(inputs)
        with patch("trading_framework.interactive._input", side_effect=lambda _: next(input_iter)):
            with patch("trading_framework.interactive._print", side_effect=lambda msg="": None):
                return run_interactive_setup()


# ---------------------------------------------------------------------------
# Quick Start path (option 1)
# ---------------------------------------------------------------------------

class QuickStartTests(_WizardTestCase):
    def test_quick_start_stocks_run_once(self):
        inputs = [
            "AAPL",  # symbols
            "1",     # path: Quick Start
            "1",     # run mode: Run once
        ]
        result = self._run(inputs)
        self.assertEqual(["AAPL"], result.settings.symbols)
        self.assertTrue(result.run_once)
        self.assertEqual(2, len(result.settings.all_strategies))
        self.assertTrue(result.settings.paper_trading)
        self.assertIsNotNone(result.settings.market_session)
        self.assertEqual("5m", result.settings.market_data.bar_interval)

    def test_quick_start_crypto_auto_config(self):
        inputs = [
            "BTC-USD",  # crypto symbol
            "1",        # Quick Start
            "1",        # Run once
        ]
        result = self._run(inputs)
        self.assertEqual(["BTC-USD"], result.settings.symbols)
        self.assertIsNone(result.settings.market_session)
        self.assertEqual("1h", result.settings.market_data.bar_interval)
        self.assertEqual("rsi", result.settings.all_strategies[0].name)

    def test_quick_start_backtest(self):
        inputs = [
            "MSFT",  # symbols
            "1",     # Quick Start
            "3",     # Backtest
            "2",     # 2 years
        ]
        result = self._run(inputs)
        self.assertTrue(result.backtest)
        self.assertEqual("2y", result.settings.market_data.lookback)
        self.assertEqual("1d", result.settings.market_data.bar_interval)

    def test_quick_start_tui(self):
        inputs = [
            "SPY",  # symbols
            "1",    # Quick Start
            "4",    # TUI Dashboard
        ]
        result = self._run(inputs)
        self.assertTrue(result.tui)

    def test_quick_start_cancel(self):
        inputs = [
            "AAPL",
            "1",
            "5",  # Cancel
        ]
        with self.assertRaises(SystemExit):
            self._run(inputs)


# ---------------------------------------------------------------------------
# Preset path (option 2)
# ---------------------------------------------------------------------------

class PresetPathTests(_WizardTestCase):
    def test_day_trader_preset(self):
        inputs = [
            "AAPL",  # symbols
            "2",     # Preset
            "1",     # Day Trader
            "1",     # Run once
        ]
        result = self._run(inputs)
        strat_names = [s.name for s in result.settings.all_strategies]
        self.assertIn("macd", strat_names)
        self.assertIn("rsi", strat_names)
        self.assertTrue(result.settings.paper_trading)

    def test_crypto_preset(self):
        inputs = [
            "ETH-USD",
            "2",     # Preset
            "3",     # Crypto
            "1",     # Run once
        ]
        result = self._run(inputs)
        self.assertIsNone(result.settings.market_session)
        self.assertEqual("1h", result.settings.market_data.bar_interval)

    def test_backtest_lab_preset(self):
        inputs = [
            "AAPL",
            "2",     # Preset
            "6",     # Backtest Lab
            "1",     # 1 year
        ]
        result = self._run(inputs)
        self.assertTrue(result.backtest)
        self.assertEqual(6, len(result.settings.all_strategies))

    def test_goslin_preset(self):
        inputs = [
            "SPY",
            "2",     # Preset
            "4",     # Goslin
            "2",     # Monitor
        ]
        result = self._run(inputs)
        self.assertEqual("goslin_momentum", result.settings.all_strategies[0].name)
        self.assertFalse(result.run_once)

    def test_crypto_symbols_auto_disable_market_hours(self):
        inputs = [
            "BTC-USD",
            "2",     # Preset
            "2",     # Swing Trader (normally has market hours)
            "1",     # Run once
        ]
        result = self._run(inputs)
        self.assertIsNone(result.settings.market_session)


# ---------------------------------------------------------------------------
# Advanced path (option 3)
# ---------------------------------------------------------------------------

class AdvancedTests(_WizardTestCase):
    def test_advanced_single_strategy(self):
        inputs = [
            "TSLA",
            "3",     # Advanced
            "2",     # RSI
            "14", "30", "70",  # RSI params
            "1d",    # bar interval
            "300",   # poll
            "n",     # no market session
            "n",     # no risk
            "y", "", "",  # paper trading defaults
            "n",     # don't save
            "1",     # Run once
        ]
        result = self._run(inputs)
        self.assertEqual("rsi", result.settings.strategy.name)
        self.assertTrue(result.settings.paper_trading)

    def test_advanced_multi_strategy(self):
        inputs = [
            "AAPL",
            "3",     # Advanced
            "1,4",   # SMA + MACD
            "5", "20",           # SMA params
            "12", "26", "9",     # MACD params
            "5m",    # bar interval
            "300",   # poll
            "",      # market session default (yes)
            "",      # risk default (yes)
            "",      # position tracking (yes)
            "5",     # stop loss
            "10",    # take profit
            "0",     # cooldown
            "0",     # daily limit
            "",      # paper (yes)
            "",      # cash default
            "",      # size default
            "n",     # don't save
            "1",     # Run once
        ]
        result = self._run(inputs)
        self.assertEqual(2, len(result.settings.all_strategies))

    def test_advanced_cancel(self):
        inputs = [
            "AAPL",
            "3",     # Advanced
            "1",     # SMA
            "", "",  # params
            "",      # bar interval
            "",      # poll
            "",      # market session
            "n",     # no risk
            "n",     # no paper
            "n",     # don't save
            "5",     # Cancel
        ]
        with self.assertRaises(SystemExit):
            self._run(inputs)

    def test_advanced_help_on_param(self):
        inputs = [
            "AAPL",
            "3",     # Advanced
            "1",     # SMA
            "?", "5",  # help then value
            "20",    # long_window
            "",      # bar interval
            "",      # poll
            "",      # market session
            "n",     # no risk
            "n",     # no paper
            "n",     # don't save
            "1",     # Run once
        ]
        result = self._run(inputs)
        self.assertEqual(5, result.settings.strategy.params["short_window"])


# ---------------------------------------------------------------------------
# Symbol handling
# ---------------------------------------------------------------------------

class SymbolTests(_WizardTestCase):
    def test_crypto_warning_continues(self):
        inputs = [
            "ETH",  # triggers warning
            "y",    # continue
            "1",    # Quick Start
            "1",    # Run once
        ]
        result = self._run(inputs)
        self.assertEqual(["ETH"], result.settings.symbols)

    def test_currency_warning_exits(self):
        inputs = [
            "USD",  # triggers warning
            "n",    # don't continue
        ]
        with self.assertRaises(SystemExit):
            self._run(inputs)


# ---------------------------------------------------------------------------
# Utility tests
# ---------------------------------------------------------------------------

class ParseStrategyChoicesTests(unittest.TestCase):
    def test_single(self):
        self.assertEqual([0], _parse_strategy_choices("1", 6))

    def test_comma(self):
        self.assertEqual([0, 1], _parse_strategy_choices("1,2", 6))

    def test_space(self):
        self.assertEqual([0, 1], _parse_strategy_choices("1 2", 6))

    def test_invalid(self):
        self.assertEqual([0], _parse_strategy_choices("1,abc,99", 6))

    def test_dedup(self):
        self.assertEqual([0], _parse_strategy_choices("1,1,1", 6))


class ComputeLookbackTests(unittest.TestCase):
    def test_small(self):
        self.assertEqual("5d", _compute_lookback("5m", 21))

    def test_large(self):
        self.assertIn(_compute_lookback("1d", 201), ("1y", "2y"))


class ValidateSymbolTests(unittest.TestCase):
    def test_valid(self):
        _, w = _validate_symbol("AAPL")
        self.assertIsNone(w)

    def test_crypto_warns(self):
        _, w = _validate_symbol("ETH")
        self.assertIn("ETH-USD", w)

    def test_currency_warns(self):
        _, w = _validate_symbol("USD")
        self.assertIn("currency", w)


class IsCryptoTests(unittest.TestCase):
    def test_crypto(self):
        self.assertTrue(_is_crypto(["BTC-USD"]))

    def test_stocks(self):
        self.assertFalse(_is_crypto(["AAPL"]))


class StrategyInfoTests(unittest.TestCase):
    def test_all_have_required_keys(self):
        for name, info in STRATEGY_INFO.items():
            self.assertIn("display_name", info, name)
            self.assertIn("plain_desc", info, name)
            self.assertIn("params", info, name)
            self.assertIn("bars_needed", info, name)
            for p in info["params"]:
                self.assertIn("help", p, f"{name}/{p['name']}")

    def test_bars_needed_positive(self):
        for name, info in STRATEGY_INFO.items():
            defaults = {p["name"]: p["default"] for p in info["params"]}
            self.assertGreater(info["bars_needed"](defaults), 0)


class PresetValidationTests(unittest.TestCase):
    def test_presets_use_valid_strategies(self):
        for name, preset in PRESETS.items():
            for strat in preset["strategies"]:
                self.assertIn(strat["name"], STRATEGY_INFO, f"Preset {name}: unknown strategy {strat['name']}")


class SaveConfigTests(unittest.TestCase):
    def test_save_and_load(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            _save_config_file(
                path, symbols=["AAPL"],
                selected_strategies=[{"name": "rsi", "info": STRATEGY_INFO["rsi"], "params": {"period": 14}}],
                bar_interval="5m", lookback="5d", poll_seconds=120,
                use_market_session=True, signal_history_path="history.jsonl",
            )
            with open(path) as f:
                config = json.load(f)
            self.assertEqual(["AAPL"], config["symbols"])
            self.assertEqual("rsi", config["strategy"]["name"])
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
