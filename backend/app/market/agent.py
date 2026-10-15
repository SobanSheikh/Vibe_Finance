from collections.abc import Callable
from math import ceil
from time import perf_counter

from app.analysis.contracts import (
    AgentName,
    AgentResult,
    AgentStatus,
    Evidence,
    EvidenceKind,
    Signal,
    SignalClassification,
    SignalDimension,
)
from app.analysis.state import AnalysisState
from app.market.analytics import (
    MarketAnalytics,
    calculate_market_analytics,
    calculate_momentum_accuracy_30d,
)
from app.market.models import MarketDataError, MarketDataProvider

LOW_VOLATILITY_THRESHOLD = 0.20
HIGH_VOLATILITY_THRESHOLD = 0.35


def _momentum_classification(value: float) -> SignalClassification:
    if value >= 0.05:
        return SignalClassification.POSITIVE
    if value <= -0.05:
        return SignalClassification.NEGATIVE
    return SignalClassification.NEUTRAL


def _volume_classification(analytics: MarketAnalytics) -> SignalClassification:
    if abs(analytics.volume_zscore_20d) < 2:
        return SignalClassification.NEUTRAL
    return _momentum_classification(analytics.return_30d)


def _volatility_classification(value: float) -> SignalClassification:
    if value < LOW_VOLATILITY_THRESHOLD:
        return SignalClassification.POSITIVE
    if value >= HIGH_VOLATILITY_THRESHOLD:
        return SignalClassification.NEGATIVE
    return SignalClassification.NEUTRAL


def _volatility_confidence(value: float) -> float:
    distance_to_boundary = min(
        abs(value - LOW_VOLATILITY_THRESHOLD),
        abs(value - HIGH_VOLATILITY_THRESHOLD),
    )
    return round(0.6 + min(distance_to_boundary / 0.1, 1) * 0.3, 2)


def _volatility_rationale(value: float) -> str:
    if value < LOW_VOLATILITY_THRESHOLD:
        band = "low"
    elif value >= HIGH_VOLATILITY_THRESHOLD:
        band = "high"
    else:
        band = "moderate"
    return (
        f"Annualized volatility is {value:.1%}, classified as {band}: below 20% is "
        "low, 20% to below 35% is moderate, and 35% or above is high."
    )


def _confidence(value: float, scale: float) -> float:
    return round(min(0.95, 0.55 + min(abs(value) / scale, 1) * 0.4), 2)


def build_market_agent(
    provider: MarketDataProvider,
) -> Callable[[AnalysisState], dict[str, AgentResult]]:
    def market_agent(state: AnalysisState) -> dict[str, AgentResult]:
        started_at = perf_counter()
        company = state["request"].company
        try:
            bars = provider.history(company.symbol, company.exchange)
            analytics = calculate_market_analytics(bars)
            signal_accuracy = calculate_momentum_accuracy_30d(bars)
        except MarketDataError as exc:
            return {
                "market_result": AgentResult(
                    agent=AgentName.MARKET,
                    status=AgentStatus.DEGRADED,
                    summary="Live market data was unavailable; no market conclusion was produced.",
                    confidence=0,
                    warnings=[str(exc)],
                    latency_ms=ceil((perf_counter() - started_at) * 1000),
                )
            }

        latest = max(bars, key=lambda item: item.trading_date)
        exchange_suffixes = {"NSE": ".NS", "BSE": ".BO"}
        market_symbol = company.symbol + exchange_suffixes.get(company.exchange.upper(), "")
        source_url = f"https://finance.yahoo.com/quote/{market_symbol}/history"
        return_evidence = Evidence(
            id=f"market-{company.symbol.lower()}-{latest.trading_date}-return-30d",
            kind=EvidenceKind.MARKET_OBSERVATION,
            title="30-session price momentum",
            observation=f"Daily close return was {analytics.return_30d:+.2%}.",
            source_name=provider.name,
            source_url=source_url,
            observed_at=latest.trading_date,
        )
        volume_evidence = Evidence(
            id=f"market-{company.symbol.lower()}-{latest.trading_date}-volume-zscore",
            kind=EvidenceKind.MARKET_OBSERVATION,
            title="20-session volume anomaly",
            observation=f"Latest volume z-score was {analytics.volume_zscore_20d:+.2f}.",
            source_name=provider.name,
            source_url=source_url,
            observed_at=latest.trading_date,
        )
        volatility_evidence = Evidence(
            id=f"market-{company.symbol.lower()}-{latest.trading_date}-volatility",
            kind=EvidenceKind.MARKET_OBSERVATION,
            title="30-session annualized volatility",
            observation=(
                "Annualized volatility from the latest 30 daily returns was "
                f"{analytics.annualized_volatility:.1%}."
            ),
            source_name=provider.name,
            source_url=source_url,
            observed_at=latest.trading_date,
        )
        momentum = _momentum_classification(analytics.return_30d)
        volume = _volume_classification(analytics)
        volatility = _volatility_classification(analytics.annualized_volatility)
        momentum_confidence = _confidence(analytics.return_30d, 0.15)
        volume_confidence = _confidence(analytics.volume_zscore_20d, 3)
        volatility_confidence = _volatility_confidence(analytics.annualized_volatility)
        return {
            "market_result": AgentResult(
                agent=AgentName.MARKET,
                status=AgentStatus.COMPLETED,
                summary=(
                    f"30-session momentum is {momentum.value}; volume confirmation is "
                    f"{volume.value}; annualized volatility is "
                    f"{analytics.annualized_volatility:.1%}."
                ),
                confidence=round(
                    (momentum_confidence + volume_confidence + volatility_confidence) / 3,
                    2,
                ),
                signals=[
                    Signal(
                        dimension=SignalDimension.PRICE_MOMENTUM,
                        classification=momentum,
                        confidence=momentum_confidence,
                        rationale=return_evidence.observation,
                        evidence_ids=[return_evidence.id],
                    ),
                    Signal(
                        dimension=SignalDimension.VOLUME_ANOMALY,
                        classification=volume,
                        confidence=volume_confidence,
                        rationale=volume_evidence.observation,
                        evidence_ids=[volume_evidence.id],
                    ),
                    Signal(
                        dimension=SignalDimension.PRICE_VOLATILITY,
                        classification=volatility,
                        confidence=volatility_confidence,
                        rationale=_volatility_rationale(analytics.annualized_volatility),
                        evidence_ids=[volatility_evidence.id],
                    ),
                ],
                evidence=[return_evidence, volume_evidence, volatility_evidence],
                metrics=(
                    {"signal_accuracy_30d": signal_accuracy} if signal_accuracy is not None else {}
                ),
                latency_ms=ceil((perf_counter() - started_at) * 1000),
            )
        }

    return market_agent
