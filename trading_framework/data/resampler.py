"""Timeframe resampler — convert bars between intervals.

Aggregates shorter-interval bars into longer intervals.
For example, convert 1-minute bars into 5-minute or hourly bars.

Usage:
    from trading_framework.data.resampler import resample

    hourly_bars = resample(minute_bars, target_interval="1h")
    daily_bars = resample(hourly_bars, target_interval="1d")
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import List

from ..models import PriceBar

logger = logging.getLogger(__name__)

# Interval to seconds mapping
_INTERVAL_SECONDS = {
    "1m": 60, "2m": 120, "5m": 300, "15m": 900, "30m": 1800,
    "60m": 3600, "1h": 3600, "90m": 5400,
    "1d": 86400, "5d": 432000, "1wk": 604800,
}


def resample(bars: List[PriceBar], target_interval: str) -> List[PriceBar]:
    """Resample bars to a larger timeframe.

    Aggregates OHLCV bars: Open = first open, High = max high,
    Low = min low, Close = last close, Volume = sum.

    Args:
        bars: Input bars (must be sorted by timestamp ascending).
        target_interval: Target interval string (e.g., "5m", "1h", "1d").

    Returns:
        List of resampled PriceBars at the target interval.

    Raises:
        ValueError: If target interval is unknown.
    """
    if not bars:
        return []

    target_seconds = _INTERVAL_SECONDS.get(target_interval)
    if target_seconds is None:
        raise ValueError(f"Unknown target interval: '{target_interval}'. "
                         f"Supported: {', '.join(sorted(_INTERVAL_SECONDS.keys()))}")

    result: List[PriceBar] = []
    bucket: List[PriceBar] = []
    bucket_start: datetime | None = None

    for bar in bars:
        bar_bucket = _bucket_start(bar.timestamp, target_seconds)

        if bucket_start is None:
            bucket_start = bar_bucket

        if bar_bucket != bucket_start and bucket:
            result.append(_aggregate_bucket(bucket))
            bucket = []
            bucket_start = bar_bucket

        bucket.append(bar)

    # Final bucket
    if bucket:
        result.append(_aggregate_bucket(bucket))

    logger.debug("Resampled %d bars to %d bars (%s)", len(bars), len(result), target_interval)
    return result


def _bucket_start(timestamp: datetime, interval_seconds: int) -> datetime:
    """Calculate the start of the time bucket for a given timestamp."""
    epoch = timestamp.timestamp()
    bucket_epoch = (int(epoch) // interval_seconds) * interval_seconds
    return datetime.fromtimestamp(bucket_epoch, tz=timezone.utc)


def _aggregate_bucket(bars: List[PriceBar]) -> PriceBar:
    """Aggregate multiple bars into a single OHLCV bar."""
    return PriceBar(
        symbol=bars[0].symbol,
        timestamp=bars[0].timestamp,
        open=bars[0].open,
        high=max(b.high for b in bars),
        low=min(b.low for b in bars),
        close=bars[-1].close,
        volume=sum(b.volume for b in bars),
    )
