import unittest
from unittest.mock import patch

from trading_framework.prettylog import PrettyLogger


class PrettyLoggerTests(unittest.TestCase):
    def setUp(self):
        self.output = []
        self.patcher = patch("builtins.print", side_effect=lambda msg="": self.output.append(msg))
        self.patcher.start()
        self.logger = PrettyLogger()

    def tearDown(self):
        self.patcher.stop()

    def test_cycle_start(self):
        self.logger("[cycle_start] symbols=['AAPL', 'MSFT']")
        self.assertEqual(1, len(self.output))
        self.assertIn("Polling", self.output[0])
        self.assertIn("AAPL", self.output[0])

    def test_cycle_end(self):
        self.logger("[cycle_end] signals=1 holds=2 errors=0 elapsed=0.500s")
        self.assertEqual(1, len(self.output))
        self.assertIn("1 signal(s)", self.output[0])
        self.assertIn("2 hold(s)", self.output[0])
        self.assertIn("0.500s", self.output[0])

    def test_signal(self):
        self.logger("[signal] AAPL: BUY at 189.50")
        self.assertIn("SIGNAL", self.output[0])
        self.assertIn("AAPL", self.output[0])

    def test_hold(self):
        self.logger("[hold] AAPL: No crossover on the latest bar.")
        self.assertIn("AAPL", self.output[0])
        self.assertNotIn("[hold]", self.output[0])

    def test_error(self):
        self.logger("[error] AAPL: connection timeout")
        self.assertIn("ERROR", self.output[0])
        self.assertIn("connection timeout", self.output[0])

    def test_skip(self):
        self.logger("[skip] market session is closed")
        self.assertIn("Skipped", self.output[0])

    def test_dup(self):
        self.logger("[dup] AAPL: already sent BUY for this bar")
        self.assertIn("duplicate", self.output[0])


if __name__ == "__main__":
    unittest.main()
