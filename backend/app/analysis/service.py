import asyncio
from copy import deepcopy
from threading import Lock
from time import perf_counter
from uuid import UUID, uuid4

from app.analysis.contracts import (
    AgentStatus,
    AnalysisJob,
    AnalysisJobAccepted,
    AnalysisJobStatus,
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


class InMemoryAnalysisService:
    """Process-local job service for the end-to-end demo workflow.

    The interface is deliberately isolated so a durable Supabase/Celery-backed
    implementation can replace it without changing HTTP routes or graph nodes.
    """

    def __init__(self) -> None:
        self._jobs: dict[UUID, AnalysisJob] = {}
        self._requests: dict[UUID, AnalysisRequest] = {}
        self._lock = Lock()
        settings = get_settings()
        chat_model = build_chat_model(settings)
        market_agent = (
            build_market_agent(YahooFinanceProvider())
            if settings.market_data_mode == "live"
            else None
        )
        portfolio_agent = (
            build_portfolio_agent(
                get_session_factory(),
                fallback=(
                    demo_portfolio_agent if settings.market_data_mode == "demo" else None
                ),
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
        job = AnalysisJob(session_id=session_id, status=AnalysisJobStatus.PENDING)
        with self._lock:
            self._jobs[session_id] = job
            self._requests[session_id] = request
        return AnalysisJobAccepted(session_id=session_id, status=job.status)

    def get(self, session_id: UUID) -> AnalysisJob:
        with self._lock:
            job = self._jobs.get(session_id)
            if job is None:
                raise AnalysisNotFoundError(str(session_id))
            return deepcopy(job)

    async def run(self, session_id: UUID) -> None:
        with self._lock:
            request = self._requests[session_id]
            self._jobs[session_id].status = AnalysisJobStatus.RUNNING

        try:
            state = await asyncio.to_thread(
                self._graph.invoke,
                {"request": request, "started_at_monotonic": perf_counter()},
            )
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
            with self._lock:
                self._jobs[session_id] = AnalysisJob(
                    session_id=session_id,
                    status=(
                        AnalysisJobStatus.DEGRADED
                        if degraded
                        else AnalysisJobStatus.COMPLETED
                    ),
                    result=response,
                )
        except Exception:
            with self._lock:
                self._jobs[session_id] = AnalysisJob(
                    session_id=session_id,
                    status=AnalysisJobStatus.FAILED,
                    error="The analysis workflow failed. Review server logs for details.",
                )
            raise


analysis_service = InMemoryAnalysisService()
