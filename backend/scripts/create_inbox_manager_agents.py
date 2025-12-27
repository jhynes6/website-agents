"""
Create inbox-manager agents for all clients in the KB registry.

This script:
1. Loads all clients from do_kb_registry.json
2. Checks which clients already have inbox-manager agents
3. Creates missing inbox-manager agents with:
   - Client's KB attached
   - Inbox manager template/instruction
   - Public endpoint
   - API key
4. Updates agent registry in Spaces
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Set

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from app.clients.digital_ocean_client import do_client
from app.clients.do_agent_registry import AgentRegistry
from app.clients.do_kb_registry import KnowledgeBaseRegistry
from app.config import get_settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("create_agents")


async def get_existing_inbox_managers() -> Set[str]:
    """Get set of client slugs that already have inbox-manager agents."""
    registry = AgentRegistry()
    existing = set()
    
    for slug, agent in registry.list_all().items():
        # Parse slug format: "inbox_manager:client-slug" or just "inbox_manager"
        if slug.startswith('inbox_manager:'):
            client_slug = slug.split(':', 1)[1]
            existing.add(client_slug)
        elif slug == 'inbox_manager':
            # Generic inbox manager, skip
            pass
    
    return existing


async def create_inbox_manager_for_client(client_slug: str, kb_uuid: str) -> bool:
    """Create an inbox-manager agent for a specific client."""
    settings = get_settings()
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Creating inbox-manager for: {client_slug}")
    logger.info(f"KB UUID: {kb_uuid}")
    
    # 1. Create agent
    agent_name = f"inbox-manager-{client_slug}"
    
    try:
        logger.info(f"  1. Creating agent: {agent_name}")
        agent = await do_client.create_agent(
            name=agent_name,
            instruction=None,  # Uses default from settings (inbox_manager template)
            knowledge_base_uuids=[kb_uuid],
            region=settings.digitalocean_genai_region,
        )
        
        if not agent:
            logger.error(f"  ✗ Failed to create agent")
            return False
        
        agent_uuid = agent.get('uuid')
        logger.info(f"  ✓ Agent created: {agent_uuid}")
        
        # 2. Wait for agent deployment to reach STATUS_RUNNING
        logger.info(f"  2. Waiting for agent deployment...")
        is_ready = await do_client.wait_for_agent_ready(agent_uuid, max_wait_seconds=120)
        
        if not is_ready:
            logger.error(f"  ✗ Agent deployment failed or timed out")
            logger.warning(f"  ⚠ Agent created but not ready. Skipping endpoint/key generation.")
            # Save agent UUID anyway for later retry
            registry = AgentRegistry()
            registry.upsert_for(
                client_slug=client_slug,
                agent_type='inbox_manager',
                agent_uuid=agent_uuid,
                agent_name=agent_name,
                region=agent.get('region'),
                model=agent.get('model', {}).get('inference_name'),
                knowledge_base_uuids=[kb_uuid],
                retrieval_method=agent.get('retrieval_method'),
            )
            return False
        
        logger.info(f"  ✓ Agent deployed (STATUS_RUNNING)")
        
        # 3. Make agent public and get endpoint URL - with retries
        logger.info(f"  3. Setting visibility to PUBLIC and getting endpoint...")
        endpoint_url = await do_client.get_agent_chat_endpoint(agent_uuid, max_retries=3)
        
        if endpoint_url:
            logger.info(f"  ✓ Endpoint: {endpoint_url[:50]}...")
        else:
            logger.warning(f"  ⚠ No endpoint URL returned after retries")
        
        # 4. Create API key - with retries
        logger.info(f"  4. Creating API key (with retries)...")
        api_key = await do_client.create_agent_api_key(agent_uuid, max_retries=3)
        
        if api_key:
            logger.info(f"  ✓ API key created: {api_key[:20]}...")
        else:
            logger.warning(f"  ⚠ Failed to create API key after retries")
        
        # 5. Update registry
        logger.info(f"  5. Updating agent registry...")
        registry = AgentRegistry()
        registry.upsert_for(
            client_slug=client_slug,
            agent_type='inbox_manager',
            agent_uuid=agent_uuid,
            agent_name=agent_name,
            endpoint_url=endpoint_url,
            api_key=api_key,
            region=agent.get('region'),
            model=agent.get('model', {}).get('inference_name'),
            knowledge_base_uuids=[kb_uuid],
            retrieval_method=agent.get('retrieval_method'),
        )
        logger.info(f"  ✓ Registry updated")
        
        logger.info(f"✓ Successfully created inbox-manager for {client_slug}")
        return True
        
    except Exception as e:
        logger.error(f"✗ Error creating agent for {client_slug}: {e}")
        return False


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Create inbox-manager agents for clients")
    parser.add_argument("--client", help="Create agent for specific client only", type=str)
    parser.add_argument("--limit", help="Limit number of agents to create", type=int)
    parser.add_argument("--dry-run", help="Show what would be created without creating", action="store_true")
    args = parser.parse_args()
    
    print("\n=== CREATING INBOX-MANAGER AGENTS ===\n")
    
    # 1. Load KB registry
    logger.info("Loading KB registry...")
    kb_registry = KnowledgeBaseRegistry()
    all_clients = list(kb_registry._data.keys())
    logger.info(f"Found {len(all_clients)} clients in KB registry")
    
    # 2. Filter by specific client if requested
    if args.client:
        if args.client in all_clients:
            all_clients = [args.client]
            logger.info(f"Filtered to specific client: {args.client}")
        else:
            logger.error(f"Client '{args.client}' not found in KB registry")
            return
    
    # 3. Get existing inbox-manager agents
    logger.info("Checking existing inbox-manager agents...")
    existing_agents = await get_existing_inbox_managers()
    logger.info(f"Found {len(existing_agents)} existing inbox-manager agents")
    
    # 4. Determine which clients need agents
    clients_needing_agents = [
        client for client in all_clients
        if client not in existing_agents
    ]
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Clients needing agents: {len(clients_needing_agents)}")
    logger.info(f"Clients with agents: {len(existing_agents)}")
    logger.info(f"{'='*60}\n")
    
    if not clients_needing_agents:
        logger.info("✓ All clients already have inbox-manager agents!")
        return
    
    # Apply limit if specified
    if args.limit:
        clients_needing_agents = clients_needing_agents[:args.limit]
        logger.info(f"Limited to first {args.limit} clients")
    
    # 5. Show plan
    print("Clients that will get inbox-manager agents:")
    for client in clients_needing_agents:
        kb_rec = kb_registry.get(client)
        print(f"  - {client} (KB: {kb_rec.kb_uuid if kb_rec else 'MISSING'})")
    
    if args.dry_run:
        print("\n[DRY RUN] No agents will be created.")
        return
    
    print(f"\n{'='*60}")
    input("Press Enter to continue or Ctrl+C to cancel...")
    print(f"{'='*60}\n")
    
    # 6. Create agents
    success_count = 0
    failure_count = 0
    
    for idx, client in enumerate(clients_needing_agents, 1):
        kb_rec = kb_registry.get(client)
        
        if not kb_rec:
            logger.error(f"[{idx}/{len(clients_needing_agents)}] Skipping {client}: No KB found")
            failure_count += 1
            continue
        
        logger.info(f"\n[{idx}/{len(clients_needing_agents)}] Processing {client}...")
        
        success = await create_inbox_manager_for_client(client, kb_rec.kb_uuid)
        
        if success:
            success_count += 1
        else:
            failure_count += 1
        
        # Small delay between creates to avoid rate limits
        if idx < len(clients_needing_agents):
            await asyncio.sleep(2)
    
    # 7. Summary
    print(f"\n{'='*60}")
    print(f"=== SUMMARY ===")
    print(f"{'='*60}")
    print(f"Total processed: {len(clients_needing_agents)}")
    print(f"✓ Successful: {success_count}")
    print(f"✗ Failed: {failure_count}")
    print(f"{'='*60}\n")
    
    if success_count > 0:
        print("Agent registry has been updated in Spaces.")
        print("\nNext steps:")
        print("1. Test an agent endpoint to verify it works")
        print("2. Check that KBs are attached and returning results")
        print("3. Update your application to use the new agents")


if __name__ == "__main__":
    asyncio.run(main())

