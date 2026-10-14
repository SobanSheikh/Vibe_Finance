from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.filings.contracts import (
    FilingIngestionAccepted,
    FilingIngestionJob,
    FilingIngestionRequest,
)
from app.filings.downloader import FilingDownloadError
from app.filings.jobs import (
    IngestionJobNotFoundError,
    filing_ingestion_jobs,
)

router = APIRouter(prefix="/api/filings", tags=["filings"])


@router.post(
    "/ingest",
    response_model=FilingIngestionAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_filing(
    request: FilingIngestionRequest,
    background_tasks: BackgroundTasks,
) -> FilingIngestionAccepted:
    try:
        accepted = filing_ingestion_jobs.create(request)
    except FilingDownloadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    background_tasks.add_task(filing_ingestion_jobs.run, accepted.job_id)
    return accepted


@router.get("/ingest/{job_id}", response_model=FilingIngestionJob)
async def get_ingestion_job(job_id: UUID) -> FilingIngestionJob:
    try:
        return filing_ingestion_jobs.get(job_id)
    except IngestionJobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Ingestion job not found") from exc
