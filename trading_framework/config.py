from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from .models import (
    AppSettings,
    MarketDataConfig,
    MarketSession,
    NotifierSettings,
    SignalHistorySettings,
    StrategySettings,
)


def load_settings(path: str | Path) -> AppSettings:
    config_path = Path(path)
    raw = json.loads(config_path.read_text(encoding="utf-8"))

    symbols = _load_symbols(raw.get("symbols"))
    poll_interval_seconds = int(raw.get("poll_interval_seconds", 300))
    market_data = _load_market_data(raw.get("market_data", {}))
    strategy = _load_strategy(raw.get("strategy"))
    market_session = _load_market_session(raw.get("market_session"))
    notifiers = _load_notifiers(raw.get("notifiers", [{"type": "console"}]))
    signal_history = _load_signal_history(raw.get("signal_history"))

    return AppSettings(
        symbols=symbols,
        poll_interval_seconds=poll_interval_seconds,
        market_data=market_data,
        strategy=strategy,
        notifiers=notifiers,
        market_session=market_session,
        signal_history=signal_history,
    )


def _load_symbols(raw_symbols: Any) -> List[str]:
    if not raw_symbols or not isinstance(raw_symbols, list):
        raise ValueError("Config must include a non-empty 'symbols' list.")

    symbols = [str(symbol).strip().upper() for symbol in raw_symbols if str(symbol).strip()]
    if not symbols:
        raise ValueError("Config contains no usable symbols.")
    return symbols


def _load_market_data(raw: Dict[str, Any]) -> MarketDataConfig:
    return MarketDataConfig(
        provider=str(raw.get("provider", "yahoo")).strip().lower(),
        bar_interval=str(raw.get("bar_interval", "5m")).strip(),
        lookback=str(raw.get("lookback", "5d")).strip(),
        timeout_seconds=int(raw.get("timeout_seconds", 10)),
    )


def _load_strategy(raw: Any) -> StrategySettings:
    if not isinstance(raw, dict) or not raw.get("name"):
        raise ValueError("Config must include a strategy with a 'name'.")

    params = raw.get("params", {})
    if params is None:
        params = {}
    if not isinstance(params, dict):
        raise ValueError("Strategy params must be an object.")

    return StrategySettings(name=str(raw["name"]).strip().lower(), params=params)


def _load_market_session(raw: Any) -> MarketSession | None:
    if not isinstance(raw, dict) or not raw.get("enabled", True):
        return None

    timezone_name = str(raw.get("timezone", "America/New_York")).strip()
    weekdays = [int(day) for day in raw.get("weekdays", [0, 1, 2, 3, 4])]
    start = _parse_time(str(raw.get("start", "09:30")))
    end = _parse_time(str(raw.get("end", "16:00")))
    return MarketSession(
        timezone_name=timezone_name,
        weekdays=weekdays,
        start=start,
        end=end,
    )


def _load_signal_history(raw: Any) -> SignalHistorySettings | None:
    if not isinstance(raw, dict):
        return None
    return SignalHistorySettings(
        enabled=bool(raw.get("enabled", True)),
        path=str(raw.get("path", "signal_history.jsonl")),
    )


def _load_notifiers(raw_notifiers: Any) -> List[NotifierSettings]:
    if not isinstance(raw_notifiers, list) or not raw_notifiers:
        return [NotifierSettings(type="console")]

    notifiers: List[NotifierSettings] = []
    for entry in raw_notifiers:
        if not isinstance(entry, dict):
            continue

        notifier_type = str(entry.get("type", "")).strip().lower()
        if not notifier_type:
            continue

        enabled = bool(entry.get("enabled", True))
        params = {key: value for key, value in entry.items() if key not in {"type", "enabled"}}
        notifiers.append(
            NotifierSettings(type=notifier_type, enabled=enabled, params=params)
        )

    return notifiers or [NotifierSettings(type="console")]


def _parse_time(value: str):
    return datetime.strptime(value, "%H:%M").time()
