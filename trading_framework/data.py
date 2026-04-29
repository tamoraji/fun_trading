from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import MarketDataConfig, PriceBar


class MarketDataError(RuntimeError):
    pass


class MarketDataProvider(ABC):
    @abstractmethod
    def fetch_bars(self, symbol: str, config: MarketDataConfig) -> List[PriceBar]:
        raise NotImplementedError


class YahooFinanceProvider(MarketDataProvider):
    base_url = "https://query1.finance.yahoo.com/v8/finance/chart"

    def fetch_bars(self, symbol: str, config: MarketDataConfig) -> List[PriceBar]:
        query = urlencode(
            {
                "interval": config.bar_interval,
                "range": config.lookback,
                "includePrePost": "false",
                "events": "div,splits",
            }
        )
        url = f"{self.base_url}/{symbol}?{query}"
        request = Request(url, headers={"User-Agent": "Mozilla/5.0"})

        with urlopen(request, timeout=config.timeout_seconds) as response:
            payload = json.load(response)

        chart = payload.get("chart", {})
        if chart.get("error"):
            raise MarketDataError(str(chart["error"]))

        results = chart.get("result") or []
        if not results:
            raise MarketDataError(f"No chart data returned for {symbol}.")

        result = results[0]
        timestamps = result.get("timestamp") or []
        quotes = (result.get("indicators", {}).get("quote") or [{}])[0]
        opens = quotes.get("open") or []
        highs = quotes.get("high") or []
        lows = quotes.get("low") or []
        closes = quotes.get("close") or []
        volumes = quotes.get("volume") or []

        bars: List[PriceBar] = []
        for index, raw_timestamp in enumerate(timestamps):
            close = _coerce_float(_value_at(closes, index))
            if close is None:
                continue

            open_value = _coerce_float(_value_at(opens, index, close)) or close
            high_value = _coerce_float(_value_at(highs, index, close)) or close
            low_value = _coerce_float(_value_at(lows, index, close)) or close
            volume_value = int(_coerce_float(_value_at(volumes, index, 0)) or 0)

            bars.append(
                PriceBar(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(raw_timestamp, tz=timezone.utc),
                    open=open_value,
                    high=high_value,
                    low=low_value,
                    close=close,
                    volume=volume_value,
                )
            )

        if not bars:
            raise MarketDataError(f"No usable price bars returned for {symbol}.")

        return bars


def create_market_data_provider(config: MarketDataConfig) -> MarketDataProvider:
    if config.provider == "yahoo":
        return YahooFinanceProvider()
    raise ValueError(f"Unsupported market data provider: {config.provider}")


def _value_at(values, index: int, default=None):
    try:
        return values[index]
    except (IndexError, TypeError):
        return default


def _coerce_float(value) -> Optional[float]:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None
