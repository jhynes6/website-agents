"""
Update all existing agents with new generation parameters.

This script updates temperature, top_p, top_k, and max_tokens
for all agents to match the current config.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from app.clients.digital_ocean_client import do_client
from app.clients.agent_templates.loader import load_agent_template
from app.config import get_settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("update_agent_params")


async def update_agent_params(agent_uuid: str, agent_name: str, params: dict, preserve_kb_uuids: list) -> bool:
    """
    Update an agent's generation parameters.
    
    IMPORTANT: The PUT endpoint replaces the entire agent config,
    so we must include knowledge_base_uuids to preserve KB connections.
    """
    try:
        # Add KB UUIDs to preserve connections
        params_with_kbs = {**params, "knowledge_base_uuids": preserve_kb_uuids}
        
        async with __import__('httpx').AsyncClient() as client:
            response = await client.put(
                f"{do_client.base_url}/agents/{agent_uuid}",
                headers=do_client.headers,
                json=params_with_kbs
            )
            response.raise_for_status()
            logger.info(f"✓ Updated {agent_name} (preserved {len(preserve_kb_uuids)} KBs)")
            return True
    except Exception as e:
        logger.error(f"✗ Failed to update {agent_name}: {e}")
        return False


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Update all agents with new generation parameters")
    parser.add_argument("--dry-run", help="Show what would be updated without updating", action="store_true")
    parser.add_argument("--yes", "-y", help="Auto-confirm without prompting", action="store_true")
    args = parser.parse_args()
    
    settings = get_settings()
    
    # Load the latest inbox_manager system prompt
    new_instruction = load_agent_template("inbox_manager")
    
    # Parameters to update
    new_params = {
        "temperature": settings.digitalocean_agent_temperature,
        "top_p": settings.digitalocean_agent_top_p,
        "top_k": settings.digitalocean_agent_top_k,
        "max_tokens": settings.digitalocean_agent_max_tokens,
        "instruction": new_instruction,
    }
    
    print("\n=== UPDATING AGENT GENERATION PARAMETERS & SYSTEM PROMPT ===\n")
    print("New parameters:")
    print(f"  Temperature: {new_params['temperature']}")
    print(f"  Top-P: {new_params['top_p']}")
    print(f"  Top-K: {new_params['top_k']}")
    print(f"  Max Tokens: {new_params['max_tokens']}")
    print(f"\nNew system prompt (inbox_manager):")
    print(f"  Length: {len(new_instruction)} characters")
    print(f"  Preview: {new_instruction[:150]}...")
    print()
    
    # Fetch all agents
    logger.info("Fetching all agents...")
    agents = await do_client.list_agents()
    logger.info(f"Found {len(agents)} agents")
    
    if not agents:
        logger.info("No agents to update")
        return
    
    # Show what will be updated
    print("\nAgents to update:")
    needs_update = []
    
    for agent in agents:
        current_temp = agent.get('temperature', 1)
        current_top_p = agent.get('top_p', 0.9)
        current_top_k = agent.get('top_k')
        current_max_tokens = agent.get('max_tokens', 512)
        current_instruction = agent.get('instruction', '')
        
        needs_update_fields = []
        if current_temp != new_params['temperature']:
            needs_update_fields.append(f"temp: {current_temp}→{new_params['temperature']}")
        if current_top_p != new_params['top_p']:
            needs_update_fields.append(f"top_p: {current_top_p}→{new_params['top_p']}")
        if current_top_k != new_params['top_k']:
            needs_update_fields.append(f"top_k: {current_top_k}→{new_params['top_k']}")
        if current_max_tokens != new_params['max_tokens']:
            needs_update_fields.append(f"max_tokens: {current_max_tokens}→{new_params['max_tokens']}")
        if current_instruction.strip() != new_instruction.strip():
            needs_update_fields.append(f"instruction: {len(current_instruction)}→{len(new_instruction)} chars")
        
        if needs_update_fields:
            needs_update.append(agent)
            print(f"  - {agent['name']}")
            print(f"    Changes: {', '.join(needs_update_fields)}")
    
    if not needs_update:
        print("\n✓ All agents already have correct parameters!")
        return
    
    print(f"\nTotal agents needing update: {len(needs_update)}")
    
    if args.dry_run:
        print("\n[DRY RUN] No agents will be updated.")
        return
    
    if not args.yes:
        print(f"\n{'='*60}")
        input("Press Enter to continue or Ctrl+C to cancel...")
        print(f"{'='*60}\n")
    
    # Update agents
    success_count = 0
    failure_count = 0
    
    for idx, agent in enumerate(needs_update, 1):
        agent_uuid = agent.get('uuid')
        agent_name = agent.get('name')
        kb_uuids = agent.get('knowledge_base_uuids', [])
        
        logger.info(f"[{idx}/{len(needs_update)}] Updating {agent_name}...")
        
        success = await update_agent_params(agent_uuid, agent_name, new_params, kb_uuids)
        
        if success:
            success_count += 1
        else:
            failure_count += 1
        
        # Small delay between updates to avoid rate limits
        if idx < len(needs_update):
            await asyncio.sleep(1)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"=== SUMMARY ===")
    print(f"{'='*60}")
    print(f"Total processed: {len(needs_update)}")
    print(f"✓ Updated: {success_count}")
    print(f"✗ Failed: {failure_count}")
    print(f"{'='*60}\n")
    
    if success_count > 0:
        print("Agents updated successfully!")
        print("\nNew parameters are now active:")
        print(f"  - Temperature: {new_params['temperature']} (more deterministic)")
        print(f"  - Top-P: {new_params['top_p']} (balanced)")
        print(f"  - Top-K: {new_params['top_k']} (moderate diversity)")
        print(f"  - Max Tokens: {new_params['max_tokens']} (longer responses)")
        print(f"  - System Prompt: Updated from inbox_manager.md template")


if __name__ == "__main__":
    asyncio.run(main())

