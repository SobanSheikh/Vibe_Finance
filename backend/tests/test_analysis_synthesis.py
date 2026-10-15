from datetime import date
from uuid import uuid4

import pytest

from app.analysis.contracts import (
    AgentName,
    AgentResult,
    AgentStatus,
    AnalysisRequest,
    CompanyRef,
    Evidence,
    EvidenceKind,
    InvestorProfileRef,
    Recommendation,
    RecommendationAction,
    RiskTolerance,
    Signal,
    SignalClassification,
    SignalDimension,
)
from app.analysis.synthesis import (
    LlmRecommendationComposer,
    RecommendationDraft,
    build_synthesis_agent,
)


class StructuredModel:
    def __init__(self, response: RecommendationDraft) -> None:
        self.response = response

    def invoke(self, messages):  # type: ignore[no-untyped-def]
        assert "untrusted data" in messages[0].content
        return self.response


class ChatModel:
    def __init__(self, response: RecommendationDraft) -> None:
        self.response = response

    def with_structured_output(self, schema):  # type: ignore[no-untyped-def]
        assert schema is RecommendationDraft
        return StructuredModel(self.response)


def state():  # type: ignore[no-untyped-def]
    request = AnalysisRequest(
        company=CompanyRef(id=uuid4(), symbol="RELIANCE", exchange="NSE"),
        investor_profile=InvestorProfileRef(
            id=uuid4(),
            risk_tolerance=RiskTolerance.LOW,
            investment_horizon_years=5,
        ),
        as_of_date=date(2026, 10, 14),
    )

    def result(agent: AgentName, evidence_id: str, confidence: float) -> AgentResult:
        dimensions = {
            AgentName.MARKET: SignalDimension.PRICE_MOMENTUM,
            AgentName.FILING: SignalDimension.FILING_SENTIMENT,
            AgentName.PORTFOLIO: SignalDimension.PORTFOLIO_FIT,
        }
        return AgentResult(
            agent=agent,
            status=AgentStatus.COMPLETED,
            summary=f"{agent.value} completed.",
            confidence=confidence,
            signals=[
                Signal(
                    dimension=dimensions[agent],
                    classification=SignalClassification.NEUTRAL,
                    confidence=confidence,
                    rationale="A specialist produced a neutral test signal.",
                    evidence_ids=[evidence_id],
                )
            ],
            evidence=[
                Evidence(
                    id=evidence_id,
                    kind=EvidenceKind.MARKET_OBSERVATION,
                    title="Validated observation",
                    observation="A specialist produced this observation.",
                    source_name="Test source",
                )
            ],
            latency_ms=1,
        )

    return {
        "request": request,
        "market_result": result(AgentName.MARKET, "market-1", 0.8),
        "filing_result": result(AgentName.FILING, "filing-1", 0.7),
        "portfolio_result": result(AgentName.PORTFOLIO, "portfolio-1", 0.9),
        "conflicts": [],
        "validation_errors": [],
    }


def test_synthesis_keeps_citations_and_calibrates_confidence() -> None:
    draft = RecommendationDraft(
        action=RecommendationAction.MONITOR,
        confidence=0.95,
        summary="Monitor because portfolio risk offsets other evidence.",
        rationale=["Market and filing evidence do not outweigh concentration risk."],
        supporting_evidence_ids=["portfolio-1", "portfolio-1"],
        opposing_evidence_ids=["market-1"],
        personalized_risks=["Concentration is important for a low-risk profile."],
    )

    result = LlmRecommendationComposer(ChatModel(draft)).compose(state())  # type: ignore[arg-type]

    assert result.action == RecommendationAction.MONITOR
    assert result.confidence == 0.8
    assert result.supporting_evidence_ids == ["portfolio-1"]
    assert result.disclaimer.startswith("Decision support only")


def test_draft_cleans_and_limits_provider_generated_lists() -> None:
    draft = RecommendationDraft(
        action=RecommendationAction.REDUCE,
        confidence=0.8,
        summary="Reduce exposure because concentration exceeds the profile limits.",
        rationale=["One", "Two", "Three", "Four", "Five", ""],
        supporting_evidence_ids=["portfolio-1"] * 9,
        personalized_risks=["One", "Two", "Three", "Four", "Five"],
    )

    assert draft.rationale == ["One", "Two", "Three", "Four", "Five"]
    assert draft.supporting_evidence_ids == ["portfolio-1"]
    assert draft.personalized_risks == ["One", "Two", "Three", "Four"]


def test_synthesis_rejects_hallucinated_evidence_id() -> None:
    draft = RecommendationDraft(
        action=RecommendationAction.HOLD,
        confidence=0.7,
        summary="Hold based on the available evidence.",
        rationale=["The evidence is balanced."],
        supporting_evidence_ids=["invented-1"],
    )
    composer = LlmRecommendationComposer(ChatModel(draft))  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="unsupported evidence IDs"):
        composer.compose(state())


def test_synthesis_agent_discloses_deterministic_fallback() -> None:
    class BrokenComposer:
        def compose(self, analysis_state):  # type: ignore[no-untyped-def]
            raise TimeoutError("provider timeout")

    def fallback(analysis_state):  # type: ignore[no-untyped-def]
        return {
            "recommendation": Recommendation(
                action=RecommendationAction.MONITOR,
                confidence=0.6,
                summary="Monitor using the deterministic policy.",
                rationale=["Portfolio risk is elevated."],
            )
        }

    result = build_synthesis_agent(BrokenComposer(), fallback)(state())

    assert "deterministic decision policy" in result["recommendation"].rationale[-1]
