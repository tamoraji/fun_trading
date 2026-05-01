"""Data layer — market data providers, caching, and resampling.

Handles all market data acquisition, caching, and transformation:
- Multiple data providers (Yahoo Finance, Alpaca, CCXT, CSV)
- SQLite-based caching with TTL
- Timeframe resampling (1m -> 5m -> 1h -> 1d)
- Data manager that routes requests by asset class

Dependencies: core, infra.
"""
# Re-export current data classes for backward compatibility.
# NOTE: The flat module ``data.py`` is shadowed by this package directory,
# so we load it explicitly via importlib to avoid a circular import.
import importlib.util as _ilu
import pathlib as _pl

_data_flat = _pl.Path(__file__).resolve().parent.parent / "data.py"
_spec = _ilu.spec_from_file_location("trading_framework._data_flat", _data_flat)
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

MarketDataProvider = _mod.MarketDataProvider
MarketDataError = _mod.MarketDataError
YahooFinanceProvider = _mod.YahooFinanceProvider
create_market_data_provider = _mod.create_market_data_provider

del _ilu, _pl, _data_flat, _spec, _mod


def __getattr__(name):
    """Lazy import to avoid circular dependency with cache.py."""
    if name == "CachedDataProvider":
        from ..cache import CachedDataProvider
        globals()["CachedDataProvider"] = CachedDataProvider
        return CachedDataProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
