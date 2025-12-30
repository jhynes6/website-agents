#!/usr/bin/env python3
"""
Upsert documents from Supabase Storage to Pinecone.

Each client folder becomes a namespace in the 'sb-knowledge-bases' index.
Documents are chunked and vectorized before upserting.

Usage:
    python upsert_to_pinecone.py --client a-perfect-promotion  # Single client
    python upsert_to_pinecone.py --all  # All clients
    python upsert_to_pinecone.py --dry-run --client test-client  # Preview only
"""
import sys
import os
import json
import httpx
import hashlib
import yaml
from urllib.parse import quote
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import asyncio

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

# Load environment
env_path = backend_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)

from app.config import get_settings
from app.clients.pinecone_client import pinecone_kb_client  # noqa: E402
from app.clients.supabase_storage_client import SupabaseStorageClient  # noqa: E402


# Constants
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200
SHARED_BUCKET = "client-data-sources"


def _resolve_supabase_storage_key(settings) -> str:
    """
    Resolve the API key to use for Supabase Storage operations.

    Prefer a service-role key if present (needed for admin-like operations and
    avoids RLS/policy surprises). Fall back to SUPABASE_AGENT_KEY.

    We intentionally read SUPABASE_AGENT_SERVICE_ROLE_KEY directly since
    backend/app/config.py does not currently model it.
    """
    # Highest priority: explicit "agent service role" env var (user-provided naming)
    v = (os.getenv("SUPABASE_AGENT_SERVICE_ROLE_KEY") or "").strip()
    if v:
        return v
    # Next: standard Supabase service role env var
    v = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if v:
        return v
    # Fall back: configured agent key
    return str(getattr(settings, "supabase_agent_key", "") or "").strip()


def _list_bucket_ids(*, settings) -> List[str]:
    """
    List Supabase Storage buckets (requires service role in most projects).
    """
    api_key = _resolve_supabase_storage_key(settings)
    client = SupabaseStorageClient(project_url=str(settings.supabase_agent_url or ""), service_role_key=api_key)
    buckets = client.list_buckets()
    ids: List[str] = []
    for b in buckets:
        if not isinstance(b, dict):
            continue
        bid = str(b.get("id") or b.get("name") or "").strip()
        if bid:
            ids.append(bid)
    return ids


def _is_probably_client_bucket(bucket_id: str) -> bool:
    """
    Heuristic filter so we don't accidentally process internal/testing buckets.
    """
    bid = (bucket_id or "").strip()
    if not bid:
        return False
    if bid.startswith("__"):
        return False
    # shared bucket (not a client slug)
    if bid == SHARED_BUCKET:
        return False
    return True


def _list_client_slugs_from_shared_bucket(*, settings) -> List[str]:
    """
    Legacy/shared storage model:
      - single bucket: client-data-sources
      - top-level "folders" (prefixes) are client slugs
    """
    api_key = _resolve_supabase_storage_key(settings)
    client = SupabaseStorageClient(project_url=str(settings.supabase_agent_url or ""), service_role_key=api_key)
    try:
        items = client.list_objects(SHARED_BUCKET, prefix="", limit=1000, offset=0, sort_by={"column": "name", "order": "asc"})
    except Exception:
        return []

    slugs: List[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("metadata") is not None:
            continue
        name = str(item.get("name") or "").strip().rstrip("/")
        if not name or name.startswith(".") or name.startswith("__"):
            continue
        slugs.append(name)
    return sorted(set(slugs))


def _detect_storage_mode(*, settings) -> tuple[str, List[str]]:
    """
    Returns (mode, client_slugs)

    mode:
      - "bucket_per_client": each client slug is a bucket
      - "shared_bucket": one bucket, client slugs are top-level prefixes
    """
    bucket_ids = _list_bucket_ids(settings=settings)
    client_buckets = [b for b in bucket_ids if _is_probably_client_bucket(b)]
    if client_buckets:
        client_buckets.sort()
        return "bucket_per_client", client_buckets

    # Fallback: shared bucket model
    slugs = _list_client_slugs_from_shared_bucket(settings=settings)
    return "shared_bucket", slugs


async def list_clients_from_storage() -> List[str]:
    """
    List client slugs for `--all`.

    This repo's current Storage model is **bucket-per-client** where:
      - bucket name == client_slug
      - object prefixes include: website/, drive/, intake_form/

    We therefore list buckets and treat each client bucket as a slug.
    """
    settings = get_settings()
    if not settings.supabase_agent_url or not settings.supabase_agent_key:
        raise RuntimeError("SUPABASE_AGENT_URL and SUPABASE_AGENT_KEY must be configured to use --all")

    mode, slugs = _detect_storage_mode(settings=settings)
    print(f"🧭 Storage mode: {mode} (clients discovered: {len(slugs)})")
    return slugs


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    
    return chunks


def parse_markdown_frontmatter(content: bytes) -> tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter and markdown content."""
    try:
        text = content.decode('utf-8')
        
        if text.startswith('---'):
            # Find the closing ---
            parts = text.split('---', 2)
            if len(parts) >= 3:
                frontmatter_str = parts[1]
                body = parts[2].strip()
                
                # Parse YAML
                metadata = yaml.safe_load(frontmatter_str) or {}
                return metadata, body
        
        # No frontmatter
        return {}, text
    except Exception as e:
        print(f"Error parsing frontmatter: {e}")
        return {}, text if isinstance(text, str) else content.decode('utf-8', errors='ignore')


def generate_chunk_id(client_slug: str, doc_id: str, chunk_index: int) -> str:
    """Generate unique ID for a chunk."""
    base = f"{client_slug}_{doc_id}_{chunk_index}"
    return hashlib.md5(base.encode()).hexdigest()


async def download_file_from_storage(bucket: str, path: str) -> Optional[bytes]:
    """Download a file from Supabase Storage."""
    settings = get_settings()
    
    if not settings.supabase_agent_url or not settings.supabase_agent_key:
        print("❌ Supabase credentials not configured")
        return None
    
    BUCKET_NAME = bucket
    base_url = str(settings.supabase_agent_url).rstrip("/")
    storage_url = f"{base_url}/storage/v1"
    api_key = _resolve_supabase_storage_key(settings)
    
    # Full path in bucket
    full_path = path.lstrip("/")
    
    headers = {"Authorization": f"Bearer {api_key}", "apikey": api_key}
    
    # Must URL-encode segments but preserve slashes
    download_url = f"{storage_url}/object/{BUCKET_NAME}/{quote(full_path, safe='/')}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(download_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.content
            else:
                print(f"❌ Failed to download {full_path}: {response.status_code}")
                return None
    except Exception as e:
        print(f"❌ Error downloading {full_path}: {e}")
        return None


async def list_client_files(*, bucket: str, client_slug: str, prefix_mode: str) -> List[tuple[str, Dict[str, Any]]]:
    """List all markdown files for a client from all subfolders.
    
    Returns list of tuples: (subfolder, file_info)
    """
    settings = get_settings()
    
    BUCKET_NAME = bucket
    base_url = str(settings.supabase_agent_url).rstrip("/")
    storage_url = f"{base_url}/storage/v1"
    api_key = _resolve_supabase_storage_key(settings)
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "apikey": api_key,
    }
    
    list_url = f"{storage_url}/object/list/{BUCKET_NAME}"
    all_files = []
    
    # List files from each subfolder (website, drive, intake_form)
    for subfolder in ["website", "drive", "intake_form"]:
        
        if prefix_mode == "bucket_per_client":
            prefix = f"{subfolder}"
        
        else:
            # shared bucket: client_slug/subfolder
            prefix = f"{client_slug}/{subfolder}"
        
        payload = {
            "limit": 1000,
            "offset": 0,
            "prefix": prefix,
            "search": "",
            "sortBy": {
                "column": "name",
                "order": "asc"
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(list_url, headers=headers, json=payload, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Filter for .md files only (exclude folders and .keep files)
                    md_files = [
                        (subfolder, item) for item in data 
                        if item.get("metadata") is not None 
                        and item.get("name", "").endswith(".md")
                        and not item.get("name", "").endswith("/.keep")
                    ]
                    
                    all_files.extend(md_files)
                else:
                    print(f"❌ Failed to list {subfolder}: {response.status_code}")
        except Exception as e:
            print(f"❌ Error listing {subfolder}: {e}")
    
    return all_files


async def process_client(client_slug: str, dry_run: bool = False) -> Dict[str, Any]:
    """Process all documents for a client and upsert to Pinecone."""
    print(f"\n{'[DRY RUN] ' if dry_run else ''}📁 Processing client: {client_slug}")
    print("=" * 80)
    
    settings = get_settings()
    
    # Pinecone (Records API + integrated embedding) is handled by pinecone_kb_client.
    if not dry_run and not settings.pinecone_api_key:
            print("❌ PINECONE_API_KEY not configured")
            return {"success": False, "error": "Missing Pinecone API key"}
        
    # Determine storage model for this run.
    # Prefer bucket-per-client if a bucket exists; otherwise fall back to shared bucket.
    mode, _ = _detect_storage_mode(settings=settings)
    if mode == "bucket_per_client":
        bucket = client_slug
        prefix_mode = "bucket_per_client"
    else:
        bucket = SHARED_BUCKET
        prefix_mode = "shared_bucket"
    
    # List all files for client
    files = await list_client_files(bucket=bucket, client_slug=client_slug, prefix_mode=prefix_mode)
    print(f"📄 Found {len(files)} markdown files")
    
    if not files:
        return {"success": False, "files_processed": 0, "chunks_created": 0}
    
    total_files = 0
    docs_for_upsert: List[Dict[str, Any]] = []
    
    for subfolder, file_info in files:
        file_name = file_info["name"]  # Filename only, relative to prefix
        file_path = f"{subfolder}/{file_name}"  # Full path relative to client folder
        
        print(f"\n  Processing: {file_path}")
        
        # Download file
        if prefix_mode == "bucket_per_client":
            object_path = file_path
        else:
            object_path = f"{client_slug}/{file_path}"
        content_bytes = await download_file_from_storage(bucket, object_path)
        if not content_bytes:
            print(f"    ⚠️  Skipped (download failed)")
            continue
        
        # Parse frontmatter
        metadata, body = parse_markdown_frontmatter(content_bytes)
        
        if not body.strip():
            print(f"    ⚠️  Skipped (empty content)")
            continue
        
        if dry_run:
            total_files += 1
            continue
        
        # Normalize into the document shape expected by pinecone_kb_client.upsert_documents()
        kws = metadata.get("keywords")
        if isinstance(kws, str) and kws.strip():
            kws_list = [k.strip().lower() for k in kws.split(",") if k.strip()]
        elif isinstance(kws, list):
            kws_list = [str(k).strip().lower() for k in kws if str(k).strip()]
        else:
            kws_list = []

        docs_for_upsert.append(
            {
                "title": metadata.get("title") or file_name,
                "url": metadata.get("url") or "",
                "content_type": metadata.get("content_type") or "",
                "document_source": metadata.get("document_source") or subfolder,
                "keywords": kws_list,
                "markdown": body,
                # Stable identifier for record IDs
                "file_key": f"{client_slug}/{file_path}",
            }
        )

        total_files += 1
        
    if dry_run:
        print("\n" + "=" * 80)
        print(f"✅ [DRY RUN] Completed: {client_slug}")
        print(f"   Files processed: {total_files}")
        print(f"   Documents prepared: {len(docs_for_upsert)}")
        return {"success": True, "client_slug": client_slug, "files_processed": total_files, "records_upserted": 0}

    print(f"\n🔼 Upserting to Pinecone (index: {settings.pinecone_kb_index_name}, namespace: {client_slug})")
    upsert_res = pinecone_kb_client.upsert_documents(client_slug=client_slug, documents=docs_for_upsert)
    
    print("\n" + "=" * 80)
    print(f"✅ Completed: {client_slug}")
    print(f"   Files processed: {total_files}")
    print(f"   Records upserted: {int(upsert_res.get('records_upserted') or 0)}")
    
    return {
        "success": True,
        "client_slug": client_slug,
        "files_processed": total_files,
        "records_upserted": int(upsert_res.get("records_upserted") or 0),
        "index": upsert_res.get("index"),
        "namespace": upsert_res.get("namespace"),
    }


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Upsert documents from Supabase Storage to Pinecone",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--client",
        type=str,
        help="Process specific client by slug"
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all clients"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without upserting to Pinecone"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="When using --all, stop after this many clients",
    )

    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="When using --all, keep going even if one client fails",
    )
    
    args = parser.parse_args()
    
    if not args.client and not args.all:
        print("❌ Error: Specify --client <slug> or --all")
        parser.print_help()
        return
    
    if args.client:
        result = await process_client(args.client, dry_run=args.dry_run)
        print(f"\n📊 Result: {json.dumps(result, indent=2)}")
    elif args.all:
        print("Processing all clients (from Supabase Storage)...")
        slugs = await list_clients_from_storage()
        if args.limit is not None:
            slugs = slugs[: max(0, int(args.limit))]

        print(f"📁 Found {len(slugs)} clients")

        results: List[Dict[str, Any]] = []
        ok = 0
        failed = 0
        for i, slug in enumerate(slugs, 1):
            print(f"\n[{i}/{len(slugs)}] {slug}")
            try:
                r = await process_client(slug, dry_run=args.dry_run)
                results.append(r)
                ok += 1 if r.get("success") else 0
                failed += 0 if r.get("success") else 1
            except Exception as e:
                failed += 1
                results.append({"success": False, "client_slug": slug, "error": str(e)})
                print(f"❌ Failed: {slug}: {e}")
                if not args.continue_on_error:
                    break

        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total attempted: {len(results)}")
        print(f"Successful: {ok}")
        print(f"Failed: {failed}")
        print("=" * 80)
        # Print JSON summary for easy piping/logging
        print(json.dumps({"ok": ok, "failed": failed, "results": results}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

