# Full Pipeline Documentation

## Overview

This document describes the complete client onboarding pipeline from ingestion to chatbot.

## Pipeline Architecture

```
Client Data (Website + Drive)
        ↓
[1] Scraping & Cleaning
        ↓
[2] Supabase Storage (Markdown with YAML)
        ↓
[3] Pinecone Vectorization (per-client namespace)
        ↓
[4] RAG Chatbot (OpenAI + Context Retrieval)
```

---

## Phase 1: Data Ingestion

### Input
- `client_slug`: Unique identifier (e.g., "a-perfect-promotion")
- `url`: Client website URL
- `drive_folder_id`: Google Drive folder ID (optional)

### Process
1. **Website Scraping** (Firecrawl)
   - Crawls website with depth/limit controls
   - Extracts markdown content
   - Captures metadata (title, URL, favicon)

2. **Drive Ingestion** (Google Drive API)
   - Downloads files from specified folder
   - Converts to markdown
   - Preserves file metadata

3. **Content Cleaning** (LLM-powered)
   - Removes navigation, boilerplate
   - Categorizes content (homepage, blog, case studies, etc.)
   - Extracts keywords

### Output
- Cleaned documents with metadata
- Ready for storage

---

## Phase 2: Supabase Storage

### Bucket Structure
```
client-data-sources/
  ├── {client-slug}/
  │   ├── website/
  │   │   └── {doc_id}.md
  │   ├── drive/
  │   │   └── {doc_id}.md
  │   ├── intake_form/
  │   │   └── {doc_id}.md
  │   └── metadata.json
```

### Document Format
Each `.md` file contains:
- **YAML Frontmatter**: Metadata (doc_id, URL, title, keywords, etc.)
- **Body**: Cleaned markdown content

```markdown
---
doc_id: "client-slug_website_domain_path.md"
client_slug: "client-slug"
document_source: "website"
url: "https://example.com/page"
title: "Page Title"
content_type: "homepage"
keywords:
  - "keyword1"
  - "keyword2"
ingested_at: "2025-12-30T10:00:00.000000+00:00"
content_body_size: 5432
size: 5890
content_length: 5890
---

# Page Content

Cleaned markdown body...
```

### Endpoint
- Function: `_upload_to_storage()` in `backend/app/routes/create.py`
- Uploads all documents with upsert (overwrites if exists)
- Local backup if upload fails

---

## Phase 3: Pinecone Vectorization

### Index Configuration
- **Index Name**: `sb-knowledge-bases`
- **Dimension**: 1024 (text-embedding-3-small)
- **Metric**: cosine
- **Cloud**: AWS (us-west-2)

### Namespace Strategy
- One namespace per client
- Namespace = `client_slug`
- Example: `"a-perfect-promotion"`

### Process
1. **Read from Supabase Storage**
   - Lists all `.md` files for client
   - Downloads and parses YAML + body

2. **Chunking**
   - Chunk size: 1200 characters
   - Overlap: 200 characters
   - Preserves context between chunks

3. **Embedding Generation**
   - Model: `text-embedding-3-small`
   - Dimensions: 1024
   - Provider: OpenAI

4. **Vector Metadata**
   ```json
   {
     "client_slug": "a-perfect-promotion",
     "doc_id": "a-perfect-promotion_website_...",
     "chunk_index": 0,
     "text": "Chunk preview (1000 chars)",
     "document_source": "website",
     "content_type": "homepage",
     "url": "https://...",
     "title": "Page Title",
     "keywords": "keyword1,keyword2,...",
     "ingested_at": "2025-12-30T10:00:00",
     "storage_path": "a-perfect-promotion/website/..."
   }
   ```

5. **Upsert to Pinecone**
   - Batch upsert per file
   - Overwrites existing vectors

### Endpoint
- Function: `_vectorize_to_pinecone()` in `backend/app/routes/create.py`
- Called automatically after successful Supabase upload

---

## Phase 4: RAG Chatbot

### Query Flow
```
User Message
    ↓
Embed Query (OpenAI)
    ↓
Search Pinecone (client namespace)
    ↓
Retrieve Top-K Chunks
    ↓
Build Context + System Prompt
    ↓
Generate Response (OpenAI GPT-4o-mini)
    ↓
Return Response + Sources
```

### API Endpoint
**POST** `/api/mintagent/chat`

**Request:**
```json
{
  "client_slug": "a-perfect-promotion",
  "messages": [
    {"role": "user", "content": "What does this company do?"}
  ],
  "top_k": 5,
  "model": "gpt-4o-mini"
}
```

**Response:**
```json
{
  "response": "A Perfect Promotion specializes in...",
  "sources": [
    {
      "doc_id": "a-perfect-promotion_website_...",
      "url": "https://...",
      "title": "About Us",
      "content_type": "homepage",
      "score": 0.85,
      "chunk_index": 0
    }
  ],
  "namespace": "a-perfect-promotion"
}
```

### Multi-turn Conversations
The API supports conversation history:
```json
{
  "messages": [
    {"role": "user", "content": "What products do you offer?"},
    {"role": "assistant", "content": "We offer promotional products..."},
    {"role": "user", "content": "How much do they cost?"}
  ]
}
```

---

## Usage

### 1. Ingest a New Client

**Via Backend API:**
```bash
curl -X POST http://localhost:8000/api/mintagent/create \
  -H "Content-Type: application/json" \
  -d '{
    "clientSlug": "new-client",
    "url": "https://newclient.com",
    "limit": 500,
    "maxDepth": 3
  }'
```

**Via Python Script:**
```bash
python backend/scripts/ingest_to_supabase.py --client new-client
```

### 2. Chat with a Client's Chatbot

**Via Backend API:**
```bash
curl -X POST http://localhost:8000/api/mintagent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "client_slug": "new-client",
    "messages": [
      {"role": "user", "content": "Tell me about your services"}
    ],
    "top_k": 3
  }'
```

**Via Python:**
```python
import httpx

response = httpx.post("http://localhost:8000/api/mintagent/chat", json={
    "client_slug": "new-client",
    "messages": [{"role": "user", "content": "Hello!"}],
    "top_k": 5
})
print(response.json()["response"])
```

### 3. Test Full Pipeline

```bash
python backend/scripts/test_full_pipeline.py --client a-perfect-promotion
```

---

## Key Features

✅ **Automatic Upserting**: Always overwrites existing data, no duplicates
✅ **Namespace Isolation**: Each client's data is isolated in Pinecone
✅ **Local Backup**: Failed uploads saved locally for recovery
✅ **Rich Metadata**: Full document context preserved in vectors
✅ **Multi-turn Chat**: Supports conversation history
✅ **Source Citations**: Returns relevant documents with scores
✅ **Keyword Enrichment**: Automatic keyword extraction
✅ **Content Categorization**: LLM-based content type detection

---

## Monitoring & Debugging

### Check Supabase Storage
```python
from app.clients.supabase_agent_storage_client import SupabaseAgentStorageClient
client = SupabaseAgentStorageClient()
files = client.list_objects("client-data-sources", prefix="client-slug/website")
```

### Check Pinecone Namespace
```python
from pinecone import Pinecone
pc = Pinecone(api_key="...")
index = pc.Index("sb-knowledge-bases")
stats = index.describe_index_stats()
print(stats.namespaces.get("client-slug"))
```

### View Logs
```bash
# Backend logs show all operations
tail -f backend/logs/mintagent.log
```

---

## Configuration

### Required Environment Variables

```bash
# Supabase
SUPABASE_AGENT_URL=https://xxx.supabase.co
SUPABASE_AGENT_KEY=eyJhbGc...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc... # For bucket creation

# Pinecone
PINECONE_API_KEY=pcsk_...

# OpenAI
OPENAI_API_KEY=sk-proj-...

# Firecrawl
FIRECRAWL_API_KEY=fc-...

# Google Drive (optional)
GOOGLE_SERVICE_ACCOUNT_JSON={"type": "service_account", ...}
```

---

## Future Enhancements

- [ ] Streaming chat responses
- [ ] Custom system prompts per client
- [ ] Citation highlighting in responses
- [ ] Metadata filtering in queries
- [ ] Batch client processing
- [ ] Admin dashboard for chatbot management
- [ ] Usage analytics per client
- [ ] Fine-tune embedding models per vertical

---

## Troubleshooting

### Issue: Chat returns no sources
**Solution**: Ensure namespace exists in Pinecone and has vectors
```python
python backend/scripts/upsert_to_pinecone.py --client client-slug
```

### Issue: Supabase upload fails
**Solution**: Check bucket exists and RLS policies allow inserts
```sql
-- Create bucket if missing
INSERT INTO storage.buckets (id, name, public) 
VALUES ('client-data-sources', 'client-data-sources', false);

-- Add RLS policies (see backend/scripts/BUCKET_CREATION.md)
```

### Issue: Embeddings dimension mismatch
**Solution**: Ensure EMBEDDING_DIMENSIONS = 1024 in create.py

---

## Support

For issues or questions:
1. Check logs: `backend/logs/mintagent.log`
2. Run test script: `python backend/scripts/test_full_pipeline.py`
3. Verify env vars are set correctly

---

**Last Updated**: 2025-12-30
**Version**: 1.0.0

