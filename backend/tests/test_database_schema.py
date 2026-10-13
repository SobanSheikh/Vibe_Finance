from pgvector.sqlalchemy import VECTOR

from app.config import sqlalchemy_database_url
from app.db import Base, models

EXPECTED_TABLES = {
    "companies",
    "market_prices",
    "investor_profiles",
    "holdings",
    "watchlist_items",
    "financial_documents",
    "document_chunks",
    "analysis_sessions",
    "agent_runs",
    "recommendations",
    "citations",
}

def test_all_expected_tables_are_registered() -> None:
    assert models.Company.__tablename__ == "companies"
    assert EXPECTED_TABLES == set(Base.metadata.tables)


def test_document_embedding_has_expected_dimensions() -> None:
    embedding_type = Base.metadata.tables["document_chunks"].c.embedding.type

    assert isinstance(embedding_type, VECTOR)
    assert embedding_type.dim == 384


def test_database_url_is_normalized_for_psycopg() -> None:
    assert sqlalchemy_database_url("postgres://user:pass@host/db") == (
        "postgresql+psycopg://user:pass@host/db"
    )
    assert sqlalchemy_database_url("postgresql://user:pass@host/db") == (
        "postgresql+psycopg://user:pass@host/db"
    )
