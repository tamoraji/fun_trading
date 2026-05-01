"""Transaction cost modeling for backtests.

Models slippage and commissions to make backtest results more realistic.

Usage:
    from trading_framework.analytics.costs import apply_costs, CostModel

    model = CostModel(slippage_pct=0.1, commission_per_trade=1.0)
    adjusted_trades = apply_costs(trades, model)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..backtest import Trade


@dataclass(frozen=True)
class CostModel:
    """Transaction cost model.

    Args:
        slippage_pct: Slippage as % of price. Worsens entry/exit by this amount.
            E.g., 0.1 = 0.1% slippage (BUY at higher price, SELL at lower).
        commission_per_trade: Fixed commission per round-trip trade in dollars.
        commission_pct: Commission as % of trade value (alternative to fixed).
    """
    slippage_pct: float = 0.1
    commission_per_trade: float = 0.0
    commission_pct: float = 0.0


def apply_costs(trades: List[Trade], model: CostModel) -> List[Trade]:
    """Apply slippage and commission to a list of trades.

    Returns new Trade objects with adjusted profit_pct values.

    Args:
        trades: Original trades from backtest.
        model: Cost model parameters.

    Returns:
        New list of Trades with adjusted P&L.
    """
    adjusted = []
    for t in trades:
        # Slippage: worsen entry and exit prices
        slippage_factor = model.slippage_pct / 100.0
        if t.entry_action == "BUY":
            adj_entry = t.entry_price * (1 + slippage_factor)
            adj_exit = t.exit_price * (1 - slippage_factor)
            raw_pnl_pct = (adj_exit - adj_entry) / adj_entry * 100
        else:  # SELL (short)
            adj_entry = t.entry_price * (1 - slippage_factor)
            adj_exit = t.exit_price * (1 + slippage_factor)
            raw_pnl_pct = (adj_entry - adj_exit) / adj_entry * 100

        # Commission
        trade_value = t.entry_price  # approximate
        commission_cost = model.commission_per_trade + (trade_value * model.commission_pct / 100.0)
        commission_pct = (commission_cost / trade_value) * 100 if trade_value > 0 else 0

        adjusted_pnl = round(raw_pnl_pct - commission_pct, 4)

        adjusted.append(Trade(
            symbol=t.symbol,
            strategy_name=t.strategy_name,
            entry_action=t.entry_action,
            entry_price=t.entry_price,
            entry_timestamp=t.entry_timestamp,
            exit_price=t.exit_price,
            exit_timestamp=t.exit_timestamp,
            profit_pct=adjusted_pnl,
        ))

    return adjusted


def cost_summary(
    original_trades: List[Trade],
    adjusted_trades: List[Trade],
) -> dict:
    """Compare original vs cost-adjusted trade results.

    Returns:
        Dict with original_return, adjusted_return, total_cost_pct.
    """
    def _compound(trades):
        equity = 1.0
        for t in trades:
            equity *= (1 + t.profit_pct / 100)
        return round((equity - 1) * 100, 4)

    orig = _compound(original_trades)
    adj = _compound(adjusted_trades)

    return {
        "original_return_pct": orig,
        "adjusted_return_pct": adj,
        "total_cost_pct": round(orig - adj, 4),
        "num_trades": len(original_trades),
    }
