# How to Run the Trading Framework

## Prerequisites

- Python 3.9 or higher
- No external dependencies required (stdlib only)

## Quick Start — Interactive Mode (Recommended)

```bash
python -m trading_framework
```

The wizard guides you through everything: symbols, strategy, parameters, and run mode.

```
============================================================
  Trading Framework — Interactive Setup
============================================================

Which symbols would you like to monitor?
  Stocks:  AAPL, MSFT, SPY, TSLA, GOOGL
  Crypto:  BTC-USD, ETH-USD, SOL-USD
  Forex:   EURUSD=X, GBPUSD=X
Enter symbols (comma-separated) [AAPL, MSFT, SPY]:

Which strategy would you like to use?
  You can pick multiple: e.g. 1,2

  1. Moving Average Crossover (SMA)
  2. Relative Strength Index (RSI)
  3. Breakout (Channel)
  4. MACD (Moving Average Convergence Divergence)
  5. Goslin Three-Line Momentum
  6. Market Profile (Value Area)

Choose strategy number(s) [1]:

...

How would you like to run?
  1. Run once (analyze now and exit)
  2. Monitor continuously
  3. Backtest (replay historical data)
  4. Cancel
```

## Quick Start — Config File Mode

```bash
# SMA Crossover strategy
python -m trading_framework --config config.example.json --once

# RSI strategy
python -m trading_framework --config config.rsi-example.json --once

# Continuous monitoring
python -m trading_framework --config config.example.json
```

`--once` runs a single cycle and exits. Without it, the framework polls continuously. Press `Ctrl+C` to stop.

## Run Modes

### 1. Run Once
Analyze current market data and exit.
```bash
python -m trading_framework --config my-config.json --once
```
Or choose "1. Run once" in the interactive wizard.

### 2. Monitor Continuously
Poll at regular intervals (default 300s).
```bash
python -m trading_framework --config my-config.json
```
Or choose "2. Monitor continuously" in the wizard.

### 3. Backtest
Replay historical data through your strategies and see performance metrics.

In the wizard, choose "3. Backtest" then select history length (1y/2y/5y). You'll get a report like:

```
============================================================
  Backtest: AAPL — SMA Crossover
============================================================
  Period:           2025-04-30 to 2026-04-30 (252 bars)
  Signals:          18
  Trades:           9 round-trips
------------------------------------------------------------
  Total return:     +12.34%
  Buy & hold:       +18.56%
  Win rate:         66.7% (6/9)
  Profit factor:    2.01
  Max drawdown:     -8.45%
  Sharpe ratio:     1.23
------------------------------------------------------------
  Trade Log:
  #    Entry      Action  Entry $    Exit $      P&L  Days
  --------------------------------------------------------
  1    2025-08-15 BUY      185.30    192.10  +3.67%    12
  ...
============================================================
```

Run multiple strategies to get a comparison table.

## Features

### Strategies

6 strategies available. Pick one or combine multiple (e.g. `1,2,3`):

| # | Strategy | Best for |
|---|----------|----------|
| 1 | SMA Crossover | Trend following |
| 2 | RSI | Mean reversion, overbought/oversold |
| 3 | Breakout | Consolidation breakouts with volume |
| 4 | MACD | Trend + momentum |
| 5 | Goslin Momentum | High-conviction futures/daily trading |
| 6 | Market Profile | Fair value / mean reversion with volume |

See `docs/strategy-manual.md` for detailed explanations.

### Risk Management

Enable in wizard or config to protect against naive signals:

```json
"risk": {
    "cooldown_seconds": 300,
    "position_aware": true,
    "stop_loss_pct": 5.0,
    "take_profit_pct": 10.0,
    "min_volume": 100000,
    "max_signals_per_day": 3
}
```

| Filter | What it does |
|--------|-------------|
| Cooldown | Block repeat signals within N seconds |
| Position tracking | Block BUY if already long, SELL if already short |
| Stop-loss / Take-profit | Annotate signals with SL/TP price levels |
| Volume guard | Block signals on low-volume bars |
| Daily limit | Cap signals per symbol per day |

### Paper Trading

Simulate execution without real money. Tracks positions, cash, and P&L:

```json
"paper_trading": {
    "enabled": true,
    "starting_cash": 100000,
    "position_size_pct": 10,
    "portfolio_path": "paper_portfolio.json"
}
```

Portfolio state is saved between sessions — positions carry over.

### Data Caching

Cache market data locally to avoid redundant API calls:

```json
"cache": {
    "enabled": true,
    "dir": ".cache",
    "ttl_seconds": 300
}
```

Makes backtests instant on second run. Enabled by default in the wizard.

### Signal History

Every BUY/SELL signal is saved to a `.jsonl` file:

```bash
cat signal_history.jsonl
```

## Configuration Reference

All config options:

```json
{
  "symbols": ["AAPL", "MSFT"],
  "poll_interval_seconds": 300,
  "market_data": {
    "provider": "yahoo",
    "bar_interval": "5m",
    "lookback": "5d",
    "timeout_seconds": 10
  },
  "strategy": {
    "name": "moving_average_crossover",
    "params": {"short_window": 5, "long_window": 20}
  },
  "strategies": [
    {"name": "rsi", "params": {"period": 14}},
    {"name": "macd", "params": {}}
  ],
  "market_session": {
    "enabled": true,
    "timezone": "America/New_York",
    "weekdays": [0, 1, 2, 3, 4],
    "start": "09:30",
    "end": "16:00"
  },
  "signal_history": {"enabled": true, "path": "signal_history.jsonl"},
  "risk": {"cooldown_seconds": 300, "position_aware": true, "stop_loss_pct": 5.0},
  "paper_trading": {"enabled": true, "starting_cash": 100000},
  "cache": {"enabled": true, "ttl_seconds": 300}
}
```

## Running Tests

```bash
# Full suite
python -m pytest tests/ -v

# By module
python -m pytest tests/test_strategy.py -v          # SMA
python -m pytest tests/test_rsi_strategy.py -v       # RSI
python -m pytest tests/test_breakout_strategy.py -v  # Breakout
python -m pytest tests/test_macd_strategy.py -v      # MACD
python -m pytest tests/test_goslin_strategy.py -v    # Goslin
python -m pytest tests/test_market_profile_strategy.py -v  # Market Profile
python -m pytest tests/test_backtest.py -v           # Backtesting
python -m pytest tests/test_metrics.py -v            # Metrics
python -m pytest tests/test_risk.py -v               # Risk management
python -m pytest tests/test_paper.py -v              # Paper trading
python -m pytest tests/test_cache.py -v              # Data cache
python -m pytest tests/test_engine.py -v             # Engine
python -m pytest tests/test_history.py -v            # Signal history
python -m pytest tests/test_interactive.py -v        # Interactive wizard
```

## Troubleshooting

**"No usable price bars returned"** — Yahoo Finance may be down or the symbol is invalid. Check your internet connection and verify the symbol exists on Yahoo Finance.

**"market session is closed"** — You're running outside US market hours. Set `"enabled": false` in `market_session` or answer "n" to the market hours question in the wizard.

**"Not enough history"** — The strategy needs more bars than available. Use a longer lookback (the wizard auto-calculates this), or use shorter strategy parameters.

**No signals emitted** — Normal. Most strategies don't signal on every bar. Try backtesting to see signal frequency over time.

**Signal history file not created** — Signals are only written on BUY/SELL. HOLD signals are not persisted.
