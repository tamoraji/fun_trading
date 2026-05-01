"""Notification router — dispatches signals to channels by confidence level.

Routes aggregated signals to different notification channels based on
their confidence level:
- HIGH confidence → immediate notification (Telegram, console, etc.)
- MEDIUM confidence → logged + optional notification
- LOW confidence → logged only (daily digest)

Usage:
    from trading_framework.signals.router import NotificationRouter

    router = NotificationRouter()
    router.add_channel("telegram", my_telegram_notifier, min_confidence=Confidence.HIGH)
    router.add_channel("console", my_console_notifier, min_confidence=Confidence.LOW)
    router.route(aggregated_signal)
"""
from __future__ import annotations

import logging
from typing import Callable, Dict, List, NamedTuple

from ..core.types import Confidence
from .aggregator import AggregatedSignal

logger = logging.getLogger(__name__)

# Confidence ordering for comparison
_CONFIDENCE_ORDER = {
    Confidence.NONE: 0,
    Confidence.LOW: 1,
    Confidence.MEDIUM: 2,
    Confidence.HIGH: 3,
}


class Channel(NamedTuple):
    name: str
    handler: Callable[[AggregatedSignal], None]
    min_confidence: Confidence


class NotificationRouter:
    """Routes aggregated signals to notification channels by confidence threshold.

    Each channel has a minimum confidence level. A signal is sent to a channel
    only if its confidence meets or exceeds the channel's threshold.
    """

    def __init__(self) -> None:
        self._channels: List[Channel] = []
        self._routed_count: int = 0

    def add_channel(
        self,
        name: str,
        handler: Callable[[AggregatedSignal], None],
        min_confidence: Confidence = Confidence.LOW,
    ) -> None:
        """Register a notification channel.

        Args:
            name: Channel identifier (for logging).
            handler: Callable that receives an AggregatedSignal.
            min_confidence: Minimum confidence level to route to this channel.
        """
        self._channels.append(Channel(name=name, handler=handler, min_confidence=min_confidence))
        logger.debug("Added channel '%s' with min_confidence=%s", name, min_confidence.value)

    def route(self, agg_signal: AggregatedSignal) -> List[str]:
        """Route a signal to all qualifying channels.

        Args:
            agg_signal: The aggregated, scored signal.

        Returns:
            List of channel names the signal was routed to.
        """
        signal_level = _CONFIDENCE_ORDER.get(agg_signal.confidence, 0)
        routed_to = []

        for channel in self._channels:
            channel_level = _CONFIDENCE_ORDER.get(channel.min_confidence, 0)
            if signal_level >= channel_level:
                try:
                    channel.handler(agg_signal)
                    routed_to.append(channel.name)
                except Exception as exc:
                    logger.error("Channel '%s' failed: %s", channel.name, exc)

        self._routed_count += 1
        if routed_to:
            logger.info(
                "Routed %s %s (%s) to: %s",
                agg_signal.signal.action, agg_signal.signal.symbol,
                agg_signal.confidence.value, ", ".join(routed_to),
            )
        return routed_to

    @property
    def stats(self) -> Dict[str, int]:
        return {
            "channels": len(self._channels),
            "total_routed": self._routed_count,
        }
