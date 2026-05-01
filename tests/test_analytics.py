"""Tests for analytics layer: features, regime detection, ML strategy, costs."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from trading_framework.models import BUY, SELL, HOLD, PriceBar
from trading_framework.backtest import Trade
from trading_framework.analytics.ml.features import extract_features, get_feature_names
from trading_framework.analytics.ml.models import MomentumMLStrategy
from trading_framework.analytics.regime import detect_regime, regime_summary, MarketRegime
from trading_framework.analytics.costs import CostModel, apply_costs, cost_summary


def _bars(count=50, start_price=100.0, trend=0.5, volume=10000):
    """Create synthetic bars with configurable trend."""
    start = datetime(2026, 1, 2, 14, 0, tzinfo=timezone.utc)
    bars = []
    for i in range(count):
        price = start_price + i * trend
        bars.append(PriceBar(
            symbol="TEST", timestamp=start + timedelta(days=i),
            open=price - 0.2, high=price + 1.0, low=price - 1.0, close=price,
            volume=volume + (i * 100),
        ))
    return bars


def _trade(entry_price=100, exit_price=110, action="BUY"):
    if action == "BUY":
        pnl = (exit_price - entry_price) / entry_price * 100
    else:
        pnl = (entry_price - exit_price) / entry_price * 100
    return Trade(
        symbol="TEST", strategy_name="test", entry_action=action,
        entry_price=entry_price, exit_price=exit_price,
        entry_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        exit_timestamp=datetime(2026, 2, 1, tzinfo=timezone.utc),
        profit_pct=round(pnl, 4),
    )


# ---------------------------------------------------------------------------
# Feature Engineering
# ---------------------------------------------------------------------------

class FeatureTests(unittest.TestCase):
    def test_extract_features_returns_correct_count(self):
        bars = _bars(count=50)
        features = extract_features(bars, lookback=20)
        self.assertEqual(50, len(features))

    def test_features_have_all_keys(self):
        bars = _bars(count=50)
        features = extract_features(bars, lookback=20)
        last = features[-1]
        for name in get_feature_names():
            self.assertIn(name, last, f"Missing feature: {name}")

    def test_early_features_have_nones(self):
        bars = _bars(count=50)
        features = extract_features(bars, lookback=20)
        # First bar should have None for lookback-dependent features
        self.assertIsNone(features[0]["sma"])
        self.assertIsNone(features[0]["volatility"])

    def test_later_features_populated(self):
        bars = _bars(count=50)
        features = extract_features(bars, lookback=20)
        last = features[-1]
        self.assertIsNotNone(last["sma"])
        self.assertIsNotNone(last["rsi_14"])
        self.assertIsNotNone(last["volatility"])
        self.assertIsNotNone(last["bollinger_pct"])

    def test_return_1d_calculated(self):
        bars = _bars(count=5, start_price=100, trend=1.0)
        features = extract_features(bars)
        # Bar 1: close=101, prev=100, return = 1%
        self.assertAlmostEqual(0.01, features[1]["return_1d"], places=3)

    def test_empty_bars(self):
        self.assertEqual([], extract_features([]))


# ---------------------------------------------------------------------------
# Regime Detection
# ---------------------------------------------------------------------------

class RegimeTests(unittest.TestCase):
    def test_trending_up_detected_by_summary(self):
        bars = _bars(count=50, trend=1.0)
        summary = regime_summary(bars)
        # Slope should be positive for uptrend
        self.assertGreater(summary["slope"], 0)

    def test_trending_down_detected_by_summary(self):
        bars = _bars(count=50, start_price=200, trend=-1.0)
        summary = regime_summary(bars)
        # Slope should be negative for downtrend
        self.assertLess(summary["slope"], 0)

    def test_regime_is_valid_enum(self):
        bars = _bars(count=80, trend=0.5)
        regime = detect_regime(bars, lookback=20)
        self.assertIsInstance(regime, MarketRegime)

    def test_ranging(self):
        # Alternating up/down = no trend
        bars = []
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for i in range(50):
            price = 100 + (1 if i % 2 == 0 else -1) * 0.5
            bars.append(PriceBar(
                symbol="TEST", timestamp=start + timedelta(days=i),
                open=price, high=price + 0.5, low=price - 0.5, close=price,
                volume=10000,
            ))
        regime = detect_regime(bars, lookback=20)
        self.assertIn(regime, (MarketRegime.RANGING, MarketRegime.LOW_VOLATILITY))

    def test_insufficient_data(self):
        bars = _bars(count=5)
        self.assertEqual(MarketRegime.UNKNOWN, detect_regime(bars, lookback=20))

    def test_regime_summary(self):
        bars = _bars(count=50, trend=1.0)
        summary = regime_summary(bars)
        self.assertIn("regime", summary)
        self.assertIn("slope", summary)
        self.assertIn("volatility", summary)


# ---------------------------------------------------------------------------
# ML Strategy
# ---------------------------------------------------------------------------

class MomentumMLTests(unittest.TestCase):
    def test_hold_on_insufficient_data(self):
        strategy = MomentumMLStrategy(lookback=20)
        bars = _bars(count=10)
        signal = strategy.evaluate("TEST", bars)
        self.assertEqual(HOLD, signal.action)

    def test_produces_signal_on_sufficient_data(self):
        strategy = MomentumMLStrategy(lookback=20)
        bars = _bars(count=60, trend=1.0)
        signal = strategy.evaluate("TEST", bars)
        self.assertIn(signal.action, (BUY, SELL, HOLD))
        self.assertIn("score", signal.details)
        self.assertEqual("momentum_ml", signal.strategy_name)

    def test_invalid_params(self):
        with self.assertRaises(ValueError):
            MomentumMLStrategy(lookback=0)
        with self.assertRaises(ValueError):
            MomentumMLStrategy(buy_threshold=0.3, sell_threshold=0.7)

    def test_factory_registration(self):
        from trading_framework.infra.plugin import is_registered
        # Ensure strategies module is imported to trigger registration
        import trading_framework.analytics.ml.models  # noqa
        self.assertTrue(is_registered("momentum_ml"))


# ---------------------------------------------------------------------------
# Transaction Costs
# ---------------------------------------------------------------------------

class CostTests(unittest.TestCase):
    def test_slippage_reduces_profit(self):
        trades = [_trade(entry_price=100, exit_price=110)]  # +10%
        model = CostModel(slippage_pct=0.5)
        adjusted = apply_costs(trades, model)
        self.assertLess(adjusted[0].profit_pct, trades[0].profit_pct)

    def test_commission_reduces_profit(self):
        trades = [_trade(entry_price=100, exit_price=110)]
        model = CostModel(slippage_pct=0, commission_per_trade=5.0)
        adjusted = apply_costs(trades, model)
        self.assertLess(adjusted[0].profit_pct, trades[0].profit_pct)

    def test_zero_costs_no_change(self):
        trades = [_trade(entry_price=100, exit_price=110)]
        model = CostModel(slippage_pct=0, commission_per_trade=0)
        adjusted = apply_costs(trades, model)
        self.assertAlmostEqual(trades[0].profit_pct, adjusted[0].profit_pct, places=2)

    def test_cost_summary(self):
        trades = [_trade(100, 110), _trade(110, 105, "SELL")]
        model = CostModel(slippage_pct=0.1, commission_per_trade=2.0)
        adjusted = apply_costs(trades, model)
        summary = cost_summary(trades, adjusted)
        self.assertIn("original_return_pct", summary)
        self.assertIn("adjusted_return_pct", summary)
        self.assertGreater(summary["total_cost_pct"], 0)

    def test_short_trade_slippage(self):
        trades = [_trade(entry_price=100, exit_price=90, action="SELL")]  # +10% short
        model = CostModel(slippage_pct=0.5)
        adjusted = apply_costs(trades, model)
        self.assertLess(adjusted[0].profit_pct, trades[0].profit_pct)


if __name__ == "__main__":
    unittest.main()
