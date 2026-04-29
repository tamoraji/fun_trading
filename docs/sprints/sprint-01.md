# Sprint 01

## Sprint goal

Make the framework more useful for real monitoring by adding durable signal output, expanding strategy coverage, and improving runtime visibility.

## Sprint length

One week

## Selected stories

### SIG-001 Persist emitted signals to local history

Feature brief:

- [`docs/features/SIG-001-feature-brief.md`](/Users/moji/fun_trading/docs/features/SIG-001-feature-brief.md)

Why now:

- The framework currently emits transient signals only
- Signal history is needed for review, debugging, and later analytics

Acceptance criteria:

1. Emitted signals are written to a local history store
2. The storage format is simple to inspect
3. Signal persistence has automated test coverage

### STRAT-001 Add RSI strategy with configurable thresholds and tests

Why now:

- The framework needs more than one strategy to become a real platform
- RSI is a simple, well-bounded addition that fits the current architecture

Acceptance criteria:

1. Config can choose RSI strategy
2. RSI thresholds and window are configurable
3. Strategy behavior is covered by automated tests

### OBS-001 Add structured logs for each polling cycle

Why now:

- Runtime visibility is weak
- Structured logs make later debugging and reporting easier

Acceptance criteria:

1. Each polling cycle records start, end, symbol count, and result summary
2. Errors are logged consistently
3. Log output remains readable in local runs

## Owners by role

- Product Manager: scope control and acceptance
- Scrum Master: sprint tracking
- Quant Researcher: RSI rules and validation scenarios
- Tech Lead: design of persistence and logging boundaries
- Developer: implementation
- QA and Validation: test and regression check
- Release and Operations: runtime config and rollout check

## Risks

- Signal storage format may need to change later if analytics requirements grow
- RSI can be implemented incorrectly if the formula and edge cases are not written down first
- Logging can become noisy if structure is added without filtering rules

## Demo target

By the end of the sprint, the team should be able to run the framework locally, emit signals, inspect saved signal history, see structured logs, and choose between moving-average crossover and RSI from config.
