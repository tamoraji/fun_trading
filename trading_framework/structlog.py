from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable, List


class StructuredLogger:
    """JSON-structured logger for the trading engine.

    Callable — can be used as a drop-in replacement for the plain print logger.
    """

    def __init__(self, sink: Callable[[str], None] | None = None):
        self._sink = sink or print

    def __call__(self, message: str) -> None:
        self.log(message)

    def _emit(self, event: str, **fields: Any) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **fields,
        }
        self._sink(json.dumps(record))

    def log(self, message: str) -> None:
        self._emit("log", message=message)

    def cycle_start(self, symbols: List[str]) -> None:
        self._emit("cycle_start", symbols=symbols, symbol_count=len(symbols))

    def cycle_end(
        self,
        signals_emitted: int,
        holds: int,
        errors: int,
        elapsed_seconds: float,
    ) -> None:
        self._emit(
            "cycle_end",
            signals_emitted=signals_emitted,
            holds=holds,
            errors=errors,
            elapsed_seconds=round(elapsed_seconds, 3),
        )

    def signal_emitted(self, symbol: str, action: str, price: float, strategy: str) -> None:
        self._emit("signal_emitted", symbol=symbol, action=action, price=price, strategy=strategy)

    def error(self, symbol: str, message: str) -> None:
        self._emit("error", symbol=symbol, message=message)

    def skip(self, reason: str) -> None:
        self._emit("skip", reason=reason)
