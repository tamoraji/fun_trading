from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from trading_framework.models import BUY, HOLD, SELL, PriceBar, StrategySettings
from trading_framework.strategy import BreakoutStrategy, create_strategy


def build_bars(symbol: str, prices: list, volumes: list | None = None) -> list[PriceBar]:
    """Build PriceBars from (close, high, low) tuples or plain floats."""
    start = datetime(2026, 1, 2, 14, 30, tzinfo=timezone.utc)
    bars: list[PriceBar] = []
    for i, p in enumerate(prices):
        if isinstance(p, tuple):
            close, high, low = p
        else:
            close = high = low = float(p)
        vol = volumes[i] if volumes else 1000
        bars.append(
            PriceBar(
                symbol=symbol,
                timestamp=start + timedelta(minutes=i * 5),
                open=close,
                high=high,
                low=low,
                close=close,
                volume=vol,
            )
        )
    return bars


class BreakoutStrategyTests(unittest.TestCase):
    # --- BUY ---
    def test_buy_on_upward_breakout_with_volume_confirmation(self):
        # 20 bars with high=105, then bar 21 closes at 106 with high volume
        prices = [(100.0, 105.0, 95.0)] * 20 + [(106.0, 106.0, 106.0)]
        volumes = [1000] * 20 + [2000]  # 2000 >= 1.5 * 1000
        strategy = BreakoutStrategy(lookback=20, volume_factor=1.5)
        bars = build_bars("AAPL", prices, volumes)

        signal = strategy.evaluate("AAPL", bars)

        self.assertEqual(BUY, signal.action)
        self.assertEqual("breakout", signal.strategy_name)
        self.assertTrue(signal.details["volume_confirmed"])

    # --- SELL ---
    def test_sell_on_downward_breakout_with_volume_confirmation(self):
        prices = [(100.0, 105.0, 95.0)] * 20 + [(94.0, 94.0, 94.0)]
        volumes = [1000] * 20 + [2000]
        strategy = BreakoutStrategy(lookback=20, volume_factor=1.5)
        bars = build_bars("AAPL", prices, volumes)

        signal = strategy.evaluate("AAPL", bars)

        self.assertEqual(SELL, signal.action)
        self.assertTrue(signal.details["volume_confirmed"])

    # --- HOLD: within channel ---
    def test_hold_when_price_within_channel(self):
        prices = [(100.0, 105.0, 95.0)] * 20 + [(100.0, 100.0, 100.0)]
        volumes = [1000] * 21
        strategy = BreakoutStrategy(lookback=20, volume_factor=1.5)
        bars = build_bars("AAPL", prices, volumes)

        signal = strategy.evaluate("AAPL", bars)

        self.assertEqual(HOLD, signal.action)

    # --- HOLD: not enough history ---
    def test_hold_when_not_enough_history(self):
        prices = [100.0] * 5
        strategy = BreakoutStrategy(lookback=20, volume_factor=1.5)
        bars = build_bars("AAPL", prices)

        signal = strategy.evaluate("AAPL", bars)

        self.assertEqual(HOLD, signal.action)
        self.assertEqual(5, signal.details["bars_available"])
        self.assertEqual(21, signal.details["bars_needed"])

    # --- HOLD: breakout but volume too low ---
    def test_hold_when_breakout_but_volume_too_low(self):
        prices = [(100.0, 105.0, 95.0)] * 20 + [(106.0, 106.0, 106.0)]
        volumes = [1000] * 20 + [1000]  # 1000 < 1.5 * 1000
        strategy = BreakoutStrategy(lookback=20, volume_factor=1.5)
        bars = build_bars("AAPL", prices, volumes)

        signal = strategy.evaluate("AAPL", bars)

        self.assertEqual(HOLD, signal.action)
        self.assertFalse(signal.details["volume_confirmed"])

    # --- BUY with volume_factor=0 (disabled) ---
    def test_buy_when_volume_factor_disabled(self):
        prices = [(100.0, 105.0, 95.0)] * 20 + [(106.0, 106.0, 106.0)]
        volumes = [1000] * 21  # low volume, but factor is 0
        strategy = BreakoutStrategy(lookback=20, volume_factor=0)
        bars = build_bars("AAPL", prices, volumes)

        signal = strategy.evaluate("AAPL", bars)

        self.assertEqual(BUY, signal.action)
        self.assertTrue(signal.details["volume_confirmed"])

    # --- Invalid lookback ---
    def test_invalid_lookback_raises(self):
        with self.assertRaises(ValueError):
            BreakoutStrategy(lookback=0)

        with self.assertRaises(ValueError):
            BreakoutStrategy(lookback=-5)

    # --- Factory ---
    def test_factory_creates_breakout_strategy(self):
        settings = StrategySettings(
            name="breakout",
            params={"lookback": 10, "volume_factor": 2.0},
        )
        strategy = create_strategy(settings)

        self.assertIsInstance(strategy, BreakoutStrategy)
        self.assertEqual(10, strategy.lookback)
        self.assertEqual(2.0, strategy.volume_factor)

    # --- Details include all expected fields ---
    def test_details_include_all_expected_fields(self):
        prices = [(100.0, 105.0, 95.0)] * 20 + [(106.0, 106.0, 106.0)]
        volumes = [1000] * 20 + [2000]
        strategy = BreakoutStrategy(lookback=20, volume_factor=1.5)
        bars = build_bars("AAPL", prices, volumes)

        signal = strategy.evaluate("AAPL", bars)

        expected_keys = {
            "channel_high",
            "channel_low",
            "current_close",
            "current_volume",
            "average_volume",
            "volume_confirmed",
            "lookback",
        }
        self.assertEqual(expected_keys, set(signal.details.keys()))
        self.assertEqual(105.0, signal.details["channel_high"])
        self.assertEqual(95.0, signal.details["channel_low"])
        self.assertEqual(106.0, signal.details["current_close"])
        self.assertEqual(2000, signal.details["current_volume"])
        self.assertEqual(20, signal.details["lookback"])


if __name__ == "__main__":
    unittest.main()
