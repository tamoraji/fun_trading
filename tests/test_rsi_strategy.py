from datetime import datetime, timedelta, timezone
import unittest

from trading_framework.models import BUY, HOLD, SELL, PriceBar
from trading_framework.strategy import RSIStrategy, create_strategy, StrategySettings


def build_bars(symbol, closes):
    start = datetime(2026, 1, 2, 14, 30, tzinfo=timezone.utc)
    bars = []
    for index, close in enumerate(closes):
        timestamp = start + timedelta(minutes=index * 5)
        bars.append(
            PriceBar(
                symbol=symbol,
                timestamp=timestamp,
                open=close,
                high=close,
                low=close,
                close=close,
                volume=1000 + index,
            )
        )
    return bars


class RSIStrategyTests(unittest.TestCase):
    def test_buy_signal_when_rsi_crosses_below_oversold(self):
        # Alternating prices then a big drop -> RSI crosses below oversold
        closes = [50, 51, 50, 51, 50, 51, 50, 51, 50, 51, 50, 51, 50, 51, 50, 41]
        strategy = RSIStrategy(period=14, oversold=30, overbought=70)
        bars = build_bars("AAPL", closes)

        signal = strategy.evaluate("AAPL", bars)

        self.assertEqual(BUY, signal.action)
        self.assertEqual("rsi", signal.strategy_name)
        self.assertIn("rsi", signal.details)
        self.assertLess(signal.details["rsi"], 30)

    def test_sell_signal_when_rsi_crosses_above_overbought(self):
        # Alternating prices then a big rise -> RSI crosses above overbought
        closes = [50, 49, 50, 49, 50, 49, 50, 49, 50, 49, 50, 49, 50, 49, 50, 59]
        strategy = RSIStrategy(period=14, oversold=30, overbought=70)
        bars = build_bars("AAPL", closes)

        signal = strategy.evaluate("AAPL", bars)

        self.assertEqual(SELL, signal.action)
        self.assertIn("rsi", signal.details)
        self.assertGreater(signal.details["rsi"], 70)

    def test_hold_when_rsi_is_neutral(self):
        # Alternating up and down -> RSI near 50
        closes = [50, 51, 50, 51, 50, 51, 50, 51, 50, 51, 50, 51, 50, 51, 50, 51]
        strategy = RSIStrategy(period=14, oversold=30, overbought=70)
        bars = build_bars("AAPL", closes)

        signal = strategy.evaluate("AAPL", bars)

        self.assertEqual(HOLD, signal.action)

    def test_hold_when_not_enough_history(self):
        closes = [50, 51, 52]
        strategy = RSIStrategy(period=14, oversold=30, overbought=70)
        bars = build_bars("AAPL", closes)

        signal = strategy.evaluate("AAPL", bars)

        self.assertEqual(HOLD, signal.action)
        self.assertIn("bars_available", signal.details)

    def test_configurable_thresholds(self):
        # Use wider oversold threshold so a moderate drop triggers a BUY
        closes = [50, 51, 50, 51, 50, 51, 50, 51, 50, 51, 50, 51, 50, 51, 50, 44]
        strategy = RSIStrategy(period=14, oversold=40, overbought=60)
        bars = build_bars("AAPL", closes)

        signal = strategy.evaluate("AAPL", bars)

        self.assertEqual(BUY, signal.action)

    def test_invalid_period_raises(self):
        with self.assertRaises(ValueError):
            RSIStrategy(period=0)

    def test_invalid_thresholds_raises(self):
        with self.assertRaises(ValueError):
            RSIStrategy(period=14, oversold=70, overbought=30)

    def test_factory_creates_rsi_strategy(self):
        settings = StrategySettings(
            name="rsi",
            params={"period": 14, "oversold": 25, "overbought": 75},
        )
        strategy = create_strategy(settings)

        self.assertIsInstance(strategy, RSIStrategy)
        self.assertEqual(14, strategy.period)
        self.assertEqual(25, strategy.oversold)
        self.assertEqual(75, strategy.overbought)

    def test_rsi_details_include_period_and_thresholds(self):
        closes = [50, 51, 50, 51, 50, 51, 50, 51, 50, 51, 50, 51, 50, 51, 50, 41]
        strategy = RSIStrategy(period=14, oversold=30, overbought=70)
        bars = build_bars("AAPL", closes)

        signal = strategy.evaluate("AAPL", bars)

        self.assertEqual(14, signal.details["period"])
        self.assertEqual(30, signal.details["oversold"])
        self.assertEqual(70, signal.details["overbought"])


if __name__ == "__main__":
    unittest.main()
