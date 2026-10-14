import pytest

from app.filings.downloader import FilingDownloader, FilingDownloadError


def downloader() -> FilingDownloader:
    return FilingDownloader({"sebi.gov.in", "nseindia.com"}, max_bytes=1_000_000)


def test_downloader_accepts_https_subdomain_from_allowlist() -> None:
    downloader().validate_url("https://www.sebi.gov.in/reports/annual-report.pdf")


@pytest.mark.parametrize(
    "url",
    [
        "http://www.sebi.gov.in/report.pdf",
        "https://example.com/report.pdf",
        "https://sebi.gov.in.evil.example/report.pdf",
        "https://user:password@sebi.gov.in/report.pdf",
        "https://sebi.gov.in:8443/report.pdf",
    ],
)
def test_downloader_rejects_unsafe_or_unapproved_urls(url: str) -> None:
    with pytest.raises(FilingDownloadError):
        downloader().validate_url(url)
