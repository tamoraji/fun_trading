from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from typing import List

import pytest

from trading_framework.cache import CachedDataProvider
from trading_framework.data import MarketDataProvider
from trading_framework.models import MarketDataConfig, PriceBar


class FakeProvider(MarketDataProvider):
    def __init__(self, bars: List[PriceBar]):
        self.bars = bars
        self.call_count = 0

    def fetch_bars(self, symbol: str, config: MarketDataConfig) -> List[PriceBar]:
        self.call_count += 1
        return self.bars


def _make_bars(symbol: str = "AAPL", count: int = 3) -> List[PriceBar]:
    base = datetime(2026, 1, 5, 14, 0, 0, tzinfo=timezone.utc)
    return [
        PriceBar(
            symbol=symbol,
            timestamp=datetime(
                base.year, base.month, base.day, base.hour, base.minute + i * 5,
                tzinfo=timezone.utc,
            ),
            open=100.0 + i,
            high=101.0 + i,
            low=99.0 + i,
            close=100.5 + i,
            volume=1000 * (i + 1),
        )
        for i in range(count)
    ]


def _default_config(**overrides) -> MarketDataConfig:
    defaults = {"provider": "yahoo", "bar_interval": "5m", "lookback": "5d", "timeout_seconds": 10}
    defaults.update(overrides)
    return MarketDataConfig(**defaults)


class TestCachedDataProvider:
    def test_first_fetch_calls_upstream(self):
        bars = _make_bars()
        fake = FakeProvider(bars)
        with tempfile.TemporaryDirectory() as tmpdir:
            cached = CachedDataProvider(fake, cache_dir=tmpdir, ttl_seconds=300)
            result = cached.fetch_bars("AAPL", _default_config())
            assert fake.call_count == 1
            assert len(result) == len(bars)

    def test_second_fetch_uses_cache(self):
        bars = _make_bars()
        fake = FakeProvider(bars)
        with tempfile.TemporaryDirectory() as tmpdir:
            cached = CachedDataProvider(fake, cache_dir=tmpdir, ttl_seconds=300)
            config = _default_config()
            cached.fetch_bars("AAPL", config)
            cached.fetch_bars("AAPL", config)
            assert fake.call_count == 1

    def test_stale_cache_refetches(self):
        bars = _make_bars()
        fake = FakeProvider(bars)
        with tempfile.TemporaryDirectory() as tmpdir:
            cached = CachedDataProvider(fake, cache_dir=tmpdir, ttl_seconds=0)
            config = _default_config()
            cached.fetch_bars("AAPL", config)
            cached.fetch_bars("AAPL", config)
            assert fake.call_count == 2

    def test_cached_bars_match_original(self):
        bars = _make_bars()
        fake = FakeProvider(bars)
        with tempfile.TemporaryDirectory() as tmpdir:
            cached = CachedDataProvider(fake, cache_dir=tmpdir, ttl_seconds=300)
            config = _default_config()
            cached.fetch_bars("AAPL", config)
            result = cached.fetch_bars("AAPL", config)
            assert fake.call_count == 1  # served from cache
            for original, from_cache in zip(bars, result):
                assert original.symbol == from_cache.symbol
                assert original.timestamp == from_cache.timestamp
                assert original.open == pytest.approx(from_cache.open)
                assert original.high == pytest.approx(from_cache.high)
                assert original.low == pytest.approx(from_cache.low)
                assert original.close == pytest.approx(from_cache.close)
                assert original.volume == from_cache.volume

    def test_cache_stats(self):
        bars = _make_bars()
        fake = FakeProvider(bars)
        with tempfile.TemporaryDirectory() as tmpdir:
            cached = CachedDataProvider(fake, cache_dir=tmpdir, ttl_seconds=300)
            cached.fetch_bars("AAPL", _default_config())
            stats = cached.cache_stats()
            assert stats["bars"] == 3
            assert stats["symbols"] == 1
            assert stats["fetches"] == 1

    def test_clear_cache_symbol(self):
        aapl_bars = _make_bars("AAPL")
        msft_bars = _make_bars("MSFT")
        fake_aapl = FakeProvider(aapl_bars)
        fake_msft = FakeProvider(msft_bars)
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use fake_aapl as upstream initially, fetch AAPL
            cached = CachedDataProvider(fake_aapl, cache_dir=tmpdir, ttl_seconds=300)
            cached.fetch_bars("AAPL", _default_config())
            # Swap upstream to fetch MSFT
            cached.upstream = fake_msft
            cached.fetch_bars("MSFT", _default_config())
            assert cached.cache_stats()["symbols"] == 2
            cached.clear_cache("AAPL")
            stats = cached.cache_stats()
            assert stats["symbols"] == 1
            assert stats["bars"] == 3  # only MSFT bars remain

    def test_clear_cache_all(self):
        bars = _make_bars()
        fake = FakeProvider(bars)
        with tempfile.TemporaryDirectory() as tmpdir:
            cached = CachedDataProvider(fake, cache_dir=tmpdir, ttl_seconds=300)
            cached.fetch_bars("AAPL", _default_config())
            cached.clear_cache()
            stats = cached.cache_stats()
            assert stats["bars"] == 0
            assert stats["symbols"] == 0
            assert stats["fetches"] == 0

    def test_different_symbols_cached_independently(self):
        aapl_bars = _make_bars("AAPL")
        msft_bars = _make_bars("MSFT")
        fake_aapl = FakeProvider(aapl_bars)
        fake_msft = FakeProvider(msft_bars)
        with tempfile.TemporaryDirectory() as tmpdir:
            cached = CachedDataProvider(fake_aapl, cache_dir=tmpdir, ttl_seconds=300)
            config = _default_config()
            cached.fetch_bars("AAPL", config)
            cached.upstream = fake_msft
            cached.fetch_bars("MSFT", config)
            # Both fetched from upstream
            assert fake_aapl.call_count == 1
            assert fake_msft.call_count == 1
            # Second calls served from cache
            cached.upstream = fake_aapl
            cached.fetch_bars("AAPL", config)
            cached.upstream = fake_msft
            cached.fetch_bars("MSFT", config)
            assert fake_aapl.call_count == 1
            assert fake_msft.call_count == 1

    def test_different_intervals_cached_independently(self):
        bars_5m = _make_bars("AAPL")
        bars_1h = _make_bars("AAPL", count=2)
        fake = FakeProvider(bars_5m)
        with tempfile.TemporaryDirectory() as tmpdir:
            cached = CachedDataProvider(fake, cache_dir=tmpdir, ttl_seconds=300)
            cached.fetch_bars("AAPL", _default_config(bar_interval="5m"))
            fake.bars = bars_1h
            cached.fetch_bars("AAPL", _default_config(bar_interval="1h"))
            assert fake.call_count == 2
            stats = cached.cache_stats()
            # 3 bars at 5m + 2 bars at 1h = 5 total
            assert stats["bars"] == 5

    def test_db_created_in_cache_dir(self):
        bars = _make_bars()
        fake = FakeProvider(bars)
        with tempfile.TemporaryDirectory() as tmpdir:
            cached = CachedDataProvider(fake, cache_dir=tmpdir, ttl_seconds=300)
            assert cached.db_path.exists()
            assert str(cached.db_path).startswith(tmpdir)
            assert cached.db_path.name == "market_data.db"
