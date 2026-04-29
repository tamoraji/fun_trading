# How to Run the Trading Framework

## Prerequisites

- Python 3.9 or higher
- No external dependencies required (stdlib only)

Verify your Python version:

```bash
python3 --version
```

## Quick Start

### 1. Run with the default config (SMA Crossover strategy)

```bash
cd /Users/moji/fun_trading
python -m trading_framework --config config.example.json --once
```

`--once` runs a single polling cycle and exits. Without it, the framework polls continuously.

### 2. Run with the RSI strategy

```bash
python -m trading_framework --config config.rsi-example.json --once
```

### 3. Run continuously (live monitoring)

```bash
python -m trading_framework --config config.example.json
```

This polls every 300 seconds (5 minutes) by default. Press `Ctrl+C` to stop.

**Note:** The market session filter is enabled by default (US market hours, Mon-Fri 9:30-16:00 ET). Outside those hours, cycles are skipped. To test anytime, set `"enabled": false` in the `market_session` config section.

## Understanding the Output

The framework now outputs structured JSON logs. Each line is a JSON object:

```json
{"timestamp": "2026-04-29T14:30:00+00:00", "event": "cycle_start", "symbols": ["AAPL", "MSFT", "SPY"], "symbol_count": 3}
{"timestamp": "2026-04-29T14:30:01+00:00", "event": "log", "message": "[hold] AAPL: No crossover on the latest bar."}
{"timestamp": "2026-04-29T14:30:01+00:00", "event": "log", "message": "[signal] MSFT: BUY at 425.30"}
{"timestamp": "2026-04-29T14:30:02+00:00", "event": "cycle_end", "signals_emitted": 1, "holds": 2, "errors": 0, "elapsed_seconds": 1.234}
```

Key events:
- `cycle_start` — beginning of a polling cycle with symbol list
- `log` — individual symbol evaluations (hold, signal, dup, error)
- `cycle_end` — summary with counts and timing
- `skip` — market session is closed

## Signal History

When `signal_history` is enabled in config, every BUY/SELL signal is appended to a `.jsonl` file:

```bash
# View saved signals
cat signal_history.jsonl
```

Each line is a JSON record:

```json
{"symbol": "AAPL", "action": "BUY", "price": 189.50, "timestamp": "2026-04-29T14:35:00+00:00", "reason": "Short moving average crossed above long moving average.", "strategy_name": "moving_average_crossover", "details": {"short_sma": 188.2, "long_sma": 187.5, ...}}
```

To pretty-print:

```bash
python3 -c "
import json
with open('signal_history.jsonl') as f:
    for line in f:
        record = json.loads(line)
        print(f\"{record['timestamp']}  {record['action']:4s}  {record['symbol']:6s}  \${record['price']:.2f}  ({record['strategy_name']}: {record['reason']})\")
"
```

## Configuration

### Switching strategies

Edit the `"strategy"` section in your config file:

**SMA Crossover:**
```json
"strategy": {
    "name": "moving_average_crossover",
    "params": {
        "short_window": 5,
        "long_window": 20
    }
}
```

**RSI:**
```json
"strategy": {
    "name": "rsi",
    "params": {
        "period": 14,
        "oversold": 30,
        "overbought": 70
    }
}
```

### Changing symbols

```json
"symbols": ["AAPL", "MSFT", "SPY", "TSLA", "GOOGL"]
```

### Adjusting poll interval

```json
"poll_interval_seconds": 60
```

### Disabling market session filter (for testing anytime)

```json
"market_session": {
    "enabled": false
}
```

### Disabling signal history

```json
"signal_history": {
    "enabled": false
}
```

## Running Tests

Run the full test suite:

```bash
cd /Users/moji/fun_trading
python -m pytest tests/ -v
```

Run tests for a specific module:

```bash
# Signal history tests
python -m pytest tests/test_history.py -v

# RSI strategy tests
python -m pytest tests/test_rsi_strategy.py -v

# Structured logging tests
python -m pytest tests/test_structlog.py -v

# Engine tests
python -m pytest tests/test_engine.py -v

# SMA strategy tests
python -m pytest tests/test_strategy.py -v
```

## Creating a Custom Config

Copy the example and modify:

```bash
cp config.example.json my-config.json
# Edit my-config.json with your preferred settings
python -m trading_framework --config my-config.json --once
```

## Troubleshooting

**"No usable price bars returned"** — Yahoo Finance may be down or the symbol is invalid. Check your internet connection and verify the symbol exists on Yahoo Finance.

**"market session is closed"** — You're running outside US market hours. Set `"enabled": false` in `market_session` to test anytime.

**No signals emitted** — The strategy may not detect a crossover/threshold breach on the current data. This is normal. Try running for several cycles or use a different strategy/parameters.

**Signal history file not created** — Signals are only written when a BUY or SELL is emitted. HOLD signals are not persisted. Run during market hours with volatile symbols for best results.
