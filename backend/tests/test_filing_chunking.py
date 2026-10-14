from langchain_core.embeddings import Embeddings

from app.filings.chunking import SemanticFinancialChunker
from app.filings.models import ExtractedPage


class DeterministicEmbeddings(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)

    @staticmethod
    def _vector(text: str) -> list[float]:
        seed = sum(ord(character) for character in text) % 31
        return [float((seed + index) % 7) / 7 for index in range(384)]


def test_semantic_chunks_preserve_page_attribution_and_vector_size() -> None:
    pages = [
        ExtractedPage(
            page_number=7,
            content=(
                "Revenue grew during the reporting period. Operating margins remained stable. "
                "Consumer demand supported the retail segment. Borrowings increased during the "
                "year. Finance costs rose because of higher interest rates. Management expects "
                "capital expenditure to remain elevated."
            ),
        )
    ]

    chunks = SemanticFinancialChunker(DeterministicEmbeddings()).chunk_and_embed(pages)

    assert chunks
    assert all(chunk.page_number == 7 for chunk in chunks)
    assert all(len(chunk.embedding) == 384 for chunk in chunks)
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))


def test_chunker_rejects_wrong_embedding_dimensions() -> None:
    class WrongDimensions(DeterministicEmbeddings):
        @staticmethod
        def _vector(text: str) -> list[float]:
            return [0.0] * 10

    chunker = SemanticFinancialChunker(WrongDimensions())

    try:
        chunker.chunk_and_embed([ExtractedPage(1, "One sentence. A second sentence.")])
    except ValueError as exc:
        assert "384-dimensional" in str(exc)
    else:
        raise AssertionError("Expected dimension validation to fail")
