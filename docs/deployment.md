# Deployment

The production layout uses three services:

| Component | Host | Responsibility |
| --- | --- | --- |
| React/Vite frontend | Vercel | Static dashboard |
| FastAPI backend | Render Docker web service | API, agents, ingestion, and embedding inference |
| PostgreSQL, pgvector, and file storage | Supabase | Durable application data, vectors, and source filings |

## Embedding model

`BAAI/bge-small-en-v1.5` runs locally inside the FastAPI container through
FastEmbed and ONNX Runtime. The Docker build downloads it into
`/opt/fastembed-cache`, so production requests do not download a model. The
model produces the 384-dimensional vectors expected by the existing Supabase
schema.

Use a backend instance with at least 1 GB of memory. Keep one application worker
for the hackathon deployment because analysis, upload, and SEC synchronization
job progress is currently maintained in process while durable results are stored
in PostgreSQL.

## 1. Prepare Supabase

Apply all migrations from the repository:

```bash
npx supabase link --project-ref YOUR_PROJECT_REF
npx supabase db push
```

Confirm that the private `financial-filings` bucket exists and that the seed
companies are available.

Use the Supabase pooler connection string for `DATABASE_URL`. Keep the server-only
secret key in the backend host; never expose it through a `VITE_` variable.

## 2. Deploy the backend to Render

Create a Render Blueprint from the repository-level `render.yaml`. Render builds
`backend/Dockerfile` and prompts for every secret marked `sync: false`.

Set these values:

- `FRONTEND_URL`: the final Vercel origin, without a trailing slash.
- `DATABASE_URL`: Supabase PostgreSQL pooler URL.
- `SUPABASE_URL`: Supabase project URL.
- `SUPABASE_SECRET_KEY`: server-only secret or legacy service-role key.
- `SEC_USER_AGENT`: application name followed by a real contact email.
- `LLM_API_KEY`: Anthropic API key for the configured Claude preset.

The container starts on Render's `PORT` and exposes `/api/health` for health
checks. Do not add multiple Uvicorn workers until job state has been moved to a
shared queue such as Redis.

After deployment, verify:

```bash
curl https://YOUR-RENDER-SERVICE.onrender.com/api/health
curl https://YOUR-RENDER-SERVICE.onrender.com/api/companies
```

## 3. Deploy the frontend to Vercel

Import the same repository as a separate Vercel project and set its Root
Directory to `frontend`. Vercel will use `frontend/vercel.json`.

Add this build-time environment variable:

```text
VITE_API_URL=https://YOUR-RENDER-SERVICE.onrender.com
```

Deploy the frontend, then update the Render `FRONTEND_URL` value to the final
Vercel origin and redeploy the backend so CORS accepts the production site.

## 4. Production smoke test

1. Load companies and investor profiles.
2. Create a new investor and add one holding.
3. Open an indexed filing and download its stored source.
4. Run intelligence and observe all three agent progress states.
5. Confirm that source citations open and that the completed session appears in Research.
6. Run the same company for two profiles in Evaluation and confirm different personalized outcomes.

## Current deployment constraint

FastAPI background tasks are appropriate for the hackathon demo, but they are
not a durable distributed queue. A container restart can interrupt an active
analysis or filing job. Completed analyses, documents, vectors, portfolios, and
filing files remain durable in Supabase.
