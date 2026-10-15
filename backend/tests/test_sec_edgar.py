import asyncio

import httpx
import pytest

from app.filings.extraction import extract_html_sections
from app.filings.sec import SecEdgarClient, SecEdgarError


def test_html_extraction_keeps_visible_text_and_removes_hidden_content() -> None:
    content = b"""
        <html><head><style>secret css</style><script>secret script</script></head>
        <body><h1>Annual report</h1><p>Revenue increased by 12 percent.</p>
        <ix:hidden>secret xbrl metadata</ix:hidden></body></html>
    """

    sections = extract_html_sections(content)

    assert len(sections) == 1
    assert sections[0].page_number is None
    assert "Annual report" in sections[0].content
    assert "Revenue increased" in sections[0].content
    assert "secret" not in sections[0].content


def test_sec_client_requires_identifiable_user_agent() -> None:
    with pytest.raises(SecEdgarError, match="SEC_USER_AGENT"):
        SecEdgarClient("VibeFinance", 1_000)


def test_sec_discovery_selects_one_recent_filing_per_form() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["User-Agent"] == "VibeFinance developer@example.com"
        return httpx.Response(
            200,
            json={
                "filings": {
                    "recent": {
                        "accessionNumber": ["0001-26-000003", "0001-26-000002", "0001-26-000001"],
                        "form": ["8-K", "10-Q", "10-K"],
                        "filingDate": ["2026-10-10", "2026-08-01", "2026-02-01"],
                        "reportDate": ["2026-10-09", "2026-06-30", "2025-12-31"],
                        "primaryDocument": ["event.htm", "quarter.htm", "annual.htm"],
                    }
                }
            },
            request=request,
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            client = SecEdgarClient(
                "VibeFinance developer@example.com",
                1_000_000,
                client=http_client,
            )
            filings = await client.discover_recent(
                "0001652044",
                ["10-K", "10-Q", "8-K"],
                1,
            )

        assert [filing.form for filing in filings] == ["8-K", "10-Q", "10-K"]
        assert filings[-1].reporting_period() == "FY 2025"
        assert filings[-1].source_url == (
            "https://www.sec.gov/Archives/edgar/data/1652044/000126000001/annual.htm"
        )

    asyncio.run(run())
