"""Strategy plugin registry with decorator-based registration.

Replaces the manual if/elif chain in create_strategy() with a
decorator-based registry. Each strategy file registers itself on import.

Usage — registering a strategy:

    from trading_framework.infra.plugin import register_strategy
    from trading_framework.core.interfaces import Strategy

    @register_strategy("my_strategy")
    class MyStrategy(Strategy):
        name = "my_strategy"
        def __init__(self, param1=10):
            self.param1 = param1
        def evaluate(self, symbol, bars):
            ...

Usage — creating a strategy from settings:

    from trading_framework.infra.plugin import create_strategy_from_registry
    from trading_framework.models import StrategySettings

    settings = StrategySettings(name="my_strategy", params={"param1": 20})
    strategy = create_strategy_from_registry(settings)

Usage — listing available strategies:

    from trading_framework.infra.plugin import list_strategies
    for name, cls in list_strategies().items():
        print(f"{name}: {cls.__doc__}")
"""
from __future__ import annotations

import logging
from typing import Dict, Type

logger = logging.getLogger(__name__)

# Global strategy registry: name -> class
_STRATEGY_REGISTRY: Dict[str, Type] = {}


def register_strategy(name: str):
    """Decorator to register a strategy class in the global registry.

    Args:
        name: The config name for this strategy (e.g., "rsi", "macd").

    Example:
        @register_strategy("bollinger_bands")
        class BollingerBandsStrategy(Strategy):
            ...
    """
    def decorator(cls):
        if name in _STRATEGY_REGISTRY:
            logger.warning(
                "Strategy '%s' already registered (%s). Overwriting with %s.",
                name, _STRATEGY_REGISTRY[name].__name__, cls.__name__,
            )
        _STRATEGY_REGISTRY[name] = cls
        logger.debug("Registered strategy: %s -> %s", name, cls.__name__)
        return cls
    return decorator


def create_strategy_from_registry(settings) -> object:
    """Create a strategy instance from StrategySettings using the registry.

    Args:
        settings: A StrategySettings with name and params.

    Returns:
        An instance of the registered strategy class.

    Raises:
        ValueError: If the strategy name is not registered.
    """
    cls = _STRATEGY_REGISTRY.get(settings.name)
    if cls is None:
        available = ", ".join(sorted(_STRATEGY_REGISTRY.keys()))
        raise ValueError(
            f"Unknown strategy: '{settings.name}'. "
            f"Available: {available or 'none (no strategies registered)'}"
        )
    return cls(**settings.params)


def list_strategies() -> Dict[str, Type]:
    """Return a copy of the strategy registry.

    Returns:
        Dict mapping strategy name to class.
    """
    return dict(_STRATEGY_REGISTRY)


def is_registered(name: str) -> bool:
    """Check if a strategy name is registered."""
    return name in _STRATEGY_REGISTRY


def clear_registry() -> None:
    """Clear all registered strategies. Useful for testing."""
    _STRATEGY_REGISTRY.clear()
