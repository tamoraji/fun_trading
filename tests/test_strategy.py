from datetime import datetime, timedelta, timezone
import unittest

from trading_framework.models import BUY, HOLD, SELL, PriceBar
from trading_framework.strategy import MovingAverageCrossoverStrategy


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


class MovingAverageCrossoverStrategyTests(unittest.TestCase):
    def test_buy_signal_on_bullish_crossover(self):
        strategy = MovingAverageCrossoverStrategy(short_window=3, long_window=5)
        bars = build_bars("AAPL", [12, 12, 12, 12, 12, 10, 9, 8, 9, 12])

        signal = strategy.evaluate("AAPL", bars)

        self.assertEqual(BUY, signal.action)
        self.assertEqual("moving_average_crossover", signal.strategy_name)

    def test_sell_signal_on_bearish_crossover(self):
        strategy = MovingAverageCrossoverStrategy(short_window=3, long_window=5)
        bars = build_bars("AAPL", [8, 8, 8, 8, 8, 10, 11, 12, 11, 8])

        signal = strategy.evaluate("AAPL", bars)

        self.assertEqual(SELL, signal.action)

    def test_hold_when_history_is_too_short(self):
        strategy = MovingAverageCrossoverStrategy(short_window=3, long_window=5)
        bars = build_bars("AAPL", [10, 11, 12, 13, 14])

        signal = strategy.evaluate("AAPL", bars)

        self.assertEqual(HOLD, signal.action)


if __name__ == "__main__":
    unittest.main()
