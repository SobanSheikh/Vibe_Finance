import re
from datetime import date
from urllib.parse import quote
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)

from app.config import get_settings
from app.filings.contracts import (
    FilingDocumentResponse,
    FilingIngestionAccepted,
    FilingIngestionJob,
    FilingIngestionRequest,
    SecSyncAccepted,
    SecSyncJob,
    SecSyncRequest,
)
from app.filings.downloader import FilingDownloadError
from app.filings.jobs import (
    IngestionJobNotFoundError,
    filing_ingestion_jobs,
    process_uploaded_filing,
)
from app.filings.sec_jobs import (
    SecSyncError,
    SecSyncJobNotFoundError,
    sec_sync_jobs,
)
from app.filings.storage import FilingStorageError, SupabaseFilingStorage
from app.filings.uploads import (
    FilingUploadError,
    FilingUploadService,
    get_filing_document,
    get_filing_download_source,
    list_filing_documents,
    prepare_filing_retry,
    validate_pdf_upload,
)

router = APIRouter(prefix="/api/filings", tags=["filings"])


def _content_disposition(file_name: str) -> str:
    fallback = re.sub(r"[^A-Za-z0-9._-]+", "_", file_name).strip("._")
    fallback = fallback[:150] or "filing-download"
    encoded = quote(file_name, safe="")
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{encoded}"


@router.post(
    "/sec/sync",
    response_model=SecSyncAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def sync_sec_filings(
    request: SecSyncRequest,
    background_tasks: BackgroundTasks,
) -> SecSyncAccepted:
    try:
        accepted = sec_sync_jobs.create(request)
    except SecSyncError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    background_tasks.add_task(sec_sync_jobs.run, accepted.job_id)
    return accepted


@router.get("/sec/sync/{job_id}", response_model=SecSyncJob)
def get_sec_sync_job(job_id: UUID) -> SecSyncJob:
    try:
        return sec_sync_jobs.get(job_id)
    except SecSyncJobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="SEC sync job not found") from exc


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


@router.post(
    "/upload",
    response_model=FilingDocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_filing(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    company_id: UUID = Form(...),
    title: str = Form(..., min_length=1, max_length=500),
    document_type: str = Form("annual_report", min_length=1, max_length=80),
    source_name: str = Form("Uploaded filing", min_length=1, max_length=150),
    reporting_period: str = Form(..., min_length=1, max_length=80),
    published_at: date | None = Form(None),
    source_url: str | None = Form(None, max_length=2_000),
) -> FilingDocumentResponse:
    settings = get_settings()
    max_bytes = settings.filing_max_download_mb * 1024 * 1024
    content = await file.read(max_bytes + 1)
    await file.close()
    try:
        validate_pdf_upload(
            file.filename or "filing.pdf",
            file.content_type,
            content,
            max_bytes,
        )
        if source_url and not source_url.startswith("https://"):
            raise FilingUploadError("Source URL must use HTTPS")
        document = await FilingUploadService(settings).accept(
            company_id=company_id,
            title=title,
            document_type=document_type,
            source_name=source_name,
            reporting_period=reporting_period,
            published_at=published_at,
            source_url=source_url,
            file_name=file.filename or "filing.pdf",
            content_type="application/pdf",
            content=content,
        )
    except FilingUploadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FilingStorageError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if document.processing_status != "completed":
        background_tasks.add_task(process_uploaded_filing, document.id)
    return document


@router.get("/documents", response_model=list[FilingDocumentResponse])
def list_documents(company_id: UUID) -> list[FilingDocumentResponse]:
    return list_filing_documents(company_id)


@router.get("/documents/{document_id}", response_model=FilingDocumentResponse)
def get_document(document_id: UUID) -> FilingDocumentResponse:
    document = get_filing_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Filing document not found")
    return document


@router.get(
    "/documents/{document_id}/download",
    response_class=Response,
    responses={
        200: {
            "description": "The original uploaded or synchronized filing",
            "content": {
                "application/pdf": {},
                "text/html": {},
                "application/octet-stream": {},
            },
        },
        404: {"description": "Filing document not found"},
        409: {"description": "Filing has no stored source file"},
        502: {"description": "Stored file could not be loaded"},
        503: {"description": "Private filing storage is not configured"},
    },
)
def download_document(document_id: UUID) -> Response:
    try:
        source = get_filing_download_source(document_id)
    except FilingUploadError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if source is None:
        raise HTTPException(status_code=404, detail="Filing document not found")

    settings = get_settings()
    backend_key = settings.supabase_backend_key
    if not settings.supabase_url or not backend_key or backend_key.startswith("sb_publishable_"):
        raise HTTPException(
            status_code=503,
            detail="Private filing storage is not configured",
        )
    try:
        storage = SupabaseFilingStorage(
            settings.supabase_url,
            backend_key,
            settings.filing_storage_bucket,
        )
        content = storage.download(
            source.storage_path,
            settings.filing_max_download_mb * 1024 * 1024,
        )
    except FilingStorageError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return Response(
        content=content,
        media_type=source.mime_type,
        headers={
            "Content-Disposition": _content_disposition(source.file_name),
            "Cache-Control": "private, max-age=300",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post(
    "/documents/{document_id}/retry",
    response_model=FilingDocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def retry_document(
    document_id: UUID,
    background_tasks: BackgroundTasks,
) -> FilingDocumentResponse:
    try:
        document = prepare_filing_retry(document_id)
    except FilingUploadError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if document is None:
        raise HTTPException(status_code=404, detail="Filing document not found")
    background_tasks.add_task(process_uploaded_filing, document_id)
    return document
