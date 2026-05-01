"""Position sizing models — compute trade size based on risk parameters.

Determines how many shares/units to trade per signal.

Usage:
    from trading_framework.execution.position_sizer import (
        FixedPercentSizer, FixedAmountSizer, KellyCriterionSizer,
    )

    sizer = FixedPercentSizer(percent=10.0)
    quantity = sizer.size(equity=100000, price=150.0)  # -> 66.67 shares
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod


class PositionSizer(ABC):
    """Abstract position sizing interface."""

    @abstractmethod
    def size(self, equity: float, price: float, **kwargs) -> float:
        """Calculate the number of units to trade.

        Args:
            equity: Total portfolio equity.
            price: Current price per unit.
            **kwargs: Additional context (win_rate, avg_win, avg_loss, etc.)

        Returns:
            Number of units (shares, contracts, coins) to trade.
        """
        raise NotImplementedError


class FixedPercentSizer(PositionSizer):
    """Size position as a percentage of total equity.

    Args:
        percent: Percentage of equity per trade (e.g., 10.0 = 10%).
    """

    def __init__(self, percent: float = 10.0):
        if percent <= 0 or percent > 100:
            raise ValueError("percent must be between 0 and 100.")
        self.percent = percent

    def size(self, equity: float, price: float, **kwargs) -> float:
        if price <= 0:
            return 0.0
        trade_value = equity * (self.percent / 100.0)
        return trade_value / price


class FixedAmountSizer(PositionSizer):
    """Size position as a fixed dollar amount per trade.

    Args:
        amount: Fixed dollar amount per trade.
    """

    def __init__(self, amount: float = 10_000.0):
        if amount <= 0:
            raise ValueError("amount must be positive.")
        self.amount = amount

    def size(self, equity: float, price: float, **kwargs) -> float:
        if price <= 0:
            return 0.0
        return self.amount / price


class RiskPerTradeSizer(PositionSizer):
    """Size position based on risk per trade (stop-loss distance).

    Sizes so that if the stop-loss is hit, you lose at most `risk_percent`
    of equity.

    Args:
        risk_percent: Max % of equity to risk per trade (e.g., 2.0 = 2%).
        stop_loss_percent: Stop-loss distance as % of entry price.
    """

    def __init__(self, risk_percent: float = 2.0, stop_loss_percent: float = 5.0):
        if risk_percent <= 0 or stop_loss_percent <= 0:
            raise ValueError("risk_percent and stop_loss_percent must be positive.")
        self.risk_percent = risk_percent
        self.stop_loss_percent = stop_loss_percent

    def size(self, equity: float, price: float, **kwargs) -> float:
        if price <= 0:
            return 0.0
        risk_amount = equity * (self.risk_percent / 100.0)
        loss_per_unit = price * (self.stop_loss_percent / 100.0)
        if loss_per_unit <= 0:
            return 0.0
        return risk_amount / loss_per_unit


class KellyCriterionSizer(PositionSizer):
    """Size position using the Kelly Criterion.

    Kelly fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win

    Typically used with a fractional Kelly (e.g., half-Kelly) for safety.

    Args:
        win_rate: Historical win rate (0.0 to 1.0).
        avg_win: Average winning trade % (e.g., 5.0 for 5%).
        avg_loss: Average losing trade % (e.g., 3.0 for 3%).
        fraction: Kelly fraction to use (0.5 = half-Kelly, safer). Default 0.5.
        max_percent: Maximum position size as % of equity. Default 25%.
    """

    def __init__(
        self,
        win_rate: float = 0.5,
        avg_win: float = 5.0,
        avg_loss: float = 3.0,
        fraction: float = 0.5,
        max_percent: float = 25.0,
    ):
        self.win_rate = win_rate
        self.avg_win = avg_win
        self.avg_loss = avg_loss
        self.fraction = fraction
        self.max_percent = max_percent

    def size(self, equity: float, price: float, **kwargs) -> float:
        if price <= 0 or self.avg_win <= 0:
            return 0.0

        # Use kwargs to override defaults if available
        win_rate = kwargs.get("win_rate", self.win_rate)
        avg_win = kwargs.get("avg_win", self.avg_win)
        avg_loss = kwargs.get("avg_loss", self.avg_loss)

        # Kelly fraction = (p * b - q) / b where p=win_rate, q=1-p, b=avg_win/avg_loss
        if avg_loss <= 0:
            kelly = 0.0
        else:
            b = avg_win / avg_loss
            kelly = (win_rate * b - (1 - win_rate)) / b

        # Apply fractional Kelly and cap
        kelly = max(kelly * self.fraction, 0.0)
        kelly = min(kelly, self.max_percent / 100.0)

        trade_value = equity * kelly
        return trade_value / price
