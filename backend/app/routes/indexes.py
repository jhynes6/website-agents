import json
import logging
from typing import Any, Dict, List, Optional
import asyncio
from fastapi import APIRouter, HTTPException

from ..clients.digital_ocean_client import do_client
from ..clients.do_agent_registry import AgentRegistry
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
    List all indexes (DigitalOcean Knowledge Bases) that have agents.
    Accepts client_slug (preferred), clientSlug (JS compat), or namespace (deprecated).
    """
    settings = get_settings()
    
    # Handle aliases
    target_slug = client_slug or clientSlug or namespace

    if not settings.digitalocean_token:
        return {"indexes": []} if not target_slug else {"error": "Not configured"}

    # Load agent registry to filter by clients with agents
    agent_registry = AgentRegistry()
    
    # Also load from centralized token store for complete agent info
    token_store = {}
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: agent_registry.s3_client.get_object(
                Bucket='mintleads-agents-store',
                Key='agent-api-tokens.json'
            ) if agent_registry.s3_client else None
        )
        if response:
            token_data = json.loads(response['Body'].read().decode('utf-8'))
            token_store = token_data.get('tokens', {})
    except Exception as e:
        logger.warning(f"Could not load agent tokens: {e}")
    
    # Get inbox_manager agents and merge with token store
    inbox_agents = {}
    for slug, record in agent_registry._data.items():
        if 'inbox_manager' in slug and ':' in slug:
            client_slug = slug.replace('inbox_manager:', '')
            # Merge with token store data
            token_key = slug
            if token_key in token_store:
                token_data = token_store[token_key]
                if not record.endpoint_url and token_data.get('endpoint'):
                    record.endpoint_url = token_data['endpoint']
                if not record.api_key and token_data.get('api_key'):
                    record.api_key = token_data['api_key']
            inbox_agents[client_slug] = record
    
    # If target_slug is provided, fetch specific KB
    if target_slug:
        # Check if this client has an agent
        if target_slug not in inbox_agents:
            raise HTTPException(status_code=404, detail="No agent found for this client")
        
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
            kb_stats = {
                "pages": 0,
                "chunks": 0
            }
            
            if do_client.s3_client and settings.digitalocean_spaces_bucket:
                try:
                    loop = asyncio.get_event_loop()
                    
                    # Load from _client_kb_master for comprehensive stats
                    try:
                        client_report_response = await loop.run_in_executor(
                            None,
                            lambda: do_client.s3_client.get_object(
                                Bucket=settings.digitalocean_spaces_bucket,
                                Key=f"_client_kb_master/clients/{target_slug}.json"
                            )
                        )
                        client_report = json.loads(client_report_response['Body'].read().decode('utf-8'))
                        
                        # Extract KB stats
                        kb_info = client_report.get("kb", {})
                        spaces_info = client_report.get("spaces", {})
                        
                        kb_stats["pages"] = spaces_info.get("total_files", 0)
                        # Chunks would come from KB details if available
                        
                        # Update metadata from client report
                        if client_report.get("ui", {}).get("title"):
                            metadata["title"] = client_report["ui"]["title"]
                        if client_report.get("ui", {}).get("favicon"):
                            metadata["favicon"] = client_report["ui"]["favicon"]
                            
                        # Update stats
                        if "createdAt" in client_report.get("timestamps", {}):
                            stats["createdAt"] = client_report["timestamps"]["createdAt"]
                        stats["pagesCrawled"] = spaces_info.get("total_files", 0)
                        
                    except Exception as e:
                        logger.debug(f"Could not load from _client_kb_master: {e}")
                    
                    # Fallback to old metadata.json
                    try:
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
                            kb_stats["pages"] = stored_meta["pagesCrawled"]
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
                except Exception:
                    pass

            # Add agent info
            agent_record = inbox_agents.get(target_slug)
            agent_info = None
            if agent_record:
                agent_info = {
                    "agentUuid": agent_record.agent_uuid,
                    "agentName": agent_record.agent_name,
                    "endpointUrl": agent_record.endpoint_url,
                    "hasApiKey": bool(agent_record.api_key),
                    "region": agent_record.region,
                    "model": agent_record.model,
                    "retrievalMethod": agent_record.retrieval_method
                }

            index_data = {
                "url": f"https://{target_slug}.com",
                "clientSlug": target_slug,
                "namespace": target_slug, # Keep for compat
                "pagesCrawled": stats["pagesCrawled"],
                "pages": kb_stats["pages"],
                "chunks": kb_stats["chunks"],
                "createdAt": stats["createdAt"],
                "metadata": metadata,
                "agent": agent_info
            }
            
            return {"index": index_data}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to fetch KB {target_slug}: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch index")

    # List all KBs that have agents
    try:
        kbs = await do_client.list_knowledge_bases()
    except Exception as e:
        logger.error(f"Failed to list KBs: {e}")
        raise HTTPException(status_code=500, detail="Failed to list knowledge bases")

    # Filter KBs to only those with agents
    filtered_kbs = [kb for kb in kbs if kb.get("name") in inbox_agents]
    
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
        
        kb_stats = {
            "pages": 0,
            "chunks": 0
        }
        
        # Try to fetch metadata.json from Spaces
        if do_client.s3_client and settings.digitalocean_spaces_bucket:
            try:
                loop = asyncio.get_event_loop()
                
                # Load from _client_kb_master for comprehensive stats
                try:
                    client_report_response = await loop.run_in_executor(
                        None,
                        lambda: do_client.s3_client.get_object(
                            Bucket=settings.digitalocean_spaces_bucket,
                            Key=f"_client_kb_master/clients/{slug}.json"
                        )
                    )
                    client_report = json.loads(client_report_response['Body'].read().decode('utf-8'))
                    
                    # Extract KB stats
                    kb_info = client_report.get("kb", {})
                    spaces_info = client_report.get("spaces", {})
                    
                    kb_stats["pages"] = spaces_info.get("total_files", 0)
                    stats["pagesCrawled"] = spaces_info.get("total_files", 0)
                    
                    # Update metadata from client report
                    if client_report.get("ui", {}).get("title"):
                        metadata["title"] = client_report["ui"]["title"]
                    if client_report.get("ui", {}).get("favicon"):
                        metadata["favicon"] = client_report["ui"]["favicon"]
                        
                    # Update stats
                    if "createdAt" in client_report.get("timestamps", {}):
                        stats["createdAt"] = client_report["timestamps"]["createdAt"]
                        
                except Exception:
                    pass
                
                # Fallback to old metadata.json
                try:
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
                        kb_stats["pages"] = stored_meta["pagesCrawled"]
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
            except Exception:
                pass

        # Add agent info
        agent_record = inbox_agents.get(slug)
        agent_info = None
        if agent_record:
            agent_info = {
                "agentUuid": agent_record.agent_uuid,
                "agentName": agent_record.agent_name,
                "endpointUrl": agent_record.endpoint_url,
                "hasApiKey": bool(agent_record.api_key),
                "region": agent_record.region,
                "model": agent_record.model,
                "retrievalMethod": agent_record.retrieval_method
            }

        return {
            "url": f"https://{slug}.com",
            "clientSlug": slug,
            "namespace": slug, # Keep for compat
            "pagesCrawled": stats["pagesCrawled"],
            "pages": kb_stats["pages"],
            "chunks": kb_stats["chunks"],
            "createdAt": stats["createdAt"],
            "metadata": metadata,
            "agent": agent_info
        }

    # Gather all filtered KBs
    results = await asyncio.gather(*[process_kb(kb) for kb in filtered_kbs])
    
    # Filter out any None results
    indexes = [r for r in results if r]
    
    # Sort by createdAt desc
    indexes.sort(key=lambda x: x.get("createdAt") or "", reverse=True)

    return {"indexes": indexes}
