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
        rsi = _compute_rsi(closes, self.period)
        previous_rsi = _compute_rsi(closes[:-1], self.period)
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


def create_strategy(settings: StrategySettings) -> Strategy:
    if settings.name == "moving_average_crossover":
        return MovingAverageCrossoverStrategy(
            short_window=int(settings.params.get("short_window", 5)),
            long_window=int(settings.params.get("long_window", 20)),
        )
    if settings.name == "rsi":
        return RSIStrategy(
            period=int(settings.params.get("period", 14)),
            oversold=int(settings.params.get("oversold", 30)),
            overbought=int(settings.params.get("overbought", 70)),
        )
    raise ValueError(f"Unsupported strategy: {settings.name}")


def _compute_rsi(closes: List[float], period: int) -> float:
    """Compute RSI using the standard Wilder smoothing method."""
    changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

    # Seed: simple average of first `period` changes
    gains = [max(c, 0) for c in changes[:period]]
    losses = [abs(min(c, 0)) for c in changes[:period]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    # Wilder smoothing for remaining changes
    for change in changes[period:]:
        gain = max(change, 0)
        loss = abs(min(change, 0))
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _average(values: Iterable[float]) -> float:
    return float(fmean(values))
