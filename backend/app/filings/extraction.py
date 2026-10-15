import re
from html.parser import HTMLParser
from io import BytesIO

from pypdf import PdfReader

from app.filings.models import ExtractedPage


class DocumentExtractionError(ValueError):
    pass


class _VisibleTextParser(HTMLParser):
    _hidden_tags = {"script", "style", "noscript", "ix:hidden"}
    _block_tags = {
        "address",
        "article",
        "aside",
        "blockquote",
        "br",
        "div",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "li",
        "main",
        "p",
        "section",
        "table",
        "td",
        "th",
        "tr",
        "ul",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag.lower() in self._hidden_tags:
            self._hidden_depth += 1
        elif not self._hidden_depth and tag.lower() in self._block_tags:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._hidden_tags:
            self._hidden_depth = max(0, self._hidden_depth - 1)
        elif not self._hidden_depth and tag.lower() in self._block_tags:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._hidden_depth:
            self.parts.append(data)


def extract_pdf_pages(content: bytes) -> list[ExtractedPage]:
    if not content:
        raise DocumentExtractionError("PDF content is empty")
    try:
        reader = PdfReader(BytesIO(content))
        pages = [
            ExtractedPage(page_number=index, content=(page.extract_text() or "").strip())
            for index, page in enumerate(reader.pages, start=1)
        ]
    except Exception as exc:
        raise DocumentExtractionError("PDF text extraction failed") from exc

    readable_pages = [page for page in pages if page.content]
    if not readable_pages:
        raise DocumentExtractionError("PDF contains no extractable text")
    return readable_pages


def extract_html_sections(content: bytes, max_section_chars: int = 12_000) -> list[ExtractedPage]:
    """Extract visible EDGAR filing text into bounded, page-less sections."""
    if not content:
        raise DocumentExtractionError("HTML content is empty")
    try:
        parser = _VisibleTextParser()
        parser.feed(content.decode("utf-8", errors="replace"))
        parser.close()
    except Exception as exc:
        raise DocumentExtractionError("HTML text extraction failed") from exc

    lines = [re.sub(r"\s+", " ", line).strip() for line in "".join(parser.parts).splitlines()]
    lines = [line for line in lines if line]
    sections: list[str] = []
    current: list[str] = []
    current_size = 0
    for line in lines:
        for start in range(0, len(line), max_section_chars):
            part = line[start : start + max_section_chars]
            added_size = len(part) + (1 if current else 0)
            if current and current_size + added_size > max_section_chars:
                sections.append("\n".join(current))
                current = []
                current_size = 0
            current.append(part)
            current_size += len(part) + (1 if len(current) > 1 else 0)
    if current:
        sections.append("\n".join(current))
    if not sections:
        raise DocumentExtractionError("HTML filing contains no extractable text")
    return [ExtractedPage(page_number=None, content=section) for section in sections]
