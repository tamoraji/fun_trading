"""Tests for the event bus."""
from __future__ import annotations

import unittest
from dataclasses import dataclass

from trading_framework.infra.event_bus import EventBus


@dataclass(frozen=True)
class FakeEvent:
    value: str


@dataclass(frozen=True)
class OtherEvent:
    number: int


class EventBusTests(unittest.TestCase):
    def setUp(self):
        self.bus = EventBus()

    def test_subscribe_and_publish(self):
        received = []
        self.bus.subscribe(FakeEvent, lambda e: received.append(e.value))
        self.bus.publish(FakeEvent(value="hello"))
        self.assertEqual(["hello"], received)

    def test_multiple_handlers(self):
        results = []
        self.bus.subscribe(FakeEvent, lambda e: results.append("a"))
        self.bus.subscribe(FakeEvent, lambda e: results.append("b"))
        self.bus.publish(FakeEvent(value="x"))
        self.assertEqual(["a", "b"], results)

    def test_different_event_types_independent(self):
        fake_received = []
        other_received = []
        self.bus.subscribe(FakeEvent, lambda e: fake_received.append(e.value))
        self.bus.subscribe(OtherEvent, lambda e: other_received.append(e.number))
        self.bus.publish(FakeEvent(value="hello"))
        self.bus.publish(OtherEvent(number=42))
        self.assertEqual(["hello"], fake_received)
        self.assertEqual([42], other_received)

    def test_no_handlers_is_fine(self):
        # Publishing with no subscribers should not raise
        self.bus.publish(FakeEvent(value="nobody listening"))

    def test_handler_error_does_not_stop_others(self):
        results = []

        def bad_handler(event):
            raise RuntimeError("oops")

        self.bus.subscribe(FakeEvent, bad_handler)
        self.bus.subscribe(FakeEvent, lambda e: results.append("ok"))
        self.bus.publish(FakeEvent(value="test"))
        # Second handler should still run
        self.assertEqual(["ok"], results)

    def test_unsubscribe(self):
        results = []
        handler = lambda e: results.append(e.value)
        self.bus.subscribe(FakeEvent, handler)
        self.bus.publish(FakeEvent(value="before"))
        self.bus.unsubscribe(FakeEvent, handler)
        self.bus.publish(FakeEvent(value="after"))
        self.assertEqual(["before"], results)

    def test_duplicate_subscribe_ignored(self):
        results = []
        handler = lambda e: results.append("x")
        self.bus.subscribe(FakeEvent, handler)
        self.bus.subscribe(FakeEvent, handler)  # duplicate
        self.bus.publish(FakeEvent(value="test"))
        self.assertEqual(["x"], results)  # only once

    def test_stats(self):
        self.bus.subscribe(FakeEvent, lambda e: None)
        self.bus.subscribe(FakeEvent, lambda e: None)
        self.bus.publish(FakeEvent(value="a"))
        self.bus.publish(FakeEvent(value="b"))
        stats = self.bus.stats
        self.assertEqual(2, stats["total_events_published"])
        self.assertEqual(2, stats["subscriptions"]["FakeEvent"])

    def test_clear(self):
        self.bus.subscribe(FakeEvent, lambda e: None)
        self.bus.publish(FakeEvent(value="x"))
        self.bus.clear()
        self.assertEqual(0, self.bus.stats["total_events_published"])
        self.assertEqual({}, self.bus.stats["subscriptions"])


if __name__ == "__main__":
    unittest.main()
