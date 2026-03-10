# AGENTS.md

Operational guide for humans and coding agents working in this repository.

## Purpose

MintAgent is a production RAG platform that ingests client content (web + Google Drive), stores source-of-truth content in Supabase, indexes chunks in Pinecone, and serves grounded chat responses through a Next.js + FastAPI stack.

Use this file as the default collaboration contract when making changes.

## 5-Agent Team Model

For architecture, system design, and multi-component work, always evaluate the change through all five lenses below before finalizing.

### 1) Architect
- Define boundaries first (frontend, API routes, ingestion services, storage, vector index).
- Confirm data contracts and ownership before coding.
- Avoid tight coupling across ingestion, retrieval, and UI layers.

### 2) Backend Engineer
- Design route/service interfaces before implementation.
- Keep ingestion and retrieval paths deterministic and observable.
- Validate auth, retries, and error surfaces (especially third-party APIs).

### 3) Frontend Engineer
- Favor clear UX, loading/error states, and minimal client state.
- Keep API integration explicit (`/api/mintagent/*` proxy routes).
- Protect against regressions in chat, indexes list, and client creation flows.

### 4) QA / Testing Engineer
- Name failure modes first.
- Add/adjust tests for logic and integration points touched.
- Validate both happy path and degraded behavior.

### 5) DevOps / Infrastructure
- Ensure deployability, env-driven config, and health checks.
- Preserve structured logging and traceability for ingestion and chat.
- Prevent secret leakage and production-only assumptions in local code.

## Operating Protocol

1. **New architecture / multi-component feature**: run all 5 perspectives.
2. **Significant change**: check at least 3 relevant perspectives.
3. **Code review order**: QA first, then Architect validates contracts.
4. **Conflict handling**:
   - Architect breaks design ties.
   - Backend/Frontend break implementation ties in their domains.

## System Boundaries and Core Contracts

### Primary Components
- **Frontend**: Next.js App Router (`app/`)
- **Backend**: FastAPI (`backend/app/`)
- **Storage + relational data**: Supabase Storage + Postgres
- **Vector retrieval**: Pinecone
- **LLM layer**: OpenAI-based embeddings/chat

### Client Isolation Contract
- `client_slug` is the stable tenant key.
- Supabase folder: `client-data-sources/{client-slug}/...`
- Pinecone namespace: `{client-slug}` (or `{client-slug}-semantic` for A/B)
- Postgres rows are keyed/filterable by `client_slug`.

### Important Data Contracts
- Storage documents are markdown with frontmatter metadata.
- `public.clients` tracks client-level metadata.
- `public.documents` tracks document lifecycle and ingestion status.
- `content_hash` is used for change detection consistency.

## High-Signal Repository Map

### Frontend
- `app/page.tsx` - create client knowledge base
- `app/indexes/page.tsx` - list/manage client indexes
- `app/dashboard/page.tsx` - RAG chat UI
- `app/api/mintagent/*` - frontend proxy routes

### Backend
- `backend/app/routes/create.py` - ingestion orchestration
- `backend/app/routes/chat.py` - RAG chat endpoint
- `backend/app/routes/indexes.py` - list/delete index namespaces
- `backend/app/routes/resources.py` - resource metadata endpoints
- `backend/app/services/drive_ingest.py` - Drive ingestion
- `backend/app/clients/pinecone_client.py` - chunking + vector upsert/search
- `backend/app/clients/supabase_storage_client.py` - storage operations
- `backend/app/clients/supabase_agents_db_client.py` - DB operations

## Local Development Commands

### Start services
```bash
# backend
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# frontend (repo root, separate terminal)
npm run dev
```

### Health and debug
```bash
curl http://127.0.0.1:8000/healthz
curl http://127.0.0.1:8000/api/mintagent/debug
```

### Frontend checks
```bash
npm run lint
npm run build
```

## Change Workflow for Agents

1. Read relevant docs/routes first; do not guess contracts.
2. Define the contract change (inputs, outputs, side effects).
3. Implement smallest safe change.
4. Run validation (lint/build/tests or targeted script checks).
5. Summarize:
   - what changed
   - why it changed
   - how it was validated
   - residual risks

## QA Expectations (Minimum)

For each non-trivial change, explicitly evaluate at least 3 failure modes:
- third-party API failure/timeouts (Firecrawl, OpenAI, Pinecone, Supabase)
- malformed or missing metadata / slug mismatch
- partial pipeline success (stored but not embedded, embedded with stale hash)

Also confirm:
- clear error handling path
- no silent data loss
- no cross-client data leakage

## DevOps and Security Guardrails

- Never hardcode secrets; use env vars from `.env*`.
- Preserve health checks and useful logs around ingestion/retrieval.
- Prefer idempotent operations for scripts and ingestion retries.
- Be explicit when a change requires new environment variables or infra updates.

## Existing Runtime Agent Workflows (Product Features)

The application also includes runtime "assistant" workflows (distinct from the 5-agent engineering model):
- Draft agent -> QA agent -> Finalize agent (`backend/scripts/3_AGENT_SYSTEM.md`)
- Query optimizer and result formatter prompts under `.claude/agents/`

When modifying these flows, verify prompt/schema compatibility and endpoint contracts.

## Reference Docs

- `README.md`
- `CLAUDE.md`
- `docs/WORKFLOW_UI_TO_CLIENT_ASSISTANT.md`
- `docs/BACKEND_API_REFERENCE.md`
- `docs/LOCAL_DEVELOPMENT.md`
- `README_CHUNKING_AB_TEST.md`
