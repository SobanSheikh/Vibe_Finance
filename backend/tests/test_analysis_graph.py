from datetime import date
from uuid import uuid4

from app.analysis.contracts import (
    AgentName,
    AgentResult,
    AgentStatus,
    AnalysisRequest,
    CompanyRef,
    InvestorProfileRef,
    Recommendation,
    RecommendationAction,
    RiskTolerance,
    SessionMetrics,
)
from app.analysis.graph import AnalysisGraphNodes, build_analysis_graph
from app.analysis.state import AnalysisState


def agent_result(name: AgentName) -> AgentResult:
    return AgentResult(
        agent=name,
        status=AgentStatus.DEGRADED,
        summary="Provider adapter is not configured in this test.",
        confidence=0,
        warnings=["No provider configured"],
        latency_ms=1,
    )


def test_graph_runs_three_specialists_before_synthesis() -> None:
    execution_order: list[str] = []

    def market(_: AnalysisState):
        execution_order.append("market")
        return {"market_result": agent_result(AgentName.MARKET)}

    def filing(_: AnalysisState):
        execution_order.append("filing")
        return {"filing_result": agent_result(AgentName.FILING)}

    def portfolio(_: AnalysisState):
        execution_order.append("portfolio")
        return {"portfolio_result": agent_result(AgentName.PORTFOLIO)}

    def validate(state: AnalysisState):
        assert all(
            key in state for key in ("market_result", "filing_result", "portfolio_result")
        )
        execution_order.append("validate")
        return {"validation_errors": []}

    def resolve(_: AnalysisState):
        execution_order.append("resolve")
        return {"conflicts": []}

    def compose(_: AnalysisState):
        execution_order.append("compose")
        return {
            "recommendation": Recommendation(
                action=RecommendationAction.INSUFFICIENT_EVIDENCE,
                confidence=0,
                summary="More evidence is required.",
                rationale=["All provider adapters are unavailable."],
            )
        }

    def metrics(_: AnalysisState):
        execution_order.append("metrics")
        return {
            "metrics": SessionMetrics(
                end_to_end_latency_ms=5,
                agent_latency_ms={
                    AgentName.MARKET: 1,
                    AgentName.FILING: 1,
                    AgentName.PORTFOLIO: 1,
                },
                evidence_count=0,
            )
        }

    graph = build_analysis_graph(
        AnalysisGraphNodes(
            market_agent=market,
            filing_agent=filing,
            portfolio_agent=portfolio,
            validate_evidence=validate,
            resolve_conflicts=resolve,
            compose_recommendation=compose,
            collect_metrics=metrics,
        )
    )
    request = AnalysisRequest(
        company=CompanyRef(id=uuid4(), symbol="RELIANCE"),
        investor_profile=InvestorProfileRef(
            id=uuid4(), risk_tolerance=RiskTolerance.LOW, investment_horizon_years=5
        ),
        as_of_date=date(2026, 10, 14),
    )

    result = graph.invoke({"request": request})

    assert set(execution_order[:3]) == {"market", "filing", "portfolio"}
    assert execution_order[3:] == ["validate", "resolve", "compose", "metrics"]
    assert result["recommendation"].action == RecommendationAction.INSUFFICIENT_EVIDENCE
