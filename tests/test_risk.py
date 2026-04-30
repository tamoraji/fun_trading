from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from trading_framework.models import BUY, HOLD, SELL, PriceBar, Signal
from trading_framework.risk import NullRiskManager, RiskManager, RiskSettings


def _signal(symbol="AAPL", action=BUY, price=150.0, timestamp=None):
    return Signal(
        symbol=symbol, action=action, price=price,
        timestamp=timestamp or datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        reason="test", strategy_name="test", details={},
    )


def _bars(volume=10000):
    return [PriceBar(symbol="AAPL", timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
                     open=150, high=155, low=148, close=150, volume=volume)]


class TestCooldown(unittest.TestCase):

    def test_cooldown_blocks_signal_within_window(self):
        rm = RiskManager(RiskSettings(cooldown_seconds=60))
        t0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        t1 = t0 + timedelta(seconds=30)
        result1 = rm.evaluate(_signal(timestamp=t0), _bars())
        self.assertEqual(result1.action, BUY)
        result2 = rm.evaluate(_signal(timestamp=t1), _bars())
        self.assertEqual(result2.action, HOLD)
        self.assertIn("cooldown", result2.details.get("risk_filter", ""))

    def test_cooldown_passes_signal_after_window(self):
        rm = RiskManager(RiskSettings(cooldown_seconds=60))
        t0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        t1 = t0 + timedelta(seconds=61)
        rm.evaluate(_signal(timestamp=t0), _bars())
        result = rm.evaluate(_signal(timestamp=t1), _bars())
        self.assertEqual(result.action, BUY)

    def test_cooldown_disabled_when_zero(self):
        rm = RiskManager(RiskSettings(cooldown_seconds=0))
        t0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        t1 = t0 + timedelta(seconds=1)
        rm.evaluate(_signal(timestamp=t0), _bars())
        result = rm.evaluate(_signal(timestamp=t1), _bars())
        self.assertEqual(result.action, BUY)


class TestPositionAwareness(unittest.TestCase):

    def test_position_blocks_duplicate_buy(self):
        rm = RiskManager(RiskSettings(position_aware=True))
        t0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        t1 = t0 + timedelta(seconds=10)
        rm.evaluate(_signal(action=BUY, timestamp=t0), _bars())
        result = rm.evaluate(_signal(action=BUY, timestamp=t1), _bars())
        self.assertEqual(result.action, HOLD)
        self.assertEqual(result.details["risk_filter"], "position_aware")

    def test_position_blocks_duplicate_sell(self):
        rm = RiskManager(RiskSettings(position_aware=True))
        t0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        t1 = t0 + timedelta(seconds=10)
        rm.evaluate(_signal(action=SELL, timestamp=t0), _bars())
        result = rm.evaluate(_signal(action=SELL, timestamp=t1), _bars())
        self.assertEqual(result.action, HOLD)
        self.assertEqual(result.details["risk_filter"], "position_aware")

    def test_position_allows_opposite_signal(self):
        rm = RiskManager(RiskSettings(position_aware=True))
        t0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        t1 = t0 + timedelta(seconds=10)
        rm.evaluate(_signal(action=BUY, timestamp=t0), _bars())
        result = rm.evaluate(_signal(action=SELL, timestamp=t1), _bars())
        self.assertEqual(result.action, SELL)

    def test_position_tracks_close_and_reopen(self):
        rm = RiskManager(RiskSettings(position_aware=True))
        t0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        t1 = t0 + timedelta(seconds=10)
        t2 = t0 + timedelta(seconds=20)
        # Open long
        rm.evaluate(_signal(action=BUY, timestamp=t0), _bars())
        # Close long (sell opposite)
        rm.evaluate(_signal(action=SELL, timestamp=t1), _bars())
        # Reopen long - should be allowed since position was closed
        result = rm.evaluate(_signal(action=BUY, timestamp=t2), _bars())
        self.assertEqual(result.action, BUY)

    def test_position_disabled_by_default(self):
        rm = RiskManager(RiskSettings())
        t0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        t1 = t0 + timedelta(seconds=10)
        rm.evaluate(_signal(action=BUY, timestamp=t0), _bars())
        result = rm.evaluate(_signal(action=BUY, timestamp=t1), _bars())
        self.assertEqual(result.action, BUY)


class TestVolumeGuard(unittest.TestCase):

    def test_volume_blocks_low_volume(self):
        rm = RiskManager(RiskSettings(min_volume=50000))
        result = rm.evaluate(_signal(), _bars(volume=1000))
        self.assertEqual(result.action, HOLD)
        self.assertEqual(result.details["risk_filter"], "min_volume")

    def test_volume_passes_sufficient_volume(self):
        rm = RiskManager(RiskSettings(min_volume=5000))
        result = rm.evaluate(_signal(), _bars(volume=10000))
        self.assertEqual(result.action, BUY)

    def test_volume_disabled_when_zero(self):
        rm = RiskManager(RiskSettings(min_volume=0))
        result = rm.evaluate(_signal(), _bars(volume=1))
        self.assertEqual(result.action, BUY)


class TestStopLossTakeProfit(unittest.TestCase):

    def test_sl_tp_annotates_buy_signal(self):
        rm = RiskManager(RiskSettings(stop_loss_pct=2.0, take_profit_pct=5.0))
        result = rm.evaluate(_signal(action=BUY, price=100.0), _bars())
        self.assertEqual(result.action, BUY)
        self.assertAlmostEqual(result.details["stop_loss"], 98.0)
        self.assertAlmostEqual(result.details["take_profit"], 105.0)

    def test_sl_tp_annotates_sell_signal(self):
        rm = RiskManager(RiskSettings(stop_loss_pct=2.0, take_profit_pct=5.0))
        result = rm.evaluate(_signal(action=SELL, price=100.0), _bars())
        self.assertEqual(result.action, SELL)
        self.assertAlmostEqual(result.details["stop_loss"], 102.0)
        self.assertAlmostEqual(result.details["take_profit"], 95.0)

    def test_sl_tp_not_added_when_zero(self):
        rm = RiskManager(RiskSettings(stop_loss_pct=0.0, take_profit_pct=0.0))
        result = rm.evaluate(_signal(), _bars())
        self.assertNotIn("stop_loss", result.details)
        self.assertNotIn("take_profit", result.details)


class TestDailyLimit(unittest.TestCase):

    def test_daily_limit_blocks_after_max(self):
        rm = RiskManager(RiskSettings(max_signals_per_day=2))
        t0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        t1 = t0 + timedelta(minutes=1)
        t2 = t0 + timedelta(minutes=2)
        self.assertEqual(rm.evaluate(_signal(timestamp=t0), _bars()).action, BUY)
        self.assertEqual(rm.evaluate(_signal(timestamp=t1), _bars()).action, BUY)
        result = rm.evaluate(_signal(timestamp=t2), _bars())
        self.assertEqual(result.action, HOLD)
        self.assertEqual(result.details["risk_filter"], "daily_limit")


class TestNullRiskManager(unittest.TestCase):

    def test_null_risk_manager_passes_through(self):
        nrm = NullRiskManager()
        sig = _signal()
        result = nrm.evaluate(sig, _bars())
        self.assertIs(result, sig)


if __name__ == "__main__":
    unittest.main()
