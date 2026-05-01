"""Market regime detection — identify trending vs ranging markets.

Classifies the current market state into regimes based on volatility
and trend strength. Strategies can adapt their parameters or enable/disable
based on the detected regime.

Regimes:
    TRENDING_UP    — Strong upward trend with moderate volatility
    TRENDING_DOWN  — Strong downward trend with moderate volatility
    RANGING        — Low volatility, price oscillating in a range
    HIGH_VOLATILITY — High volatility, unstable market
    LOW_VOLATILITY  — Very low volatility (squeeze, potential breakout)

Usage:
    from trading_framework.analytics.regime import detect_regime, MarketRegime

    regime = detect_regime(bars, lookback=20)
    if regime == MarketRegime.RANGING:
        # use mean-reversion strategy
    elif regime in (MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN):
        # use trend-following strategy
"""
from __future__ import annotations

import math
from enum import Enum
from statistics import fmean, stdev
from typing import Dict, List

from ..models import PriceBar


class MarketRegime(Enum):
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    UNKNOWN = "unknown"


def detect_regime(
    bars: List[PriceBar],
    lookback: int = 20,
    trend_threshold: float = 0.02,
    vol_high_pct: float = 75.0,
    vol_low_pct: float = 25.0,
) -> MarketRegime:
    """Detect the current market regime from recent price bars.

    Uses two metrics:
    1. Trend strength: linear regression slope of closes normalized by price
    2. Volatility percentile: current vol vs historical vol distribution

    Args:
        bars: Time-sorted price bars (need at least lookback * 2 for vol percentile).
        lookback: Window for regime calculation.
        trend_threshold: Min normalized slope to classify as trending (default 2%).
        vol_high_pct: Percentile above which vol is "high" (default 75th).
        vol_low_pct: Percentile below which vol is "low" (default 25th).

    Returns:
        MarketRegime enum value.
    """
    if len(bars) < lookback + 1:
        return MarketRegime.UNKNOWN

    closes = [b.close for b in bars[-lookback:]]

    # --- Trend: normalized slope ---
    slope = _linear_slope(closes)
    avg_price = fmean(closes)
    normalized_slope = slope / avg_price if avg_price != 0 else 0.0

    # --- Volatility: rolling std of returns ---
    returns = [(closes[i] - closes[i - 1]) / closes[i - 1]
               for i in range(1, len(closes)) if closes[i - 1] != 0]

    if len(returns) < 2:
        return MarketRegime.UNKNOWN

    current_vol = stdev(returns)

    # Historical volatility distribution (longer lookback if available)
    hist_vols = _rolling_volatilities(bars, lookback)
    if hist_vols:
        vol_percentile = _percentile_rank(current_vol, hist_vols)
    else:
        vol_percentile = 50.0

    # --- Classify ---
    if vol_percentile >= vol_high_pct:
        return MarketRegime.HIGH_VOLATILITY

    if vol_percentile <= vol_low_pct:
        return MarketRegime.LOW_VOLATILITY

    if normalized_slope > trend_threshold:
        return MarketRegime.TRENDING_UP

    if normalized_slope < -trend_threshold:
        return MarketRegime.TRENDING_DOWN

    return MarketRegime.RANGING


def regime_summary(bars: List[PriceBar], lookback: int = 20) -> Dict[str, str | float]:
    """Return regime detection with supporting metrics.

    Returns:
        Dict with regime, slope, volatility, vol_percentile.
    """
    if len(bars) < lookback + 1:
        return {"regime": MarketRegime.UNKNOWN.value, "slope": 0, "volatility": 0, "vol_percentile": 0}

    closes = [b.close for b in bars[-lookback:]]
    slope = _linear_slope(closes)
    avg_price = fmean(closes)
    normalized_slope = slope / avg_price if avg_price != 0 else 0.0

    returns = [(closes[i] - closes[i - 1]) / closes[i - 1]
               for i in range(1, len(closes)) if closes[i - 1] != 0]
    current_vol = stdev(returns) if len(returns) > 1 else 0.0

    hist_vols = _rolling_volatilities(bars, lookback)
    vol_percentile = _percentile_rank(current_vol, hist_vols) if hist_vols else 50.0

    regime = detect_regime(bars, lookback)

    return {
        "regime": regime.value,
        "slope": round(normalized_slope, 6),
        "volatility": round(current_vol, 6),
        "vol_percentile": round(vol_percentile, 1),
    }


def _linear_slope(values: List[float]) -> float:
    """Simple linear regression slope."""
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = fmean(values)
    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    return numerator / denominator if denominator != 0 else 0.0


def _rolling_volatilities(bars: List[PriceBar], window: int) -> List[float]:
    """Compute rolling volatility values for percentile ranking."""
    closes = [b.close for b in bars]
    vols = []
    for i in range(window + 1, len(closes)):
        segment = closes[i - window:i]
        returns = [(segment[j] - segment[j - 1]) / segment[j - 1]
                   for j in range(1, len(segment)) if segment[j - 1] != 0]
        if len(returns) > 1:
            vols.append(stdev(returns))
    return vols


def _percentile_rank(value: float, distribution: List[float]) -> float:
    """Compute percentile rank of value within distribution."""
    if not distribution:
        return 50.0
    below = sum(1 for v in distribution if v < value)
    return (below / len(distribution)) * 100.0
