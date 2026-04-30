from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from trading_framework.models import BUY, HOLD, SELL, PriceBar, StrategySettings
from trading_framework.strategy import (
    MarketProfileStrategy,
    _compute_value_area,
    create_strategy,
)


def build_bars(
    symbol: str,
    prices: list[float],
    volumes: list[int | float] | None = None,
) -> list[PriceBar]:
    """Build PriceBars from close prices and optional volumes."""
    start = datetime(2026, 1, 2, 14, 30, tzinfo=timezone.utc)
    bars: list[PriceBar] = []
    for i, close in enumerate(prices):
        vol = volumes[i] if volumes else 1000
        bars.append(
            PriceBar(
                symbol=symbol,
                timestamp=start + timedelta(minutes=i * 5),
                open=close,
                high=close,
                low=close,
                close=close,
                volume=vol,
            )
        )
    return bars


class MarketProfileStrategyTests(unittest.TestCase):
    # --- BUY: price crosses back above VAL ---
    def test_buy_when_price_crosses_back_above_val(self):
        # 20 bars with most volume concentrated around $150.
        # Bars at $150 get high volume so VAL will be around $148.
        # Previous bar dips to $140 (below VAL), current bar returns to $148.
        prices = [150.0] * 10 + [148.0] * 5 + [152.0] * 5 + [140.0, 148.0]
        volumes = [5000] * 10 + [4000] * 5 + [3000] * 5 + [100, 100]
        strategy = MarketProfileStrategy(lookback=20, value_area_pct=70.0)
        bars = build_bars("AAPL", prices, volumes)

        signal = strategy.evaluate("AAPL", bars)

        self.assertEqual(BUY, signal.action)
        self.assertEqual("market_profile", signal.strategy_name)
        self.assertIn("mean reversion buy", signal.reason)

    # --- SELL: price crosses back below VAH ---
    def test_sell_when_price_crosses_back_below_vah(self):
        # Most volume around $150, VAH = $150 (70% of volume is in $150 bars).
        # Previous bar at $160 (above VAH), current bar drops to $150 (crosses back to VAH).
        prices = [150.0] * 10 + [148.0] * 5 + [152.0] * 5 + [160.0, 150.0]
        volumes = [5000] * 10 + [4000] * 5 + [3000] * 5 + [100, 100]
        strategy = MarketProfileStrategy(lookback=20, value_area_pct=70.0)
        bars = build_bars("AAPL", prices, volumes)

        signal = strategy.evaluate("AAPL", bars)

        self.assertEqual(SELL, signal.action)
        self.assertIn("mean reversion sell", signal.reason)

    # --- HOLD: price within value area ---
    def test_hold_when_price_within_value_area(self):
        # Both previous and current close within the value area.
        prices = [150.0] * 20 + [150.0, 150.0]
        volumes = [5000] * 20 + [100, 100]
        strategy = MarketProfileStrategy(lookback=20, value_area_pct=70.0)
        bars = build_bars("AAPL", prices, volumes)

        signal = strategy.evaluate("AAPL", bars)

        self.assertEqual(HOLD, signal.action)

    # --- HOLD: not enough history ---
    def test_hold_when_not_enough_history(self):
        prices = [150.0] * 5
        strategy = MarketProfileStrategy(lookback=20, value_area_pct=70.0)
        bars = build_bars("AAPL", prices)

        signal = strategy.evaluate("AAPL", bars)

        self.assertEqual(HOLD, signal.action)
        self.assertEqual(5, signal.details["bars_available"])
        self.assertEqual(21, signal.details["bars_needed"])

    # --- Invalid lookback ---
    def test_invalid_lookback_raises(self):
        with self.assertRaises(ValueError):
            MarketProfileStrategy(lookback=0)
        with self.assertRaises(ValueError):
            MarketProfileStrategy(lookback=-5)

    # --- Invalid value_area_pct ---
    def test_invalid_value_area_pct_raises(self):
        with self.assertRaises(ValueError):
            MarketProfileStrategy(value_area_pct=0)
        with self.assertRaises(ValueError):
            MarketProfileStrategy(value_area_pct=101)

    # --- Factory ---
    def test_factory_creates_market_profile_strategy(self):
        settings = StrategySettings(
            name="market_profile",
            params={"lookback": 10, "value_area_pct": 80.0},
        )
        strategy = create_strategy(settings)

        self.assertIsInstance(strategy, MarketProfileStrategy)
        self.assertEqual(10, strategy.lookback)
        self.assertEqual(80.0, strategy.value_area_pct)

    # --- Details include all fields ---
    def test_details_include_all_fields(self):
        prices = [150.0] * 10 + [148.0] * 5 + [152.0] * 5 + [140.0, 148.0]
        volumes = [5000] * 10 + [4000] * 5 + [3000] * 5 + [100, 100]
        strategy = MarketProfileStrategy(lookback=20, value_area_pct=70.0)
        bars = build_bars("AAPL", prices, volumes)

        signal = strategy.evaluate("AAPL", bars)

        expected_keys = {
            "poc",
            "vwap",
            "vah",
            "val",
            "current_close",
            "previous_close",
            "price_location",
            "lookback",
            "value_area_pct",
        }
        self.assertEqual(expected_keys, set(signal.details.keys()))
        self.assertEqual(148.0, signal.details["current_close"])
        self.assertEqual(140.0, signal.details["previous_close"])
        self.assertEqual(20, signal.details["lookback"])
        self.assertEqual(70.0, signal.details["value_area_pct"])
        self.assertIn(signal.details["price_location"], ("above_value", "in_value", "below_value"))

    # --- _compute_value_area helper ---
    def test_compute_value_area_basic(self):
        # 5 bars: bar at $100 with highest volume should be POC
        prices = [100.0, 102.0, 98.0, 101.0, 99.0]
        volumes = [5000, 1000, 1000, 1000, 1000]
        bars = build_bars("TEST", prices, volumes)

        poc, vwap, vah, val = _compute_value_area(bars, 70.0)

        # POC should be $100 (highest volume bar)
        self.assertEqual(100.0, poc)
        # VWAP: (100*5000 + 102*1000 + 98*1000 + 101*1000 + 99*1000) / 9000
        expected_vwap = (500000 + 102000 + 98000 + 101000 + 99000) / 9000
        self.assertAlmostEqual(expected_vwap, vwap, places=4)
        # Value area: 70% of 9000 = 6300. First bar (5000) + next highest (102, 1000) = 6000, not enough.
        # Need third bar too to reach 7000 >= 6300.
        # So value bars include $100 (5000), $102 (1000), and one of the 1000-volume bars.
        # VAH >= 102, VAL <= 100 (since $100 is in the set)
        self.assertGreaterEqual(vah, 100.0)
        self.assertLessEqual(val, 100.0)

    def test_compute_value_area_zero_volume(self):
        """When all volumes are zero, fallback to simple close-based values."""
        prices = [100.0, 105.0, 95.0]
        volumes = [0, 0, 0]
        bars = build_bars("TEST", prices, volumes)

        poc, vwap, vah, val = _compute_value_area(bars, 70.0)

        self.assertEqual(poc, vwap)  # Both are average of closes
        self.assertEqual(105.0, vah)
        self.assertEqual(95.0, val)


if __name__ == "__main__":
    unittest.main()
