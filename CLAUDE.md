# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MintAgent is a production RAG (Retrieval-Augmented Generation) system that ingests client data from websites and Google Drive, stores it in Supabase, vectorizes it in Pinecone, and delivers it through an interactive chat interface. The system creates isolated, client-specific knowledge bases with intelligent chunking and metadata tracking.

**Tech Stack:**
- **Frontend**: Next.js 15 (TypeScript, React 19, App Router)
- **Backend**: FastAPI (Python 3.10+)
- **Storage**: Supabase (Storage + Postgres)
- **Vector DB**: Pinecone
- **Scraping**: Firecrawl API
- **LLM**: OpenAI (embeddings + chat)

## Development Commands

### Starting the Application

**Backend (Terminal 1):**
```bash
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Frontend (Terminal 2):**
```bash
npm run dev
# Sets NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:8000 automatically
```

**Access Points:**
- Frontend: http://localhost:3000
- Backend health: http://127.0.0.1:8000/healthz
- Backend debug: http://127.0.0.1:8000/api/mintagent/debug

### Installation

**Frontend:**
```bash
npm install
```

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Linting & Building

```bash
# Lint frontend
npm run lint

# Build frontend
npm run build

# Start production frontend
npm start
```

### Key Backend Scripts

Located in `backend/scripts/`:

**Bulk Operations:**
```bash
# Ingest all clients to Supabase Storage
python backend/scripts/ingest_to_supabase.py --all

# Vectorize all clients to Pinecone
python backend/scripts/upsert_to_pinecone.py --all

# Process single client with specific chunker
python backend/scripts/upsert_to_pinecone.py --client acme-co --chunker md_semantic_v1

# Create Pinecone Assistants for all clients
python backend/scripts/create_assistants_for_kb_namespaces.py

# Bulk onboard clients from CSV
python backend/scripts/bulk_client_onboarding.py
```

**Utilities:**
```bash
# Sync clients from Storage to DB
python backend/scripts/sync_clients_from_storage_to_db.py

# List all clients
python backend/scripts/list_clients.py

# Verify Supabase credentials
python backend/scripts/verify_supabase_creds.py

# Build client map reports (CSV exports)
python backend/scripts/build_client_maps_reports.py
```

## Architecture

### Data Flow (End-to-End)

```
User Input (UI)
    → Firecrawl (website scraping) + Google Drive API (document ingestion)
    → LLM Cleaning & Categorization
    → Content Hash + Keywords + Document Context (LLM-generated)
    → Supabase Storage (client-data-sources/{client-slug}/)
    → Postgres DB (public.clients, public.documents)
    → Chunking (character-based or semantic markdown)
    → Embedding Generation (OpenAI text-embedding-3-small)
    → Pinecone Upsert (sb-knowledge-bases/{client-slug} namespace)
    → RAG Chat (query → retrieval → LLM response)
```

### Client Isolation

Each client has:
- **Unique slug**: `{client-slug}` (e.g., `acme-co`)
- **Storage folder**: `client-data-sources/{client-slug}/`
- **Pinecone namespace**: `{client-slug}` (or `{client-slug}-semantic` for A/B testing)
- **DB records**: `public.clients` and `public.documents` tables filtered by `client_slug`

### Key Components

**Frontend (`app/`):**
- `app/page.tsx`: Main client creation form
- `app/indexes/page.tsx`: List all client knowledge bases
- `app/dashboard/page.tsx`: Interactive RAG chat interface
- `app/api/mintagent/*`: Next.js API routes (proxies to FastAPI backend)

**Backend (`backend/app/`):**

**Routes (`backend/app/routes/`):**
- `create.py`: Orchestrates full ingestion pipeline (website + Drive → Storage → Pinecone)
- `chat.py`: RAG query endpoint (Pinecone retrieval + LLM response)
- `assistant_chat.py`: 3-stage assistant workflow
- `inbox_manager.py`: Specialized drafting workflows
- `indexes.py`: List/delete clients
- `query.py`: Direct Pinecone query endpoint
- `resources.py`: Resource links and client metadata
- `stats.py`: Client statistics

**Clients (`backend/app/clients/`):**
- `firecrawl.py`: Website scraping via Firecrawl API
- `supabase_storage_client.py`: Supabase Storage operations (upload, download, delete)
- `supabase_agents_db_client.py`: Postgres table operations (clients, documents)
- `pinecone_client.py`: Vector DB operations (upsert, search, chunking strategies)
- `pinecone_assistant_client.py`: Pinecone Assistant API wrapper
- `llm.py`: OpenAI LLM client wrapper

**Services (`backend/app/services/`):**
- `drive_ingest.py`: Google Drive folder ingestion (Docs, Sheets, Slides, PDFs)
- `client_onboarding_storage.py`: Client onboarding storage helpers
- `client_maps_reports.py`: Generate CSV reports of client knowledge bases

**Utils (`backend/app/utils/`):**
- `content_hash.py`: Content hashing utilities (SHA256)

### Storage Structure

**Supabase Storage** (`client-data-sources` bucket):
```
client-data-sources/
  └── {client-slug}/
      ├── website/{doc_id}.md       # Scraped website pages
      ├── drive/{doc_id}.md         # Google Drive documents
      ├── intake_form/{doc_id}.md   # Intake form submissions
      └── metadata.json             # Client metadata + chunker config
```

**Document Format** (markdown with frontmatter):
```markdown
---
doc_id: "acme-co_website_acme.com_about.md"
client_slug: "acme-co"
document_source: "website"
url: "https://acme.com/about"
title: "About Acme"
content_type: "about"
keywords: ["company", "mission"]
content_hash: "abc123..."
document_context: "This document describes Acme's company mission..."
storage_bucket: "client-data-sources"
storage_path: "acme-co/website/acme-co_website_acme.com_about.md"
file_type: "html"
ingested_at: "2025-01-08T10:00:00Z"
---

# Document Body
Cleaned markdown content...
```

### Database Schema

**`public.clients`:**
- `client_slug` (PK)
- `client_name`, `client_domain`, `website`, `drive_folder_url`
- `created_at`, `last_updated`

**`public.documents`:**
- `doc_id` (PK)
- `client_slug` (FK)
- `ingestion_status`: `ingested`, `embedded`, `error - ingest`, `error - embed`
- `document_source`: `website`, `drive`, `intake_form`
- `content_type`: `homepage`, `about`, `case_studies`, `pitch_decks`, etc.
- `url`, `keywords`, `content_hash`, `document_context`
- `text` (full document body)
- `db_file_url` (public Supabase Storage URL)

### Pinecone Vector Storage

**Index**: `sb-knowledge-bases` (default)
**Namespace**: `{client-slug}` (one per client)

**Vector Metadata** (stored with each chunk):
- `text`: Chunk content
- `title`, `url`, `doc_id`
- `document_source`, `content_type`
- `keywords`: Array of extracted keywords
- `content_hash`: SHA256 hash for change detection
- `document_context`: LLM-generated document summary
- `storage_bucket`, `storage_path`, `storage_preview_url`
- `file_type`: Original file type (`html`, `pdf`, `docx`, etc.)
- `chunker`: Chunking strategy used (`char:1200:200` or `md_semantic_v1:w350:m550:o80`)

## Chunking Strategies

Two strategies are supported for A/B testing (see `README_CHUNKING_AB_TEST.md` for details):

**1. Character-based (default):** `char:1200:200`
- 1200 characters per chunk
- 200 character overlap
- Simple sliding window

**2. Semantic markdown (opt-in):** `md_semantic_v1:w350:m550:o80`
- Markdown structure-aware (respects headings, paragraphs, lists)
- Target: 350 words, max: 550 words, overlap: 80 words

**A/B Testing Approach:**
- Baseline namespace: `{client-slug}` (character chunking)
- Semantic namespace: `{client-slug}-semantic` (semantic chunking)
- Both read from same Supabase Storage folder
- Can use same index with different namespaces OR separate indexes

**Per-client config**: Stored in `client-data-sources/{client-slug}/metadata.json` as `"chunker": "..."`

## Configuration

### Environment Variables

Copy `env.example` to `.env.local` and fill in:

**Required:**
- `FIRECRAWL_API_KEY`: Firecrawl API key
- `OPENAI_API_KEY`: OpenAI API key
- `SUPABASE_AGENT_URL`: Supabase project URL
- `SUPABASE_AGENT_KEY`: Supabase service role key (for Storage + DB writes)
- `PINECONE_API_KEY`: Pinecone API key
- `PINECONE_KB_INDEX`: Default `sb-knowledge-bases`

**Optional:**
- `ANTHROPIC_API_KEY`, `GROQ_API_KEY`: Alternative LLM providers
- `BISON_API_KEY`, `BISON_SUPABASE_*`: Email Bison integration
- `PINECONE_KB_SEMANTIC_INDEX`: Separate index for semantic A/B testing

### Backend Config Loading

**File**: `backend/app/config.py`

The backend loads env vars from (in order):
1. `backend/.env`
2. `backend/.env.local`
3. `.env`
4. `.env.local`
5. `../.env` (parent dir fallbacks)

All settings are defined in `Settings` class (Pydantic).

## Important Patterns

### Content Enrichment Pipeline

For each ingested document:
1. **Clean markdown** (remove navigation, boilerplate)
2. **Categorize content** via LLM (homepage, blog, case study, etc.)
3. **Extract keywords** via LLM (GPT-4o-mini)
4. **Generate document context** via LLM (1-2 sentence summary)
5. **Compute content hash** (SHA256 of normalized text)

This happens in `backend/app/routes/create.py` (`_upload_to_storage` function).

### Google Drive Authentication

Requires `service_account.json` at repo root with Google Cloud credentials. The file should have permissions to access Google Drive API.

**Service**: `backend/app/services/drive_ingest.py`

### RAG Query Flow

1. User sends message in chat UI (`app/dashboard/page.tsx`)
2. Frontend calls `POST /api/mintagent/chat`
3. Backend route: `backend/app/routes/chat.py`
4. Pinecone similarity search in `{client-slug}` namespace
5. Retrieve top-K chunks (default 5-10)
6. Build context block from retrieved chunks
7. LLM call with system prompt: "Use ONLY the provided context. Cite sources."
8. Return response with citations (title, URL, snippet, relevance score)

### Error Handling

The `documents` table tracks ingestion status:
- `ingested`: Successfully stored in Supabase Storage
- `embedded`: Successfully vectorized in Pinecone
- `error - ingest`: Failed during ingestion
- `error - embed`: Failed during vectorization

Check logs and DB for debugging.

## Common Gotchas

1. **Firecrawl pagination**: The system handles Firecrawl's paginated crawl results automatically. Main crawl has `limit` (default 500), separate blog crawl has `blogLimit` (default 50).

2. **Pinecone rate limiting**: The `pinecone_client.py` has built-in retry logic with exponential backoff for rate limits. Configurable via `_is_retryable_pinecone_error()`.

3. **Mixed chunkers**: Re-upserting with a different chunker without clearing the namespace will mix old + new chunks. Use separate namespaces for A/B testing (e.g., `{client-slug}-semantic`).

4. **Service role keys**: Supabase Storage operations require service role key, not anon key. Set `SUPABASE_AGENT_KEY` to service role key.

5. **Content hashes**: Used for change detection. If document content changes, hash changes, and system can detect updates.

6. **Google Drive file types**: Supported formats include Google Docs (→ Markdown), Sheets (→ CSV → Markdown), Slides (→ Markdown), and PDFs (text extraction). Binary files are skipped.

## Testing & Debugging

**Backend config check:**
```bash
curl http://127.0.0.1:8000/api/mintagent/debug
```

**Client metadata:**
```bash
curl http://127.0.0.1:8000/api/mintagent/client-metadata/{clientSlug}
```

**Verify Supabase credentials:**
```bash
python backend/scripts/verify_supabase_creds.py
```

**Check Pinecone namespace stats:**
Use Pinecone console or query `/api/mintagent/stats?namespace={clientSlug}`

## Project-Specific Notes

- **No Upstash or DigitalOcean**: Previously used, now removed. All storage is Supabase + Pinecone.
- **Client slug format**: Lowercase, hyphenated (e.g., `acme-co`, `galactic-fed`)
- **Semantic embeddings UI checkbox**: Controls whether to use semantic chunking and separate namespace
- **Bulk operations**: Use `--all` flag with bulk scripts to process all 2clients in Storage
- **CSV onboarding**: `bulk_client_onboarding.py` supports CSV-driven client creation
- **Firecrawl config**: Poll interval and timeout configurable via env vars (defaults: 1s poll, 600s timeout)
