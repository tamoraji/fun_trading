from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from .data import MarketDataProvider
from .models import MarketDataConfig, PriceBar


class CachedDataProvider(MarketDataProvider):
    """Wraps another provider with a SQLite cache layer."""

    def __init__(
        self,
        upstream: MarketDataProvider,
        cache_dir: str = ".cache",
        ttl_seconds: int = 300,
    ):
        self.upstream = upstream
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.cache_dir / "market_data.db"
        self.ttl_seconds = ttl_seconds
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bars (
                    symbol TEXT NOT NULL,
                    bar_interval TEXT NOT NULL,
                    timestamp_utc TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume INTEGER NOT NULL,
                    PRIMARY KEY (symbol, bar_interval, timestamp_utc)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fetch_log (
                    symbol TEXT NOT NULL,
                    bar_interval TEXT NOT NULL,
                    lookback TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    PRIMARY KEY (symbol, bar_interval, lookback)
                )
            """)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def fetch_bars(self, symbol: str, config: MarketDataConfig) -> List[PriceBar]:
        # Check if cache is fresh
        if self._is_fresh(symbol, config):
            cached = self._read_cache(symbol, config.bar_interval)
            if cached:
                return cached

        # Fetch from upstream
        bars = self.upstream.fetch_bars(symbol, config)

        # Save to cache
        self._write_cache(symbol, config, bars)

        return bars

    def _is_fresh(self, symbol: str, config: MarketDataConfig) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT fetched_at FROM fetch_log WHERE symbol=? AND bar_interval=? AND lookback=?",
                (symbol, config.bar_interval, config.lookback),
            ).fetchone()
        if row is None:
            return False
        fetched_at = datetime.fromisoformat(row[0])
        age = (datetime.now(timezone.utc) - fetched_at).total_seconds()
        return age < self.ttl_seconds

    def _read_cache(self, symbol: str, bar_interval: str) -> List[PriceBar]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT timestamp_utc, open, high, low, close, volume FROM bars "
                "WHERE symbol=? AND bar_interval=? ORDER BY timestamp_utc",
                (symbol, bar_interval),
            ).fetchall()
        return [
            PriceBar(
                symbol=symbol,
                timestamp=datetime.fromisoformat(row[0]),
                open=row[1], high=row[2], low=row[3], close=row[4], volume=int(row[5]),
            )
            for row in rows
        ]

    def _write_cache(self, symbol: str, config: MarketDataConfig, bars: List[PriceBar]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            # Upsert bars
            conn.executemany(
                "INSERT OR REPLACE INTO bars (symbol, bar_interval, timestamp_utc, open, high, low, close, volume) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (symbol, config.bar_interval, bar.timestamp.isoformat(),
                     bar.open, bar.high, bar.low, bar.close, bar.volume)
                    for bar in bars
                ],
            )
            # Update fetch log
            conn.execute(
                "INSERT OR REPLACE INTO fetch_log (symbol, bar_interval, lookback, fetched_at) "
                "VALUES (?, ?, ?, ?)",
                (symbol, config.bar_interval, config.lookback, now),
            )

    def clear_cache(self, symbol: str | None = None) -> None:
        """Clear cached data. If symbol is given, clear only that symbol."""
        with self._connect() as conn:
            if symbol:
                conn.execute("DELETE FROM bars WHERE symbol=?", (symbol,))
                conn.execute("DELETE FROM fetch_log WHERE symbol=?", (symbol,))
            else:
                conn.execute("DELETE FROM bars")
                conn.execute("DELETE FROM fetch_log")

    def cache_stats(self) -> dict:
        """Return cache statistics."""
        with self._connect() as conn:
            bar_count = conn.execute("SELECT COUNT(*) FROM bars").fetchone()[0]
            symbol_count = conn.execute("SELECT COUNT(DISTINCT symbol) FROM bars").fetchone()[0]
            fetch_count = conn.execute("SELECT COUNT(*) FROM fetch_log").fetchone()[0]
        return {
            "bars": bar_count,
            "symbols": symbol_count,
            "fetches": fetch_count,
            "db_path": str(self.db_path),
        }
