from urllib.parse import quote

import httpx


class FilingStorageError(RuntimeError):
    pass


class SupabaseFilingStorage:
    """Private object storage for uploaded source documents."""

    def __init__(self, supabase_url: str, service_key: str, bucket: str) -> None:
        if not supabase_url or not service_key or not bucket:
            raise FilingStorageError("Supabase filing storage is not configured")
        self._base_url = supabase_url.rstrip("/")
        self._service_key = service_key
        self.bucket = bucket

    def _object_url(self, path: str) -> str:
        safe_bucket = quote(self.bucket, safe="")
        safe_path = quote(path, safe="/")
        return f"{self._base_url}/storage/v1/object/{safe_bucket}/{safe_path}"

    def _headers(
        self,
        content_type: str | None = None,
        *,
        upsert: bool = False,
    ) -> dict[str, str]:
        headers = {"apikey": self._service_key}
        if self._service_key.startswith("eyJ"):
            headers["Authorization"] = f"Bearer {self._service_key}"
        if content_type:
            headers["Content-Type"] = content_type
            headers["x-upsert"] = str(upsert).lower()
        return headers

    async def upload(
        self,
        path: str,
        content: bytes,
        content_type: str,
        *,
        upsert: bool = False,
    ) -> None:
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    self._object_url(path),
                    headers=self._headers(content_type, upsert=upsert),
                    content=content,
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise FilingStorageError("Could not store the uploaded filing") from exc

    def download(self, path: str, max_bytes: int) -> bytes:
        try:
            with httpx.Client(timeout=60) as client:
                response = client.get(
                    self._object_url(path),
                    headers=self._headers(),
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise FilingStorageError("Could not load the uploaded filing") from exc
        if len(response.content) > max_bytes:
            raise FilingStorageError("Stored filing exceeds the configured size limit")
        return response.content
