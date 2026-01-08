# Chunking Strategy A/B Testing (Pinecone KB)

This repo supports **opt-in A/B testing** of chunking strategies used when upserting into the Pinecone KB index (`sb-knowledge-bases`).

## What exists today

- **Default chunker (baseline)**: character windowing  
  `char:1200:200` (1200 chars per chunk, 200 char overlap)

- **Semantic chunker (opt-in)**: markdown section-aware chunking  
  `md_semantic_v1` (or with params: `md_semantic_v1:w350:m550:o80`)

Chunker selection is passed into `pinecone_kb_client.upsert_documents(..., chunker_name=...)` and stored per-chunk in Pinecone metadata as `chunker`.

## Why you must A/B carefully (avoid “mixed chunkers”)

**Important:** changing chunkers and re-upserting without clearing the namespace will generally **mix old + new chunks** in the same namespace, because record IDs are derived from chunk contents and indices. Different chunking strategies create different chunk boundaries → different IDs → old records will remain.

For a clean A/B test, do one of:

- **Option A (recommended):** clear the Pinecone namespace between runs (destructive to that client namespace).
- **Option B:** A/B in separate namespaces by using separate `clientSlug`s (copy the Storage folder to a new slug).

## New recommended A/B — Separate namespaces (no destructive deletes)

Instead of clearing namespaces (destructive), we now support A/B testing by writing to a second namespace:

- **Baseline namespace**: `{clientSlug}`
- **Semantic namespace**: `{clientSlug}-semantic`

Both variants read from the **same Supabase Storage folder**:
- `client-data-sources/{clientSlug}/...`

### Index strategy (two options)

- **Option 1 (recommended): one index, two namespaces**
  - index: `sb-knowledge-bases`
  - namespaces: `{clientSlug}` and `{clientSlug}-semantic`

- **Option 2: two indexes**
  - baseline index: `sb-knowledge-bases`
  - semantic index: `sb-knowledge-bases-semantic`
  - namespaces: `{clientSlug}` and `{clientSlug}-semantic`

The UI “Semantic embeddings” checkbox controls this behavior for UI ingests.

### 1) Pick a test client

Example:
- `CLIENT_SLUG=galactic-fed`

### 2) Baseline run (char chunking)

Force baseline chunking:

```bash
python backend/scripts/upsert_to_pinecone.py --client galactic-fed --chunker "char:1200:200"
```

### 3) Evaluate baseline

Use the UI:
- `/dashboard?clientSlug=galactic-fed`

Run a fixed list of queries and record:
- answer quality
- source relevance
- hallucination rate
- whether sources align to natural sections (FAQ items, headings, etc.)

### (Legacy) Clear the namespace (destructive)

Use Pinecone’s “delete all records in a namespace” operation (per Pinecone docs).

Create a temporary script or run a one-off in a Python REPL:

```python
from pinecone import Pinecone
import os

pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
desc = pc.describe_index("sb-knowledge-bases")
index = pc.Index(host=desc.host)

# DANGER: deletes *all* records for this clientSlug namespace
index.delete(delete_all=True, namespace="galactic-fed")
```

### 5) Variant run (semantic chunking)

```bash
python backend/scripts/upsert_to_pinecone.py --client galactic-fed --chunker "md_semantic_v1"
```

Or with explicit parameters (recommended starting point):

```bash
python backend/scripts/upsert_to_pinecone.py --client galactic-fed --chunker "md_semantic_v1:w350:m550:o80"
```

### 6) Evaluate variant

Repeat the same query set and compare.

## Option B — A/B via two client slugs (no destructive deletes)

If you don’t want to delete anything from an existing client namespace:

1. Copy the Storage folder:
   - from: `client-data-sources/{CLIENT_SLUG}/...`
   - to:   `client-data-sources/{CLIENT_SLUG}-semantic/...`
2. Upsert each slug with a different chunker:

```bash
python backend/scripts/upsert_to_pinecone.py --client galactic-fed --chunker "char:1200:200"
python backend/scripts/upsert_to_pinecone.py --client galactic-fed-semantic --chunker "md_semantic_v1"
```

Then compare dashboards:
- `/dashboard?clientSlug=galactic-fed`
- `/dashboard?clientSlug=galactic-fed-semantic`

## Per-client default (“auto” mode)

We persist a per-client chunker choice in Supabase Storage:

- bucket: `client-data-sources`
- key: `{clientSlug}/metadata.json`
- field: `"chunker": "..."` (string)

The `upsert_to_pinecone.py` script supports:

- `--chunker auto` (default): reads `chunker` from `metadata.json`
- `--chunker <value>`: forces a chunker for the run

Examples:

```bash
# Reads `client-data-sources/galactic-fed/metadata.json` -> chunker field
python backend/scripts/upsert_to_pinecone.py --client galactic-fed --chunker auto

# Forces semantic regardless of metadata.json
python backend/scripts/upsert_to_pinecone.py --client galactic-fed --chunker md_semantic_v1
```

## Chunker strings supported

- **Baseline**
  - `char:1200:200` (default behavior if nothing else is specified)
  - `char` / `char_v1` (alias)

- **Semantic markdown**
  - `md_semantic_v1`
  - `md_semantic_v1:w350:m550:o80`
    - `w###` = target words per chunk
    - `m###` = max words per chunk
    - `o###` = overlap words

## Where to change the implementation

- Chunker implementation + selection:
  - `backend/app/clients/pinecone_client.py` (`PineconeKBClient.upsert_documents()`)

- Bulk upsert CLI:
  - `backend/scripts/upsert_to_pinecone.py` (`--chunker`, `auto` reads metadata.json)

- UI ingestion (create) path:
  - `backend/app/routes/create.py`
    - accepts `chunker` in request payload
    - writes `chunker` into `client-data-sources/{clientSlug}/metadata.json`
    - vectorization reads `chunker` back from metadata.json


