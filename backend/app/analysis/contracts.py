from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RiskTolerance(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AgentName(StrEnum):
    MARKET = "market_signal"
    FILING = "filing_research"
    PORTFOLIO = "portfolio_risk"


class AgentStatus(StrEnum):
    COMPLETED = "completed"
    DEGRADED = "degraded"
    FAILED = "failed"


class AnalysisJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    DEGRADED = "degraded"
    FAILED = "failed"


class SignalDimension(StrEnum):
    PRICE_MOMENTUM = "price_momentum"
    VOLUME_ANOMALY = "volume_anomaly"
    FILING_SENTIMENT = "filing_sentiment"
    PORTFOLIO_FIT = "portfolio_fit"


class SignalClassification(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"
    INSUFFICIENT_DATA = "insufficient_data"


class EvidenceKind(StrEnum):
    MARKET_OBSERVATION = "market_observation"
    DOCUMENT_EXCERPT = "document_excerpt"
    PORTFOLIO_CALCULATION = "portfolio_calculation"


class RecommendationAction(StrEnum):
    INCREASE = "increase"
    HOLD = "hold"
    MONITOR = "monitor"
    REDUCE = "reduce"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class CompanyRef(StrictModel):
    id: UUID
    symbol: str = Field(min_length=1, max_length=32)
    exchange: str = Field(default="NSE", min_length=1, max_length=20)


class InvestorProfileRef(StrictModel):
    id: UUID
    risk_tolerance: RiskTolerance
    investment_horizon_years: int = Field(gt=0, le=100)


class AnalysisRequest(StrictModel):
    company: CompanyRef
    investor_profile: InvestorProfileRef
    as_of_date: date


class Evidence(StrictModel):
    id: str = Field(min_length=1, max_length=160)
    kind: EvidenceKind
    title: str = Field(min_length=1, max_length=500)
    observation: str = Field(min_length=1)
    source_name: str = Field(min_length=1, max_length=150)
    source_url: str | None = None
    observed_at: datetime | date | None = None
    document_id: UUID | None = None
    chunk_id: UUID | None = None
    page_number: int | None = Field(default=None, gt=0)
    relevance: float | None = Field(default=None, ge=0, le=1)
    is_synthetic: bool = False


class Signal(StrictModel):
    dimension: SignalDimension
    classification: SignalClassification
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)


class AgentError(StrictModel):
    code: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1)
    retryable: bool = False


class AgentResult(StrictModel):
    agent: AgentName
    status: AgentStatus
    summary: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    signals: list[Signal] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[AgentError] = Field(default_factory=list)
    latency_ms: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_evidence_links(self) -> "AgentResult":
        evidence_ids = {item.id for item in self.evidence}
        referenced_ids = {item for signal in self.signals for item in signal.evidence_ids}
        missing_ids = referenced_ids - evidence_ids
        if missing_ids:
            missing = ", ".join(sorted(missing_ids))
            raise ValueError(f"signals reference missing evidence: {missing}")
        if self.status == AgentStatus.COMPLETED and not self.signals:
            raise ValueError("a completed agent must return at least one signal")
        return self


class EvidenceConflict(StrictModel):
    dimension: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1)
    agent_names: list[AgentName] = Field(min_length=2)
    evidence_ids: list[str] = Field(default_factory=list)


class SessionMetrics(StrictModel):
    end_to_end_latency_ms: int = Field(ge=0)
    agent_latency_ms: dict[AgentName, int]
    evidence_count: int = Field(ge=0)
    portfolio_concentration_score: float | None = Field(default=None, ge=0, le=1)
    signal_accuracy_30d: float | None = Field(default=None, ge=0, le=1)


class Recommendation(StrictModel):
    action: RecommendationAction
    confidence: float = Field(ge=0, le=1)
    summary: str = Field(min_length=1)
    rationale: list[str] = Field(min_length=1)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    opposing_evidence_ids: list[str] = Field(default_factory=list)
    personalized_risks: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "Decision support only. VibeFinance does not provide financial advice."
    )


class AnalysisResponse(StrictModel):
    session_id: UUID
    status: AgentStatus
    request: AnalysisRequest
    agents: list[AgentResult] = Field(min_length=3)
    conflicts: list[EvidenceConflict]
    recommendation: Recommendation
    metrics: SessionMetrics


class AnalysisJobAccepted(StrictModel):
    session_id: UUID
    status: AnalysisJobStatus


class AnalysisJob(StrictModel):
    session_id: UUID
    status: AnalysisJobStatus
    result: AnalysisResponse | None = None
    error: str | None = None
