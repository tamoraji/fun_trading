import json
import unittest

from trading_framework.structlog import StructuredLogger


class StructuredLoggerTests(unittest.TestCase):
    def setUp(self):
        self.lines = []
        self.logger = StructuredLogger(sink=self.lines.append)

    def test_cycle_start_emits_json(self):
        self.logger.cycle_start(symbols=["AAPL", "MSFT"])

        self.assertEqual(1, len(self.lines))
        record = json.loads(self.lines[0])
        self.assertEqual("cycle_start", record["event"])
        self.assertEqual(["AAPL", "MSFT"], record["symbols"])
        self.assertEqual(2, record["symbol_count"])
        self.assertIn("timestamp", record)

    def test_cycle_end_emits_json_with_summary(self):
        self.logger.cycle_end(
            signals_emitted=2,
            holds=1,
            errors=0,
            elapsed_seconds=1.234,
        )

        record = json.loads(self.lines[0])
        self.assertEqual("cycle_end", record["event"])
        self.assertEqual(2, record["signals_emitted"])
        self.assertEqual(1, record["holds"])
        self.assertEqual(0, record["errors"])
        self.assertAlmostEqual(1.234, record["elapsed_seconds"], places=3)

    def test_signal_emitted_event(self):
        self.logger.signal_emitted(symbol="AAPL", action="BUY", price=150.0, strategy="rsi")

        record = json.loads(self.lines[0])
        self.assertEqual("signal_emitted", record["event"])
        self.assertEqual("AAPL", record["symbol"])
        self.assertEqual("BUY", record["action"])
        self.assertAlmostEqual(150.0, record["price"])
        self.assertEqual("rsi", record["strategy"])

    def test_error_event(self):
        self.logger.error(symbol="AAPL", message="connection timeout")

        record = json.loads(self.lines[0])
        self.assertEqual("error", record["event"])
        self.assertEqual("AAPL", record["symbol"])
        self.assertEqual("connection timeout", record["message"])

    def test_skip_event(self):
        self.logger.skip(reason="market session is closed")

        record = json.loads(self.lines[0])
        self.assertEqual("skip", record["event"])
        self.assertEqual("market session is closed", record["reason"])

    def test_log_passes_through_to_old_logger_interface(self):
        self.logger.log("[hold] AAPL: no crossover")

        record = json.loads(self.lines[0])
        self.assertEqual("log", record["event"])
        self.assertEqual("[hold] AAPL: no crossover", record["message"])

    def test_callable_interface_calls_log(self):
        # The logger should be callable so it can replace the old print-based logger
        self.logger("[hold] AAPL: test")

        record = json.loads(self.lines[0])
        self.assertEqual("log", record["event"])


if __name__ == "__main__":
    unittest.main()
