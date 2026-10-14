from typing import TypedDict

from app.analysis.contracts import (
    AgentResult,
    AnalysisRequest,
    EvidenceConflict,
    Recommendation,
    SessionMetrics,
)


class AnalysisState(TypedDict, total=False):
    """Shared state passed through the analysis graph.

    Specialist agents write to distinct keys so LangGraph can execute them in
    parallel without merge ambiguity.
    """

    request: AnalysisRequest
    started_at_monotonic: float
    market_result: AgentResult
    filing_result: AgentResult
    portfolio_result: AgentResult
    validation_errors: list[str]
    conflicts: list[EvidenceConflict]
    recommendation: Recommendation
    metrics: SessionMetrics
