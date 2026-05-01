# Architecture

## Overview

The trading framework is organized into 8 layers, each with clear responsibilities and dependencies. The layers communicate through well-defined interfaces and an event bus.

```
┌──────────────────────────────────────────────────────┐
│                    UI Layer                           │
│  CLI  │  TUI  │  Web Dashboard  │  Telegram Bot      │
├──────────────────────────────────────────────────────┤
│                  Service Layer                        │
│  TradingService: the single API all UIs consume      │
├─────────┬──────────┬────────────┬────────────────────┤
│ Signals │Execution │ Analytics  │ Risk               │
├─────────┴──────────┴────────────┴────────────────────┤
│               Strategy Layer (plugins)               │
├──────────────────────────────────────────────────────┤
│                    Data Layer                         │
├──────────────────────────────────────────────────────┤
│               Infrastructure Layer                   │
├──────────────────────────────────────────────────────┤
│                    Core Layer                         │
└──────────────────────────────────────────────────────┘
```

## Layer Details

### Core (`trading_framework/core/`)
**Zero dependencies.** The foundation everything imports from.

- `models.py` — Data structures: PriceBar, Signal, AppSettings, etc.
- `events.py` — Event types for the event bus (planned)
- `interfaces.py` — ABCs: Strategy, DataProvider, Notifier, Broker (planned)
- `types.py` — Constants (BUY, SELL, HOLD), enums (planned)

### Infrastructure (`trading_framework/infra/`)
**Depends on: Core only.**

- `event_bus.py` — In-process pub/sub for decoupled communication (planned)
- `plugin.py` — Strategy registry with `@register_strategy` decorator (planned)
- `config.py` — JSON config loading and validation (current: `config.py`)
- `scheduler.py` — Interval and cron-like scheduling (planned)

### Data (`trading_framework/data/`)
**Depends on: Core, Infrastructure.**

- `manager.py` — Routes data requests to providers by asset class (planned)
- `cache.py` — SQLite-based caching with TTL (current: `cache.py`)
- `resampler.py` — Timeframe conversion (planned)
- `providers/yahoo.py` — Yahoo Finance provider (current: `data.py`)
- `providers/alpaca.py` — Alpaca Markets (planned)
- `providers/ccxt.py` — Crypto exchanges (planned)
- `providers/csv.py` — Local CSV files (planned)

### Strategies (`trading_framework/strategies/`)
**Depends on: Core only.**

Each strategy is a separate module implementing the Strategy interface:

| Module | Strategy | Signal Logic |
|--------|----------|-------------|
| `sma.py` | Moving Average Crossover | Fast SMA crosses slow SMA |
| `rsi.py` | Relative Strength Index | RSI crosses oversold/overbought thresholds |
| `breakout.py` | Channel Breakout | Price breaks high/low channel with volume |
| `macd.py` | MACD | MACD line crosses signal line |
| `goslin.py` | Goslin Three-Line Momentum | Direction + timing + confirming all agree |
| `market_profile.py` | Market Profile Value Area | Price returns to value area |
| `composite.py` | Composite Scoring | Weighted multi-strategy voting (planned) |

Shared indicator math in `indicators.py` (RSI, EMA, SMA, value area).

### Signals (`trading_framework/signals/`)
**Depends on: Core, Infrastructure.**

- `aggregator.py` — Multi-strategy signal fusion with confidence (planned)
- `confidence.py` — Signal quality scoring model (planned)
- `router.py` — Channel-based notification routing (planned)
- `history.py` — Persistent signal recording (current: `history.py`)
- `notifiers/console.py` — Terminal output (current: `notifiers.py`)
- `notifiers/telegram.py` — Telegram Bot (planned)

### Execution (`trading_framework/execution/`)
**Depends on: Core, Infrastructure.**

- `broker.py` — Broker ABC: submit_order, get_positions, etc. (planned)
- `paper.py` — Paper trading portfolio (current: `paper.py`)
- `order_manager.py` — Signal → approval gate → execution (planned)
- `position_sizer.py` — Position sizing models (planned)

### Analytics (`trading_framework/analytics/`)
**Depends on: Core, Data, Strategies.**

- `backtest.py` — Historical replay with trade matching (current: `backtest.py`)
- `metrics.py` — Performance metrics and reporting (current: `metrics.py`)
- `ml/features.py` — Feature engineering from price bars (planned)
- `ml/models.py` — ML model interface (planned)
- `regime.py` — Market regime detection (planned)

### Risk (`trading_framework/risk_mgmt/`)
**Depends on: Core only.**

- `manager.py` — Risk filter chain (current: `risk.py`)
- `filters.py` — Individual filter implementations (planned split)

### Service (`trading_framework/service/`)
**Depends on: All lower layers.**

- `api.py` — TradingService facade: the single entry point all UIs call (planned)
- `engine.py` — Event-bus-aware trading engine (current: `engine.py`)

### UI (`trading_framework/ui/`)
**Depends on: Service layer only (+ UI framework deps).**

- `cli.py` — Command-line interface (current: `cli.py`)
- `interactive.py` — Setup wizard with Quick Start, Presets, Advanced (current: `interactive.py`)
- `tui.py` — Textual terminal dashboard (current: `tui.py`)
- `web/` — FastAPI + Jinja2 + Plotly browser dashboard (current: `web/`)
- `telegram.py` — Telegram bot for notifications + HITL (planned)

## Dependency Rules

1. **Core** imports nothing from the framework
2. **Infrastructure** imports only from Core
3. **Data, Strategies, Risk** import from Core and Infrastructure
4. **Signals, Execution, Analytics** import from Core, Infrastructure, and lower layers
5. **Service** imports from all lower layers — it's the orchestrator
6. **UI** imports ONLY from Service — never from engine/strategy/data directly

## Migration Status

| Package | Status | Notes |
|---------|--------|-------|
| `core/` | **Active** | types.py (BUY/SELL/HOLD, Confidence, AssetClass), events.py (8 event types), interfaces.py (6 ABCs) |
| `infra/` | **Active** | event_bus.py (sync pub/sub), plugin.py (strategy registry with @register_strategy) |
| `data/` | Scaffolded | Re-exports from flat `data.py` + `cache.py` |
| `strategies/` | **Active** | 6 strategies split into individual files + indicators.py + plugin registration |
| `signals/` | Scaffolded | Re-exports from flat `notifiers.py` + `history.py` |
| `execution/` | Scaffolded | Re-exports from flat `paper.py` |
| `analytics/` | Scaffolded | Re-exports from flat `backtest.py` + `metrics.py` |
| `risk_mgmt/` | Scaffolded | Re-exports from flat `risk.py` |
| `service/` | **Active** | TradingService facade (create_engine, run_backtest, list_strategies, etc.) |
| `ui/` | Scaffolded | CLI refactor planned for Phase 2 |

Strategies are split into individual files with plugin registration. The TradingService facade provides a single API for all UIs. The event bus is wired into the engine. Flat modules remain for backward compatibility. 200 tests pass.
