import json
import logging
from typing import Any, Dict, List, Optional
import asyncio
from fastapi import APIRouter, HTTPException

from ..clients.digital_ocean_client import do_client
from ..config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/indexes")
async def list_indexes(
    client_slug: Optional[str] = None, 
    clientSlug: Optional[str] = None,
    namespace: Optional[str] = None
) -> Dict[str, Any]:
    """
    List all indexes (DigitalOcean Knowledge Bases) or get a specific one.
    Accepts client_slug (preferred), clientSlug (JS compat), or namespace (deprecated).
    """
    settings = get_settings()
    
    # Handle aliases
    target_slug = client_slug or clientSlug or namespace

    if not settings.digitalocean_token:
        return {"indexes": []} if not target_slug else {"error": "Not configured"}

    # If target_slug is provided, fetch specific KB
    if target_slug:
        try:
            # We can't efficiently "get by tag" or metadata easily without listing or known UUID.
            # But the client_slug is the name.
            kb = await do_client.get_knowledge_base_by_name(target_slug)
            if not kb:
                raise HTTPException(status_code=404, detail="Knowledge Base not found")
            
            kb_id = kb.get("uuid")
            
            # Default metadata
            metadata = {
                "title": target_slug,
                "description": f"Knowledge Base ID: {kb_id}",
                "favicon": None,
                "indexName": target_slug
            }
            
            stats = {
                "pagesCrawled": 0,
                "createdAt": kb.get("created_at") or kb.get("updated_at")
            }
            
            # Fetch metadata.json
            if do_client.s3_client and settings.digitalocean_spaces_bucket:
                try:
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None,
                        lambda: do_client.s3_client.get_object(
                            Bucket=settings.digitalocean_spaces_bucket,
                            Key=f"{target_slug}/metadata.json"
                        )
                    )
                    content = response['Body'].read().decode('utf-8')
                    stored_meta = json.loads(content)
                    
                    if "pagesCrawled" in stored_meta:
                        stats["pagesCrawled"] = stored_meta["pagesCrawled"]
                    if "createdAt" in stored_meta:
                        stats["createdAt"] = stored_meta["createdAt"]
                    if "metadata" in stored_meta:
                        m = stored_meta["metadata"]
                        if m.get("title"): metadata["title"] = m["title"]
                        if m.get("description"): metadata["description"] = m["description"]
                        if m.get("favicon"): metadata["favicon"] = m["favicon"]
                        if m.get("ogImage"): metadata["ogImage"] = m["ogImage"]
                        if m.get("indexName"): metadata["indexName"] = m["indexName"]
                except Exception:
                    pass

            index_data = {
                "url": f"https://{target_slug}.com",
                "clientSlug": target_slug,
                "namespace": target_slug, # Keep for compat
                "pagesCrawled": stats["pagesCrawled"],
                "createdAt": stats["createdAt"],
                "metadata": metadata
            }
            
            return {"index": index_data}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to fetch KB {target_slug}: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch index")

    # List all KBs
    try:
        kbs = await do_client.list_knowledge_bases()
    except Exception as e:
        logger.error(f"Failed to list KBs: {e}")
        raise HTTPException(status_code=500, detail="Failed to list knowledge bases")

    indexes = []
    
    # Process KBs in parallel to fetch metadata
    async def process_kb(kb: Dict[str, Any]):
        slug = kb.get("name")
        kb_id = kb.get("uuid")
        
        # Default metadata
        metadata = {
            "title": slug,
            "description": f"Knowledge Base ID: {kb_id}",
            "favicon": None,
            "indexName": slug
        }
        
        stats = {
            "pagesCrawled": 0,
            "createdAt": kb.get("created_at") or kb.get("updated_at")
        }
        
        # Try to fetch metadata.json from Spaces
        if do_client.s3_client and settings.digitalocean_spaces_bucket:
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: do_client.s3_client.get_object(
                        Bucket=settings.digitalocean_spaces_bucket,
                        Key=f"{slug}/metadata.json"
                    )
                )
                content = response['Body'].read().decode('utf-8')
                stored_meta = json.loads(content)
                
                # Merge stats
                if "pagesCrawled" in stored_meta:
                    stats["pagesCrawled"] = stored_meta["pagesCrawled"]
                if "createdAt" in stored_meta:
                    stats["createdAt"] = stored_meta["createdAt"]
                    
                # Merge metadata
                if "metadata" in stored_meta:
                    m = stored_meta["metadata"]
                    if m.get("title"): metadata["title"] = m["title"]
                    if m.get("description"): metadata["description"] = m["description"]
                    if m.get("favicon"): metadata["favicon"] = m["favicon"]
                    if m.get("ogImage"): metadata["ogImage"] = m["ogImage"]

            except Exception:
                pass

        return {
            "url": f"https://{slug}.com",
            "clientSlug": slug,
            "namespace": slug, # Keep for compat
            "pagesCrawled": stats["pagesCrawled"],
            "createdAt": stats["createdAt"],
            "metadata": metadata
        }

    # Gather all KBs
    results = await asyncio.gather(*[process_kb(kb) for kb in kbs])
    
    # Filter out any None results
    indexes = [r for r in results if r]
    
    # Sort by createdAt desc
    indexes.sort(key=lambda x: x.get("createdAt") or "", reverse=True)

    return {"indexes": indexes}
