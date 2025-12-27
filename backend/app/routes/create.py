import json
import asyncio
import logging
import os
import time
from pathlib import Path
from urllib.parse import urlparse
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..clients.firecrawl import firecrawl_client
from ..clients.llm import llm_client
from ..clients.digital_ocean_client import DigitalOceanClient
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


async def _ingest_to_digitalocean(client_slug: str, documents: List[Dict[str, Any]]) -> tuple[Optional[str], bool]:
    """
    Uploads documents to DigitalOcean Spaces and creates/updates a Knowledge Base.
    Returns (kb_uuid, source_added_flag).
    """
    if not do_client.settings.digitalocean_token:
        return None, False

    kb_uuid = None
    source_added = False
    
    # 1. Ensure directory structure exists in Spaces BEFORE creating KB
    # This ensures the prefix exists when we try to add it as a data source.
    if do_client.settings.digitalocean_spaces_bucket:
        try:
            for subfolder in ["drive", "intake_form", "website"]:
                # Upload empty object with trailing slash to create "folder"
                folder_key = f"{client_slug}/{subfolder}/"
                do_client.upload_file_content(b"", folder_key, content_type="application/x-directory")
            log("create.do.folders_created", {"client": client_slug})
        except Exception as e:
            log("create.do.folder_error", {"error": str(e)})
            # Continue anyway, as file uploads might still work or folder might exist

    # Prepare initial data source if bucket is configured
    initial_sources = []
    if do_client.settings.digitalocean_spaces_bucket:
        initial_sources.append({
            "spaces_data_source": {
                "bucket_name": do_client.settings.digitalocean_spaces_bucket,
                "region": do_client.settings.digitalocean_spaces_region,
                "item_path": f"{client_slug}/"
            }
        })
        
    # 2. Create or Get Knowledge Base
    kb = await do_client.ensure_client_kb(slug=client_slug, data_sources=initial_sources)
    if kb:
        kb_uuid = kb.get("uuid")
        log("create.do.kb_created", {"uuid": kb_uuid, "name": client_slug})
        
        # 3. Always verify/fix source to ensure correct prefix
        if do_client.settings.digitalocean_spaces_bucket:
             source_added, source_newly_created = await do_client.ensure_correct_spaces_source(
                 kb_uuid, 
                 do_client.settings.digitalocean_spaces_bucket, 
                 f"{client_slug}/"
             )
    
    if not kb_uuid:
        log("create.do.error", {"message": "Failed to resolve Knowledge Base UUID"})
        # We proceed to upload even if KB creation fails, so files are in Spaces
        # but return None for UUID
    
    # Upload files to Spaces
    uploaded_count = 0
    if do_client.settings.digitalocean_spaces_bucket:
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
                
                # Sanitized filename
                # User requested to strip 'www.' from the filename for Spaces
                raw_id = str(doc.get("id", "unknown"))
                if raw_id.startswith("www."):
                    raw_id = raw_id[4:]
                
                doc_id = raw_id.replace("/", "_")
                
                # Build Structured Path for Filtering
                # {client_slug}/{document_source}/{filename}
                doc_source_raw = doc.get("document_source", "unknown")
                safe_source = _normalize_slug(doc_source_raw)
                
                # Check if it is a drive file (by ID or source)
                is_drive_file = str(doc.get("id", "")).startswith("drive_") or safe_source in ["drive", "intake_form", "intake-form", "client_materials"]
                
                if is_drive_file:
                     title = doc.get("title", "untitled")
                     # Sanitize title
                     safe_title = _normalize_slug(title)
                     
                     # Map sources to specific folders
                     if safe_source in ["intake_form", "intake-form"]:
                         folder = "intake_form" # Keep underscore for folder
                     else:
                         folder = "drive" # Map 'client_materials' and others to 'drive'
                         
                     filename = f"{client_slug}/{folder}/drive_{safe_title}.md"
                else:
                     filename = f"{client_slug}/{safe_source}/{doc_id}.md"
                
                # Add metadata header to markdown
                meta = doc.get("metadata", {})
                header_lines = ["---"]
                header_lines.append(f"client_slug: {client_slug}") # Tag with client slug
                if meta.get("url"):
                    header_lines.append(f"url: {meta['url']}")
                if meta.get("title"):
                    header_lines.append(f"title: {meta['title']}")
                
                # Add document classification
                if doc.get("content_type"):
                    header_lines.append(f"content_type: {doc['content_type']}")
                if doc.get("document_source"):
                    header_lines.append(f"document_source: {doc['document_source']}")

                header_lines.append("---\n\n")
                
                full_content = ("\n".join(header_lines) + content).encode("utf-8")
                
                res = do_client.upload_file_content(full_content, filename)
                if res:
                    uploaded_count += 1
            except Exception as e:
                log("create.do.upload_error", {"doc_id": doc.get("id"), "error": str(e)})
        
        # -------------------------------------------------------------------------
        # Skip icon upload as user requested
        # -------------------------------------------------------------------------
        # We now rely on metadata.json favicon link
        # 
        # log("create.do.uploaded", {"count": uploaded_count, "client": client_slug})
        # ... (removed icon upload logic)

    else:
        log("create.do.skipped_upload", {"reason": "No Spaces bucket configured"})

    if not kb_uuid:
        return None, False

    # -------------------------------------------------------------------------
    # 5. Save Metadata for UI (Indexes List)
    # -------------------------------------------------------------------------
    if do_client.settings.digitalocean_spaces_bucket:
        try:
            # Prepare metadata object
            metadata_file = {
                "url": url,
                "client_slug": client_slug,
                "pagesCrawled": len(pages) if 'pages' in locals() else 0,
                "createdAt": time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "metadata": {
                    "title": pages_preview[0]["title"] if pages_preview else client_slug,
                    "indexName": index_name
                }
            }
            
            # Find favicon/ogImage
            for doc in final_documents:
                meta = doc.get("metadata", {})
                if meta.get("favicon"):
                    metadata_file["metadata"]["favicon"] = meta["favicon"]
                    break
                if meta.get("ogImage"):
                    metadata_file["metadata"]["ogImage"] = meta["ogImage"]
            
            if "favicon" not in metadata_file["metadata"]:
                 # Try to find it in homepage doc
                 for doc in final_documents:
                     if doc.get("content_type") in ["homepage", "home", "home page"]:
                         f = doc.get("metadata", {}).get("favicon")
                         if f: 
                             metadata_file["metadata"]["favicon"] = f
                             break

            # Upload to Spaces
            do_client.upload_file_content(
                json.dumps(metadata_file), 
                f"{client_slug}/metadata.json", 
                content_type="application/json"
            )
            log("create.do.metadata_saved", {"client": client_slug})
            logger.info(f"Metadata file: {metadata_file}")
        except Exception as e:
            log("create.do.metadata_error", {"error": str(e)})

    # Re-index check
    if source_added and not source_newly_created and uploaded_count > 0 and do_client.settings.digitalocean_spaces_bucket:
        # Re-index if we added new files to an existing source
        log("create.do.trigger_reindex", {"kb": kb_uuid, "client": client_slug})
        reindex_success = await do_client.trigger_reindexing(
            kb_uuid,
            do_client.settings.digitalocean_spaces_bucket,
            prefix=f"{client_slug}/"
        )
        if not reindex_success:
            # If reindex failed (e.g. source not found), try adding the source
            log("create.do.reindex_failed_adding", {"kb": kb_uuid})
            await do_client.add_spaces_source(
                kb_uuid, 
                do_client.settings.digitalocean_spaces_bucket, 
                prefix=f"{client_slug}/"
            )
    
    return kb_uuid, source_added


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
    # 4. Ingest to DigitalOcean
    # -------------------------------------------------------------------------
    do_kb_uuid = None
    do_source_added = False
    if final_documents:
        try:
            do_kb_uuid, do_source_added = await _ingest_to_digitalocean(client_slug, final_documents)
            
            # -------------------------------------------------------------------------
            # 5. Save Metadata for UI (Indexes List)
            # -------------------------------------------------------------------------
            if do_client.settings.digitalocean_spaces_bucket:
                try:
                    # Calculate document counts
                    # Counts by content_type for website and drive
                    website_docs_list = [d for d in final_documents if d.get("document_source") == "website"]
                    drive_docs_list = [d for d in final_documents if d.get("document_source") in ["drive", "client_materials"]]
                    intake_form_docs = len([d for d in final_documents if d.get("document_source") in ["intake_form", "intake-form"]])

                    def _by_content_type(docs: List[Dict[str, Any]]) -> Dict[str, int]:
                        counts: Dict[str, int] = {}
                        for doc in docs:
                            ct = doc.get("content_type") or doc.get("metadata", {}).get("content_type") or "other"
                            counts[ct] = counts.get(ct, 0) + 1
                        return counts

                    website_docs = {
                        "total": len(website_docs_list),
                        "by_content_type": _by_content_type(website_docs_list)
                    }
                    drive_docs_count = {
                        "total": len(drive_docs_list),
                        "by_content_type": _by_content_type(drive_docs_list)
                    }

                    # Homepage doc for title + favicon
                    homepage_doc = next(
                        (
                            d
                            for d in website_docs_list
                            if (d.get("content_type") or d.get("metadata", {}).get("content_type"))
                            in ["homepage", "home", "home page"]
                        ),
                        None,
                    )
                    homepage_meta = homepage_doc.get("metadata", {}) if homepage_doc else {}
                    homepage_title = homepage_meta.get("title") or (homepage_doc or {}).get("title") or client_slug
                    homepage_favicon = homepage_meta.get("favicon") or homepage_meta.get("ogImage")

                    # Prepare metadata object
                    metadata_file = {
                        "website_url": url,
                        "drive_url": drive_folder_input or "",
                        "client_slug": client_slug,
                        "website_docs": website_docs,
                        "intake_form_docs": intake_form_docs,
                        "drive_docs": drive_docs_count,
                        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                        "metadata": {
                            "title": homepage_title,
                        },
                    }
                    if homepage_favicon:
                        metadata_file["metadata"]["favicon"] = homepage_favicon

                    # Upload to Spaces
                    do_client.upload_file_content(
                        json.dumps(metadata_file), 
                        f"{client_slug}/metadata.json", 
                        content_type="application/json"
                    )
                    log("create.do.metadata_saved", {"client": client_slug})
                except Exception as e:
                    log("create.do.metadata_error", {"error": str(e)})

        except Exception as e:
            log("create.do.error", {"error": str(e)})
            # Don't fail the request if DO fails, just log it

    return {
        "status": "success",
        "index": index_name,
        "namespace": namespace,
        "pages_processed": len(pages),
        "drive_docs_processed": len(drive_docs),
        "total_documents": len(final_documents),
        "digital_ocean": {
            "kb_uuid": do_kb_uuid,
            "source_added": do_source_added
        }
    }
