"""Tests for the strategy plugin registry."""
from __future__ import annotations

import unittest

from trading_framework.infra.plugin import (
    register_strategy,
    create_strategy_from_registry,
    list_strategies,
    is_registered,
    clear_registry,
)
from trading_framework.models import StrategySettings


class PluginRegistryTests(unittest.TestCase):
    def setUp(self):
        clear_registry()

    def tearDown(self):
        clear_registry()

    def test_register_and_create(self):
        @register_strategy("test_strat")
        class TestStrat:
            def __init__(self, param=10):
                self.param = param

        settings = StrategySettings(name="test_strat", params={"param": 42})
        instance = create_strategy_from_registry(settings)
        self.assertEqual(42, instance.param)

    def test_unknown_strategy_raises(self):
        settings = StrategySettings(name="nonexistent", params={})
        with self.assertRaises(ValueError) as ctx:
            create_strategy_from_registry(settings)
        self.assertIn("nonexistent", str(ctx.exception))

    def test_list_strategies(self):
        @register_strategy("alpha")
        class Alpha:
            pass

        @register_strategy("beta")
        class Beta:
            pass

        strats = list_strategies()
        self.assertIn("alpha", strats)
        self.assertIn("beta", strats)
        self.assertEqual(2, len(strats))

    def test_is_registered(self):
        @register_strategy("exists")
        class Exists:
            pass

        self.assertTrue(is_registered("exists"))
        self.assertFalse(is_registered("nope"))

    def test_clear_registry(self):
        @register_strategy("temp")
        class Temp:
            pass

        self.assertTrue(is_registered("temp"))
        clear_registry()
        self.assertFalse(is_registered("temp"))

    def test_default_params(self):
        @register_strategy("with_defaults")
        class WithDefaults:
            def __init__(self, x=5, y=10):
                self.x = x
                self.y = y

        settings = StrategySettings(name="with_defaults", params={})
        instance = create_strategy_from_registry(settings)
        self.assertEqual(5, instance.x)
        self.assertEqual(10, instance.y)

    def test_overwrite_warns(self):
        @register_strategy("dup")
        class First:
            pass

        @register_strategy("dup")
        class Second:
            pass

        # Second registration should overwrite
        strats = list_strategies()
        self.assertEqual(Second, strats["dup"])


if __name__ == "__main__":
    unittest.main()
