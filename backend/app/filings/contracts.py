from datetime import date
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IngestionStatus(StrEnum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FilingIngestionRequest(StrictModel):
    company_id: UUID
    title: str = Field(min_length=1, max_length=500)
    document_type: str = Field(min_length=1, max_length=80)
    source_url: HttpUrl
    source_name: str = Field(min_length=1, max_length=150)
    reporting_period: str | None = Field(default=None, max_length=80)
    published_at: date | None = None


class FilingIngestionAccepted(StrictModel):
    job_id: UUID
    status: IngestionStatus


class FilingIngestionJob(StrictModel):
    job_id: UUID
    status: IngestionStatus
    document_id: UUID | None = None
    page_count: int | None = Field(default=None, ge=0)
    chunk_count: int | None = Field(default=None, ge=0)
    error: str | None = None


class FilingSearchInput(StrictModel):
    company_id: UUID
    queries: list[Annotated[str, Field(min_length=10, max_length=500)]] = Field(
        min_length=1,
        max_length=5,
    )
    limit: int = Field(default=6, ge=1, le=10)


class FilingSearchItem(StrictModel):
    chunk_id: UUID
    document_id: UUID
    document_title: str
    content: str
    source_name: str
    source_url: str
    page_number: int | None
    published_at: date | None
    similarity: float = Field(ge=-1, le=1)
    retrieval_score: float
    matched_queries: int = Field(ge=1, le=5)
    is_synthetic: bool


class FilingSearchResult(StrictModel):
    status: Literal["completed", "no_evidence", "unavailable"]
    items: list[FilingSearchItem] = Field(default_factory=list)
    error: str | None = None
