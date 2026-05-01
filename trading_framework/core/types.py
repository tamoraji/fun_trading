"""Core type constants and enums.

These are the fundamental constants used across the entire framework.
All action types, confidence levels, and asset classes are defined here.
"""
from __future__ import annotations

from enum import Enum

# --- Action constants (backward compatible with existing string constants) ---
BUY = "BUY"
SELL = "SELL"
HOLD = "HOLD"


class Confidence(Enum):
    """Signal confidence level based on multi-strategy agreement."""
    HIGH = "high"       # Most strategies agree
    MEDIUM = "medium"   # Some strategies agree
    LOW = "low"         # Single strategy, weak signal
    NONE = "none"       # No confidence scoring applied


class AssetClass(Enum):
    """Asset class for routing to the correct data provider."""
    STOCK = "stock"
    CRYPTO = "crypto"
    FOREX = "forex"
    FUTURES = "futures"
    OPTIONS = "options"
    COMMODITY = "commodity"
    UNKNOWN = "unknown"


def detect_asset_class(symbol: str) -> AssetClass:
    """Auto-detect asset class from symbol format.

    Examples:
        AAPL        -> STOCK
        BTC-USD     -> CRYPTO
        EURUSD=X    -> FOREX
        ES=F        -> FUTURES
        AAPL240119C -> OPTIONS
    """
    symbol = symbol.upper()
    if symbol.endswith("-USD") or symbol.endswith("-USDT") or symbol.endswith("-BTC"):
        return AssetClass.CRYPTO
    if symbol.endswith("=X"):
        return AssetClass.FOREX
    if symbol.endswith("=F"):
        return AssetClass.FUTURES
    if len(symbol) > 6 and any(c.isdigit() for c in symbol[-6:]):
        return AssetClass.OPTIONS
    return AssetClass.STOCK
