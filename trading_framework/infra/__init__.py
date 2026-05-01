"""Infrastructure layer — event bus, plugin registry, config loading, scheduling.

Provides the foundational infrastructure that all higher layers use:
- Event bus for decoupled communication between components
- Plugin registry for strategy auto-discovery
- Configuration loading and validation
- Task scheduling (interval + cron-like)

Dependencies: core only.
"""
from .event_bus import EventBus
from .plugin import register_strategy, create_strategy_from_registry, list_strategies
