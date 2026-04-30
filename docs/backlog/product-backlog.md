# Product Backlog

This backlog evolves the trading framework from a basic polling engine into a fully automated trading platform with market monitoring, multi-technique forecasting, trade execution, and human-in-the-loop oversight.

---

## Epic list

### EPIC-01 Strategy Library

Goal: build a rich, extensible library of trading strategies covering technical indicators, candlestick patterns, and composite signal systems.

Initial stories:

- ~~STRAT-001 Add RSI strategy~~ DONE
- ~~STRAT-002 Add breakout strategy~~ DONE
- ~~STRAT-003 Add strategy registry (multi-strategy from config)~~ DONE
- ~~STRAT-004 Add MACD strategy~~ DONE
- STRAT-005 Add Bollinger Bands strategy (squeeze breakout, mean reversion bounce)
- STRAT-006 Add Stochastic Oscillator strategy with configurable K/D periods
- STRAT-007 Add ADX/DMI trend strength filter strategy
- STRAT-008 Add Ichimoku Cloud strategy (cloud breakout, TK cross, Chikou confirmation)
- STRAT-009 Add VWAP strategy for intraday mean reversion and trend following
- STRAT-010 Add candlestick pattern recognition (pin bar, engulfing, doji, hammer, morning/evening star)
- STRAT-011 Add Sikka classic pattern strategies (Type A/B/C/F, Concurrent patterns) from reference tables
- STRAT-012 Add Sikka modern Trend Rider strategies (Type 1-6, Wiggle-and-Cross, First Turn)
- STRAT-013 Add support/resistance level detection (pivot points, Fibonacci retracement/extension)
- STRAT-014 Add divergence detection engine (price vs RSI, MACD, OBV divergences)
- STRAT-015 Add multi-timeframe strategy support (e.g. daily trend + 5m entry)
- STRAT-016 Add composite signal scoring system (combine multiple strategies with weighted votes)
- STRAT-017 Add pairs trading / cointegration strategy for correlated instruments
- STRAT-018 Add Parabolic SAR trailing strategy
- STRAT-019 Add volume profile and OBV-based strategies
- ~~STRAT-020 Add Goslin momentum method strategies~~ DONE
- STRAT-021 Add Market Profile (Value Area) strategy — DONE

### EPIC-02 Backtesting and Simulation

Goal: validate strategies on historical data before live deployment with realistic market simulation.

Initial stories:

- ~~SIM-001 Add historical replay mode~~ DONE
- ~~SIM-002 Add backtest result summary metrics~~ DONE
- ~~SIM-003 Add comparison output between strategies~~ DONE
- SIM-004 Add slippage modeling (fixed, percentage, volume-based)
- SIM-005 Add commission and fee modeling (per-trade, per-share, percentage, tiered)
- SIM-006 Add walk-forward optimization with in-sample/out-of-sample splits
- SIM-007 Add Monte Carlo simulation for strategy robustness testing
- SIM-008 Add equity curve and drawdown curve visualization (Plotly or Matplotlib)
- SIM-009 Add trade entry/exit overlay on price charts
- SIM-010 Add parameter sweep / grid search optimization for strategy tuning
- SIM-011 Add vectorized backtesting mode for fast parameter sweeps
- SIM-012 Add multi-timeframe backtest support
- SIM-013 Add benchmark comparison (alpha, beta, tracking error vs SPY/index)
- SIM-014 Add trade-level analytics (individual position inspection, holding period distribution)

### EPIC-03 Signal Delivery and History

Goal: make signals durable, multi-channel, and useful for review and improvement.

Initial stories:

- ~~SIG-001 Persist emitted signals to local history~~ DONE
- SIG-002 Add Telegram notifier with bot integration
- SIG-003 Add daily summary report of emitted signals
- SIG-004 Add Slack notifier
- SIG-005 Add Discord notifier
- SIG-006 Add SMS notifier (via Twilio or similar)
- SIG-007 Add push notification support (mobile)
- SIG-008 Add signal history query and filtering CLI (by date, symbol, strategy, action)
- SIG-009 Add weekly/monthly performance summary reports
- SIG-010 Add signal export (CSV, JSON) for external analysis
- SIG-011 Add alert cooldown and deduplication across notification channels
- SIG-012 Add alert escalation (escalate to different channel if not acknowledged)
- SIG-013 Add trade journal with entry/exit reasoning capture

### EPIC-04 Risk Management

Goal: protect capital with pre-trade, active-trade, and portfolio-level risk controls.

Initial stories:

- ~~RISK-001 Add cooldown support~~ DONE
- ~~RISK-002 Add position-aware logic~~ DONE
- ~~RISK-003 Add configurable risk filters (volume guard)~~ DONE
- ~~RISK-004 Add stop-loss and take-profit~~ DONE
- RISK-005 Add take-profit targets (multiple scaled targets)
- RISK-006 Add break-even stop (move stop to entry after reaching threshold)
- RISK-007 Add time-based stop (exit after N bars if no movement)
- RISK-008 Add maximum position size limits (per-asset and total portfolio)
- RISK-009 Add maximum concurrent open positions limit
- RISK-010 Add daily loss circuit breaker (halt trading after X% daily loss)
- RISK-011 Add maximum drawdown limit (halt all trading if threshold breached)
- RISK-012 Add portfolio exposure limits (gross and net)
- RISK-013 Add sector/asset-class concentration limits
- RISK-014 Add correlation-based position limits (avoid correlated bets)
- RISK-015 Add position sizing models (fixed, percentage-of-equity, Kelly criterion, risk-per-trade)
- RISK-016 Add kill switch / emergency stop (halt all trading immediately)
- RISK-017 Add fat-finger protection (reject orders beyond size/price thresholds)
- RISK-018 Add stale data detection (halt if data feed is delayed beyond threshold)
- RISK-019 Add minimum ROI time-decay table (require higher ROI for shorter holds)
- RISK-020 Add Value at Risk (VaR) and Expected Shortfall monitoring

### EPIC-05 Broker and Execution Integration

Goal: connect to brokers for paper trading and live execution with smart order management.

Initial stories:

- ~~EXEC-001 Add paper-trading execution adapter~~ DONE
- ~~EXEC-002 Record order intents and execution outcomes~~ DONE
- EXEC-003 Add broker interface abstraction (pluggable broker adapters)
- EXEC-004 Add Alpaca broker adapter (paper + live trading)
- EXEC-005 Add Interactive Brokers adapter via IB Gateway API
- EXEC-006 Add order type support (market, limit, stop, stop-limit, trailing stop)
- EXEC-007 Add bracket orders (entry + take-profit + stop-loss as a unit)
- EXEC-008 Add OCO (One-Cancels-Other) order support
- EXEC-009 Add partial fill handling and position building
- EXEC-010 Add automatic position sizing based on risk parameters
- EXEC-011 Add TWAP/VWAP execution scheduling for large orders
- EXEC-012 Add automatic reconnection and connection health monitoring
- EXEC-013 Add rate limit management per broker
- EXEC-014 Add multi-account support
- EXEC-015 Add order state machine with lifecycle tracking (pending, filled, partial, cancelled, rejected)

### EPIC-06 Observability and Reporting

Goal: full visibility into runtime behavior, strategy performance, and system health.

Initial stories:

- ~~OBS-001 Add structured logs for each polling cycle~~ DONE
- OBS-002 Add basic health and error counters
- OBS-003 Add strategy performance review report (per-strategy P&L, hit rate, expectancy)
- OBS-004 Add performance attribution (which strategies/signals drove returns)
- OBS-005 Add rolling Sharpe/Sortino/drawdown monitoring dashboard
- OBS-006 Add trade cost analysis (slippage, commissions, market impact)
- OBS-007 Add system metrics (API latency, data freshness, memory usage)
- OBS-008 Add configurable log levels and log rotation
- OBS-009 Add Prometheus/Grafana metrics export for external monitoring
- OBS-010 Add anomaly detection on strategy behavior (sudden regime change alerts)

### EPIC-07 Human-in-the-Loop Controls

Goal: provide human oversight, approval workflows, and manual override for all automated actions.

Initial stories:

- HITL-001 Add trade approval workflow (signals require human confirmation before execution)
- HITL-002 Add configurable approval thresholds (auto-execute small trades, require approval for large ones)
- HITL-003 Add approval timeout handling (auto-cancel or escalate if no response within N minutes)
- HITL-004 Add manual override controls (force-close, pause/resume bot, adjust stops on active trades)
- HITL-005 Add parameter hot-reload (adjust strategy parameters without restarting)
- HITL-006 Add strategy enable/disable per symbol without restart
- HITL-007 Add confidence scoring on signals (high/medium/low) to inform human decisions
- HITL-008 Add interactive Telegram bot for approvals and status queries
- HITL-009 Add audit log of all human interventions (approvals, rejections, overrides)
- HITL-010 Add batch approval mode for multiple pending trades

### EPIC-08 Market Monitoring and Scanning

Goal: continuous market surveillance with intelligent alerting and asset screening.

Initial stories:

- SCAN-001 Add market scanner with configurable screening criteria (price, volume, technical)
- SCAN-002 Add momentum scanning (top gainers/losers by timeframe)
- SCAN-003 Add volume spike detection and unusual activity alerts
- SCAN-004 Add new high/low detection across watchlist
- SCAN-005 Add cross-market correlation monitoring
- SCAN-006 Add volatility regime detection (low-vol squeeze, high-vol expansion)
- SCAN-007 Add economic calendar integration (FOMC, NFP, CPI event awareness)
- SCAN-008 Add pre-market and after-hours monitoring mode
- SCAN-009 Add dynamic watchlist management (add/remove symbols based on criteria)
- SCAN-010 Add multi-exchange data aggregation (stocks, crypto, forex from different sources)

### EPIC-09 Data Management and Multi-Source Integration

Goal: reliable, multi-source data pipeline with caching, cleaning, and multi-timeframe support.

Initial stories:

- DATA-001 Add Alpha Vantage data provider
- DATA-002 Add Polygon.io data provider for real-time and historical data
- DATA-003 Add CSV/file-based data import for custom datasets
- ~~DATA-004 Add local data caching layer~~ DONE
- DATA-005 Add data resampling (convert 1m bars to 5m, 15m, 1h, daily)
- DATA-006 Add multiple timeframe alignment and synchronization
- DATA-007 Add corporate action adjustments (splits, dividends)
- DATA-008 Add data quality checks (gap detection, stale data, outlier filtering)
- DATA-009 Add WebSocket real-time streaming support
- DATA-010 Add fundamental data provider (earnings, revenue, ratios)
- DATA-011 Add order book / Level 2 data support
- DATA-012 Add cryptocurrency exchange data providers (Binance, Coinbase)

### EPIC-10 Forecasting and ML/AI Integration

Goal: add statistical, machine learning, and AI-based forecasting alongside traditional technical analysis.

Initial stories:

- ML-001 Add feature engineering pipeline (rolling stats, lagged features, cross-sectional ranks)
- ML-002 Add ARIMA/SARIMA time series forecasting
- ML-003 Add GARCH volatility forecasting
- ML-004 Add Random Forest / Gradient Boosting classifier for direction prediction
- ML-005 Add LSTM/GRU recurrent neural network for sequence prediction
- ML-006 Add sentiment analysis from financial news feeds
- ML-007 Add social media sentiment integration (Reddit, Twitter/X, StockTwits)
- ML-008 Add regime detection using Hidden Markov Models
- ML-009 Add ensemble model system (combine multiple model predictions with confidence weighting)
- ML-010 Add online/adaptive learning (auto-retrain models on new data)
- ML-011 Add model performance monitoring and drift detection
- ML-012 Add Kalman filter for noise reduction and state estimation
- ML-013 Add reinforcement learning agent for trade execution optimization
- ML-014 Add Transformer-based price forecasting model
- ML-015 Add LLM-powered market analysis (summarize news, earnings calls, SEC filings)

### EPIC-11 Portfolio Management

Goal: manage positions across multiple assets with intelligent allocation, rebalancing, and tracking.

Initial stories:

- PORT-001 Add portfolio state tracker (positions, cash, total equity, P&L)
- PORT-002 Add position sizing models (equal weight, risk parity, Kelly criterion)
- PORT-003 Add calendar-based rebalancing (daily, weekly, monthly)
- PORT-004 Add threshold-based rebalancing (rebalance when drift exceeds X%)
- PORT-005 Add multi-strategy capital allocation (assign capital percentages per strategy)
- PORT-006 Add strategy-level performance tracking (individual and aggregate)
- PORT-007 Add benchmark comparison and alpha/beta calculation
- PORT-008 Add sector/asset-class allocation tracking and constraints
- PORT-009 Add tax lot tracking (FIFO, LIFO, specific lot)
- PORT-010 Add portfolio optimization (mean-variance, minimum variance, max diversification)

### EPIC-12 User Interface and Dashboard

Goal: provide multiple UI options for different user groups — terminal power users, desktop users, and web/mobile users. The core logic must stay UI-agnostic so any frontend can consume it.

**Design principle:** All UI layers consume the same service/API layer. No business logic in UI code.

Initial stories:

**TUI (Terminal UI) — for power users and headless servers:**
- UI-001 Add rich TUI dashboard using curses or textual (live-updating terminal UI)
- UI-002 Add TUI backtest results viewer with scrollable trade log
- UI-003 Add TUI signal history browser with filtering and search

**Web Dashboard — for browser-based monitoring and team access:**
- UI-004 Add web-based dashboard (Flask/FastAPI + simple frontend)
- UI-005 Add real-time P&L and open positions display
- UI-006 Add interactive price charts with indicator overlays
- UI-007 Add strategy performance comparison views
- UI-008 Add signal history browser with filtering
- UI-009 Add configuration editor in dashboard
- UI-010 Add trade approval/rejection UI for human-in-the-loop workflow

**GUI (Desktop) — for traders who prefer native apps:**
- UI-011 Add desktop GUI using Tkinter or PyQt (cross-platform)
- UI-012 Add portfolio allocation and exposure visualization
- UI-013 Add system tray integration with signal notifications

**Shared / API layer:**
- UI-014 Extract service layer API that all UIs consume (decouple UI from engine)
- UI-015 Add mobile-responsive design for web dashboard
- UI-010 Add API endpoints for external tool integration

### EPIC-13 Infrastructure and Deployment

Goal: make the platform production-ready with containerization, scheduling, and reliability.

Initial stories:

- INFRA-001 Add Docker containerization with docker-compose
- INFRA-002 Add PostgreSQL support for production data persistence
- INFRA-003 Add configuration versioning and environment-specific configs
- INFRA-004 Add scheduled strategy execution (cron-based market-open/close triggers)
- INFRA-005 Add automatic data download and update pipeline
- INFRA-006 Add health check endpoint for uptime monitoring
- INFRA-007 Add graceful shutdown with position safety checks
- INFRA-008 Add automatic restart and crash recovery
- INFRA-009 Add cloud deployment guide (AWS/GCP with Terraform or similar)
- INFRA-010 Add CI/CD pipeline for automated testing and deployment

---

## Priority order

Recommended phased delivery:

### Phase 1 — Foundation (Sprints 1-3)
1. EPIC-03 Signal Delivery and History (SIG-001 through SIG-003)
2. EPIC-01 Strategy Library — core indicators (STRAT-001 through STRAT-005)
3. EPIC-06 Observability and Reporting (OBS-001 through OBS-003)

### Phase 2 — Analysis and Backtesting (Sprints 4-6)
4. EPIC-09 Data Management (DATA-001 through DATA-006)
5. EPIC-02 Backtesting and Simulation (SIM-001 through SIM-005)
6. EPIC-01 Strategy Library — patterns and composites (STRAT-010 through STRAT-016)

### Phase 3 — Risk and Execution (Sprints 7-9)
7. EPIC-04 Risk Management (RISK-001 through RISK-010)
8. EPIC-05 Broker and Execution (EXEC-001 through EXEC-006)
9. EPIC-07 Human-in-the-Loop Controls (HITL-001 through HITL-005)

### Phase 4 — Intelligence (Sprints 10-12)
10. EPIC-08 Market Monitoring and Scanning (SCAN-001 through SCAN-006)
11. EPIC-10 Forecasting and ML/AI (ML-001 through ML-006)
12. EPIC-11 Portfolio Management (PORT-001 through PORT-005)

### Phase 5 — Scale and Polish (Sprints 13+)
13. EPIC-12 User Interface and Dashboard (UI-001 through UI-007)
14. EPIC-13 Infrastructure and Deployment (INFRA-001 through INFRA-005)
15. Remaining stories across all epics

---

## Next three stories (Sprint 01)

1. SIG-001 Persist emitted signals to local history
2. STRAT-001 Add RSI strategy with configurable thresholds and tests
3. OBS-001 Add structured logs for each polling cycle
