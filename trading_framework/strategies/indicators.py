"""Shared technical indicator functions used by multiple strategies."""
from __future__ import annotations

from statistics import fmean
from typing import Iterable, List

from ..models import PriceBar


def average(values: Iterable[float]) -> float:
    """Compute the arithmetic mean of *values* using ``fmean``."""
    return float(fmean(values))


def compute_rsi(closes: List[float], period: int) -> float:
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


def compute_ema(values: List[float], period: int) -> List[float]:
    """Compute EMA for a list of values. Seed with SMA of first *period* values."""
    multiplier = 2.0 / (period + 1)
    sma = sum(values[:period]) / period
    ema_values = [sma]
    for v in values[period:]:
        ema_values.append(v * multiplier + ema_values[-1] * (1 - multiplier))
    return ema_values


def compute_value_area(
    bars: List[PriceBar], value_area_pct: float
) -> tuple[float, float, float, float]:
    """Compute POC, VWAP, VAH, VAL from a list of PriceBars."""
    total_volume = sum(b.volume for b in bars)
    if total_volume == 0:
        closes = [b.close for b in bars]
        mid = average(closes)
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
