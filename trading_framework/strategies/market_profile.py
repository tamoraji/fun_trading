"""Market Profile Value Area strategy.

Generates BUY when price returns to the value area from below (mean reversion),
SELL when it returns from above.
"""
from __future__ import annotations

from typing import List

from ..models import BUY, HOLD, SELL, PriceBar, Signal
from ..infra.plugin import register_strategy
from .indicators import compute_value_area

from ..strategy import Strategy


@register_strategy("market_profile")
class MarketProfileStrategy(Strategy):
    name = "market_profile"

    def __init__(self, lookback: int = 20, value_area_pct: float = 70.0):
        if lookback <= 0:
            raise ValueError("Lookback must be a positive integer.")
        if not (1 <= value_area_pct <= 100):
            raise ValueError("value_area_pct must be between 1 and 100.")
        self.lookback = lookback
        self.value_area_pct = value_area_pct

    def evaluate(self, symbol: str, bars: List[PriceBar]) -> Signal:
        latest_bar = bars[-1]

        if len(bars) < self.lookback + 1:
            return Signal(
                symbol=symbol,
                action=HOLD,
                price=latest_bar.close,
                timestamp=latest_bar.timestamp,
                reason="Not enough history to compute market profile.",
                strategy_name=self.name,
                details={"bars_available": len(bars), "bars_needed": self.lookback + 1},
            )

        lookback_bars = bars[-self.lookback - 1:-1]
        current_bar = bars[-1]
        previous_bar = bars[-2]

        poc, vwap, vah, val = compute_value_area(lookback_bars, self.value_area_pct)

        prev_close = previous_bar.close
        curr_close = current_bar.close

        if curr_close > vah:
            price_location = "above_value"
        elif curr_close < val:
            price_location = "below_value"
        else:
            price_location = "in_value"

        details = {
            "poc": poc,
            "vwap": vwap,
            "vah": vah,
            "val": val,
            "current_close": curr_close,
            "previous_close": prev_close,
            "price_location": price_location,
            "lookback": self.lookback,
            "value_area_pct": self.value_area_pct,
        }

        # BUY: was below VAL, crossed back above VAL
        if prev_close < val and curr_close >= val:
            return Signal(
                symbol=symbol,
                action=BUY,
                price=latest_bar.close,
                timestamp=latest_bar.timestamp,
                reason="Price returned to value area from below (mean reversion buy).",
                strategy_name=self.name,
                details=details,
            )

        # SELL: was above VAH, crossed back below VAH
        if prev_close > vah and curr_close <= vah:
            return Signal(
                symbol=symbol,
                action=SELL,
                price=latest_bar.close,
                timestamp=latest_bar.timestamp,
                reason="Price returned to value area from above (mean reversion sell).",
                strategy_name=self.name,
                details=details,
            )

        return Signal(
            symbol=symbol,
            action=HOLD,
            price=latest_bar.close,
            timestamp=latest_bar.timestamp,
            reason="No value area crossover on the latest bar.",
            strategy_name=self.name,
            details=details,
        )
