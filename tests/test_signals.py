"""Tests for signal aggregation, confidence scoring, and notification routing."""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from trading_framework.core.types import Confidence
from trading_framework.core.events import SignalEmitted, CycleCompleted
from trading_framework.infra.event_bus import EventBus
from trading_framework.models import BUY, SELL, HOLD, PriceBar, Signal
from trading_framework.signals.confidence import score_signals
from trading_framework.signals.aggregator import SignalAggregator, AggregatedSignal
from trading_framework.signals.router import NotificationRouter


def _signal(symbol="AAPL", action=BUY, strategy="sma", price=150.0):
    return Signal(
        symbol=symbol, action=action, price=price,
        timestamp=datetime(2026, 5, 1, 14, 0, tzinfo=timezone.utc),
        reason="test", strategy_name=strategy, details={},
    )


def _bars(symbol="AAPL", count=5, volume=10000):
    return [
        PriceBar(symbol=symbol, timestamp=datetime(2026, 5, 1, 14, 0, tzinfo=timezone.utc),
                 open=150, high=155, low=148, close=150, volume=volume)
        for _ in range(count)
    ]


# ---------------------------------------------------------------------------
# Confidence Scoring
# ---------------------------------------------------------------------------

class ConfidenceTests(unittest.TestCase):
    def test_single_strategy_low_confidence(self):
        signals = [_signal(strategy="sma")]
        scored = score_signals(signals, _bars(), total_strategies=6)
        self.assertEqual(1, len(scored))
        self.assertEqual(Confidence.LOW, scored[0]["confidence"])
        self.assertEqual(1, scored[0]["agreeing"])

    def test_three_of_six_high_confidence(self):
        signals = [
            _signal(strategy="sma"),
            _signal(strategy="rsi"),
            _signal(strategy="macd"),
        ]
        scored = score_signals(signals, _bars(), total_strategies=6)
        self.assertEqual(1, len(scored))  # all same symbol+action
        self.assertEqual(Confidence.HIGH, scored[0]["confidence"])
        self.assertEqual(3, scored[0]["agreeing"])

    def test_two_of_six_medium_confidence(self):
        signals = [_signal(strategy="sma"), _signal(strategy="rsi")]
        scored = score_signals(signals, _bars(), total_strategies=6)
        self.assertEqual(Confidence.MEDIUM, scored[0]["confidence"])

    def test_different_actions_scored_separately(self):
        signals = [
            _signal(symbol="AAPL", action=BUY, strategy="sma"),
            _signal(symbol="AAPL", action=SELL, strategy="rsi"),
        ]
        scored = score_signals(signals, _bars(), total_strategies=6)
        self.assertEqual(2, len(scored))

    def test_different_symbols_scored_separately(self):
        signals = [
            _signal(symbol="AAPL", strategy="sma"),
            _signal(symbol="MSFT", strategy="sma"),
        ]
        scored = score_signals(signals, _bars(), total_strategies=6)
        self.assertEqual(2, len(scored))

    def test_empty_signals_returns_empty(self):
        self.assertEqual([], score_signals([], _bars(), total_strategies=6))

    def test_sorted_by_score_descending(self):
        signals = [
            _signal(symbol="AAPL", strategy="sma"),
            _signal(symbol="AAPL", strategy="rsi"),
            _signal(symbol="AAPL", strategy="macd"),
            _signal(symbol="MSFT", strategy="sma"),
        ]
        scored = score_signals(signals, _bars(), total_strategies=6)
        scores = [s["score"] for s in scored]
        self.assertEqual(sorted(scores, reverse=True), scores)

    def test_strategies_list_captured(self):
        signals = [_signal(strategy="sma"), _signal(strategy="rsi")]
        scored = score_signals(signals, _bars(), total_strategies=4)
        self.assertIn("sma", scored[0]["strategies"])
        self.assertIn("rsi", scored[0]["strategies"])


# ---------------------------------------------------------------------------
# Signal Aggregator
# ---------------------------------------------------------------------------

class AggregatorTests(unittest.TestCase):
    def test_aggregator_collects_and_scores_on_cycle_end(self):
        bus = EventBus()
        received = []
        aggregator = SignalAggregator(
            event_bus=bus,
            total_strategies=4,
            on_aggregated=lambda agg: received.append(agg),
        )

        # Simulate signals during a cycle
        bars = _bars()
        bus.publish(SignalEmitted(signal=_signal(strategy="sma"), bars=bars))
        bus.publish(SignalEmitted(signal=_signal(strategy="rsi"), bars=bars))

        # Nothing scored yet
        self.assertEqual(0, len(received))

        # Cycle ends -> scoring happens
        bus.publish(CycleCompleted(
            timestamp=datetime.now(timezone.utc),
            signals_emitted=2, holds=0, errors=0, elapsed_seconds=0.1,
        ))

        self.assertEqual(1, len(received))
        self.assertIsInstance(received[0], AggregatedSignal)
        self.assertEqual(2, len(received[0].agreeing_strategies))
        self.assertEqual(Confidence.HIGH, received[0].confidence)

    def test_aggregator_resets_after_cycle(self):
        bus = EventBus()
        received = []
        aggregator = SignalAggregator(
            event_bus=bus, total_strategies=2,
            on_aggregated=lambda agg: received.append(agg),
        )

        # Cycle 1
        bus.publish(SignalEmitted(signal=_signal(strategy="sma"), bars=_bars()))
        bus.publish(CycleCompleted(timestamp=datetime.now(timezone.utc),
                                   signals_emitted=1, holds=0, errors=0, elapsed_seconds=0.1))

        # Cycle 2 (no signals)
        bus.publish(CycleCompleted(timestamp=datetime.now(timezone.utc),
                                   signals_emitted=0, holds=0, errors=0, elapsed_seconds=0.1))

        # Only 1 aggregated signal from cycle 1
        self.assertEqual(1, len(received))

    def test_last_aggregated_accessible(self):
        bus = EventBus()
        aggregator = SignalAggregator(event_bus=bus, total_strategies=2)

        bus.publish(SignalEmitted(signal=_signal(strategy="sma"), bars=_bars()))
        bus.publish(CycleCompleted(timestamp=datetime.now(timezone.utc),
                                   signals_emitted=1, holds=0, errors=0, elapsed_seconds=0.1))

        self.assertEqual(1, len(aggregator.last_aggregated))


# ---------------------------------------------------------------------------
# Notification Router
# ---------------------------------------------------------------------------

class RouterTests(unittest.TestCase):
    def _agg(self, confidence=Confidence.HIGH):
        return AggregatedSignal(
            signal=_signal(),
            confidence=confidence,
            score=0.8,
            agreeing_strategies=["sma", "rsi"],
            total_strategies=6,
        )

    def test_high_confidence_reaches_all_channels(self):
        router = NotificationRouter()
        received = {"high": [], "low": []}
        router.add_channel("high_only", lambda a: received["high"].append(a), Confidence.HIGH)
        router.add_channel("all", lambda a: received["low"].append(a), Confidence.LOW)

        router.route(self._agg(Confidence.HIGH))
        self.assertEqual(1, len(received["high"]))
        self.assertEqual(1, len(received["low"]))

    def test_low_confidence_skips_high_channel(self):
        router = NotificationRouter()
        received = {"high": [], "low": []}
        router.add_channel("high_only", lambda a: received["high"].append(a), Confidence.HIGH)
        router.add_channel("all", lambda a: received["low"].append(a), Confidence.LOW)

        router.route(self._agg(Confidence.LOW))
        self.assertEqual(0, len(received["high"]))  # skipped
        self.assertEqual(1, len(received["low"]))    # received

    def test_medium_confidence_routing(self):
        router = NotificationRouter()
        results = []
        router.add_channel("high", lambda a: results.append("high"), Confidence.HIGH)
        router.add_channel("medium", lambda a: results.append("medium"), Confidence.MEDIUM)
        router.add_channel("low", lambda a: results.append("low"), Confidence.LOW)

        router.route(self._agg(Confidence.MEDIUM))
        self.assertNotIn("high", results)
        self.assertIn("medium", results)
        self.assertIn("low", results)

    def test_route_returns_channel_names(self):
        router = NotificationRouter()
        router.add_channel("console", lambda a: None, Confidence.LOW)
        router.add_channel("telegram", lambda a: None, Confidence.HIGH)

        routed = router.route(self._agg(Confidence.HIGH))
        self.assertIn("console", routed)
        self.assertIn("telegram", routed)

    def test_channel_error_does_not_stop_others(self):
        router = NotificationRouter()
        results = []

        def bad_handler(a):
            raise RuntimeError("fail")

        router.add_channel("bad", bad_handler, Confidence.LOW)
        router.add_channel("good", lambda a: results.append("ok"), Confidence.LOW)

        router.route(self._agg(Confidence.HIGH))
        self.assertEqual(["ok"], results)

    def test_stats(self):
        router = NotificationRouter()
        router.add_channel("a", lambda a: None, Confidence.LOW)
        router.add_channel("b", lambda a: None, Confidence.HIGH)
        router.route(self._agg(Confidence.HIGH))
        stats = router.stats
        self.assertEqual(2, stats["channels"])
        self.assertEqual(1, stats["total_routed"])


# ---------------------------------------------------------------------------
# Telegram notifier (unit test with mocked HTTP)
# ---------------------------------------------------------------------------

class TelegramNotifierTests(unittest.TestCase):
    def test_missing_token_raises(self):
        from trading_framework.signals.notifiers.telegram import TelegramNotifier
        with self.assertRaises(ValueError):
            TelegramNotifier(bot_token="", chat_id="123")

    def test_missing_chat_id_raises(self):
        from trading_framework.signals.notifiers.telegram import TelegramNotifier
        with self.assertRaises(ValueError):
            TelegramNotifier(bot_token="token", chat_id="")

    def test_instantiation_with_valid_params(self):
        from trading_framework.signals.notifiers.telegram import TelegramNotifier
        notifier = TelegramNotifier(bot_token="123:ABC", chat_id="-100123")
        self.assertEqual("123:ABC", notifier.bot_token)
        self.assertEqual("-100123", notifier.chat_id)


if __name__ == "__main__":
    unittest.main()
