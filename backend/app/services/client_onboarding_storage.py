from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from ..clients.firecrawl import firecrawl_client
from ..clients.supabase_storage_client import SupabaseStorageClient
from ..logging import log
from .drive_ingest import build_drive_documents


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_service_account_path() -> Path:
    # Try common locations used elsewhere in the repo.
    candidates = [
        Path("service_account.json"),
        Path("backend/service_account.json"),
        Path(__file__).resolve().parent.parent.parent.parent / "service_account.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    # fall back to first candidate for error messages
    return candidates[-1]


def _normalize_url(url: Optional[str]) -> Optional[str]:
    u = (url or "").strip()
    if not u:
        return None
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    return u


def _extract_drive_doc_id(url: str) -> Optional[str]:
    """
    Extract file id from a Google Docs/Drive URL.
    Examples:
      - https://docs.google.com/document/d/<ID>/edit
      - https://drive.google.com/file/d/<ID>/view
    """
    u = (url or "").strip()
    if not u:
        return None
    m = re.search(r"/d/([a-zA-Z0-9_-]{10,})", u)
    return m.group(1) if m else None


@dataclass
class OnboardResult:
    client_slug: str
    bucket: str
    ensured_bucket: bool
    ensured_prefixes: List[str]
    website: Dict[str, Any]
    drive: Dict[str, Any]
    intake_form: Dict[str, Any]


async def onboard_client_to_supabase_storage(
    *,
    client_slug: str,
    website_url: Optional[str],
    drive_folder_url: Optional[str],
    intake_form_url: Optional[str] = None,
    website_limit: int = 500,
    website_max_depth: Optional[int] = None,
) -> OnboardResult:
    """
    New onboarding workflow:
      1) Check Storage buckets for client
      2) Create bucket if missing
      3) Ensure subfolder prefixes (website/drive/intake_form)
      4) Crawl website and store outputs to website/
      5) Ingest drive folder and store outputs to drive/ and intake_form/
    """
    slug = (client_slug or "").strip()
    if not slug:
        raise ValueError("client_slug required")

    storage = SupabaseStorageClient()

    # 1/2) ensure bucket
    existed = storage.bucket_exists(slug)
    if not existed:
        log("onboarding.storage.bucket.create", {"client_slug": slug})
        storage.create_bucket(slug, public=True)
    else:
        log("onboarding.storage.bucket.exists", {"client_slug": slug})

    # 3) ensure prefixes
    prefixes = ["website", "drive", "intake_form"]
    storage.ensure_prefixes(slug, prefixes)

    # 4) website crawl
    website_result: Dict[str, Any] = {"status": "skipped"}
    wurl = _normalize_url(website_url)
    if wurl:
        log("onboarding.website.start", {"client_slug": slug, "url": wurl, "limit": website_limit})
        pages, raw_status = await firecrawl_client.crawl_and_wait(
            wurl,
            website_limit,
            include_paths=None,
            exclude_paths=None,
            max_depth=website_max_depth,
        )

        # Store each page as markdown, keyed by url hash to avoid collisions.
        saved: List[Dict[str, Any]] = []
        for p in pages:
            meta = (p.get("metadata") or {}) if isinstance(p, dict) else {}
            page_url = (meta.get("sourceURL") or p.get("url") or "").strip()
            markdown = (p.get("markdown") or p.get("text") or "").strip()
            if not page_url or not markdown:
                continue

            key = SupabaseStorageClient.safe_key_for_url(page_url, prefix="website/pages", ext="md")
            storage.upload_bytes(bucket=slug, path=key, data=markdown.encode("utf-8"), content_type="text/markdown; charset=utf-8")
            saved.append(
                {
                    "url": page_url,
                    "title": meta.get("title"),
                    "content_type": meta.get("content_type"),
                    "storage_key": key,
                }
            )

        manifest = {
            "client_slug": slug,
            "source_url": wurl,
            "scraped_at": _utc_now_iso(),
            "counts": {"total_pages": len(pages), "saved_pages": len(saved)},
            "raw_status": raw_status,
            "pages": saved,
        }
        storage.upload_json(bucket=slug, path="website/manifest.json", payload=manifest)
        website_result = {"status": "ok", "saved_pages": len(saved), "total_pages": len(pages)}
        log("onboarding.website.done", {"client_slug": slug, **website_result})

    # 5) drive ingest
    drive_result: Dict[str, Any] = {"status": "skipped"}
    intake_result: Dict[str, Any] = {"status": "skipped"}

    creds_path = _resolve_service_account_path()
    if drive_folder_url:
        log("onboarding.drive.start", {"client_slug": slug})
        docs, summary, _ = build_drive_documents(drive_folder_url, slug, creds_path)

        drive_saved = 0
        intake_saved = 0

        # Store one JSON per document for now (keeps metadata + preview content).
        for d in docs:
            meta = (d.get("metadata") or {}) if isinstance(d, dict) else {}
            doc_id = (d.get("id") or "").strip()
            doc_source = meta.get("document_source")
            if not doc_id:
                continue

            if doc_source == "intake_form":
                prefix = "intake_form"
            else:
                prefix = "drive"

            key = f"{prefix}/documents/{doc_id}.json"
            storage.upload_json(bucket=slug, path=key, payload=d)
            if prefix == "intake_form":
                intake_saved += 1
            else:
                drive_saved += 1

        # Optional: if intake_form_url is provided and points to a specific doc, store a shortcut record
        intake_doc_id = _extract_drive_doc_id(intake_form_url or "")
        if intake_doc_id:
            storage.upload_json(
                bucket=slug,
                path="intake_form/intake_form_url.json",
                payload={"client_slug": slug, "intake_form_url": intake_form_url, "drive_file_id": intake_doc_id, "saved_at": _utc_now_iso()},
            )

        storage.upload_json(
            bucket=slug,
            path="drive/manifest.json",
            payload={
                "client_slug": slug,
                "drive_folder_url": drive_folder_url,
                "saved_at": _utc_now_iso(),
                "summary": summary,
                "counts": {"documents_total": len(docs), "drive_saved": drive_saved, "intake_saved": intake_saved},
            },
        )

        drive_result = {"status": "ok", "saved": drive_saved, "total": len(docs)}
        intake_result = {"status": "ok", "saved": intake_saved}
        log("onboarding.drive.done", {"client_slug": slug, **drive_result})

    return OnboardResult(
        client_slug=slug,
        bucket=slug,
        ensured_bucket=not existed,
        ensured_prefixes=prefixes,
        website=website_result,
        drive=drive_result,
        intake_form=intake_result,
    )


