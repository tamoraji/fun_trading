"""Signal aggregator — fuses signals from multiple strategies.

Subscribes to SignalEmitted events from the event bus. After each cycle,
aggregates signals by symbol, scores them with the confidence model,
and publishes AggregatedSignal events.

Usage:
    from trading_framework.signals.aggregator import SignalAggregator

    aggregator = SignalAggregator(event_bus=bus, total_strategies=6)
    # Aggregator auto-subscribes to SignalEmitted and CycleCompleted
    # After each cycle, it scores and routes signals
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List

from ..core.events import SignalEmitted, CycleCompleted
from ..core.types import Confidence
from ..infra.event_bus import EventBus
from ..models import PriceBar, Signal
from .confidence import score_signals

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AggregatedSignal:
    """A signal enriched with confidence scoring from multi-strategy agreement."""
    signal: Signal
    confidence: Confidence
    score: float
    agreeing_strategies: List[str]
    total_strategies: int


class SignalAggregator:
    """Collects signals during a cycle and scores them at cycle end.

    The aggregator subscribes to:
    - SignalEmitted: collects signals as they arrive during a cycle
    - CycleCompleted: triggers scoring and publishes AggregatedSignal events

    Args:
        event_bus: The event bus to subscribe to and publish on.
        total_strategies: Total number of strategies being run (for scoring).
        on_aggregated: Optional callback for each scored signal (for notification routing).
    """

    def __init__(
        self,
        event_bus: EventBus,
        total_strategies: int = 1,
        on_aggregated=None,
    ):
        self.event_bus = event_bus
        self.total_strategies = total_strategies
        self.on_aggregated = on_aggregated

        # Collect signals during current cycle
        self._cycle_signals: List[Signal] = []
        self._cycle_bars: List[PriceBar] = []

        # Subscribe to events
        event_bus.subscribe(SignalEmitted, self._on_signal_emitted)
        event_bus.subscribe(CycleCompleted, self._on_cycle_completed)

        # History of aggregated signals (for UI access)
        self.last_aggregated: List[AggregatedSignal] = []

    def _on_signal_emitted(self, event: SignalEmitted) -> None:
        """Collect signals as they arrive during a cycle."""
        self._cycle_signals.append(event.signal)
        # Keep bars for volume context
        if event.bars and not self._cycle_bars:
            self._cycle_bars = event.bars

    def _on_cycle_completed(self, event: CycleCompleted) -> None:
        """Score collected signals and publish aggregated results."""
        if not self._cycle_signals:
            self._cycle_signals = []
            self._cycle_bars = []
            return

        scored = score_signals(
            signals=self._cycle_signals,
            bars=self._cycle_bars,
            total_strategies=self.total_strategies,
        )

        self.last_aggregated = []
        for item in scored:
            agg = AggregatedSignal(
                signal=item["signal"],
                confidence=item["confidence"],
                score=item["score"],
                agreeing_strategies=item["strategies"],
                total_strategies=item["total_strategies"],
            )
            self.last_aggregated.append(agg)

            logger.info(
                "Aggregated: %s %s — %s confidence (%.2f), %d/%d strategies agree: %s",
                item["signal"].action, item["signal"].symbol,
                item["confidence"].value, item["score"],
                item["agreeing"], item["total_strategies"],
                ", ".join(item["strategies"]),
            )

            if self.on_aggregated:
                self.on_aggregated(agg)

        # Reset for next cycle
        self._cycle_signals = []
        self._cycle_bars = []
