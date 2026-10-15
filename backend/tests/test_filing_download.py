from uuid import uuid4

from fastapi.testclient import TestClient

from app.config import Settings
from app.filings import router as filings_router
from app.filings.uploads import FilingDownloadSource, FilingUploadError
from app.main import app

client = TestClient(app)


class FakeStorage:
    requested_path: str | None = None
    requested_limit: int | None = None

    def __init__(self, supabase_url: str, service_key: str, bucket: str) -> None:
        assert supabase_url == "https://project.supabase.co"
        assert service_key == "sb_secret_test"
        assert bucket == "financial-filings"

    def download(self, path: str, max_bytes: int) -> bytes:
        self.__class__.requested_path = path
        self.__class__.requested_limit = max_bytes
        return b"%PDF-1.7 downloaded filing"


def test_download_document_returns_private_stored_file(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    document_id = uuid4()
    source = FilingDownloadSource(
        storage_path=f"company/{document_id}/annual report.pdf",
        file_name="Annual Report 2025.pdf",
        mime_type="application/pdf",
    )
    monkeypatch.setattr(filings_router, "get_filing_download_source", lambda _: source)
    monkeypatch.setattr(filings_router, "SupabaseFilingStorage", FakeStorage)
    monkeypatch.setattr(
        filings_router,
        "get_settings",
        lambda: Settings(
            _env_file=None,
            supabase_url="https://project.supabase.co",
            supabase_secret_key="sb_secret_test",
        ),
    )

    response = client.get(f"/api/filings/documents/{document_id}/download")

    assert response.status_code == 200
    assert response.content == b"%PDF-1.7 downloaded filing"
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == (
        "attachment; filename=\"Annual_Report_2025.pdf\"; "
        "filename*=UTF-8''Annual%20Report%202025.pdf"
    )
    assert response.headers["x-content-type-options"] == "nosniff"
    assert FakeStorage.requested_path == source.storage_path
    assert FakeStorage.requested_limit == 25 * 1024 * 1024


def test_download_document_returns_not_found(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(filings_router, "get_filing_download_source", lambda _: None)

    response = client.get(f"/api/filings/documents/{uuid4()}/download")

    assert response.status_code == 404
    assert response.json() == {"detail": "Filing document not found"}


def test_download_document_rejects_record_without_stored_source(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def missing_source(_):  # type: ignore[no-untyped-def]
        raise FilingUploadError("This filing does not have a stored source file")

    monkeypatch.setattr(filings_router, "get_filing_download_source", missing_source)

    response = client.get(f"/api/filings/documents/{uuid4()}/download")

    assert response.status_code == 409
    assert response.json() == {"detail": "This filing does not have a stored source file"}


def test_download_document_requires_private_storage_key(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    source = FilingDownloadSource(
        storage_path="company/document/report.pdf",
        file_name="report.pdf",
        mime_type="application/pdf",
    )
    monkeypatch.setattr(filings_router, "get_filing_download_source", lambda _: source)
    monkeypatch.setattr(
        filings_router,
        "get_settings",
        lambda: Settings(
            _env_file=None,
            supabase_url="https://project.supabase.co",
            supabase_key="sb_publishable_test",
        ),
    )

    response = client.get(f"/api/filings/documents/{uuid4()}/download")

    assert response.status_code == 503
    assert response.json() == {"detail": "Private filing storage is not configured"}
