from __future__ import annotations

import math
import unittest
from datetime import datetime, timedelta, timezone

from trading_framework.backtest import Trade
from trading_framework.models import PriceBar
from trading_framework.metrics import (
    BacktestMetrics,
    compute_metrics,
    format_comparison,
    format_report,
)


def _trade(entry_price, exit_price, entry_action="BUY",
           entry_date=None, exit_date=None):
    """Create a Trade with computed profit_pct."""
    if entry_action == "BUY":
        profit_pct = (exit_price - entry_price) / entry_price * 100
    else:
        profit_pct = (entry_price - exit_price) / entry_price * 100
    return Trade(
        symbol="TEST",
        strategy_name="test",
        entry_action=entry_action,
        entry_price=entry_price,
        entry_timestamp=entry_date or datetime(2026, 1, 1, tzinfo=timezone.utc),
        exit_price=exit_price,
        exit_timestamp=exit_date or datetime(2026, 6, 1, tzinfo=timezone.utc),
        profit_pct=round(profit_pct, 4),
    )


def _bars(start_price, end_price, count=100):
    """Create linearly interpolated PriceBars."""
    bars = []
    start = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    for i in range(count):
        price = start_price + (end_price - start_price) * i / max(count - 1, 1)
        bars.append(PriceBar(
            symbol="TEST",
            timestamp=start + timedelta(minutes=i * 5),
            open=price,
            high=price,
            low=price,
            close=price,
            volume=1000,
        ))
    return bars


class TestComputeMetrics(unittest.TestCase):

    def test_total_return_compounding(self):
        # 3 trades: +10%, +5%, -3%
        trades = [
            _trade(100, 110),   # +10%
            _trade(100, 105),   # +5%
            _trade(100, 97),    # -3%
        ]
        bars = _bars(100, 120)
        m = compute_metrics(trades, bars)
        # Compound: 1.10 * 1.05 * 0.97 = 1.12035 -> +12.035%
        expected = round((1.10 * 1.05 * 0.97 - 1) * 100, 4)
        self.assertAlmostEqual(m.total_return_pct, expected, places=3)

    def test_win_rate(self):
        trades = [
            _trade(100, 110),   # win
            _trade(100, 105),   # win
            _trade(100, 90),    # loss
        ]
        bars = _bars(100, 100)
        m = compute_metrics(trades, bars)
        self.assertAlmostEqual(m.win_rate_pct, 66.67, places=2)

    def test_profit_factor(self):
        trades = [
            _trade(100, 120),   # +20%
            _trade(100, 110),   # +10%
            _trade(100, 95),    # -5%
        ]
        bars = _bars(100, 100)
        m = compute_metrics(trades, bars)
        # profit_factor = (20+10) / 5 = 6.0
        self.assertAlmostEqual(m.profit_factor, 6.0, places=4)

    def test_max_drawdown(self):
        # Sequence: +10%, -20%, +5%
        # Equity: 1.10, 0.88, 0.924
        # Peak after first: 1.10, drawdown after second: (1.10-0.88)/1.10 = 20%
        trades = [
            _trade(100, 110),   # +10%
            _trade(100, 80),    # -20%
            _trade(100, 105),   # +5%
        ]
        bars = _bars(100, 100)
        m = compute_metrics(trades, bars)
        expected_dd = round((1.10 - 0.88) / 1.10 * 100, 4)
        self.assertAlmostEqual(m.max_drawdown_pct, expected_dd, places=2)

    def test_sharpe_ratio_positive(self):
        # All positive returns should yield positive Sharpe
        trades = [
            _trade(100, 110, entry_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
                   exit_date=datetime(2026, 2, 1, tzinfo=timezone.utc)),
            _trade(100, 105, entry_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
                   exit_date=datetime(2026, 3, 1, tzinfo=timezone.utc)),
            _trade(100, 108, entry_date=datetime(2026, 3, 1, tzinfo=timezone.utc),
                   exit_date=datetime(2026, 4, 1, tzinfo=timezone.utc)),
        ]
        bars = _bars(100, 120)
        m = compute_metrics(trades, bars)
        self.assertGreater(m.sharpe_ratio, 0)

    def test_buy_and_hold(self):
        bars = _bars(100, 150)
        m = compute_metrics([], bars)
        self.assertAlmostEqual(m.buy_and_hold_return_pct, 50.0, places=2)

    def test_no_trades_returns_zeros(self):
        bars = _bars(100, 100)
        m = compute_metrics([], bars)
        self.assertEqual(m.num_trades, 0)
        self.assertEqual(m.total_return_pct, 0.0)
        self.assertEqual(m.win_rate_pct, 0.0)
        self.assertEqual(m.avg_win_pct, 0.0)
        self.assertEqual(m.avg_loss_pct, 0.0)
        self.assertEqual(m.profit_factor, 0.0)
        self.assertEqual(m.max_drawdown_pct, 0.0)
        self.assertEqual(m.sharpe_ratio, 0.0)

    def test_all_wins_profit_factor_inf(self):
        trades = [
            _trade(100, 110),
            _trade(100, 120),
        ]
        bars = _bars(100, 100)
        m = compute_metrics(trades, bars)
        self.assertEqual(m.profit_factor, float('inf'))

    def test_format_report_contains_key_sections(self):
        trades = [_trade(100, 110), _trade(100, 95)]
        bars = _bars(100, 120)
        m = compute_metrics(trades, bars)
        report = format_report(
            symbol="TEST",
            strategy_name="TestStrategy",
            metrics=m,
            num_signals=4,
            num_bars=100,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 6, 1),
        )
        self.assertIn("TEST", report)
        self.assertIn("TestStrategy", report)
        self.assertIn("Total return", report)
        self.assertIn("Buy & hold", report)
        self.assertIn("Win rate", report)
        self.assertIn("Profit factor", report)
        self.assertIn("Max drawdown", report)
        self.assertIn("Sharpe ratio", report)
        self.assertIn("2026-01-01", report)
        self.assertIn("2026-06-01", report)

    def test_format_comparison_multiple_strategies(self):
        bars = _bars(100, 120)
        trades_a = [_trade(100, 115)]
        trades_b = [_trade(100, 105), _trade(100, 90)]
        m_a = compute_metrics(trades_a, bars)
        m_b = compute_metrics(trades_b, bars)
        table = format_comparison([("StrategyA", m_a), ("StrategyB", m_b)])
        self.assertIn("StrategyA", table)
        self.assertIn("StrategyB", table)
        self.assertIn("Buy & Hold", table)
        self.assertIn("Return", table)
        self.assertIn("Win Rate", table)
        self.assertIn("Sharpe", table)
        self.assertIn("Max DD", table)


if __name__ == "__main__":
    unittest.main()
