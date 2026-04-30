from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from statistics import fmean, stdev
from typing import List, Tuple

from .backtest import Trade
from .models import PriceBar


@dataclass(frozen=True)
class BacktestMetrics:
    total_return_pct: float
    num_trades: int
    win_rate_pct: float
    avg_win_pct: float
    avg_loss_pct: float
    profit_factor: float
    max_drawdown_pct: float
    sharpe_ratio: float
    buy_and_hold_return_pct: float


def compute_metrics(trades: List[Trade], bars: List[PriceBar]) -> BacktestMetrics:
    """Compute all backtest metrics from trades and bar history."""
    num_trades = len(trades)

    if num_trades == 0:
        bh = _buy_and_hold(bars)
        return BacktestMetrics(
            total_return_pct=0.0, num_trades=0, win_rate_pct=0.0,
            avg_win_pct=0.0, avg_loss_pct=0.0, profit_factor=0.0,
            max_drawdown_pct=0.0, sharpe_ratio=0.0,
            buy_and_hold_return_pct=bh,
        )

    returns = [t.profit_pct for t in trades]
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r < 0]

    # Total return (compounded)
    equity = 1.0
    for r in returns:
        equity *= (1 + r / 100)
    total_return_pct = round((equity - 1) * 100, 4)

    # Win rate
    win_rate_pct = round(len(wins) / num_trades * 100, 2)

    # Avg win / loss
    avg_win_pct = round(fmean(wins), 4) if wins else 0.0
    avg_loss_pct = round(fmean(losses), 4) if losses else 0.0

    # Profit factor
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    if gross_loss == 0:
        profit_factor = float('inf') if gross_profit > 0 else 0.0
    else:
        profit_factor = round(gross_profit / gross_loss, 4)

    # Max drawdown
    max_drawdown_pct = _max_drawdown(returns)

    # Sharpe ratio
    sharpe_ratio = _sharpe(returns, trades)

    # Buy and hold
    bh = _buy_and_hold(bars)

    return BacktestMetrics(
        total_return_pct=total_return_pct,
        num_trades=num_trades,
        win_rate_pct=win_rate_pct,
        avg_win_pct=avg_win_pct,
        avg_loss_pct=avg_loss_pct,
        profit_factor=profit_factor,
        max_drawdown_pct=max_drawdown_pct,
        sharpe_ratio=sharpe_ratio,
        buy_and_hold_return_pct=bh,
    )


def _max_drawdown(returns: List[float]) -> float:
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    for r in returns:
        equity *= (1 + r / 100)
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak * 100
        if dd > max_dd:
            max_dd = dd
    return round(max_dd, 4)


def _sharpe(returns: List[float], trades: List[Trade]) -> float:
    if len(returns) < 2:
        return 0.0
    try:
        std = stdev(returns)
    except Exception:
        return 0.0
    if std == 0:
        return 0.0
    mean_r = fmean(returns)
    # Annualize: estimate trades per year from date range
    first = trades[0].entry_timestamp
    last = trades[-1].exit_timestamp
    days = max((last - first).days, 1)
    trades_per_year = len(trades) / days * 365
    return round((mean_r / std) * math.sqrt(max(trades_per_year, 1)), 4)


def _buy_and_hold(bars: List[PriceBar]) -> float:
    if len(bars) < 2:
        return 0.0
    return round((bars[-1].close - bars[0].close) / bars[0].close * 100, 4)


def format_trades(trades: List[Trade]) -> str:
    """Format a trade log showing each round-trip trade."""
    if not trades:
        return "  No trades."

    # Dynamic column width based on largest price
    max_price = max(max(t.entry_price, t.exit_price) for t in trades)
    pw = max(9, len(f"{max_price:,.2f}") + 1)

    lines = [
        f"  {'#':<4} {'Date':<12} {'Side':<6} {'Entry':>{pw}} {'Exit':>{pw}} {'P&L':>9} {'Days':>5}",
        "  " + "-" * (4 + 12 + 6 + pw + pw + 9 + 5 + 5),
    ]
    for i, t in enumerate(trades, 1):
        sign = "+" if t.profit_pct >= 0 else ""
        days = (t.exit_timestamp - t.entry_timestamp).days
        lines.append(
            f"  {i:<4} {t.entry_timestamp.strftime('%Y-%m-%d'):<12} "
            f"{t.entry_action:<6} {t.entry_price:>{pw},.2f} {t.exit_price:>{pw},.2f} "
            f"{sign}{t.profit_pct:>7.2f}% {days:>5}"
        )
    return "\n".join(lines)


def format_report(
    symbol: str,
    strategy_name: str,
    metrics: BacktestMetrics,
    num_signals: int,
    num_bars: int,
    start_date: datetime,
    end_date: datetime,
    trades: List[Trade] | None = None,
) -> str:
    pf = f"{metrics.profit_factor:.2f}" if metrics.profit_factor != float('inf') else "inf"
    sign = lambda v: f"+{v:.2f}" if v >= 0 else f"{v:.2f}"

    lines = [
        "",
        "=" * 60,
        f"  Backtest: {symbol} — {strategy_name}",
        "=" * 60,
        f"  Period:           {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({num_bars} bars)",
        f"  Signals:          {num_signals}",
        f"  Trades:           {metrics.num_trades} round-trips",
        "-" * 60,
        f"  Total return:     {sign(metrics.total_return_pct)}%",
        f"  Buy & hold:       {sign(metrics.buy_and_hold_return_pct)}%",
        f"  Win rate:         {metrics.win_rate_pct:.1f}% ({int(metrics.num_trades * metrics.win_rate_pct / 100)}/{metrics.num_trades})" if metrics.num_trades > 0 else "  Win rate:         N/A",
        f"  Avg win:          {sign(metrics.avg_win_pct)}%",
        f"  Avg loss:         {sign(metrics.avg_loss_pct)}%",
        f"  Profit factor:    {pf}",
        f"  Max drawdown:     -{metrics.max_drawdown_pct:.2f}%",
        f"  Sharpe ratio:     {metrics.sharpe_ratio:.2f}",
    ]

    if trades:
        lines.append("-" * 60)
        lines.append("  Trade Log:")
        lines.append(format_trades(trades))

    lines.append("=" * 60)
    return "\n".join(lines)


def format_comparison(results: List[Tuple[str, BacktestMetrics]]) -> str:
    lines = [
        "",
        "-" * 70,
        f"  {'Strategy':<30} {'Return':>8} {'Win Rate':>10} {'Sharpe':>8} {'Max DD':>8}",
        "-" * 70,
    ]
    for name, m in results:
        sign = lambda v: f"+{v:.2f}" if v >= 0 else f"{v:.2f}"
        lines.append(
            f"  {name:<30} {sign(m.total_return_pct) + '%':>8} "
            f"{m.win_rate_pct:>8.1f}% {m.sharpe_ratio:>8.2f} {'-' + f'{m.max_drawdown_pct:.2f}' + '%':>8}"
        )
    # Add buy & hold from first result
    if results:
        bh = results[0][1].buy_and_hold_return_pct
        sign_bh = f"+{bh:.2f}" if bh >= 0 else f"{bh:.2f}"
        lines.append(f"  {'Buy & Hold':<30} {sign_bh + '%':>8} {'—':>10} {'—':>8} {'—':>8}")
    lines.append("-" * 70)
    return "\n".join(lines)
