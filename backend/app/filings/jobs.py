import asyncio
from copy import deepcopy
from threading import Lock
from uuid import UUID, uuid4

from sqlalchemy import select

from app.config import get_settings
from app.db.models import Company
from app.db.session import get_session_factory
from app.filings.contracts import (
    FilingIngestionAccepted,
    FilingIngestionJob,
    FilingIngestionRequest,
    IngestionStatus,
)
from app.filings.downloader import FilingDownloader
from app.filings.models import DocumentMetadata
from app.filings.service import FilingIngestionService


class IngestionJobNotFoundError(LookupError):
    pass


class FilingIngestionJobs:
    def __init__(self) -> None:
        settings = get_settings()
        self._downloader = FilingDownloader(
            allowed_hosts=settings.filing_host_allowlist,
            max_bytes=settings.filing_max_download_mb * 1024 * 1024,
        )
        self._jobs: dict[UUID, FilingIngestionJob] = {}
        self._requests: dict[UUID, FilingIngestionRequest] = {}
        self._lock = Lock()

    def create(self, request: FilingIngestionRequest) -> FilingIngestionAccepted:
        self._downloader.validate_url(str(request.source_url))
        job_id = uuid4()
        job = FilingIngestionJob(job_id=job_id, status=IngestionStatus.PENDING)
        with self._lock:
            self._jobs[job_id] = job
            self._requests[job_id] = request
        return FilingIngestionAccepted(job_id=job_id, status=job.status)

    def get(self, job_id: UUID) -> FilingIngestionJob:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise IngestionJobNotFoundError(str(job_id))
            return deepcopy(job)

    async def run(self, job_id: UUID) -> None:
        request = self._requests[job_id]
        self._set_status(job_id, IngestionStatus.DOWNLOADING)
        try:
            content = await self._downloader.download(str(request.source_url))
            self._set_status(job_id, IngestionStatus.PROCESSING)
            result = await asyncio.to_thread(self._process, request, content)
            with self._lock:
                self._jobs[job_id] = FilingIngestionJob(
                    job_id=job_id,
                    status=IngestionStatus.COMPLETED,
                    document_id=result.document_id,
                    page_count=result.page_count,
                    chunk_count=result.chunk_count,
                )
        except Exception:
            with self._lock:
                self._jobs[job_id] = FilingIngestionJob(
                    job_id=job_id,
                    status=IngestionStatus.FAILED,
                    error="Filing ingestion failed. Review server logs for details.",
                )
            raise

    @staticmethod
    def _process(request: FilingIngestionRequest, content: bytes):  # type: ignore[no-untyped-def]
        session_factory = get_session_factory()
        with session_factory() as session:
            company_exists = session.scalar(
                select(Company.id).where(Company.id == request.company_id)
            )
            if company_exists is None:
                raise ValueError("Company does not exist")
            metadata = DocumentMetadata(
                company_id=request.company_id,
                title=request.title,
                document_type=request.document_type,
                source_url=str(request.source_url),
                source_name=request.source_name,
                reporting_period=request.reporting_period,
                published_at=request.published_at,
            )
            return FilingIngestionService().ingest_pdf(session, metadata, content)

    def _set_status(self, job_id: UUID, status: IngestionStatus) -> None:
        with self._lock:
            current = self._jobs[job_id]
            self._jobs[job_id] = current.model_copy(update={"status": status})


filing_ingestion_jobs = FilingIngestionJobs()
