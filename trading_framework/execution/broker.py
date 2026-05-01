"""Broker ABC — unified interface for paper and live trading.

All broker implementations (paper, Alpaca, IBKR) implement this interface.
The engine and order manager interact with brokers only through these methods.

Usage:
    from trading_framework.execution.broker import Broker

    class MyBroker(Broker):
        def submit_order(self, signal, quantity): ...
        def get_positions(self): ...
        def get_cash(self): ...
        def get_equity(self): ...
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..models import Signal


class Broker(ABC):
    """Abstract broker interface for order execution and account management."""

    @abstractmethod
    def submit_order(self, signal: Signal, quantity: float | None = None) -> Any:
        """Submit an order based on a signal.

        Args:
            signal: The trading signal (BUY/SELL with symbol, price).
            quantity: Override position size. None = use broker's default sizing.

        Returns:
            An order record or None if rejected.
        """
        raise NotImplementedError

    @abstractmethod
    def get_positions(self) -> Dict[str, Any]:
        """Return all open positions as {symbol: position_info}."""
        raise NotImplementedError

    @abstractmethod
    def get_cash(self) -> float:
        """Return available cash balance."""
        raise NotImplementedError

    @abstractmethod
    def get_equity(self) -> float:
        """Return total account equity (cash + positions value)."""
        raise NotImplementedError

    @abstractmethod
    def get_orders(self, limit: int = 20) -> List[Any]:
        """Return recent order history."""
        raise NotImplementedError

    @abstractmethod
    def get_realized_pnl(self) -> float:
        """Return total realized P&L."""
        raise NotImplementedError
