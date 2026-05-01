from datetime import datetime, time, timezone
import unittest

from trading_framework.data import MarketDataProvider
from trading_framework.engine import TradingEngine
from trading_framework.history import SignalHistory
from trading_framework.models import (
    AppSettings,
    MarketDataConfig,
    MarketSession,
    NotifierSettings,
    StrategySettings,
)
from trading_framework.notifiers import Notifier
from trading_framework.strategy import MovingAverageCrossoverStrategy

from tests.test_strategy import build_bars


class FakeProvider(MarketDataProvider):
    def __init__(self, bars_by_symbol):
        self.bars_by_symbol = bars_by_symbol
        self.calls = 0

    def fetch_bars(self, symbol, config):
        self.calls += 1
        return self.bars_by_symbol[symbol]


class RecordingHistory(SignalHistory):
    def __init__(self):
        self.signals = []

    def write(self, signal):
        self.signals.append(signal)

    def read_all(self):
        return self.signals


class RecordingNotifier(Notifier):
    def __init__(self):
        self.signals = []

    def send(self, signal):
        self.signals.append(signal)


class TradingEngineTests(unittest.TestCase):
    def _settings(self, market_session=None):
        return AppSettings(
            symbols=["AAPL"],
            poll_interval_seconds=60,
            market_data=MarketDataConfig(),
            strategy=StrategySettings(
                name="moving_average_crossover",
                params={"short_window": 3, "long_window": 5},
            ),
            notifiers=[NotifierSettings(type="console")],
            market_session=market_session,
        )

    def test_engine_emits_once_per_bar(self):
        provider = FakeProvider({"AAPL": build_bars("AAPL", [12, 12, 12, 12, 12, 10, 9, 8, 9, 12])})
        notifier = RecordingNotifier()
        engine = TradingEngine(
            settings=self._settings(),
            provider=provider,
            strategy=MovingAverageCrossoverStrategy(short_window=3, long_window=5),
            notifiers=[notifier],
            logger=lambda _: None,
        )

        first_cycle = engine.run_cycle()
        second_cycle = engine.run_cycle()

        self.assertEqual(1, len(first_cycle))
        self.assertEqual(0, len(second_cycle))
        self.assertEqual(1, len(notifier.signals))

    def test_engine_skips_work_outside_market_session(self):
        market_session = MarketSession(
            timezone_name="America/New_York",
            weekdays=[0, 1, 2, 3, 4],
            start=time(9, 30),
            end=time(16, 0),
        )
        provider = FakeProvider({"AAPL": build_bars("AAPL", [12, 12, 12, 12, 12, 10, 9, 8, 9, 12])})
        notifier = RecordingNotifier()
        engine = TradingEngine(
            settings=self._settings(market_session=market_session),
            provider=provider,
            strategy=MovingAverageCrossoverStrategy(short_window=3, long_window=5),
            notifiers=[notifier],
            logger=lambda _: None,
        )

        signals = engine.run_cycle(now=datetime(2026, 3, 23, 21, 30, tzinfo=timezone.utc))

        self.assertEqual([], signals)
        self.assertEqual(0, provider.calls)
        self.assertEqual([], notifier.signals)


    def test_engine_writes_emitted_signals_to_history(self):
        provider = FakeProvider({"AAPL": build_bars("AAPL", [12, 12, 12, 12, 12, 10, 9, 8, 9, 12])})
        notifier = RecordingNotifier()
        history = RecordingHistory()
        engine = TradingEngine(
            settings=self._settings(),
            provider=provider,
            strategy=MovingAverageCrossoverStrategy(short_window=3, long_window=5),
            notifiers=[notifier],
            history=history,
            logger=lambda _: None,
        )

        engine.run_cycle()

        self.assertEqual(1, len(history.signals))
        self.assertEqual("AAPL", history.signals[0].symbol)


    def test_engine_publishes_events_to_bus(self):
        from trading_framework.core.events import SignalEmitted, CycleStarted, CycleCompleted

        provider = FakeProvider({"AAPL": build_bars("AAPL", [12, 12, 12, 12, 12, 10, 9, 8, 9, 12])})
        engine = TradingEngine(
            settings=self._settings(),
            provider=provider,
            strategy=MovingAverageCrossoverStrategy(short_window=3, long_window=5),
            notifiers=[],
            logger=lambda _: None,
        )

        events_received = []
        engine.event_bus.subscribe(CycleStarted, lambda e: events_received.append(("cycle_start", e)))
        engine.event_bus.subscribe(SignalEmitted, lambda e: events_received.append(("signal", e)))
        engine.event_bus.subscribe(CycleCompleted, lambda e: events_received.append(("cycle_end", e)))

        engine.run_cycle()

        event_types = [t for t, _ in events_received]
        self.assertIn("cycle_start", event_types)
        self.assertIn("signal", event_types)
        self.assertIn("cycle_end", event_types)

        # Verify signal event has correct data
        signal_event = next(e for t, e in events_received if t == "signal")
        self.assertEqual("AAPL", signal_event.signal.symbol)
        self.assertEqual("BUY", signal_event.signal.action)


if __name__ == "__main__":
    unittest.main()
