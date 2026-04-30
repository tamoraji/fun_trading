from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from trading_framework.models import BUY, HOLD, SELL, PriceBar, StrategySettings
from trading_framework.strategy import GoslinMomentumStrategy, create_strategy


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


class GoslinMomentumStrategyTests(unittest.TestCase):
    """Tests for the Goslin Three-Line Momentum strategy."""

    # Use small periods so we can build manageable test data
    # direction_period=10, timing_short=2, timing_long=4, confirming_period=5
    # min_bars = 10 + 5 + 1 = 16

    def _make_strategy(self, **kwargs):
        defaults = {
            "direction_period": 10,
            "timing_short": 2,
            "timing_long": 4,
            "confirming_period": 5,
        }
        defaults.update(kwargs)
        return GoslinMomentumStrategy(**defaults)

    # --- BUY: three-point alignment ---
    def test_buy_signal_three_point_alignment(self):
        strategy = self._make_strategy()
        # Need >= 16 bars. Build an uptrend so price > direction SMA,
        # with a short dip then recovery so timing crosses from <=0 to >0.
        # Base uptrend around 100, rising to ~110
        prices = [
            100, 101, 102, 103, 104, 105, 106, 107, 108, 109,  # bars 0-9: uptrend
            110, 109.5, 109, 108.5,  # bars 10-13: small dip (timing goes negative)
            109, 112,                # bars 14-15: recovery (timing crosses positive)
        ]
        bars = build_bars("AAPL", prices)
        signal = strategy.evaluate("AAPL", bars)
        self.assertEqual(BUY, signal.action)
        self.assertEqual("goslin_momentum", signal.strategy_name)
        self.assertIn("Three-point buy", signal.reason)
        self.assertEqual("above", signal.details["price_vs_direction"])

    # --- SELL: three-point alignment ---
    def test_sell_signal_three_point_alignment(self):
        strategy = self._make_strategy()
        # Downtrend so price < direction SMA, with a short rally then decline
        # so timing crosses from >=0 to <0.
        prices = [
            110, 109, 108, 107, 106, 105, 104, 103, 102, 101,  # bars 0-9: downtrend
            100, 100.5, 101, 101.5,  # bars 10-13: small rally (timing goes positive)
            101, 98,                 # bars 14-15: decline (timing crosses negative)
        ]
        bars = build_bars("AAPL", prices)
        signal = strategy.evaluate("AAPL", bars)
        self.assertEqual(SELL, signal.action)
        self.assertEqual("goslin_momentum", signal.strategy_name)
        self.assertIn("Three-point sell", signal.reason)
        self.assertEqual("below", signal.details["price_vs_direction"])

    # --- HOLD: trend conflicts with timing ---
    def test_hold_when_trend_conflicts_timing(self):
        strategy = self._make_strategy()
        # Uptrend (price above direction) but timing crosses DOWN -- should HOLD, not SELL
        prices = [
            100, 101, 102, 103, 104, 105, 106, 107, 108, 109,  # uptrend
            110, 111, 112, 113,  # continued up (timing positive)
            112, 110,            # small dip (timing may cross down)
        ]
        bars = build_bars("AAPL", prices)
        signal = strategy.evaluate("AAPL", bars)
        # Price is above direction (uptrend), so even if timing turns down, no SELL
        self.assertIn(signal.action, (HOLD, BUY))
        if signal.action == HOLD:
            self.assertIn("not aligned", signal.reason)

    # --- HOLD: not enough history ---
    def test_hold_when_not_enough_history(self):
        strategy = self._make_strategy()  # min_bars = 16
        prices = [100.0] * 10
        bars = build_bars("AAPL", prices)
        signal = strategy.evaluate("AAPL", bars)
        self.assertEqual(HOLD, signal.action)
        self.assertIn("Not enough history", signal.reason)
        self.assertEqual(10, signal.details["bars_available"])
        self.assertEqual(16, signal.details["bars_needed"])

    # --- HOLD: no crossover ---
    def test_hold_when_no_crossover(self):
        strategy = self._make_strategy()
        # Steady uptrend: timing stays positive the whole time, no crossover
        prices = [100 + i * 0.5 for i in range(20)]
        bars = build_bars("AAPL", prices)
        signal = strategy.evaluate("AAPL", bars)
        self.assertEqual(HOLD, signal.action)
        self.assertIn("not aligned", signal.reason)

    # --- Invalid periods ---
    def test_invalid_periods_raise(self):
        with self.assertRaises(ValueError):
            GoslinMomentumStrategy(direction_period=0)
        with self.assertRaises(ValueError):
            GoslinMomentumStrategy(timing_short=-1)
        with self.assertRaises(ValueError):
            GoslinMomentumStrategy(timing_long=0)
        with self.assertRaises(ValueError):
            GoslinMomentumStrategy(confirming_period=-5)
        # timing_short must be < timing_long
        with self.assertRaises(ValueError):
            GoslinMomentumStrategy(timing_short=10, timing_long=10)
        with self.assertRaises(ValueError):
            GoslinMomentumStrategy(timing_short=15, timing_long=10)

    # --- Factory ---
    def test_factory_creates_goslin_strategy(self):
        settings = StrategySettings(
            name="goslin_momentum",
            params={
                "direction_period": 30,
                "timing_short": 2,
                "timing_long": 8,
                "confirming_period": 10,
            },
        )
        strategy = create_strategy(settings)
        self.assertIsInstance(strategy, GoslinMomentumStrategy)
        self.assertEqual(30, strategy.direction_period)
        self.assertEqual(2, strategy.timing_short)
        self.assertEqual(8, strategy.timing_long)
        self.assertEqual(10, strategy.confirming_period)

    def test_factory_creates_goslin_with_defaults(self):
        settings = StrategySettings(name="goslin_momentum", params={})
        strategy = create_strategy(settings)
        self.assertIsInstance(strategy, GoslinMomentumStrategy)
        self.assertEqual(49, strategy.direction_period)
        self.assertEqual(3, strategy.timing_short)
        self.assertEqual(10, strategy.timing_long)
        self.assertEqual(15, strategy.confirming_period)

    # --- Details include all expected fields ---
    def test_details_include_all_fields(self):
        strategy = self._make_strategy()
        prices = [100 + i * 0.5 for i in range(20)]
        bars = build_bars("AAPL", prices)
        signal = strategy.evaluate("AAPL", bars)
        expected_keys = {
            "direction_line", "price_vs_direction",
            "timing_line", "previous_timing",
            "confirming_line", "previous_confirming",
            "direction_period", "timing_short", "timing_long", "confirming_period",
        }
        self.assertEqual(expected_keys, set(signal.details.keys()))
        self.assertEqual(10, signal.details["direction_period"])
        self.assertEqual(2, signal.details["timing_short"])
        self.assertEqual(4, signal.details["timing_long"])
        self.assertEqual(5, signal.details["confirming_period"])


if __name__ == "__main__":
    unittest.main()
