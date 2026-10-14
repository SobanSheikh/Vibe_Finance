from collections.abc import Callable
from math import ceil
from time import perf_counter

from langchain_core.tools import BaseTool
from sqlalchemy.orm import Session, sessionmaker

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
from app.filings.contracts import FilingSearchResult
from app.filings.interpreter import FilingInterpretation, FilingInterpreter
from app.filings.models import RetrievedChunk
from app.filings.query_planner import FilingQueryPlanner
from app.filings.service import FilingRetrievalService
from app.filings.tools import build_filing_retrieval_tool

POSITIVE_TERMS = (
    "growth",
    "improved",
    "increase in revenue",
    "strong demand",
    "resilient",
    "profit increased",
    "debt reduced",
    "cash flow increased",
)
NEGATIVE_TERMS = (
    "decline",
    "decreased",
    "loss",
    "finance costs increased",
    "debt increased",
    "material risk",
    "weak demand",
    "impairment",
    "going concern",
)


def build_filing_agent(
    session_factory: sessionmaker[Session],
    retrieval: FilingRetrievalService | None = None,
    retrieval_tool: BaseTool | None = None,
    query_planner: FilingQueryPlanner | None = None,
    interpreter: FilingInterpreter | None = None,
    fallback: Callable[[AnalysisState], dict[str, AgentResult]] | None = None,
) -> Callable[[AnalysisState], dict[str, AgentResult]]:
    filing_search = retrieval_tool or build_filing_retrieval_tool(
        session_factory,
        retrieval,
    )
    planner = query_planner or FilingQueryPlanner()

    def filing_agent(state: AnalysisState) -> dict[str, AgentResult]:
        started_at = perf_counter()
        request = state["request"]
        company = request.company
        try:
            queries = planner.plan(company, request.investor_profile)
            raw_result = filing_search.invoke(
                {
                    "company_id": company.id,
                    "queries": [item.query for item in queries],
                    "limit": 6,
                }
            )
            search_result = FilingSearchResult.model_validate(raw_result)
        except Exception:
            return _unavailable_result(
                started_at,
                "The filing retrieval tool returned an invalid response.",
            )

        if search_result.status == "unavailable":
            if fallback is not None:
                return fallback(state)
            return _unavailable_result(
                started_at,
                search_result.error or "The filing evidence store is unavailable.",
            )
        if search_result.status == "no_evidence":
            return _unavailable_result(
                started_at,
                f"No indexed filing evidence is available for {company.symbol}.",
            )
        chunks = [RetrievedChunk(**item.model_dump()) for item in search_result.items]
        evidence = [_evidence_from_chunk(index, chunk) for index, chunk in enumerate(chunks)]
        if interpreter is not None:
            try:
                interpretation = interpreter.interpret(
                    company,
                    request.investor_profile,
                    chunks,
                    [item.id for item in evidence],
                )
                return _result_from_interpretation(
                    started_at,
                    chunks,
                    evidence,
                    interpretation,
                )
            except Exception:
                return _result_from_chunks(
                    started_at,
                    chunks,
                    evidence,
                    warning=(
                        "Structured LLM interpretation was unavailable; a deterministic "
                        "evidence classifier was used."
                    ),
                )
        return _result_from_chunks(started_at, chunks, evidence)

    return filing_agent


def _result_from_chunks(
    started_at: float,
    chunks: list[RetrievedChunk],
    evidence: list[Evidence],
    warning: str | None = None,
) -> dict[str, AgentResult]:
    combined = " ".join(chunk.content.lower() for chunk in chunks)
    positive_score = sum(combined.count(term) for term in POSITIVE_TERMS)
    negative_score = sum(combined.count(term) for term in NEGATIVE_TERMS)
    if positive_score and negative_score:
        classification = SignalClassification.MIXED
        summary = "Retrieved filings contain both operating strengths and financial risks."
    elif negative_score > positive_score:
        classification = SignalClassification.NEGATIVE
        summary = "Retrieved filings emphasize financial or operating risks."
    elif positive_score > negative_score:
        classification = SignalClassification.POSITIVE
        summary = "Retrieved filings emphasize operating or financial strengths."
    else:
        classification = SignalClassification.NEUTRAL
        summary = "Retrieved filings do not contain a dominant directional signal."

    mean_similarity = sum(chunk.similarity for chunk in chunks) / len(chunks)
    confidence = round(min(0.9, max(0.5, mean_similarity)), 2)
    rationale = (
        f"After multi-query retrieval and reranking, {len(chunks)} filing excerpts contained "
        f"{positive_score} strength indicators and {negative_score} risk indicators."
    )
    return {
        "filing_result": AgentResult(
            agent=AgentName.FILING,
            status=AgentStatus.COMPLETED,
            summary=summary,
            confidence=confidence,
            signals=[
                Signal(
                    dimension=SignalDimension.FILING_SENTIMENT,
                    classification=classification,
                    confidence=confidence,
                    rationale=rationale,
                    evidence_ids=[item.id for item in evidence],
                )
            ],
            evidence=evidence,
            warnings=[warning] if warning else [],
            latency_ms=ceil((perf_counter() - started_at) * 1000),
        )
    }


def _result_from_interpretation(
    started_at: float,
    chunks: list[RetrievedChunk],
    evidence: list[Evidence],
    interpretation: FilingInterpretation,
) -> dict[str, AgentResult]:
    evidence_by_id = {item.id: item for item in evidence}
    cited_evidence = [evidence_by_id[item] for item in interpretation.evidence_ids]
    cited_chunk_ids = {item.chunk_id for item in cited_evidence}
    cited_chunks = [chunk for chunk in chunks if chunk.chunk_id in cited_chunk_ids]
    mean_similarity = sum(chunk.similarity for chunk in cited_chunks) / len(cited_chunks)
    retrieval_ceiling = min(0.95, 0.55 + max(0, mean_similarity) * 0.4)
    confidence = round(min(interpretation.confidence, retrieval_ceiling), 2)
    findings = []
    if interpretation.strengths:
        findings.append("Strengths: " + "; ".join(interpretation.strengths))
    if interpretation.risks:
        findings.append("Risks: " + "; ".join(interpretation.risks))
    findings.append("Outlook: " + interpretation.outlook)
    rationale = interpretation.rationale + " " + " ".join(findings)
    return {
        "filing_result": AgentResult(
            agent=AgentName.FILING,
            status=AgentStatus.COMPLETED,
            summary=interpretation.summary,
            confidence=confidence,
            signals=[
                Signal(
                    dimension=SignalDimension.FILING_SENTIMENT,
                    classification=SignalClassification(interpretation.classification),
                    confidence=confidence,
                    rationale=rationale,
                    evidence_ids=interpretation.evidence_ids,
                )
            ],
            evidence=cited_evidence,
            latency_ms=ceil((perf_counter() - started_at) * 1000),
        )
    }


def _evidence_from_chunk(index: int, chunk: RetrievedChunk) -> Evidence:
    excerpt = " ".join(chunk.content.split())
    if len(excerpt) > 600:
        excerpt = excerpt[:597].rstrip() + "..."
    return Evidence(
        id=f"filing-{chunk.chunk_id}-{index}",
        kind=EvidenceKind.DOCUMENT_EXCERPT,
        title=chunk.document_title,
        observation=excerpt,
        source_name=chunk.source_name,
        source_url=chunk.source_url,
        document_id=chunk.document_id,
        chunk_id=chunk.chunk_id,
        page_number=chunk.page_number,
        relevance=round(max(0, min(1, chunk.similarity)), 4),
        is_synthetic=chunk.is_synthetic,
    )


def _unavailable_result(started_at: float, reason: str) -> dict[str, AgentResult]:
    evidence = Evidence(
        id="filing-insufficient-data",
        kind=EvidenceKind.DOCUMENT_EXCERPT,
        title="Filing evidence unavailable",
        observation=reason,
        source_name="VibeFinance filing index",
    )
    return {
        "filing_result": AgentResult(
            agent=AgentName.FILING,
            status=AgentStatus.DEGRADED,
            summary=reason,
            confidence=0.2,
            signals=[
                Signal(
                    dimension=SignalDimension.FILING_SENTIMENT,
                    classification=SignalClassification.INSUFFICIENT_DATA,
                    confidence=0.2,
                    rationale=reason,
                    evidence_ids=[evidence.id],
                )
            ],
            evidence=[evidence],
            warnings=[reason],
            latency_ms=ceil((perf_counter() - started_at) * 1000),
        )
    }
