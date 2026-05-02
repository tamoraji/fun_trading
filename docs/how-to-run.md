# How to Run the Trading Framework

## Prerequisites

- Python 3.9 or higher
- No external dependencies required (stdlib only)

## Setup

```bash
# Create virtual environment (first time only)
python -m venv .venv
source .venv/bin/activate    # macOS/Linux
# .venv\Scripts\activate     # Windows

# Install with TUI support
pip install -e ".[tui,dev]"

# Or install everything (TUI + web + dev)
pip install -e ".[all,dev]"
```

## Quick Start — Interactive Mode (Recommended)

```bash
python -m trading_framework
```

The wizard starts by asking for symbols, then offers three paths:

```
============================================================
  Trading Framework
============================================================

What would you like to trade?
Enter symbol(s) [AAPL]: AAPL, BTC-USD

How would you like to set up?

  1. Quick Start
     Just pick symbols — we configure everything automatically.

  2. Choose a Preset
     Pre-built profiles for day trading, swing trading, crypto, etc.

  3. Advanced Setup
     Full control over every parameter.
```

### Quick Start (Option 1)
Enter your symbols and go. Auto-detects crypto vs stocks and configures strategies, intervals, risk, and paper trading accordingly. Just 3 inputs total.

### Presets (Option 2)
Choose from pre-built profiles:
- **Day Trader** — 5m bars, MACD+RSI, tight risk
- **Swing Trader** — Daily bars, SMA+Breakout, moderate risk
- **Crypto** — 1h bars, RSI+Breakout+MACD, 24/7
- **Futures/Goslin** — Daily bars, Goslin momentum, conservative
- **Value Investor** — Daily bars, Market Profile
- **Backtest Lab** — Compare ALL strategies on historical data

### Advanced (Option 3)
Full control: pick strategies (multiple allowed), set every parameter (type `?` for help on any option), configure risk filters, paper trading, and more.

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

In the wizard, choose "3. Backtest" then select history length (1y/2y/5y).

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

### 4. TUI Dashboard
Live visual monitoring with color-coded panels. Choose "4. TUI Dashboard" in the wizard or use `--tui`:

```bash
python -m trading_framework --config my-config.json --tui
```

```
┌─────────────────────────────────────────────────────────┐
│  Trading Framework — Live Dashboard                     │
├────────────────────────────┬────────────────────────────┤
│  PORTFOLIO                 │  STATUS                    │
│  Cash: $90,000             │  Cycle: 47                 │
│  Realized P&L: +$2,340    │  Signals: 1                │
│  AAPL  long  $189.50      │  Holds: 5                  │
├────────────────────────────┴────────────────────────────┤
│  14:30  ★ AAPL/macd  BUY $189.50                       │
│  14:30  AAPL/rsi  HOLD (within normal range)            │
├─────────────────────────────────────────────────────────┤
│  Q: Quit  P: Pause/Resume  S: Summary                  │
└─────────────────────────────────────────────────────────┘
```

Keyboard shortcuts: **Q** quit, **P** pause/resume, **S** portfolio summary.

Requires `pip install -e ".[tui]"` (textual).

### 5. Web Dashboard
Full 6-tab trading platform in your browser.

```bash
python -m trading_framework --web
# Open http://127.0.0.1:8000
```

| Tab | What it does |
|-----|-------------|
| **Markets** | Watchlist with prices, change%, regime badges. Click symbol → candlestick chart with SMA 20/50 overlays. Auto-refreshes every 60s. |
| **Trading** | Live signal feed with confidence scoring (HIGH/MED/LOW). Strategy status. Auto-refreshes every 30s. |
| **Backtest Lab** | Pick symbol + strategy → candlestick chart with BUY/SELL markers + cost-adjusted metrics. |
| **Predictions** | ML momentum scores per symbol (progress bars), feature values (RSI, volatility, trend), regime-based strategy recommendations. |
| **Portfolio** | Open positions, equity summary, full order history. |
| **Settings** | Strategy reference, presets, documentation links. |

Or choose "5. Web Dashboard" in the wizard. Requires `pip install -e ".[web]"`.

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

### Smart Signals (Confidence Scoring)

When running multiple strategies, the framework scores signals by multi-strategy agreement:

| Confidence | Criteria | Example |
|-----------|----------|---------|
| **HIGH** | 50%+ of strategies agree | 3/6 strategies say BUY |
| **MEDIUM** | 30-49% agree | 2/6 agree |
| **LOW** | Single strategy | 1/6 says BUY |

The notification router dispatches by confidence level — e.g., only HIGH confidence signals go to Telegram, while everything is logged locally.

```python
# Programmatic usage
from trading_framework.signals import SignalAggregator, NotificationRouter
from trading_framework.core.types import Confidence

aggregator = SignalAggregator(event_bus=engine.event_bus, total_strategies=6)
router = NotificationRouter()
router.add_channel("telegram", telegram_notifier.send_aggregated, Confidence.HIGH)
router.add_channel("console", print, Confidence.LOW)
```

### Telegram Notifications

Send signals to your phone via Telegram Bot:

1. Create a bot via `@BotFather` on Telegram
2. Get your chat ID from `@userinfobot`
3. Configure in JSON config:

```json
"notifiers": [
    {"type": "console"},
    {"type": "telegram", "bot_token": "YOUR_TOKEN", "chat_id": "YOUR_CHAT_ID"}
]
```

Or use programmatically:
```python
from trading_framework.signals.notifiers.telegram import TelegramNotifier
notifier = TelegramNotifier(bot_token="123:ABC", chat_id="-100123")
notifier.send(signal)
```

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

### Human-in-the-Loop (Trade Approval)

Require human approval before executing trades:

```python
from trading_framework.execution import OrderManager

manager = OrderManager(broker=portfolio, mode="approval", timeout_seconds=300)

# Signal is queued, not executed
pending = manager.execute(signal)

# Approve or reject from Telegram, TUI, or web
manager.approve(pending.id)   # executes the trade
manager.reject(pending.id, reason="Too risky")

# Auto-expire stale orders
manager.expire_stale()
```

### Position Sizing

4 sizing models available:

| Model | Description |
|-------|-------------|
| `FixedPercentSizer(10)` | 10% of equity per trade |
| `FixedAmountSizer(10000)` | $10K per trade |
| `RiskPerTradeSizer(2, 5)` | Risk 2% of equity with 5% stop-loss |
| `KellyCriterionSizer(0.6, 5, 3)` | Kelly criterion based on win rate |

```python
from trading_framework.execution import FixedPercentSizer
sizer = FixedPercentSizer(percent=10)
quantity = sizer.size(equity=100000, price=150.0)  # → 66.67 shares
```

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

### CSV Data Import

Load historical data from CSV files for offline backtesting:

```python
from trading_framework.data.providers.csv import CSVDataProvider

provider = CSVDataProvider(data_dir="./data")
bars = provider.fetch_bars("AAPL", config)  # loads ./data/AAPL.csv
```

CSV format: `date,open,high,low,close,volume` (header row required).

### Data Manager (Multi-Source Routing)

Routes requests to the right provider based on asset class:

```python
from trading_framework.data.manager import DataManager
from trading_framework.core.types import AssetClass

manager = DataManager(default_provider=yahoo_provider)
manager.register_provider(AssetClass.CRYPTO, crypto_provider)

manager.fetch_bars("AAPL", config)    # → yahoo (stock)
manager.fetch_bars("BTC-USD", config) # → crypto provider
manager.fetch_bars("EURUSD=X", config) # → yahoo (forex, default)
```

### Timeframe Resampling

Convert bars between intervals:

```python
from trading_framework.data.resampler import resample

hourly = resample(minute_bars, "1h")
daily = resample(hourly_bars, "1d")
```

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

### ML Features and Regime Detection

Extract features for ML model input:

```python
from trading_framework.analytics.ml import extract_features
features = extract_features(bars, lookback=20)
# 14 features: return_1d, return_5d, sma, std, rsi_14, bollinger_pct,
#              volume_ratio, volatility, high_low_pct, price_vs_sma, etc.
```

Detect current market regime:

```python
from trading_framework.analytics import detect_regime, MarketRegime
regime = detect_regime(bars, lookback=20)
if regime == MarketRegime.TRENDING_UP:
    # use trend-following strategy
elif regime == MarketRegime.RANGING:
    # use mean-reversion strategy
```

ML-powered strategy (strategy #7):

```python
# Momentum ML uses feature scoring to generate signals
# Available as strategy "momentum_ml" in the wizard
```

### Transaction Cost Modeling

Add slippage and commission to backtests:

```python
from trading_framework.analytics import CostModel, apply_costs, cost_summary
model = CostModel(slippage_pct=0.1, commission_per_trade=1.0)
adjusted = apply_costs(trades, model)
summary = cost_summary(original_trades, adjusted)
# summary = {"original_return_pct": 12.3, "adjusted_return_pct": 10.8, "total_cost_pct": 1.5}
```

## Architecture

See `docs/architecture.md` for the full 8-layer architecture, dependency rules, and migration status.

## Troubleshooting

**"No usable price bars returned"** — Yahoo Finance may be down or the symbol is invalid. Check your internet connection and verify the symbol exists on Yahoo Finance.

**"market session is closed"** — You're running outside US market hours. Set `"enabled": false` in `market_session` or answer "n" to the market hours question in the wizard.

**"Not enough history"** — The strategy needs more bars than available. Use a longer lookback (the wizard auto-calculates this), or use shorter strategy parameters.

**No signals emitted** — Normal. Most strategies don't signal on every bar. Try backtesting to see signal frequency over time.

**Signal history file not created** — Signals are only written on BUY/SELL. HOLD signals are not persisted.
