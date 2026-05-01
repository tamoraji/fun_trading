from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Callable, Dict, List, Tuple

from .core.events import SignalEmitted, SignalBlocked, CycleStarted, CycleCompleted, DataError
from .data import MarketDataProvider
from .history import SignalHistory, NullHistory
from .infra.event_bus import EventBus
from .models import AppSettings, HOLD, Signal
from .notifiers import Notifier
from .risk import NullRiskManager
from .strategy import Strategy


class TradingEngine:
    def __init__(
        self,
        settings: AppSettings,
        provider: MarketDataProvider,
        strategy: Strategy | None = None,
        notifiers: List[Notifier] | None = None,
        history: SignalHistory | None = None,
        clock: Callable[[], datetime] | None = None,
        sleeper: Callable[[float], None] | None = None,
        logger: Callable[[str], None] | None = None,
        strategies: List[Strategy] | None = None,
        risk_manager=None,
        portfolio=None,
        event_bus: EventBus | None = None,
    ):
        self.settings = settings
        self.provider = provider
        self.strategies = strategies or ([strategy] if strategy else [])
        self.notifiers = notifiers or []
        self.history = history or NullHistory()
        self.risk_manager = risk_manager or NullRiskManager()
        self.portfolio = portfolio
        self.event_bus = event_bus or EventBus()
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.sleeper = sleeper or time.sleep
        self.logger = logger or print
        self._last_signal_keys: Dict[str, Tuple[str, str]] = {}

    def run_cycle(self, now: datetime | None = None) -> List[Signal]:
        cycle_time = now or self.clock()
        if self.settings.market_session and not self.settings.market_session.is_open(cycle_time):
            self.logger("[skip] market session is closed")
            return []

        self.logger(f"[cycle_start] symbols={self.settings.symbols}")
        self.event_bus.publish(CycleStarted(timestamp=cycle_time, symbols=self.settings.symbols))

        started = time.monotonic()
        emitted: List[Signal] = []
        holds = 0
        errors = 0

        for symbol in self.settings.symbols:
            try:
                bars = self.provider.fetch_bars(symbol, self.settings.market_data)
            except Exception as exc:  # pragma: no cover - defensive logging
                self.logger(f"[error] {symbol}: {exc}")
                self.event_bus.publish(DataError(symbol=symbol, error=str(exc)))
                errors += 1
                continue

            for strategy in self.strategies:
                try:
                    signal = strategy.evaluate(symbol, bars)
                except Exception as exc:
                    self.logger(f"[error] {symbol}/{strategy.name}: {exc}")
                    errors += 1
                    continue

                if signal.action == HOLD:
                    self.logger(f"[hold] {symbol}/{signal.strategy_name}: {signal.reason}")
                    holds += 1
                    continue

                # Run through risk filters
                signal = self.risk_manager.evaluate(signal, bars)
                if signal.action == HOLD:
                    risk_filter = signal.details.get("risk_filter", "unknown")
                    self.logger(f"[risk] {symbol}/{signal.strategy_name}: blocked by {risk_filter} — {signal.reason}")
                    self.event_bus.publish(SignalBlocked(signal=signal, reason=signal.reason, filter_name=risk_filter))
                    holds += 1
                    continue

                dedup_key = f"{symbol}:{signal.strategy_name}"
                signal_key = (signal.action, signal.timestamp.isoformat())
                if self._last_signal_keys.get(dedup_key) == signal_key:
                    self.logger(f"[dup] {symbol}/{signal.strategy_name}: already sent {signal.action} for this bar")
                    continue

                for notifier in self.notifiers:
                    notifier.send(signal)

                try:
                    self.history.write(signal)
                except Exception as exc:
                    self.logger(f"[error] history write failed for {symbol}: {exc}")

                self._last_signal_keys[dedup_key] = signal_key
                self.logger(f"[signal] {symbol}/{signal.strategy_name}: {signal.action} at {signal.price:.2f}")
                self.event_bus.publish(SignalEmitted(signal=signal, bars=bars))
                emitted.append(signal)

                if self.portfolio:
                    order = self.portfolio.execute(signal)
                    if order:
                        pnl_str = f" P&L: ${order.pnl:,.2f}" if order.pnl is not None else ""
                        self.logger(f"[paper] {symbol}: {order.action} {order.quantity:.4f} @ ${order.price:.2f}{pnl_str}")

        elapsed = time.monotonic() - started
        self.logger(
            f"[cycle_end] signals={len(emitted)} holds={holds} errors={errors} "
            f"elapsed={elapsed:.3f}s"
        )
        self.event_bus.publish(CycleCompleted(
            timestamp=cycle_time, signals_emitted=len(emitted),
            holds=holds, errors=errors, elapsed_seconds=elapsed,
        ))

        if self.portfolio:
            self.logger(
                f"[portfolio] cash=${self.portfolio.cash:,.2f} "
                f"positions={len(self.portfolio.positions)} "
                f"realized_pnl=${self.portfolio.realized_pnl():,.2f}"
            )

        return emitted

    def run_forever(self) -> None:
        while True:
            started = time.monotonic()
            self.run_cycle()
            elapsed = time.monotonic() - started
            sleep_for = max(0.0, self.settings.poll_interval_seconds - elapsed)
            self.sleeper(sleep_for)
