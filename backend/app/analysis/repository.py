from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.analysis.contracts import (
    AgentName,
    AgentStatus,
    AnalysisHistoryItem,
    AnalysisJob,
    AnalysisJobStatus,
    AnalysisProgress,
    AnalysisProgressPhase,
    AnalysisProgressState,
    AnalysisRequest,
    AnalysisResponse,
)
from app.db.models import (
    AgentRun,
    AnalysisSession,
    Citation,
    RunStatus,
)
from app.db.models import (
    Recommendation as RecommendationRecord,
)


class AnalysisRepository:
    """Persist normalized evaluation records and a restart-safe response snapshot."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(self, session_id: UUID, request: AnalysisRequest) -> None:
        with self._session_factory() as session:
            session.add(
                AnalysisSession(
                    id=session_id,
                    profile_id=request.investor_profile.id,
                    company_id=request.company.id,
                    as_of_date=request.as_of_date,
                    status=RunStatus.PENDING,
                    input_snapshot=request.model_dump(mode="json"),
                    metrics={},
                    degraded_reasons=[],
                )
            )
            session.commit()

    def mark_running(self, session_id: UUID) -> None:
        with self._session_factory() as session:
            record = session.get(AnalysisSession, session_id)
            if record is None:
                return
            record.status = RunStatus.RUNNING
            session.commit()

    def complete(self, response: AnalysisResponse) -> None:
        completed_at = datetime.now(UTC)
        with self._session_factory() as session:
            record = session.get(AnalysisSession, response.session_id)
            if record is None:
                return
            record.status = RunStatus(response.status.value)
            record.metrics = response.metrics.model_dump(mode="json")
            record.degraded_reasons = _degraded_reasons(response)
            record.result_snapshot = response.model_dump(mode="json")
            record.completed_at = completed_at

            session.execute(delete(AgentRun).where(AgentRun.session_id == response.session_id))
            session.flush()
            agent_runs: dict[str, AgentRun] = {}
            for result in response.agents:
                first_error = result.errors[0] if result.errors else None
                run = AgentRun(
                    session_id=response.session_id,
                    agent_name=result.agent.value,
                    status=RunStatus(result.status.value),
                    input_data=response.request.model_dump(mode="json"),
                    output_data=result.model_dump(mode="json"),
                    error_code=first_error.code if first_error else None,
                    error_message=first_error.message if first_error else None,
                    latency_ms=result.latency_ms,
                    started_at=completed_at - timedelta(milliseconds=result.latency_ms),
                    completed_at=completed_at,
                )
                session.add(run)
                agent_runs[result.agent.value] = run
            session.flush()

            session.add(
                RecommendationRecord(
                    session_id=response.session_id,
                    classification=response.status.value,
                    action=response.recommendation.action.value,
                    confidence=response.recommendation.confidence,
                    rationale="\n".join(response.recommendation.rationale),
                    supporting_evidence=response.recommendation.supporting_evidence_ids,
                    opposing_evidence=response.recommendation.opposing_evidence_ids,
                    disclaimer=response.recommendation.disclaimer,
                )
            )
            for result in response.agents:
                run = agent_runs[result.agent.value]
                for evidence in result.evidence:
                    if evidence.chunk_id is None:
                        continue
                    session.add(
                        Citation(
                            agent_run_id=run.id,
                            document_chunk_id=evidence.chunk_id,
                            claim_key=evidence.id[:120],
                            quoted_excerpt=evidence.observation,
                            similarity_score=evidence.relevance,
                        )
                    )
            session.commit()

    def fail(self, session_id: UUID, error: str) -> None:
        with self._session_factory() as session:
            record = session.get(AnalysisSession, session_id)
            if record is None:
                return
            record.status = RunStatus.FAILED
            record.degraded_reasons = [error]
            record.completed_at = datetime.now(UTC)
            session.commit()

    def get_job(self, session_id: UUID) -> AnalysisJob | None:
        with self._session_factory() as session:
            record = session.get(AnalysisSession, session_id)
            if record is None:
                return None
            result = (
                AnalysisResponse.model_validate(record.result_snapshot)
                if record.result_snapshot
                else None
            )
            error = None
            if record.status == RunStatus.FAILED and record.degraded_reasons:
                error = str(record.degraded_reasons[0])
            return AnalysisJob(
                session_id=record.id,
                status=AnalysisJobStatus(record.status.value),
                progress=_persisted_progress(record.status, result),
                result=result,
                error=error,
            )

    def list_history(
        self,
        *,
        profile_id: UUID | None = None,
        company_id: UUID | None = None,
        limit: int = 30,
    ) -> list[AnalysisHistoryItem]:
        statement = select(AnalysisSession).order_by(AnalysisSession.started_at.desc()).limit(limit)
        if profile_id is not None:
            statement = statement.where(AnalysisSession.profile_id == profile_id)
        if company_id is not None:
            statement = statement.where(AnalysisSession.company_id == company_id)

        with self._session_factory() as session:
            records = session.scalars(statement).all()
            items: list[AnalysisHistoryItem] = []
            for record in records:
                result = (
                    AnalysisResponse.model_validate(record.result_snapshot)
                    if record.result_snapshot
                    else None
                )
                company_snapshot = record.input_snapshot.get("company", {})
                items.append(
                    AnalysisHistoryItem(
                        session_id=record.id,
                        status=AnalysisJobStatus(record.status.value),
                        company_id=record.company_id,
                        profile_id=record.profile_id,
                        company_symbol=str(company_snapshot.get("symbol", "Unknown")),
                        as_of_date=record.as_of_date,
                        started_at=record.started_at,
                        completed_at=record.completed_at,
                        recommendation_action=(result.recommendation.action if result else None),
                        recommendation_summary=(result.recommendation.summary if result else None),
                        recommendation_confidence=(
                            result.recommendation.confidence if result else None
                        ),
                        end_to_end_latency_ms=(
                            result.metrics.end_to_end_latency_ms if result else None
                        ),
                        evidence_count=result.metrics.evidence_count if result else None,
                        portfolio_concentration_score=(
                            result.metrics.portfolio_concentration_score if result else None
                        ),
                        signal_accuracy_30d=(
                            result.metrics.signal_accuracy_30d if result else None
                        ),
                    )
                )
            return items


def _degraded_reasons(response: AnalysisResponse) -> list[str]:
    reasons: list[str] = []
    for result in response.agents:
        if result.status != AgentStatus.COMPLETED:
            reasons.append(f"{result.agent.value}: {result.summary}")
        reasons.extend(result.warnings)
        reasons.extend(error.message for error in result.errors)
    return list(dict.fromkeys(reasons))


def _persisted_progress(
    status: RunStatus,
    result: AnalysisResponse | None,
) -> AnalysisProgress:
    if result is not None:
        return AnalysisProgress(
            phase=AnalysisProgressPhase.COMPLETE,
            agents={
                agent.agent: AnalysisProgressState(agent.status.value) for agent in result.agents
            },
            completed_nodes=[
                "market_agent",
                "filing_agent",
                "portfolio_agent",
                "validate_evidence",
                "resolve_conflicts",
                "compose_recommendation",
                "collect_metrics",
            ],
        )
    phase = (
        AnalysisProgressPhase.FAILED
        if status == RunStatus.FAILED
        else AnalysisProgressPhase.SPECIALISTS
        if status == RunStatus.RUNNING
        else AnalysisProgressPhase.QUEUED
    )
    agent_state = (
        AnalysisProgressState.FAILED
        if status == RunStatus.FAILED
        else AnalysisProgressState.RUNNING
        if status == RunStatus.RUNNING
        else AnalysisProgressState.QUEUED
    )
    return AnalysisProgress(
        phase=phase,
        agents={agent: agent_state for agent in AgentName},
    )
