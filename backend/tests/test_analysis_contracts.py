from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.analysis.contracts import (
    AgentName,
    AgentResult,
    AgentStatus,
    AnalysisRequest,
    CompanyRef,
    Evidence,
    EvidenceKind,
    InvestorProfileRef,
    RiskTolerance,
    Signal,
    SignalClassification,
    SignalDimension,
)


def analysis_request() -> AnalysisRequest:
    return AnalysisRequest(
        company=CompanyRef(id=uuid4(), symbol="RELIANCE", exchange="NSE"),
        investor_profile=InvestorProfileRef(
            id=uuid4(),
            risk_tolerance=RiskTolerance.LOW,
            investment_horizon_years=5,
        ),
        as_of_date=date(2026, 10, 14),
    )


def test_request_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        AnalysisRequest(
            company=CompanyRef(id=uuid4(), symbol="RELIANCE"),
            investor_profile=InvestorProfileRef(
                id=uuid4(), risk_tolerance=RiskTolerance.LOW, investment_horizon_years=5
            ),
            as_of_date=date(2026, 10, 14),
            unsupported=True,
        )


def test_agent_result_requires_resolvable_evidence_ids() -> None:
    with pytest.raises(ValidationError, match="missing evidence"):
        AgentResult(
            agent=AgentName.MARKET,
            status=AgentStatus.COMPLETED,
            summary="Momentum is positive.",
            confidence=0.8,
            signals=[
                Signal(
                    dimension=SignalDimension.PRICE_MOMENTUM,
                    classification=SignalClassification.POSITIVE,
                    confidence=0.8,
                    rationale="The 30-day return is positive.",
                    evidence_ids=["missing-observation"],
                )
            ],
            evidence=[
                Evidence(
                    id="market-observation-1",
                    kind=EvidenceKind.MARKET_OBSERVATION,
                    title="30-day return",
                    observation="Return was 8.4%.",
                    source_name="Market data provider",
                )
            ],
            latency_ms=12,
        )
