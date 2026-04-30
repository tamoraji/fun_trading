from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List

from .models import HOLD, PriceBar, Signal
from .strategy import Strategy


@dataclass(frozen=True)
class Trade:
    symbol: str
    strategy_name: str
    entry_action: str
    entry_price: float
    entry_timestamp: datetime
    exit_price: float
    exit_timestamp: datetime
    profit_pct: float


@dataclass(frozen=True)
class BacktestResult:
    symbol: str
    strategy_name: str
    signals: List[Signal]
    trades: List[Trade]
    bars: List[PriceBar]


def replay_bars(strategy: Strategy, symbol: str, bars: List[PriceBar]) -> List[Signal]:
    """Walk through bars progressively, collecting non-HOLD signals."""
    signals: List[Signal] = []
    for i in range(1, len(bars) + 1):
        signal = strategy.evaluate(symbol, bars[:i])
        if signal.action != HOLD:
            # Deduplicate: skip if same action+timestamp as last signal
            if signals and signals[-1].action == signal.action and signals[-1].timestamp == signal.timestamp:
                continue
            signals.append(signal)
    return signals


def match_trades(signals: List[Signal]) -> List[Trade]:
    """Match signals into round-trip trades. BUY->SELL or SELL->BUY."""
    trades: List[Trade] = []
    position: Signal | None = None

    for signal in signals:
        if position is None:
            position = signal
        elif signal.action != position.action:
            # Opposite action closes the position
            if position.action == "BUY":
                profit_pct = (signal.price - position.price) / position.price * 100
            else:
                profit_pct = (position.price - signal.price) / position.price * 100

            trades.append(Trade(
                symbol=position.symbol,
                strategy_name=position.strategy_name,
                entry_action=position.action,
                entry_price=position.price,
                entry_timestamp=position.timestamp,
                exit_price=signal.price,
                exit_timestamp=signal.timestamp,
                profit_pct=round(profit_pct, 4),
            ))
            position = None
        # else: same direction while in position -> ignore

    return trades


def run_backtest(strategy: Strategy, symbol: str, bars: List[PriceBar]) -> BacktestResult:
    """Run a complete backtest: replay bars, match trades, return result."""
    signals = replay_bars(strategy, symbol, bars)
    trades = match_trades(signals)
    return BacktestResult(
        symbol=symbol,
        strategy_name=strategy.name,
        signals=signals,
        trades=trades,
        bars=bars,
    )
