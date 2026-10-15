import asyncio
import logging
from copy import deepcopy
from threading import Lock
from time import perf_counter
from typing import Any
from uuid import UUID, uuid4

from app.analysis.contracts import (
    AgentName,
    AgentStatus,
    AnalysisHistoryItem,
    AnalysisJob,
    AnalysisJobAccepted,
    AnalysisJobStatus,
    AnalysisProgress,
    AnalysisProgressPhase,
    AnalysisProgressState,
    AnalysisRequest,
    AnalysisResponse,
)
from app.analysis.demo import (
    build_demo_nodes,
    compose_deterministic_recommendation,
    demo_filing_agent,
    demo_portfolio_agent,
)
from app.analysis.graph import build_analysis_graph
from app.analysis.repository import AnalysisRepository
from app.analysis.synthesis import LlmRecommendationComposer, build_synthesis_agent
from app.config import get_settings
from app.db.session import get_session_factory
from app.filings import build_filing_agent
from app.filings.interpreter import LlmFilingInterpreter
from app.filings.query_planner import FilingQueryPlanner
from app.llm import build_chat_model
from app.market import YahooFinanceProvider, build_market_agent
from app.portfolio import build_portfolio_agent


class AnalysisNotFoundError(LookupError):
    pass


logger = logging.getLogger(__name__)


def _queued_progress() -> AnalysisProgress:
    return AnalysisProgress(
        phase=AnalysisProgressPhase.QUEUED,
        agents={agent: AnalysisProgressState.QUEUED for agent in AgentName},
    )


class AnalysisService:
    """Run jobs locally while persisting lifecycle and validated results in PostgreSQL."""

    def __init__(self) -> None:
        self._jobs: dict[UUID, AnalysisJob] = {}
        self._requests: dict[UUID, AnalysisRequest] = {}
        self._lock = Lock()
        settings = get_settings()
        self._repository = (
            AnalysisRepository(get_session_factory()) if settings.database_url else None
        )
        chat_model = build_chat_model(settings)
        market_agent = (
            build_market_agent(YahooFinanceProvider())
            if settings.market_data_mode == "live"
            else None
        )
        portfolio_agent = (
            build_portfolio_agent(
                get_session_factory(),
                fallback=(demo_portfolio_agent if settings.market_data_mode == "demo" else None),
            )
            if settings.database_url
            else None
        )
        filing_agent = (
            build_filing_agent(
                get_session_factory(),
                query_planner=FilingQueryPlanner(chat_model),
                interpreter=LlmFilingInterpreter(chat_model) if chat_model else None,
                fallback=demo_filing_agent if settings.market_data_mode == "demo" else None,
            )
            if settings.database_url
            else None
        )
        self._graph = build_analysis_graph(
            build_demo_nodes(
                market_agent=market_agent,
                filing_agent=filing_agent,
                portfolio_agent=portfolio_agent,
                compose_recommendation=(
                    build_synthesis_agent(
                        LlmRecommendationComposer(chat_model),
                        compose_deterministic_recommendation,
                    )
                    if chat_model
                    else None
                ),
            )
        )

    def create(self, request: AnalysisRequest) -> AnalysisJobAccepted:
        session_id = uuid4()
        job = AnalysisJob(
            session_id=session_id,
            status=AnalysisJobStatus.PENDING,
            progress=_queued_progress(),
        )
        if self._repository is not None:
            self._repository.create(session_id, request)
        with self._lock:
            self._jobs[session_id] = job
            self._requests[session_id] = request
        return AnalysisJobAccepted(session_id=session_id, status=job.status)

    def get(self, session_id: UUID) -> AnalysisJob:
        with self._lock:
            job = self._jobs.get(session_id)
            if job is not None:
                return deepcopy(job)
        if self._repository is not None:
            persisted = self._repository.get_job(session_id)
            if persisted is not None:
                return persisted
        raise AnalysisNotFoundError(str(session_id))

    def list_history(
        self,
        *,
        profile_id: UUID | None = None,
        company_id: UUID | None = None,
        limit: int = 30,
    ) -> list[AnalysisHistoryItem]:
        if self._repository is None:
            return []
        return self._repository.list_history(
            profile_id=profile_id,
            company_id=company_id,
            limit=limit,
        )

    async def run(self, session_id: UUID) -> None:
        with self._lock:
            request = self._requests[session_id]
            self._jobs[session_id].status = AnalysisJobStatus.RUNNING
            self._jobs[session_id].progress = AnalysisProgress(
                phase=AnalysisProgressPhase.SPECIALISTS,
                agents={agent: AnalysisProgressState.RUNNING for agent in AgentName},
            )

        try:
            if self._repository is not None:
                await asyncio.to_thread(self._repository.mark_running, session_id)
            state = await asyncio.to_thread(self._run_graph, session_id, request)
            agent_results = [
                state["market_result"],
                state["filing_result"],
                state["portfolio_result"],
            ]
            degraded = bool(state["validation_errors"]) or any(
                result.status != AgentStatus.COMPLETED for result in agent_results
            )
            response_status = AgentStatus.DEGRADED if degraded else AgentStatus.COMPLETED
            response = AnalysisResponse(
                session_id=session_id,
                status=response_status,
                request=request,
                agents=agent_results,
                conflicts=state["conflicts"],
                recommendation=state["recommendation"],
                metrics=state["metrics"],
            )
            final_status = (
                AnalysisJobStatus.DEGRADED if degraded else AnalysisJobStatus.COMPLETED
            )
            with self._lock:
                self._jobs[session_id] = AnalysisJob(
                    session_id=session_id,
                    status=AnalysisJobStatus.RUNNING,
                    progress=AnalysisProgress(
                        phase=AnalysisProgressPhase.PERSISTENCE,
                        agents={
                            result.agent: AnalysisProgressState(result.status.value)
                            for result in agent_results
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
                    ),
                    result=response,
                )
            if self._repository is not None:
                await asyncio.to_thread(self._repository.complete, response)
            with self._lock:
                self._jobs[session_id].status = final_status
                self._jobs[session_id].progress.phase = AnalysisProgressPhase.COMPLETE
        except Exception:
            logger.exception("Analysis session %s failed", session_id)
            with self._lock:
                self._jobs[session_id] = AnalysisJob(
                    session_id=session_id,
                    status=AnalysisJobStatus.FAILED,
                    progress=AnalysisProgress(
                        phase=AnalysisProgressPhase.FAILED,
                        agents=self._jobs[session_id].progress.agents,
                        completed_nodes=self._jobs[session_id].progress.completed_nodes,
                    ),
                    error="The analysis workflow failed. Review server logs for details.",
                )
            if self._repository is not None:
                try:
                    await asyncio.to_thread(
                        self._repository.fail,
                        session_id,
                        "The analysis workflow failed. Review server logs for details.",
                    )
                except Exception:
                    logger.exception("Could not persist failure for analysis %s", session_id)
            raise

    def _run_graph(self, session_id: UUID, request: AnalysisRequest) -> dict[str, Any]:
        state: dict[str, Any] = {
            "request": request,
            "started_at_monotonic": perf_counter(),
        }
        for update in self._graph.stream(state, stream_mode="updates"):
            for node_name, node_update in update.items():
                if isinstance(node_update, dict):
                    state.update(node_update)
                self._record_node_progress(session_id, node_name, node_update)
        return state

    def _record_node_progress(
        self,
        session_id: UUID,
        node_name: str,
        node_update: object,
    ) -> None:
        agent_nodes = {
            "market_agent": (AgentName.MARKET, "market_result"),
            "filing_agent": (AgentName.FILING, "filing_result"),
            "portfolio_agent": (AgentName.PORTFOLIO, "portfolio_result"),
        }
        with self._lock:
            progress = self._jobs[session_id].progress
            agents = dict(progress.agents)
            completed_nodes = [*progress.completed_nodes, node_name]
            phase = progress.phase
            if node_name in agent_nodes and isinstance(node_update, dict):
                agent_name, result_key = agent_nodes[node_name]
                result = node_update.get(result_key)
                if result is not None:
                    agents[agent_name] = AnalysisProgressState(result.status.value)
                if all(value != AnalysisProgressState.RUNNING for value in agents.values()):
                    phase = AnalysisProgressPhase.VALIDATION
            elif node_name == "resolve_conflicts":
                phase = AnalysisProgressPhase.SYNTHESIS
            elif node_name in {"compose_recommendation", "collect_metrics"}:
                phase = AnalysisProgressPhase.PERSISTENCE
            self._jobs[session_id].progress = AnalysisProgress(
                phase=phase,
                agents=agents,
                completed_nodes=list(dict.fromkeys(completed_nodes)),
            )


analysis_service = AnalysisService()
