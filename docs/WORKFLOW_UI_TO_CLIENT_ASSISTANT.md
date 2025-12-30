### Goal of this document
This doc is the **end-to-end, “nothing hand-wavy”** description of how a user goes from the **MintAgent UI** to getting a **client-specific, context-grounded answer**.

This repository is now **Supabase + Pinecone**:
- **Supabase**: Storage + relational “non-vectorized” data (client artifacts, manifests, future tables).
- **Pinecone**: Vector index used at chat-time retrieval (RAG) and for grounded assistant responses.

---

### High-level system map (request path)
When developing locally, there are **two servers**:
- **Next.js UI**: `npm run dev` (serves UI, and Next route handlers under `app/api/**`)
- **Python backend**: `uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload`

The UI calls the Python backend either:
- **Directly** via `NEXT_PUBLIC_BACKEND_URL` (recommended for local dev), or
- **Indirectly** via Next route handlers that proxy requests to the backend.

The helper that decides this is `lib/backend.ts`.

---

### The user journey (UI pages)

#### 1) Entry point: “Create” page
Primary UI entry is `app/page.tsx` (MintAgent page).

User inputs:
- **Website URL** (required unless Drive-only workflow is allowed)
- **Google Drive folder URL** (optional)
- Crawl options (limit, include/exclude paths, etc.)

What happens when user clicks “Create”:
- The UI sends a POST request to the “create” API route (Next proxy):
  - `app/api/mintagent/create/route.ts`
- That route forwards the payload to the Python backend:
  - `POST /api/mintagent/create` (implemented in `backend/app/routes/create.py`)

#### 2) Index list: “Indexes” page
`app/indexes/page.tsx` lists existing client indexes (backed by Pinecone namespaces).

It calls:
- `GET /api/indexes` (Next route) → proxies to `GET /api/mintagent/indexes` (Python)
- `GET /api/mintagent/resource-links` (Python)
- `GET /api/mintagent/summary-warnings` (Python)

#### 3) Chat runtime: “Dashboard” page
`app/dashboard/page.tsx` is the interactive chat UI.

Core chat call:
- `app/api/mintagent/query/route.ts` → proxies to `POST /api/mintagent/query` (Python)

For inbox-manager style drafting, there are also specialized endpoints:
- `POST /api/mintagent/inbox-manager/draft` (Python) in `backend/app/routes/inbox_manager.py`
- The 3-stage “assistant_chat” flow:
  - `POST /api/mintagent/assistant-chat/draft`
  - `POST /api/mintagent/assistant-chat/qa`
  - `POST /api/mintagent/assistant-chat/finalize`
  - implemented in `backend/app/routes/assistant_chat.py`

---

### Backend: create workflow (scrape → normalize → store → vectorize)
The backend create flow lives in:
- `backend/app/routes/create.py`

At a high level it:
- **Crawls** website pages with Firecrawl (`backend/app/clients/firecrawl.py`)
- **Optionally** ingests Google Drive folder content (`backend/app/services/drive_ingest.py`)
- **Normalizes** content into canonical “documents” (text + metadata)
- **Stores raw artifacts** in Supabase Storage (bucket-per-client layout)
- **Upserts vectors** into Pinecone (namespace-per-client)

#### 1) Crawl website (Firecrawl)
Firecrawl client:
- `backend/app/clients/firecrawl.py`

Core method:
- `crawl_and_wait(url, limit, include_paths, exclude_paths, max_depth)` → returns a list of pages

Each page typically has:
- `markdown` (preferred)
- `metadata.sourceURL`, `metadata.title`, etc.

#### 2) Ingest Drive folder (Google API)
Drive ingest service:
- `backend/app/services/drive_ingest.py`

Key functions:
- `extract_drive_folder_id()` – robustly parses folder IDs from URLs
- `list_drive_files()` – recursively lists files
- `download_drive_file_text()` – exports Docs/Sheets/Slides to text/CSV, extracts PDFs when possible
- `build_drive_documents()` – converts Drive files into canonical document dicts
- `categorize_drive_documents()` – optional LLM classification for content_type

Drive auth:
- requires `service_account.json` at repo root (or `backend/service_account.json`)

#### 3) Store raw artifacts (Supabase Storage)
Supabase Storage client:
- `backend/app/clients/supabase_agent_storage_client.py`

Storage layout:
- **Bucket name** = `client_slug`
- **Folders (prefixes)**:
  - `website/`
  - `drive/`
  - `intake_form/`

Folder creation is implemented by uploading a tiny placeholder object:
- `website/.keep`, `drive/.keep`, `intake_form/.keep`

Important:
- Supabase “folders” are just **object key prefixes**.

Auth:
- `SUPABASE_AGENT_URL`
- `SUPABASE_AGENT_KEY` (**should be a service_role JWT** for server-side bucket creation + upload)

#### 4) Vectorize + upsert (Pinecone)
Pinecone client:
- `backend/app/clients/pinecone_client.py`

Index strategy:
- **Single Pinecone index**, many **namespaces** (1 namespace per client slug)

Canonical namespace:
- `namespace = client_slug`

Stored fields (typical):
- `text` (chunk text)
- `title`
- ≈
- `document_source` (`website`, `client_materials`, `intake_form`, etc.)
- `content_type` (`homepage`, `case_studies`, etc.)
- `file_key` / `doc_id` (stable identifiers)

---

### Backend: grounded assistant at query-time (RAG)
There are two main “assistant” patterns in this repo:

#### Pattern A) Direct RAG + LLM response (default)
Used in:
- `backend/app/routes/query.py`
- `backend/app/routes/inbox_manager.py`
- `backend/app/routes/assistant_chat.py`

Steps:
- extract latest user query from `messages`
- run Pinecone similarity search in the **client namespace**
- build a “context block” from top hits
- call LLM with a strict system prompt:
  - “use ONLY the provided context”
  - “cite sources”
  - “say you don’t know when context is insufficient”

Output returned to UI:
- assistant response text
- citations/sources (title, url/file_key, snippet, scores)

#### Pattern B) Pinecone Assistant (optional)
There are scripts and clients for Pinecone Assistant usage (assistant-level file store + chat).
This pattern can be used when you want Pinecone Assistant to manage file-level RAG and citations.

---

### “Client-specific grounding” guarantee
The grounding boundary is enforced by:
- **Namespace isolation in Pinecone** (`namespace = client_slug`)
- Optional additional metadata filters (when used) for document_source/content_type

So even if multiple clients exist, a chat for `clientSlug="vew-media"` retrieves only from:
- `Pinecone index: <kb_index>`
- `namespace: vew-media`

---

### Operational notes (what to verify when debugging)

#### If create fails
Check:
- Firecrawl key set and reachable
- Pinecone API key and index exists
- Supabase Storage key is **service_role** (or you’ve explicitly opened RLS policies)
- `service_account.json` for Drive ingest (if Drive is enabled)

#### If chat returns irrelevant sources
Check:
- the Pinecone namespace used matches the clientSlug
- documents were actually upserted for that namespace
- metadata fields are stable (`title`, `url`, `doc_id`, etc.)

---

### Where to look in code (quick pointers)
- **UI create flow**: `app/page.tsx` → `app/api/mintagent/create/route.ts`
- **Backend create**: `backend/app/routes/create.py`
- **Backend query**: `backend/app/routes/query.py`
- **RAG retrieval**: `backend/app/clients/pinecone_client.py`
- **Storage writes**: `backend/app/clients/supabase_agent_storage_client.py`
- **Drive ingest**: `backend/app/services/drive_ingest.py`
- **Inbox manager**: `backend/app/routes/inbox_manager.py`
- **3-stage assistant**: `backend/app/routes/assistant_chat.py`


