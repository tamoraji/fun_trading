"""Feature engineering pipeline for ML models.

Transforms raw PriceBars into a feature matrix suitable for machine
learning. Features include rolling statistics, momentum indicators,
volatility measures, and calendar effects.

Usage:
    from trading_framework.analytics.ml.features import extract_features

    features = extract_features(bars, lookback=20)
    # features = [{"timestamp": ..., "close": ..., "return_1d": ..., "rsi_14": ..., ...}, ...]
"""
from __future__ import annotations

import math
from datetime import datetime
from statistics import fmean, stdev
from typing import Any, Dict, List

from ...models import PriceBar


def extract_features(bars: List[PriceBar], lookback: int = 20) -> List[Dict[str, Any]]:
    """Extract features from price bars for ML model input.

    Each bar produces one feature row. Features require `lookback` bars
    of history, so the first `lookback` rows will have some None values.

    Args:
        bars: Time-sorted price bars.
        lookback: Window for rolling calculations.

    Returns:
        List of feature dicts, one per bar (aligned with bars by index).
    """
    if not bars:
        return []

    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    volumes = [b.volume for b in bars]

    features = []
    for i, bar in enumerate(bars):
        row: Dict[str, Any] = {
            "timestamp": bar.timestamp,
            "close": bar.close,
            "volume": bar.volume,
        }

        # --- Returns ---
        if i >= 1:
            row["return_1d"] = (closes[i] - closes[i - 1]) / closes[i - 1] if closes[i - 1] != 0 else 0.0
        else:
            row["return_1d"] = 0.0

        if i >= 5:
            row["return_5d"] = (closes[i] - closes[i - 5]) / closes[i - 5] if closes[i - 5] != 0 else 0.0
        else:
            row["return_5d"] = None

        # --- Rolling stats (need `lookback` bars) ---
        if i >= lookback:
            window = closes[i - lookback + 1:i + 1]
            vol_window = volumes[i - lookback + 1:i + 1]

            row["sma"] = fmean(window)
            row["std"] = stdev(window) if len(window) > 1 else 0.0
            row["price_vs_sma"] = (bar.close - row["sma"]) / row["sma"] if row["sma"] != 0 else 0.0

            # Bollinger position (0 = lower band, 1 = upper band)
            if row["std"] > 0:
                row["bollinger_pct"] = (bar.close - (row["sma"] - 2 * row["std"])) / (4 * row["std"])
            else:
                row["bollinger_pct"] = 0.5

            # Volume ratio
            avg_vol = fmean(vol_window)
            row["volume_ratio"] = bar.volume / avg_vol if avg_vol > 0 else 1.0

            # Rolling high/low distance
            rolling_high = max(highs[i - lookback + 1:i + 1])
            rolling_low = min(lows[i - lookback + 1:i + 1])
            price_range = rolling_high - rolling_low
            row["high_low_pct"] = (bar.close - rolling_low) / price_range if price_range > 0 else 0.5

            # Volatility (annualized from daily returns)
            if i >= lookback + 1:
                returns = [(closes[j] - closes[j - 1]) / closes[j - 1]
                           for j in range(i - lookback + 1, i + 1) if closes[j - 1] != 0]
                if len(returns) > 1:
                    row["volatility"] = stdev(returns) * math.sqrt(252)
                else:
                    row["volatility"] = 0.0
            else:
                row["volatility"] = None
        else:
            row["sma"] = None
            row["std"] = None
            row["price_vs_sma"] = None
            row["bollinger_pct"] = None
            row["volume_ratio"] = None
            row["high_low_pct"] = None
            row["volatility"] = None

        # --- RSI (14-period) ---
        if i >= 15:
            row["rsi_14"] = _quick_rsi(closes[:i + 1], 14)
        else:
            row["rsi_14"] = None

        # --- Calendar features ---
        row["day_of_week"] = bar.timestamp.weekday()
        row["month"] = bar.timestamp.month

        features.append(row)

    return features


def _quick_rsi(closes: List[float], period: int) -> float:
    """Fast RSI computation for feature extraction."""
    changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(c, 0) for c in changes[:period]]
    losses = [abs(min(c, 0)) for c in changes[:period]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    for change in changes[period:]:
        avg_gain = (avg_gain * (period - 1) + max(change, 0)) / period
        avg_loss = (avg_loss * (period - 1) + abs(min(change, 0))) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def get_feature_names(lookback: int = 20) -> List[str]:
    """Return the list of feature names produced by extract_features."""
    return [
        "close", "volume", "return_1d", "return_5d",
        "sma", "std", "price_vs_sma", "bollinger_pct",
        "volume_ratio", "high_low_pct", "volatility",
        "rsi_14", "day_of_week", "month",
    ]
