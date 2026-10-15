from dataclasses import dataclass
from math import sqrt
from statistics import pstdev, stdev

from app.market.models import MarketBar, MarketDataError


@dataclass(frozen=True)
class MarketAnalytics:
    return_30d: float
    volume_zscore_20d: float
    annualized_volatility: float


def calculate_momentum_accuracy_30d(bars: list[MarketBar]) -> float | None:
    """Backtest 30-session momentum labels against the following 30 sessions."""
    ordered = sorted(bars, key=lambda item: item.trading_date)
    if len(ordered) < 61:
        return None

    def classify(value: float) -> int:
        if value >= 0.05:
            return 1
        if value <= -0.05:
            return -1
        return 0

    outcomes = []
    for index in range(30, len(ordered) - 30):
        momentum = ordered[index].close / ordered[index - 30].close - 1
        forward_return = ordered[index + 30].close / ordered[index].close - 1
        outcomes.append(classify(momentum) == classify(forward_return))
    return round(sum(outcomes) / len(outcomes), 4) if outcomes else None


def calculate_market_analytics(bars: list[MarketBar]) -> MarketAnalytics:
    """Calculate signals from chronological, daily market bars."""

    if len(bars) < 31:
        raise MarketDataError("At least 31 complete daily bars are required")
    ordered = sorted(bars, key=lambda item: item.trading_date)
    if any(item.close <= 0 or item.volume < 0 for item in ordered):
        raise MarketDataError("Market bars contain invalid close or volume values")

    return_30d = ordered[-1].close / ordered[-31].close - 1
    baseline_volumes = [item.volume for item in ordered[-21:-1]]
    volume_deviation = pstdev(baseline_volumes)
    volume_zscore = (
        (ordered[-1].volume - sum(baseline_volumes) / len(baseline_volumes)) / volume_deviation
        if volume_deviation
        else 0.0
    )
    closes = [item.close for item in ordered[-31:]]
    daily_returns = [current / previous - 1 for previous, current in zip(closes, closes[1:])]
    return MarketAnalytics(
        return_30d=return_30d,
        volume_zscore_20d=volume_zscore,
        annualized_volatility=stdev(daily_returns) * sqrt(252),
    )
