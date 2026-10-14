from urllib.parse import urlparse

import httpx


class FilingDownloadError(ValueError):
    pass


class FilingDownloader:
    def __init__(self, allowed_hosts: set[str], max_bytes: int) -> None:
        self.allowed_hosts = {host.lower() for host in allowed_hosts}
        self.max_bytes = max_bytes

    def validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        if parsed.scheme != "https":
            raise FilingDownloadError("Filing URLs must use HTTPS")
        if not hostname or not any(
            hostname == allowed or hostname.endswith(f".{allowed}")
            for allowed in self.allowed_hosts
        ):
            raise FilingDownloadError("Filing URL host is not allowed")
        if parsed.username or parsed.password or parsed.port not in (None, 443):
            raise FilingDownloadError("Filing URL contains unsupported authority information")

    async def download(self, url: str) -> bytes:
        self.validate_url(url)
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
                async with client.stream(
                    "GET",
                    url,
                    headers={"User-Agent": "VibeFinance/0.1 educational-hackathon"},
                ) as response:
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").lower()
                    has_pdf_extension = urlparse(url).path.lower().endswith(".pdf")
                    if "pdf" not in content_type and not has_pdf_extension:
                        raise FilingDownloadError("Source did not return a PDF")
                    declared_length = int(response.headers.get("content-length", "0"))
                    if declared_length > self.max_bytes:
                        raise FilingDownloadError("PDF exceeds the configured download limit")
                    content = bytearray()
                    async for chunk in response.aiter_bytes():
                        content.extend(chunk)
                        if len(content) > self.max_bytes:
                            raise FilingDownloadError("PDF exceeds the configured download limit")
                    if not content.startswith(b"%PDF"):
                        raise FilingDownloadError("Downloaded content is not a valid PDF")
                    return bytes(content)
        except httpx.HTTPError as exc:
            raise FilingDownloadError("Filing download failed") from exc
