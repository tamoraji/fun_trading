"""Goslin Three-Line Momentum strategy.

Uses direction, timing, and confirming lines to generate signals
when all three indicators align for a trade.
"""
from __future__ import annotations

from typing import List

from ..models import BUY, HOLD, SELL, PriceBar, Signal
from ..infra.plugin import register_strategy
from .indicators import average

from ..strategy import Strategy


@register_strategy("goslin_momentum")
class GoslinMomentumStrategy(Strategy):
    name = "goslin_momentum"

    def __init__(
        self,
        direction_period: int = 49,
        timing_short: int = 3,
        timing_long: int = 10,
        confirming_period: int = 15,
    ):
        if direction_period <= 0 or timing_short <= 0 or timing_long <= 0 or confirming_period <= 0:
            raise ValueError("All Goslin periods must be positive integers.")
        if timing_short >= timing_long:
            raise ValueError("timing_short must be less than timing_long.")

        self.direction_period = direction_period
        self.timing_short = timing_short
        self.timing_long = timing_long
        self.confirming_period = confirming_period

    def evaluate(self, symbol: str, bars: List[PriceBar]) -> Signal:
        min_bars = self.direction_period + self.confirming_period + 1
        latest_bar = bars[-1]

        if len(bars) < min_bars:
            return Signal(
                symbol=symbol,
                action=HOLD,
                price=latest_bar.close,
                timestamp=latest_bar.timestamp,
                reason="Not enough history to compute Goslin momentum.",
                strategy_name=self.name,
                details={"bars_available": len(bars), "bars_needed": min_bars},
            )

        closes = [bar.close for bar in bars]

        # Direction Line: SMA of last direction_period closes
        direction_line = average(closes[-self.direction_period:])
        price_above = latest_bar.close > direction_line

        # Timing Line: compute for recent bars to build confirming line
        # We need confirming_period + 1 timing values
        timing_values: List[float] = []
        for i in range(self.confirming_period + 1):
            offset = len(closes) - self.confirming_period - 1 + i
            if offset >= self.timing_long:
                short_avg = average(closes[offset - self.timing_short + 1:offset + 1])
                long_avg = average(closes[offset - self.timing_long + 1:offset + 1])
                timing_values.append(short_avg - long_avg)

        timing_line = timing_values[-1]
        previous_timing = timing_values[-2]

        # Confirming Line: SMA of last confirming_period timing values
        confirming_line = average(timing_values[-self.confirming_period:])
        previous_confirming = average(timing_values[-self.confirming_period - 1:-1])

        details = {
            "direction_line": round(direction_line, 6),
            "price_vs_direction": "above" if price_above else "below",
            "timing_line": round(timing_line, 6),
            "previous_timing": round(previous_timing, 6),
            "confirming_line": round(confirming_line, 6),
            "previous_confirming": round(previous_confirming, 6),
            "direction_period": self.direction_period,
            "timing_short": self.timing_short,
            "timing_long": self.timing_long,
            "confirming_period": self.confirming_period,
        }

        # BUY: price above direction + timing crossed to positive + confirming supports
        timing_crossed_up = previous_timing <= 0 and timing_line > 0
        confirming_bullish = confirming_line > 0 or confirming_line > previous_confirming

        if price_above and timing_crossed_up and confirming_bullish:
            return Signal(
                symbol=symbol,
                action=BUY,
                price=latest_bar.close,
                timestamp=latest_bar.timestamp,
                reason="Three-point buy: price above direction, timing crossed up, confirming bullish.",
                strategy_name=self.name,
                details=details,
            )

        # SELL: price below direction + timing crossed to negative + confirming supports
        timing_crossed_down = previous_timing >= 0 and timing_line < 0
        confirming_bearish = confirming_line < 0 or confirming_line < previous_confirming

        if not price_above and timing_crossed_down and confirming_bearish:
            return Signal(
                symbol=symbol,
                action=SELL,
                price=latest_bar.close,
                timestamp=latest_bar.timestamp,
                reason="Three-point sell: price below direction, timing crossed down, confirming bearish.",
                strategy_name=self.name,
                details=details,
            )

        return Signal(
            symbol=symbol,
            action=HOLD,
            price=latest_bar.close,
            timestamp=latest_bar.timestamp,
            reason="Goslin conditions not aligned for a trade.",
            strategy_name=self.name,
            details=details,
        )
