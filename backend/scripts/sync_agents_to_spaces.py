"""
Sync agents from DigitalOcean API to the mintleads-agents-store Space.

This script:
1. Fetches all agents from DO API
2. Creates a registry entry for each agent
3. Uploads to mintleads-agents-store Space
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from app.clients.digital_ocean_client import do_client
from app.config import get_settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("sync_agents")


async def sync_agents_to_spaces():
    """Sync all agents from DO API to Spaces."""
    settings = get_settings()
    
    # 1. Fetch all agents from DO
    logger.info("Fetching agents from DigitalOcean API...")
    agents = await do_client.list_agents()
    logger.info(f"Found {len(agents)} agents")
    
    # 2. Build registry structure
    registry = {}
    
    for agent in agents:
        agent_uuid = agent.get('uuid')
        agent_name = agent.get('name')
        
        # Parse slug from name
        # Patterns:
        #   "inbox-manager-pi-lit" -> "inbox_manager:pi-lit"
        #   "inbox-manager" -> "inbox_manager"
        #   "copywriting" -> "copywriting"
        
        if '-' in agent_name:
            parts = agent_name.split('-', 2)  # Split on first 2 hyphens max
            if len(parts) >= 3:
                # e.g., "inbox-manager-pi-lit" -> template="inbox-manager", client="pi-lit"
                template = '-'.join(parts[:2])  # "inbox-manager"
                client = parts[2]  # "pi-lit"
                slug = f"{template.replace('-', '_')}:{client}"  # "inbox_manager:pi-lit"
            else:
                # e.g., "inbox-manager" or "copywriting" -> no client suffix
                slug = agent_name.replace('-', '_')
        else:
            slug = agent_name
        
        # Get endpoint URL (if public)
        endpoint_url = None
        try:
            endpoint_url = await do_client.get_agent_chat_endpoint(agent_uuid)
        except Exception as e:
            logger.warning(f"Failed to get endpoint for {agent_name}: {e}")
        
        # Get API key (fetch from existing registry if exists, otherwise None)
        api_key = None
        # We'll need to create new API keys or fetch from local registry during migration
        
        registry[slug] = {
            "agent_uuid": agent_uuid,
            "agent_name": agent_name,
            "slug": slug,
            "endpoint_url": endpoint_url,
            "api_key": api_key,  # Will need to be populated separately
            "region": agent.get('region'),
            "model": agent.get('model', {}).get('inference_name'),
            "knowledge_base_uuids": agent.get('knowledge_base_uuids', []),
            "retrieval_method": agent.get('retrieval_method'),
            "created_at": agent.get('created_at'),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "raw": agent  # Store full agent object for reference
        }
    
    # 3. Upload to Spaces
    logger.info(f"Uploading registry to mintleads-agents-store...")
    
    registry_content = json.dumps(registry, indent=2)
    bucket = 'mintleads-agents-store'
    
    try:
        do_client.s3_client.put_object(
            Bucket=bucket,
            Key='agent_registry.json',
            Body=registry_content.encode('utf-8'),
            ContentType='application/json'
        )
        logger.info(f"✓ Successfully uploaded agent_registry.json")
    except Exception as e:
        logger.error(f"✗ Failed to upload: {e}")
        return False
    
    # 4. Create individual agent files
    logger.info("Creating individual agent files...")
    
    for slug, agent_data in registry.items():
        # Sanitize slug for filename
        safe_slug = slug.replace(':', '_').replace('/', '_')
        key = f"agents/{safe_slug}.json"
        
        try:
            do_client.s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=json.dumps(agent_data, indent=2).encode('utf-8'),
                ContentType='application/json'
            )
            logger.info(f"  ✓ {key}")
        except Exception as e:
            logger.error(f"  ✗ {key}: {e}")
    
    logger.info(f"\n✓ Sync complete! {len(registry)} agents synced to Spaces")
    
    return True


async def migrate_api_keys_from_local():
    """Migrate API keys from local registry to Spaces registry."""
    settings = get_settings()
    
    # Read local registry
    local_registry_path = Path(__file__).parent.parent / 'app' / 'clients' / 'do_agent_registry.json'
    
    if not local_registry_path.exists():
        logger.warning("No local registry found to migrate API keys from")
        return
    
    try:
        with open(local_registry_path) as f:
            content = f.read().strip()
            if not content:
                logger.info("Local registry is empty, skipping API key migration")
                return
            local_registry = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("Local registry is invalid JSON, skipping API key migration")
        return
    
    logger.info(f"Found {len(local_registry)} agents in local registry")
    
    # Fetch current Spaces registry
    try:
        response = do_client.s3_client.get_object(
            Bucket='mintleads-agents-store',
            Key='agent_registry.json'
        )
        spaces_registry = json.loads(response['Body'].read().decode('utf-8'))
    except Exception as e:
        logger.error(f"Failed to fetch Spaces registry: {e}")
        return
    
    # Merge API keys and endpoints
    updated = 0
    for slug, local_data in local_registry.items():
        if slug in spaces_registry:
            # Update API key and endpoint if available
            if local_data.get('api_key'):
                spaces_registry[slug]['api_key'] = local_data['api_key']
                updated += 1
            if local_data.get('endpoint_url'):
                spaces_registry[slug]['endpoint_url'] = local_data['endpoint_url']
    
    if updated > 0:
        logger.info(f"Migrated API keys for {updated} agents")
        
        # Upload updated registry
        try:
            do_client.s3_client.put_object(
                Bucket='mintleads-agents-store',
                Key='agent_registry.json',
                Body=json.dumps(spaces_registry, indent=2).encode('utf-8'),
                ContentType='application/json'
            )
            logger.info("✓ Updated Spaces registry with API keys")
        except Exception as e:
            logger.error(f"✗ Failed to update: {e}")


async def main():
    print("\n=== SYNCING AGENTS TO SPACES ===\n")
    
    # Sync agents
    success = await sync_agents_to_spaces()
    
    if success:
        print("\n=== MIGRATING API KEYS FROM LOCAL REGISTRY ===\n")
        await migrate_api_keys_from_local()
    
    print("\n=== DONE ===")


if __name__ == "__main__":
    asyncio.run(main())

