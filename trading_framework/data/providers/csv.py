"""CSV data provider — load price bars from local CSV files.

Useful for offline backtesting, custom datasets, and historical data
that isn't available from online providers.

Expected CSV format:
    date,open,high,low,close,volume
    2025-01-02,150.00,152.50,149.00,151.25,1234567
    2025-01-03,151.25,153.00,150.50,152.75,987654

The date column is parsed as datetime. Column names are case-insensitive.
Supports: date/datetime/timestamp for the date column.

Usage:
    from trading_framework.data.providers.csv import CSVDataProvider

    provider = CSVDataProvider(data_dir="./data")
    bars = provider.fetch_bars("AAPL", config)
    # Looks for ./data/AAPL.csv
"""
from __future__ import annotations

import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from ...models import MarketDataConfig, PriceBar
from ...data import MarketDataProvider, MarketDataError

logger = logging.getLogger(__name__)


class CSVDataProvider(MarketDataProvider):
    """Loads price bars from CSV files in a data directory.

    Each symbol maps to a file: {data_dir}/{SYMBOL}.csv

    Args:
        data_dir: Directory containing CSV files.
        date_format: strftime format for parsing dates. None = auto-detect.
    """

    def __init__(self, data_dir: str = "./data", date_format: str | None = None):
        self.data_dir = Path(data_dir)
        self.date_format = date_format

    def fetch_bars(self, symbol: str, config: MarketDataConfig) -> List[PriceBar]:
        """Load bars from {data_dir}/{symbol}.csv."""
        file_path = self.data_dir / f"{symbol.upper()}.csv"

        if not file_path.exists():
            raise MarketDataError(f"CSV file not found: {file_path}")

        bars = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                # Normalize headers to lowercase
                if reader.fieldnames:
                    reader.fieldnames = [h.strip().lower() for h in reader.fieldnames]

                for row in reader:
                    bar = self._parse_row(symbol, row)
                    if bar:
                        bars.append(bar)
        except Exception as exc:
            raise MarketDataError(f"Failed to read CSV for {symbol}: {exc}") from exc

        if not bars:
            raise MarketDataError(f"No usable price bars in {file_path}")

        # Sort by timestamp ascending
        bars.sort(key=lambda b: b.timestamp)

        logger.info("Loaded %d bars for %s from %s", len(bars), symbol, file_path)
        return bars

    def _parse_row(self, symbol: str, row: dict) -> Optional[PriceBar]:
        """Parse a single CSV row into a PriceBar."""
        try:
            # Find date column
            date_str = row.get("date") or row.get("datetime") or row.get("timestamp") or ""
            date_str = date_str.strip()
            if not date_str:
                return None

            timestamp = self._parse_date(date_str)

            close = float(row.get("close", 0))
            if close == 0:
                return None

            return PriceBar(
                symbol=symbol.upper(),
                timestamp=timestamp,
                open=float(row.get("open", close)),
                high=float(row.get("high", close)),
                low=float(row.get("low", close)),
                close=close,
                volume=int(float(row.get("volume", 0))),
            )
        except (ValueError, TypeError) as exc:
            logger.debug("Skipping invalid CSV row: %s (%s)", row, exc)
            return None

    def _parse_date(self, date_str: str) -> datetime:
        """Parse a date string, trying multiple formats."""
        if self.date_format:
            return datetime.strptime(date_str, self.date_format).replace(tzinfo=timezone.utc)

        # Auto-detect common formats
        for fmt in [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
        ]:
            try:
                return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue

        # Try ISO format
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            pass

        raise ValueError(f"Cannot parse date: '{date_str}'")
