"""Data manager — routes data requests to providers by asset class.

Auto-detects asset class from symbol format and routes to the appropriate
provider. Handles fallback and optional caching.

Usage:
    from trading_framework.data.manager import DataManager

    manager = DataManager()
    manager.register_provider(AssetClass.STOCK, yahoo_provider)
    manager.register_provider(AssetClass.CRYPTO, yahoo_provider)  # Yahoo handles crypto too
    manager.set_default(yahoo_provider)

    bars = manager.fetch_bars("AAPL", config)     # routes to STOCK provider
    bars = manager.fetch_bars("BTC-USD", config)   # routes to CRYPTO provider
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from ..core.types import AssetClass, detect_asset_class
from ..models import MarketDataConfig, PriceBar
from ..data import MarketDataProvider, MarketDataError

logger = logging.getLogger(__name__)


class DataManager(MarketDataProvider):
    """Routes data requests to asset-class-specific providers.

    Implements the MarketDataProvider interface so it can be used
    as a drop-in replacement anywhere a provider is expected.

    Args:
        default_provider: Fallback provider when no asset-class-specific one is registered.
    """

    def __init__(self, default_provider: MarketDataProvider | None = None):
        self._providers: Dict[AssetClass, MarketDataProvider] = {}
        self._default = default_provider

    def register_provider(self, asset_class: AssetClass, provider: MarketDataProvider) -> None:
        """Register a provider for a specific asset class.

        Args:
            asset_class: The asset class this provider handles.
            provider: The data provider instance.
        """
        self._providers[asset_class] = provider
        logger.debug("Registered provider for %s: %s", asset_class.value, type(provider).__name__)

    def set_default(self, provider: MarketDataProvider) -> None:
        """Set the default fallback provider."""
        self._default = provider

    def fetch_bars(self, symbol: str, config: MarketDataConfig) -> List[PriceBar]:
        """Fetch bars by auto-detecting asset class and routing to the right provider.

        Falls back to default provider if no specific provider is registered.

        Raises:
            MarketDataError: If no provider can handle the request.
        """
        asset_class = detect_asset_class(symbol)
        provider = self._providers.get(asset_class) or self._default

        if provider is None:
            raise MarketDataError(
                f"No provider registered for {asset_class.value} "
                f"(symbol: {symbol}). Register a provider or set a default."
            )

        logger.debug("Routing %s (%s) to %s", symbol, asset_class.value, type(provider).__name__)
        return provider.fetch_bars(symbol, config)

    @property
    def providers(self) -> Dict[str, str]:
        """Return registered providers for debugging."""
        result = {}
        for asset_class, provider in self._providers.items():
            result[asset_class.value] = type(provider).__name__
        if self._default:
            result["default"] = type(self._default).__name__
        return result
