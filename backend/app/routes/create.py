import json
import asyncio
import logging
import os
import time
import re
import uuid
import yaml
import httpx
from pathlib import Path
from urllib.parse import urlparse, quote
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..clients.firecrawl import firecrawl_client
from ..clients.llm import llm_client
from ..clients.pinecone_client import pinecone_kb_client
from ..clients.supabase_agent_storage_client import SupabaseAgentStorageClient
from ..clients.supabase_agents_db_client import SupabaseAgentsDbClient
from ..config import get_settings
from ..logging import log, logger
from ..services.drive_ingest import (
    build_drive_documents,
    categorize_drive_documents,
    extract_drive_folder_id,
)
from ..utils.content_hash import compute_content_hash
from pinecone import Pinecone
from openai import OpenAI
import tempfile

DRIVE_CONTENT_SYSTEM_PROMPT = """
You are helping categorize document content based on the type of information in each document.

Categories and definitions:

- capabilities_overview: content that provides an overview of the company's capabilities
- case_studies: content with case studies detailing success stories or project examples
- brochures_newsletters: content with brochures or newsletters
- pitch_decks: content with pitch decks
- other: use this if you cannot confidently assign the content to one of the provided categories

Return ONLY the category name.
"""

DRIVE_VALID_CATEGORIES = [
    "capabilities_overview",
    "case_studies",
    "brochures_newsletters",
    "pitch_decks",
    "other",
]

router = APIRouter()

# -----------------------------------------------------------------------------
# Map + Scrape endpoints (used by homepage "Map + Scrape" flow)
# -----------------------------------------------------------------------------


@router.post("/map")
async def map_site(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Discover URLs for a site (best-effort) using Firecrawl's /map.
    Frontend expects: { success: true, links: [...] }.
    """
    url = str(payload.get("url") or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="url is required")
    limit = int(payload.get("limit") or 5000)
    req_id = uuid.uuid4().hex[:10]
    t0 = time.perf_counter()
    log("create.map.start", {"req_id": req_id, "url": url, "limit": limit})
    try:
        links = await firecrawl_client.map_urls(url, limit=limit)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        log("create.map.ok", {"req_id": req_id, "url": url, "links": len(links), "elapsed_ms": elapsed_ms})
        return {"success": True, "links": links, "details": {"pagesFound": len(links)}}
    except Exception as e:
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        log("create.map.error", {"req_id": req_id, "url": url, "limit": limit, "elapsed_ms": elapsed_ms, "error": str(e)})
        return {"success": False, "error": str(e), "links": []}


@router.post("/scrape")
async def scrape_urls(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Scrape a provided list of URLs using Firecrawl's /scrape.
    This is used by the homepage "Map + Scrape" flow.

    NOTE: This endpoint can optionally persist results to Supabase Storage/DB and ingest to Pinecone,
    depending on request flags and whether `clientSlug` is provided.
    """
    urls_in = payload.get("urls") or []
    if not isinstance(urls_in, list) or not urls_in:
        raise HTTPException(status_code=400, detail="urls (list) is required")

    client_slug = str(payload.get("clientSlug") or payload.get("client_slug") or payload.get("namespace") or "").strip()
    index = str(payload.get("index") or client_slug or "").strip() or None
    namespace = client_slug or (index or "default")
    req_id = uuid.uuid4().hex[:10]
    t0_total = time.perf_counter()
    urls_preview = [str(u or "").strip() for u in urls_in[:5]]
    log(
        "create.scrape.start",
        {
            "req_id": req_id,
            "namespace": namespace,
            "index": index,
            "urls_count": len(urls_in),
            "urls_preview": urls_preview,
        },
    )

    # Robustness: default to persisting scraped pages when clientSlug is provided,
    # so a UI crash after scraping doesn't force re-scrape (credits).
    persist_to_supabase = payload.get("persistToSupabase")
    if persist_to_supabase is None:
        persist_to_supabase = True if client_slug else False
    persist_to_supabase = bool(persist_to_supabase)

    # Optionally embed/upsert to Pinecone as part of the scrape flow (default on if persisting).
    ingest_to_pinecone = payload.get("ingestToPinecone")
    if ingest_to_pinecone is None:
        ingest_to_pinecone = True if persist_to_supabase else False
    ingest_to_pinecone = bool(ingest_to_pinecone)

    # Match /create behavior: by default, run LLM markdown cleaning unless explicitly skipped.
    # (This affects what gets written to Storage and embedded into Pinecone.)
    skip_markdown_clean = bool(payload.get("skipMarkdownClean") or payload.get("skip_markdown_clean") or False)

    # LLM enrichment (document_context + keywords).
    # Default behavior: enable whenever we're persisting scraped pages (Map+Scrape ingestion).
    generate_document_context = payload.get("generateDocumentContext")
    generate_keywords = payload.get("generateKeywords")
    enrichment_default = bool(persist_to_supabase and client_slug)
    if generate_document_context is None:
        generate_document_context = enrichment_default
    if generate_keywords is None:
        generate_keywords = enrichment_default
    generate_document_context = bool(generate_document_context)
    generate_keywords = bool(generate_keywords)

    requested_chunker = str(payload.get("chunker") or "").strip() or None
    semantic_embeddings = bool(payload.get("semanticEmbeddings") or payload.get("semantic_embeddings") or False)

    # Scrape in parallel but keep concurrency conservative.
    sem = asyncio.Semaphore(6)
    pages: List[Dict[str, Any]] = []

    # ---------------------------------------------------------------------
    # Skip re-scraping URLs that were already ingested recently (DB-backed)
    # ---------------------------------------------------------------------
    def _norm_url(u: str) -> str:
        try:
            p = urlparse((u or "").strip())
            scheme = (p.scheme or "https").lower()
            netloc = (p.netloc or "").lower()
            path = p.path or ""
            # Normalize: strip trailing slash except for root
            if path.endswith("/") and path != "/":
                path = path[:-1]
            # Ignore fragments for dedupe
            return f"{scheme}://{netloc}{path}"
        except Exception:
            return (u or "").strip()

    blocked_recent: set[str] = set()
    blocked_count = 0
    if client_slug:
        try:
            db = SupabaseAgentsDbClient()
            recent_urls = await db.get_recent_document_urls(client_slug=client_slug, document_source="website", days=30)
            blocked_recent = {_norm_url(u) for u in recent_urls if isinstance(u, str) and u.strip()}
            if blocked_recent:
                before = len(urls_in)
                urls_in = [u for u in urls_in if _norm_url(str(u or "")) not in blocked_recent]
                blocked_count = before - len(urls_in)
        except Exception as e:
            log("create.scrape.recent_urls_error", {"req_id": req_id, "client": client_slug, "error": str(e)})

    if blocked_count:
        log(
            "create.scrape.recent_urls_blocked",
            {"req_id": req_id, "client": client_slug, "blocked": blocked_count, "remaining": len(urls_in)},
        )

    async def scrape_one(u: str) -> Optional[Dict[str, Any]]:
        url = str(u or "").strip()
        if not url:
            return None
        async with sem:
            t0 = time.perf_counter()
            log("create.scrape.url_start", {"req_id": req_id, "url": url})
            try:
                res = await asyncio.to_thread(firecrawl_client.scrape_url, url)
                if not isinstance(res, dict):
                    elapsed_ms = int((time.perf_counter() - t0) * 1000)
                    log("create.scrape.url_ok", {"req_id": req_id, "url": url, "elapsed_ms": elapsed_ms, "markdown_len": 0})
                    return {"url": url, "metadata": {"sourceURL": url}, "markdown": ""}
                # normalize shape to resemble crawl results
                meta = res.get("metadata")
                if not isinstance(meta, dict):
                    meta = {}
                    res["metadata"] = meta
                meta.setdefault("sourceURL", url)
                res.setdefault("url", url)
                # Firecrawl scrape returns "markdown" at top-level in our client config.
                if "markdown" not in res and isinstance(res.get("data"), dict):
                    res["markdown"] = res["data"].get("markdown")  # fallback if shape changes
                md_len = len(str(res.get("markdown") or ""))
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
                log("create.scrape.url_ok", {"req_id": req_id, "url": url, "elapsed_ms": elapsed_ms, "markdown_len": md_len})
                return res
            except Exception as e:
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
                # Best-effort parse status code from "Firecrawl error {status}: ..."
                status = None
                m = re.search(r"Firecrawl error\s+(\d{3})\s*:", str(e))
                if m:
                    try:
                        status = int(m.group(1))
                    except Exception:
                        status = None
                log(
                    "create.scrape.url_error",
                    {"req_id": req_id, "url": url, "elapsed_ms": elapsed_ms, "status": status, "error": str(e)},
                )
                return {"url": url, "metadata": {"sourceURL": url}, "markdown": "", "error": str(e)}

    results = await asyncio.gather(*[scrape_one(u) for u in urls_in])
    pages = [r for r in results if isinstance(r, dict)]

    errors = [p for p in pages if isinstance(p.get("error"), str) and p.get("error")]
    empty_md = [p for p in pages if not str(p.get("markdown") or "").strip()]
    elapsed_total_ms = int((time.perf_counter() - t0_total) * 1000)
    log(
        "create.scrape.done",
        {
            "req_id": req_id,
            "namespace": namespace,
            "index": index,
            "urls_count": len(urls_in),
            "pages_returned": len(pages),
            "errors": len(errors),
            "empty_markdown": len(empty_md),
            "elapsed_ms": elapsed_total_ms,
            "persist_to_supabase": persist_to_supabase,
            "ingest_to_pinecone": ingest_to_pinecone,
            "semantic_embeddings": semantic_embeddings,
            "generate_document_context": generate_document_context,
            "generate_keywords": generate_keywords,
            "skip_markdown_clean": skip_markdown_clean,
        },
    )

    # If requested, persist scraped pages to Supabase Storage + vectorize to Pinecone (create-like behavior).
    storage_info: Dict[str, Any] = {}
    pinecone_info: Dict[str, Any] = {}
    if persist_to_supabase and client_slug:
        try:
            # Convert scrape results to the same document shape used by the create pipeline.
            final_documents: List[Dict[str, Any]] = []
            for p in pages:
                url = str(p.get("url") or (p.get("metadata") or {}).get("sourceURL") or "").strip()
                md_raw = str(p.get("markdown") or "").strip()
                if not url or not md_raw:
                    continue
                meta = p.get("metadata") if isinstance(p.get("metadata"), dict) else {}
                meta = {**meta, "url": url}
                # Best-effort title/favicon extraction
                title = str(meta.get("ogTitle") or meta.get("title") or "").strip() or url
                favicon = meta.get("favicon") or meta.get("ogImage") or meta.get("og:image") or meta.get("twitter:image")
                if favicon:
                    meta["favicon"] = favicon
                # Heuristic: homepage if path is empty or '/'
                content_type = "other"
                try:
                    parsed = urlparse(url)
                    if parsed.path in ("", "/"):
                        content_type = "homepage"
                except Exception:
                    content_type = "other"

                # Match /create: deterministic preclean. (LLM cleaning is run after we assemble the list,
                # with bounded concurrency to avoid appearing "stuck" on large batches.)
                md = _preclean_markdown_for_kb(md_raw)

                final_documents.append(
                    {
                        "title": title,
                        "document_source": "website",
                        "content_type": content_type,
                        "markdown": md,
                        "metadata": meta,
                    }
                )

            if final_documents:
                # Match /create: optional LLM markdown cleaning (default on unless skipMarkdownClean=true).
                if not skip_markdown_clean:
                    clean_sem = asyncio.Semaphore(6)

                    async def _clean_one(d: Dict[str, Any]) -> None:
                        async with clean_sem:
                            try:
                                u = str((d.get("metadata") or {}).get("url") or "")
                                t = str(d.get("title") or "")
                                pre = str(d.get("markdown") or "")
                                cleaned = await _llm_clean_markdown_for_kb(url=u, title=t, markdown=pre)
                                d["markdown"] = _preclean_markdown_for_kb(cleaned)
                            except Exception as e:
                                log(
                                    "create.scrape.markdown_clean_error",
                                    {"req_id": req_id, "url": str((d.get("metadata") or {}).get("url") or ""), "error": str(e)},
                                )

                    log("create.scrape.markdown_clean_start", {"req_id": req_id, "client": client_slug, "docs": len(final_documents)})
                    await asyncio.gather(*[_clean_one(d) for d in final_documents])
                    log("create.scrape.markdown_clean_done", {"req_id": req_id, "client": client_slug, "docs": len(final_documents)})

                # LLM enrichment (same as /create): add per-file document_context + keywords before uploading.
                if generate_document_context or generate_keywords:
                    try:
                        enrich_sem = asyncio.Semaphore(10)
                        progress_lock = asyncio.Lock()
                        progress_counter = {"done": 0, "errors": 0}
                        enrichment_start_time = time.time()

                        async def _enrich_one(d: Dict[str, Any], idx: int) -> None:
                            async with enrich_sem:
                                doc_url = str((d.get("metadata") or {}).get("url") or d.get("url") or "")
                                doc_title = str(d.get("title") or (d.get("metadata") or {}).get("title") or "")[:50]
                                doc_start_time = time.time()
                                
                                title = str(d.get("title") or (d.get("metadata") or {}).get("title") or "")
                                body = str(d.get("markdown") or "")
                                
                                try:
                                    if generate_document_context:
                                        ctx = await _extract_document_context_for_doc(body=body)
                                        if isinstance(ctx, str) and ctx.strip():
                                            d["document_context"] = ctx.strip()
                                except Exception as e:
                                    async with progress_lock:
                                        progress_counter["errors"] += 1
                                    log("create.scrape.document_context_error", {"req_id": req_id, "idx": idx, "url": doc_url, "title": doc_title, "error": str(e)})
                                try:
                                    if generate_keywords:
                                        kws = await _extract_keywords_for_doc(title=title, body=body)
                                        if kws:
                                            d["keywords"] = kws
                                except Exception as e:
                                    async with progress_lock:
                                        progress_counter["errors"] += 1
                                    log("create.scrape.keywords_error", {"req_id": req_id, "idx": idx, "url": doc_url, "title": doc_title, "error": str(e)})
                                
                                async with progress_lock:
                                    progress_counter["done"] += 1
                                    done = progress_counter["done"]
                                    total = len(final_documents)
                                    elapsed = time.time() - enrichment_start_time
                                    doc_elapsed = time.time() - doc_start_time
                                    
                                    # Log every 25 documents or every 10% completion
                                    if done % 25 == 0 or done % max(1, total // 10) == 0 or done == total:
                                        pct = (done / total) * 100
                                        avg_time = elapsed / done if done > 0 else 0
                                        est_remaining = (total - done) * avg_time if done > 0 else 0
                                        log(
                                            "create.scrape.enrichment_progress",
                                            {
                                                "req_id": req_id,
                                                "client": client_slug,
                                                "done": done,
                                                "total": total,
                                                "percent": round(pct, 1),
                                                "errors": progress_counter["errors"],
                                                "elapsed_sec": round(elapsed, 1),
                                                "avg_sec_per_doc": round(avg_time, 2),
                                                "est_remaining_sec": round(est_remaining, 1),
                                                "current_doc_time_sec": round(doc_elapsed, 2),
                                                "current_url": doc_url[:100],
                                                "current_title": doc_title,
                                            },
                                        )

                        log(
                            "create.scrape.enrichment_start",
                            {"req_id": req_id, "client": client_slug, "docs": len(final_documents), "sem": 10},
                        )
                        await asyncio.gather(*[_enrich_one(d, idx) for idx, d in enumerate(final_documents)])
                        total_elapsed = time.time() - enrichment_start_time
                        log(
                            "create.scrape.enrichment_done",
                            {
                                "req_id": req_id,
                                "client": client_slug,
                                "docs": len(final_documents),
                                "elapsed_sec": round(total_elapsed, 1),
                                "errors": progress_counter["errors"],
                                "avg_sec_per_doc": round(total_elapsed / len(final_documents), 2) if final_documents else 0,
                            },
                        )

                    except Exception as e:
                        log("create.scrape.enrichment_error", {"req_id": req_id, "client": client_slug, "error": str(e)})

                # Ensure the client row exists in DB (Map+Scrape-only flows should still create/update it).
                try:
                    db = SupabaseAgentsDbClient()
                    # Derive a best-effort website + domain
                    website_url = str(payload.get("websiteUrl") or payload.get("url") or "").strip()
                    if not website_url:
                        # fall back to first scraped page url
                        website_url = str((final_documents[0].get("metadata") or {}).get("url") or "").strip()
                    client_domain = ""
                    try:
                        parsed = urlparse(website_url)
                        client_domain = (parsed.netloc or "").replace("www.", "").strip()
                    except Exception:
                        client_domain = ""
                    if client_domain:
                        await db.upsert_client(
                            client_slug=client_slug,
                            client_domain=client_domain,
                            client_name=str(payload.get("clientName") or payload.get("client_name") or "") or None,
                            website=website_url or None,
                        )
                        log("create.scrape.db_client_upsert_ok", {"req_id": req_id, "client": client_slug, "domain": client_domain})
                except Exception as e:
                    log("create.scrape.db_client_upsert_error", {"req_id": req_id, "client": client_slug, "error": str(e)})

                log("create.scrape.persist_start", {"req_id": req_id, "client": client_slug, "docs_prepared": len(final_documents)})
                storage_info = await _upload_to_storage(client_slug, final_documents)
                log("create.scrape.persist_done", {"req_id": req_id, "client": client_slug, **(storage_info or {})})

                # Write/update supabase_storage_metadata.json (so /indexes has something durable even if UI dies)
                supabase_client = get_supabase_storage_client()
                BUCKET_NAME = "client-data-sources"
                if supabase_client:
                    try:
                        homepage_doc = next((d for d in final_documents if d.get("content_type") == "homepage"), final_documents[0])
                        hm = homepage_doc.get("metadata") or {}
                        homepage_title = hm.get("ogTitle") or hm.get("title") or client_slug
                        homepage_favicon = hm.get("favicon") or hm.get("ogImage")
                        supabase_storage_metadata_file: Dict[str, Any] = {
                            "website_url": str(payload.get("websiteUrl") or payload.get("url") or ""),
                            "drive_url": "",
                            "client_slug": client_slug,
                            "client_name": str(payload.get("clientName") or payload.get("client_name") or "") or None,
                            "website_docs": {
                                "total": len([d for d in final_documents if d.get("document_source") == "website"]),
                                "by_content_type": {},
                            },
                            "intake_form_docs": 0,
                            "drive_docs": {"total": 0, "by_content_type": {}},
                            "createdAt": time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                            "metadata": {
                                "title": homepage_title,
                                **({"favicon": homepage_favicon} if homepage_favicon else {}),
                            },
                            "chunker": requested_chunker or "char:1200:200",
                            "source": "supabase_storage",
                        }
                        # counts
                        by_ct: Dict[str, int] = {}
                        for d in final_documents:
                            if d.get("document_source") != "website":
                                continue
                            ct = d.get("content_type") or "other"
                            by_ct[ct] = by_ct.get(ct, 0) + 1
                        supabase_storage_metadata_file["website_docs"]["by_content_type"] = by_ct

                        supabase_client.upload_json(
                            bucket=BUCKET_NAME,
                            path=f"{client_slug}/supabase_storage_metadata.json",
                            payload=supabase_storage_metadata_file,
                            upsert=True,
                        )
                        log("create.scrape.supabase_metadata_saved", {"req_id": req_id, "client": client_slug, "key": "supabase_storage_metadata.json"})
                    except Exception as e:
                        log("create.scrape.supabase_metadata_error", {"req_id": req_id, "client": client_slug, "error": str(e)})

                # Vectorize to Pinecone (optional)
                if ingest_to_pinecone and storage_info.get("success"):
                    try:
                        settings = get_settings()
                        effective_namespace = f"{client_slug}-semantic" if semantic_embeddings else client_slug
                        effective_index = settings.pinecone_kb_index_name
                        force_chunker = "md_semantic_v1" if semantic_embeddings else None
                        log(
                            "create.scrape.pinecone_start",
                            {
                                "req_id": req_id,
                                "client": client_slug,
                                "index": effective_index,
                                "namespace": effective_namespace,
                                "force_chunker": force_chunker,
                            },
                        )
                        pinecone_info = await _vectorize_to_pinecone(
                            client_slug,
                            namespace_override=effective_namespace,
                            index_override=effective_index,
                            force_chunker=force_chunker,
                        )
                        log("create.scrape.pinecone_done", {"req_id": req_id, "client": client_slug, **(pinecone_info or {})})

                        # Write pinecone_namespace_metadata.json if vectorization succeeded
                        supabase_client = get_supabase_storage_client()
                        if supabase_client and pinecone_info.get("success"):
                            try:
                                pinecone_meta = pinecone_kb_client.build_onboarding_metadata_report(
                                    client_slug=str(pinecone_info.get("namespace") or effective_namespace),
                                    website_url=str(payload.get("websiteUrl") or payload.get("url") or ""),
                                    drive_url="",
                                    index_name=str(pinecone_info.get("index") or effective_index),
                                )
                                BUCKET_NAME = "client-data-sources"
                                supabase_client.upload_json(
                                    bucket=BUCKET_NAME,
                                    path=f"{client_slug}/pinecone_namespace_metadata.json",
                                    payload=pinecone_meta,
                                    upsert=True,
                                )
                                log("create.scrape.pinecone_metadata_saved", {"req_id": req_id, "client": client_slug, "key": "pinecone_namespace_metadata.json"})
                            except Exception as e:
                                log("create.scrape.pinecone_metadata_error", {"req_id": req_id, "client": client_slug, "error": str(e)})
                    except Exception as e:
                        log("create.scrape.pinecone_error", {"req_id": req_id, "client": client_slug, "error": str(e)})
                        pinecone_info = {"success": False, "error": str(e)}
        except Exception as e:
            log("create.scrape.persist_error", {"req_id": req_id, "client": client_slug, "error": str(e)})

    # Don’t ship thousands of markdown blobs back to the browser (it’s fragile + slow).
    # The UI only needs a small sample to extract homepage metadata.
    data_preview = pages[:10]

    return {
        "success": True,
        "namespace": namespace,
        "index": index,
        "details": {
            "pagesScraped": len(pages),
            "errors": len(errors),
            "emptyMarkdown": len(empty_md),
            "persistedToSupabase": bool(storage_info.get("success")) if persist_to_supabase and client_slug else False,
            "pineconeUpserted": bool(pinecone_info.get("success")) if ingest_to_pinecone and client_slug else False,
            "recordsUpserted": int(pinecone_info.get("records_upserted") or 0) if isinstance(pinecone_info, dict) else 0,
        },
        "data": data_preview,
    }

# Initialize Supabase Agent Storage client (lazy - only if configured)
_supabase_storage_client = None

def get_supabase_storage_client() -> Optional[SupabaseAgentStorageClient]:
    """Get Supabase Storage client if configured."""
    global _supabase_storage_client
    if _supabase_storage_client is None:
        settings = get_settings()
        if settings.supabase_agent_url and settings.supabase_agent_key:
            try:
                _supabase_storage_client = SupabaseAgentStorageClient()
                log("create.supabase.initialized", {"url": str(settings.supabase_agent_url)})
            except Exception as e:
                log("create.supabase.init_error", {"error": str(e)})
                return None
        else:
            log("create.supabase.not_configured", {})
            return None
    return _supabase_storage_client

_MD_CODEBLOCK_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
_MD_IMAGE_RE = re.compile(r"!\[[^\]]*]\([^)]+\)")
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_MD_HTML_TAG_RE = re.compile(r"<[^>]+>")
_MD_BASE64_IMAGE_RE = re.compile(r"!\[[^\]]*]\(<Base64-Image-Removed>\)")
_MD_SOCIAL_SHARE_RE = re.compile(r"\[(Facebook|Twitter|LinkedIn|Email)\]\([^)]+\)", re.IGNORECASE)
_MD_ADDTOANY_RE = re.compile(r"https?://www\.addtoany\.com/add_to/\S+", re.IGNORECASE)
_MD_STANDALONE_CTA_RE = re.compile(
    r"(?im)^\s*(talk to us|schedule a call( today)?|learn more|contact us|book a call|request (a )?demo)\s*$"
)


def _preclean_markdown_for_kb(text: str) -> str:
    """
    Deterministic cleanup to remove common Firecrawl noise.
    - Removes images (including <Base64-Image-Removed>)
    - Converts markdown links to just anchor text
    - Removes social-share link blocks + addtoany URLs
    - Collapses whitespace
    """
    t = (text or "").strip()
    if not t:
        return ""
    t = _MD_CODEBLOCK_RE.sub(" ", t)
    t = _MD_BASE64_IMAGE_RE.sub(" ", t)
    t = _MD_IMAGE_RE.sub(" ", t)
    t = _MD_ADDTOANY_RE.sub("", t)
    # remove social share blocks
    t = _MD_SOCIAL_SHARE_RE.sub(" ", t)
    # links -> anchor text only
    t = _MD_LINK_RE.sub(r"\1", t)
    t = _MD_HTML_TAG_RE.sub(" ", t)
    # remove CTA-only lines
    t = _MD_STANDALONE_CTA_RE.sub("", t)
    # collapse whitespace + blank lines
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r"[ \t]{2,}", " ", t).strip()
    return t


async def _llm_clean_markdown_for_kb(*, url: str, title: str, markdown: str) -> str:
    """
    Use gpt-4o-mini to remove headers/footers/nav/link noise while preserving
    the page's sales-relevant content.
    Returns cleaned markdown only (no code fences).
    """
    md = (markdown or "").strip()
    if not md:
        return ""

    def _split_markdown_for_llm(text: str, *, max_chars: int = 6000) -> List[str]:
        """
        Split markdown into chunks without arbitrarily dropping content.
        Prefers splitting on blank lines, falls back to hard splits if needed.
        """
        t = (text or "").strip()
        if not t:
            return []
        if len(t) <= max_chars:
            return [t]

        parts = t.split("\n\n")
        chunks: List[str] = []
        buf: List[str] = []
        size = 0
        for p in parts:
            sep = 2 if buf else 0
            if size + sep + len(p) <= max_chars:
                buf.append(p)
                size += sep + len(p)
                continue
            if buf:
                chunks.append("\n\n".join(buf).strip())
            buf = [p]
            size = len(p)
            # handle very large single paragraph
            if size > max_chars:
                large = buf[0]
                buf = []
                size = 0
                for i in range(0, len(large), max_chars):
                    chunks.append(large[i : i + max_chars].strip())
        if buf:
            chunks.append("\n\n".join(buf).strip())
        return [c for c in chunks if c]

    system = (
        "You clean scraped website markdown for a sales knowledge base.\n"
        "Remove anything not useful to understanding what the company sells.\n"
        "MUST remove:\n"
        "- headers, nav menus, footers, legal boilerplate, cookie banners\n"
        "- social share links (facebook/twitter/linkedin/email), addtoany blocks\n"
        "- large image/logo walls and image-only sections (including Base64-Image-Removed)\n"
        "- standalone CTAs and form field lists (name/email/phone dropdowns etc)\n"
        "- outbound links: keep the visible text only, and drop the URL\n"
        "\n"
        "MUST keep:\n"
        "- product/service descriptions, features, benefits, process, deliverables\n"
        "- pricing details, case studies, testimonials (when substantive)\n"
        "- key facts that help sell/position the offering\n"
        "\n"
        "Output rules:\n"
        "- Return ONLY cleaned markdown.\n"
        "- No YAML frontmatter.\n"
        "- No code fences.\n"
        "- Keep headings/bullets when they carry meaning.\n"
    )
    segments = _split_markdown_for_llm(md, max_chars=6000)
    if not segments:
        return ""

    try:
        cleaned_parts: List[str] = []
        total = len(segments)
        for i, seg in enumerate(segments, 1):
            user = (
                f"URL: {url}\nTitle: {title}\n"
                f"SEGMENT {i}/{total} (part of a larger page; do not summarize or invent content):\n\n"
                f"MARKDOWN:\n{seg}"
            )
            resp = await llm_client.chat(
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.1,
                # Allow the model to return a substantial cleaned segment without truncating mid-output.
                max_tokens=4000,
                model="gpt-4o-mini",
            )
            out = (resp["choices"][0]["message"]["content"] or "").strip()
            # Strip accidental fences/frontmatter if the model disobeys
            out = re.sub(r"(?s)^```.*?\n", "", out).strip()
            out = re.sub(r"(?s)\n```$", "", out).strip()
            out = re.sub(r"(?s)^---\n.*?\n---\n", "", out).strip()
            cleaned_parts.append(out)

        return "\n\n".join([p for p in cleaned_parts if p]).strip()
    except Exception as e:
        log("create.markdown_clean.error", {"error": str(e), "url": url})
        return markdown


async def _clean_pages_markdown_parallel(pages: List[Dict[str, Any]], max_concurrency: int = 6) -> List[Dict[str, Any]]:
    """
    Clean website markdown content after Firecrawl.
    Uses deterministic pre-clean for all pages, and LLM clean only when the page is noisy.
    """
    sem = asyncio.Semaphore(max_concurrency)

    async def _clean_one(p: Dict[str, Any]) -> Dict[str, Any]:
        async with sem:
            meta = p.get("metadata", {}) or {}
            url = str(meta.get("sourceURL") or p.get("url") or "").strip()
            title = str(meta.get("title") or "").strip()
            raw = str(p.get("markdown") or p.get("text") or "").strip()
            if not raw:
                return p

            # Always pre-clean
            pre = _preclean_markdown_for_kb(raw)
            if not pre:
                p["markdown"] = ""
                return p

            # Heuristic: only spend LLM tokens on noisy pages
            img_count = raw.count("![")
            base64_count = raw.lower().count("base64-image-removed")
            social_count = raw.lower().count("addtoany.com/add_to") + sum(raw.lower().count(x) for x in ["[facebook]", "[twitter]", "[linkedin]", "[email]"])
            noisy = (img_count >= 10) or (base64_count >= 5) or (social_count >= 2) or (len(raw) >= 12_000)

            cleaned = pre
            if noisy:
                cleaned = await _llm_clean_markdown_for_kb(url=url, title=title, markdown=pre)
                cleaned = _preclean_markdown_for_kb(cleaned)

            # Write back (this is what will be embedded + stored in Pinecone)
            p["markdown"] = cleaned
            return p

    tasks = [_clean_one(p) for p in pages]
    return await asyncio.gather(*tasks)


def _clean_for_keywords(text: str) -> str:
    """
    Lightweight markdown/html cleanup for keyword extraction.
    """
    t = (text or "").strip()
    if not t:
        return ""
    t = _MD_CODEBLOCK_RE.sub(" ", t)
    t = _MD_IMAGE_RE.sub(" ", t)
    t = _MD_LINK_RE.sub(r"\1", t)  # keep anchor text
    t = _MD_HTML_TAG_RE.sub(" ", t)
    # collapse whitespace
    t = re.sub(r"\s+", " ", t).strip()
    return t


async def _extract_keywords_for_doc(title: str, body: str) -> List[str]:
    """
    Return 3-5 keywords/short phrases (string list). Flat only.
    """
    cleaned = _clean_for_keywords(body)
    if not cleaned:
        return []

    # keep prompt small
    cleaned = cleaned[:2500]
    title = (title or "").strip()

    system = (
        "Extract 3-5 keywords or short keyphrases that best describe the document.\n"
        "Rules:\n"
        "- Return ONLY valid JSON.\n"
        "- Preferred format: {\"keywords\": [\"...\"]}\n"
        "- 3 to 5 items.\n"
        "- Lowercase.\n"
        "- No punctuation except hyphens.\n"
        "- No nested structures.\n"
        "- Avoid generic words (home, page, click, welcome).\n"
    )
    user = f"Title: {title}\n\nBody:\n{cleaned}"

    try:
        resp = await llm_client.chat(
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.2,
            max_tokens=120,
            model="gpt-4o-mini",
        )
        raw = resp["choices"][0]["message"]["content"].strip()
        # best-effort parse (LLMs often wrap JSON in prose)
        parsed: Any = None
        try:
            parsed = json.loads(raw)
        except Exception:
            # Try to extract the first JSON array or object substring.
            m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", raw)
            if m:
                parsed = json.loads(m.group(1))

        items: List[str] = []
        if isinstance(parsed, dict) and isinstance(parsed.get("keywords"), list):
            items = [x for x in parsed.get("keywords") if isinstance(x, str)]
        elif isinstance(parsed, list):
            items = [x for x in parsed if isinstance(x, str)]

        out: List[str] = []
        for item in items:
            s = item.strip().lower()
            if s:
                out.append(s)
        return out[:5]
    except Exception as e:
        log("create.keywords.error", {"error": str(e)})
    return []


async def _extract_document_context_for_doc(body: str) -> Optional[str]:
    """
    Summarize the document in 1-2 sentences for KB labeling ("document_context").

    IMPORTANT: Input must be the cleaned markdown body ONLY (no YAML header).
    """
    cleaned = (body or "").strip()
    if not cleaned:
        return None

    # Keep prompt bounded.
    cleaned = cleaned[:4000]

    user = (
        "What is this document? Please summarize it in one or two sentences to describe its purpose and content, "
        "as if labeling it for use in a knowledge base or vector database.\n\n"
        f"{cleaned}"
    )
    try:
        resp = await llm_client.chat(
            messages=[{"role": "user", "content": user}],
            temperature=0.2,
            max_tokens=120,
            model="gpt-4o-mini",
        )
        raw = resp["choices"][0]["message"]["content"].strip()
        # Defensive cleanup: strip wrapping quotes and excessive whitespace.
        raw = raw.strip().strip('"').strip("'").strip()
        return raw or None
    except Exception as e:
        log("create.document_context.error", {"error": str(e)})
        return None


def _doc_id_from_url(raw_url: str) -> str:
    """Build a stable id from domain + path without a trailing slash."""
    parsed = urlparse(raw_url or "")
    netloc = parsed.netloc
    raw_path = parsed.path or "/"
    # Drop trailing slash unless the path is just "/"
    path = "" if raw_path == "/" else raw_path.rstrip("/")
    if netloc:
        return f"{netloc}{path}"
    # Fallback: if no netloc (e.g., already a bare path), return the path itself.
    return path


def _normalize_slug(raw: str) -> str:
    """Create a safe slug for namespaces/index names."""
    if not raw:
        return ""
    lowered = raw.strip().lower()
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in lowered)
    # Collapse multiple hyphens
    while "--" in safe:
        safe = safe.replace("--", "-")
    return safe.strip("-")


async def _upload_to_storage(client_slug: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Upload documents to Supabase Storage as markdown files with YAML frontmatter.
    
    This is the data preparation phase - vectorization happens separately.
    
    If uploads fail, saves files locally as a backup.

    Returns a small status object for UI/debugging.
    """
    # Get Supabase Storage client if configured
    supabase_client = get_supabase_storage_client()
    supabase_uploaded = 0
    supabase_failed = 0
    local_backup_dir = None
    
    if not supabase_client:
        log("create.supabase.not_configured", {"reason": "SUPABASE_AGENT_URL or SUPABASE_AGENT_KEY not set"})
        return {"uploaded_to_supabase": 0, "failed": 0, "success": False}
    
    # 1. Check if bucket exists and is ready for uploads
    # Using single bucket "client-data-sources" for all clients
    BUCKET_NAME = "client-data-sources"
    bucket_ready = False
    
    try:
        # Try to create folder structure for this client - this verifies bucket exists and is writable
        for subfolder in ["website", "drive", "intake_form"]:
            keep_path = f"{client_slug}/{subfolder}/.keep"
            supabase_client.upload_bytes(
                bucket=BUCKET_NAME,
                path=keep_path,
                data=b"# Folder placeholder\n",
                content_type="text/plain; charset=utf-8",
                upsert=True
            )
        # If we got here, bucket exists and uploads work!
        bucket_ready = True
        log("create.supabase.bucket_ready", {"client": client_slug, "bucket": BUCKET_NAME})
    except Exception as e:
        error_msg = str(e).lower()
        if "bucket not found" in error_msg or "not found" in error_msg:
            # Bucket doesn't exist - provide helpful message
            log("create.supabase.bucket_missing", {
                "bucket": BUCKET_NAME,
                "error": str(e),
                "hint": f"Create bucket via SQL: INSERT INTO storage.buckets (id, name, public, file_size_limit) VALUES ('{BUCKET_NAME}', '{BUCKET_NAME}', false, 104857600) ON CONFLICT (id) DO NOTHING;"
            })
        else:
            # Some other error (connection, auth, etc.)
            log("create.supabase.connection_error", {
                "client": client_slug,
                "bucket": BUCKET_NAME,
                "error": str(e)
            })
    
    # If bucket doesn't exist, prepare local backup directory
    if not bucket_ready:
        project_root = Path(__file__).parent.parent.parent.parent
        local_backup_dir = project_root / "data" / "supabase_backup" / client_slug
        local_backup_dir.mkdir(parents=True, exist_ok=True)
        log("create.local_backup.initialized", {"client": client_slug, "path": str(local_backup_dir)})

    # 2) Upload raw files to Supabase Storage
    db: SupabaseAgentsDbClient | None = None
    try:
        db = SupabaseAgentsDbClient()
    except Exception:
        db = None

    for doc in documents:
        try:
            # Handle content being string or dict
            content_field = doc.get("content")
            if isinstance(content_field, str):
                content = content_field
            else:
                content = (content_field or {}).get("text", "")

            if not content and "markdown" in doc:
                content = doc["markdown"]
            
            if not content:
                continue
            
            # Determine document source first
            doc_source_raw = doc.get("document_source", "unknown")
            safe_source = _normalize_slug(doc_source_raw)
            
            # Check if it is a drive file (by ID or source)
            is_drive_file = str(doc.get("id", "")).startswith("drive_") or safe_source in ["drive", "intake_form", "intake-form", "client_materials"]
            
            # Generate doc_id: {client_slug}_{document_source}_{domain}_{path_with_underscores}.md
            meta = doc.get("metadata", {})
            doc_url = meta.get("url", "")
            
            if is_drive_file:
                # For drive files: {client_slug}_{document_source}_{safe_title}.md
                title = doc.get("title", "untitled")
                safe_title = _normalize_slug(title)
                doc_id = f"{client_slug}_{safe_source}_{safe_title}.md"
                
                # Map sources to specific folders
                if safe_source in ["intake_form", "intake-form"]:
                    folder = "intake_form"
                else:
                    folder = "drive"
                
                filename = f"{client_slug}/{folder}/{doc_id}"
            elif doc_url:
                # For website files: {client_slug}_{document_source}_{domain}_{path_with_underscores}.md
                parsed = urlparse(doc_url)
                domain = parsed.netloc.replace("www.", "")  # Remove www.
                path = parsed.path.strip("/")  # Remove leading/trailing slashes
                
                if path:
                    # Replace slashes with underscores in path
                    path_with_underscores = path.replace("/", "_")
                    doc_id = f"{client_slug}_{safe_source}_{domain}_{path_with_underscores}.md"
                else:
                    # Homepage
                    doc_id = f"{client_slug}_{safe_source}_{domain}_index.md"
                
                # Use doc_id as filename (no subfolders)
                filename = f"{client_slug}/{safe_source}/{doc_id}"
            else:
                # Fallback for files without URL
                raw_id = str(doc.get("id", "unknown"))
                safe_id = raw_id.replace("/", "_")
                doc_id = f"{client_slug}_{safe_source}_{safe_id}.md"
                filename = f"{client_slug}/{safe_source}/{doc_id}"
            
            # Build comprehensive YAML frontmatter
            header_lines = ["---"]
            
            # Core identifiers
            header_lines.append(f"doc_id: \"{doc_id}\"")
            header_lines.append(f"client_slug: \"{client_slug}\"")
            header_lines.append(f"document_source: \"{doc.get('document_source', 'unknown')}\"")

            # Storage location (used later for Pinecone metadata + easy lookup in Supabase UI)
            header_lines.append(f"storage_bucket: \"{BUCKET_NAME}\"")
            header_lines.append(f"storage_path: \"{filename}\"")

            # Public "view" URL (same shape as storage_preview_url, but stored explicitly for DB column db_file_url)
            db_file_url = ""
            try:
                settings = get_settings()
                base = str(settings.supabase_agent_url or settings.supabase_url or "").rstrip("/")
                if base:
                    db_file_url = f"{base}/storage/v1/object/public/{BUCKET_NAME}/{quote(filename, safe='/')}"
            except Exception:
                db_file_url = ""
            if db_file_url:
                header_lines.append(f"storage_preview_url: \"{db_file_url}\"")

            # Original file type (before converting to .md)
            # - website sources come from HTML pages
            # - drive sources come from Drive mimeType (captured during listing)
            file_type = None
            try:
                ds_norm = str(doc.get("document_source", "") or "").strip().lower()
                if ds_norm == "website":
                    file_type = "html"
                else:
                    mime = ""
                    if isinstance(meta, dict) and meta.get("mimeType"):
                        mime = str(meta.get("mimeType") or "")
                    # Best-effort mapping
                    if mime == "application/pdf":
                        file_type = "pdf"
                    elif mime == "application/vnd.google-apps.document":
                        file_type = "gdoc"
                    elif mime == "application/vnd.google-apps.presentation":
                        file_type = "gslide"
                    elif mime == "application/vnd.google-apps.spreadsheet":
                        file_type = "gsheet"
                    elif "officedocument.wordprocessingml.document" in mime:
                        file_type = "docx"
                    elif "officedocument.presentationml.presentation" in mime:
                        file_type = "pptx"
                    elif "officedocument.spreadsheetml.sheet" in mime:
                        file_type = "xlsx"
                    elif mime.startswith("text/"):
                        # text/plain, text/markdown, etc.
                        file_type = mime.split("/", 1)[-1] or "txt"
                    else:
                        # Fall back to extension from the source title, if present
                        t = str(doc.get("title") or "")
                        if "." in t:
                            file_type = t.rsplit(".", 1)[-1].lower()
            except Exception:
                file_type = None

            if file_type:
                header_lines.append(f"file_type: \"{file_type}\"")
            
            # URL and title
            if doc_url:
                header_lines.append(f"url: \"{doc_url}\"")
                if meta.get("title"):
                    # Escape quotes in title
                    title_escaped = str(meta["title"]).replace('"', '\\"')
                    header_lines.append(f"title: \"{title_escaped}\"")
            
            # Content classification
            if doc.get("content_type"):
                header_lines.append(f"content_type: \"{doc['content_type']}\"")
            
            # 1-2 sentence summary for KB labeling
            doc_context = doc.get("document_context")
            if isinstance(doc_context, str) and doc_context.strip():
                # Use JSON string encoding (valid YAML 1.2) to avoid malformed frontmatter.
                header_lines.append(f"document_context: {json.dumps(doc_context.strip())}")

            # Content hash (hash of the markdown body BEFORE chunking)
            content_hash = compute_content_hash(content)
            header_lines.append(f"content_hash: \"{content_hash}\"")
            
            # Keywords (store as string for DB + easy grepping)
            keywords = doc.get("keywords", [])
            if keywords and isinstance(keywords, list):
                kw_str = ", ".join([str(k).strip() for k in keywords if str(k).strip()])
                if kw_str:
                    header_lines.append(f"keywords: {json.dumps(kw_str)}")
            
            # Ingestion timestamp
            ingested_at = time.strftime("%Y-%m-%dT%H:%M:%S.000000+00:00")
            header_lines.append(f"ingested_at: \"{ingested_at}\"")
            
            # Calculate sizes
            content_body_bytes = len(content.encode("utf-8"))
            header_lines.append(f"content_body_size: {content_body_bytes}")
            
            # Build content to calculate total size
            header_lines.append("---\n\n")
            full_content_temp = ("\n".join(header_lines) + content).encode("utf-8")
            total_file_size = len(full_content_temp)
            
            # Add size metadata (will be close to final size)
            header_lines.insert(-1, f"size: {total_file_size}")
            header_lines.insert(-1, f"content_length: {total_file_size}")

            # YAML frontmatter content (without the --- delimiters).
            # header_lines is: ["---", <yaml lines...>, "---\\n\\n"]
            metadata_header = "\n".join(header_lines[1:-1])
            
            # Rebuild final content
            full_content = ("\n".join(header_lines) + content).encode("utf-8")
            
            # Try to upload to Supabase Storage (or save locally if bucket doesn't exist)
            upload_success = False
            
            if bucket_ready:
                try:
                    supabase_client.upload_bytes(
                        bucket=BUCKET_NAME,
                        path=filename,
                        data=full_content,
                        content_type="text/markdown; charset=utf-8",
                        upsert=True  # Always overwrite
                    )
                    supabase_uploaded += 1
                    upload_success = True
                    
                    # Store doc_id and metadata for potential future use
                    doc["doc_id"] = doc_id
                    doc["_storage_path"] = filename
                    doc["_content_body_size"] = content_body_bytes
                    doc["_total_size"] = len(full_content)
                    doc["_content_hash"] = content_hash

                    # Upsert documents table row (ingested)
                    if db is not None:
                        try:
                            kw_str = ""
                            kws = doc.get("keywords") or []
                            if isinstance(kws, list):
                                kw_str = ", ".join([str(k).strip() for k in kws if str(k).strip()])
                            await db.upsert_documents(
                                docs=[
                                    {
                                        "doc_id": doc_id,
                                        "client_slug": client_slug,
                                        "ingestion_status": "ingested",
                                        "document_source": str(doc.get("document_source") or ""),
                                        "content_type": str(doc.get("content_type") or ""),
                                        "url": str(doc_url or ""),
                                        "keywords": kw_str or None,
                                        "document_context": (str(doc.get("document_context")).strip() if isinstance(doc.get("document_context"), str) else None),
                                        "content_hash": content_hash,
                                        "db_file_url": db_file_url or None,
                                        "metadata_header": metadata_header,
                                        "text": content,
                                    }
                                ]
                            )
                        except Exception:
                            # Don't fail ingestion on DB write issues
                            pass
                except Exception as e:
                    log("create.supabase.upload_error", {"doc_id": doc_id, "error": str(e)})
                    supabase_failed += 1
                    upload_success = False

                    # Record ingest error in documents table
                    if db is not None:
                        try:
                            await db.upsert_documents(
                                docs=[
                                    {
                                        "doc_id": doc_id,
                                        "client_slug": client_slug,
                                        "ingestion_status": "error - ingest",
                                        "document_source": str(doc.get("document_source") or ""),
                                        "content_type": str(doc.get("content_type") or ""),
                                        "url": str(doc_url or ""),
                                        "keywords": None,
                                        "document_context": (str(doc.get("document_context")).strip() if isinstance(doc.get("document_context"), str) else None),
                                        "content_hash": compute_content_hash(content),
                                        "db_file_url": db_file_url or None,
                                        "metadata_header": metadata_header,
                                        "text": content,
                                    }
                                ]
                            )
                        except Exception:
                            pass
            
            # If upload failed or bucket doesn't exist, save locally
            if not upload_success and local_backup_dir:
                try:
                    local_file_path = local_backup_dir / filename
                    local_file_path.parent.mkdir(parents=True, exist_ok=True)
                    local_file_path.write_bytes(full_content)
                    log("create.local_backup.saved", {"doc_id": doc_id, "path": str(local_file_path)})
                except Exception as e:
                    log("create.local_backup.error", {"doc_id": doc_id, "error": str(e)})
        except Exception as e:
            log("create.storage.upload_error", {"doc_id": doc.get("id", "unknown"), "error": str(e)})
            supabase_failed += 1
                    
        except Exception as e:
            log("create.storage.upload_error", {"doc_id": doc.get("id", "unknown"), "error": str(e)})
            supabase_failed += 1
    
    total_docs = len(documents)
    success = supabase_uploaded == total_docs and supabase_failed == 0
    
    log("create.supabase.uploaded", {
        "count": supabase_uploaded,
        "failed": supabase_failed,
        "total": total_docs,
        "client": client_slug,
        "success": success
    })
    
    if local_backup_dir and supabase_failed > 0:
        log("create.local_backup.complete", {
            "client": client_slug,
            "path": str(local_backup_dir),
            "files_backed_up": supabase_failed
        })

    return {
        "uploaded_to_supabase": supabase_uploaded,
        "failed": supabase_failed,
        "total": total_docs,
        "success": success,
        "local_backup_path": str(local_backup_dir) if local_backup_dir else None,
    }


async def _create_assistant(client_slug: str) -> Dict[str, Any]:
    """
    Create a Pinecone Assistant for the client and upload all documents.
    
    Creates an assistant named after the client slug and uploads all
    markdown files from Supabase Storage to populate the knowledge base.
    """
    settings = get_settings()
    
    if not settings.pinecone_api_key:
        log("create.assistant.not_configured", {"client": client_slug})
        return {"success": False, "reason": "Missing Pinecone API key"}
    
    BUCKET_NAME = "client-data-sources"
    assistant_name = client_slug
    
    # Initialize Pinecone
    pc = Pinecone(api_key=settings.pinecone_api_key)
    
    # Check if assistant already exists
    try:
        existing_assistants = pc.assistant.list_assistants()
        assistant_exists = any(
            a.name == assistant_name 
            for a in existing_assistants.get("assistants", [])
        )
        
        if assistant_exists:
            log("create.assistant.exists", {"client": client_slug, "assistant": assistant_name})
            return {
                "success": True,
                "assistant_name": assistant_name,
                "created": False,
                "reason": "Assistant already exists"
            }
    except Exception as e:
        log("create.assistant.check_error", {"client": client_slug, "error": str(e)})
        # Continue anyway - might be first time
    
    # Create assistant with custom instructions
    instructions = f"""You are a helpful AI assistant with knowledge about {client_slug}.
Answer questions based on the provided documents about this organization.
Be concise, accurate, and cite sources when possible.
If you don't know the answer, say so clearly."""
    
    try:
        assistant = pc.assistant.create_assistant(
            assistant_name=assistant_name,
            instructions=instructions,
            timeout=30
        )
        log("create.assistant.created", {
            "client": client_slug,
            "assistant": assistant_name,
            "status": assistant.status
        })
    except Exception as e:
        log("create.assistant.create_error", {"client": client_slug, "error": str(e)})
        return {"success": False, "error": str(e)}
    
    # Get Supabase client and list all markdown files
    supabase_client = get_supabase_storage_client()
    if not supabase_client:
        log("create.assistant.no_supabase", {"client": client_slug})
        return {"success": False, "reason": "Supabase Storage not configured"}
    
    # List all markdown files
    all_files = []
    for subfolder in ["website", "drive", "intake_form"]:
        prefix = f"{client_slug}/{subfolder}"
        
        try:
            objects = supabase_client.list_objects(BUCKET_NAME, prefix=prefix)
            for obj in objects:
                name = obj.get("name", "")
                if name and name.endswith(".md") and not name.endswith("/.keep"):
                    full_path = f"{prefix}/{name}"
                    all_files.append((full_path, name))
        except Exception as e:
            log("create.assistant.list_error", {"subfolder": subfolder, "error": str(e)})
    
    if not all_files:
        log("create.assistant.no_files", {"client": client_slug})
        return {
            "success": True,
            "assistant_name": assistant_name,
            "files_uploaded": 0,
            "warning": "No files to upload"
        }
    
    log("create.assistant.uploading", {
        "client": client_slug,
        "files": len(all_files)
    })
    
    # Upload files to assistant
    uploaded_count = 0
    failed_count = 0
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        for file_path, file_name in all_files:
            try:
                # Download from Supabase
                content_bytes = supabase_client.download_bytes(BUCKET_NAME, file_path)
                if not content_bytes:
                    failed_count += 1
                    continue
                
                # Save to temp file
                safe_filename = file_name.replace("/", "_")
                local_file = temp_path / safe_filename
                local_file.write_bytes(content_bytes)
                
                # Upload to assistant
                pc.assistant.Assistant(assistant_name=assistant_name).upload_file(
                    file_path=str(local_file),
                    timeout=None
                )
                
                uploaded_count += 1
                
            except Exception as e:
                log("create.assistant.upload_error", {
                    "file": file_name,
                    "error": str(e)
                })
                failed_count += 1
    
    log("create.assistant.complete", {
        "client": client_slug,
        "assistant": assistant_name,
        "uploaded": uploaded_count,
        "failed": failed_count
    })
    
    return {
        "success": True,
        "assistant_name": assistant_name,
        "files_uploaded": uploaded_count,
        "files_failed": failed_count,
        "created": True
    }


async def _vectorize_to_pinecone(
    client_slug: str,
    *,
    namespace_override: Optional[str] = None,
    index_override: Optional[str] = None,
    force_chunker: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Vectorize all markdown files from Supabase Storage to Pinecone.
    
    Reads files from client-data-sources bucket, chunks content,
    generates embeddings, and upserts to Pinecone index with client namespace.
    """
    settings = get_settings()
    
    BUCKET_NAME = "client-data-sources"

    # Pinecone (Records API via pinecone_kb_client)
    if not settings.pinecone_api_key:
        log("create.pinecone.not_configured", {"client": client_slug})
        return {"success": False, "reason": "Missing PINECONE_API_KEY"}

    namespace = (namespace_override or client_slug).strip() or client_slug
    effective_index_name = (index_override or settings.pinecone_kb_index_name).strip() or settings.pinecone_kb_index_name
    
    # Get Supabase Storage client
    supabase_client = get_supabase_storage_client()
    if not supabase_client:
        log("create.pinecone.no_supabase", {"client": client_slug})
        return {"success": False, "reason": "Supabase Storage not configured"}
    
    # List all markdown files for the client using the server-side Storage client (JWT/service-role).
    # This avoids brittle assumptions about list response shape and avoids using publishable keys.
    from ..clients.supabase_storage_client import SupabaseStorageClient

    storage = SupabaseStorageClient()

    def _normalize_object_name(*, client_slug: str, subfolder: str, name: str) -> str:
        """
        Supabase list_objects can return names either relative to prefix or already prefixed.
        Normalize to full object path within the bucket.
        """
        n = (name or "").strip().lstrip("/")
        if not n:
            return ""
        if n.startswith(f"{client_slug}/"):
            return n
        if n.startswith(f"{subfolder}/"):
            return f"{client_slug}/{n}"
        return f"{client_slug}/{subfolder}/{n}"
    
    all_files: List[str] = []
    for subfolder in ["website", "drive", "intake_form"]:
        prefix = f"{client_slug}/{subfolder}/"
        offset = 0
        while True:
            try:
                items = storage.list_objects(
                    BUCKET_NAME,
                    prefix=prefix,
                    limit=1000,
                    offset=offset,
                    sort_by={"column": "name", "order": "asc"},
                )
            except Exception as e:
                log("create.pinecone.list_error", {"subfolder": subfolder, "error": str(e)})
                break

            if not items:
                break

            files_this_page: List[str] = []
            for it in items:
                if not isinstance(it, dict):
                    continue
                # Folder entries have metadata=None; file entries typically have dict metadata.
                if it.get("metadata") is None:
                    continue
                name = str(it.get("name") or "")
                if not name.endswith(".md"):
                    continue
                full = _normalize_object_name(client_slug=client_slug, subfolder=subfolder, name=name)
                if full:
                    files_this_page.append(full)

            all_files.extend(files_this_page)

            # Pagination: if we got fewer than limit items, we're done.
            if len(items) < 1000:
                break
            offset += 1000
    
    if not all_files:
        log("create.pinecone.no_files", {"client": client_slug})
        return {"success": True, "files_processed": 0, "records_upserted": 0, "namespace": namespace, "index": effective_index_name}
    
    log("create.pinecone.processing", {"client": client_slug, "files": len(all_files)})
    
    # Process each file into documents, then upsert via pinecone_kb_client (integrated embedding).
    files_processed = 0
    docs: List[Dict[str, Any]] = []
    doc_ids: List[str] = []

    # DB: mark per-file embed errors so they show up in Supabase (instead of just logs).
    db_for_embed: SupabaseAgentsDbClient | None = None
    try:
        db_for_embed = SupabaseAgentsDbClient()
    except Exception:
        db_for_embed = None

    def _extract_frontmatter_block(text: str) -> tuple[str, str]:
        """
        Return (frontmatter, body). frontmatter does NOT include the --- delimiters.
        """
        s = text or ""
        if not s.startswith("---"):
            return "", s
        parts = s.split("---", 2)
        if len(parts) >= 3:
            return (parts[1] or "").strip(), (parts[2] or "").strip()
        return "", s

    def _extract_doc_id_from_frontmatter(frontmatter: str) -> Optional[str]:
        """
        Best-effort doc_id extraction even when YAML is malformed.
        """
        fm = frontmatter or ""
        m = re.search(r'(?m)^\s*doc_id:\s*"([^"]+)"\s*$', fm)
        if m:
            return m.group(1).strip()
        m2 = re.search(r"(?m)^\s*doc_id:\s*([^\n#]+)$", fm)
        if m2:
            return m2.group(1).strip().strip('"').strip("'")
        return None
    
    for file_path in all_files:
        try:
            # Download file
            content_bytes = storage.download_bytes(BUCKET_NAME, file_path)
            if not content_bytes:
                continue
            
            content_str = content_bytes.decode("utf-8")

            # Extract raw frontmatter/body first so we can still mark DB errors even if YAML parsing fails.
            frontmatter_raw, body = _extract_frontmatter_block(content_str)
            
            # Parse YAML frontmatter
            metadata: Dict[str, Any] = {}
            if frontmatter_raw:
                import yaml
                try:
                    metadata = yaml.safe_load(frontmatter_raw) or {}
                except Exception as e:
                    # YAML is malformed; mark this doc as embed-error in DB and continue.
                    doc_id_fallback = _extract_doc_id_from_frontmatter(frontmatter_raw)
                    if db_for_embed is not None and doc_id_fallback:
                        try:
                            await db_for_embed.upsert_documents(
                                docs=[
                                    {
                                        "doc_id": doc_id_fallback,
                                        "client_slug": client_slug,
                                        "ingestion_status": "embed - error",
                                        "ingestion_error": str(e),
                                        "metadata_header": frontmatter_raw or None,
                                    }
                                ]
                            )
                        except Exception:
                            pass
                    raise
            
            # Ensure doc_id exists
            doc_id = metadata.get("doc_id")
            if not doc_id:
                continue
            doc_ids.append(str(doc_id))
            
            # Normalize keywords to string list
            kws_in = metadata.get("keywords")
            if isinstance(kws_in, str) and kws_in.strip():
                kws = [k.strip().lower() for k in kws_in.split(",") if k.strip()]
            elif isinstance(kws_in, list):
                kws = [str(k).strip().lower() for k in kws_in if str(k).strip()]
            else:
                kws = []

            docs.append(
                {
                    "title": metadata.get("title") or "",
                    "url": metadata.get("url") or "",
                    "content_type": metadata.get("content_type") or "",
                    "document_source": metadata.get("document_source") or "unknown",
                    "keywords": kws,
                    "markdown": body,
                    # Stable per-file identity for record IDs + UI links
                    # Prefer storage_path (full Supabase key) so it is stable and directly traceable.
                    "file_key": metadata.get("storage_path") or metadata.get("file_key") or file_path,
                    # New storage metadata (for Pinecone record metadata)
                    "storage_bucket": metadata.get("storage_bucket") or "client-data-sources",
                    "storage_path": metadata.get("storage_path") or file_path,
                    "storage_preview_url": metadata.get("storage_preview_url") or "",
                    "db_file_url": metadata.get("storage_preview_url") or "",
                    "file_type": metadata.get("file_type") or ("html" if (metadata.get("document_source") == "website") else None),
                    "content_hash": metadata.get("content_hash") or "",
                    "document_context": metadata.get("document_context") or "",
                }
            )
            files_processed += 1
        
        except Exception as e:
            # Best-effort: mark embed error in DB for this specific file.
            try:
                if "frontmatter_raw" in locals():
                    doc_id_fallback = _extract_doc_id_from_frontmatter(frontmatter_raw)
                    if db_for_embed is not None and doc_id_fallback:
                        await db_for_embed.upsert_documents(
                            docs=[
                                {
                                    "doc_id": doc_id_fallback,
                                    "client_slug": client_slug,
                                    "ingestion_status": "embed - error",
                                    "ingestion_error": str(e),
                                    "metadata_header": frontmatter_raw or None,
                                }
                            ]
                        )
            except Exception:
                pass
            log("create.pinecone.file_error", {"file": file_path, "error": str(e)})
    
    log("create.pinecone.complete", {
        "client": client_slug,
        "files": files_processed,
        "docs": len(docs),
    })
    
    try:
        # Allow per-client chunker selection (A/B) via metadata.json or request payload.
        chunker_name = None
        try:
            # Prefer new metadata file; fall back to legacy metadata.json.
            supabase_meta = supabase_client.download_json(BUCKET_NAME, f"{client_slug}/supabase_storage_metadata.json")
            if not isinstance(supabase_meta, dict):
                supabase_meta = supabase_client.download_json(BUCKET_NAME, f"{client_slug}/metadata.json")
            if isinstance(supabase_meta, dict):
                c = supabase_meta.get("chunker") or (supabase_meta.get("chunking") or {}).get("chunker")
                if isinstance(c, str) and c.strip():
                    chunker_name = c.strip()
        except Exception:
            pass
        if isinstance(force_chunker, str) and force_chunker.strip():
            chunker_name = force_chunker.strip()

        upsert_res = pinecone_kb_client.upsert_documents(
            client_slug=namespace,
            documents=docs,
            chunker_name=chunker_name,
            index_name=effective_index_name,
        )

        # Mark documents embedded in DB
        try:
            if db_for_embed is not None and doc_ids:
                await db_for_embed.set_documents_status(doc_ids=doc_ids, status="embedded")
        except Exception:
            pass

        return {"success": True, "files_processed": files_processed, "doc_ids": doc_ids, "namespace": namespace, "index": effective_index_name, **upsert_res}
    except Exception as e:
        log("create.pinecone.error", {"client": client_slug, "error": str(e)})
        try:
            if db_for_embed is not None and doc_ids:
                await db_for_embed.set_documents_status(doc_ids=doc_ids, status="embed - error")
        except Exception:
            pass
        return {"success": False, "files_processed": files_processed, "error": str(e), "namespace": namespace, "index": effective_index_name}


async def _categorize_pages_parallel(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Categorize pages in parallel using LLM."""
    tasks = []
    
    # We only want to categorize pages that don't already have a specific content_type
    # But usually, scraped pages just have metadata.
    # We will iterate and create tasks.
    
    for p in pages:
        meta = p.get("metadata", {})
        source_url = meta.get("sourceURL") or p.get("url") or ""
        if not source_url:
            tasks.append(asyncio.sleep(0)) # No-op task
            continue
            
        # Create categorization task
        tasks.append(llm_client.categorize_url(source_url))

    results = await asyncio.gather(*tasks)
    
    # Update pages with results
    for i, res in enumerate(results):
        if res and isinstance(res, str):
            # If it was a sleep task, res is None. If it was categorization, it's a string.
            if "metadata" not in pages[i]:
                pages[i]["metadata"] = {}
            pages[i]["metadata"]["content_type"] = res
            
    return pages


@router.post("/create")
async def create_chatbot(payload: Dict[str, Any]) -> Dict[str, Any]:
    settings = get_settings()
    url: Optional[str] = payload.get("url")
    # Defaults requested: max 500 pages, depth 3
    limit: int = int(payload.get("limit") or 500)
    max_depth: int = int(payload.get("maxDepth") or payload.get("depth") or 3)
    include_paths: Optional[List[str]] = payload.get("includePaths")
    exclude_paths: Optional[List[str]] = payload.get("excludePaths")
    index_name: Optional[str] = payload.get("index")
    # Blog crawl limit: if the user requested "All" (high limit) but didn't specify blogLimit,
    # don't silently cap blog pages at 50.
    blog_limit_raw = payload.get("blogLimit")
    if blog_limit_raw is None and int(payload.get("limit") or 500) >= 1000:
        blog_limit = int(payload.get("limit") or 1000)
    else:
        blog_limit = int(blog_limit_raw or 50)
    client_slug: Optional[str] = payload.get("clientSlug") or payload.get("client_slug")
    client_name: Optional[str] = payload.get("clientName") or payload.get("client_name")
    skip_redis: bool = bool(payload.get("skipRedisSave"))
    drive_folder_input: Optional[str] = (
        payload.get("clientDriveFolder")
        or payload.get("driveFolderId")
        or payload.get("driveFolder")
        or payload.get("drive_folder")
    )
    # Optional chunking strategy (opt-in A/B). Examples:
    # - "char:1200:200" (default)
    # - "md_semantic_v1" or "md_semantic_v1:w350:m550:o80"
    requested_chunker: Optional[str] = payload.get("chunker") or payload.get("chunkerName") or payload.get("chunking")
    if isinstance(requested_chunker, dict):
        requested_chunker = requested_chunker.get("chunker")
    if isinstance(requested_chunker, str):
        requested_chunker = requested_chunker.strip() or None
    else:
        requested_chunker = None

    # Semantic embeddings A/B: keep Storage the same, but write to Pinecone under a -semantic namespace
    semantic_embeddings: bool = bool(payload.get("semanticEmbeddings") or payload.get("semantic_embeddings"))

    # Pinecone Assistant creation is disabled by default (opt-in only).
    create_assistant: bool = bool(
        payload.get("createAssistant")
        or payload.get("create_assistant")
        or payload.get("createPineconeAssistant")
    )

    # Validate required inputs
    if not client_slug:
        raise HTTPException(status_code=400, detail="clientSlug is required")
    if not url and not drive_folder_input:
        raise HTTPException(status_code=400, detail="Either url or clientDriveFolder is required")

    normalized_slug = _normalize_slug(client_slug)
    if not normalized_slug:
        raise HTTPException(status_code=400, detail="clientSlug must contain letters or numbers")

    # Canonical namespace/index are the client slug (no timestamp)
    namespace = normalized_slug
    index_name = normalized_slug

    # Canonical client fields for DB
    client_domain = normalized_slug
    website_field: Optional[str] = None
    if url:
        try:
            u = url.strip()
            if "://" not in u:
                u = "https://" + u
            parsed = urlparse(u)
            dom = (parsed.netloc or "").split("@")[-1].split(":")[0].lower().replace("www.", "").strip()
            if dom:
                client_domain = dom
                website_field = f"https://{dom}"
        except Exception:
            pass

    drive_folder_url_field: Optional[str] = None
    if drive_folder_input:
        raw = str(drive_folder_input).strip()
        if raw.startswith("http://") or raw.startswith("https://"):
            drive_folder_url_field = raw
        else:
            # treat as folder id
            drive_folder_url_field = f"https://drive.google.com/drive/folders/{raw}"

    # Upsert client row early (intake_form_url is populated later after drive scan)
    try:
        db = SupabaseAgentsDbClient()
        await db.upsert_client(
            client_slug=normalized_slug,
            client_domain=client_domain,
            client_name=client_name,
            website=website_field,
            drive_folder_url=drive_folder_url_field,
            intake_form_url=None,
        )
    except Exception:
        pass

    log(
        "create.request",
        {
            "url": url,
            "limit": limit,
            "max_depth": max_depth,
            "include": include_paths,
            "exclude": exclude_paths,
            "clientSlug": normalized_slug,
            "driveFolder": bool(drive_folder_input),
        },
    )

    pages: List[Dict[str, Any]] = []
    raw_status: Dict[str, Any] | None = None

    if url:
        # Two-phase crawl: main (non-blog) + blog (capped)
        main_excludes = list(exclude_paths or [])
        main_excludes.append(".*blog.*")  # exclude blog from main crawl

        log(
            "create.crawl.phase",
            {
                "phase": "main",
                "url": url,
                "limit": limit,
                "max_depth": max_depth,
                "include_paths": include_paths,
                "exclude_paths": main_excludes,
            },
        )
        # If user asks for very large crawls, broaden internal coverage.
        crawl_entire_domain = payload.get("crawlEntireDomain")
        if crawl_entire_domain is None and limit >= 1000:
            crawl_entire_domain = True

        main_pages, raw_status_main = await firecrawl_client.crawl_and_wait(
            url,
            limit,
            include_paths,
            main_excludes,
            max_depth,
            crawl_entire_domain=crawl_entire_domain,
            allow_subdomains=None,
        )
        log(
            "create.crawl.phase_result",
            {
                "phase": "main",
                "limit_requested": limit,
                "pages_returned": len(main_pages),
                "status": raw_status_main.get("status") if isinstance(raw_status_main, dict) else None,
            },
        )

        log(
            "create.crawl.phase",
            {
                "phase": "blog",
                "url": url,
                "limit": blog_limit,
                "max_depth": max_depth,
                "include_paths": ["blog"],
                "exclude_paths": exclude_paths,
            },
        )
        blog_pages, raw_status_blog = await firecrawl_client.crawl_and_wait(
            url,
            blog_limit,
            [".*blog.*"],
            exclude_paths,
            max_depth,
            crawl_entire_domain=crawl_entire_domain,
            allow_subdomains=None,
        )
        log(
            "create.crawl.phase_result",
            {
                "phase": "blog",
                "limit_requested": blog_limit,
                "pages_returned": len(blog_pages),
                "status": raw_status_blog.get("status") if isinstance(raw_status_blog, dict) else None,
            },
        )

        # Merge and deduplicate pages by sourceURL/url
        def _page_key(p: Dict[str, Any]) -> str:
            return (p.get("metadata", {}).get("sourceURL") or p.get("url") or "").rstrip("/")

        merged_pages: List[Dict[str, Any]] = []
        seen = set()
        for p in main_pages + blog_pages:
            k = _page_key(p)
            if not k or k in seen:
                continue
            seen.add(k)
            merged_pages.append(p)

        pages = merged_pages
        raw_status = {"main": raw_status_main, "blog": raw_status_blog}

    # Categorize pages
    if pages:
        log("create.categorize.start", {"count": len(pages)})
        pages = await _categorize_pages_parallel(pages)
        log("create.categorize.done", {"count": len(pages)})

        # Clean markdown after Firecrawl (before keyword extraction + Pinecone ingest)
        # Default: enabled. Set `"skipMarkdownClean": true` to disable.
        if not bool(payload.get("skipMarkdownClean")):
            log("create.markdown_clean.start", {"count": len(pages)})
            pages = await _clean_pages_markdown_parallel(pages)
            log("create.markdown_clean.done", {"count": len(pages)})

    pages_preview = [
        {"url": p.get("metadata", {}).get("sourceURL") or p.get("url"), "title": p.get("metadata", {}).get("title"), "category": p.get("metadata", {}).get("content_type")}
        for p in pages[:5]
    ]
    log("create.crawl.preview", {"preview": pages_preview, "count": len(pages)})

    # -------------------------------------------------------------------------
    # 2. Add Google Drive Content (if requested)
    # -------------------------------------------------------------------------
    drive_docs: List[Dict[str, Any]] = []
    if drive_folder_input:
        try:
            folder_id = extract_drive_folder_id(drive_folder_input)
            log("create.drive.start", {"folder_id": folder_id})
            
            # Credentials path - robust resolution
            creds_path = Path("service_account.json")
            if not creds_path.exists():
                creds_path = Path("../service_account.json")
            
            if not creds_path.exists():
                # Try absolute path based on file location
                # backend/app/routes/create.py -> backend/app/routes/ -> backend/app/ -> backend/ -> root
                creds_path = Path(__file__).resolve().parent.parent.parent.parent / "service_account.json"

            if not creds_path.exists():
                log("create.drive.creds_missing", {"path": str(creds_path)})
                raise FileNotFoundError(f"service_account.json not found. Checked: {creds_path}")

            # build_drive_documents returns (documents, summary, files)
            # It requires namespace and credentials path
            # IMPORTANT: Do not truncate Drive doc text here; we write it to Supabase Storage as `.md`
            # and later vectorize from Storage. Truncation would permanently drop the rest of the document.
            raw_drive_docs, summary, _ = build_drive_documents(folder_id, namespace, creds_path, text_max_chars=None)
            log("create.drive.fetched", {"count": len(raw_drive_docs), "summary": summary})
            
            # categorize_drive_documents modifies in-place and takes only list
            await categorize_drive_documents(raw_drive_docs)
            drive_docs = raw_drive_docs
            log("create.drive.categorized", {"count": len(drive_docs)})

            # Update clients.intake_form_url after we've scanned the drive folder.
            try:
                intake_url = None
                for d in drive_docs:
                    meta = d.get("metadata") or {}
                    if not isinstance(meta, dict):
                        continue
                    if str(meta.get("document_source") or "").strip() == "intake_form":
                        intake_url = str(meta.get("url") or "") or str((d.get("content") or {}).get("url") or "")
                        intake_url = intake_url.strip() if intake_url else None
                        if intake_url:
                            break
                if intake_url:
                    db = SupabaseAgentsDbClient()
                    await db.upsert_client(
                        client_slug=normalized_slug,
                        client_domain=client_domain,
                        client_name=client_name,
                        website=website_field,
                        drive_folder_url=drive_folder_url_field,
                        intake_form_url=intake_url,
                    )
            except Exception:
                pass
            
        except Exception as e:
            log("create.drive.error", {"error": str(e)})
            # We don't fail the whole request if Drive fails, just log it
            pass

    # -------------------------------------------------------------------------
    # 3. Normalize & Prepare Documents
    # -------------------------------------------------------------------------
    final_documents: List[Dict[str, Any]] = []

    # Process Website Pages
    for p in pages:
        # Firecrawl returns content in 'markdown' or 'html'
        # We prefer markdown
        text_content = p.get("markdown", "") or p.get("text", "") or ""
        # If no markdown/text but HTML exists, we might want to use that (or skip)
        # For now, let's skip empty content
        if not text_content:
            continue
            
        meta = p.get("metadata", {})
        source_url = meta.get("sourceURL") or p.get("url") or ""
        title = meta.get("title") or "Untitled Page"
        
        # Use the categorized content_type if available, else default
        content_type = meta.get("content_type", "website_pages")
        
        doc = {
            "id": _doc_id_from_url(source_url),
            "url": source_url,
            "title": title,
            "content": text_content,
            "document_source": "website",
            "content_type": content_type,
            "markdown": p.get("markdown", ""), # Keep raw markdown for DO
            "html": p.get("html", ""),
            "metadata": meta
        }
        final_documents.append(doc)

    # Process Drive Docs
    for d in drive_docs:
        # Drive docs are already structured by our helper
        # We just ensure they have the right fields
        d_id = d.get("id")
        if not d_id:
            continue

        # Skip self-generated briefs
        name_fields = [
            d.get("title", ""),
            d.get("filename", ""),
            d.get("name", ""),
            d.get("metadata", {}).get("title", ""),
            d.get("metadata", {}).get("filename", ""),
        ]
        if any("client_brief" in str(n).lower() for n in name_fields if n):
            log("create.drive.skip_client_brief", {"id": d_id, "name": name_fields})
            continue

        # Title is in metadata or content, not top-level
        meta = d.get("metadata", {})
        title = meta.get("title") or d.get("content", {}).get("title") or "Untitled Drive Doc"
        
        # Preserve document_source from metadata (intake_form vs client_materials)
        doc_source = meta.get("document_source", "drive")

        final_documents.append({
            "id": d_id,
            "url": d.get("url", ""),
            "title": title,
            "content": d.get("content", ""),
            "document_source": doc_source,
            "content_type": meta.get("content_type", "other"),
            "markdown": d.get("content", ""), # Drive content is text, treat as markdown
            "metadata": meta
        })

    log("create.prepare.summary", {"total_docs": len(final_documents)})

    # -------------------------------------------------------------------------
    # 3. Add per-file keywords (LLM) for Pinecone metadata filtering
    # -------------------------------------------------------------------------
    if final_documents:
        # Run per-doc LLM work concurrently with a bounded semaphore.
        enrich_sem = asyncio.Semaphore(12)
        progress_lock = asyncio.Lock()
        progress_counter = {"done": 0, "errors": 0}
        enrichment_start_time = time.time()

        async def _enrich_one(d: Dict[str, Any], idx: int) -> None:
            async with enrich_sem:
                doc_url = str(d.get("url") or (d.get("metadata") or {}).get("url") or "")
                doc_title = str(d.get("title") or (d.get("metadata") or {}).get("title") or "")[:50]
                doc_start_time = time.time()
                
                title = str(d.get("title") or (d.get("metadata") or {}).get("title") or "")
                body = str(d.get("markdown") or d.get("content") or "")
                
                try:
                    ctx = await _extract_document_context_for_doc(body=body)
                    if isinstance(ctx, str) and ctx.strip():
                        d["document_context"] = ctx.strip()
                except Exception as e:
                    async with progress_lock:
                        progress_counter["errors"] += 1
                    log("create.document_context.error", {"idx": idx, "url": doc_url, "title": doc_title, "error": str(e)})
                try:
                    kws = await _extract_keywords_for_doc(title=title, body=body)
                    if kws:
                        d["keywords"] = kws
                except Exception as e:
                    async with progress_lock:
                        progress_counter["errors"] += 1
                    log("create.keywords.error", {"idx": idx, "url": doc_url, "title": doc_title, "error": str(e)})
                
                async with progress_lock:
                    progress_counter["done"] += 1
                    done = progress_counter["done"]
                    total = len(final_documents)
                    elapsed = time.time() - enrichment_start_time
                    doc_elapsed = time.time() - doc_start_time
                    
                    # Log every 25 documents or every 10% completion
                    if done % 25 == 0 or done % max(1, total // 10) == 0 or done == total:
                        pct = (done / total) * 100
                        avg_time = elapsed / done if done > 0 else 0
                        est_remaining = (total - done) * avg_time if done > 0 else 0
                        log(
                            "create.enrichment_progress",
                            {
                                "done": done,
                                "total": total,
                                "percent": round(pct, 1),
                                "errors": progress_counter["errors"],
                                "elapsed_sec": round(elapsed, 1),
                                "avg_sec_per_doc": round(avg_time, 2),
                                "est_remaining_sec": round(est_remaining, 1),
                                "current_doc_time_sec": round(doc_elapsed, 2),
                                "current_url": doc_url[:100],
                                "current_title": doc_title,
                            },
                        )

        log("create.enrichment_start", {"docs": len(final_documents), "sem": 12})
        await asyncio.gather(*[_enrich_one(d, idx) for idx, d in enumerate(final_documents)])
        total_elapsed = time.time() - enrichment_start_time
        log(
            "create.enrichment_done",
            {
                "docs": len(final_documents),
                "elapsed_sec": round(total_elapsed, 1),
                "errors": progress_counter["errors"],
                "avg_sec_per_doc": round(total_elapsed / len(final_documents), 2) if final_documents else 0,
            },
        )

    # -------------------------------------------------------------------------
    # 4. Ingest (Pinecone + optional Spaces raw store)
    # -------------------------------------------------------------------------
    storage_info: Dict[str, Any] = {}
    if final_documents:
        try:
            storage_info = await _upload_to_storage(client_slug, final_documents)
            
            # -------------------------------------------------------------------------
            # 5. Save Metadata for UI (Indexes List)
            # -------------------------------------------------------------------------
            # We write TWO metadata files (do not overwrite legacy metadata.json):
            # - supabase_storage_metadata.json: derived from what we just uploaded to Storage
            # - pinecone_namespace_metadata.json: derived from Pinecone namespace after vectorization
            website_docs_list = [d for d in final_documents if d.get("document_source") == "website"]
            drive_docs_list = [d for d in final_documents if d.get("document_source") in ["drive", "client_materials"]]
            intake_form_docs = len([d for d in final_documents if d.get("document_source") in ["intake_form", "intake-form"]])

            def _by_content_type(docs: List[Dict[str, Any]]) -> Dict[str, int]:
                counts: Dict[str, int] = {}
                for doc in docs:
                    ct = doc.get("content_type") or doc.get("metadata", {}).get("content_type") or "other"
                    counts[ct] = counts.get(ct, 0) + 1
                return counts

            website_docs = {"total": len(website_docs_list), "by_content_type": _by_content_type(website_docs_list)}
            drive_docs_count = {"total": len(drive_docs_list), "by_content_type": _by_content_type(drive_docs_list)}

            homepage_doc = next(
                (
                    d
                    for d in website_docs_list
                    if (d.get("content_type") or d.get("metadata", {}).get("content_type")) in ["homepage", "home", "home page"]
                ),
                None,
            )
            homepage_meta = homepage_doc.get("metadata", {}) if homepage_doc else {}
            homepage_title = homepage_meta.get("title") or (homepage_doc or {}).get("title") or client_slug
            homepage_favicon = homepage_meta.get("favicon") or homepage_meta.get("ogImage")

            supabase_storage_metadata_file: Dict[str, Any] = {
                "website_url": url,
                "drive_url": drive_folder_input or "",
                "client_slug": client_slug,
                "client_name": client_name or None,
                "website_docs": website_docs,
                "intake_form_docs": intake_form_docs,
                "drive_docs": drive_docs_count,
                "createdAt": time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "metadata": {"title": homepage_title, **({"favicon": homepage_favicon} if homepage_favicon else {})},
                # Persist chosen chunker so bulk scripts + future re-ingests can keep behavior consistent.
                "chunker": requested_chunker or "char:1200:200",
                "source": "supabase_storage",
            }

            # Upload supabase_storage_metadata.json to Supabase Storage
            supabase_client = get_supabase_storage_client()
            BUCKET_NAME = "client-data-sources"
            if supabase_client:
                try:
                    supabase_client.upload_json(
                        bucket=BUCKET_NAME,
                        path=f"{client_slug}/supabase_storage_metadata.json",
                        payload=supabase_storage_metadata_file,
                        upsert=True
                    )
                    log("create.supabase.metadata_saved", {"client": client_slug, "bucket": BUCKET_NAME, "key": "supabase_storage_metadata.json"})
                except Exception as e:
                    log("create.supabase.metadata_error", {"error": str(e), "client": client_slug})

            # -------------------------------------------------------------------------
            # 6. Vectorize to Pinecone (only if Supabase upload was successful)
            # -------------------------------------------------------------------------
            pinecone_info: Dict[str, Any] = {}
            if storage_info.get("success"):
                try:
                    effective_namespace = f"{client_slug}-semantic" if semantic_embeddings else client_slug
                    # Always use the primary KB index. Semantic runs are isolated by namespace suffix only.
                    effective_index = settings.pinecone_kb_index_name
                    force_chunker = "md_semantic_v1" if semantic_embeddings else None
                    pinecone_info = await _vectorize_to_pinecone(
                        client_slug,
                        namespace_override=effective_namespace,
                        index_override=effective_index,
                        force_chunker=force_chunker,
                    )
                    if pinecone_info.get("success"):
                        log("create.pinecone.success", {
                            "client": client_slug,
                            "files": pinecone_info.get("files_processed", 0),
                            "records": pinecone_info.get("records_upserted", 0),
                            "namespace": pinecone_info.get("namespace")
                        })
                    else:
                        log("create.pinecone.failed", {
                            "client": client_slug,
                            "reason": pinecone_info.get("reason", "Unknown")
                        })
                except Exception as e:
                    log("create.pinecone.error", {"client": client_slug, "error": str(e)})
                    pinecone_info = {"success": False, "error": str(e)}

            # After vectorization, write pinecone_namespace_metadata.json (authoritative for UI display)
            if supabase_client and storage_info.get("success") and pinecone_info.get("success"):
                try:
                    effective_namespace = pinecone_info.get("namespace") or client_slug
                    effective_index = pinecone_info.get("index") or settings.pinecone_kb_index_name
                    pinecone_meta = pinecone_kb_client.build_onboarding_metadata_report(
                        client_slug=str(effective_namespace),
                        website_url=url,
                        drive_url=drive_folder_input or "",
                        index_name=str(effective_index),
                        wait_after_upsert_s=1.5,
                    )
                    if isinstance(pinecone_meta, dict):
                        # Ensure Pinecone metadata carries favicon from Supabase metadata (for UI logos).
                        # Pinecone namespace enumeration may not reliably recover favicons.
                        sb_meta = supabase_storage_metadata_file.get("metadata") if isinstance(supabase_storage_metadata_file, dict) else None
                        pc_meta = pinecone_meta.get("metadata")
                        if not isinstance(pc_meta, dict):
                            pc_meta = {}
                            pinecone_meta["metadata"] = pc_meta
                        if isinstance(sb_meta, dict) and sb_meta.get("favicon") and not pc_meta.get("favicon"):
                            pc_meta["favicon"] = sb_meta.get("favicon")

                        # Preserve chunker + a marker
                        pinecone_meta["chunker"] = pinecone_meta.get("chunker") or (requested_chunker or "char:1200:200")
                        pinecone_meta["source"] = "pinecone_namespace"
                        pinecone_meta["base_client_slug"] = client_slug
                        pinecone_meta["semantic_embeddings"] = bool(semantic_embeddings)
                        pinecone_meta["client_name"] = client_name or pinecone_meta.get("client_name") or None

                        # Workaround for side-by-side comparisons in the UI:
                        # Create a separate "index card" by writing metadata under {client_slug}-semantic/
                        # so /indexes discovers it as a distinct entry (it lists top-level prefixes in Storage).
                        if semantic_embeddings and isinstance(effective_namespace, str) and effective_namespace.strip():
                            try:
                                sem_slug = effective_namespace.strip()
                                sem_meta = json.loads(json.dumps(pinecone_meta))  # cheap deep copy (dict is JSON-safe)
                                sem_meta["client_slug"] = sem_slug
                                sem_meta["base_client_slug"] = client_slug
                                sem_meta["semantic_embeddings"] = True
                                ui_meta = sem_meta.get("metadata")
                                if not isinstance(ui_meta, dict):
                                    ui_meta = {}
                                    sem_meta["metadata"] = ui_meta
                                # Make the card title visually distinct
                                title0 = str(ui_meta.get("title") or "").strip()
                                if title0 and "(semantic)" not in title0.lower():
                                    ui_meta["title"] = f"{title0} (semantic)"
                                elif not title0:
                                    ui_meta["title"] = f"{client_slug} (semantic)"
                                supabase_client.upload_json(
                                    bucket=BUCKET_NAME,
                                    path=f"{sem_slug}/pinecone_namespace_metadata.json",
                                    payload=sem_meta,
                                    upsert=True,
                                )
                                log("create.supabase.metadata_saved", {"client": sem_slug, "bucket": BUCKET_NAME, "key": "pinecone_namespace_metadata.json"})
                            except Exception:
                                pass

                        supabase_client.upload_json(
                            bucket=BUCKET_NAME,
                            path=f"{client_slug}/pinecone_namespace_metadata.json",
                            payload=pinecone_meta,
                            upsert=True,
                        )
                        log("create.supabase.metadata_saved", {"client": client_slug, "bucket": BUCKET_NAME, "key": "pinecone_namespace_metadata.json"})
                except Exception as e:
                    log("create.pinecone.report_error", {"error": str(e), "client": client_slug})

            # -------------------------------------------------------------------------
            # 7. (Optional) Create Pinecone Assistant (DISABLED BY DEFAULT)
            # -------------------------------------------------------------------------
            assistant_info: Dict[str, Any] = {"success": False, "skipped": True, "reason": "Assistant creation disabled by default"}
            if create_assistant and storage_info.get("success") and pinecone_info.get("success"):
                try:
                    assistant_info = await _create_assistant(client_slug)
                    if assistant_info.get("success"):
                        if assistant_info.get("created"):
                            log("create.assistant.success", {
                                "client": client_slug,
                                "assistant": assistant_info.get("assistant_name"),
                                "files": assistant_info.get("files_uploaded", 0)
                            })
                        else:
                            log("create.assistant.skipped", {
                                "client": client_slug,
                                "reason": assistant_info.get("reason", "Already exists")
                            })
                    else:
                        log("create.assistant.failed", {
                            "client": client_slug,
                            "reason": assistant_info.get("reason", "Unknown")
                        })
                except Exception as e:
                    log("create.assistant.error", {"client": client_slug, "error": str(e)})
                    assistant_info = {"success": False, "error": str(e)}
            elif not create_assistant:
                log("create.assistant.disabled", {"client": client_slug})

        except Exception as e:
            log("create.ingest.error", {"error": str(e)})
            # Don't fail the request if ingestion fails, just log it

    # Keep both keys for frontend compatibility
    return {
        "success": True,
        "status": "success",
        "index": settings.pinecone_kb_index_name,
        "namespace": namespace,
        "pages_processed": len(pages),
        "drive_docs_processed": len(drive_docs),
        "total_documents": len(final_documents),
        "storage": storage_info if 'storage_info' in locals() else {},
        "pinecone": pinecone_info if 'pinecone_info' in locals() else {},
        "assistant": assistant_info if 'assistant_info' in locals() else {},
    }
