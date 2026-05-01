"""MACD (Moving Average Convergence/Divergence) strategy.

Generates BUY when the MACD line crosses above the signal line,
SELL when it crosses below.
"""
from __future__ import annotations

from typing import List

from ..models import BUY, HOLD, SELL, PriceBar, Signal
from ..infra.plugin import register_strategy
from .indicators import compute_ema

from ..strategy import Strategy


@register_strategy("macd")
class MACDStrategy(Strategy):
    name = "macd"

    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ):
        if fast_period <= 0 or slow_period <= 0 or signal_period <= 0:
            raise ValueError("All MACD periods must be positive integers.")
        if fast_period >= slow_period:
            raise ValueError("fast_period must be less than slow_period.")

        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period

    def evaluate(self, symbol: str, bars: List[PriceBar]) -> Signal:
        min_bars = self.slow_period + self.signal_period
        latest_bar = bars[-1]

        if len(bars) < min_bars:
            return Signal(
                symbol=symbol,
                action=HOLD,
                price=latest_bar.close,
                timestamp=latest_bar.timestamp,
                reason="Not enough history to compute MACD.",
                strategy_name=self.name,
                details={"bars_available": len(bars), "bars_needed": min_bars},
            )

        closes = [bar.close for bar in bars]

        fast_ema_values = compute_ema(closes, self.fast_period)
        slow_ema_values = compute_ema(closes, self.slow_period)

        # MACD line: fast EMA - slow EMA (aligned to slow EMA start)
        offset = self.slow_period - self.fast_period
        macd_line = [
            fast_ema_values[offset + i] - slow_ema_values[i]
            for i in range(len(slow_ema_values))
        ]

        signal_line_values = compute_ema(macd_line, self.signal_period)

        current_macd = macd_line[-1]
        current_signal = signal_line_values[-1]
        previous_macd = macd_line[-2]
        previous_signal = signal_line_values[-2]
        histogram = current_macd - current_signal

        details = {
            "macd": round(current_macd, 6),
            "signal_line": round(current_signal, 6),
            "histogram": round(histogram, 6),
            "previous_macd": round(previous_macd, 6),
            "previous_signal": round(previous_signal, 6),
            "fast_period": self.fast_period,
            "slow_period": self.slow_period,
            "signal_period": self.signal_period,
        }

        if previous_macd <= previous_signal and current_macd > current_signal:
            return Signal(
                symbol=symbol,
                action=BUY,
                price=latest_bar.close,
                timestamp=latest_bar.timestamp,
                reason="MACD line crossed above signal line.",
                strategy_name=self.name,
                details=details,
            )

        if previous_macd >= previous_signal and current_macd < current_signal:
            return Signal(
                symbol=symbol,
                action=SELL,
                price=latest_bar.close,
                timestamp=latest_bar.timestamp,
                reason="MACD line crossed below signal line.",
                strategy_name=self.name,
                details=details,
            )

        return Signal(
            symbol=symbol,
            action=HOLD,
            price=latest_bar.close,
            timestamp=latest_bar.timestamp,
            reason="No MACD crossover on the latest bar.",
            strategy_name=self.name,
            details=details,
        )
