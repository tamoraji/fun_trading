from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest.mock import patch

from trading_framework.interactive import (
    run_interactive_setup,
    _save_config_file,
    _compute_lookback,
    _validate_symbol,
    STRATEGY_INFO,
)
from trading_framework.models import AppSettings


class InteractiveSetupTests(unittest.TestCase):
    """Tests for the interactive setup wizard using mocked input/output."""

    def _run_with_inputs(self, inputs: list[str]) -> AppSettings:
        """Run interactive setup with a sequence of simulated user inputs."""
        input_iter = iter(inputs)
        outputs = []

        with patch("trading_framework.interactive._input", side_effect=lambda _: next(input_iter)):
            with patch("trading_framework.interactive._print", side_effect=lambda msg="": outputs.append(msg)):
                return run_interactive_setup()

    def test_default_setup_all_enter(self):
        # User presses Enter for every prompt (all defaults)
        inputs = [
            "",      # symbols -> AAPL, MSFT, SPY
            "",      # strategy -> 1 (SMA)
            "",      # short_window -> 5
            "",      # long_window -> 20
            "",      # bar_interval -> 5m
            "",      # poll_interval -> 300
            "",      # market session -> Yes
            "",      # signal history -> Yes
            "",      # history path -> signal_history.jsonl
            "",      # save config -> No
            "",      # start monitoring -> Yes
        ]
        settings = self._run_with_inputs(inputs)

        self.assertEqual(["AAPL", "MSFT", "SPY"], settings.symbols)
        self.assertEqual("moving_average_crossover", settings.strategy.name)
        self.assertEqual(5, settings.strategy.params["short_window"])
        self.assertEqual(20, settings.strategy.params["long_window"])
        self.assertEqual(300, settings.poll_interval_seconds)
        self.assertIsNotNone(settings.market_session)
        self.assertIsNotNone(settings.signal_history)
        # Default SMA needs 21 bars of 5m data -> lookback should be "5d"
        self.assertEqual("5d", settings.market_data.lookback)

    def test_rsi_strategy_selection(self):
        inputs = [
            "TSLA, GOOGL",  # symbols
            "2",             # strategy -> RSI
            "10",            # period
            "25",            # oversold
            "75",            # overbought
            "15m",           # bar_interval
            "60",            # poll_interval
            "n",             # no market session
            "y",             # signal history
            "",              # history path default
            "n",             # don't save config
            "y",             # start
        ]
        settings = self._run_with_inputs(inputs)

        self.assertEqual(["TSLA", "GOOGL"], settings.symbols)
        self.assertEqual("rsi", settings.strategy.name)
        self.assertEqual(10, settings.strategy.params["period"])
        self.assertEqual(25, settings.strategy.params["oversold"])
        self.assertEqual(75, settings.strategy.params["overbought"])
        self.assertEqual("15m", settings.market_data.bar_interval)
        self.assertEqual(60, settings.poll_interval_seconds)
        self.assertIsNone(settings.market_session)

    def test_cancel_exits(self):
        inputs = [
            "",      # symbols
            "",      # strategy
            "",      # short_window
            "",      # long_window
            "",      # bar_interval
            "",      # poll_interval
            "",      # market session
            "",      # signal history
            "",      # history path
            "",      # save config
            "n",     # DON'T start -> should exit
        ]
        with self.assertRaises(SystemExit):
            self._run_with_inputs(inputs)

    def test_invalid_strategy_defaults_to_first(self):
        inputs = [
            "",      # symbols
            "99",    # invalid strategy number
            "",      # short_window
            "",      # long_window
            "",      # bar_interval
            "",      # poll_interval
            "",      # market session
            "",      # signal history
            "",      # history path
            "",      # save config
            "y",     # start
        ]
        settings = self._run_with_inputs(inputs)
        self.assertEqual("moving_average_crossover", settings.strategy.name)

    def test_no_signal_history(self):
        inputs = [
            "",      # symbols
            "",      # strategy
            "",      # short_window
            "",      # long_window
            "",      # bar_interval
            "",      # poll_interval
            "",      # market session
            "n",     # NO signal history
            "",      # save config
            "y",     # start
        ]
        settings = self._run_with_inputs(inputs)
        self.assertIsNone(settings.signal_history)

    def test_large_sma_with_daily_bars_gets_adequate_lookback(self):
        # SMA 50/200 with 1d bars needs 201 bars = ~201 days -> should be "2y"
        inputs = [
            "BTC-USD",  # symbols
            "1",         # strategy SMA
            "50",        # short_window
            "200",       # long_window
            "1d",        # bar_interval (daily!)
            "300",       # poll_interval
            "n",         # no market session
            "y",         # signal history
            "",          # history path
            "n",         # don't save
            "y",         # start
        ]
        settings = self._run_with_inputs(inputs)
        # 201 bars of daily data needs more than 6 months
        self.assertIn(settings.market_data.lookback, ("1y", "2y"))

    def test_symbol_warning_for_crypto_without_usd(self):
        # ETH without -USD triggers warning, user confirms
        inputs = [
            "ETH",   # symbol (triggers warning)
            "y",     # continue with warning
            "",      # strategy
            "",      # short_window
            "",      # long_window
            "",      # bar_interval
            "",      # poll_interval
            "",      # market session
            "",      # signal history
            "",      # history path
            "",      # save config
            "y",     # start
        ]
        settings = self._run_with_inputs(inputs)
        self.assertEqual(["ETH"], settings.symbols)

    def test_symbol_warning_for_currency_code(self):
        # USD alone triggers warning, user declines -> exit
        inputs = [
            "USD",   # symbol (triggers warning)
            "n",     # don't continue -> exit
        ]
        with self.assertRaises(SystemExit):
            self._run_with_inputs(inputs)


class ComputeLookbackTests(unittest.TestCase):
    def test_small_sma_5m_bars(self):
        # 21 bars of 5m data -> tiny, should be "5d"
        self.assertEqual("5d", _compute_lookback("5m", 21))

    def test_large_sma_daily_bars(self):
        # 201 bars of daily data -> ~301 days with buffer
        result = _compute_lookback("1d", 201)
        self.assertIn(result, ("1y", "2y"))

    def test_medium_rsi_hourly(self):
        # 16 bars of 1h data -> ~3.4 days with buffer -> "5d"
        self.assertEqual("5d", _compute_lookback("1h", 16))

    def test_very_large_needs_multi_year(self):
        # 500 bars of daily data -> ~750 days
        result = _compute_lookback("1d", 500)
        self.assertIn(result, ("2y", "5y"))


class ValidateSymbolTests(unittest.TestCase):
    def test_valid_stock_symbol(self):
        sym, warning = _validate_symbol("AAPL")
        self.assertEqual("AAPL", sym)
        self.assertIsNone(warning)

    def test_crypto_without_usd_warns(self):
        sym, warning = _validate_symbol("ETH")
        self.assertEqual("ETH", sym)
        self.assertIn("ETH-USD", warning)

    def test_currency_code_warns(self):
        sym, warning = _validate_symbol("USD")
        self.assertEqual("USD", sym)
        self.assertIn("currency", warning)

    def test_valid_crypto_pair_no_warning(self):
        sym, warning = _validate_symbol("BTC-USD")
        self.assertEqual("BTC-USD", sym)
        self.assertIsNone(warning)


class SaveConfigTests(unittest.TestCase):
    def test_save_and_reload_config(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name

        try:
            _save_config_file(
                path,
                symbols=["AAPL"],
                strategy_name="rsi",
                strategy_params={"period": 14, "oversold": 30, "overbought": 70},
                bar_interval="5m",
                lookback="5d",
                poll_seconds=120,
                use_market_session=True,
                signal_history_path="history.jsonl",
            )

            with open(path) as f:
                config = json.load(f)

            self.assertEqual(["AAPL"], config["symbols"])
            self.assertEqual("rsi", config["strategy"]["name"])
            self.assertEqual(14, config["strategy"]["params"]["period"])
            self.assertEqual(120, config["poll_interval_seconds"])
            self.assertEqual("5d", config["market_data"]["lookback"])
            self.assertTrue(config["market_session"]["enabled"])
            self.assertTrue(config["signal_history"]["enabled"])
        finally:
            os.unlink(path)

    def test_save_without_market_session(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name

        try:
            _save_config_file(
                path,
                symbols=["SPY"],
                strategy_name="moving_average_crossover",
                strategy_params={"short_window": 5, "long_window": 20},
                bar_interval="1d",
                lookback="60d",
                poll_seconds=300,
                use_market_session=False,
                signal_history_path=None,
            )

            with open(path) as f:
                config = json.load(f)

            self.assertFalse(config["market_session"]["enabled"])
            self.assertNotIn("signal_history", config)
            self.assertEqual("60d", config["market_data"]["lookback"])
        finally:
            os.unlink(path)


class StrategyInfoTests(unittest.TestCase):
    def test_all_strategies_have_required_keys(self):
        for name, info in STRATEGY_INFO.items():
            self.assertIn("display_name", info, f"{name} missing display_name")
            self.assertIn("short_desc", info, f"{name} missing short_desc")
            self.assertIn("params", info, f"{name} missing params")
            self.assertIn("bars_needed", info, f"{name} missing bars_needed")
            for param in info["params"]:
                self.assertIn("name", param)
                self.assertIn("prompt", param)
                self.assertIn("default", param)

    def test_bars_needed_functions_return_positive_int(self):
        for name, info in STRATEGY_INFO.items():
            defaults = {p["name"]: p["default"] for p in info["params"]}
            bars = info["bars_needed"](defaults)
            self.assertGreater(bars, 0, f"{name} bars_needed should be positive")


if __name__ == "__main__":
    unittest.main()
