from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

BUY = "BUY"
SELL = "SELL"
HOLD = "HOLD"


@dataclass(frozen=True)
class PriceBar:
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(frozen=True)
class Signal:
    symbol: str
    action: str
    price: float
    timestamp: datetime
    reason: str
    strategy_name: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MarketDataConfig:
    provider: str = "yahoo"
    bar_interval: str = "5m"
    lookback: str = "5d"
    timeout_seconds: int = 10


@dataclass(frozen=True)
class StrategySettings:
    name: str
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NotifierSettings:
    type: str
    enabled: bool = True
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MarketSession:
    timezone_name: str
    weekdays: List[int]
    start: time
    end: time

    def is_open(self, current_time: datetime) -> bool:
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        localized = current_time.astimezone(ZoneInfo(self.timezone_name))
        if localized.weekday() not in self.weekdays:
            return False

        local_time = localized.time().replace(tzinfo=None)
        return self.start <= local_time <= self.end


@dataclass(frozen=True)
class SignalHistorySettings:
    enabled: bool = True
    path: str = "signal_history.jsonl"


@dataclass(frozen=True)
class AppSettings:
    symbols: List[str]
    poll_interval_seconds: int
    market_data: MarketDataConfig
    strategy: StrategySettings
    notifiers: List[NotifierSettings]
    market_session: Optional[MarketSession] = None
    signal_history: Optional[SignalHistorySettings] = None
