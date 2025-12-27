"""
Fix missing endpoints in agent-api-tokens.json.

This script:
1. Reads agent-api-tokens.json
2. For agents without endpoints, queries DO API
3. Makes them public if needed
4. Updates both agent-api-tokens.json and individual agent files
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from app.clients.digital_ocean_client import do_client
from app.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("fix_missing_endpoints")


async def load_tokens_from_spaces():
    """Load token file from Spaces."""
    settings = get_settings()
    import boto3
    
    s3 = boto3.client(
        's3',
        region_name=settings.digitalocean_spaces_region,
        endpoint_url=f'https://{settings.digitalocean_spaces_region}.digitaloceanspaces.com',
        aws_access_key_id=settings.digitalocean_spaces_key,
        aws_secret_access_key=settings.digitalocean_spaces_secret
    )
    
    obj = s3.get_object(Bucket='mintleads-agents-store', Key='agent-api-tokens.json')
    return json.loads(obj['Body'].read().decode('utf-8'))


async def save_tokens_to_spaces(data):
    """Save updated token file to Spaces."""
    settings = get_settings()
    import boto3
    
    s3 = boto3.client(
        's3',
        region_name=settings.digitalocean_spaces_region,
        endpoint_url=f'https://{settings.digitalocean_spaces_region}.digitaloceanspaces.com',
        aws_access_key_id=settings.digitalocean_spaces_key,
        aws_secret_access_key=settings.digitalocean_spaces_secret
    )
    
    s3.put_object(
        Bucket='mintleads-agents-store',
        Key='agent-api-tokens.json',
        Body=json.dumps(data, indent=2),
        ContentType='application/json'
    )


async def update_agent_file(slug, endpoint):
    """Update individual agent file with endpoint."""
    settings = get_settings()
    import boto3
    
    s3 = boto3.client(
        's3',
        region_name=settings.digitalocean_spaces_region,
        endpoint_url=f'https://{settings.digitalocean_spaces_region}.digitaloceanspaces.com',
        aws_access_key_id=settings.digitalocean_spaces_key,
        aws_secret_access_key=settings.digitalocean_spaces_secret
    )
    
    file_slug = slug.replace(':', '_')
    key = f'agents/{file_slug}.json'
    
    try:
        obj = s3.get_object(Bucket='mintleads-agents-store', Key=key)
        agent_data = json.loads(obj['Body'].read().decode('utf-8'))
        agent_data['endpoint_url'] = endpoint
        agent_data['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        s3.put_object(
            Bucket='mintleads-agents-store',
            Key=key,
            Body=json.dumps(agent_data, indent=2),
            ContentType='application/json'
        )
        return True
    except Exception as e:
        logger.warning(f"Could not update agent file {key}: {e}")
        return False


async def main():
    print("\n=== FIXING MISSING ENDPOINTS ===\n")
    
    # Load tokens file
    logger.info("Loading agent-api-tokens.json...")
    tokens_data = await load_tokens_from_spaces()
    tokens = tokens_data.get('tokens', {})
    
    # Find agents without endpoints
    missing_endpoints = {
        slug: creds for slug, creds in tokens.items()
        if not creds.get('endpoint')
    }
    
    print(f"Found {len(missing_endpoints)} agents without endpoints\n")
    
    if not missing_endpoints:
        print("✓ All agents have endpoints!")
        return
    
    # Get all agents from DO API
    logger.info("Fetching agents from DO API...")
    all_agents = await do_client.list_agents()
    agents_by_uuid = {a['uuid']: a for a in all_agents}
    
    # Fix each agent
    fixed_count = 0
    failed_count = 0
    
    for slug, creds in missing_endpoints.items():
        agent_uuid = creds.get('agent_uuid')
        client_name = slug.replace('inbox_manager:', '')
        
        print(f"\n[{fixed_count + failed_count + 1}/{len(missing_endpoints)}] {client_name}")
        
        if not agent_uuid:
            logger.error(f"  ✗ No agent UUID in tokens file")
            failed_count += 1
            continue
        
        agent = agents_by_uuid.get(agent_uuid)
        if not agent:
            logger.error(f"  ✗ Agent not found in DO API")
            failed_count += 1
            continue
        
        deployment = agent.get('deployment', {})
        status = deployment.get('status')
        url = deployment.get('url')
        visibility = deployment.get('visibility')
        
        print(f"  Status: {status}")
        print(f"  Visibility: {visibility}")
        print(f"  URL: {url}")
        
        if status != 'STATUS_RUNNING':
            logger.warning(f"  ⚠ Agent not running, skipping")
            failed_count += 1
            continue
        
        if not url:
            logger.error(f"  ✗ No URL in deployment")
            failed_count += 1
            continue
        
        # Make public if needed
        if visibility != 'VISIBILITY_PUBLIC':
            logger.info(f"  Making agent public...")
            public_url = await do_client.get_agent_chat_endpoint(agent_uuid)
            if public_url:
                url = public_url
                logger.info(f"  ✓ Made public: {url}")
            else:
                logger.warning(f"  ⚠ Could not make public, using playground URL")
        
        # Update tokens
        tokens[slug]['endpoint'] = url
        tokens[slug]['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        # Update individual agent file
        await update_agent_file(slug, url)
        
        print(f"  ✓ Endpoint updated: {url[:50]}...")
        fixed_count += 1
    
    # Save updated tokens file
    logger.info("\nSaving updated agent-api-tokens.json...")
    tokens_data['tokens'] = tokens
    tokens_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    await save_tokens_to_spaces(tokens_data)
    
    print(f"\n{'='*60}")
    print("=== SUMMARY ===")
    print(f"{'='*60}")
    print(f"✓ Fixed: {fixed_count}")
    print(f"✗ Failed: {failed_count}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())

