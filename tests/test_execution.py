"""Tests for execution layer: broker, order manager, position sizer."""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from trading_framework.models import BUY, SELL, Signal
from trading_framework.infra.event_bus import EventBus
from trading_framework.core.events import ApprovalRequested, ApprovalReceived, OrderFilled
from trading_framework.execution.broker import Broker
from trading_framework.execution.order_manager import OrderManager, OrderStatus
from trading_framework.execution.position_sizer import (
    FixedPercentSizer, FixedAmountSizer, RiskPerTradeSizer, KellyCriterionSizer,
)


def _signal(symbol="AAPL", action=BUY, price=150.0):
    return Signal(
        symbol=symbol, action=action, price=price,
        timestamp=datetime(2026, 5, 1, 14, 0, tzinfo=timezone.utc),
        reason="test", strategy_name="test", details={},
    )


class FakeBroker:
    """Simple mock broker for testing."""
    def __init__(self):
        self.orders = []

    def execute(self, signal):
        class FakeOrder:
            def __init__(s):
                s.symbol = signal.symbol
                s.action = signal.action
                s.price = signal.price
                s.quantity = 10.0
                s.pnl = None
        order = FakeOrder()
        self.orders.append(order)
        return order


# ---------------------------------------------------------------------------
# Order Manager
# ---------------------------------------------------------------------------

class OrderManagerAutoTests(unittest.TestCase):
    def test_auto_mode_executes_immediately(self):
        broker = FakeBroker()
        manager = OrderManager(broker=broker, mode="auto")
        result = manager.execute(_signal())
        self.assertIsNotNone(result)
        self.assertEqual(1, len(broker.orders))

    def test_auto_mode_publishes_order_filled(self):
        bus = EventBus()
        events = []
        bus.subscribe(OrderFilled, lambda e: events.append(e))

        broker = FakeBroker()
        manager = OrderManager(broker=broker, event_bus=bus, mode="auto")
        manager.execute(_signal())
        self.assertEqual(1, len(events))
        self.assertEqual("AAPL", events[0].symbol)

    def test_no_broker_returns_none(self):
        manager = OrderManager(broker=None, mode="auto")
        result = manager.execute(_signal())
        self.assertIsNone(result)


class OrderManagerApprovalTests(unittest.TestCase):
    def test_approval_mode_queues_order(self):
        broker = FakeBroker()
        manager = OrderManager(broker=broker, mode="approval")
        pending = manager.execute(_signal())
        self.assertEqual(OrderStatus.PENDING_APPROVAL, pending.status)
        self.assertEqual(0, len(broker.orders))  # not executed yet
        self.assertEqual(1, len(manager.pending_orders))

    def test_approve_executes_order(self):
        broker = FakeBroker()
        manager = OrderManager(broker=broker, mode="approval")
        pending = manager.execute(_signal())
        result = manager.approve(pending.id)
        self.assertIsNotNone(result)
        self.assertEqual(1, len(broker.orders))
        self.assertEqual(0, len(manager.pending_orders))

    def test_reject_removes_order(self):
        broker = FakeBroker()
        manager = OrderManager(broker=broker, mode="approval")
        pending = manager.execute(_signal())
        manager.reject(pending.id, reason="Too risky")
        self.assertEqual(0, len(broker.orders))
        self.assertEqual(0, len(manager.pending_orders))

    def test_approval_publishes_events(self):
        bus = EventBus()
        approval_events = []
        bus.subscribe(ApprovalRequested, lambda e: approval_events.append(("requested", e)))
        bus.subscribe(ApprovalReceived, lambda e: approval_events.append(("received", e)))

        broker = FakeBroker()
        manager = OrderManager(broker=broker, event_bus=bus, mode="approval")
        pending = manager.execute(_signal())
        manager.approve(pending.id)

        self.assertEqual(2, len(approval_events))
        self.assertEqual("requested", approval_events[0][0])
        self.assertEqual("received", approval_events[1][0])
        self.assertTrue(approval_events[1][1].approved)

    def test_reject_publishes_event(self):
        bus = EventBus()
        events = []
        bus.subscribe(ApprovalReceived, lambda e: events.append(e))

        broker = FakeBroker()
        manager = OrderManager(broker=broker, event_bus=bus, mode="approval")
        pending = manager.execute(_signal())
        manager.reject(pending.id, reason="nope")

        self.assertEqual(1, len(events))
        self.assertFalse(events[0].approved)

    def test_on_approval_needed_callback(self):
        notifications = []
        broker = FakeBroker()
        manager = OrderManager(
            broker=broker, mode="approval",
            on_approval_needed=lambda p: notifications.append(p.id),
        )
        pending = manager.execute(_signal())
        self.assertEqual(1, len(notifications))
        self.assertEqual(pending.id, notifications[0])

    def test_expire_stale_orders(self):
        broker = FakeBroker()
        manager = OrderManager(broker=broker, mode="approval", timeout_seconds=0)
        manager.execute(_signal())  # immediately stale
        expired = manager.expire_stale()
        self.assertEqual(1, expired)
        self.assertEqual(0, len(manager.pending_orders))

    def test_stats(self):
        broker = FakeBroker()
        manager = OrderManager(broker=broker, mode="approval")
        manager.execute(_signal())
        manager.execute(_signal(symbol="MSFT"))
        stats = manager.stats
        self.assertEqual(2, stats["pending"])
        self.assertEqual(2, stats["total_submitted"])


# ---------------------------------------------------------------------------
# Position Sizer
# ---------------------------------------------------------------------------

class FixedPercentSizerTests(unittest.TestCase):
    def test_10_percent(self):
        sizer = FixedPercentSizer(percent=10.0)
        qty = sizer.size(equity=100_000, price=150.0)
        self.assertAlmostEqual(66.67, qty, places=1)

    def test_zero_price(self):
        sizer = FixedPercentSizer(percent=10.0)
        self.assertEqual(0.0, sizer.size(equity=100_000, price=0))

    def test_invalid_percent(self):
        with self.assertRaises(ValueError):
            FixedPercentSizer(percent=0)


class FixedAmountSizerTests(unittest.TestCase):
    def test_fixed_10k(self):
        sizer = FixedAmountSizer(amount=10_000)
        qty = sizer.size(equity=100_000, price=200.0)
        self.assertAlmostEqual(50.0, qty)

    def test_invalid_amount(self):
        with self.assertRaises(ValueError):
            FixedAmountSizer(amount=-100)


class RiskPerTradeSizerTests(unittest.TestCase):
    def test_2_percent_risk_5_percent_stop(self):
        sizer = RiskPerTradeSizer(risk_percent=2.0, stop_loss_percent=5.0)
        qty = sizer.size(equity=100_000, price=100.0)
        # Risk $2000, stop-loss $5 per share -> 400 shares
        self.assertAlmostEqual(400.0, qty)

    def test_invalid_params(self):
        with self.assertRaises(ValueError):
            RiskPerTradeSizer(risk_percent=0, stop_loss_percent=5)


class KellyCriterionSizerTests(unittest.TestCase):
    def test_positive_kelly(self):
        sizer = KellyCriterionSizer(win_rate=0.6, avg_win=5.0, avg_loss=3.0, fraction=0.5)
        qty = sizer.size(equity=100_000, price=100.0)
        self.assertGreater(qty, 0)

    def test_negative_edge_returns_zero(self):
        sizer = KellyCriterionSizer(win_rate=0.3, avg_win=2.0, avg_loss=5.0, fraction=1.0)
        qty = sizer.size(equity=100_000, price=100.0)
        self.assertEqual(0.0, qty)

    def test_capped_at_max_percent(self):
        sizer = KellyCriterionSizer(win_rate=0.9, avg_win=10.0, avg_loss=1.0, fraction=1.0, max_percent=25.0)
        qty = sizer.size(equity=100_000, price=100.0)
        max_qty = 100_000 * 0.25 / 100.0  # 250
        self.assertLessEqual(qty, max_qty + 0.01)


if __name__ == "__main__":
    unittest.main()
