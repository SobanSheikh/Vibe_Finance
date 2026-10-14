from datetime import UTC, datetime
from typing import Any

import httpx

from app.market.models import MarketBar, MarketDataError


class YahooFinanceProvider:
    """Daily-bar adapter for Yahoo Finance's public chart response."""

    name = "Yahoo Finance"
    base_url = "https://query1.finance.yahoo.com/v8/finance/chart"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client

    def history(self, symbol: str, exchange: str) -> list[MarketBar]:
        ticker = self._ticker(symbol, exchange)
        client = self._client or httpx.Client(timeout=10, follow_redirects=True)
        should_close = self._client is None
        try:
            response = client.get(
                f"{self.base_url}/{ticker}",
                params={"range": "6mo", "interval": "1d", "events": "history"},
                headers={"User-Agent": "VibeFinance/0.1 educational-hackathon"},
            )
            response.raise_for_status()
            return self._parse(response.json())
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise MarketDataError(f"Yahoo Finance data unavailable for {ticker}") from exc
        finally:
            if should_close:
                client.close()

    @staticmethod
    def _ticker(symbol: str, exchange: str) -> str:
        suffixes = {"NSE": ".NS", "BSE": ".BO"}
        normalized_symbol = symbol.strip().upper()
        normalized_exchange = exchange.strip().upper()
        if not normalized_symbol:
            raise MarketDataError("A market symbol is required")
        suffix = suffixes.get(normalized_exchange)
        if suffix is None:
            raise MarketDataError(f"Unsupported exchange: {normalized_exchange}")
        if normalized_symbol.endswith(suffix):
            return normalized_symbol
        return normalized_symbol + suffix

    @staticmethod
    def _parse(payload: dict[str, Any]) -> list[MarketBar]:
        chart = payload["chart"]
        if chart.get("error"):
            raise MarketDataError(str(chart["error"]))
        result = chart["result"][0]
        timestamps = result["timestamp"]
        quote = result["indicators"]["quote"][0]
        bars = [
            MarketBar(
                trading_date=datetime.fromtimestamp(timestamp, tz=UTC).date(),
                close=float(close),
                volume=int(volume),
            )
            for timestamp, close, volume in zip(timestamps, quote["close"], quote["volume"])
            if close is not None and volume is not None
        ]
        if not bars:
            raise MarketDataError("Provider returned no complete daily bars")
        return bars
