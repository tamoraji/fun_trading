"""Core interfaces (ABCs) for the trading framework.

Every pluggable component implements one of these interfaces. This module
has ZERO implementation — only abstract contracts. Implementations live
in their respective layer packages.

Import guide:
    from trading_framework.core.interfaces import Strategy, DataProvider, Notifier
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from ..models import MarketDataConfig, PriceBar, Signal


class Strategy(ABC):
    """Evaluates price bars and produces a trading signal.

    Implementations: strategies/sma.py, strategies/rsi.py, etc.
    """
    name: str = "base"

    @abstractmethod
    def evaluate(self, symbol: str, bars: List[PriceBar]) -> Signal:
        """Analyze bars and return a BUY, SELL, or HOLD signal."""
        raise NotImplementedError


class DataProvider(ABC):
    """Fetches historical price bars for a symbol.

    Implementations: data/providers/yahoo.py, data/providers/alpaca.py, etc.
    """

    @abstractmethod
    def fetch_bars(self, symbol: str, config: MarketDataConfig) -> List[PriceBar]:
        """Return time-sorted list of PriceBars for the given symbol."""
        raise NotImplementedError


class Notifier(ABC):
    """Delivers a signal to a notification channel.

    Implementations: signals/notifiers/console.py, telegram.py, etc.
    """

    @abstractmethod
    def send(self, signal: Signal) -> None:
        """Send a signal notification."""
        raise NotImplementedError


class SignalStore(ABC):
    """Persists signals for later retrieval.

    Implementations: signals/history.py (JsonLinesHistory)
    """

    @abstractmethod
    def write(self, signal: Signal) -> None:
        """Write a signal to persistent storage."""
        raise NotImplementedError

    @abstractmethod
    def read_all(self) -> List[Dict[str, Any]]:
        """Read all stored signals."""
        raise NotImplementedError


class RiskFilter(ABC):
    """Evaluates whether a signal should be allowed through.

    Implementations: risk_mgmt/filters.py
    """

    @abstractmethod
    def evaluate(self, signal: Signal, bars: List[PriceBar]) -> Signal:
        """Return the signal (possibly modified) or a HOLD signal if blocked."""
        raise NotImplementedError


class Broker(ABC):
    """Executes orders against a trading account (paper or live).

    Implementations: execution/paper.py, execution/alpaca.py (planned)
    """

    @abstractmethod
    def execute(self, signal: Signal) -> Any:
        """Execute a signal. Returns an order record or None."""
        raise NotImplementedError

    @abstractmethod
    def get_positions(self) -> Dict[str, Any]:
        """Return current open positions."""
        raise NotImplementedError

    @abstractmethod
    def get_cash(self) -> float:
        """Return available cash."""
        raise NotImplementedError
