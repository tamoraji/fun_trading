"""ML model interface and simple implementations.

ML models are wrapped as Strategy implementations, so they plug directly
into the existing engine. Train on historical features, predict direction.

Usage:
    from trading_framework.analytics.ml.models import MomentumMLStrategy

    # Train
    strategy = MomentumMLStrategy(lookback=20, threshold=0.6)
    # Use like any other strategy:
    signal = strategy.evaluate("AAPL", bars)

The MomentumMLStrategy is a simple "ML-lite" model that uses feature
scoring instead of a full sklearn pipeline. It's stdlib-only and serves
as the interface template for more sophisticated models.
"""
from __future__ import annotations

import logging
from statistics import fmean
from typing import List

from ...models import BUY, HOLD, SELL, PriceBar, Signal
from ...strategy import Strategy
from ...infra.plugin import register_strategy
from .features import extract_features

logger = logging.getLogger(__name__)


@register_strategy("momentum_ml")
class MomentumMLStrategy(Strategy):
    """Simple ML-inspired momentum strategy using feature scoring.

    Scores the current market state using multiple features (RSI, trend,
    volatility, volume) and generates signals when the composite score
    exceeds a threshold.

    This is a stdlib-only implementation. For full ML (Random Forest,
    XGBoost, etc.), extend this pattern with sklearn/lightgbm.

    Args:
        lookback: Feature extraction window.
        buy_threshold: Score above this → BUY (0.0 to 1.0).
        sell_threshold: Score below this → SELL (0.0 to 1.0).
    """
    name = "momentum_ml"

    def __init__(
        self,
        lookback: int = 20,
        buy_threshold: float = 0.65,
        sell_threshold: float = 0.35,
    ):
        if lookback <= 0:
            raise ValueError("lookback must be positive.")
        if buy_threshold <= sell_threshold:
            raise ValueError("buy_threshold must be greater than sell_threshold.")
        self.lookback = lookback
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

    def evaluate(self, symbol: str, bars: List[PriceBar]) -> Signal:
        min_bars = self.lookback + 16  # need lookback + RSI warm-up
        latest_bar = bars[-1]

        if len(bars) < min_bars:
            return Signal(
                symbol=symbol, action=HOLD, price=latest_bar.close,
                timestamp=latest_bar.timestamp,
                reason="Not enough history for ML features.",
                strategy_name=self.name,
                details={"bars_available": len(bars), "bars_needed": min_bars},
            )

        features = extract_features(bars, lookback=self.lookback)
        current = features[-1]

        # Score = weighted combination of features (0.0 to 1.0)
        score = self._compute_score(current)

        details = {
            "score": round(score, 4),
            "buy_threshold": self.buy_threshold,
            "sell_threshold": self.sell_threshold,
            "rsi_14": current.get("rsi_14"),
            "return_1d": current.get("return_1d"),
            "volume_ratio": current.get("volume_ratio"),
            "bollinger_pct": current.get("bollinger_pct"),
            "volatility": current.get("volatility"),
        }

        if score >= self.buy_threshold:
            return Signal(
                symbol=symbol, action=BUY, price=latest_bar.close,
                timestamp=latest_bar.timestamp,
                reason=f"ML momentum score {score:.2f} above buy threshold {self.buy_threshold}.",
                strategy_name=self.name,
                details=details,
            )

        if score <= self.sell_threshold:
            return Signal(
                symbol=symbol, action=SELL, price=latest_bar.close,
                timestamp=latest_bar.timestamp,
                reason=f"ML momentum score {score:.2f} below sell threshold {self.sell_threshold}.",
                strategy_name=self.name,
                details=details,
            )

        return Signal(
            symbol=symbol, action=HOLD, price=latest_bar.close,
            timestamp=latest_bar.timestamp,
            reason=f"ML score {score:.2f} in neutral zone ({self.sell_threshold}-{self.buy_threshold}).",
            strategy_name=self.name,
            details=details,
        )

    def _compute_score(self, features: dict) -> float:
        """Compute a momentum score from features (0.0 bearish to 1.0 bullish).

        Factors and weights:
        - RSI position (30%): RSI/100, higher = more bullish
        - Trend (25%): price_vs_sma, positive = bullish
        - Bollinger position (20%): bollinger_pct, 0=oversold, 1=overbought
        - Volume confirmation (15%): above-average volume = stronger signal
        - Return momentum (10%): recent return direction
        """
        components = []
        weights = []

        # RSI (0 to 1)
        rsi = features.get("rsi_14")
        if rsi is not None:
            components.append(rsi / 100.0)
            weights.append(0.30)

        # Trend (price vs SMA, clamped to 0-1)
        pvs = features.get("price_vs_sma")
        if pvs is not None:
            # Normalize: -5% = 0.0, 0% = 0.5, +5% = 1.0
            trend_score = max(0.0, min(1.0, pvs / 0.10 + 0.5))
            components.append(trend_score)
            weights.append(0.25)

        # Bollinger position (already 0-1)
        boll = features.get("bollinger_pct")
        if boll is not None:
            components.append(max(0.0, min(1.0, boll)))
            weights.append(0.20)

        # Volume (above average = bullish signal, capped at 1.0)
        vol_ratio = features.get("volume_ratio")
        if vol_ratio is not None:
            vol_score = min(vol_ratio / 2.0, 1.0)
            components.append(vol_score)
            weights.append(0.15)

        # Return momentum (clamped to 0-1)
        ret = features.get("return_1d")
        if ret is not None:
            ret_score = max(0.0, min(1.0, ret / 0.05 + 0.5))
            components.append(ret_score)
            weights.append(0.10)

        if not components:
            return 0.5  # neutral

        total_weight = sum(weights)
        return sum(c * w for c, w in zip(components, weights)) / total_weight
