"""Execution layer — broker abstraction and order management.

Handles the bridge from signals to actual (or simulated) trades:
- Broker ABC: unified interface for paper and live trading
- Paper trading: simulated execution with portfolio tracking
- Order manager: signal -> approval gate -> order submission
- Position sizer: compute trade size based on risk parameters

Dependencies: core, infra (event bus).
"""
# Re-export current paper trading for backward compatibility
from ..paper import PaperPortfolio, Position, OrderRecord
