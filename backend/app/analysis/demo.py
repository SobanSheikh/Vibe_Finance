from math import ceil
from time import perf_counter

from app.analysis.contracts import (
    AgentName,
    AgentResult,
    AgentStatus,
    Evidence,
    EvidenceConflict,
    EvidenceKind,
    Recommendation,
    RecommendationAction,
    RiskTolerance,
    SessionMetrics,
    Signal,
    SignalClassification,
    SignalDimension,
)
from app.analysis.graph import AnalysisGraphNodes, AnalysisNode
from app.analysis.state import AnalysisState


def _market_agent(_: AnalysisState) -> dict[str, AgentResult]:
    started_at = perf_counter()
    evidence = [
        Evidence(
            id="demo-market-return-30d",
            kind=EvidenceKind.MARKET_OBSERVATION,
            title="30-day adjusted return",
            observation="Synthetic adjusted close increased by 8.42% over 30 sessions.",
            source_name="VibeFinance deterministic demo dataset",
            source_url="demo://market/reliance/2026-10-14",
            is_synthetic=True,
        ),
        Evidence(
            id="demo-market-volume-zscore",
            kind=EvidenceKind.MARKET_OBSERVATION,
            title="Trading-volume anomaly",
            observation="Synthetic latest-session volume has a 20-day z-score of +2.31.",
            source_name="VibeFinance deterministic demo dataset",
            source_url="demo://market/reliance/2026-10-14",
            is_synthetic=True,
        ),
        Evidence(
            id="demo-market-volatility",
            kind=EvidenceKind.MARKET_OBSERVATION,
            title="30-session annualized volatility",
            observation="Synthetic annualized volatility from 30 daily returns is 22.0%.",
            source_name="VibeFinance deterministic demo dataset",
            source_url="demo://market/reliance/2026-10-14",
            is_synthetic=True,
        ),
    ]
    return {
        "market_result": AgentResult(
            agent=AgentName.MARKET,
            status=AgentStatus.COMPLETED,
            summary=(
                "Synthetic price momentum is positive and volume is unusually high; "
                "this is a workflow demonstration, not a live market reading."
            ),
            confidence=0.78,
            signals=[
                Signal(
                    dimension=SignalDimension.PRICE_MOMENTUM,
                    classification=SignalClassification.POSITIVE,
                    confidence=0.81,
                    rationale="The synthetic 30-day adjusted return is +8.42%.",
                    evidence_ids=[evidence[0].id],
                ),
                Signal(
                    dimension=SignalDimension.VOLUME_ANOMALY,
                    classification=SignalClassification.POSITIVE,
                    confidence=0.74,
                    rationale="The synthetic 20-day volume z-score is +2.31.",
                    evidence_ids=[evidence[1].id],
                ),
                Signal(
                    dimension=SignalDimension.PRICE_VOLATILITY,
                    classification=SignalClassification.NEUTRAL,
                    confidence=0.72,
                    rationale="Synthetic 30-session annualized volatility is 22.0%.",
                    evidence_ids=[evidence[2].id],
                ),
            ],
            evidence=evidence,
            warnings=["Synthetic demo data; live market adapter is not connected."],
            metrics={"signal_accuracy_30d": 0.64},
            latency_ms=ceil((perf_counter() - started_at) * 1000),
        )
    }


def demo_filing_agent(_: AnalysisState) -> dict[str, AgentResult]:
    started_at = perf_counter()
    evidence = [
        Evidence(
            id="demo-filing-finance-costs",
            kind=EvidenceKind.DOCUMENT_EXCERPT,
            title="Synthetic FY2025 filing excerpt",
            observation=(
                "Revenue remained resilient while finance costs increased during the "
                "reporting period."
            ),
            source_name="VibeFinance synthetic annual-report fixture",
            source_url="demo://filings/reliance/fy2025",
            page_number=84,
            relevance=0.89,
            is_synthetic=True,
        )
    ]
    return {
        "filing_result": AgentResult(
            agent=AgentName.FILING,
            status=AgentStatus.COMPLETED,
            summary="The synthetic filing contains resilient revenue and rising financing risk.",
            confidence=0.71,
            signals=[
                Signal(
                    dimension=SignalDimension.FILING_SENTIMENT,
                    classification=SignalClassification.MIXED,
                    confidence=0.68,
                    rationale="Revenue resilience is offset by increased finance costs.",
                    evidence_ids=[evidence[0].id],
                )
            ],
            evidence=evidence,
            warnings=["Synthetic document; the filing retrieval adapter is not connected."],
            latency_ms=ceil((perf_counter() - started_at) * 1000),
        )
    }


def demo_portfolio_agent(state: AnalysisState) -> dict[str, AgentResult]:
    started_at = perf_counter()
    profile = state["request"].investor_profile
    conservative = profile.risk_tolerance == RiskTolerance.LOW
    classification = SignalClassification.NEGATIVE if conservative else SignalClassification.NEUTRAL
    observation = (
        "Synthetic energy exposure is 41%, above the conservative demo limit of 35%."
        if conservative
        else "Synthetic energy exposure is 41%, within the demo profile's 50% limit."
    )
    evidence = Evidence(
        id="demo-portfolio-sector-exposure",
        kind=EvidenceKind.PORTFOLIO_CALCULATION,
        title="Energy-sector concentration",
        observation=observation,
        source_name="VibeFinance synthetic portfolio fixture",
        source_url=f"demo://portfolios/{profile.id}",
        is_synthetic=True,
    )
    return {
        "portfolio_result": AgentResult(
            agent=AgentName.PORTFOLIO,
            status=AgentStatus.COMPLETED,
            summary=(
                "The position would deepen concentration beyond the conservative limit."
                if conservative
                else "The position remains within this profile's concentration limit."
            ),
            confidence=0.88,
            signals=[
                Signal(
                    dimension=SignalDimension.PORTFOLIO_FIT,
                    classification=classification,
                    confidence=0.88,
                    rationale=observation,
                    evidence_ids=[evidence.id],
                )
            ],
            evidence=[evidence],
            warnings=["Synthetic portfolio; Supabase holdings adapter is not connected."],
            metrics={"concentration_score": 0.41},
            latency_ms=ceil((perf_counter() - started_at) * 1000),
        )
    }


def _validate_evidence(state: AnalysisState) -> dict[str, list[str]]:
    results = [state["market_result"], state["filing_result"], state["portfolio_result"]]
    evidence_ids = [evidence.id for result in results for evidence in result.evidence]
    duplicate_ids = sorted({item for item in evidence_ids if evidence_ids.count(item) > 1})
    return {
        "validation_errors": [
            f"Duplicate evidence identifier: {evidence_id}" for evidence_id in duplicate_ids
        ]
    }


def _resolve_conflicts(state: AnalysisState) -> dict[str, list[EvidenceConflict]]:
    results = [state["market_result"], state["filing_result"], state["portfolio_result"]]
    positive_agents = {
        result.agent
        for result in results
        if any(signal.classification == SignalClassification.POSITIVE for signal in result.signals)
    }
    cautious_agents = {
        result.agent
        for result in results
        if any(
            signal.classification in {SignalClassification.NEGATIVE, SignalClassification.MIXED}
            for signal in result.signals
        )
    }
    if not positive_agents or not cautious_agents:
        return {"conflicts": []}
    involved = sorted(positive_agents | cautious_agents, key=str)
    return {
        "conflicts": [
            EvidenceConflict(
                dimension="overall_outlook",
                description=(
                    "Positive market signals conflict with filing or personalized portfolio risk."
                ),
                agent_names=involved,
                evidence_ids=[evidence.id for result in results for evidence in result.evidence],
            )
        ]
    }


def compose_deterministic_recommendation(
    state: AnalysisState,
) -> dict[str, Recommendation]:
    results = [state["market_result"], state["filing_result"], state["portfolio_result"]]
    portfolio_signal = state["portfolio_result"].signals[0]
    all_evidence = [evidence.id for result in results for evidence in result.evidence]
    is_high_risk = portfolio_signal.classification == SignalClassification.NEGATIVE
    action = RecommendationAction.MONITOR if is_high_risk else RecommendationAction.HOLD
    confidence = sum(result.confidence for result in results) / len(results)
    return {
        "recommendation": Recommendation(
            action=action,
            confidence=round(confidence, 2),
            summary=(
                "Monitor the position and avoid increasing exposure."
                if is_high_risk
                else "Hold while monitoring filing risks and elevated volume."
            ),
            rationale=[
                state["market_result"].summary,
                state["filing_result"].summary,
                state["portfolio_result"].summary,
            ],
            supporting_evidence_ids=all_evidence[:2],
            opposing_evidence_ids=all_evidence[2:],
            personalized_risks=(
                ["Recorded portfolio concentration exceeds the selected profile's limit."]
                if is_high_risk
                else []
            ),
        )
    }


def _collect_metrics(state: AnalysisState) -> dict[str, SessionMetrics]:
    results = [state["market_result"], state["filing_result"], state["portfolio_result"]]
    return {
        "metrics": SessionMetrics(
            end_to_end_latency_ms=ceil((perf_counter() - state["started_at_monotonic"]) * 1000),
            agent_latency_ms={item.agent: item.latency_ms for item in results},
            evidence_count=sum(len(item.evidence) for item in results),
            portfolio_concentration_score=state["portfolio_result"].metrics.get(
                "concentration_score"
            ),
            signal_accuracy_30d=state["market_result"].metrics.get("signal_accuracy_30d"),
        )
    }


def build_demo_nodes(
    market_agent: AnalysisNode | None = None,
    filing_agent: AnalysisNode | None = None,
    portfolio_agent: AnalysisNode | None = None,
    compose_recommendation: AnalysisNode | None = None,
) -> AnalysisGraphNodes:
    """Return a deterministic workflow for end-to-end integration and demos."""

    return AnalysisGraphNodes(
        market_agent=market_agent or _market_agent,
        filing_agent=filing_agent or demo_filing_agent,
        portfolio_agent=portfolio_agent or demo_portfolio_agent,
        validate_evidence=_validate_evidence,
        resolve_conflicts=_resolve_conflicts,
        compose_recommendation=(compose_recommendation or compose_deterministic_recommendation),
        collect_metrics=_collect_metrics,
    )
