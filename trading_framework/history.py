from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from .models import Signal, SignalHistorySettings


class SignalHistory(ABC):
    @abstractmethod
    def write(self, signal: Signal) -> None:
        raise NotImplementedError

    @abstractmethod
    def read_all(self) -> List[dict]:
        raise NotImplementedError


class JsonLinesHistory(SignalHistory):
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def write(self, signal: Signal) -> None:
        record = {
            "symbol": signal.symbol,
            "action": signal.action,
            "price": signal.price,
            "timestamp": signal.timestamp.isoformat(),
            "reason": signal.reason,
            "strategy_name": signal.strategy_name,
            "details": signal.details,
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def read_all(self) -> List[dict]:
        if not self.path.exists():
            return []
        records = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records


class NullHistory(SignalHistory):
    """No-op history used when signal history is disabled."""

    def write(self, signal: Signal) -> None:
        pass

    def read_all(self) -> List[dict]:
        return []


def create_signal_history(settings: SignalHistorySettings | None) -> SignalHistory:
    if settings is None or not settings.enabled:
        return NullHistory()
    return JsonLinesHistory(path=settings.path)
