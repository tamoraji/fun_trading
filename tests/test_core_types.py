"""Tests for core types and asset class detection."""
from __future__ import annotations

import unittest

from trading_framework.core.types import (
    BUY, SELL, HOLD,
    Confidence, AssetClass, detect_asset_class,
)


class AssetClassDetectionTests(unittest.TestCase):
    def test_stock(self):
        self.assertEqual(AssetClass.STOCK, detect_asset_class("AAPL"))
        self.assertEqual(AssetClass.STOCK, detect_asset_class("MSFT"))
        self.assertEqual(AssetClass.STOCK, detect_asset_class("SPY"))

    def test_crypto(self):
        self.assertEqual(AssetClass.CRYPTO, detect_asset_class("BTC-USD"))
        self.assertEqual(AssetClass.CRYPTO, detect_asset_class("ETH-USD"))
        self.assertEqual(AssetClass.CRYPTO, detect_asset_class("SOL-USDT"))

    def test_forex(self):
        self.assertEqual(AssetClass.FOREX, detect_asset_class("EURUSD=X"))
        self.assertEqual(AssetClass.FOREX, detect_asset_class("GBPJPY=X"))

    def test_futures(self):
        self.assertEqual(AssetClass.FUTURES, detect_asset_class("ES=F"))
        self.assertEqual(AssetClass.FUTURES, detect_asset_class("GC=F"))

    def test_constants_unchanged(self):
        self.assertEqual("BUY", BUY)
        self.assertEqual("SELL", SELL)
        self.assertEqual("HOLD", HOLD)

    def test_confidence_enum(self):
        self.assertEqual("high", Confidence.HIGH.value)
        self.assertEqual("low", Confidence.LOW.value)


if __name__ == "__main__":
    unittest.main()
