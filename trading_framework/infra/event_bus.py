"""In-process synchronous event bus.

A simple pub/sub system for decoupling components. The engine publishes
events (SignalEmitted, CycleCompleted, etc.) and any number of handlers
react without the engine knowing about them.

This is intentionally simple — no async, no queues, no serialization.
For a single-process personal trading tool, this is all you need.

Usage:
    from trading_framework.infra.event_bus import EventBus
    from trading_framework.core.events import SignalEmitted

    bus = EventBus()

    # Subscribe a handler
    def on_signal(event: SignalEmitted):
        print(f"Signal: {event.signal.action} {event.signal.symbol}")

    bus.subscribe(SignalEmitted, on_signal)

    # Publish an event — all subscribers are called synchronously
    bus.publish(SignalEmitted(signal=my_signal, bars=my_bars))

    # Unsubscribe
    bus.unsubscribe(SignalEmitted, on_signal)
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Callable, Dict, List, Type

logger = logging.getLogger(__name__)


class EventBus:
    """Synchronous in-process event bus.

    Thread-safe for publishing from a single thread (the engine loop).
    Handlers are called in subscription order, synchronously.
    If a handler raises, the error is logged and remaining handlers still run.
    """

    def __init__(self) -> None:
        self._handlers: Dict[Type, List[Callable]] = defaultdict(list)
        self._event_count: int = 0

    def subscribe(self, event_type: Type, handler: Callable) -> None:
        """Register a handler for an event type.

        Args:
            event_type: The event class to subscribe to (e.g., SignalEmitted).
            handler: A callable that takes the event as its only argument.
        """
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)
            logger.debug("Subscribed %s to %s", handler.__name__, event_type.__name__)

    def unsubscribe(self, event_type: Type, handler: Callable) -> None:
        """Remove a handler for an event type."""
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)
            logger.debug("Unsubscribed %s from %s", handler.__name__, event_type.__name__)

    def publish(self, event: Any) -> None:
        """Dispatch an event to all registered handlers.

        Handlers are called synchronously in subscription order.
        If a handler raises an exception, it is logged and the next handler runs.

        Args:
            event: An event instance (e.g., SignalEmitted(...)).
        """
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])
        self._event_count += 1

        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:
                logger.error(
                    "Handler %s failed for %s: %s",
                    handler.__name__, event_type.__name__, exc,
                    exc_info=True,
                )

    @property
    def stats(self) -> Dict[str, Any]:
        """Return bus statistics for debugging."""
        return {
            "total_events_published": self._event_count,
            "subscriptions": {
                event_type.__name__: len(handlers)
                for event_type, handlers in self._handlers.items()
            },
        }

    def clear(self) -> None:
        """Remove all subscriptions. Useful for testing."""
        self._handlers.clear()
        self._event_count = 0
