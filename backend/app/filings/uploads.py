import asyncio
import re
from datetime import date
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select

from app.config import Settings, get_settings
from app.db.models import (
    Company,
    DocumentChunk,
    DocumentProcessingStatus,
    FinancialDocument,
)
from app.db.session import get_session_factory
from app.filings.contracts import FilingDocumentResponse
from app.filings.storage import SupabaseFilingStorage


class FilingUploadError(ValueError):
    pass


def validate_pdf_upload(
    file_name: str,
    content_type: str | None,
    content: bytes,
    max_bytes: int,
) -> None:
    if not file_name.lower().endswith(".pdf"):
        raise FilingUploadError("Only PDF filings are supported")
    if content_type not in {"application/pdf", "application/octet-stream"}:
        raise FilingUploadError("Uploaded filing must use a PDF content type")
    if not content:
        raise FilingUploadError("Uploaded filing is empty")
    if len(content) > max_bytes:
        raise FilingUploadError("Uploaded filing exceeds the configured size limit")
    if not content.startswith(b"%PDF-"):
        raise FilingUploadError("Uploaded file does not contain a valid PDF signature")


class FilingUploadService:
    def __init__(
        self,
        settings: Settings | None = None,
        storage: SupabaseFilingStorage | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        key = self.settings.supabase_backend_key
        if storage is None:
            if not self.settings.supabase_url or not key:
                raise FilingUploadError("Supabase filing storage is not configured")
            if key.startswith("sb_publishable_"):
                raise FilingUploadError(
                    "Private filing storage requires SUPABASE_SECRET_KEY, not a publishable key"
                )
            storage = SupabaseFilingStorage(
                self.settings.supabase_url,
                key,
                self.settings.filing_storage_bucket,
            )
        self.storage = storage

    async def accept(
        self,
        *,
        company_id: UUID,
        title: str,
        document_type: str,
        source_name: str,
        reporting_period: str | None,
        published_at: date | None,
        source_url: str | None,
        file_name: str,
        content_type: str,
        content: bytes,
    ) -> FilingDocumentResponse:
        document_type = document_type.strip().lower()
        reporting_period = reporting_period.strip() if reporting_period else None
        if not reporting_period:
            raise FilingUploadError("A reporting period is required")
        checksum = sha256(content).hexdigest()
        existing = await asyncio.to_thread(
            self._update_existing_metadata,
            company_id,
            checksum,
            title,
            document_type,
            source_name,
            reporting_period,
            published_at,
            source_url,
        )
        if existing is not None:
            return existing

        replacement = await asyncio.to_thread(
            self._find_period_match,
            company_id,
            document_type,
            reporting_period,
        )
        if replacement is not None:
            document_id, storage_path = replacement
            await self.storage.upload(
                storage_path,
                content,
                content_type,
                upsert=True,
            )
            return await asyncio.to_thread(
                self._replace_pending_document,
                document_id,
                title,
                document_type,
                source_name,
                reporting_period,
                published_at,
                source_url,
                file_name,
                content_type,
                content,
                checksum,
            )

        document_id = uuid4()
        safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "-", file_name).strip("-_")
        safe_name = safe_name or "filing.pdf"
        storage_path = f"{company_id}/{document_id}/{safe_name}"
        await self.storage.upload(storage_path, content, content_type)

        return await asyncio.to_thread(
            self._persist_pending_document,
            document_id,
            company_id,
            title,
            document_type,
            source_name,
            reporting_period,
            published_at,
            source_url,
            file_name,
            content_type,
            content,
            checksum,
            storage_path,
        )

    @staticmethod
    def _find_period_match(
        company_id: UUID,
        document_type: str,
        reporting_period: str,
    ) -> tuple[UUID, str] | None:
        with get_session_factory()() as session:
            document = session.scalar(
                select(FinancialDocument).where(
                    FinancialDocument.company_id == company_id,
                    func.lower(func.trim(FinancialDocument.document_type)) == document_type.lower(),
                    func.lower(func.trim(FinancialDocument.reporting_period))
                    == reporting_period.lower(),
                )
            )
            if document is None:
                return None
            if not document.storage_path:
                raise FilingUploadError(
                    "This filing period is occupied by a document without a stored source"
                )
            return document.id, document.storage_path

    @staticmethod
    def _replace_pending_document(
        document_id: UUID,
        title: str,
        document_type: str,
        source_name: str,
        reporting_period: str,
        published_at: date | None,
        source_url: str | None,
        file_name: str,
        content_type: str,
        content: bytes,
        checksum: str,
    ) -> FilingDocumentResponse:
        with get_session_factory()() as session:
            document = session.get(FinancialDocument, document_id)
            if document is None:
                raise FilingUploadError("The filing selected for replacement no longer exists")
            session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
            document.title = title
            document.document_type = document_type
            document.source_name = source_name
            document.reporting_period = reporting_period
            document.published_at = published_at
            document.source_url = source_url
            document.file_name = file_name
            document.file_size_bytes = len(content)
            document.mime_type = content_type
            document.checksum = checksum
            document.processing_status = DocumentProcessingStatus.PENDING
            document.error_message = None
            document.page_count = None
            document.chunk_count = None
            session.commit()
            session.refresh(document)
            return filing_document_response(document)

    @staticmethod
    def _update_existing_metadata(
        company_id: UUID,
        checksum: str,
        title: str,
        document_type: str,
        source_name: str,
        reporting_period: str | None,
        published_at: date | None,
        source_url: str | None,
    ) -> FilingDocumentResponse | None:
        session_factory = get_session_factory()
        with session_factory() as session:
            if session.scalar(select(Company.id).where(Company.id == company_id)) is None:
                raise FilingUploadError("Company does not exist")
            existing = session.scalar(
                select(FinancialDocument).where(FinancialDocument.checksum == checksum)
            )
            if existing is not None:
                if existing.company_id != company_id:
                    raise FilingUploadError(
                        "This filing is already associated with another company"
                    )
                existing.title = title
                existing.document_type = document_type
                existing.source_name = source_name
                existing.reporting_period = reporting_period
                existing.published_at = published_at
                existing.source_url = source_url
                session.commit()
                session.refresh(existing)
                return filing_document_response(existing)
        return None

    @staticmethod
    def _persist_pending_document(
        document_id: UUID,
        company_id: UUID,
        title: str,
        document_type: str,
        source_name: str,
        reporting_period: str | None,
        published_at: date | None,
        source_url: str | None,
        file_name: str,
        content_type: str,
        content: bytes,
        checksum: str,
        storage_path: str,
    ) -> FilingDocumentResponse:
        session_factory = get_session_factory()
        with session_factory() as session:
            document = FinancialDocument(
                id=document_id,
                company_id=company_id,
                title=title,
                document_type=document_type,
                reporting_period=reporting_period,
                source_url=source_url,
                source_name=source_name,
                published_at=published_at,
                is_synthetic=False,
                checksum=checksum,
                storage_path=storage_path,
                file_name=file_name,
                file_size_bytes=len(content),
                mime_type=content_type,
                processing_status=DocumentProcessingStatus.PENDING,
            )
            session.add(document)
            session.commit()
            session.refresh(document)
            return filing_document_response(document)


def filing_document_response(document: FinancialDocument) -> FilingDocumentResponse:
    return FilingDocumentResponse(
        id=document.id,
        company_id=document.company_id,
        title=document.title,
        document_type=document.document_type,
        reporting_period=document.reporting_period,
        source_url=document.source_url,
        source_name=document.source_name,
        published_at=document.published_at,
        file_name=document.file_name,
        file_size_bytes=document.file_size_bytes,
        processing_status=document.processing_status.value,
        error_message=document.error_message,
        page_count=document.page_count,
        chunk_count=document.chunk_count,
    )


def get_filing_document(document_id: UUID) -> FilingDocumentResponse | None:
    with get_session_factory()() as session:
        document = session.get(FinancialDocument, document_id)
        return filing_document_response(document) if document else None


def list_filing_documents(company_id: UUID) -> list[FilingDocumentResponse]:
    with get_session_factory()() as session:
        documents = session.scalars(
            select(FinancialDocument)
            .where(FinancialDocument.company_id == company_id)
            .order_by(FinancialDocument.created_at.desc())
        ).all()
        return [filing_document_response(document) for document in documents]


def prepare_filing_retry(document_id: UUID) -> FilingDocumentResponse | None:
    with get_session_factory()() as session:
        document = session.get(FinancialDocument, document_id)
        if document is None:
            return None
        if not document.storage_path:
            raise FilingUploadError("Only uploaded filings can be retried")
        session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
        document.processing_status = DocumentProcessingStatus.PENDING
        document.error_message = None
        document.page_count = None
        document.chunk_count = None
        session.commit()
        session.refresh(document)
        return filing_document_response(document)
