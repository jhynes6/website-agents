# Backend API Reference (FastAPI)

This document describes the **MintAgent Python Backend** HTTP API as implemented in `backend/app/routes/*`.

## Base URL + routing

- **Local dev base URL**: `http://127.0.0.1:8000`
- **FastAPI app**: `backend/app/main.py`
- **API prefix for all MintAgent endpoints**: `/api/mintagent`
- **Health check**: `GET /healthz` (no prefix)

### Conventions

- **Client identifier**: `clientSlug` (preferred) or `client_slug` (Python-style). Some endpoints also accept `namespace` for back-compat.
- **Indexes/namespaces**: in the current Pinecone-backed architecture, the **namespace == client slug**.
- **Content filtering**: metadata filters are expressed via request fields like `contentType`, `documentSource`, `keywords`.

---

## `GET /healthz`

Simple liveness probe.

### Response (200)

```json
{ "ok": true }
```

Source: `backend/app/main.py`.

---

## `GET /api/mintagent/debug`

Returns minimal backend configuration visibility (safe booleans only).

### Response (200)

```json
{
  "firecrawl_base_url": "https://api.firecrawl.dev",
  "ai": {
    "openai_configured": true,
    "anthropic_configured": false,
    "groq_configured": false
  }
}
```

Source: `backend/app/routes/debug.py`.

---

## `POST /api/mintagent/create` (Onboarding / ingestion)

Creates or refreshes a client knowledge base by:

- Crawling a website via Firecrawl (2-phase crawl: **main** + **blog**),
- Optionally ingesting a Google Drive folder,
- Normalizing documents,
- Extracting per-document `keywords` (LLM),
- Uploading raw artifacts to storage (Supabase Storage),
- Upserting vectors into Pinecone,
- Optionally creating a Pinecone Assistant,
- Writing UI metadata files for index listing:
  - `supabase_storage_metadata.json`
  - `pinecone_namespace_metadata.json` (preferred for display)

### Request body

```json
{
  "clientSlug": "acme-co",
  "url": "https://acme.co",
  "clientDriveFolder": "https://drive.google.com/drive/folders/....",
  "limit": 500,
  "maxDepth": 3,
  "includePaths": ["pricing", "services"],
  "excludePaths": ["privacy", "terms"],
  "blogLimit": 50,
  "skipMarkdownClean": false,
  "skipRedisSave": true,
  "model": "gpt-4o-mini"
}
```

### Key request fields

- **`clientSlug`** *(required)*: the canonical identifier (also becomes Pinecone namespace).
- **`url`**: website to crawl. Required unless `clientDriveFolder` is provided.
- **`clientDriveFolder`** (aliases: `driveFolderId`, `driveFolder`, `drive_folder`): Drive folder link or ID. Optional.
- **`limit`**: max pages for main crawl (default `500`).
- **`blogLimit`**: max pages for blog crawl (default `50`).
- **`maxDepth`** (alias: `depth`): crawl depth (default `3`).
- **`includePaths` / `excludePaths`**: path filters forwarded to crawl.
- **`skipMarkdownClean`**: if true, disables post-crawl markdown cleaning.
- **`createAssistant`** (aliases: `create_assistant`, `createPineconeAssistant`): if true, attempts to create a Pinecone Assistant. **Default is false**.
- **`skipRedisSave`**: legacy switch (present for back-compat).

### Response (200)

Returns a summary of what happened (storage, Pinecone vectorization, assistant creation).

```json
{
  "success": true,
  "status": "success",
  "index": "sb-knowledge-bases",
  "namespace": "acme-co",
  "pages_processed": 123,
  "drive_docs_processed": 14,
  "total_documents": 137,
  "storage": { "success": true },
  "pinecone": {
    "success": true,
    "files_processed": 137,
    "chunks_created": 982,
    "namespace": "acme-co"
  },
  "assistant": {
    "success": true,
    "created": true,
    "assistant_name": "inbox_manager_acme-co",
    "files_uploaded": 137
  }
}
```

### Error cases

- **400**: missing `clientSlug`, or missing both `url` and Drive folder.
- **500**: unexpected failures; many ingestion sub-steps are logged and may be skipped rather than failing the entire request.

Source: `backend/app/routes/create.py`.

---

## `GET /api/mintagent/indexes` (List “indexes” for UI)

Lists Pinecone namespaces (client slugs) that have content, formatted for the frontend “Indexes” page.

### Query params

- **`client_slug`**: return only this client (preferred)
- **`clientSlug`**: alias
- **`namespace`**: alias (deprecated)

### Response (200)

When listing all:

```json
{
  "indexes": [
    {
      "url": "https://acme-co.com",
      "clientSlug": "acme-co",
      "namespace": "acme-co",
      "pagesCrawled": 42,
      "pages": 42,
      "chunks": 982,
      "createdAt": "2025-12-30T00:00:00+00:00",
      "metadata": {
        "title": "Acme Co",
        "description": "Pinecone namespace: acme-co",
        "favicon": "https://...",
        "ogImage": "https://...",
        "indexName": "acme-co"
      },
      "agent": null,
      "agents": {}
    }
  ]
}
```

When filtering to a single slug:

```json
{ "index": { "...": "..." } }
```

### Error cases

- **404**: slug provided but not found in Pinecone namespace stats.

Source: `backend/app/routes/indexes.py`.

---

## `POST /api/mintagent/stats` (Namespace stats)

Returns high-level statistics for a client slug.

### Request body

```json
{ "clientSlug": "acme-co" }
```

Alias supported:

```json
{ "namespace": "acme-co" }
```

### Response (200)

```json
{
  "total": 982,
  "by_content_type": {},
  "by_document_source": {}
}
```

Notes:

- Today this endpoint uses Pinecone namespace `vector_count` as the primary signal, and returns empty breakdown maps.

Source: `backend/app/routes/stats.py`.

---

## `POST /api/mintagent/query` (Recommended RAG query endpoint)

Retrieves context from Pinecone for `clientSlug`, then generates an answer using the LLM.

This is the endpoint you generally want for “ask the KB a question”, including streaming support.

### Request body (simple)

```json
{
  "clientSlug": "acme-co",
  "query": "What services do you offer?"
}
```

### Request body (chat-style)

If `query` is not present, the backend will take the **last** `"role": "user"` message as the query text:

```json
{
  "clientSlug": "acme-co",
  "messages": [
    { "role": "user", "content": "What services do you offer?" }
  ]
}
```

### Optional request fields

- **`index`**: optional; currently not required (namespace routing uses `clientSlug`).
- **`agentType` / `agent_type`**: changes system prompt selection (defaults to `inbox_manager`).
- **`topK`**: number of context snippets to retrieve (default `5`).
- **`stream`**: if `true`, returns `text/plain` streaming frames (see below).

Metadata filters:

- **`contentType` / `content_type`**: filters to a single content type.
- **`documentSource` / `document_source`**: filters by source (e.g. `website`, `drive`, `intake_form`).
- **`keywords`** / `keyword` / `keywordsAny`: filters where **any** keyword matches (stored as a list of strings).

### Response (non-streaming, 200)

```json
{
  "answer": "…",
  "sources": [
    { "title": "Pricing", "url": "https://acme.co/pricing", "snippet": "…" }
  ]
}
```

### Response (streaming)

If `stream: true`, response is:

- **Content-Type**: `text/plain; charset=utf-8`
- **Format**: newline-delimited frames of the form:

```
<type>:<json>\n
```

Frame types:

- **`8:`**: emitted once at the start, includes the sources:
  - `8:{"sources":[...]}`
- **`0:`**: emitted repeatedly, includes LLM deltas:
  - usually JSON string chunks (depends on `llm_client.stream_answer`)

Source: `backend/app/routes/query.py`.

---

## `POST /api/mintagent/assistant-chat/*` (3-stage reply pipeline)

These endpoints implement a “Draft → QA → Finalize” pipeline, grounded by Pinecone retrieval.

### `POST /api/mintagent/assistant-chat/draft`

Generates an initial draft reply.

Request:

```json
{
  "clientSlug": "acme-co",
  "messages": [{ "role": "user", "content": "Do you do X?" }],
  "top_k": 5,
  "model": "gpt-4o-mini"
}
```

Response:

```json
{
  "draft": "…",
  "citations": [
    { "title": "Source", "url": "…", "snippet": "…", "score": 0.12, "doc_id": "…", "content_type": "…" }
  ],
  "usage": {}
}
```

### `POST /api/mintagent/assistant-chat/qa`

Quality-checks a draft reply and returns structured QA.

Request:

```json
{
  "clientSlug": "acme-co",
  "draft": "…",
  "originalMessage": "Do you do X?",
  "model": "gpt-4o-mini"
}
```

Response:

```json
{
  "qa_result": {
    "is_accurate": true,
    "confidence": 0.8,
    "inaccuracies": [],
    "missing_info": [],
    "suggestions": [],
    "overall_assessment": "…"
  },
  "is_accurate": true,
  "suggestions": [],
  "confidence": 0.8,
  "qa_raw": "{...}"
}
```

### `POST /api/mintagent/assistant-chat/finalize`

Polishes a draft (optionally incorporating QA feedback).

Request:

```json
{
  "clientSlug": "acme-co",
  "draft": "…",
  "qaFeedback": { "suggestions": ["…"] },
  "tone": "professional",
  "model": "gpt-4o-mini"
}
```

Response:

```json
{
  "finalReply": "…",
  "changes": ["…"],
  "reasoning": "…",
  "raw_response": "{...}"
}
```

### `POST /api/mintagent/assistant-chat/full-pipeline`

Runs draft → (optional) QA → (optional) finalize in one call.

Request:

```json
{
  "clientSlug": "acme-co",
  "messages": [{ "role": "user", "content": "Do you do X?" }],
  "tone": "professional",
  "skipQA": false,
  "skipFinalize": false
}
```

Response:

```json
{
  "draft": { "draft": "…", "citations": [] },
  "qa": { "qa_result": { "is_accurate": true } },
  "final": { "finalReply": "…" },
  "pipeline_trace": [
    { "stage": "draft", "status": "success" },
    { "stage": "qa", "status": "success" },
    { "stage": "finalize", "status": "success" }
  ]
}
```

Source: `backend/app/routes/assistant_chat.py`.

---

## `POST /api/mintagent/inbox-manager/*` (Inbox manager reply tools)

These endpoints are specialized for the “inbox manager” workflow.

### `POST /api/mintagent/inbox-manager/draft`

Drafts an email reply grounded by Pinecone retrieval.

Request (minimal):

```json
{
  "clientSlug": "acme-co",
  "replyText": "Hey—do you support SOC2?"
}
```

Alternate inputs:

- `query` (alias for `replyText`)
- `messages` (uses last user message)
- `webhookPayload` / `res` (extracts `data.reply.text_body`)

Response:

```json
{
  "draft": "…",
  "sources": [{ "title": "Source", "url": "…", "snippet": "…" }]
}
```

### `POST /api/mintagent/inbox-manager/qa`

Runs QA on a proposed reply against the full webhook payload.

Request:

```json
{
  "clientSlug": "acme-co",
  "webhookPayload": { "event": {}, "data": { "reply": {} } },
  "proposedReply": "…",
  "model": "gpt-4o-mini"
}
```

Response:

```json
{
  "qa_raw": "{...}",
  "qa": {
    "is_safe_to_send": true,
    "confidence": 0.8,
    "issues": [],
    "suggested_edits": [],
    "rewritten_reply": "..."
  }
}
```

Source: `backend/app/routes/inbox_manager.py`.

---

## `POST /api/mintagent/chat` (Legacy typed chat endpoint)

Older, typed “chat with KB” endpoint.

### Request body

```json
{
  "client_slug": "acme-co",
  "messages": [{ "role": "user", "content": "What do you do?" }],
  "top_k": 5,
  "model": "gpt-4o-mini"
}
```

### Response (200)

```json
{
  "response": "…",
  "sources": [
    {
      "doc_id": "…",
      "url": "…",
      "title": "…",
      "content_type": "…",
      "score": 0.12,
      "chunk_index": 0
    }
  ],
  "namespace": "acme-co"
}
```

Notes:

- Uses a hard-coded Pinecone index name (`sb-knowledge-bases`).
- Does not support the `/query` streaming protocol.

Source: `backend/app/routes/chat.py`.

---

## Reporting & resource endpoints

These endpoints expose report artifacts (historically stored in Spaces) via Pinecone “report indexes”.

### `GET /api/mintagent/resource-links`

Returns API URLs (not presigned storage URLs) to common report artifacts:

```json
{
  "client_data": "http://.../api/mintagent/report/_client_kb_master/summary.json",
  "client_kb_data": "http://.../api/mintagent/report/_client_kb_master/reports/client_audit_results.json",
  "agent_directory": "http://.../api/mintagent/report/agent-registry.json"
}
```

### `GET /api/mintagent/summary-warnings`

Returns `top_warnings` from `_client_kb_master/summary.json`:

```json
{ "warnings": ["..."], "generated_at": "..." }
```

### `GET /api/mintagent/client-details/{client_slug}`

Fetches:

- KB/client data from `_client_kb_master/clients/{client_slug}.json`
- Agent registry data (if present) from `agents/inbox_manager_{client_slug}.json`

```json
{
  "client_slug": "acme-co",
  "kb_data": { "...": "..." },
  "agent_data": { "...": "..." }
}
```

### `GET /api/mintagent/report/{doc_id:path}`

Fetches an arbitrary report document by `doc_id` from Pinecone report indexes.

Examples:

- `/api/mintagent/report/_client_kb_master/summary.json`
- `/api/mintagent/report/_client_kb_master/clients/acme-co.json`
- `/api/mintagent/report/agent-registry.json`

Source: `backend/app/routes/resources.py`.

---

## Back-compat / deprecated endpoints

### `POST /api/mintagent/ensure-agent` (stub)

Back-compat endpoint. DigitalOcean agent provisioning was removed; this returns a non-fatal stub response.

Request:

```json
{ "clientSlug": "acme-co", "agentType": "inbox_manager" }
```

Response:

```json
{
  "clientSlug": "acme-co",
  "agentType": "inbox_manager",
  "agent_uuid": null,
  "agent_endpoint": null,
  "agent_key": null,
  "status": "ok",
  "reason": "No agent provisioning required; chat is Pinecone-grounded."
}
```

Source: `backend/app/routes/agents.py`.

### `GET /api/mintagent/agent-debug/{agent_uuid}` (deprecated)

Always returns **410 Gone**.

Source: `backend/app/routes/agent_debug.py`.

---

## Bulk scripts (CLI)

These scripts live in `backend/scripts/` and are intended for **bulk client processing** (onboarding, upload, vectorization, assistants, and ops/debug).

### Common setup

- Run from repo root, with backend deps installed and env configured (see `env.example` / `docs/LOCAL_DEVELOPMENT.md`).
- Most scripts rely on:
  - **Supabase**: `SUPABASE_AGENT_URL`, `SUPABASE_AGENT_KEY` (and sometimes `SUPABASE_AGENT_SERVICE_ROLE_KEY`)
  - **Pinecone**: `PINECONE_API_KEY`
  - **Firecrawl**: `FIRECRAWL_API_KEY`
  - **OpenAI**: `OPENAI_API_KEY`

### `backend/scripts/onboard_clients_to_supabase_storage.py`

Creates per-client buckets (if missing), ensures `website/`, `drive/`, `intake_form/` prefixes (via `.keep`), and can crawl/ingest sources depending on flags.

- **All clients**:

```bash
python backend/scripts/onboard_clients_to_supabase_storage.py --all
```

- **Single client**:

```bash
python backend/scripts/onboard_clients_to_supabase_storage.py --client-slug abundantly
```

- **Useful flags**:
  - `--website-limit 500`
  - `--website-max-depth 3`
  - `--skip-website`
  - `--skip-drive`
  - `--limit-clients 5`

### `backend/scripts/ingest_to_supabase.py`

Bulk “ingest” runner that calls the backend ingestion logic (website crawl + optional drive ingest) for clients sourced from `backend/scripts/io/bulk_onboarding_run_file.csv`.

- **All clients**:

```bash
python backend/scripts/ingest_to_supabase.py --all
```

- **Single client**:

```bash
python backend/scripts/ingest_to_supabase.py --client-slug abundantly
```

Notes:

- This script requires **Firecrawl**; it will warn if Supabase is not configured (uploads will be skipped).

### `backend/scripts/upsert_to_pinecone.py`

Reads markdown files from Supabase Storage (`client-data-sources/<clientSlug>/{website,drive,intake_form}/*.md`), chunks them, embeds them, and upserts to Pinecone under namespace `clientSlug`.

- **Single client**:

```bash
python backend/scripts/upsert_to_pinecone.py --client abundantly
```

- **All clients (from Supabase Storage folder listing)**:

```bash
python backend/scripts/upsert_to_pinecone.py --all
```

- **Dry run**:

```bash
python backend/scripts/upsert_to_pinecone.py --dry-run --client abundantly
```

- **Useful flags**:
  - `--limit 10` (only for `--all`)
  - `--continue-on-error` (only for `--all`)

### `backend/scripts/create_assistant.py`

Creates a **Pinecone Assistant** for a single client and uploads that client’s markdown files from Supabase Storage.

```bash
python backend/scripts/create_assistant.py abundantly
```

Optional flags:

- `--instructions "..."` (custom assistant instructions)
- `--force` (delete and recreate if it already exists)

If you want to do this in bulk, use a small shell loop (example):

```bash
for slug in abundantly a-perfect-promotion; do
  python backend/scripts/create_assistant.py "$slug"
done
```

### `backend/scripts/verify_supabase_creds.py`

Non-destructive credential verification:

```bash
python backend/scripts/verify_supabase_creds.py
```

Checks:

- list buckets (agent key)
- upload a tiny object to `client-data-sources` (agent key)
- list objects under a temp prefix (agent key)
- optional create/delete temp bucket (service role key, if configured)

### `backend/scripts/list_clients.py`

Lists top-level client folders in `client-data-sources`:

```bash
python backend/scripts/list_clients.py
```

### `backend/scripts/list_storage_files.py`

Lists files under a prefix (useful for debugging ingestion results):

```bash
python backend/scripts/list_storage_files.py --client-slug abundantly
```

### `backend/scripts/delete_all_supabase_storage_buckets.py` (dangerous)

Deletes **ALL** buckets in the configured Supabase project.

- Dry-run:

```bash
python backend/scripts/delete_all_supabase_storage_buckets.py
```

- Actually delete:

```bash
python backend/scripts/delete_all_supabase_storage_buckets.py --yes
```

### SQL generators / misc

- `backend/scripts/create_all_client_buckets.py`: generates SQL (`backend/scripts/create_all_buckets.sql`) for creating buckets + RLS policies from `bulk_onboarding_run_file.csv` (run it, then apply SQL in Supabase).


