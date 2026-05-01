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
        average_volume = _average([b.volume for b in window])

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

        fast_ema_values = _compute_ema(closes, self.fast_period)
        slow_ema_values = _compute_ema(closes, self.slow_period)

        # MACD line: fast EMA - slow EMA (aligned to slow EMA start)
        offset = self.slow_period - self.fast_period
        macd_line = [
            fast_ema_values[offset + i] - slow_ema_values[i]
            for i in range(len(slow_ema_values))
        ]

        signal_line_values = _compute_ema(macd_line, self.signal_period)

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
        direction_line = _average(closes[-self.direction_period:])
        price_above = latest_bar.close > direction_line

        # Timing Line: compute for recent bars to build confirming line
        # We need confirming_period + 1 timing values
        timing_values: List[float] = []
        for i in range(self.confirming_period + 1):
            offset = len(closes) - self.confirming_period - 1 + i
            if offset >= self.timing_long:
                short_avg = _average(closes[offset - self.timing_short + 1:offset + 1])
                long_avg = _average(closes[offset - self.timing_long + 1:offset + 1])
                timing_values.append(short_avg - long_avg)

        timing_line = timing_values[-1]
        previous_timing = timing_values[-2]

        # Confirming Line: SMA of last confirming_period timing values
        confirming_line = _average(timing_values[-self.confirming_period:])
        previous_confirming = _average(timing_values[-self.confirming_period - 1:-1])

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

        poc, vwap, vah, val = _compute_value_area(lookback_bars, self.value_area_pct)

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
    if settings.name == "breakout":
        return BreakoutStrategy(
            lookback=int(settings.params.get("lookback", 20)),
            volume_factor=float(settings.params.get("volume_factor", 1.5)),
        )
    if settings.name == "macd":
        return MACDStrategy(
            fast_period=int(settings.params.get("fast_period", 12)),
            slow_period=int(settings.params.get("slow_period", 26)),
            signal_period=int(settings.params.get("signal_period", 9)),
        )
    if settings.name == "goslin_momentum":
        return GoslinMomentumStrategy(
            direction_period=int(settings.params.get("direction_period", 49)),
            timing_short=int(settings.params.get("timing_short", 3)),
            timing_long=int(settings.params.get("timing_long", 10)),
            confirming_period=int(settings.params.get("confirming_period", 15)),
        )
    if settings.name == "market_profile":
        return MarketProfileStrategy(
            lookback=int(settings.params.get("lookback", 20)),
            value_area_pct=float(settings.params.get("value_area_pct", 70.0)),
        )
    # Fall back to plugin registry for strategies registered via @register_strategy
    try:
        # Ensure strategy modules are imported (triggers registration)
        import trading_framework.analytics.ml.models  # noqa: F401
        from .infra.plugin import create_strategy_from_registry
        return create_strategy_from_registry(settings)
    except (ImportError, ValueError):
        pass
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


def _compute_ema(values: List[float], period: int) -> List[float]:
    """Compute EMA for a list of values. Seed with SMA of first *period* values."""
    multiplier = 2.0 / (period + 1)
    sma = sum(values[:period]) / period
    ema_values = [sma]
    for v in values[period:]:
        ema_values.append(v * multiplier + ema_values[-1] * (1 - multiplier))
    return ema_values


def _compute_value_area(
    bars: List[PriceBar], value_area_pct: float
) -> tuple[float, float, float, float]:
    """Compute POC, VWAP, VAH, VAL from a list of PriceBars."""
    total_volume = sum(b.volume for b in bars)
    if total_volume == 0:
        closes = [b.close for b in bars]
        mid = _average(closes)
        return mid, mid, max(closes), min(closes)

    # VWAP
    vwap = sum(b.close * b.volume for b in bars) / total_volume

    # POC: bar with highest volume
    poc_bar = max(bars, key=lambda b: b.volume)
    poc = poc_bar.close

    # Value Area: sort bars by volume descending, accumulate until value_area_pct reached
    sorted_bars = sorted(bars, key=lambda b: b.volume, reverse=True)
    target_volume = total_volume * (value_area_pct / 100)
    accumulated = 0.0
    value_bars: List[PriceBar] = []
    for bar in sorted_bars:
        value_bars.append(bar)
        accumulated += bar.volume
        if accumulated >= target_volume:
            break

    vah = max(b.close for b in value_bars)
    val = min(b.close for b in value_bars)

    return poc, round(vwap, 4), round(vah, 4), round(val, 4)


def _average(values: Iterable[float]) -> float:
    return float(fmean(values))
