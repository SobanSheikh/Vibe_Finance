from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.analysis.contracts import AnalysisJob, AnalysisJobAccepted, AnalysisRequest
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


@router.get("/{session_id}", response_model=AnalysisJob)
async def get_analysis(session_id: UUID) -> AnalysisJob:
    try:
        return analysis_service.get(session_id)
    except AnalysisNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Analysis session not found") from exc
