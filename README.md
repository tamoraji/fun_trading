# Trading Framework

A small Python framework for polling market data on a fixed interval and emitting trading signals through pluggable notifiers.

## What it includes

- Interval-based engine for repeated market checks
- Pluggable market data providers
- Strategy interface with a moving-average crossover example
- Console, webhook, and SMTP email notification backends
- JSON-based configuration
- Unit tests for signal generation and engine behavior

## Quick start

```bash
python3 -m trading_framework --config config.example.json --once
```

Run continuously:

```bash
python3 -m trading_framework --config config.example.json
```

## Configuration

Start from [`config.example.json`](/Users/moji/fun_trading/config.example.json) and adjust:

- `symbols`: market tickers to monitor
- `poll_interval_seconds`: how often the engine wakes up
- `market_data`: source and bar settings
- `strategy`: strategy name and parameters
- `market_session`: optional trading-hours gate
- `notifiers`: one or more outputs for signals

## Default assumptions

- Asset class: U.S. equities
- Data source: Yahoo Finance chart endpoint
- Strategy: moving-average crossover
- Session hours: U.S. regular market hours

## Notification options

- `console`: prints signals locally
- `webhook`: posts a JSON payload to a webhook URL
- `email`: sends a plain-text email using SMTP

## Testing

```bash
python3 -m unittest discover -s tests
```

## Project process

The agile operating model for this project is in [`docs/agile-operating-model.md`](/Users/moji/fun_trading/docs/agile-operating-model.md).
Use [`docs/templates/feature-brief.md`](/Users/moji/fun_trading/docs/templates/feature-brief.md) to start new feature work.
Role charters are in [`docs/agents/README.md`](/Users/moji/fun_trading/docs/agents/README.md), reusable agent prompts are in [`docs/agents/prompt-pack.md`](/Users/moji/fun_trading/docs/agents/prompt-pack.md), the sprint workflow diagram is in [`docs/process/sprint-workflow.md`](/Users/moji/fun_trading/docs/process/sprint-workflow.md), the initial backlog is in [`docs/backlog/product-backlog.md`](/Users/moji/fun_trading/docs/backlog/product-backlog.md), handoff rules are in [`docs/process/handoffs.md`](/Users/moji/fun_trading/docs/process/handoffs.md), and the first sprint plan is in [`docs/sprints/sprint-01.md`](/Users/moji/fun_trading/docs/sprints/sprint-01.md).
