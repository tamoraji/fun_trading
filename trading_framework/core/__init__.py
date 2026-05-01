"""Core layer — models, events, interfaces, and type definitions.

This is the foundation of the trading framework. All other layers import
from here. This package has ZERO external dependencies.

Modules:
    models      — PriceBar, Signal, AppSettings, config dataclasses
    events      — Event types for the event bus (SignalEmitted, OrderFilled, etc.)
    interfaces  — ABCs for Strategy, DataProvider, Notifier, Broker, RiskFilter
    types       — Constants (BUY, SELL, HOLD), Confidence, AssetClass enums
"""
# Re-export models for backward compatibility
from ..models import (
    BUY, SELL, HOLD,
    PriceBar, Signal, AppSettings,
    MarketDataConfig, StrategySettings, NotifierSettings,
    MarketSession, SignalHistorySettings,
)

# New core modules
from .types import Confidence, AssetClass, detect_asset_class
from .events import (
    SignalEmitted, SignalBlocked, CycleStarted, CycleCompleted,
    OrderFilled, DataError, ApprovalRequested, ApprovalReceived,
)
from .interfaces import Strategy, DataProvider, Notifier, SignalStore, RiskFilter, Broker
