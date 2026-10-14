from dataclasses import dataclass, field
from datetime import date
from uuid import UUID


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    content: str


@dataclass(frozen=True)
class EmbeddedChunk:
    chunk_index: int
    content: str
    page_number: int
    embedding: list[float]
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentMetadata:
    company_id: UUID
    title: str
    document_type: str
    source_url: str
    source_name: str
    reporting_period: str | None = None
    published_at: date | None = None
    is_synthetic: bool = False


@dataclass(frozen=True)
class IngestionResult:
    document_id: UUID
    page_count: int
    chunk_count: int


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: UUID
    document_id: UUID
    document_title: str
    content: str
    source_name: str
    source_url: str
    page_number: int | None
    published_at: date | None
    similarity: float
    is_synthetic: bool
    matched_queries: int = 1
    retrieval_score: float = 0
