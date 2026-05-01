"""Tests for data layer: CSV provider, resampler, data manager."""
from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from trading_framework.core.types import AssetClass
from trading_framework.models import MarketDataConfig, PriceBar
from trading_framework.data import MarketDataError
from trading_framework.data.providers.csv import CSVDataProvider
from trading_framework.data.resampler import resample
from trading_framework.data.manager import DataManager


def _make_bars(symbol="AAPL", count=10, interval_minutes=1, start_price=100.0):
    """Create synthetic bars for testing."""
    start = datetime(2026, 1, 2, 14, 0, tzinfo=timezone.utc)
    bars = []
    for i in range(count):
        price = start_price + i * 0.5
        bars.append(PriceBar(
            symbol=symbol,
            timestamp=start + timedelta(minutes=i * interval_minutes),
            open=price, high=price + 0.5, low=price - 0.5, close=price,
            volume=1000 + i * 100,
        ))
    return bars


# ---------------------------------------------------------------------------
# CSV Provider
# ---------------------------------------------------------------------------

class CSVProviderTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def _write_csv(self, symbol, rows):
        path = os.path.join(self.tmpdir, f"{symbol}.csv")
        with open(path, "w") as f:
            f.write("date,open,high,low,close,volume\n")
            for row in rows:
                f.write(",".join(str(v) for v in row) + "\n")
        return path

    def test_load_basic_csv(self):
        self._write_csv("AAPL", [
            ["2025-01-02", 150.0, 152.0, 149.0, 151.0, 100000],
            ["2025-01-03", 151.0, 153.0, 150.0, 152.0, 120000],
        ])
        provider = CSVDataProvider(data_dir=self.tmpdir)
        bars = provider.fetch_bars("AAPL", MarketDataConfig())
        self.assertEqual(2, len(bars))
        self.assertEqual("AAPL", bars[0].symbol)
        self.assertAlmostEqual(151.0, bars[0].close)
        self.assertAlmostEqual(152.0, bars[1].close)

    def test_sorted_by_timestamp(self):
        self._write_csv("MSFT", [
            ["2025-01-05", 300, 305, 298, 302, 50000],
            ["2025-01-02", 290, 295, 288, 292, 60000],
            ["2025-01-03", 292, 298, 290, 295, 55000],
        ])
        provider = CSVDataProvider(data_dir=self.tmpdir)
        bars = provider.fetch_bars("MSFT", MarketDataConfig())
        self.assertTrue(bars[0].timestamp < bars[1].timestamp < bars[2].timestamp)

    def test_missing_file_raises(self):
        provider = CSVDataProvider(data_dir=self.tmpdir)
        with self.assertRaises(MarketDataError):
            provider.fetch_bars("NONEXISTENT", MarketDataConfig())

    def test_empty_csv_raises(self):
        path = os.path.join(self.tmpdir, "EMPTY.csv")
        with open(path, "w") as f:
            f.write("date,open,high,low,close,volume\n")
        provider = CSVDataProvider(data_dir=self.tmpdir)
        with self.assertRaises(MarketDataError):
            provider.fetch_bars("EMPTY", MarketDataConfig())

    def test_case_insensitive_symbol(self):
        self._write_csv("SPY", [
            ["2025-01-02", 450, 455, 448, 452, 200000],
        ])
        provider = CSVDataProvider(data_dir=self.tmpdir)
        bars = provider.fetch_bars("spy", MarketDataConfig())
        self.assertEqual(1, len(bars))
        self.assertEqual("SPY", bars[0].symbol)

    def test_datetime_with_time(self):
        self._write_csv("TEST", [
            ["2025-01-02 09:30:00", 100, 102, 99, 101, 5000],
            ["2025-01-02 10:00:00", 101, 103, 100, 102, 6000],
        ])
        provider = CSVDataProvider(data_dir=self.tmpdir)
        bars = provider.fetch_bars("TEST", MarketDataConfig())
        self.assertEqual(2, len(bars))


# ---------------------------------------------------------------------------
# Resampler
# ---------------------------------------------------------------------------

class ResamplerTests(unittest.TestCase):
    def test_resample_1m_to_5m(self):
        bars = _make_bars(count=10, interval_minutes=1)
        result = resample(bars, "5m")
        self.assertEqual(2, len(result))
        # First bucket: bars 0-4
        self.assertEqual(bars[0].open, result[0].open)
        self.assertEqual(bars[4].close, result[0].close)
        self.assertEqual(max(b.high for b in bars[:5]), result[0].high)
        self.assertEqual(min(b.low for b in bars[:5]), result[0].low)
        self.assertEqual(sum(b.volume for b in bars[:5]), result[0].volume)

    def test_resample_1m_to_1h(self):
        bars = _make_bars(count=120, interval_minutes=1)
        result = resample(bars, "1h")
        self.assertEqual(2, len(result))

    def test_resample_empty_returns_empty(self):
        self.assertEqual([], resample([], "1h"))

    def test_unknown_interval_raises(self):
        with self.assertRaises(ValueError):
            resample(_make_bars(), "3m")

    def test_resample_preserves_symbol(self):
        bars = _make_bars(symbol="TSLA", count=10, interval_minutes=1)
        result = resample(bars, "5m")
        for bar in result:
            self.assertEqual("TSLA", bar.symbol)

    def test_single_bar_returns_one(self):
        bars = _make_bars(count=1)
        result = resample(bars, "1h")
        self.assertEqual(1, len(result))


# ---------------------------------------------------------------------------
# Data Manager
# ---------------------------------------------------------------------------

class FakeProvider:
    def __init__(self, bars):
        self.bars = bars
        self.call_count = 0

    def fetch_bars(self, symbol, config):
        self.call_count += 1
        return self.bars


class DataManagerTests(unittest.TestCase):
    def test_routes_by_asset_class(self):
        stock_provider = FakeProvider(_make_bars(symbol="AAPL"))
        crypto_provider = FakeProvider(_make_bars(symbol="BTC-USD"))

        manager = DataManager()
        manager.register_provider(AssetClass.STOCK, stock_provider)
        manager.register_provider(AssetClass.CRYPTO, crypto_provider)

        manager.fetch_bars("AAPL", MarketDataConfig())
        self.assertEqual(1, stock_provider.call_count)
        self.assertEqual(0, crypto_provider.call_count)

        manager.fetch_bars("BTC-USD", MarketDataConfig())
        self.assertEqual(1, stock_provider.call_count)
        self.assertEqual(1, crypto_provider.call_count)

    def test_falls_back_to_default(self):
        default = FakeProvider(_make_bars())
        manager = DataManager(default_provider=default)

        manager.fetch_bars("UNKNOWN", MarketDataConfig())
        self.assertEqual(1, default.call_count)

    def test_no_provider_raises(self):
        manager = DataManager()
        with self.assertRaises(MarketDataError):
            manager.fetch_bars("AAPL", MarketDataConfig())

    def test_providers_property(self):
        p = FakeProvider([])
        manager = DataManager(default_provider=p)
        manager.register_provider(AssetClass.CRYPTO, p)
        providers = manager.providers
        self.assertIn("crypto", providers)
        self.assertIn("default", providers)

    def test_forex_routing(self):
        forex_provider = FakeProvider(_make_bars())
        manager = DataManager()
        manager.register_provider(AssetClass.FOREX, forex_provider)

        manager.fetch_bars("EURUSD=X", MarketDataConfig())
        self.assertEqual(1, forex_provider.call_count)


if __name__ == "__main__":
    unittest.main()
