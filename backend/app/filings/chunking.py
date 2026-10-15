from langchain_core.embeddings import Embeddings
from langchain_experimental.text_splitter import SemanticChunker

from app.filings.models import EmbeddedChunk, ExtractedPage


class SemanticFinancialChunker:
    def __init__(self, embeddings: Embeddings) -> None:
        self._embeddings = embeddings
        self._splitter = SemanticChunker(
            embeddings,
            breakpoint_threshold_type="percentile",
            breakpoint_threshold_amount=90,
            min_chunk_size=180,
        )

    def chunk_and_embed(self, pages: list[ExtractedPage]) -> list[EmbeddedChunk]:
        chunk_inputs: list[tuple[int | None, str]] = []
        for page in pages:
            chunks = self._splitter.split_text(page.content)
            chunk_inputs.extend(
                (page.page_number, chunk.strip()) for chunk in chunks if chunk.strip()
            )

        if not chunk_inputs:
            return []
        vectors = self._embeddings.embed_documents([content for _, content in chunk_inputs])
        if len(vectors) != len(chunk_inputs):
            raise ValueError("Embedding provider returned an unexpected vector count")

        embedded: list[EmbeddedChunk] = []
        for index, ((page_number, content), vector) in enumerate(zip(chunk_inputs, vectors)):
            if len(vector) != 384:
                raise ValueError(f"Expected a 384-dimensional embedding, received {len(vector)}")
            embedded.append(
                EmbeddedChunk(
                    chunk_index=index,
                    content=content,
                    page_number=page_number,
                    embedding=vector,
                    metadata={"chunking_strategy": "semantic_percentile_90"},
                )
            )
        return embedded
