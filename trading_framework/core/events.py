"""Event types for the event bus.

Events are simple frozen dataclasses that carry data between components
without creating direct dependencies. The engine publishes events;
notifiers, history, paper trading, and other handlers subscribe.

Usage:
    from trading_framework.core.events import SignalEmitted, CycleCompleted
    bus.subscribe(SignalEmitted, my_handler)
    bus.publish(SignalEmitted(signal=signal, bars=bars))
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List

from ..models import PriceBar, Signal


@dataclass(frozen=True)
class SignalEmitted:
    """Fired when a strategy produces a non-HOLD signal that passes risk filters."""
    signal: Signal
    bars: List[PriceBar]


@dataclass(frozen=True)
class SignalBlocked:
    """Fired when a signal is blocked by a risk filter."""
    signal: Signal
    reason: str
    filter_name: str


@dataclass(frozen=True)
class CycleStarted:
    """Fired at the beginning of each polling cycle."""
    timestamp: datetime
    symbols: List[str]


@dataclass(frozen=True)
class CycleCompleted:
    """Fired at the end of each polling cycle with summary stats."""
    timestamp: datetime
    signals_emitted: int
    holds: int
    errors: int
    elapsed_seconds: float


@dataclass(frozen=True)
class OrderFilled:
    """Fired when a paper or live order is executed."""
    symbol: str
    action: str
    price: float
    quantity: float
    pnl: float | None = None
    timestamp: datetime | None = None


@dataclass(frozen=True)
class DataError:
    """Fired when a data fetch fails."""
    symbol: str
    error: str


@dataclass(frozen=True)
class ApprovalRequested:
    """Fired when a signal requires human approval before execution (HITL)."""
    signal: Signal
    timeout_seconds: int = 300


@dataclass(frozen=True)
class ApprovalReceived:
    """Fired when a human approves or rejects a pending signal."""
    signal: Signal
    approved: bool
    reason: str = ""
