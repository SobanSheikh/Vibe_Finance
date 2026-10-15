import pytest

from app.config import Settings
from app.filings.storage import SupabaseFilingStorage
from app.filings.uploads import FilingUploadError, FilingUploadService, validate_pdf_upload


def test_pdf_upload_validation_accepts_pdf_signature() -> None:
    validate_pdf_upload(
        "annual-report.pdf",
        "application/pdf",
        b"%PDF-1.7 test content",
        1_000,
    )


@pytest.mark.parametrize(
    ("file_name", "content_type", "content", "message"),
    [
        ("report.txt", "application/pdf", b"%PDF-1.7", "Only PDF"),
        ("report.pdf", "text/plain", b"%PDF-1.7", "PDF content type"),
        ("report.pdf", "application/pdf", b"", "empty"),
        ("report.pdf", "application/pdf", b"not a pdf", "PDF signature"),
    ],
)
def test_pdf_upload_validation_rejects_invalid_files(
    file_name: str,
    content_type: str,
    content: bytes,
    message: str,
) -> None:
    with pytest.raises(FilingUploadError, match=message):
        validate_pdf_upload(file_name, content_type, content, 1_000)


def test_pdf_upload_validation_rejects_oversized_file() -> None:
    with pytest.raises(FilingUploadError, match="size limit"):
        validate_pdf_upload("report.pdf", "application/pdf", b"%PDF-123", 7)


def test_storage_object_url_escapes_path_segments() -> None:
    storage = SupabaseFilingStorage(
        "https://project.supabase.co/",
        "test-service-key",
        "financial-filings",
    )

    assert storage._object_url("company id/report 2025.pdf") == (  # noqa: SLF001
        "https://project.supabase.co/storage/v1/object/financial-filings/"
        "company%20id/report%202025.pdf"
    )


def test_opaque_secret_key_is_sent_only_as_api_key() -> None:
    storage = SupabaseFilingStorage(
        "https://project.supabase.co",
        "sb_secret_example",
        "financial-filings",
    )

    assert storage._headers() == {"apikey": "sb_secret_example"}  # noqa: SLF001


def test_storage_upload_headers_allow_explicit_replacement() -> None:
    storage = SupabaseFilingStorage(
        "https://project.supabase.co",
        "sb_secret_example",
        "financial-filings",
    )

    assert storage._headers("application/pdf", upsert=True) == {  # noqa: SLF001
        "apikey": "sb_secret_example",
        "Content-Type": "application/pdf",
        "x-upsert": "true",
    }


def test_legacy_service_role_jwt_is_also_sent_as_bearer_token() -> None:
    storage = SupabaseFilingStorage(
        "https://project.supabase.co",
        "eyJlegacy-service-role",
        "financial-filings",
    )

    assert storage._headers() == {  # noqa: SLF001
        "apikey": "eyJlegacy-service-role",
        "Authorization": "Bearer eyJlegacy-service-role",
    }


def test_upload_service_rejects_publishable_key_for_private_storage() -> None:
    settings = Settings(
        _env_file=None,
        supabase_url="https://project.supabase.co",
        supabase_key="sb_publishable_example",
    )

    with pytest.raises(FilingUploadError, match="SUPABASE_SECRET_KEY"):
        FilingUploadService(settings)
