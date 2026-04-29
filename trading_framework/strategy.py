from __future__ import annotations

from abc import ABC, abstractmethod
from statistics import fmean
from typing import Iterable, List

from .models import BUY, HOLD, SELL, PriceBar, Signal, StrategySettings


class Strategy(ABC):
    name = "base"

    @abstractmethod
    def evaluate(self, symbol: str, bars: List[PriceBar]) -> Signal:
        raise NotImplementedError


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
        current_short = _average(closes[-self.short_window :])
        current_long = _average(closes[-self.long_window :])
        previous_short = _average(closes[-self.short_window - 1 : -1])
        previous_long = _average(closes[-self.long_window - 1 : -1])

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


def create_strategy(settings: StrategySettings) -> Strategy:
    if settings.name == "moving_average_crossover":
        return MovingAverageCrossoverStrategy(
            short_window=int(settings.params.get("short_window", 5)),
            long_window=int(settings.params.get("long_window", 20)),
        )
    raise ValueError(f"Unsupported strategy: {settings.name}")


def _average(values: Iterable[float]) -> float:
    return float(fmean(values))
