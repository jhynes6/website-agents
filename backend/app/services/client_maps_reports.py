from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..config import get_settings
from ..logging import log
from ..clients.supabase_storage_client import SupabaseStorageClient


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_reports_bucket(storage: SupabaseStorageClient, bucket: str) -> None:
    """
    Ensure reports bucket exists (private).
    """
    b = (bucket or "").strip()
    if not b:
        raise ValueError("reports bucket required")
    if storage.bucket_exists(b):
        return
    storage.create_bucket(b, public=False)


def upsert_client_map_report(
    *,
    client_slug: str,
    website_url: str,
    links: List[str],
    limit_used: int,
    reports_bucket: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Writes:
      - _reports/client_maps/{client_slug}.json
      - _reports/client_maps/index.json (aggregated)
    """
    slug = (client_slug or "").strip()
    if not slug:
        raise ValueError("client_slug required")
    website = (website_url or "").strip()
    b = (reports_bucket or get_settings().supabase_reports_bucket_name or "").strip()
    if not b:
        raise ValueError("SUPABASE_REPORTS_BUCKET not configured")

    storage = SupabaseStorageClient()
    _ensure_reports_bucket(storage, b)

    # Normalize links (unique, stable-ish)
    uniq: List[str] = []
    seen = set()
    for u in links or []:
        s = (u or "").strip()
        if not s or s in seen:
            continue
        seen.add(s)
        uniq.append(s)

    client_path = f"_reports/client_maps/{slug}.json"
    payload = {
        "client_slug": slug,
        "website_url": website,
        "generated_at": _now_iso(),
        "limit_used": int(limit_used),
        "count": len(uniq),
        "links": uniq,
    }
    storage.upload_json(bucket=b, path=client_path, payload=payload, upsert=True)

    # Update aggregated index (best-effort)
    index_path = "_reports/client_maps/index.json"
    index: Dict[str, Any] = {"updated_at": _now_iso(), "clients": {}}
    try:
        if storage.object_exists(b, index_path):
            raw = storage.download_json(b, index_path)
            if isinstance(raw, dict):
                index = raw
    except Exception as e:
        log("reports.client_maps.index_read_error", {"error": str(e)})

    if not isinstance(index.get("clients"), dict):
        index["clients"] = {}
    index["updated_at"] = _now_iso()
    index["clients"][slug] = {
        "website_url": website,
        "map_file_path": client_path,
        "count": len(uniq),
        "generated_at": payload["generated_at"],
        "limit_used": int(limit_used),
    }
    storage.upload_json(bucket=b, path=index_path, payload=index, upsert=True)

    return {"bucket": b, "client_path": client_path, "index_path": index_path, "count": len(uniq)}


