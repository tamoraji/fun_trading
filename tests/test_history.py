import json
import os
import tempfile
import unittest
from datetime import datetime, timezone

from trading_framework.history import JsonLinesHistory, NullHistory, create_signal_history
from trading_framework.models import BUY, SELL, Signal, SignalHistorySettings


def _make_signal(symbol="AAPL", action=BUY, price=150.0):
    return Signal(
        symbol=symbol,
        action=action,
        price=price,
        timestamp=datetime(2026, 4, 29, 14, 30, tzinfo=timezone.utc),
        reason="test reason",
        strategy_name="test_strategy",
        details={"key": "value"},
    )


class JsonLinesHistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        )
        self.tmp.close()
        self.path = self.tmp.name

    def tearDown(self):
        os.unlink(self.path)

    def test_write_and_read_single_signal(self):
        history = JsonLinesHistory(self.path)
        signal = _make_signal()

        history.write(signal)

        records = history.read_all()
        self.assertEqual(1, len(records))
        self.assertEqual("AAPL", records[0]["symbol"])
        self.assertEqual("BUY", records[0]["action"])
        self.assertAlmostEqual(150.0, records[0]["price"])
        self.assertEqual("test reason", records[0]["reason"])
        self.assertEqual("test_strategy", records[0]["strategy_name"])
        self.assertEqual({"key": "value"}, records[0]["details"])

    def test_write_multiple_signals_appends(self):
        history = JsonLinesHistory(self.path)

        history.write(_make_signal(symbol="AAPL", action=BUY))
        history.write(_make_signal(symbol="MSFT", action=SELL))

        records = history.read_all()
        self.assertEqual(2, len(records))
        self.assertEqual("AAPL", records[0]["symbol"])
        self.assertEqual("MSFT", records[1]["symbol"])

    def test_read_all_returns_empty_for_nonexistent_file(self):
        history = JsonLinesHistory("/tmp/does_not_exist_test_history.jsonl")
        records = history.read_all()
        self.assertEqual([], records)

    def test_history_survives_process_restart(self):
        history1 = JsonLinesHistory(self.path)
        history1.write(_make_signal())

        # Simulate process restart by creating new instance
        history2 = JsonLinesHistory(self.path)
        records = history2.read_all()
        self.assertEqual(1, len(records))

    def test_each_line_is_valid_json(self):
        history = JsonLinesHistory(self.path)
        history.write(_make_signal(symbol="AAPL"))
        history.write(_make_signal(symbol="MSFT"))

        with open(self.path, "r") as f:
            lines = [line.strip() for line in f if line.strip()]

        self.assertEqual(2, len(lines))
        for line in lines:
            parsed = json.loads(line)
            self.assertIn("symbol", parsed)
            self.assertIn("timestamp", parsed)


class NullHistoryTests(unittest.TestCase):
    def test_write_does_nothing(self):
        history = NullHistory()
        history.write(_make_signal())
        self.assertEqual([], history.read_all())


class CreateSignalHistoryTests(unittest.TestCase):
    def test_returns_null_history_when_none(self):
        history = create_signal_history(None)
        self.assertIsInstance(history, NullHistory)

    def test_returns_null_history_when_disabled(self):
        settings = SignalHistorySettings(enabled=False)
        history = create_signal_history(settings)
        self.assertIsInstance(history, NullHistory)

    def test_returns_jsonlines_when_enabled(self):
        settings = SignalHistorySettings(enabled=True, path="/tmp/test.jsonl")
        history = create_signal_history(settings)
        self.assertIsInstance(history, JsonLinesHistory)


if __name__ == "__main__":
    unittest.main()
