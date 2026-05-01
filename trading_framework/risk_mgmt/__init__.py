"""Risk management layer — signal filtering and capital protection.

Filters that evaluate signals before execution:
- Cooldown: minimum time between signals
- Position awareness: prevent conflicting orders
- Volume guard: require minimum volume
- Stop-loss / take-profit: price level annotation
- Daily limits: cap signals per symbol per day
- Circuit breaker: halt on excessive losses          [planned]

Dependencies: core only.
"""
# Re-export current risk classes for backward compatibility
from ..risk import RiskSettings, RiskManager, NullRiskManager
