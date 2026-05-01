"""Relative Strength Index (RSI) strategy.

Generates BUY when RSI crosses into the oversold zone,
SELL when it crosses into the overbought zone.
"""
from __future__ import annotations

from typing import List

from ..models import BUY, HOLD, SELL, PriceBar, Signal
from ..infra.plugin import register_strategy
from .indicators import compute_rsi

from ..strategy import Strategy


@register_strategy("rsi")
class RSIStrategy(Strategy):
    name = "rsi"

    def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70):
        if period <= 0:
            raise ValueError("RSI period must be a positive integer.")
        if oversold >= overbought:
            raise ValueError("oversold threshold must be less than overbought threshold.")

        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def evaluate(self, symbol: str, bars: List[PriceBar]) -> Signal:
        # Need at least period + 2 bars (period changes + 1 for previous RSI)
        if len(bars) < self.period + 2:
            latest_bar = bars[-1]
            return Signal(
                symbol=symbol,
                action=HOLD,
                price=latest_bar.close,
                timestamp=latest_bar.timestamp,
                reason="Not enough history to compute RSI.",
                strategy_name=self.name,
                details={"bars_available": len(bars), "bars_needed": self.period + 2},
            )

        closes = [bar.close for bar in bars]
        rsi = compute_rsi(closes, self.period)
        previous_rsi = compute_rsi(closes[:-1], self.period)
        latest_bar = bars[-1]

        details = {
            "rsi": round(rsi, 4),
            "previous_rsi": round(previous_rsi, 4),
            "period": self.period,
            "oversold": self.oversold,
            "overbought": self.overbought,
        }

        # BUY: RSI crossed into oversold zone
        if rsi < self.oversold and previous_rsi >= self.oversold:
            return Signal(
                symbol=symbol,
                action=BUY,
                price=latest_bar.close,
                timestamp=latest_bar.timestamp,
                reason=f"RSI crossed below oversold threshold ({self.oversold}).",
                strategy_name=self.name,
                details=details,
            )

        # SELL: RSI crossed into overbought zone
        if rsi > self.overbought and previous_rsi <= self.overbought:
            return Signal(
                symbol=symbol,
                action=SELL,
                price=latest_bar.close,
                timestamp=latest_bar.timestamp,
                reason=f"RSI crossed above overbought threshold ({self.overbought}).",
                strategy_name=self.name,
                details=details,
            )

        return Signal(
            symbol=symbol,
            action=HOLD,
            price=latest_bar.close,
            timestamp=latest_bar.timestamp,
            reason=f"RSI at {rsi:.1f}, within normal range.",
            strategy_name=self.name,
            details=details,
        )
