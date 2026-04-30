from __future__ import annotations

import tempfile
from datetime import datetime, timezone

from trading_framework.models import BUY, SELL, Signal
from trading_framework.paper import PaperPortfolio


def _signal(symbol="AAPL", action=BUY, price=150.0, timestamp=None):
    return Signal(
        symbol=symbol,
        action=action,
        price=price,
        timestamp=timestamp or datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        reason="test",
        strategy_name="test",
        details={},
    )


# --- Opening/closing positions ---


def test_buy_opens_long_position():
    p = PaperPortfolio()
    order = p.execute(_signal(action=BUY))
    assert order is not None
    assert "AAPL" in p.positions
    assert p.positions["AAPL"].side == "long"
    assert order.pnl is None


def test_sell_opens_short_position():
    p = PaperPortfolio()
    order = p.execute(_signal(action=SELL))
    assert order is not None
    assert "AAPL" in p.positions
    assert p.positions["AAPL"].side == "short"
    assert order.pnl is None


def test_buy_then_sell_closes_long():
    p = PaperPortfolio()
    p.execute(_signal(action=BUY, price=100.0))
    order = p.execute(_signal(action=SELL, price=110.0))
    assert order is not None
    assert order.pnl is not None
    assert order.pnl > 0
    assert "AAPL" not in p.positions


def test_sell_then_buy_closes_short():
    p = PaperPortfolio()
    p.execute(_signal(action=SELL, price=100.0))
    order = p.execute(_signal(action=BUY, price=90.0))
    assert order is not None
    assert order.pnl is not None
    assert order.pnl > 0
    assert "AAPL" not in p.positions


def test_duplicate_buy_rejected():
    p = PaperPortfolio()
    p.execute(_signal(action=BUY))
    order = p.execute(_signal(action=BUY))
    assert order is None


def test_duplicate_sell_rejected():
    p = PaperPortfolio()
    p.execute(_signal(action=SELL))
    order = p.execute(_signal(action=SELL))
    assert order is None


# --- P&L ---


def test_profitable_long_trade():
    p = PaperPortfolio()
    p.execute(_signal(action=BUY, price=100.0))
    order = p.execute(_signal(action=SELL, price=120.0))
    assert order is not None
    assert order.pnl is not None
    assert order.pnl > 0


def test_losing_long_trade():
    p = PaperPortfolio()
    p.execute(_signal(action=BUY, price=100.0))
    order = p.execute(_signal(action=SELL, price=80.0))
    assert order is not None
    assert order.pnl is not None
    assert order.pnl < 0


def test_profitable_short_trade():
    p = PaperPortfolio()
    p.execute(_signal(action=SELL, price=100.0))
    order = p.execute(_signal(action=BUY, price=80.0))
    assert order is not None
    assert order.pnl is not None
    assert order.pnl > 0


# --- Portfolio ---


def test_starting_equity():
    p = PaperPortfolio(starting_cash=50_000.0, cash=50_000.0)
    assert p.total_equity() == 50_000.0


def test_cash_decreases_on_open():
    p = PaperPortfolio()
    initial_cash = p.cash
    p.execute(_signal(action=BUY, price=150.0))
    assert p.cash < initial_cash


def test_cash_returns_on_close():
    p = PaperPortfolio()
    p.execute(_signal(action=BUY, price=100.0))
    cash_after_open = p.cash
    p.execute(_signal(action=SELL, price=100.0))
    # Cash should return to approximately starting value (same price, no P&L)
    assert p.cash > cash_after_open


def test_realized_pnl_sums_correctly():
    p = PaperPortfolio()
    # Trade 1: long AAPL
    p.execute(_signal(symbol="AAPL", action=BUY, price=100.0))
    p.execute(_signal(symbol="AAPL", action=SELL, price=110.0))
    # Trade 2: long GOOG
    p.execute(_signal(symbol="GOOG", action=BUY, price=200.0))
    p.execute(_signal(symbol="GOOG", action=SELL, price=210.0))
    pnl = p.realized_pnl()
    assert pnl > 0
    # Should be sum of both trades' P&L
    trade_pnls = [o.pnl for o in p.orders if o.pnl is not None]
    assert len(trade_pnls) == 2
    assert pnl == round(sum(trade_pnls), 2)


def test_position_size_percentage():
    p = PaperPortfolio(position_size_pct=20.0)
    p.execute(_signal(action=BUY, price=100.0))
    pos = p.positions["AAPL"]
    expected_value = 100_000.0 * 0.20  # 20% of portfolio
    actual_value = pos.quantity * pos.entry_price
    assert abs(actual_value - expected_value) < 0.01


# --- Persistence ---


def test_save_and_load():
    p = PaperPortfolio(starting_cash=50_000.0, cash=50_000.0, position_size_pct=15.0)
    p.execute(_signal(action=BUY, price=100.0))

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name

    p.save(path)
    loaded = PaperPortfolio.load(path)

    assert loaded.starting_cash == p.starting_cash
    assert loaded.cash == p.cash
    assert loaded.position_size_pct == p.position_size_pct
    assert len(loaded.positions) == len(p.positions)
    assert "AAPL" in loaded.positions
    assert loaded.positions["AAPL"].side == p.positions["AAPL"].side
    assert loaded.positions["AAPL"].entry_price == p.positions["AAPL"].entry_price
    assert loaded.positions["AAPL"].quantity == p.positions["AAPL"].quantity
    assert len(loaded.orders) == len(p.orders)


# --- Summary ---


def test_summary_contains_key_sections():
    p = PaperPortfolio()
    p.execute(_signal(action=BUY, price=150.0))
    text = p.summary()
    assert "Paper Trading Portfolio" in text
    assert "Starting cash" in text
    assert "Current cash" in text
    assert "Open Positions" in text
    assert "AAPL" in text
