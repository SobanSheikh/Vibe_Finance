from langchain_core.tools import BaseTool, tool
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.filings.contracts import FilingSearchInput, FilingSearchItem, FilingSearchResult
from app.filings.service import FilingRetrievalService


def build_filing_retrieval_tool(
    session_factory: sessionmaker[Session],
    retrieval: FilingRetrievalService | None = None,
) -> BaseTool:
    retrieval_service = retrieval or FilingRetrievalService()

    @tool("search_company_filings", args_schema=FilingSearchInput)
    def search_company_filings(
        company_id: str,
        queries: list[str],
        limit: int = 6,
    ) -> dict[str, object]:
        """Search one company's indexed filings for cited financial evidence.

        Use focused financial queries. Results are company-scoped, deduplicated,
        reranked excerpts with document and page-level citation metadata. This
        tool never searches the open web and never accepts arbitrary SQL.
        """
        request = FilingSearchInput(
            company_id=company_id,
            queries=queries,
            limit=limit,
        )
        try:
            with session_factory() as session:
                session.connection()
                chunks = retrieval_service.search_many(
                    session,
                    request.company_id,
                    request.queries,
                    final_limit=request.limit,
                )
        except SQLAlchemyError:
            return FilingSearchResult(
                status="unavailable",
                error="The filing evidence store is temporarily unavailable.",
            ).model_dump(mode="json")
        except Exception:
            return FilingSearchResult(
                status="unavailable",
                error="The filing search could not generate or compare embeddings.",
            ).model_dump(mode="json")

        if not chunks:
            return FilingSearchResult(status="no_evidence").model_dump(mode="json")
        return FilingSearchResult(
            status="completed",
            items=[
                FilingSearchItem(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    document_title=chunk.document_title,
                    content=chunk.content,
                    source_name=chunk.source_name,
                    source_url=chunk.source_url,
                    page_number=chunk.page_number,
                    published_at=chunk.published_at,
                    similarity=chunk.similarity,
                    retrieval_score=chunk.retrieval_score,
                    matched_queries=chunk.matched_queries,
                    is_synthetic=chunk.is_synthetic,
                )
                for chunk in chunks
            ],
        ).model_dump(mode="json")

    return search_company_filings
