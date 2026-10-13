# VibeFinance

VibeFinance is an evidence-first, personalized financial-intelligence platform for
retail investors. It combines market signals, cited financial documents, and
portfolio risk through a multi-agent workflow.

## Repository structure

- `frontend/` — React, TypeScript, and Vite dashboard
- `backend/` — FastAPI application and agent orchestration
- `supabase/` — database migrations (added with the data layer)
- `docs/` — architecture, evaluation, and demo documentation

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
