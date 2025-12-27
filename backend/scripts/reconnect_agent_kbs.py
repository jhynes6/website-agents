#!/usr/bin/env python3
"""
Reconnect all inbox-manager agents to their respective knowledge bases.

This script:
1. Lists all inbox-manager agents
2. For each agent, finds the matching KB by client slug
3. Attaches the KB to the agent using the POST endpoint

Usage:
    python backend/scripts/reconnect_agent_kbs.py
    python backend/scripts/reconnect_agent_kbs.py --limit 5
    python backend/scripts/reconnect_agent_kbs.py --client pi-lit
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from app.clients.digital_ocean_client import do_client
from app.clients.do_kb_registry import KnowledgeBaseRegistry

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("reconnect_agent_kbs")


async def attach_kb_to_agent(agent_uuid: str, agent_name: str, kb_uuid: str, kb_name: str) -> bool:
    """Attach a KB to an agent using the POST endpoint."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{do_client.base_url}/agents/{agent_uuid}/knowledge_bases",
                headers=do_client.headers,
                json={"knowledge_base_uuids": [kb_uuid]},
                timeout=30
            )
            response.raise_for_status()
            logger.info(f"  ✓ Attached KB '{kb_name}' to '{agent_name}'")
            return True
    except Exception as e:
        logger.error(f"  ✗ Failed to attach KB to '{agent_name}': {e}")
        return False


async def main():
    parser = argparse.ArgumentParser(description="Reconnect all agents to their KBs")
    parser.add_argument("--client", type=str, help="Only process this specific client slug")
    parser.add_argument("--limit", type=int, help="Limit number of agents to process")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without doing it")
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("RECONNECTING AGENTS TO KNOWLEDGE BASES")
    print("="*80 + "\n")
    
    # Load KB registry
    kb_registry = KnowledgeBaseRegistry()
    all_kbs = kb_registry.all()
    logger.info(f"Loaded {len(all_kbs)} knowledge bases from registry")
    
    # Get all agents
    logger.info("Fetching all agents...")
    agents = await do_client.list_agents()
    inbox_agents = [a for a in agents if 'inbox-manager' in a.get('name', '')]
    logger.info(f"Found {len(inbox_agents)} inbox-manager agents")
    
    # Filter agents with no KBs
    agents_needing_kb = []
    for agent in inbox_agents:
        kb_count = len(agent.get('knowledge_base_uuids', []))
        if kb_count == 0:
            agents_needing_kb.append(agent)
    
    logger.info(f"Found {len(agents_needing_kb)} agents with NO knowledge bases attached")
    
    if not agents_needing_kb:
        print("\n✓ All agents already have knowledge bases attached!")
        return
    
    # Filter by client if specified
    if args.client:
        agents_needing_kb = [a for a in agents_needing_kb if args.client in a.get('name', '')]
        logger.info(f"Filtered to {len(agents_needing_kb)} agents for client: {args.client}")
    
    # Apply limit
    if args.limit:
        agents_needing_kb = agents_needing_kb[:args.limit]
        logger.info(f"Limited to first {args.limit} agents")
    
    if not agents_needing_kb:
        print("\n⚠ No agents to process after filtering")
        return
    
    # Process each agent
    print(f"\n{'-'*80}")
    print(f"Agents to process: {len(agents_needing_kb)}")
    print(f"{'-'*80}\n")
    
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    for idx, agent in enumerate(agents_needing_kb, 1):
        agent_uuid = agent.get('uuid')
        agent_name = agent.get('name')
        
        # Extract client slug from agent name (e.g., "inbox-manager-pi-lit" -> "pi-lit")
        client_slug = agent_name.replace('inbox-manager-', '')
        
        logger.info(f"[{idx}/{len(agents_needing_kb)}] Processing: {agent_name}")
        
        # Find matching KB
        kb_record = kb_registry.get(client_slug)
        
        if not kb_record:
            logger.warning(f"  ⚠ No KB found for client: {client_slug}")
            skip_count += 1
            continue
        
        kb_uuid = kb_record.kb_uuid
        logger.info(f"  Found KB: {client_slug} ({kb_uuid})")
        
        if args.dry_run:
            logger.info(f"  [DRY RUN] Would attach KB to agent")
            success_count += 1
        else:
            success = await attach_kb_to_agent(agent_uuid, agent_name, kb_uuid, client_slug)
            if success:
                success_count += 1
                # Small delay to avoid rate limiting
                await asyncio.sleep(1)
            else:
                fail_count += 1
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Total processed: {len(agents_needing_kb)}")
    print(f"✓ Success: {success_count}")
    print(f"✗ Failed: {fail_count}")
    print(f"⚠ Skipped (no KB): {skip_count}")
    print(f"{'='*80}\n")
    
    if args.dry_run:
        print("[DRY RUN] No changes were made. Run without --dry-run to apply changes.")
    elif success_count > 0:
        print("✓ Agents are reconnected and redeploying!")
        print("  Wait ~30-60 seconds for redeployment to complete.")


if __name__ == "__main__":
    asyncio.run(main())

