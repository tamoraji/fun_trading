"""Moving Average Crossover (SMA) strategy.

Generates BUY when the fast SMA crosses above the slow SMA,
SELL when it crosses below.
"""
from __future__ import annotations

from typing import List

from ..models import BUY, HOLD, SELL, PriceBar, Signal
from ..infra.plugin import register_strategy
from .indicators import average

# Import the ABC from the flat module for now (will move to core later)
from ..strategy import Strategy


@register_strategy("moving_average_crossover")
class MovingAverageCrossoverStrategy(Strategy):
    name = "moving_average_crossover"

    def __init__(self, short_window: int = 5, long_window: int = 20):
        if short_window <= 0 or long_window <= 0:
            raise ValueError("Moving average windows must be positive integers.")
        if short_window >= long_window:
            raise ValueError("short_window must be smaller than long_window.")

        self.short_window = short_window
        self.long_window = long_window

    def evaluate(self, symbol: str, bars: List[PriceBar]) -> Signal:
        if len(bars) < self.long_window + 1:
            latest_bar = bars[-1]
            return Signal(
                symbol=symbol,
                action=HOLD,
                price=latest_bar.close,
                timestamp=latest_bar.timestamp,
                reason="Not enough history to evaluate the moving averages.",
                strategy_name=self.name,
                details={"bars_available": len(bars)},
            )

        closes = [bar.close for bar in bars]
        latest_bar = bars[-1]
        current_short = average(closes[-self.short_window :])
        current_long = average(closes[-self.long_window :])
        previous_short = average(closes[-self.short_window - 1 : -1])
        previous_long = average(closes[-self.long_window - 1 : -1])

        details = {
            "short_sma": round(current_short, 6),
            "long_sma": round(current_long, 6),
            "previous_short_sma": round(previous_short, 6),
            "previous_long_sma": round(previous_long, 6),
            "short_window": self.short_window,
            "long_window": self.long_window,
        }

        if previous_short <= previous_long and current_short > current_long:
            return Signal(
                symbol=symbol,
                action=BUY,
                price=latest_bar.close,
                timestamp=latest_bar.timestamp,
                reason="Short moving average crossed above long moving average.",
                strategy_name=self.name,
                details=details,
            )

        if previous_short >= previous_long and current_short < current_long:
            return Signal(
                symbol=symbol,
                action=SELL,
                price=latest_bar.close,
                timestamp=latest_bar.timestamp,
                reason="Short moving average crossed below long moving average.",
                strategy_name=self.name,
                details=details,
            )

        return Signal(
            symbol=symbol,
            action=HOLD,
            price=latest_bar.close,
            timestamp=latest_bar.timestamp,
            reason="No crossover on the latest bar.",
            strategy_name=self.name,
            details=details,
        )
