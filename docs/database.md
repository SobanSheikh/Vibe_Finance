# Database architecture

VibeFinance uses Supabase PostgreSQL for relational application data and
`pgvector` for financial-document retrieval.

## Security boundary

React never receives database credentials or a server key. FastAPI is the
trusted boundary and connects with `DATABASE_URL`. If the Supabase Data API is
used, its service-role key remains in the backend environment only.

Every application table has Row Level Security enabled without permissive
public policies. User policies will be added when authentication is built.

## Retrieval

Financial documents are divided into chunks with source metadata and
384-dimensional embeddings. `match_document_chunks` performs company-scoped
cosine search and caps retrieval at 20 results, preventing cross-company
evidence leakage.

## Applying the migration

Review `supabase/migrations/001_initial_schema.sql`, then apply it through the
Supabase SQL Editor or a linked Supabase CLI project. Applying it is a remote
database change and is deliberately separate from repository setup.
