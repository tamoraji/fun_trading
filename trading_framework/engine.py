from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Callable, Dict, List, Tuple

from .data import MarketDataProvider
from .models import AppSettings, HOLD, Signal
from .notifiers import Notifier
from .strategy import Strategy


class TradingEngine:
    def __init__(
        self,
        settings: AppSettings,
        provider: MarketDataProvider,
        strategy: Strategy,
        notifiers: List[Notifier],
        clock: Callable[[], datetime] | None = None,
        sleeper: Callable[[float], None] | None = None,
        logger: Callable[[str], None] | None = None,
    ):
        self.settings = settings
        self.provider = provider
        self.strategy = strategy
        self.notifiers = notifiers
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.sleeper = sleeper or time.sleep
        self.logger = logger or print
        self._last_signal_keys: Dict[str, Tuple[str, str]] = {}

    def run_cycle(self, now: datetime | None = None) -> List[Signal]:
        cycle_time = now or self.clock()
        if self.settings.market_session and not self.settings.market_session.is_open(cycle_time):
            self.logger("[skip] market session is closed")
            return []

        emitted: List[Signal] = []
        for symbol in self.settings.symbols:
            try:
                bars = self.provider.fetch_bars(symbol, self.settings.market_data)
                signal = self.strategy.evaluate(symbol, bars)
            except Exception as exc:  # pragma: no cover - defensive logging
                self.logger(f"[error] {symbol}: {exc}")
                continue

            if signal.action == HOLD:
                self.logger(f"[hold] {symbol}: {signal.reason}")
                continue

            signal_key = (signal.action, signal.timestamp.isoformat())
            if self._last_signal_keys.get(symbol) == signal_key:
                self.logger(f"[dup] {symbol}: already sent {signal.action} for this bar")
                continue

            for notifier in self.notifiers:
                notifier.send(signal)

            self._last_signal_keys[symbol] = signal_key
            self.logger(f"[signal] {symbol}: {signal.action} at {signal.price:.2f}")
            emitted.append(signal)

        return emitted

    def run_forever(self) -> None:
        while True:
            started = time.monotonic()
            self.run_cycle()
            elapsed = time.monotonic() - started
            sleep_for = max(0.0, self.settings.poll_interval_seconds - elapsed)
            self.sleeper(sleep_for)
