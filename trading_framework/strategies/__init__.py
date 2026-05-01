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
# Import all strategies to trigger @register_strategy decorators
from . import sma, rsi, breakout, macd, goslin, market_profile

# Re-export for backward compatibility
from .sma import MovingAverageCrossoverStrategy
from .rsi import RSIStrategy
from .breakout import BreakoutStrategy
from .macd import MACDStrategy
from .goslin import GoslinMomentumStrategy
from .market_profile import MarketProfileStrategy
from .indicators import average, compute_rsi, compute_ema, compute_value_area

# Re-export Strategy ABC and factory from flat module (backward compat)
from ..strategy import Strategy, create_strategy
