import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException

from ..config import get_settings
from ..clients.supabase_agents_db_client import SupabaseAgentsDbClient

router = APIRouter()
logger = logging.getLogger(__name__)

INDEXES_BUCKET = "client-data-sources"
INDEXES_SUMMARY_KEY = "__reports/indexes.json"
INDEXES_CACHE_TTL_S = 30.0

# Simple in-process cache to keep the /indexes page snappy during navigation/reloads.
# (Dev server + LAN usage can trigger frequent reloads.)
_indexes_cache: Dict[str, Any] = {"ts": 0.0, "payload": None}


def _normalize_client_slug(value: str) -> str:
    return (value or "").strip().lower().replace(" ", "-").replace("_", "-")


def _supabase_storage_client():
    """
    Storage client for server-side reads (service role preferred).
    """
    from ..clients.supabase_storage_client import SupabaseStorageClient

    return SupabaseStorageClient()


def _list_client_slugs_from_storage() -> List[str]:
    """
    Preferred source for the UI indexes list: Supabase Storage.

    Supports the shared-bucket layout:
      - bucket: client-data-sources
      - prefixes: {clientSlug}/<metadata files>
    """
    c = _supabase_storage_client()
    bucket = INDEXES_BUCKET
    try:
        items = c.list_objects(bucket, prefix="", limit=1000, offset=0, sort_by={"column": "name", "order": "asc"})
    except Exception:
        return []

    slugs: List[str] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        if it.get("metadata") is not None:
            continue
        name = str(it.get("name") or "").strip().rstrip("/")
        if not name or name.startswith(".") or name.startswith("__"):
            continue
        slugs.append(name)
    # De-dupe and sort
    return sorted(set(slugs))


def _index_payload_from_metadata(*, client_slug: str, meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert Supabase `metadata.json` into the UI's index card shape.
    """
    website_url = str(meta.get("website_url") or meta.get("websiteUrl") or "") or f"https://{client_slug}.com"
    created_at = (
        meta.get("createdAt")
        or meta.get("created_at")
        or meta.get("created")
        or datetime.now(timezone.utc).isoformat()
    )
    website_docs = meta.get("website_docs") or meta.get("websiteDocs") or {}
    pages = int((website_docs or {}).get("total") or 0)
    ui_meta = meta.get("metadata") or {}
    if not isinstance(ui_meta, dict):
        ui_meta = {}

    return {
        "url": website_url,
        "clientSlug": client_slug,
        "namespace": client_slug,  # back-compat
        "pagesCrawled": pages,
        "pages": pages,
        # For this Supabase-backed view, chunks/vectors are not required.
        # (Stats page pulls Pinecone stats separately.)
        "chunks": 0,
        "createdAt": created_at,
        "metadata": ui_meta,
        "agent": None,
        "agents": {},
    }


async def _try_load_indexes_summary(storage) -> Optional[Dict[str, Any]]:
    """
    Fast path: load a single aggregated indexes file from Storage.
    Returns the response payload shape for the UI: {"indexes": [...]}
    """
    try:
        data = await asyncio.to_thread(storage.download_json, INDEXES_BUCKET, INDEXES_SUMMARY_KEY)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    indexes = data.get("indexes")
    if not isinstance(indexes, list):
        return None
    # Pass through (already in UI payload shape).
    return {"indexes": indexes}


async def _build_indexes_from_storage(storage, slugs: List[str]) -> List[Dict[str, Any]]:
    """
    Build indexes by downloading each client's metadata files.
    Prefer pinecone_namespace_metadata.json for UI display, fallback to supabase_storage_metadata.json,
    then legacy metadata.json.
    Uses concurrency to avoid N serial HTTP roundtrips.
    """
    sem = asyncio.Semaphore(25)

    async def load_one(slug: str) -> Optional[Dict[str, Any]]:
        async with sem:
            try:
                meta = None
                supabase_meta = None
                for key in (
                    f"{slug}/pinecone_namespace_metadata.json",
                    f"{slug}/supabase_storage_metadata.json",
                    f"{slug}/metadata.json",
                ):
                    try:
                        meta = await asyncio.to_thread(storage.download_json, INDEXES_BUCKET, key)
                        if isinstance(meta, dict):
                            break
                    except Exception:
                        meta = None
                        continue
                if not isinstance(meta, dict):
                    return None

                # Prefer canonical client_name from DB, but keep UI card title stable as client_slug.
                try:
                    name = (getattr(_build_indexes_from_storage, "_client_names", {}) or {}).get(slug)
                    if isinstance(name, str) and name.strip():
                        meta["client_name"] = name.strip()
                except Exception:
                    pass

                # Force the card title to be the slug (requested).
                try:
                    ui_meta = meta.get("metadata")
                    if not isinstance(ui_meta, dict):
                        ui_meta = {}
                        meta["metadata"] = ui_meta
                    ui_meta["title"] = slug
                except Exception:
                    pass

                # If we're using Pinecone metadata for display, merge favicon from Supabase metadata if missing.
                try:
                    ui_meta = meta.get("metadata") if isinstance(meta, dict) else None
                    if not (isinstance(ui_meta, dict) and ui_meta.get("favicon")):
                        supabase_meta = await asyncio.to_thread(storage.download_json, INDEXES_BUCKET, f"{slug}/supabase_storage_metadata.json")
                        sb_ui = supabase_meta.get("metadata") if isinstance(supabase_meta, dict) else None
                        if isinstance(sb_ui, dict) and sb_ui.get("favicon"):
                            if not isinstance(ui_meta, dict):
                                ui_meta = {}
                                meta["metadata"] = ui_meta
                            ui_meta["favicon"] = sb_ui.get("favicon")
                except Exception:
                    pass

                return _index_payload_from_metadata(client_slug=slug, meta=meta)
            except Exception:
                return None

    results = await asyncio.gather(*[load_one(s) for s in slugs])
    out = [r for r in results if isinstance(r, dict)]
    out.sort(key=lambda x: x.get("createdAt") or "", reverse=True)
    return out


async def _write_indexes_summary(storage, indexes: List[Dict[str, Any]]) -> None:
    """
    Best-effort write of the aggregated indexes file (does not affect response).
    """
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "indexes": indexes,
    }
    try:
        await asyncio.to_thread(
            storage.upload_json,
            bucket=INDEXES_BUCKET,
            path=INDEXES_SUMMARY_KEY,
            payload=payload,
            upsert=True,
        )
    except Exception:
        return


async def _delete_storage_prefix(*, storage, bucket: str, prefix: str) -> Dict[str, Any]:
    """
    Delete all objects under a prefix in a bucket.
    Supabase "folders" are prefixes; there is no separate folder delete.
    """
    p = (prefix or "").strip().lstrip("/").rstrip("/")
    if not p:
        raise ValueError("prefix required")

    deleted = 0
    listed_files = 0
    visited_prefixes = 0

    # Supabase list_objects often returns "folder" entries with metadata=None (not recursive).
    # We therefore traverse prefixes breadth-first and delete only file objects.
    queue: List[str] = [p]

    while queue:
        current = queue.pop(0).strip().rstrip("/")
        visited_prefixes += 1
        list_prefix = f"{current}/"

        # We intentionally do not paginate here; for our expected sizes (per-client folders),
        # limit=1000 is sufficient and keeps this simpler. If needed later, add pagination.
        items = await asyncio.to_thread(storage.list_objects, bucket, prefix=list_prefix, limit=1000, offset=0)
        if not items:
            continue

        file_paths: List[str] = []
        for it in items:
            if not isinstance(it, dict):
                continue

            name = str(it.get("name") or "").strip().lstrip("/").rstrip("/")
            if not name:
                continue

            meta = it.get("metadata")

            # Folder entry (metadata=None): enqueue deeper prefix.
            if meta is None:
                # If API returned an already-prefixed name, use it; else join to current.
                child = name if name.startswith(f"{current}/") else f"{current}/{name}"
                child = child.strip().rstrip("/")
                if child and child not in queue:
                    queue.append(child)
                continue

            # File entry (metadata is a dict): delete the full object key.
            listed_files += 1
            full = name if name.startswith(f"{current}/") else f"{current}/{name}"
            file_paths.append(full)

        if file_paths:
            await asyncio.to_thread(storage.delete_objects, bucket, file_paths)
            deleted += len(file_paths)

    return {
        "bucket": bucket,
        "prefix": f"{p}/",
        "visited_prefixes": visited_prefixes,
        "listed_files": listed_files,
        "deleted_objects": deleted,
    }


async def _delete_pinecone_namespace(*, index_name: str, namespace: str) -> Dict[str, Any]:
    """
    Delete a Pinecone namespace (serverless) or, if not supported, delete all records in the namespace.
    """
    settings = get_settings()
    if not settings.pinecone_api_key:
        return {"deleted": False, "reason": "PINECONE_API_KEY not configured"}

    from pinecone import Pinecone

    pc = Pinecone(api_key=settings.pinecone_api_key)
    desc = pc.describe_index(index_name)
    idx = pc.Index(host=desc.host)

    try:
        idx.delete_namespace(namespace=namespace)
        return {"deleted": True, "method": "delete_namespace", "index": index_name, "namespace": namespace}
    except Exception:
        pass

    try:
        idx.delete(delete_all=True, namespace=namespace)
        return {"deleted": True, "method": "delete_all", "index": index_name, "namespace": namespace}
    except Exception as e:
        return {"deleted": False, "error": str(e), "index": index_name, "namespace": namespace}


def _open_pinecone_index(index_name: str):
    """
    Return a Pinecone Index handle for the KB index (Records API + stats).
    """
    from pinecone import Pinecone  # local dependency pinned in backend/requirements.txt

    settings = get_settings()
    if not settings.pinecone_api_key:
        raise HTTPException(status_code=500, detail="PINECONE_API_KEY not configured")
    pc = Pinecone(api_key=settings.pinecone_api_key)
    desc = pc.describe_index(index_name)
    return pc.Index(host=desc.host)


def _pinecone_fetch_report_doc(*, index_name: str, namespace: str, doc_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a report doc from Pinecone by ID and parse JSON from the stored `text` field.
    Returns None if missing.
    """
    from pinecone import Pinecone

    settings = get_settings()
    if not settings.pinecone_api_key:
        return None

    pc = Pinecone(api_key=settings.pinecone_api_key)
    desc = pc.describe_index(index_name)
    idx = pc.Index(host=desc.host)

    resp = idx.fetch(ids=[doc_id], namespace=namespace)
    vec = resp.vectors.get(doc_id) if hasattr(resp, "vectors") else None
    if not vec:
        return None
    raw = (vec.metadata or {}).get("text") or ""
    try:
        return json.loads(raw)
    except Exception:
        return None


def _build_index_payload(
    *,
    client_slug: str,
    vector_count: int,
    client_report: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    # Metadata defaults
    metadata: Dict[str, Any] = {
        "title": client_slug,
        "description": f"Pinecone namespace: {client_slug}",
        "favicon": None,
        "indexName": client_slug,
    }

    created_at = None
    pages_crawled = 0

    # Prefer the canonical report
    if isinstance(client_report, dict):
        ui = client_report.get("ui") or {}
        if ui.get("title"):
            metadata["title"] = ui["title"]
        if ui.get("description"):
            metadata["description"] = ui["description"]
        if ui.get("favicon"):
            metadata["favicon"] = ui["favicon"]
        if ui.get("ogImage"):
            metadata["ogImage"] = ui["ogImage"]
        if ui.get("indexName"):
            metadata["indexName"] = ui["indexName"]

        spaces_info = client_report.get("spaces") or {}
        pages_crawled = int(spaces_info.get("total_files") or 0)

        ts = client_report.get("timestamps") or {}
        created_at = ts.get("createdAt") or ts.get("created_at") or created_at

    # Reasonable fallback
    if not created_at:
        created_at = datetime.now(timezone.utc).isoformat()

    # NOTE: This product is now Pinecone-backed; "chunks" maps to vectors in the namespace.
    return {
        "url": f"https://{client_slug}.com",
        "clientSlug": client_slug,
        "namespace": client_slug,  # back-compat
        "pagesCrawled": pages_crawled,
        "pages": pages_crawled,
        "chunks": int(vector_count),
        "createdAt": created_at,
        "metadata": metadata,
        # DO agent fields (deprecated for this Pinecone-first UI path)
        "agent": None,
        "agents": {},
    }


@router.get("/indexes")
async def list_indexes(
    client_slug: Optional[str] = None, 
    clientSlug: Optional[str] = None,
    namespace: Optional[str] = None,
    refresh: bool = False,
) -> Dict[str, Any]:
    """
    List all indexes for the UI.

    **Primary source**: Supabase Storage metadata per client (fast, aligned with ingestion).
      - pinecone_namespace_metadata.json (preferred for display)
      - supabase_storage_metadata.json (fallback)
      - metadata.json (legacy fallback)
    **Fallback**: Pinecone namespace stats (if storage isn't available).
    Accepts client_slug (preferred), clientSlug (JS compat), or namespace (deprecated).
    """
    settings = get_settings()
    
    # Handle aliases
    target_slug = _normalize_client_slug(client_slug or clientSlug or namespace or "")
    target_slug = target_slug or None
    # --- Supabase Storage path (preferred) ---
    try:
        storage = _supabase_storage_client()
        bucket = INDEXES_BUCKET

        # Build client_name map once per request (used to override card titles).
        client_names: Dict[str, str] = {}
        try:
            db = SupabaseAgentsDbClient()
            client_names = await db.get_client_names_map(client_slugs=_list_client_slugs_from_storage())
        except Exception:
            client_names = {}

        def _apply_client_names_to_indexes(payload_indexes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            for idx in payload_indexes:
                if not isinstance(idx, dict):
                    continue
                slug = str(idx.get("clientSlug") or idx.get("client_slug") or idx.get("namespace") or "").strip()
                if not slug:
                    continue
                name = client_names.get(slug)
                if not (isinstance(name, str) and name.strip()):
                    continue
                md = idx.get("metadata")
                if not isinstance(md, dict):
                    md = {}
                    idx["metadata"] = md
                md["title"] = name.strip()
                idx["clientName"] = name.strip()
            return payload_indexes

        # If we're listing all indexes, try cache + aggregated summary first.
        if not target_slug and not refresh:
            now = time.time()
            cached = _indexes_cache.get("payload")
            if cached and (now - float(_indexes_cache.get("ts") or 0.0)) < INDEXES_CACHE_TTL_S:
                # Ensure client_name titles stay current even if cache/summary is stale.
                try:
                    if isinstance(cached, dict) and isinstance(cached.get("indexes"), list):
                        cached["indexes"] = _apply_client_names_to_indexes(cached["indexes"])
                except Exception:
                    pass
                return cached

            summary = await _try_load_indexes_summary(storage)
            if summary:
                try:
                    if isinstance(summary, dict) and isinstance(summary.get("indexes"), list):
                        summary["indexes"] = _apply_client_names_to_indexes(summary["indexes"])
                except Exception:
                    pass
                _indexes_cache["ts"] = now
                _indexes_cache["payload"] = summary
                # Best-effort rewrite summary so future loads are fast + correct.
                try:
                    if isinstance(summary.get("indexes"), list) and summary["indexes"]:
                        asyncio.create_task(_write_indexes_summary(storage, summary["indexes"]))
                except Exception:
                    pass
                return summary

        slugs = _list_client_slugs_from_storage()
        if target_slug:
            slug_map = {s.lower(): s for s in slugs}
            resolved = slug_map.get(target_slug.lower())
            if not resolved:
                raise HTTPException(status_code=404, detail="Client not found in storage")
            target_slug = resolved
            slugs = [resolved]

        # Single client: just load directly (one roundtrip).
        if target_slug:
            try:
                meta = None
                for key in (
                    f"{target_slug}/pinecone_namespace_metadata.json",
                    f"{target_slug}/supabase_storage_metadata.json",
                    f"{target_slug}/metadata.json",
                ):
                    try:
                        meta = await asyncio.to_thread(storage.download_json, bucket, key)
                        if isinstance(meta, dict):
                            break
                    except Exception:
                        meta = None
                        continue
                if not isinstance(meta, dict):
                    raise HTTPException(status_code=404, detail="metadata not found for client")
                # Override card title with DB client_name
                try:
                    name = client_names.get(target_slug)
                    if isinstance(name, str) and name.strip():
                        meta["client_name"] = name.strip()
                        ui_meta = meta.get("metadata")
                        if not isinstance(ui_meta, dict):
                            ui_meta = {}
                            meta["metadata"] = ui_meta
                        ui_meta["title"] = name.strip()
                except Exception:
                    pass
                return {"index": _index_payload_from_metadata(client_slug=target_slug, meta=meta)}
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(status_code=404, detail="metadata not found for client")

        # All clients: parallel load to avoid serial N calls.
        # Hack: attach client_names to the loader without changing public signature too much.
        setattr(_build_indexes_from_storage, "_client_names", client_names)
        results = await _build_indexes_from_storage(storage, slugs)
        if target_slug:
            if not results:
                raise HTTPException(status_code=404, detail="metadata.json not found for client")
            return {"index": results[0]}
        payload = {"indexes": _apply_client_names_to_indexes(results)}
        _indexes_cache["ts"] = time.time()
        _indexes_cache["payload"] = payload
        # Best-effort summary write so subsequent loads are a single Storage read.
        if results:
            asyncio.create_task(_write_indexes_summary(storage, results))
        return payload
    except HTTPException:
        raise
    except Exception:
        # Fall back to Pinecone-backed listing (legacy)
        pass

    # --- Pinecone fallback ---
    kb_index_name = settings.pinecone_kb_index_name
    idx = _open_pinecone_index(kb_index_name)
    stats = idx.describe_index_stats()
    namespaces: Dict[str, Any] = (stats or {}).get("namespaces") or {}

    if target_slug:
        if target_slug not in namespaces:
            raise HTTPException(status_code=404, detail="Namespace not found")
        namespaces = {target_slug: namespaces[target_slug]}

    async def process_namespace(slug: str, ns_info: Dict[str, Any]) -> Dict[str, Any]:
        vector_count = int((ns_info or {}).get("vector_count") or 0)
        client_report = _pinecone_fetch_report_doc(
            index_name=settings.pinecone_client_kb_reports_index_name,
            namespace=settings.pinecone_client_kb_reports_namespace,
            doc_id=f"_client_kb_master/clients/{slug}.json",
        )
        return _build_index_payload(
            client_slug=slug,
            vector_count=vector_count,
            client_report=client_report,
        )

    results = await asyncio.gather(*[process_namespace(slug, ns_info) for slug, ns_info in namespaces.items()])
    results.sort(key=lambda x: x.get("createdAt") or "", reverse=True)
    if target_slug:
        return {"index": results[0]}
    return {"indexes": results}


@router.post("/indexes")
async def upsert_index(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Upsert a client index card into supabase_storage_metadata.json.
    This makes index visibility shared across environments (not browser-local only).
    """
    slug = _normalize_client_slug(
        str(payload.get("clientSlug") or payload.get("client_slug") or payload.get("namespace") or "")
    )
    if not slug:
        raise HTTPException(status_code=400, detail="clientSlug or namespace is required")

    storage = _supabase_storage_client()

    existing: Dict[str, Any] = {}
    try:
        loaded = await asyncio.to_thread(storage.download_json, INDEXES_BUCKET, f"{slug}/supabase_storage_metadata.json")
        if isinstance(loaded, dict):
            existing = loaded
    except Exception:
        existing = {}

    incoming_meta = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    existing_meta = existing.get("metadata") if isinstance(existing.get("metadata"), dict) else {}
    merged_meta = {**existing_meta, **incoming_meta}
    if not merged_meta.get("title"):
        merged_meta["title"] = str(payload.get("clientName") or payload.get("client_name") or slug)

    website_docs = existing.get("website_docs") if isinstance(existing.get("website_docs"), dict) else {"total": int(payload.get("pagesCrawled") or 0), "by_content_type": {}}
    drive_docs = existing.get("drive_docs") if isinstance(existing.get("drive_docs"), dict) else {"total": 0, "by_content_type": {}}
    intake_form_docs = int(existing.get("intake_form_docs") or 0)

    merged: Dict[str, Any] = {
        "website_url": str(payload.get("url") or existing.get("website_url") or "").strip(),
        "drive_url": str(payload.get("drive_url") or existing.get("drive_url") or "").strip() or None,
        "client_slug": slug,
        "client_name": str(payload.get("clientName") or payload.get("client_name") or existing.get("client_name") or "").strip() or None,
        "website_docs": website_docs,
        "intake_form_docs": intake_form_docs,
        "drive_docs": drive_docs,
        "createdAt": str(existing.get("createdAt") or datetime.now(timezone.utc).isoformat()),
        "metadata": merged_meta,
        "chunker": str(existing.get("chunker") or "char:1200:200"),
        "source": "supabase_storage",
    }

    await asyncio.to_thread(
        storage.upload_json,
        bucket=INDEXES_BUCKET,
        path=f"{slug}/supabase_storage_metadata.json",
        payload=merged,
        upsert=True,
    )

    # Invalidate cache and refresh summary best-effort.
    _indexes_cache["ts"] = 0.0
    _indexes_cache["payload"] = None
    try:
        slugs = _list_client_slugs_from_storage()
        results = await _build_indexes_from_storage(storage, slugs)
        if results:
            await _write_indexes_summary(storage, results)
    except Exception:
        pass

    return {"success": True, "index": _index_payload_from_metadata(client_slug=slug, meta=merged)}


@router.delete("/indexes")
async def delete_index(
    namespace: Optional[str] = None,
    client_slug: Optional[str] = None,
    clientSlug: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Delete a client across systems:
    - Supabase Storage prefix: client-data-sources/{clientSlug}/...
    - Pinecone namespace: sb-knowledge-bases (or configured KB index) namespace={clientSlug}

    NOTE: This is destructive and irreversible for that client's data.
    """
    settings = get_settings()
    slug = (namespace or client_slug or clientSlug or "").strip()
    if not slug:
        raise HTTPException(status_code=400, detail="namespace/clientSlug is required")

    storage = _supabase_storage_client()

    # 1) Delete Supabase Storage folder for client
    storage_result = await _delete_storage_prefix(storage=storage, bucket=INDEXES_BUCKET, prefix=slug)

    # Delete the aggregated indexes summary so it regenerates on next load.
    try:
        await asyncio.to_thread(storage.delete_objects, INDEXES_BUCKET, [INDEXES_SUMMARY_KEY])
    except Exception:
        pass

    # 2) Delete Pinecone namespace
    pinecone_result = await _delete_pinecone_namespace(index_name=settings.pinecone_kb_index_name, namespace=slug)

    # 3) Delete Supabase DB rows (clients + documents)
    db_result: Dict[str, Any] = {"deleted": False, "skipped": True, "reason": "db not configured"}
    try:
        from ..clients.supabase_agents_db_client import SupabaseAgentsDbClient

        db = SupabaseAgentsDbClient()
        # Delete documents first (in case of FK constraints), then client row.
        docs_res, client_res = await asyncio.gather(
            db.delete_documents_for_client(client_slug=slug),
            db.delete_client(client_slug=slug),
            return_exceptions=True,
        )
        out: Dict[str, Any] = {"skipped": False}
        if isinstance(docs_res, Exception):
            out["documents_error"] = str(docs_res)
        else:
            out["documents"] = docs_res
        if isinstance(client_res, Exception):
            out["clients_error"] = str(client_res)
        else:
            out["clients"] = client_res
        out["deleted"] = not bool(out.get("documents_error") or out.get("clients_error"))
        db_result = out
    except Exception as e:
        db_result = {"deleted": False, "skipped": True, "error": str(e)}

    # 4) Invalidate in-process cache
    _indexes_cache["ts"] = 0.0
    _indexes_cache["payload"] = None

    return {"success": True, "clientSlug": slug, "storage": storage_result, "pinecone": pinecone_result, "db": db_result}
