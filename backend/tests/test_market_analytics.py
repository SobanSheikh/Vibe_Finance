from datetime import date, timedelta

import pytest

from app.market.analytics import calculate_market_analytics, calculate_momentum_accuracy_30d
from app.market.models import MarketBar, MarketDataError


def market_bars(count: int = 31) -> list[MarketBar]:
    first_day = date(2026, 1, 1)
    return [
        MarketBar(first_day + timedelta(days=index), 100 + index, 1_000 + index * 10)
        for index in range(count)
    ]


def test_market_analytics_calculates_momentum_volume_and_volatility() -> None:
    bars = market_bars()
    bars[-1] = MarketBar(bars[-1].trading_date, close=140, volume=5_000)

    result = calculate_market_analytics(bars)

    assert result.return_30d == pytest.approx(0.4)
    assert result.volume_zscore_20d > 2
    assert result.annualized_volatility > 0


def test_market_analytics_requires_enough_complete_history() -> None:
    with pytest.raises(MarketDataError, match="31 complete"):
        calculate_market_analytics(market_bars(30))


def test_momentum_accuracy_uses_only_completed_forward_windows() -> None:
    bars = market_bars(91)

    assert calculate_momentum_accuracy_30d(bars) == 1.0
    assert calculate_momentum_accuracy_30d(bars[:60]) is None
