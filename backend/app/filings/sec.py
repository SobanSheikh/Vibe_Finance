from dataclasses import dataclass
from datetime import date

import httpx


class SecEdgarError(RuntimeError):
    pass


@dataclass(frozen=True)
class SecFiling:
    accession_number: str
    form: str
    filing_date: date
    report_date: date | None
    primary_document: str
    source_url: str

    def document_type(self) -> str:
        return {
            "10-K": "annual_report",
            "10-Q": "quarterly_report",
            "8-K": "regulatory_filing",
        }[self.form]

    def reporting_period(self) -> str:
        if self.form == "10-K" and self.report_date:
            return f"FY {self.report_date.year}"
        if self.form == "10-Q" and self.report_date:
            return f"Quarter ended {self.report_date.isoformat()}"
        return f"Filed {self.filing_date.isoformat()} · {self.accession_number}"


class SecEdgarClient:
    submissions_base_url = "https://data.sec.gov/submissions"
    archives_base_url = "https://www.sec.gov/Archives/edgar/data"

    def __init__(
        self,
        user_agent: str,
        max_bytes: int,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not user_agent.strip() or "@" not in user_agent or "your-email" in user_agent:
            raise SecEdgarError("Set SEC_USER_AGENT to an application name and real contact email")
        self.user_agent = user_agent.strip()
        self.max_bytes = max_bytes
        self._client = client

    @property
    def headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
        }

    async def discover_recent(
        self,
        cik: str,
        forms: list[str],
        per_form_limit: int,
    ) -> list[SecFiling]:
        normalized_cik = cik.zfill(10)
        response = await self._get(f"{self.submissions_base_url}/CIK{normalized_cik}.json")
        try:
            response.raise_for_status()
            payload = response.json()
            recent = payload["filings"]["recent"]
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise SecEdgarError("SEC filing discovery failed") from exc

        selected: list[SecFiling] = []
        counts = {form: 0 for form in forms}
        rows = zip(
            recent.get("accessionNumber", []),
            recent.get("form", []),
            recent.get("filingDate", []),
            recent.get("reportDate", []),
            recent.get("primaryDocument", []),
        )
        for accession, form, filed, reported, primary_document in rows:
            if form not in counts or counts[form] >= per_form_limit or not primary_document:
                continue
            try:
                filing_date = date.fromisoformat(filed)
                report_date = date.fromisoformat(reported) if reported else None
            except ValueError:
                continue
            accession_path = accession.replace("-", "")
            cik_path = str(int(normalized_cik))
            source_url = f"{self.archives_base_url}/{cik_path}/{accession_path}/{primary_document}"
            selected.append(
                SecFiling(
                    accession_number=accession,
                    form=form,
                    filing_date=filing_date,
                    report_date=report_date,
                    primary_document=primary_document,
                    source_url=source_url,
                )
            )
            counts[form] += 1
            if all(count >= per_form_limit for count in counts.values()):
                break
        return selected

    async def download_html(self, filing: SecFiling) -> bytes:
        response = await self._get(filing.source_url)
        try:
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SecEdgarError("SEC filing download failed") from exc
        content = response.content
        if not content:
            raise SecEdgarError("SEC filing download was empty")
        if len(content) > self.max_bytes:
            raise SecEdgarError("SEC filing exceeds the configured download limit")
        prefix = content[:1_000].lower()
        if b"<html" not in prefix and b"<!doctype html" not in prefix:
            raise SecEdgarError("SEC primary document was not HTML")
        return content

    async def _get(self, url: str) -> httpx.Response:
        try:
            if self._client is not None:
                return await self._client.get(url, headers=self.headers)
            async with httpx.AsyncClient(timeout=45, follow_redirects=True) as client:
                return await client.get(url, headers=self.headers)
        except httpx.HTTPError as exc:
            raise SecEdgarError("SEC request failed") from exc
