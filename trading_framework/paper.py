from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import BUY, SELL, Signal


@dataclass
class Position:
    symbol: str
    side: str               # "long" or "short"
    entry_price: float
    quantity: float
    entry_timestamp: datetime
    strategy_name: str


@dataclass
class OrderRecord:
    symbol: str
    action: str             # BUY or SELL
    price: float
    quantity: float
    timestamp: datetime
    strategy_name: str
    pnl: float | None       # P&L if closing a position, None if opening


@dataclass
class PaperPortfolio:
    """Simulated portfolio tracking positions, cash, and trade history."""

    starting_cash: float = 100_000.0
    cash: float = 100_000.0
    positions: Dict[str, Position] = field(default_factory=dict)
    orders: List[OrderRecord] = field(default_factory=list)
    position_size_pct: float = 10.0  # % of portfolio per trade

    def execute(self, signal: Signal) -> OrderRecord | None:
        """Execute a signal against the portfolio. Returns OrderRecord or None if rejected."""
        symbol = signal.symbol
        current_position = self.positions.get(symbol)

        if signal.action == BUY:
            if current_position and current_position.side == "long":
                return None  # Already long, skip

            if current_position and current_position.side == "short":
                # Close short position
                return self._close_position(signal)

            # Open long position
            return self._open_position(signal, "long")

        elif signal.action == SELL:
            if current_position and current_position.side == "short":
                return None  # Already short, skip

            if current_position and current_position.side == "long":
                # Close long position
                return self._close_position(signal)

            # Open short position
            return self._open_position(signal, "short")

        return None

    def _open_position(self, signal: Signal, side: str) -> OrderRecord | None:
        # Calculate position size
        portfolio_value = self.total_equity(signal.price)
        trade_value = portfolio_value * (self.position_size_pct / 100)
        quantity = trade_value / signal.price

        if quantity <= 0 or trade_value > self.cash:
            return None  # Not enough cash

        self.cash -= trade_value
        self.positions[signal.symbol] = Position(
            symbol=signal.symbol,
            side=side,
            entry_price=signal.price,
            quantity=quantity,
            entry_timestamp=signal.timestamp,
            strategy_name=signal.strategy_name,
        )

        order = OrderRecord(
            symbol=signal.symbol,
            action=signal.action,
            price=signal.price,
            quantity=quantity,
            timestamp=signal.timestamp,
            strategy_name=signal.strategy_name,
            pnl=None,
        )
        self.orders.append(order)
        return order

    def _close_position(self, signal: Signal) -> OrderRecord:
        pos = self.positions.pop(signal.symbol)

        if pos.side == "long":
            pnl = (signal.price - pos.entry_price) * pos.quantity
        else:  # short
            pnl = (pos.entry_price - signal.price) * pos.quantity

        # Return cash: original investment + P&L
        self.cash += (pos.entry_price * pos.quantity) + pnl

        order = OrderRecord(
            symbol=signal.symbol,
            action=signal.action,
            price=signal.price,
            quantity=pos.quantity,
            timestamp=signal.timestamp,
            strategy_name=signal.strategy_name,
            pnl=round(pnl, 2),
        )
        self.orders.append(order)
        return order

    def total_equity(self, current_price: float | None = None) -> float:
        """Total portfolio value = cash + position values."""
        equity = self.cash
        for pos in self.positions.values():
            price = current_price if current_price else pos.entry_price
            if pos.side == "long":
                equity += price * pos.quantity
            else:
                # Short: value = entry_value + (entry_price - current_price) * qty
                equity += pos.entry_price * pos.quantity + (pos.entry_price - price) * pos.quantity
        return round(equity, 2)

    def realized_pnl(self) -> float:
        """Sum of all closed trade P&Ls."""
        return round(sum(o.pnl for o in self.orders if o.pnl is not None), 2)

    def summary(self, current_prices: Dict[str, float] | None = None) -> str:
        """Human-readable portfolio summary."""
        lines = [
            "",
            "=" * 60,
            "  Paper Trading Portfolio",
            "=" * 60,
            f"  Starting cash:    ${self.starting_cash:,.2f}",
            f"  Current cash:     ${self.cash:,.2f}",
            f"  Realized P&L:     ${self.realized_pnl():,.2f}",
            f"  Total orders:     {len(self.orders)}",
        ]

        if self.positions:
            lines.append("-" * 60)
            lines.append("  Open Positions:")
            lines.append(f"  {'Symbol':<10} {'Side':<6} {'Entry $':>10} {'Qty':>10} {'Strategy':<20}")
            for pos in self.positions.values():
                lines.append(
                    f"  {pos.symbol:<10} {pos.side:<6} {pos.entry_price:>10.2f} "
                    f"{pos.quantity:>10.4f} {pos.strategy_name:<20}"
                )
        else:
            lines.append("  Open positions:   None")

        if self.orders:
            lines.append("-" * 60)
            lines.append("  Recent Orders (last 10):")
            lines.append(f"  {'Time':<12} {'Symbol':<8} {'Action':<5} {'Price':>9} {'Qty':>10} {'P&L':>10}")
            for order in self.orders[-10:]:
                pnl_str = f"${order.pnl:,.2f}" if order.pnl is not None else "—"
                lines.append(
                    f"  {order.timestamp.strftime('%Y-%m-%d'):<12} {order.symbol:<8} "
                    f"{order.action:<5} {order.price:>9.2f} {order.quantity:>10.4f} {pnl_str:>10}"
                )

        lines.append("=" * 60)
        return "\n".join(lines)

    def save(self, path: str) -> None:
        """Save portfolio state to JSON file."""
        data = {
            "starting_cash": self.starting_cash,
            "cash": self.cash,
            "position_size_pct": self.position_size_pct,
            "positions": {
                sym: {
                    "side": p.side, "entry_price": p.entry_price,
                    "quantity": p.quantity, "entry_timestamp": p.entry_timestamp.isoformat(),
                    "strategy_name": p.strategy_name,
                }
                for sym, p in self.positions.items()
            },
            "orders": [
                {
                    "symbol": o.symbol, "action": o.action, "price": o.price,
                    "quantity": o.quantity, "timestamp": o.timestamp.isoformat(),
                    "strategy_name": o.strategy_name, "pnl": o.pnl,
                }
                for o in self.orders
            ],
        }
        Path(path).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: str) -> PaperPortfolio:
        """Load portfolio state from JSON file."""
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        portfolio = cls(
            starting_cash=raw["starting_cash"],
            cash=raw["cash"],
            position_size_pct=raw.get("position_size_pct", 10.0),
        )
        for sym, p in raw.get("positions", {}).items():
            portfolio.positions[sym] = Position(
                symbol=sym, side=p["side"], entry_price=p["entry_price"],
                quantity=p["quantity"],
                entry_timestamp=datetime.fromisoformat(p["entry_timestamp"]),
                strategy_name=p["strategy_name"],
            )
        for o in raw.get("orders", []):
            portfolio.orders.append(OrderRecord(
                symbol=o["symbol"], action=o["action"], price=o["price"],
                quantity=o["quantity"],
                timestamp=datetime.fromisoformat(o["timestamp"]),
                strategy_name=o["strategy_name"], pnl=o.get("pnl"),
            ))
        return portfolio
