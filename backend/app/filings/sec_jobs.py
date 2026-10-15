import asyncio
import logging
import re
from copy import deepcopy
from hashlib import sha256
from threading import Lock
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.db.models import Company, DocumentProcessingStatus, FinancialDocument
from app.db.session import get_session_factory
from app.filings.contracts import (
    SecSyncAccepted,
    SecSyncJob,
    SecSyncRequest,
    SecSyncStatus,
)
from app.filings.jobs import process_uploaded_filing
from app.filings.sec import SecEdgarClient, SecEdgarError, SecFiling
from app.filings.storage import SupabaseFilingStorage

logger = logging.getLogger(__name__)


class SecSyncError(ValueError):
    pass


class SecSyncJobNotFoundError(LookupError):
    pass


class SecSyncJobs:
    def __init__(self) -> None:
        self._jobs: dict[UUID, SecSyncJob] = {}
        self._requests: dict[UUID, SecSyncRequest] = {}
        self._lock = Lock()

    def create(self, request: SecSyncRequest) -> SecSyncAccepted:
        settings = get_settings()
        key = settings.supabase_backend_key
        if not settings.sec_user_agent:
            raise SecSyncError("Set SEC_USER_AGENT to 'VibeFinance your-real-email@example.com'")
        try:
            SecEdgarClient(
                settings.sec_user_agent,
                settings.filing_max_download_mb * 1024 * 1024,
            )
        except SecEdgarError as exc:
            raise SecSyncError(str(exc)) from exc
        if not settings.supabase_url or not key or key.startswith("sb_publishable_"):
            raise SecSyncError("SEC sync requires configured private Supabase storage")
        with get_session_factory()() as session:
            company = session.get(Company, request.company_id)
            if company is None:
                raise SecSyncError("Company does not exist")
            if not company.sec_cik:
                raise SecSyncError("This company does not have an SEC CIK configured")

        job_id = uuid4()
        job = SecSyncJob(job_id=job_id, status=SecSyncStatus.PENDING)
        with self._lock:
            self._jobs[job_id] = job
            self._requests[job_id] = request
        return SecSyncAccepted(job_id=job_id, status=job.status)

    def get(self, job_id: UUID) -> SecSyncJob:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise SecSyncJobNotFoundError(str(job_id))
            return deepcopy(job)

    async def run(self, job_id: UUID) -> None:
        request = self._requests[job_id]
        settings = get_settings()
        key = settings.supabase_backend_key
        assert settings.sec_user_agent and settings.supabase_url and key
        client = SecEdgarClient(
            settings.sec_user_agent,
            settings.filing_max_download_mb * 1024 * 1024,
        )
        storage = SupabaseFilingStorage(
            settings.supabase_url,
            key,
            settings.filing_storage_bucket,
        )
        try:
            company = await asyncio.to_thread(self._load_company, request.company_id)
            self._update(job_id, status=SecSyncStatus.DISCOVERING)
            filings = await client.discover_recent(
                company.sec_cik or "",
                request.forms,
                request.per_form_limit,
            )
            self._update(
                job_id,
                status=SecSyncStatus.PROCESSING,
                discovered_count=len(filings),
            )
            for filing in filings:
                if await asyncio.to_thread(self._already_stored, company.id, filing):
                    self._increment(job_id, "skipped_count")
                    continue
                try:
                    content = await client.download_html(filing)
                    document_id = uuid4()
                    safe_name = (
                        re.sub(r"[^a-zA-Z0-9._-]+", "-", filing.primary_document).strip("-_")
                        or "filing.html"
                    )
                    storage_path = (
                        f"{company.id}/sec/{filing.accession_number.replace('-', '')}/{safe_name}"
                    )
                    await storage.upload(storage_path, content, "text/html", upsert=True)
                    persisted = await asyncio.to_thread(
                        self._persist_pending,
                        document_id,
                        company,
                        filing,
                        storage_path,
                        safe_name,
                        content,
                    )
                    if not persisted:
                        self._increment(job_id, "skipped_count")
                        continue
                    await asyncio.to_thread(process_uploaded_filing, document_id)
                    if await asyncio.to_thread(self._completed, document_id):
                        self._append_completed(job_id, document_id)
                    else:
                        self._increment(job_id, "failed_count")
                except Exception:
                    logger.exception(
                        "SEC filing sync failed for accession %s",
                        filing.accession_number,
                    )
                    self._increment(job_id, "failed_count")

            current = self.get(job_id)
            if current.failed_count == 0:
                final_status = SecSyncStatus.COMPLETED
            elif current.completed_count or current.skipped_count:
                final_status = SecSyncStatus.PARTIAL
            else:
                final_status = SecSyncStatus.FAILED
            self._update(job_id, status=final_status)
        except Exception:
            logger.exception("SEC filing sync job %s failed", job_id)
            self._update(
                job_id,
                status=SecSyncStatus.FAILED,
                error="SEC sync failed. Review the server logs and SEC configuration.",
            )

    @staticmethod
    def _load_company(company_id: UUID) -> Company:
        with get_session_factory()() as session:
            company = session.get(Company, company_id)
            if company is None:
                raise SecSyncError("Company does not exist")
            session.expunge(company)
            return company

    @staticmethod
    def _already_stored(company_id: UUID, filing: SecFiling) -> bool:
        with get_session_factory()() as session:
            document_id = session.scalar(
                select(FinancialDocument.id).where(
                    FinancialDocument.company_id == company_id,
                    or_(
                        (
                            (FinancialDocument.source_provider == "sec_edgar")
                            & (FinancialDocument.external_id == filing.accession_number)
                        ),
                        (
                            func.lower(func.trim(FinancialDocument.document_type))
                            == filing.document_type()
                        )
                        & (
                            func.lower(func.trim(FinancialDocument.reporting_period))
                            == filing.reporting_period().lower()
                        ),
                    ),
                )
            )
            return document_id is not None

    @staticmethod
    def _persist_pending(
        document_id: UUID,
        company: Company,
        filing: SecFiling,
        storage_path: str,
        file_name: str,
        content: bytes,
    ) -> bool:
        with get_session_factory()() as session:
            document = FinancialDocument(
                id=document_id,
                company_id=company.id,
                title=f"{company.name} {filing.form} filed {filing.filing_date.isoformat()}",
                document_type=filing.document_type(),
                reporting_period=filing.reporting_period(),
                source_url=filing.source_url,
                source_name="SEC EDGAR",
                source_provider="sec_edgar",
                external_id=filing.accession_number,
                published_at=filing.filing_date,
                is_synthetic=False,
                checksum=sha256(content).hexdigest(),
                storage_path=storage_path,
                file_name=file_name,
                file_size_bytes=len(content),
                mime_type="text/html",
                processing_status=DocumentProcessingStatus.PENDING,
            )
            session.add(document)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                return False
            return True

    @staticmethod
    def _completed(document_id: UUID) -> bool:
        with get_session_factory()() as session:
            status = session.scalar(
                select(FinancialDocument.processing_status).where(
                    FinancialDocument.id == document_id
                )
            )
            return status == DocumentProcessingStatus.COMPLETED

    def _update(self, job_id: UUID, **values: object) -> None:
        with self._lock:
            self._jobs[job_id] = self._jobs[job_id].model_copy(update=values)

    def _increment(self, job_id: UUID, field: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            self._jobs[job_id] = job.model_copy(update={field: getattr(job, field) + 1})

    def _append_completed(self, job_id: UUID, document_id: UUID) -> None:
        with self._lock:
            job = self._jobs[job_id]
            self._jobs[job_id] = job.model_copy(
                update={
                    "completed_count": job.completed_count + 1,
                    "document_ids": [*job.document_ids, document_id],
                }
            )


sec_sync_jobs = SecSyncJobs()
