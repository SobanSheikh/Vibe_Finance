from io import BytesIO

from pypdf import PdfReader

from app.filings.models import ExtractedPage


class DocumentExtractionError(ValueError):
    pass


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
