"""Signal confidence scoring model.

Rates signal quality based on multi-strategy agreement, volume context,
and trend alignment. Produces a Confidence level (HIGH/MEDIUM/LOW) and
a numeric score (0.0 to 1.0).

Usage:
    from trading_framework.signals.confidence import score_signals

    scored = score_signals(signals, bars, total_strategies=6)
    # scored = [{"signal": Signal, "confidence": Confidence.HIGH, "score": 0.85, "agreeing": 4}, ...]
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from ..core.types import Confidence
from ..models import PriceBar, Signal


def score_signals(
    signals: List[Signal],
    bars: List[PriceBar],
    total_strategies: int,
) -> List[Dict[str, Any]]:
    """Score a batch of signals from a single cycle.

    Groups signals by symbol, counts how many strategies agree on the
    same action, and assigns a confidence level.

    Args:
        signals: All non-HOLD signals emitted in this cycle.
        bars: Latest price bars (for volume context).
        total_strategies: Total number of strategies being run.

    Returns:
        List of scored signal dicts, sorted by score descending.
    """
    if not signals or total_strategies == 0:
        return []

    # Group signals by (symbol, action)
    groups: Dict[tuple, List[Signal]] = defaultdict(list)
    for sig in signals:
        groups[(sig.symbol, sig.action)].append(sig)

    scored = []
    for (symbol, action), group in groups.items():
        agreeing = len(group)
        agreement_ratio = agreeing / total_strategies

        # Volume factor: is current volume above average?
        volume_factor = _volume_factor(bars, symbol)

        # Compute score (0.0 to 1.0)
        # Agreement is the primary factor (70%), volume is secondary (30%)
        score = (agreement_ratio * 0.7) + (volume_factor * 0.3)
        score = round(min(score, 1.0), 4)

        # Map to confidence level
        if agreement_ratio >= 0.5:
            confidence = Confidence.HIGH
        elif agreement_ratio >= 0.3:
            confidence = Confidence.MEDIUM
        else:
            confidence = Confidence.LOW

        # Use the first signal as representative (they all have same symbol + action)
        representative = group[0]
        scored.append({
            "signal": representative,
            "confidence": confidence,
            "score": score,
            "agreeing": agreeing,
            "total_strategies": total_strategies,
            "agreement_ratio": round(agreement_ratio, 4),
            "volume_factor": round(volume_factor, 4),
            "strategies": [s.strategy_name for s in group],
        })

    # Sort by score descending
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def _volume_factor(bars: List[PriceBar], symbol: str) -> float:
    """Compute volume factor (0.0 to 1.0) for the latest bar.

    Returns 1.0 if current volume is 2x+ average, 0.5 if average, 0.0 if no data.
    """
    symbol_bars = [b for b in bars if b.symbol == symbol]
    if len(symbol_bars) < 2:
        return 0.5  # neutral if no data

    current_vol = symbol_bars[-1].volume
    avg_vol = sum(b.volume for b in symbol_bars[:-1]) / max(len(symbol_bars) - 1, 1)

    if avg_vol == 0:
        return 0.5

    ratio = current_vol / avg_vol
    # Normalize: 0x = 0.0, 1x = 0.5, 2x+ = 1.0
    return min(ratio / 2.0, 1.0)
