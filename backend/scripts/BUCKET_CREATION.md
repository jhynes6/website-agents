# Supabase Storage Structure

## Overview

All client data is stored in a **single bucket** called `client-data-sources`. Each client has their own folder within this bucket.

## Bucket Structure

```
client-data-sources/
  ├── client-slug-1/
  │   ├── website/
  │   │   └── [markdown files from website scraping]
  │   ├── drive/
  │   │   └── [markdown files from Google Drive]
  │   ├── intake_form/
  │   │   └── [intake form documents]
  │   └── metadata.json
  ├── client-slug-2/
  │   ├── website/
  │   ├── drive/
  │   ├── intake_form/
  │   └── metadata.json
  └── ...
```

## Benefits of Single Bucket

- **Simplified Management**: Only need to manage RLS policies for one bucket
- **Easier Scaling**: No per-client bucket creation needed
- **Better Organization**: Clear folder hierarchy
- **Consistent Structure**: All clients follow the same pattern

## One-Time Setup

The bucket should already exist, but if you need to create it:

```sql
INSERT INTO storage.buckets (id, name, public, file_size_limit) 
VALUES ('client-data-sources', 'client-data-sources', false, 104857600) 
ON CONFLICT (id) DO NOTHING;
```

## Verification

The ingestion script automatically verifies the bucket exists before processing. If you have the `SUPABASE_SERVICE_ROLE_KEY` in your `.env` file, the script will confirm the bucket is ready.

## Adding New Clients

When you ingest a new client:
1. The script automatically creates the client folder structure
2. Documents are uploaded to `{client-slug}/website/`, `{client-slug}/drive/`, etc.
3. `metadata.json` is created at `{client-slug}/metadata.json`

No manual setup required!

