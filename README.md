# VibeFinance

VibeFinance is an evidence-first, personalized financial-intelligence platform for
retail investors. It combines market signals, cited financial documents, and
portfolio risk through a multi-agent workflow.

## Repository structure

- `frontend/` — React, TypeScript, and Vite dashboard
- `backend/` — FastAPI application and agent orchestration
- `supabase/` — versioned PostgreSQL and pgvector migrations
- `docs/` — [architecture](docs/architecture.md) and [evaluation](docs/evaluation.md)

## Local development

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`; interactive documentation is at
`http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The dashboard is available at `http://localhost:5173`.

### Supabase CLI

The CLI is installed as a pinned root development dependency:

```bash
npm install
npm run supabase -- --version
```

Run other commands with `npm run supabase -- <command>` or `npx supabase <command>`.

## Required backend configuration

Copy `backend/.env.example` to `backend/.env`, configure PostgreSQL and private
Supabase credentials, and set `SEC_USER_AGENT` to the application name plus a
real contact email. Apply migrations with `npx supabase db push` before starting
FastAPI.

See the architecture and evaluation documents before running the judging demo.

## Deployment

The deployment-ready configuration uses Vercel for the frontend, a Dockerized
Render service for FastAPI and local embedding inference, and Supabase for
PostgreSQL, pgvector, and private filing storage.

See [deployment instructions](docs/deployment.md) for environment variables,
model hosting, and the production smoke-test checklist.
