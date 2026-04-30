from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .models import BUY, HOLD, SELL, PriceBar, Signal


@dataclass
class RiskSettings:
    """Configuration for all risk filters."""
    cooldown_seconds: int = 0           # Min seconds between signals for same symbol. 0 = disabled.
    position_aware: bool = False        # Track positions and block conflicting signals.
    stop_loss_pct: float = 0.0          # Stop-loss % below entry. 0 = disabled. Added to signal details.
    take_profit_pct: float = 0.0        # Take-profit % above entry. 0 = disabled. Added to signal details.
    min_volume: int = 0                 # Minimum volume on current bar. 0 = disabled.
    max_signals_per_day: int = 0        # Max signals per symbol per day. 0 = unlimited.


class RiskManager:
    """Evaluates signals through a chain of risk filters.

    Tracks state (positions, last signal times) across cycles.
    """

    def __init__(self, settings: RiskSettings):
        self.settings = settings
        # Cooldown tracking: symbol -> last signal datetime
        self._last_signal_time: Dict[str, datetime] = {}
        # Position tracking: symbol -> "long" | "short" | None
        self._positions: Dict[str, Optional[str]] = {}
        # Daily signal count: "symbol:YYYY-MM-DD" -> count
        self._daily_counts: Dict[str, int] = {}

    def evaluate(self, signal: Signal, bars: List[PriceBar]) -> Signal:
        """Run signal through all risk filters. Returns original signal or HOLD."""
        if signal.action == HOLD:
            return signal

        # Filter 1: Cooldown
        blocked = self._check_cooldown(signal)
        if blocked:
            return blocked

        # Filter 2: Daily signal limit
        blocked = self._check_daily_limit(signal)
        if blocked:
            return blocked

        # Filter 3: Position awareness
        blocked = self._check_position(signal)
        if blocked:
            return blocked

        # Filter 4: Minimum volume
        blocked = self._check_volume(signal, bars)
        if blocked:
            return blocked

        # Passed all filters — annotate with SL/TP if configured
        signal = self._annotate_sl_tp(signal)

        # Update state
        self._last_signal_time[signal.symbol] = signal.timestamp
        self._update_position(signal)
        self._increment_daily_count(signal)

        return signal

    def _check_cooldown(self, signal: Signal) -> Signal | None:
        if self.settings.cooldown_seconds <= 0:
            return None
        last = self._last_signal_time.get(signal.symbol)
        if last is None:
            return None
        elapsed = (signal.timestamp - last).total_seconds()
        if elapsed < self.settings.cooldown_seconds:
            return Signal(
                symbol=signal.symbol, action=HOLD, price=signal.price,
                timestamp=signal.timestamp,
                reason=f"Cooldown active ({int(elapsed)}s < {self.settings.cooldown_seconds}s).",
                strategy_name=signal.strategy_name,
                details={**signal.details, "risk_filter": "cooldown"},
            )
        return None

    def _check_daily_limit(self, signal: Signal) -> Signal | None:
        if self.settings.max_signals_per_day <= 0:
            return None
        day_key = f"{signal.symbol}:{signal.timestamp.strftime('%Y-%m-%d')}"
        count = self._daily_counts.get(day_key, 0)
        if count >= self.settings.max_signals_per_day:
            return Signal(
                symbol=signal.symbol, action=HOLD, price=signal.price,
                timestamp=signal.timestamp,
                reason=f"Daily signal limit reached ({count}/{self.settings.max_signals_per_day}).",
                strategy_name=signal.strategy_name,
                details={**signal.details, "risk_filter": "daily_limit"},
            )
        return None

    def _check_position(self, signal: Signal) -> Signal | None:
        if not self.settings.position_aware:
            return None
        pos = self._positions.get(signal.symbol)
        if pos == "long" and signal.action == BUY:
            return Signal(
                symbol=signal.symbol, action=HOLD, price=signal.price,
                timestamp=signal.timestamp,
                reason="Already in long position.",
                strategy_name=signal.strategy_name,
                details={**signal.details, "risk_filter": "position_aware"},
            )
        if pos == "short" and signal.action == SELL:
            return Signal(
                symbol=signal.symbol, action=HOLD, price=signal.price,
                timestamp=signal.timestamp,
                reason="Already in short position.",
                strategy_name=signal.strategy_name,
                details={**signal.details, "risk_filter": "position_aware"},
            )
        return None

    def _check_volume(self, signal: Signal, bars: List[PriceBar]) -> Signal | None:
        if self.settings.min_volume <= 0 or not bars:
            return None
        current_volume = bars[-1].volume
        if current_volume < self.settings.min_volume:
            return Signal(
                symbol=signal.symbol, action=HOLD, price=signal.price,
                timestamp=signal.timestamp,
                reason=f"Volume too low ({current_volume} < {self.settings.min_volume}).",
                strategy_name=signal.strategy_name,
                details={**signal.details, "risk_filter": "min_volume"},
            )
        return None

    def _annotate_sl_tp(self, signal: Signal) -> Signal:
        extra: Dict[str, Any] = {}
        if self.settings.stop_loss_pct > 0:
            if signal.action == BUY:
                extra["stop_loss"] = round(signal.price * (1 - self.settings.stop_loss_pct / 100), 2)
            elif signal.action == SELL:
                extra["stop_loss"] = round(signal.price * (1 + self.settings.stop_loss_pct / 100), 2)
        if self.settings.take_profit_pct > 0:
            if signal.action == BUY:
                extra["take_profit"] = round(signal.price * (1 + self.settings.take_profit_pct / 100), 2)
            elif signal.action == SELL:
                extra["take_profit"] = round(signal.price * (1 - self.settings.take_profit_pct / 100), 2)
        if not extra:
            return signal
        return Signal(
            symbol=signal.symbol, action=signal.action, price=signal.price,
            timestamp=signal.timestamp, reason=signal.reason,
            strategy_name=signal.strategy_name,
            details={**signal.details, **extra},
        )

    def _update_position(self, signal: Signal) -> None:
        if not self.settings.position_aware:
            return
        pos = self._positions.get(signal.symbol)
        if signal.action == BUY:
            if pos == "short":
                self._positions[signal.symbol] = None  # closed short
            else:
                self._positions[signal.symbol] = "long"
        elif signal.action == SELL:
            if pos == "long":
                self._positions[signal.symbol] = None  # closed long
            else:
                self._positions[signal.symbol] = "short"

    def _increment_daily_count(self, signal: Signal) -> None:
        if self.settings.max_signals_per_day <= 0:
            return
        day_key = f"{signal.symbol}:{signal.timestamp.strftime('%Y-%m-%d')}"
        self._daily_counts[day_key] = self._daily_counts.get(day_key, 0) + 1


class NullRiskManager:
    """Pass-through risk manager when no risk filters are configured."""

    def evaluate(self, signal: Signal, bars: List[PriceBar]) -> Signal:
        return signal
