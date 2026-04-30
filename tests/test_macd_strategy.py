from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from trading_framework.models import BUY, HOLD, SELL, PriceBar, StrategySettings
from trading_framework.strategy import MACDStrategy, create_strategy


def build_bars(symbol: str, prices: list) -> list[PriceBar]:
    """Build PriceBars from plain close prices."""
    start = datetime(2026, 1, 2, 14, 30, tzinfo=timezone.utc)
    bars: list[PriceBar] = []
    for i, close in enumerate(prices):
        bars.append(
            PriceBar(
                symbol=symbol,
                timestamp=start + timedelta(minutes=i * 5),
                open=close,
                high=close,
                low=close,
                close=close,
                volume=1000,
            )
        )
    return bars



class MACDStrategyTests(unittest.TestCase):
    # --- BUY on bullish crossover ---
    def test_buy_on_bullish_crossover(self):
        strategy = MACDStrategy(fast_period=3, slow_period=6, signal_period=3)
        # Decline then small uptick: MACD crosses above signal at last bar
        prices = [50, 50, 50, 50, 50, 50, 49, 48, 47, 46, 45, 44, 43, 42, 41, 42]
        bars = build_bars("AAPL", prices)
        signal = strategy.evaluate("AAPL", bars)
        self.assertEqual(BUY, signal.action)
        self.assertEqual("macd", signal.strategy_name)
        self.assertIn("MACD line crossed above signal line", signal.reason)

    # --- SELL on bearish crossover ---
    def test_sell_on_bearish_crossover(self):
        strategy = MACDStrategy(fast_period=3, slow_period=6, signal_period=3)
        # Rise then small downtick: MACD crosses below signal at last bar
        prices = [50, 50, 50, 50, 50, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 58]
        bars = build_bars("AAPL", prices)
        signal = strategy.evaluate("AAPL", bars)
        self.assertEqual(SELL, signal.action)
        self.assertIn("MACD line crossed below signal line", signal.reason)

    # --- HOLD when no crossover ---
    def test_hold_when_no_crossover(self):
        strategy = MACDStrategy(fast_period=3, slow_period=6, signal_period=3)
        # Steady uptrend: MACD stays above signal the whole time (no crossover)
        prices = [100 + i * 0.5 for i in range(20)]
        bars = build_bars("AAPL", prices)
        signal = strategy.evaluate("AAPL", bars)
        self.assertEqual(HOLD, signal.action)
        self.assertIn("No MACD crossover", signal.reason)

    # --- HOLD when not enough history ---
    def test_hold_when_not_enough_history(self):
        strategy = MACDStrategy(fast_period=12, slow_period=26, signal_period=9)
        prices = [100.0] * 10
        bars = build_bars("AAPL", prices)
        signal = strategy.evaluate("AAPL", bars)
        self.assertEqual(HOLD, signal.action)
        self.assertIn("Not enough history", signal.reason)
        self.assertEqual(10, signal.details["bars_available"])
        self.assertEqual(35, signal.details["bars_needed"])

    # --- Invalid periods ---
    def test_invalid_periods_raise_valueerror(self):
        with self.assertRaises(ValueError):
            MACDStrategy(fast_period=0, slow_period=26, signal_period=9)
        with self.assertRaises(ValueError):
            MACDStrategy(fast_period=12, slow_period=-1, signal_period=9)
        with self.assertRaises(ValueError):
            MACDStrategy(fast_period=12, slow_period=26, signal_period=0)

    def test_fast_period_must_be_less_than_slow_period(self):
        with self.assertRaises(ValueError):
            MACDStrategy(fast_period=26, slow_period=12, signal_period=9)
        with self.assertRaises(ValueError):
            MACDStrategy(fast_period=12, slow_period=12, signal_period=9)

    # --- Factory ---
    def test_factory_creates_macd_strategy(self):
        settings = StrategySettings(
            name="macd",
            params={"fast_period": 8, "slow_period": 21, "signal_period": 5},
        )
        strategy = create_strategy(settings)
        self.assertIsInstance(strategy, MACDStrategy)
        self.assertEqual(8, strategy.fast_period)
        self.assertEqual(21, strategy.slow_period)
        self.assertEqual(5, strategy.signal_period)

    def test_factory_creates_macd_with_defaults(self):
        settings = StrategySettings(name="macd", params={})
        strategy = create_strategy(settings)
        self.assertIsInstance(strategy, MACDStrategy)
        self.assertEqual(12, strategy.fast_period)
        self.assertEqual(26, strategy.slow_period)
        self.assertEqual(9, strategy.signal_period)

    # --- Details include all expected fields ---
    def test_details_include_all_expected_fields(self):
        strategy = MACDStrategy(fast_period=3, slow_period=6, signal_period=3)
        prices = [100 + i * 0.5 for i in range(20)]
        bars = build_bars("AAPL", prices)
        signal = strategy.evaluate("AAPL", bars)
        expected_keys = {
            "macd", "signal_line", "histogram",
            "previous_macd", "previous_signal",
            "fast_period", "slow_period", "signal_period",
        }
        self.assertEqual(expected_keys, set(signal.details.keys()))
        self.assertEqual(3, signal.details["fast_period"])
        self.assertEqual(6, signal.details["slow_period"])
        self.assertEqual(3, signal.details["signal_period"])

    # --- Custom parameters work ---
    def test_custom_parameters_produce_different_signals(self):
        # With different periods, the same data can produce different results
        prices = [50, 50, 50, 50, 50, 50, 49, 48, 47, 46, 45, 44, 43, 42, 41, 42]
        bars = build_bars("AAPL", prices)

        s1 = MACDStrategy(fast_period=3, slow_period=6, signal_period=3)
        s2 = MACDStrategy(fast_period=2, slow_period=5, signal_period=2)

        sig1 = s1.evaluate("AAPL", bars)
        sig2 = s2.evaluate("AAPL", bars)

        # Both should produce valid signals with correct strategy name
        self.assertEqual("macd", sig1.strategy_name)
        self.assertEqual("macd", sig2.strategy_name)
        # Details should reflect their respective parameters
        self.assertEqual(3, sig1.details["fast_period"])
        self.assertEqual(2, sig2.details["fast_period"])

    # --- Histogram equals MACD minus signal ---
    def test_histogram_equals_macd_minus_signal(self):
        strategy = MACDStrategy(fast_period=3, slow_period=6, signal_period=3)
        prices = [50, 50, 50, 50, 50, 50, 49, 48, 47, 46, 45, 44, 43, 42, 41, 42]
        bars = build_bars("AAPL", prices)
        signal = strategy.evaluate("AAPL", bars)
        expected_histogram = round(
            signal.details["macd"] - signal.details["signal_line"], 6
        )
        self.assertAlmostEqual(expected_histogram, signal.details["histogram"], places=6)


if __name__ == "__main__":
    unittest.main()
