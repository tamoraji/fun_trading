"""Channel Breakout strategy.

Generates BUY when price breaks above the recent high with volume confirmation,
SELL when it breaks below the recent low.
"""
from __future__ import annotations

from typing import List

from ..models import BUY, HOLD, SELL, PriceBar, Signal
from ..infra.plugin import register_strategy
from .indicators import average

from ..strategy import Strategy


@register_strategy("breakout")
class BreakoutStrategy(Strategy):
    name = "breakout"

    def __init__(self, lookback: int = 20, volume_factor: float = 1.5):
        if lookback <= 0:
            raise ValueError("lookback must be a positive integer.")
        self.lookback = lookback
        self.volume_factor = volume_factor

    def evaluate(self, symbol: str, bars: List[PriceBar]) -> Signal:
        min_bars = self.lookback + 1
        latest_bar = bars[-1]

        if len(bars) < min_bars:
            return Signal(
                symbol=symbol,
                action=HOLD,
                price=latest_bar.close,
                timestamp=latest_bar.timestamp,
                reason="Not enough history to evaluate breakout.",
                strategy_name=self.name,
                details={"bars_available": len(bars), "bars_needed": min_bars},
            )

        window = bars[-min_bars:-1]  # previous `lookback` bars
        channel_high = max(b.high for b in window)
        channel_low = min(b.low for b in window)
        current_close = latest_bar.close
        current_volume = latest_bar.volume
        average_volume = average([b.volume for b in window])

        volume_confirmed = (
            self.volume_factor == 0
            or current_volume >= self.volume_factor * average_volume
        )

        details = {
            "channel_high": channel_high,
            "channel_low": channel_low,
            "current_close": current_close,
            "current_volume": current_volume,
            "average_volume": round(average_volume, 6),
            "volume_confirmed": volume_confirmed,
            "lookback": self.lookback,
        }

        if current_close > channel_high and volume_confirmed:
            return Signal(
                symbol=symbol,
                action=BUY,
                price=latest_bar.close,
                timestamp=latest_bar.timestamp,
                reason="Price broke above channel high with volume confirmation.",
                strategy_name=self.name,
                details=details,
            )

        if current_close < channel_low and volume_confirmed:
            return Signal(
                symbol=symbol,
                action=SELL,
                price=latest_bar.close,
                timestamp=latest_bar.timestamp,
                reason="Price broke below channel low with volume confirmation.",
                strategy_name=self.name,
                details=details,
            )

        return Signal(
            symbol=symbol,
            action=HOLD,
            price=latest_bar.close,
            timestamp=latest_bar.timestamp,
            reason="No confirmed breakout.",
            strategy_name=self.name,
            details=details,
        )
