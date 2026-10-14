from datetime import date
from uuid import uuid4

import pytest

from app.analysis.contracts import CompanyRef, InvestorProfileRef, RiskTolerance
from app.filings.interpreter import FilingInterpretation, LlmFilingInterpreter
from app.filings.models import RetrievedChunk


class StructuredModel:
    def __init__(self, response: FilingInterpretation) -> None:
        self.response = response

    def invoke(self, messages):  # type: ignore[no-untyped-def]
        assert "untrusted data" in messages[0].content
        return self.response


class ChatModel:
    def __init__(self, response: FilingInterpretation) -> None:
        self.response = response

    def with_structured_output(self, schema):  # type: ignore[no-untyped-def]
        assert schema is FilingInterpretation
        return StructuredModel(self.response)


def context():  # type: ignore[no-untyped-def]
    company = CompanyRef(id=uuid4(), symbol="RELIANCE", exchange="NSE")
    profile = InvestorProfileRef(
        id=uuid4(),
        risk_tolerance=RiskTolerance.LOW,
        investment_horizon_years=5,
    )
    chunk = RetrievedChunk(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_title="Annual report 2024-25",
        content="Revenue increased, while finance costs also increased.",
        source_name="Reliance Industries",
        source_url="https://www.ril.com/report.pdf",
        page_number=10,
        published_at=date(2025, 8, 7),
        similarity=0.8,
        is_synthetic=False,
    )
    return company, profile, [chunk]


def test_interpreter_accepts_only_retrieved_evidence_ids() -> None:
    response = FilingInterpretation(
        classification="mixed",
        confidence=0.82,
        summary="Reported growth is offset by higher financing costs.",
        rationale="The excerpt reports both a strength and a cost pressure.",
        strengths=["Revenue increased"],
        risks=["Finance costs increased"],
        outlook="A conservative investor should monitor financing-cost pressure.",
        evidence_ids=["filing-evidence-1"],
    )
    interpreter = LlmFilingInterpreter(ChatModel(response))  # type: ignore[arg-type]
    company, profile, chunks = context()

    result = interpreter.interpret(
        company,
        profile,
        chunks,
        ["filing-evidence-1"],
    )

    assert result.classification == "mixed"
    assert result.evidence_ids == ["filing-evidence-1"]


def test_interpreter_rejects_hallucinated_evidence_id() -> None:
    response = FilingInterpretation(
        classification="positive",
        confidence=0.9,
        summary="The filing is positive.",
        rationale="Revenue increased.",
        outlook="Growth may continue.",
        evidence_ids=["not-retrieved"],
    )
    interpreter = LlmFilingInterpreter(ChatModel(response))  # type: ignore[arg-type]
    company, profile, chunks = context()

    with pytest.raises(ValueError, match="unsupported citations"):
        interpreter.interpret(company, profile, chunks, ["filing-evidence-1"])
