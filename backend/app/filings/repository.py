from hashlib import sha256
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DocumentChunk, FinancialDocument
from app.filings.models import DocumentMetadata, EmbeddedChunk


def persist_document(
    session: Session,
    metadata: DocumentMetadata,
    chunks: list[EmbeddedChunk],
    original_content: bytes,
) -> UUID:
    if not chunks:
        raise ValueError("At least one document chunk is required")
    checksum = sha256(original_content).hexdigest()
    existing = session.scalar(
        select(FinancialDocument).where(FinancialDocument.checksum == checksum)
    )
    if existing:
        return existing.id

    document = FinancialDocument(
        company_id=metadata.company_id,
        title=metadata.title,
        document_type=metadata.document_type,
        reporting_period=metadata.reporting_period,
        source_url=metadata.source_url,
        source_name=metadata.source_name,
        published_at=metadata.published_at,
        is_synthetic=metadata.is_synthetic,
        checksum=checksum,
    )
    session.add(document)
    session.flush()
    session.add_all(
        [
            DocumentChunk(
                document_id=document.id,
                company_id=metadata.company_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                page_number=chunk.page_number,
                token_count=None,
                chunk_metadata=chunk.metadata,
                embedding=chunk.embedding,
            )
            for chunk in chunks
        ]
    )
    session.commit()
    return document.id


def retrieve_chunks(
    session: Session,
    company_id: UUID,
    query_embedding: list[float],
    limit: int = 5,
) -> list[tuple[DocumentChunk, FinancialDocument, float]]:
    if len(query_embedding) != 384:
        raise ValueError("Query embedding must contain 384 dimensions")
    distance = DocumentChunk.embedding.cosine_distance(query_embedding)
    statement = (
        select(DocumentChunk, FinancialDocument, (1 - distance).label("similarity"))
        .join(FinancialDocument, FinancialDocument.id == DocumentChunk.document_id)
        .where(DocumentChunk.company_id == company_id)
        .order_by(distance)
        .limit(min(max(limit, 1), 20))
    )
    return [
        (chunk, document, float(similarity))
        for chunk, document, similarity in session.execute(statement)
    ]
