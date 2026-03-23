# AGENTS.md

Guidance for autonomous coding agents working in this repository.

## 1) Project Snapshot

MintAgent is a production Retrieval-Augmented Generation (RAG) system:

- Frontend: Next.js 15 (TypeScript, React 19, App Router)
- Backend: FastAPI (Python 3.10+)
- Storage + relational data: Supabase (Storage + Postgres)
- Vector search: Pinecone
- Ingestion sources: Websites (Firecrawl) + Google Drive
- LLM usage: OpenAI (embeddings + chat)

Primary goal: create isolated, per-client knowledge bases and serve grounded chat responses with citations.

---

## 2) High-Level Architecture (System Boundaries)

```text
User UI (Next.js)
  -> Next.js API proxies (/api/mintagent/*)
  -> FastAPI backend routes (backend/app/routes/*)
  -> Ingestion + enrichment pipeline
  -> Supabase Storage + Postgres tracking
  -> Chunking + embedding
  -> Pinecone upsert/query by client namespace
  -> RAG chat response
```

### Isolation Contract (must not be broken)

`client_slug` is the isolation key and must stay consistent across:

- Supabase Storage path: `client-data-sources/{client-slug}/...`
- Postgres rows in `public.clients` and `public.documents`
- Pinecone namespace: `{client-slug}` (or `{client-slug}-semantic` for A/B)

---

## 3) Repository Map

### Frontend

- `app/page.tsx` - create client/index form
- `app/indexes/page.tsx` - list client knowledge bases
- `app/dashboard/page.tsx` - chat UI
- `app/api/mintagent/*` - proxy routes to backend

### Backend

- `backend/app/routes/create.py` - end-to-end ingestion orchestration
- `backend/app/routes/chat.py` - RAG query endpoint
- `backend/app/routes/indexes.py` - list/delete indexes
- `backend/app/routes/resources.py` - resource links/metadata
- `backend/app/routes/stats.py` - client stats
- `backend/app/clients/firecrawl.py` - website scrape client
- `backend/app/clients/supabase_storage_client.py` - storage operations
- `backend/app/clients/supabase_agents_db_client.py` - DB operations
- `backend/app/clients/pinecone_client.py` - vector upsert/search + chunking
- `backend/app/services/drive_ingest.py` - Google Drive ingestion
- `backend/app/config.py` - environment + settings loading

### Scripts

- `backend/scripts/ingest_to_supabase.py`
- `backend/scripts/upsert_to_pinecone.py`
- `backend/scripts/create_assistants_for_kb_namespaces.py`
- `backend/scripts/bulk_client_onboarding.py`

---

## 4) Local Development

### Install

```bash
# frontend
npm install

# backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Run

```bash
# terminal 1 (backend)
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# terminal 2 (frontend, from repo root)
npm run dev
```

### Useful checks

```bash
npm run lint
npm run build
curl http://127.0.0.1:8000/healthz
curl http://127.0.0.1:8000/api/mintagent/debug
python backend/scripts/verify_supabase_creds.py
```

---

## 5) Environment Variables

Copy `env.example` to `.env.local` (or `backend/.env.local`) and set:

- `FIRECRAWL_API_KEY`
- `OPENAI_API_KEY`
- `SUPABASE_AGENT_URL`
- `SUPABASE_AGENT_KEY` (service role key, not anon key)
- `PINECONE_API_KEY`
- `PINECONE_KB_INDEX` (default: `sb-knowledge-bases`)

Optional:

- `PINECONE_KB_SEMANTIC_INDEX`
- `ANTHROPIC_API_KEY`, `GROQ_API_KEY`
- Bison-related variables

Config loading order is defined in `backend/app/config.py`.

---

## 6) Core Data Contracts

### Supabase Storage

```text
client-data-sources/
  {client-slug}/
    website/*.md
    drive/*.md
    intake_form/*.md
    metadata.json
```

### Postgres tables

- `public.clients` (one row per client)
- `public.documents` (one row per ingested document, status-tracked)

Document status values include:

- `ingested`
- `embedded`
- `error - ingest`
- `error - embed`

### Pinecone

- Canonical index: `sb-knowledge-bases`
- Namespace per client: `{client-slug}`
- Semantic A/B namespace: `{client-slug}-semantic`

Chunking strategies:

- Character-based default: `char:1200:200`
- Semantic markdown: `md_semantic_v1:w350:m550:o80`

---

## 7) 5-Agent Working Model (Required for significant design changes)

For any architecture or multi-component feature, reason through these lenses before coding:

1. **Architect**: boundaries, contracts, coupling risk
2. **Backend**: route/service/schema impacts, error handling, idempotency
3. **Frontend**: UX state transitions, loading/error/empty states
4. **QA**: failure modes, test coverage, regression surface
5. **DevOps**: deployability, observability, env/config, security

If tradeoffs conflict: Architecture contract wins first, then implementation details.

---

## 8) QA Baseline: Minimum Failure Modes to Consider

When touching ingestion, retrieval, or chat, explicitly check at least these:

1. Namespace mismatch (data from wrong client leaks into retrieval)
2. Partial ingestion success (storage write succeeds, vector upsert fails)
3. Empty or low-quality retrieval (LLM hallucinates without context)
4. Chunking drift (mixed old/new chunker output in same namespace)
5. Missing credentials or invalid service role key

Prefer adding/adjusting tests for changed behavior.

---

## 9) Operational Guardrails

- Never commit secrets or service keys.
- Avoid changing public API contracts unless both frontend and backend are updated together.
- Keep `client_slug` handling deterministic and normalized (lowercase, hyphenated).
- Preserve backward compatibility for existing storage paths and metadata fields.
- Do not treat generated output directories (for example `.next/`) as source-of-truth for code changes.

---

## 10) Change Workflow for Agents

1. Understand impacted boundaries first (UI/API/storage/vector).
2. Make the smallest coherent change.
3. Run targeted validation commands.
4. Summarize what changed, why, and how it was verified.
5. If schema or infra changes are introduced, document rollout and rollback notes.

---

## 11) Reference Docs

- `README.md`
- `README_CHUNKING_AB_TEST.md`
- `docs/BACKEND_API_REFERENCE.md`
- `docs/WORKFLOW_UI_TO_CLIENT_ASSISTANT.md`
- `docs/LOCAL_DEVELOPMENT.md`
- `CLAUDE.md`
