from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from trading_framework.models import BUY, HOLD, SELL, PriceBar, Signal
from trading_framework.strategy import MovingAverageCrossoverStrategy
from trading_framework.backtest import (
    BacktestResult,
    Trade,
    match_trades,
    replay_bars,
    run_backtest,
)


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


def _make_signal(action, price, minutes_offset=0, symbol="TEST", strategy_name="test_strategy"):
    ts = datetime(2026, 1, 2, 14, 30, tzinfo=timezone.utc) + timedelta(minutes=minutes_offset)
    return Signal(
        symbol=symbol,
        action=action,
        price=price,
        timestamp=ts,
        reason="test",
        strategy_name=strategy_name,
    )


class TestReplayBars(unittest.TestCase):
    def test_replay_bars_collects_signals(self):
        strategy = MovingAverageCrossoverStrategy(short_window=3, long_window=5)
        # Prices that create a bearish then bullish crossover
        closes = [12, 12, 12, 12, 12, 10, 9, 8, 9, 12]
        bars = build_bars("AAPL", closes)

        signals = replay_bars(strategy, "AAPL", bars)

        actions = [s.action for s in signals]
        self.assertTrue(len(signals) > 0, "Should collect at least one signal")
        for s in signals:
            self.assertIn(s.action, [BUY, SELL])

    def test_replay_bars_skips_holds(self):
        strategy = MovingAverageCrossoverStrategy(short_window=3, long_window=5)
        # Flat prices produce only HOLD signals
        closes = [10, 10, 10, 10, 10, 10, 10, 10, 10, 10]
        bars = build_bars("AAPL", closes)

        signals = replay_bars(strategy, "AAPL", bars)

        self.assertEqual(len(signals), 0, "HOLD signals should not appear in output")


class TestMatchTrades(unittest.TestCase):
    def test_match_trades_buy_then_sell(self):
        signals = [
            _make_signal(BUY, 100.0, minutes_offset=0),
            _make_signal(SELL, 110.0, minutes_offset=5),
        ]

        trades = match_trades(signals)

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].entry_action, BUY)
        self.assertAlmostEqual(trades[0].profit_pct, 10.0)

    def test_match_trades_ignores_same_direction(self):
        signals = [
            _make_signal(BUY, 100.0, minutes_offset=0),
            _make_signal(BUY, 105.0, minutes_offset=5),
            _make_signal(SELL, 110.0, minutes_offset=10),
        ]

        trades = match_trades(signals)

        self.assertEqual(len(trades), 1)
        # First BUY at 100 is the entry, second BUY is ignored
        self.assertEqual(trades[0].entry_price, 100.0)
        self.assertEqual(trades[0].exit_price, 110.0)
        self.assertAlmostEqual(trades[0].profit_pct, 10.0)

    def test_match_trades_no_close(self):
        signals = [
            _make_signal(BUY, 100.0, minutes_offset=0),
        ]

        trades = match_trades(signals)

        self.assertEqual(len(trades), 0)

    def test_match_trades_multiple_roundtrips(self):
        signals = [
            _make_signal(BUY, 100.0, minutes_offset=0),
            _make_signal(SELL, 110.0, minutes_offset=5),
            _make_signal(BUY, 105.0, minutes_offset=10),
            _make_signal(SELL, 115.0, minutes_offset=15),
        ]

        trades = match_trades(signals)

        self.assertEqual(len(trades), 2)
        self.assertAlmostEqual(trades[0].profit_pct, 10.0)
        self.assertAlmostEqual(trades[1].profit_pct, round((115 - 105) / 105 * 100, 4))

    def test_match_trades_short_trade(self):
        signals = [
            _make_signal(SELL, 100.0, minutes_offset=0),
            _make_signal(BUY, 90.0, minutes_offset=5),
        ]

        trades = match_trades(signals)

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].entry_action, SELL)
        self.assertAlmostEqual(trades[0].profit_pct, 10.0)

    def test_match_trades_long_trade_profit(self):
        signals = [
            _make_signal(BUY, 100.0, minutes_offset=0),
            _make_signal(SELL, 110.0, minutes_offset=5),
        ]

        trades = match_trades(signals)

        self.assertEqual(len(trades), 1)
        self.assertAlmostEqual(trades[0].profit_pct, 10.0)

    def test_match_trades_losing_trade(self):
        signals = [
            _make_signal(BUY, 100.0, minutes_offset=0),
            _make_signal(SELL, 90.0, minutes_offset=5),
        ]

        trades = match_trades(signals)

        self.assertEqual(len(trades), 1)
        self.assertAlmostEqual(trades[0].profit_pct, -10.0)


class TestRunBacktest(unittest.TestCase):
    def test_run_backtest_integration(self):
        strategy = MovingAverageCrossoverStrategy(short_window=3, long_window=5)
        # Prices that create crossovers: down then up
        closes = [12, 12, 12, 12, 12, 10, 9, 8, 9, 12]
        bars = build_bars("AAPL", closes)

        result = run_backtest(strategy, "AAPL", bars)

        self.assertIsInstance(result, BacktestResult)
        self.assertEqual(result.symbol, "AAPL")
        self.assertEqual(result.strategy_name, "moving_average_crossover")
        self.assertEqual(result.bars, bars)
        self.assertTrue(len(result.signals) > 0)
        # All trades should be valid Trade instances
        for trade in result.trades:
            self.assertIsInstance(trade, Trade)


if __name__ == "__main__":
    unittest.main()
