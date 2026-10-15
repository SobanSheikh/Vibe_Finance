# VibeFinance architecture

VibeFinance turns market observations, company filings, and an investor's stored
portfolio into evidence-backed decision support. Numerical facts are calculated
deterministically; an LLM may interpret retrieved text and synthesize an
explanation, but it cannot replace calculated values or introduce uncited filing
claims.

## End-to-end flow

1. React selects a company and investor profile from FastAPI.
2. Market prices are fetched from Yahoo Finance. Official US filings are synced
   from SEC EDGAR or uploaded manually.
3. Filing text is semantically chunked, embedded with
   `BAAI/bge-small-en-v1.5`, and stored in Supabase PostgreSQL with pgvector.
4. LangGraph starts three specialists in parallel:
   - Market Signal Agent calculates momentum, volume anomaly, and volatility.
   - Filing Research Agent invokes the company-scoped retrieval tool and returns
     only evidence-linked findings.
   - Portfolio Risk Agent calculates position and sector exposure against the
     selected profile's limits.
5. Validation checks evidence identifiers. Conflict detection compares agent
   directions, and the synthesis node creates one personalized recommendation.
6. FastAPI returns confidence, reasoning, warnings, citations, conflicts, and
   metrics. The complete session, agent runs, recommendation, and document
   citations are persisted in PostgreSQL.

```text
React -> FastAPI -> LangGraph
                    |-- Market Agent -----|
                    |-- Filing Agent -----|-> validation -> conflicts -> synthesis
                    |-- Portfolio Agent --|
                                      -> metrics -> PostgreSQL -> React
```

## Reliability and safety

- Analysis and filing sync endpoints return background-job identifiers and are
  polled with bounded backoff.
- Missing market, filing, or portfolio data produces a degraded agent result,
  not fabricated evidence.
- Unsupported LLM output falls back to deterministic interpretation.
- Conflicts and missing agents reduce synthesis confidence.
- SEC access uses an identifying User-Agent and bounded, deduplicated downloads.
- Database, storage, and LLM secrets remain behind FastAPI.
- Recommendations are research support, not financial advice.

## Data ownership

Live market observations are fetched for an analysis. SEC HTML and uploaded PDFs,
document chunks, embeddings, profiles, holdings, watchlists, and completed
analysis records are persisted. Source URLs and synthetic-data flags remain
attached to evidence shown to the user.
