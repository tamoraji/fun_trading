"""Signal layer — aggregation, confidence scoring, and notification routing.

Processes raw strategy signals into actionable, scored recommendations:
- Aggregator: fuses signals from multiple strategies
- Confidence scoring: rates signal quality (high/medium/low)
- Router: dispatches signals to notification channels by confidence level
- Notifiers: Console, webhook, email, Telegram
- History: persistent signal recording

Dependencies: core, infra (event bus).
"""
# Re-export current notifier/history classes for backward compatibility
from ..notifiers import Notifier, ConsoleNotifier, WebhookNotifier, EmailNotifier, create_notifiers, format_signal
from ..history import SignalHistory, JsonLinesHistory, NullHistory, create_signal_history
