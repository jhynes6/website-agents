# MintAgent: AI-Powered Client Knowledge Base System

> Transform client websites and documents into intelligent, context-aware chatbots with a single click.

MintAgent is a production-ready system that ingests client data from websites and Google Drive, stores it in Supabase, vectorizes it in Pinecone, and delivers it through an interactive chat interface. Built for agencies and teams who need to quickly create custom AI assistants for each client.

---

## 🌟 What Makes This Special

- **End-to-End Automation**: From website URL to working chatbot in minutes
- **Multi-Source Ingestion**: Websites (Firecrawl) + Google Drive folders
- **Intelligent Chunking**: A/B testable semantic vs. character-based chunking strategies
- **Production Architecture**: Supabase Storage + Postgres + Pinecone vector DB
- **Client Isolation**: Each client gets their own namespace and storage folder
- **Rich Metadata Tracking**: Content hashing, document context, keywords, and more
- **Bulk Operations**: CLI scripts for processing multiple clients at once

---

## 🏗️ Architecture Overview

```
┌─────────────────┐
│   Next.js UI    │  User enters client info
│  (TypeScript)   │  → Triggers ingestion
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Python Backend │  Orchestrates the pipeline:
│   (FastAPI)     │  1. Scrape website (Firecrawl)
└────────┬────────┘  2. Ingest Drive folder
         │           3. Clean & normalize content
         │           4. Store in Supabase Storage
         │           5. Vectorize in Pinecone
         │           6. Track in Postgres DB
         │
         ▼
┌─────────────────────────────────────────┐
│         Supabase (Storage + DB)         │
│  ┌──────────────────────────────────┐  │
│  │  Storage: client-data-sources/    │  │
│  │    ├── {client-slug}/             │  │
│  │    │   ├── website/*.md           │  │
│  │    │   ├── drive/*.md             │  │
│  │    │   ├── intake_form/*.md       │  │
│  │    │   └── metadata.json          │  │
│  └──────────────────────────────────┘  │
│  ┌──────────────────────────────────┐  │
│  │  Postgres: public.clients         │  │
│  │           public.documents        │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│         Pinecone Vector DB              │
│  Index: sb-knowledge-bases              │
│  Namespaces: {client-slug}              │
│  ┌──────────────────────────────────┐  │
│  │  Chunks with embeddings +        │  │
│  │  metadata (title, url, keywords,  │  │
│  │  content_hash, document_context) │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│   Chat Runtime   │  RAG retrieval + LLM
│  (Dashboard UI)  │  → Context-grounded responses
└─────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.10+ with virtual environment
- **API Keys**:
  - Firecrawl API key
  - OpenAI API key (for LLM operations)
  - Supabase project URL + service role key
  - Pinecone API key + index name

### 1. Clone and Install

```bash
git clone <repository-url>
cd website-agents

# Frontend dependencies
npm install

# Backend dependencies
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

### 2. Configure Environment

Copy `env.example` to `.env.local` (or `backend/.env.local`) and fill in your keys:

```bash
# Firecrawl
FIRECRAWL_API_KEY=your_key_here

# OpenAI
OPENAI_API_KEY=your_key_here

# Supabase (mintleads-agents project)
SUPABASE_AGENT_URL=https://your-project.supabase.co
SUPABASE_AGENT_KEY=your_service_role_key_here

# Pinecone
PINECONE_API_KEY=your_key_here
PINECONE_KB_INDEX=sb-knowledge-bases
```

### 3. Start the Servers

**Terminal 1 - Backend:**
```bash
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 - Frontend:**
```bash
npm run dev
```

### 4. Access the UI

- **Main App**: http://localhost:3000
- **Backend Health**: http://127.0.0.1:8000/healthz

---

## 📖 Complete Workflow: From UI to Chatbot

### Step 1: User Creates a Client Knowledge Base

**UI Entry Point**: `app/page.tsx` (MintAgent creation form)

The user provides:
- **Client Slug**: Unique identifier (e.g., `acme-co`)
- **Client Name**: Display name (e.g., "Acme Corporation")
- **Website URL**: `https://acme.com`
- **Google Drive Folder** (optional): Full Drive folder URL
- **Crawl Options**: Limits, depth, include/exclude paths
- **Semantic Embeddings**: Checkbox to opt into semantic chunking

**What Happens**:
1. UI sends `POST /api/mintagent/create` to the backend
2. Backend route: `backend/app/routes/create.py`

---

### Step 2: Website Scraping (Firecrawl)

**Service**: `backend/app/clients/firecrawl.py`

The backend:
1. **Crawls the website** using Firecrawl API
   - Main crawl: Up to `limit` pages (default 500)
   - Blog crawl: Additional `blogLimit` pages (default 50)
   - Respects `maxDepth`, `includePaths`, `excludePaths`
2. **Extracts markdown** from each page
3. **Captures metadata**: title, URL, favicon, etc.

**Output**: List of page objects with `markdown` content and metadata

---

### Step 3: Google Drive Ingestion (Optional)

**Service**: `backend/app/services/drive_ingest.py`

If a Drive folder is provided:
1. **Parses folder ID** from the Drive URL
2. **Recursively lists files** in the folder
3. **Downloads and converts**:
   - Google Docs → Markdown
   - Google Sheets → CSV → Markdown
   - Google Slides → Markdown
   - PDFs → Text extraction (when possible)
4. **Categorizes content** using LLM (case studies, pitch decks, etc.)

**Auth**: Requires `service_account.json` at repo root

**Output**: List of document objects with markdown content

---

### Step 4: Content Normalization & Enrichment

**Location**: `backend/app/routes/create.py` (in `_upload_to_storage`)

For each document, the system:

1. **Cleans markdown** (removes navigation, boilerplate)
2. **Categorizes content** using LLM:
   - Website: `homepage`, `about`, `blogs_resources`, etc.
   - Drive: `case_studies`, `pitch_decks`, `client_materials`, etc.
3. **Extracts keywords** using LLM (GPT-4o-mini)
4. **Generates document context** using LLM:
   - Prompt: "What is this document? Please summarize it in one or two sentences..."
   - Stored in `document_context` field
5. **Computes content hash** (SHA256 of normalized text):
   - Used to track document changes over time
   - Stored in `content_hash` field

**Output**: Enriched document objects ready for storage

---

### Step 5: Supabase Storage Upload

**Client**: `backend/app/clients/supabase_storage_client.py`

**Storage Structure**:
```
client-data-sources/
  └── {client-slug}/
      ├── website/
      │   └── {doc_id}.md
      ├── drive/
      │   └── {doc_id}.md
      ├── intake_form/
      │   └── {doc_id}.md
      └── metadata.json
```

**Document Format** (each `.md` file):
```markdown
---
doc_id: "acme-co_website_acme.com_about.md"
client_slug: "acme-co"
document_source: "website"
url: "https://acme.com/about"
title: "About Acme"
content_type: "about"
keywords: ["company", "mission", "values"]
content_hash: "abc123..."
document_context: "This document describes Acme's company mission and values..."
storage_bucket: "client-data-sources"
storage_path: "acme-co/website/acme-co_website_acme.com_about.md"
storage_preview_url: "https://...supabase.co/storage/v1/object/public/..."
file_type: "html"
ingested_at: "2025-01-08T10:00:00Z"
---

# Document Body

Cleaned markdown content...
```

**Metadata File**: `metadata.json` contains:
- Summary statistics (total docs, by content type)
- Client info (website URL, drive URL, favicon)
- Chunker used
- Creation timestamp

---

### Step 6: Postgres Database Tracking

**Client**: `backend/app/clients/supabase_agents_db_client.py`

**Tables**:

**`public.clients`**:
- `client_slug` (PK)
- `client_name`
- `client_domain`
- `website`
- `drive_folder_url`
- `intake_form_url`
- `created_at`, `last_updated`

**`public.documents`**:
- `doc_id` (PK)
- `client_slug`
- `ingestion_status` (`ingested`, `embedded`, `error - ingest`, `error - embed`)
- `document_source`
- `content_type`
- `url`
- `keywords`
- `content_hash`
- `document_context`
- `text` (full document body)
- `db_file_url` (public Supabase Storage URL)
- `created_at`, `updated_at`

**What Gets Tracked**:
- Client metadata (name, domain, URLs)
- Document status (ingested → embedded)
- Content hashes for change detection
- Full document text for quick reference

---

### Step 7: Pinecone Vectorization

**Client**: `backend/app/clients/pinecone_client.py`

**Index**: `sb-knowledge-bases` (canonical)
**Namespace**: `{client-slug}` (one per client)

**Chunking Strategy** (configurable per client):

1. **Character-based (default)**: `char:1200:200`
   - 1200 characters per chunk
   - 200 character overlap
   - Simple sliding window

2. **Semantic (opt-in)**: `md_semantic_v1:w350:m550:o80`
   - Markdown structure-aware
   - Respects headings, paragraphs, lists
   - Target: 350 words, max: 550 words, overlap: 80 words

**Semantic A/B Testing**:
- If "Semantic embeddings" checkbox is selected:
  - Namespace: `{client-slug}-semantic`
  - Optional separate index: `sb-knowledge-bases-semantic`
  - Same Supabase Storage location

**What Gets Stored**:
- **Vector**: OpenAI embedding of chunk text
- **Metadata**:
  - `text`: Chunk content
  - `title`: Document title
  - `url`: Source URL
  - `doc_id`: Stable document identifier
  - `document_source`: `website`, `drive`, `intake_form`
  - `content_type`: `homepage`, `case_studies`, etc.
  - `keywords`: Array of extracted keywords
  - `content_hash`: SHA256 hash
  - `document_context`: LLM-generated summary
  - `storage_bucket`, `storage_path`, `storage_preview_url`
  - `file_type`: Original file type (`html`, `pdf`, `docx`, etc.)
  - `chunker`: Chunking strategy used

**Upsert Process**:
1. Chunk documents using selected strategy
2. Generate embeddings (OpenAI `text-embedding-3-small`)
3. Batch upsert to Pinecone namespace
4. Update `documents` table: `ingestion_status = "embedded"`

---

### Step 8: Chat Runtime (RAG)

**UI**: `app/dashboard/page.tsx`
**Backend Route**: `backend/app/routes/chat.py`

**Query Flow**:

1. **User sends message** in chat UI
2. **Backend extracts query** from message history
3. **Pinecone similarity search**:
   - Index: `sb-knowledge-bases`
   - Namespace: `{client-slug}` (isolated per client)
   - Top-K retrieval (default: 5-10 chunks)
   - Optional metadata filters (by `content_type`, `document_source`, etc.)
4. **Build context block** from retrieved chunks
5. **LLM call** (GPT-4o-mini or GPT-4o):
   - System prompt: "Use ONLY the provided context. Cite sources. Say you don't know if context is insufficient."
   - User query + retrieved context
6. **Response returned** with:
   - Assistant message
   - Citations (title, URL, snippet, relevance score)

**Client Isolation**: Each client's chat only retrieves from their namespace, ensuring no cross-contamination.

---

## 🛠️ Key Components

### Frontend (`app/`)

- **`app/page.tsx`**: Main creation form
- **`app/indexes/page.tsx`**: List all client knowledge bases
- **`app/dashboard/page.tsx`**: Interactive chat interface
- **`app/api/mintagent/*`**: Next.js API routes (proxies to backend)

### Backend (`backend/app/`)

**Routes** (`backend/app/routes/`):
- **`create.py`**: Ingestion orchestration (website + Drive → Storage → Pinecone)
- **`chat.py`**: RAG query endpoint
- **`indexes.py`**: List clients, delete clients
- **`resources.py`**: Resource links, client metadata
- **`inbox_manager.py`**: Specialized drafting workflows
- **`assistant_chat.py`**: 3-stage assistant flow

**Clients** (`backend/app/clients/`):
- **`firecrawl.py`**: Website scraping
- **`supabase_storage_client.py`**: Supabase Storage operations
- **`supabase_agents_db_client.py`**: Postgres table operations
- **`pinecone_client.py`**: Vector DB operations (upsert, search, chunking)

**Services** (`backend/app/services/`):
- **`drive_ingest.py`**: Google Drive folder ingestion

**Utils** (`backend/app/utils/`):
- **`content_hash.py`**: Content hashing utilities

### Scripts (`backend/scripts/`)

**Bulk Operations**:
- **`ingest_to_supabase.py --all`**: Ingest all clients to Supabase Storage
- **`upsert_to_pinecone.py --all`**: Vectorize all clients from Storage
- **`create_assistant.py`**: Create Pinecone Assistant for a client
- **`create_assistants_for_kb_namespaces.py`**: Bulk create assistants

**Utilities**:
- **`sync_clients_from_storage_to_db.py`**: Backfill `clients` table from Storage
- **`delete_all_clients.py`**: Cleanup script (dangerous)
- **`bulk_client_onboarding.py`**: CSV-driven bulk onboarding

---

## 📊 Data Flow Summary

```
User Input (UI)
    ↓
[1] Firecrawl → Website Pages (Markdown)
[2] Google Drive API → Drive Files (Markdown)
    ↓
[3] LLM Cleaning & Categorization
[4] Keyword Extraction (LLM)
[5] Document Context Generation (LLM)
[6] Content Hash Computation
    ↓
[7] Supabase Storage (client-data-sources/{slug}/)
    ├── website/*.md
    ├── drive/*.md
    ├── intake_form/*.md
    └── metadata.json
    ↓
[8] Postgres DB (public.clients, public.documents)
    ↓
[9] Chunking (char or semantic)
[10] Embedding Generation (OpenAI)
    ↓
[11] Pinecone Upsert (sb-knowledge-bases/{slug})
    ↓
[12] Chat Query → RAG Retrieval → LLM Response
```

---

## 🔧 Configuration

### Environment Variables

See `env.example` for the full list. Key variables:

- **`FIRECRAWL_API_KEY`**: Required for website scraping
- **`OPENAI_API_KEY`**: Required for LLM operations
- **`SUPABASE_AGENT_URL`**: Supabase project URL
- **`SUPABASE_AGENT_KEY`**: Service role key (for Storage + DB writes)
- **`PINECONE_API_KEY`**: Pinecone API key
- **`PINECONE_KB_INDEX`**: Default: `sb-knowledge-bases`

### Chunking Configuration

Per-client chunker is stored in `metadata.json`:
- Default: `char:1200:200`
- Semantic: `md_semantic_v1:w350:m550:o80`

See `README_CHUNKING_AB_TEST.md` for A/B testing strategies.

---

## 🧪 Testing & Development

### Local Development

1. **Backend**: `uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload`
2. **Frontend**: `npm run dev` (sets `NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:8000`)

### Health Checks

- Backend: `GET http://127.0.0.1:8000/healthz`
- Frontend: `http://localhost:3000`

### Debugging

- **Backend config**: `GET /api/mintagent/debug`
- **Client metadata**: `GET /api/mintagent/client-metadata/{clientSlug}`
- **Storage verification**: `backend/scripts/verify_supabase_creds.py`

---

## 📚 Documentation

- **`docs/WORKFLOW_UI_TO_CLIENT_ASSISTANT.md`**: Detailed end-to-end workflow
- **`docs/BACKEND_API_REFERENCE.md`**: Complete API documentation
- **`docs/LOCAL_DEVELOPMENT.md`**: Local setup guide
- **`README_CHUNKING_AB_TEST.md`**: Chunking strategy A/B testing guide

---

## 🎯 Common Operations

### Create a New Client

1. Go to http://localhost:3000
2. Fill in client info (slug, name, website, Drive folder)
3. Click "Create"
4. Wait for ingestion to complete (~5-10 minutes for typical site)

### View All Clients

- Go to http://localhost:3000/indexes
- See cards for each client with stats and links

### Chat with a Client

- Go to http://localhost:3000/dashboard?clientSlug={slug}
- Start chatting (RAG retrieval happens automatically)

### Bulk Process Clients

```bash
# Ingest all clients to Supabase Storage
python backend/scripts/ingest_to_supabase.py --all

# Vectorize all clients to Pinecone
python backend/scripts/upsert_to_pinecone.py --all

# Create Pinecone Assistants for all clients
python backend/scripts/create_assistants_for_kb_namespaces.py
```

### Delete a Client

- From UI: `/indexes` page → Delete button
- Or via API: `DELETE /api/indexes?namespace={clientSlug}`
- Deletes: Pinecone namespace + Supabase Storage folder

---

## 🔒 Security & Best Practices

- **Service Role Keys**: Use service role keys for backend operations (bypasses RLS)
- **Client Isolation**: Each client's data is isolated by namespace/folder
- **Content Hashing**: Track document changes via `content_hash`
- **Error Tracking**: `ingestion_status` in `documents` table tracks failures
- **RLS Policies**: Supabase Storage buckets should have appropriate RLS policies

---

## 🚧 Troubleshooting

### Ingestion Fails

- Check Firecrawl API key
- Verify Supabase service role key has Storage write permissions
- Check Pinecone API key and index exists
- Review backend logs for specific errors

### Chat Returns Irrelevant Results

- Verify namespace matches `clientSlug`
- Check that documents were actually upserted (query Pinecone stats)
- Review chunking strategy (semantic vs. character)
- Ensure metadata fields are populated correctly

### Storage Upload Fails

- Verify `SUPABASE_AGENT_KEY` is a service role key
- Check bucket `client-data-sources` exists
- Review RLS policies on the bucket

---

## 📝 License

[Your License Here]

---

## 🙏 Acknowledgments

Built with:
- **Next.js** for the frontend
- **FastAPI** for the backend
- **Supabase** for storage and Postgres
- **Pinecone** for vector search
- **Firecrawl** for website scraping
- **OpenAI** for embeddings and LLM

---

**Ready to build?** Start with the [Quick Start](#-quick-start) section and create your first client knowledge base!

