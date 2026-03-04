# AGENTS.md

## Cursor Cloud specific instructions

### Overview

MintAgent is a two-service app: a Next.js 15 frontend (port 3000) and a FastAPI backend (port 8000). All external services (Supabase, Pinecone, OpenAI) are hosted SaaS — no Docker required.

### Starting services

**Backend** (from repo root):
```bash
source backend/venv/bin/activate && cd backend && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Frontend** (from repo root):
```bash
npm run dev
```

Health check: `curl http://127.0.0.1:8000/healthz` should return `{"ok":true}`.

### Lint / Build / Test

See `CLAUDE.md` for full command reference. Quick summary:
- Lint: `npm run lint`
- Build: `npm run build`
- No automated test suite exists in the repo.

### Non-obvious gotchas

- **`npm install` requires `--legacy-peer-deps`**: `react-day-picker@8.10.1` has a peer dep on React 16-18, but the project uses React 19. Without this flag, npm will fail with `ERESOLVE`.
- **Empty env vars crash the backend**: The Pydantic `Settings` in `backend/app/config.py` validates URL and integer fields. If `.env.local` sets them to empty strings (e.g. `FIRECRAWL_BASE_URL=`), the backend fails on startup with a `ValidationError`. Comment out any optional env var you don't have a value for, rather than leaving it as an empty `KEY=`.
- **Python venv location**: The backend expects a venv at `backend/venv/`. Always activate it before running uvicorn or backend scripts.
- **Dual lockfiles**: Both `package-lock.json` and `pnpm-lock.yaml` exist at root. Use `npm` (matches the `scripts` in `package.json`).
