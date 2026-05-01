"""Strategy layer — trading strategy implementations as plugins.

Each strategy is a separate module implementing the Strategy interface.
Strategies are registered via the @register_strategy decorator and
auto-discovered when this package is imported.

Available strategies:
- sma             — Moving Average Crossover
- rsi             — Relative Strength Index
- breakout        — Channel Breakout with volume confirmation
- macd            — MACD signal line crossover
- goslin          — Goslin Three-Line Momentum
- market_profile  — Market Profile Value Area
- composite       — Weighted multi-strategy voting          [planned]

Shared utilities in indicators.py (RSI, EMA, SMA, value area computation).

Dependencies: core only.
"""
# Re-export current strategy classes for backward compatibility
from ..strategy import (
    Strategy,
    MovingAverageCrossoverStrategy,
    RSIStrategy,
    BreakoutStrategy,
    MACDStrategy,
    GoslinMomentumStrategy,
    MarketProfileStrategy,
    create_strategy,
)
