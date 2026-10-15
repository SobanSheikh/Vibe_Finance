from datetime import date

import httpx

from app.market.yahoo import YahooFinanceProvider


def _chart_response() -> dict[str, object]:
    return {
        "chart": {
            "error": None,
            "result": [
                {
                    "timestamp": [1760400000, 1760486400],
                    "indicators": {"quote": [{"close": [1_400.5, None], "volume": [1000, 2000]}]},
                }
            ],
        }
    }


def test_yahoo_provider_maps_nse_ticker_and_parses_complete_bars() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/RELIANCE.NS")
        return httpx.Response(200, json=_chart_response())

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = YahooFinanceProvider(client)

    bars = provider.history("RELIANCE", "NSE")

    assert len(bars) == 1
    assert bars[0].trading_date == date(2025, 10, 14)
    assert bars[0].close == 1_400.5
    assert bars[0].volume == 1000
    client.close()


def test_yahoo_provider_uses_unsuffixed_nasdaq_ticker() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/GOOGL")
        return httpx.Response(200, json=_chart_response())

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = YahooFinanceProvider(client)

    assert provider.history("GOOGL", "NASDAQ")
    client.close()
