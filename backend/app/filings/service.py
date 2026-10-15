from dataclasses import replace
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import FinancialDocument
from app.filings.chunking import SemanticFinancialChunker
from app.filings.embedding import FastEmbedEmbeddings
from app.filings.extraction import extract_html_sections, extract_pdf_pages
from app.filings.models import DocumentMetadata, IngestionResult, RetrievedChunk
from app.filings.repository import (
    persist_chunks_for_document,
    persist_document,
    retrieve_chunks,
)


class FilingIngestionService:
    def __init__(self, embeddings: FastEmbedEmbeddings | None = None) -> None:
        self.embeddings = embeddings or FastEmbedEmbeddings()
        self.chunker = SemanticFinancialChunker(self.embeddings)

    def ingest_pdf(
        self,
        session: Session,
        metadata: DocumentMetadata,
        content: bytes,
    ) -> IngestionResult:
        pages = extract_pdf_pages(content)
        chunks = self.chunker.chunk_and_embed(pages)
        document_id = persist_document(session, metadata, chunks, content)
        return IngestionResult(
            document_id=document_id,
            page_count=len(pages),
            chunk_count=len(chunks),
        )

    def process_existing_document(
        self,
        session: Session,
        document: FinancialDocument,
        content: bytes,
    ) -> IngestionResult:
        if document.mime_type == "application/pdf":
            pages = extract_pdf_pages(content)
        elif document.mime_type in {"text/html", "application/xhtml+xml"}:
            pages = extract_html_sections(content)
        else:
            raise ValueError(f"Unsupported filing MIME type: {document.mime_type or 'unknown'}")
        chunks = self.chunker.chunk_and_embed(pages)
        persist_chunks_for_document(
            session,
            document,
            chunks,
            content,
            page_count=len(pages),
        )
        return IngestionResult(
            document_id=document.id,
            page_count=len(pages),
            chunk_count=len(chunks),
        )


class FilingRetrievalService:
    def __init__(self, embeddings: FastEmbedEmbeddings | None = None) -> None:
        self.embeddings = embeddings or FastEmbedEmbeddings()

    def search(
        self,
        session: Session,
        company_id: UUID,
        query: str,
        limit: int = 5,
        minimum_similarity: float = 0.35,
    ) -> list[RetrievedChunk]:
        query_embedding = self.embeddings.embed_query(query)
        rows = retrieve_chunks(session, company_id, query_embedding, limit)
        return [
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=document.id,
                document_title=document.title,
                content=chunk.content,
                source_name=document.source_name,
                source_url=document.source_url,
                page_number=chunk.page_number,
                published_at=document.published_at,
                similarity=similarity,
                is_synthetic=document.is_synthetic,
                retrieval_score=similarity,
            )
            for chunk, document, similarity in rows
            if similarity >= minimum_similarity
        ]

    def search_many(
        self,
        session: Session,
        company_id: UUID,
        queries: list[str],
        per_query_limit: int = 4,
        final_limit: int = 6,
        minimum_similarity: float = 0.35,
    ) -> list[RetrievedChunk]:
        matches: dict[UUID, RetrievedChunk] = {}
        hit_counts: dict[UUID, int] = {}
        for query in queries:
            for chunk in self.search(
                session,
                company_id,
                query,
                per_query_limit,
                minimum_similarity,
            ):
                hit_counts[chunk.chunk_id] = hit_counts.get(chunk.chunk_id, 0) + 1
                current = matches.get(chunk.chunk_id)
                if current is None or chunk.similarity > current.similarity:
                    matches[chunk.chunk_id] = chunk

        if not matches:
            return []
        newest_date = max(
            (chunk.published_at for chunk in matches.values() if chunk.published_at),
            default=None,
        )
        reranked = [
            replace(
                chunk,
                matched_queries=hit_counts[chunk.chunk_id],
                retrieval_score=(
                    chunk.similarity
                    + min(0.08, 0.02 * (hit_counts[chunk.chunk_id] - 1))
                    + (0.03 if newest_date and chunk.published_at == newest_date else 0)
                ),
            )
            for chunk in matches.values()
        ]
        return sorted(
            reranked,
            key=lambda item: (item.retrieval_score, item.published_at or date.min),
            reverse=True,
        )[: min(max(final_limit, 1), 20)]
