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
    STRATEGY_INFO,
)
from trading_framework.models import AppSettings


class InteractiveSetupTests(unittest.TestCase):
    """Tests for the interactive setup wizard using mocked input/output."""

    def _run_with_inputs(self, inputs: list[str]) -> InteractiveResult:
        """Run interactive setup with a sequence of simulated user inputs."""
        input_iter = iter(inputs)
        outputs = []

        with patch("trading_framework.interactive._input", side_effect=lambda _: next(input_iter)):
            with patch("trading_framework.interactive._print", side_effect=lambda msg="": outputs.append(msg)):
                return run_interactive_setup()

    def test_default_setup_all_enter(self):
        inputs = [
            "",      # symbols -> AAPL, MSFT, SPY
            "",      # strategy -> 1 (SMA)
            "",      # short_window -> 5
            "",      # long_window -> 20
            "",      # bar_interval -> 5m
            "",      # poll_interval -> 300
            "",      # market session -> Yes
            "",      # enable risk -> No
            "",      # cache -> Yes (default)
            "",      # cache TTL -> 300 (default)
            "",      # paper trading -> No
            "",      # signal history -> Yes
            "",      # history path -> signal_history.jsonl
            "",      # save config -> No
            "",      # run mode -> 1 (run once)
        ]
        result = self._run_with_inputs(inputs)

        self.assertEqual(["AAPL", "MSFT", "SPY"], result.settings.symbols)
        self.assertEqual("moving_average_crossover", result.settings.strategy.name)
        self.assertEqual(5, result.settings.strategy.params["short_window"])
        self.assertEqual(300, result.settings.poll_interval_seconds)
        self.assertIsNotNone(result.settings.market_session)
        self.assertIsNotNone(result.settings.signal_history)
        self.assertEqual("5d", result.settings.market_data.lookback)
        self.assertTrue(result.run_once)

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
            "",              # enable risk -> No
            "",              # cache -> Yes (default)
            "",              # cache TTL -> 300 (default)
            "",              # paper trading -> No
            "y",             # signal history
            "",              # history path default
            "n",             # don't save config
            "1",             # run once
        ]
        result = self._run_with_inputs(inputs)

        self.assertEqual(["TSLA", "GOOGL"], result.settings.symbols)
        self.assertEqual("rsi", result.settings.strategy.name)
        self.assertEqual(10, result.settings.strategy.params["period"])
        self.assertEqual("15m", result.settings.market_data.bar_interval)
        self.assertEqual(60, result.settings.poll_interval_seconds)
        self.assertIsNone(result.settings.market_session)

    def test_multi_strategy_selection(self):
        inputs = [
            "AAPL",     # symbols
            "1,2",       # both strategies
            "",          # SMA short_window -> 5
            "",          # SMA long_window -> 20
            "",          # RSI period -> 14
            "",          # RSI oversold -> 30
            "",          # RSI overbought -> 70
            "",          # bar_interval -> 5m
            "",          # poll_interval -> 300
            "",          # market session -> Yes
            "",          # enable risk -> No
            "",          # cache -> Yes (default)
            "",          # cache TTL -> 300 (default)
            "",          # paper trading -> No
            "",          # signal history -> Yes
            "",          # history path
            "",          # save config -> No
            "1",         # run once
        ]
        result = self._run_with_inputs(inputs)

        self.assertEqual(2, len(result.settings.all_strategies))
        self.assertEqual("moving_average_crossover", result.settings.all_strategies[0].name)
        self.assertEqual("rsi", result.settings.all_strategies[1].name)

    def test_continuous_mode(self):
        inputs = [
            "",      # symbols
            "",      # strategy
            "",      # short_window
            "",      # long_window
            "",      # bar_interval
            "",      # poll_interval
            "",      # market session
            "",      # enable risk -> No
            "",      # cache -> Yes (default)
            "",      # cache TTL -> 300 (default)
            "",      # paper trading -> No
            "",      # signal history
            "",      # history path
            "",      # save config
            "2",     # run continuously
        ]
        result = self._run_with_inputs(inputs)
        self.assertFalse(result.run_once)

    def test_backtest_mode(self):
        inputs = [
            "",      # symbols
            "",      # strategy
            "",      # short_window
            "",      # long_window
            "",      # bar_interval
            "",      # poll_interval
            "",      # market session
            "",      # enable risk -> No
            "",      # cache -> Yes (default)
            "",      # cache TTL -> 300 (default)
            "",      # paper trading -> No
            "",      # signal history
            "",      # history path
            "",      # save config
            "3",     # Backtest
            "2",     # 2 years
        ]
        result = self._run_with_inputs(inputs)
        self.assertTrue(result.backtest)
        self.assertEqual("2y", result.settings.market_data.lookback)
        self.assertEqual("1d", result.settings.market_data.bar_interval)

    def test_cancel_exits(self):
        inputs = [
            "",      # symbols
            "",      # strategy
            "",      # short_window
            "",      # long_window
            "",      # bar_interval
            "",      # poll_interval
            "",      # market session
            "",      # enable risk -> No
            "",      # cache -> Yes (default)
            "",      # cache TTL -> 300 (default)
            "",      # paper trading -> No
            "",      # signal history
            "",      # history path
            "",      # save config
            "4",     # Cancel
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
            "",      # enable risk -> No
            "",      # cache -> Yes (default)
            "",      # cache TTL -> 300 (default)
            "",      # paper trading -> No
            "",      # signal history
            "",      # history path
            "",      # save config
            "1",     # run once
        ]
        result = self._run_with_inputs(inputs)
        self.assertEqual("moving_average_crossover", result.settings.strategy.name)

    def test_no_signal_history(self):
        inputs = [
            "",      # symbols
            "",      # strategy
            "",      # short_window
            "",      # long_window
            "",      # bar_interval
            "",      # poll_interval
            "",      # market session
            "",      # enable risk -> No
            "",      # cache -> Yes (default)
            "",      # cache TTL -> 300 (default)
            "",      # paper trading -> No
            "n",     # NO signal history
            "",      # save config
            "1",     # run once
        ]
        result = self._run_with_inputs(inputs)
        self.assertIsNone(result.settings.signal_history)

    def test_risk_management_enabled(self):
        inputs = [
            "",      # symbols
            "",      # strategy
            "",      # short_window
            "",      # long_window
            "",      # bar_interval
            "",      # poll_interval
            "",      # market session
            "y",     # enable risk
            "300",   # cooldown
            "y",     # position aware
            "5",     # stop loss %
            "10",    # take profit %
            "0",     # min volume (off)
            "3",     # max signals per day
            "",      # cache -> Yes (default)
            "",      # cache TTL -> 300 (default)
            "",      # paper trading -> No
            "",      # signal history
            "",      # history path
            "",      # save config
            "1",     # run once
        ]
        result = self._run_with_inputs(inputs)
        self.assertIsNotNone(result.settings.risk)
        self.assertEqual(300, result.settings.risk["cooldown_seconds"])
        self.assertTrue(result.settings.risk["position_aware"])
        self.assertEqual(5.0, result.settings.risk["stop_loss_pct"])
        self.assertEqual(10.0, result.settings.risk["take_profit_pct"])
        self.assertEqual(3, result.settings.risk["max_signals_per_day"])

    def test_large_sma_with_daily_bars_gets_adequate_lookback(self):
        inputs = [
            "BTC-USD",  # symbols
            "1",         # strategy SMA
            "50",        # short_window
            "200",       # long_window
            "1d",        # bar_interval
            "300",       # poll_interval
            "n",         # no market session
            "",          # enable risk -> No
            "",          # cache -> Yes (default)
            "",          # cache TTL -> 300 (default)
            "",          # paper trading -> No
            "y",         # signal history
            "",          # history path
            "n",         # don't save
            "1",         # run once
        ]
        result = self._run_with_inputs(inputs)
        self.assertIn(result.settings.market_data.lookback, ("1y", "2y"))

    def test_symbol_warning_for_crypto_without_usd(self):
        inputs = [
            "ETH",   # symbol (triggers warning)
            "y",     # continue with warning
            "",      # strategy
            "",      # short_window
            "",      # long_window
            "",      # bar_interval
            "",      # poll_interval
            "",      # market session
            "",      # enable risk -> No
            "",      # cache -> Yes (default)
            "",      # cache TTL -> 300 (default)
            "",      # paper trading -> No
            "",      # signal history
            "",      # history path
            "",      # save config
            "1",     # run once
        ]
        result = self._run_with_inputs(inputs)
        self.assertEqual(["ETH"], result.settings.symbols)

    def test_symbol_warning_for_currency_code(self):
        inputs = [
            "USD",   # symbol (triggers warning)
            "n",     # don't continue -> exit
        ]
        with self.assertRaises(SystemExit):
            self._run_with_inputs(inputs)

    def test_cache_disabled(self):
        inputs = [
            "",      # symbols
            "",      # strategy
            "",      # short_window
            "",      # long_window
            "",      # bar_interval
            "",      # poll_interval
            "",      # market session
            "",      # risk -> No
            "n",     # cache -> No
            "",      # paper trading -> No
            "",      # signal history
            "",      # history path
            "",      # save config
            "1",     # run once
        ]
        result = self._run_with_inputs(inputs)
        self.assertFalse(result.settings.cache_enabled)

    def test_paper_trading_enabled(self):
        inputs = [
            "",      # symbols
            "",      # strategy
            "",      # short_window
            "",      # long_window
            "",      # bar_interval
            "",      # poll_interval
            "",      # market session
            "",      # risk -> No
            "",      # cache -> Yes
            "",      # cache TTL -> 300
            "y",     # paper trading -> Yes
            "50000", # starting cash
            "20",    # position size %
            "",      # signal history
            "",      # history path
            "",      # save config
            "1",     # run once
        ]
        result = self._run_with_inputs(inputs)
        self.assertTrue(result.settings.paper_trading)
        self.assertEqual(50000.0, result.settings.paper_starting_cash)
        self.assertEqual(20.0, result.settings.paper_position_size_pct)


class ParseStrategyChoicesTests(unittest.TestCase):
    def test_single(self):
        self.assertEqual([0], _parse_strategy_choices("1", 2))

    def test_comma_separated(self):
        self.assertEqual([0, 1], _parse_strategy_choices("1,2", 2))

    def test_space_separated(self):
        self.assertEqual([0, 1], _parse_strategy_choices("1 2", 2))

    def test_invalid_ignored(self):
        self.assertEqual([0], _parse_strategy_choices("1,abc,99", 2))

    def test_duplicates_removed(self):
        self.assertEqual([0], _parse_strategy_choices("1,1,1", 2))

    def test_empty_returns_empty(self):
        self.assertEqual([], _parse_strategy_choices("abc", 2))


class ComputeLookbackTests(unittest.TestCase):
    def test_small_sma_5m_bars(self):
        self.assertEqual("5d", _compute_lookback("5m", 21))

    def test_large_sma_daily_bars(self):
        result = _compute_lookback("1d", 201)
        self.assertIn(result, ("1y", "2y"))

    def test_medium_rsi_hourly(self):
        self.assertEqual("5d", _compute_lookback("1h", 16))

    def test_very_large_needs_multi_year(self):
        result = _compute_lookback("1d", 500)
        self.assertIn(result, ("2y", "5y"))


class ValidateSymbolTests(unittest.TestCase):
    def test_valid_stock_symbol(self):
        sym, warning = _validate_symbol("AAPL")
        self.assertIsNone(warning)

    def test_crypto_without_usd_warns(self):
        _, warning = _validate_symbol("ETH")
        self.assertIn("ETH-USD", warning)

    def test_currency_code_warns(self):
        _, warning = _validate_symbol("USD")
        self.assertIn("currency", warning)

    def test_valid_crypto_pair_no_warning(self):
        _, warning = _validate_symbol("BTC-USD")
        self.assertIsNone(warning)


class SaveConfigTests(unittest.TestCase):
    def test_save_and_reload_config(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name

        try:
            _save_config_file(
                path,
                symbols=["AAPL"],
                selected_strategies=[
                    {"name": "rsi", "info": STRATEGY_INFO["rsi"], "params": {"period": 14, "oversold": 30, "overbought": 70}},
                ],
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
            self.assertTrue(config["market_session"]["enabled"])
            self.assertTrue(config["signal_history"]["enabled"])
            # Single strategy -> no "strategies" key
            self.assertNotIn("strategies", config)
        finally:
            os.unlink(path)

    def test_save_multi_strategy(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name

        try:
            _save_config_file(
                path,
                symbols=["SPY"],
                selected_strategies=[
                    {"name": "moving_average_crossover", "info": STRATEGY_INFO["moving_average_crossover"], "params": {"short_window": 5, "long_window": 20}},
                    {"name": "rsi", "info": STRATEGY_INFO["rsi"], "params": {"period": 14, "oversold": 30, "overbought": 70}},
                ],
                bar_interval="1d",
                lookback="60d",
                poll_seconds=300,
                use_market_session=False,
                signal_history_path=None,
            )

            with open(path) as f:
                config = json.load(f)

            self.assertIn("strategies", config)
            self.assertEqual(2, len(config["strategies"]))
            self.assertEqual("moving_average_crossover", config["strategies"][0]["name"])
            self.assertEqual("rsi", config["strategies"][1]["name"])
        finally:
            os.unlink(path)

    def test_save_without_market_session(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name

        try:
            _save_config_file(
                path,
                symbols=["SPY"],
                selected_strategies=[
                    {"name": "moving_average_crossover", "info": STRATEGY_INFO["moving_average_crossover"], "params": {"short_window": 5, "long_window": 20}},
                ],
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
            self.assertGreater(bars, 0)


if __name__ == "__main__":
    unittest.main()
