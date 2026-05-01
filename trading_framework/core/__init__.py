"""Core layer — models, events, interfaces, and type definitions.

This is the foundation of the trading framework. All other layers import
from here. This package has ZERO external dependencies.

Modules:
    models      — PriceBar, Signal, Trade, Position, AppSettings, etc.
    events      — Event types for the event bus (SignalEmitted, OrderFilled, etc.)
    interfaces  — ABCs for Strategy, DataProvider, Notifier, Broker, RiskFilter
    types       — Constants (BUY, SELL, HOLD), type aliases, enums
"""
# Re-export current models for backward compatibility
from ..models import (
    BUY, SELL, HOLD,
    PriceBar, Signal, AppSettings,
    MarketDataConfig, StrategySettings, NotifierSettings,
    MarketSession, SignalHistorySettings,
)
