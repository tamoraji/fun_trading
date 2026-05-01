"""Infrastructure layer — event bus, plugin registry, config loading, scheduling.

Provides the foundational infrastructure that all higher layers use:
- Event bus for decoupled communication between components
- Plugin registry for strategy auto-discovery
- Configuration loading and validation
- Task scheduling (interval + cron-like)

Dependencies: core only.
"""
