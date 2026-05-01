"""Order manager — signal → approval gate → execution.

Manages the lifecycle of orders from signal to execution. Supports:
- Auto-execute mode: signals go straight to the broker
- Approval mode (HITL): signals are queued for human approval
- Timeout handling: auto-cancel or auto-execute after N seconds

The order manager subscribes to the event bus and publishes events
for each state transition.

Usage:
    from trading_framework.execution.order_manager import OrderManager

    # Auto-execute mode
    manager = OrderManager(broker=paper_portfolio, mode="auto")
    manager.execute(signal)

    # Approval mode (HITL)
    manager = OrderManager(broker=paper_portfolio, mode="approval")
    pending_id = manager.submit_for_approval(signal)
    manager.approve(pending_id)   # or manager.reject(pending_id)
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from ..models import Signal
from ..core.events import ApprovalRequested, ApprovalReceived, OrderFilled
from ..infra.event_bus import EventBus

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    EXPIRED = "expired"


@dataclass
class PendingOrder:
    """An order waiting for human approval."""
    id: str
    signal: Signal
    status: OrderStatus
    created_at: datetime
    timeout_seconds: int = 300
    result: Any = None
    reason: str = ""


class OrderManager:
    """Manages order lifecycle with optional human approval gate.

    Args:
        broker: The broker to execute orders through (paper or live).
        event_bus: Event bus for publishing order events.
        mode: "auto" (execute immediately) or "approval" (require human OK).
        timeout_seconds: How long to wait for approval before expiring.
        on_approval_needed: Callback when a signal needs human approval.
            Receives the PendingOrder. Use this to send Telegram prompts, etc.
    """

    def __init__(
        self,
        broker=None,
        event_bus: EventBus | None = None,
        mode: str = "auto",
        timeout_seconds: int = 300,
        on_approval_needed: Callable[[PendingOrder], None] | None = None,
    ):
        self.broker = broker
        self.event_bus = event_bus or EventBus()
        self.mode = mode
        self.timeout_seconds = timeout_seconds
        self.on_approval_needed = on_approval_needed

        self._pending: Dict[str, PendingOrder] = {}
        self._order_counter = 0
        self._executed: List[PendingOrder] = []

    def execute(self, signal: Signal) -> Any:
        """Process a signal through the order manager.

        In auto mode: executes immediately.
        In approval mode: queues for approval.

        Returns:
            Order result (auto mode) or PendingOrder (approval mode).
        """
        if self.mode == "approval":
            return self.submit_for_approval(signal)
        return self._execute_now(signal)

    def submit_for_approval(self, signal: Signal) -> PendingOrder:
        """Queue a signal for human approval.

        Publishes an ApprovalRequested event and calls on_approval_needed.

        Returns:
            The PendingOrder (with status PENDING_APPROVAL).
        """
        self._order_counter += 1
        order_id = f"ORD-{self._order_counter:04d}"

        pending = PendingOrder(
            id=order_id,
            signal=signal,
            status=OrderStatus.PENDING_APPROVAL,
            created_at=datetime.now(timezone.utc),
            timeout_seconds=self.timeout_seconds,
        )
        self._pending[order_id] = pending

        logger.info("Order %s queued for approval: %s %s @ $%.2f",
                     order_id, signal.action, signal.symbol, signal.price)

        self.event_bus.publish(ApprovalRequested(
            signal=signal, timeout_seconds=self.timeout_seconds,
        ))

        if self.on_approval_needed:
            self.on_approval_needed(pending)

        return pending

    def approve(self, order_id: str, reason: str = "") -> Any:
        """Approve a pending order and execute it.

        Returns:
            The broker execution result, or None if order not found/expired.
        """
        pending = self._pending.get(order_id)
        if not pending or pending.status != OrderStatus.PENDING_APPROVAL:
            logger.warning("Cannot approve order %s: not found or not pending.", order_id)
            return None

        pending.status = OrderStatus.APPROVED
        pending.reason = reason

        self.event_bus.publish(ApprovalReceived(
            signal=pending.signal, approved=True, reason=reason,
        ))

        result = self._execute_now(pending.signal)
        pending.status = OrderStatus.EXECUTED
        pending.result = result
        self._executed.append(pending)
        del self._pending[order_id]

        logger.info("Order %s approved and executed.", order_id)
        return result

    def reject(self, order_id: str, reason: str = "") -> None:
        """Reject a pending order."""
        pending = self._pending.get(order_id)
        if not pending or pending.status != OrderStatus.PENDING_APPROVAL:
            logger.warning("Cannot reject order %s: not found or not pending.", order_id)
            return

        pending.status = OrderStatus.REJECTED
        pending.reason = reason

        self.event_bus.publish(ApprovalReceived(
            signal=pending.signal, approved=False, reason=reason,
        ))

        del self._pending[order_id]
        logger.info("Order %s rejected: %s", order_id, reason)

    def expire_stale(self) -> int:
        """Expire pending orders that have timed out.

        Returns:
            Number of orders expired.
        """
        now = datetime.now(timezone.utc)
        expired = []
        for order_id, pending in list(self._pending.items()):
            age = (now - pending.created_at).total_seconds()
            if age > pending.timeout_seconds:
                pending.status = OrderStatus.EXPIRED
                expired.append(order_id)
                del self._pending[order_id]
                logger.info("Order %s expired after %ds.", order_id, int(age))
        return len(expired)

    def _execute_now(self, signal: Signal) -> Any:
        """Execute a signal immediately through the broker."""
        if not self.broker:
            logger.warning("No broker configured. Signal not executed.")
            return None

        result = self.broker.execute(signal)

        if result and hasattr(result, "pnl"):
            self.event_bus.publish(OrderFilled(
                symbol=signal.symbol,
                action=signal.action,
                price=signal.price,
                quantity=getattr(result, "quantity", 0),
                pnl=getattr(result, "pnl", None),
                timestamp=signal.timestamp,
            ))

        return result

    @property
    def pending_orders(self) -> List[PendingOrder]:
        """Return all pending orders awaiting approval."""
        return list(self._pending.values())

    @property
    def stats(self) -> Dict[str, int]:
        return {
            "pending": len(self._pending),
            "executed": len(self._executed),
            "total_submitted": self._order_counter,
        }
