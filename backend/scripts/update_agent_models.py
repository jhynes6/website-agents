"""
Update all existing agents to use a new model UUID.

This script:
1. Fetches all agents from DigitalOcean API
2. Updates each agent's model_uuid
3. Syncs the registry to Spaces
"""

import asyncio
import logging
import sys
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
logger = logging.getLogger("update_agent_models")


async def update_agent_model(agent_uuid: str, agent_name: str, new_model_uuid: str) -> bool:
    """Update an agent's model UUID."""
    try:
        async with __import__('httpx').AsyncClient() as client:
            response = await client.put(
                f"{do_client.base_url}/agents/{agent_uuid}",
                headers=do_client.headers,
                json={"model_uuid": new_model_uuid}
            )
            response.raise_for_status()
            logger.info(f"✓ Updated {agent_name}")
            return True
    except Exception as e:
        logger.error(f"✗ Failed to update {agent_name}: {e}")
        return False


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Update all agents to a new model")
    parser.add_argument("--model-uuid", help="New model UUID (defaults to config)", type=str)
    parser.add_argument("--dry-run", help="Show what would be updated without updating", action="store_true")
    parser.add_argument("--yes", "-y", help="Auto-confirm without prompting", action="store_true")
    args = parser.parse_args()
    
    settings = get_settings()
    
    # Use provided model UUID or default from config
    new_model_uuid = args.model_uuid or settings.digitalocean_agent_model_uuid
    
    print("\n=== UPDATING AGENT MODELS ===\n")
    print(f"New Model UUID: {new_model_uuid}")
    
    # Fetch all agents
    logger.info("Fetching all agents...")
    agents = await do_client.list_agents()
    logger.info(f"Found {len(agents)} agents")
    
    if not agents:
        logger.info("No agents to update")
        return
    
    # Show what will be updated
    print("\nAgents to update:")
    for agent in agents:
        current_model = agent.get('model', {})
        current_model_uuid = current_model.get('uuid', 'unknown')
        current_model_name = current_model.get('inference_name', 'unknown')
        
        needs_update = current_model_uuid != new_model_uuid
        status = "NEEDS UPDATE" if needs_update else "ALREADY UP TO DATE"
        
        print(f"  - {agent['name']}")
        print(f"    Current: {current_model_name} ({current_model_uuid})")
        print(f"    Status: {status}")
    
    if args.dry_run:
        print("\n[DRY RUN] No agents will be updated.")
        return
    
    if not args.yes:
        print(f"\n{'='*60}")
        input("Press Enter to continue or Ctrl+C to cancel...")
        print(f"{'='*60}\n")
    
    # Update agents
    success_count = 0
    skipped_count = 0
    failure_count = 0
    
    for idx, agent in enumerate(agents, 1):
        agent_uuid = agent.get('uuid')
        agent_name = agent.get('name')
        current_model_uuid = agent.get('model', {}).get('uuid')
        
        # Skip if already using the new model
        if current_model_uuid == new_model_uuid:
            logger.info(f"[{idx}/{len(agents)}] Skipping {agent_name} (already using new model)")
            skipped_count += 1
            continue
        
        logger.info(f"[{idx}/{len(agents)}] Updating {agent_name}...")
        
        success = await update_agent_model(agent_uuid, agent_name, new_model_uuid)
        
        if success:
            success_count += 1
        else:
            failure_count += 1
        
        # Small delay between updates to avoid rate limits
        if idx < len(agents):
            await asyncio.sleep(1)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"=== SUMMARY ===")
    print(f"{'='*60}")
    print(f"Total agents: {len(agents)}")
    print(f"✓ Updated: {success_count}")
    print(f"⊘ Skipped (already up to date): {skipped_count}")
    print(f"✗ Failed: {failure_count}")
    print(f"{'='*60}\n")
    
    if success_count > 0:
        print("Syncing agent registry to Spaces...")
        # Run the sync script
        import subprocess
        sync_result = subprocess.run(
            [sys.executable, str(backend_dir / "scripts" / "sync_agents_to_spaces.py")],
            cwd=backend_dir
        )
        if sync_result.returncode == 0:
            print("✓ Agent registry synced successfully")
        else:
            print("⚠ Failed to sync agent registry")


if __name__ == "__main__":
    asyncio.run(main())

