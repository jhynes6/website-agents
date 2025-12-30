import json
import asyncio
import logging
import os
import time
import re
from pathlib import Path
from urllib.parse import urlparse
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..clients.firecrawl import firecrawl_client
from ..clients.llm import llm_client
from ..clients.pinecone_client import pinecone_kb_client
from ..clients.digital_ocean_client import DigitalOceanClient
from ..clients.supabase_agent_storage_client import SupabaseAgentStorageClient
from ..config import get_settings
from ..logging import log, logger
from ..services.drive_ingest import (
    build_drive_documents,
    categorize_drive_documents,
    extract_drive_folder_id,
)

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
do_client = DigitalOceanClient()

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

    # Keep prompt bounded: head + tail to include footer patterns
    head = md[:8000]
    tail = md[-2000:] if len(md) > 10000 else ""
    if tail:
        md_in = head + "\n\n---\n\n[FOOTER_CONTEXT]\n" + tail
    else:
        md_in = head

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
    user = f"URL: {url}\nTitle: {title}\n\nMARKDOWN:\n{md_in}"

    try:
        resp = await llm_client.chat(
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.1,
            max_tokens=1400,
            model="gpt-4o-mini",
        )
        out = (resp["choices"][0]["message"]["content"] or "").strip()
        # Strip accidental fences/frontmatter if the model disobeys
        out = re.sub(r"(?s)^```.*?\n", "", out).strip()
        out = re.sub(r"(?s)\n```$", "", out).strip()
        out = re.sub(r"(?s)^---\n.*?\n---\n", "", out).strip()
        # Final deterministic cleanup (removes any leftover links/images/CTAs)
        return out
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
            
            # Keywords (if available)
            keywords = doc.get("keywords", [])
            if keywords and isinstance(keywords, list):
                # YAML list format
                header_lines.append("keywords:")
                for kw in keywords:
                    header_lines.append(f"  - \"{kw}\"")
            
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
                except Exception as e:
                    log("create.supabase.upload_error", {"doc_id": doc_id, "error": str(e)})
                    supabase_failed += 1
                    upload_success = False
            
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
    blog_limit: int = int(payload.get("blogLimit") or 50)
    client_slug: Optional[str] = payload.get("clientSlug") or payload.get("client_slug")
    skip_redis: bool = bool(payload.get("skipRedisSave"))
    drive_folder_input: Optional[str] = (
        payload.get("clientDriveFolder")
        or payload.get("driveFolderId")
        or payload.get("driveFolder")
        or payload.get("drive_folder")
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
        main_pages, raw_status_main = await firecrawl_client.crawl_and_wait(
            url,
            limit,
            include_paths,
            main_excludes,
            max_depth,
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
            raw_drive_docs, summary, _ = build_drive_documents(folder_id, namespace, creds_path)
            log("create.drive.fetched", {"count": len(raw_drive_docs), "summary": summary})
            
            # categorize_drive_documents modifies in-place and takes only list
            await categorize_drive_documents(raw_drive_docs)
            drive_docs = raw_drive_docs
            log("create.drive.categorized", {"count": len(drive_docs)})
            
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
        # Keep this conservative to avoid cost spikes: 1 request per doc
        keyword_tasks = []
        for d in final_documents:
            title = str(d.get("title") or (d.get("metadata") or {}).get("title") or "")
            body = str(d.get("markdown") or d.get("content") or "")
            keyword_tasks.append(_extract_keywords_for_doc(title=title, body=body))
        keywords_list = await asyncio.gather(*keyword_tasks)
        for d, kws in zip(final_documents, keywords_list):
            if kws:
                d["keywords"] = kws

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
            # Prefer Pinecone-based report (authoritative, post-ingest)
            # Strategy: list_paginated -> fetch -> dedupe by file_key.
            metadata_file: Dict[str, Any]
            try:
                metadata_file = pinecone_kb_client.build_onboarding_metadata_report(
                    client_slug=client_slug,
                    website_url=url,
                    drive_url=drive_folder_input or "",
                    wait_after_upsert_s=1.5,  # allow for eventual consistency right after upsert
                )
            except Exception as e:
                # Fallback to pre-ingest counts if Pinecone enumeration fails
                log("create.pinecone.report_error", {"error": str(e), "client": client_slug})

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

                metadata_file = {
                    "website_url": url,
                    "drive_url": drive_folder_input or "",
                    "client_slug": client_slug,
                    "website_docs": website_docs,
                    "intake_form_docs": intake_form_docs,
                    "drive_docs": drive_docs_count,
                    "createdAt": time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                    "metadata": {"title": homepage_title, **({"favicon": homepage_favicon} if homepage_favicon else {})},
                }

            # Upload metadata to Supabase Storage
            supabase_client = get_supabase_storage_client()
            BUCKET_NAME = "client-data-sources"
            if supabase_client:
                try:
                    supabase_client.upload_json(
                        bucket=BUCKET_NAME,
                        path=f"{client_slug}/metadata.json",
                        payload=metadata_file,
                        upsert=True
                    )
                    log("create.supabase.metadata_saved", {"client": client_slug, "bucket": BUCKET_NAME})
                except Exception as e:
                    log("create.supabase.metadata_error", {"error": str(e), "client": client_slug})

            # -------------------------------------------------------------------------
            # 6. Store metadata in Supabase Storage (Pinecone vectorization is separate)
            # -------------------------------------------------------------------------

        except Exception as e:
            log("create.ingest.error", {"error": str(e)})
            # Don't fail the request if ingestion fails, just log it

    # Keep both keys for frontend compatibility
    return {
        "success": True,
        "status": "success",
        "index": get_settings().pinecone_kb_index_name,
        "namespace": namespace,
        "pages_processed": len(pages),
        "drive_docs_processed": len(drive_docs),
        "total_documents": len(final_documents),
        "storage": storage_info,
    }
