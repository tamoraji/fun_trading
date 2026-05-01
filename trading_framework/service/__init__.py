"""Service layer — the single API that all UIs consume.

The TradingService class is the facade between the UI layer and
everything below. All UIs (CLI, TUI, Web, Telegram) call methods
on TradingService instead of importing engine/strategy/data directly.

This is the key architectural boundary:
- UI layer imports ONLY from service
- Service layer orchestrates all lower layers

Dependencies: all lower layers.
"""
from .api import TradingService
