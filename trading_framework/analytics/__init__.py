"""Analytics layer — backtesting, metrics, and ML integration.

Tools for evaluating and improving trading strategies:
- Backtesting: historical replay with trade matching
- Metrics: performance measurement (Sharpe, drawdown, win rate, etc.)
- ML: feature engineering, model training, regime detection

Dependencies: core, data (for historical bars), strategies.
"""
# Re-export current analytics for backward compatibility
from ..backtest import Trade, BacktestResult, replay_bars, match_trades, run_backtest
from ..metrics import BacktestMetrics, compute_metrics, format_report, format_trades, format_comparison
