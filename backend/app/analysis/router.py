from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

from app.analysis.contracts import (
    AnalysisHistoryItem,
    AnalysisJob,
    AnalysisJobAccepted,
    AnalysisRequest,
)
from app.analysis.service import AnalysisNotFoundError, analysis_service

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.post("", response_model=AnalysisJobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def create_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
) -> AnalysisJobAccepted:
    accepted = analysis_service.create(request)
    background_tasks.add_task(analysis_service.run, accepted.session_id)
    return accepted


@router.get("", response_model=list[AnalysisHistoryItem])
async def list_analyses(
    profile_id: UUID | None = None,
    company_id: UUID | None = None,
    limit: int = Query(default=30, ge=1, le=100),
) -> list[AnalysisHistoryItem]:
    return analysis_service.list_history(
        profile_id=profile_id,
        company_id=company_id,
        limit=limit,
    )


@router.get("/{session_id}", response_model=AnalysisJob)
async def get_analysis(session_id: UUID) -> AnalysisJob:
    try:
        return analysis_service.get(session_id)
    except AnalysisNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Analysis session not found") from exc
