"""
Refresh agent API keys and save them to Spaces.

This script regenerates API keys for agents and stores them securely in:
- mintleads-agents-store/agent-api-tokens.json (centralized token storage)
- mintleads-agents-store/agents/{agent}.json (individual agent records)

Usage:
    python refresh_agent_tokens.py --all                    # Refresh all agents
    python refresh_agent_tokens.py --client abundantly      # Refresh one client
    python refresh_agent_tokens.py --list                   # List agents without tokens
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from app.clients.digital_ocean_client import do_client
from app.clients.do_agent_registry import AgentRegistry
from app.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("refresh_agent_tokens")


async def load_tokens_from_spaces() -> Dict[str, str]:
    """Load existing tokens from Spaces."""
    settings = get_settings()
    
    try:
        import boto3
        s3 = boto3.client(
            's3',
            region_name=settings.digitalocean_spaces_region,
            endpoint_url=f'https://{settings.digitalocean_spaces_region}.digitaloceanspaces.com',
            aws_access_key_id=settings.digitalocean_spaces_key,
            aws_secret_access_key=settings.digitalocean_spaces_secret
        )
        
        obj = s3.get_object(
            Bucket='mintleads-agents-store',
            Key='agent-api-tokens.json'
        )
        data = json.loads(obj['Body'].read().decode('utf-8'))
        
        # Handle nested structure
        tokens = data.get('tokens', data)
        logger.info(f"Loaded {len(tokens)} existing tokens from Spaces")
        return tokens
    except s3.exceptions.NoSuchKey:
        logger.info("No existing tokens file found, starting fresh")
        return {}
    except Exception as e:
        logger.warning(f"Failed to load existing tokens: {e}")
        return {}


async def save_tokens_to_spaces(tokens: Dict[str, str]) -> bool:
    """Save tokens to Spaces."""
    settings = get_settings()
    
    try:
        import boto3
        s3 = boto3.client(
            's3',
            region_name=settings.digitalocean_spaces_region,
            endpoint_url=f'https://{settings.digitalocean_spaces_region}.digitaloceanspaces.com',
            aws_access_key_id=settings.digitalocean_spaces_key,
            aws_secret_access_key=settings.digitalocean_spaces_secret
        )
        
        # Add metadata
        payload = {
            "tokens": tokens,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "total_tokens": len(tokens)
        }
        
        s3.put_object(
            Bucket='mintleads-agents-store',
            Key='agent-api-tokens.json',
            Body=json.dumps(payload, indent=2),
            ContentType='application/json'
        )
        logger.info(f"✓ Saved {len(tokens)} tokens to mintleads-agents-store/agent-api-tokens.json")
        return True
    except Exception as e:
        logger.error(f"Failed to save tokens to Spaces: {e}")
        return False


async def update_agent_file_in_spaces(agent_slug: str, api_key: str) -> bool:
    """Update individual agent file with new API key."""
    settings = get_settings()
    
    try:
        import boto3
        s3 = boto3.client(
            's3',
            region_name=settings.digitalocean_spaces_region,
            endpoint_url=f'https://{settings.digitalocean_spaces_region}.digitaloceanspaces.com',
            aws_access_key_id=settings.digitalocean_spaces_key,
            aws_secret_access_key=settings.digitalocean_spaces_secret
        )
        
        # Convert slug format (inbox_manager:abundantly -> inbox_manager_abundantly)
        file_slug = agent_slug.replace(':', '_')
        key = f'agents/{file_slug}.json'
        
        # Load existing agent file
        try:
            obj = s3.get_object(Bucket='mintleads-agents-store', Key=key)
            agent_data = json.loads(obj['Body'].read().decode('utf-8'))
        except:
            logger.warning(f"Could not load existing agent file: {key}")
            return False
        
        # Update API key and timestamp
        agent_data['api_key'] = api_key
        agent_data['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        # Save back
        s3.put_object(
            Bucket='mintleads-agents-store',
            Key=key,
            Body=json.dumps(agent_data, indent=2),
            ContentType='application/json'
        )
        return True
    except Exception as e:
        logger.error(f"Failed to update agent file {agent_slug}: {e}")
        return False


async def refresh_token_for_agent(agent_slug: str, agent_uuid: str, agent_name: str) -> Optional[str]:
    """Generate a new API key for an agent."""
    try:
        logger.info(f"Generating API key for {agent_name}...")
        api_key = await do_client.create_agent_api_key(agent_uuid)
        
        if api_key:
            logger.info(f"  ✓ Generated key: {api_key[:20]}...")
            return api_key
        else:
            logger.error(f"  ✗ Failed to generate key for {agent_name}")
            return None
    except Exception as e:
        logger.error(f"  ✗ Error generating key for {agent_name}: {e}")
        return None


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Refresh agent API keys")
    parser.add_argument("--client", help="Refresh keys for specific client (e.g., abundantly)")
    parser.add_argument("--all", help="Refresh keys for all agents", action="store_true")
    parser.add_argument("--list", help="List agents and their token status", action="store_true")
    parser.add_argument("--dry-run", help="Show what would be done without doing it", action="store_true")
    parser.add_argument("--yes", "-y", help="Auto-confirm without prompting", action="store_true")
    args = parser.parse_args()
    
    print("\n=== AGENT API KEY REFRESH ===\n")
    
    # Load registry
    registry = AgentRegistry()
    
    # Get inbox-manager agents
    inbox_agents = {
        slug: rec for slug, rec in registry._data.items() 
        if 'inbox_manager' in slug or 'inbox-manager' in slug
    }
    
    if args.list:
        print(f"Found {len(inbox_agents)} inbox-manager agents:\n")
        tokens = await load_tokens_from_spaces()
        
        for slug, rec in sorted(inbox_agents.items()):
            client_slug = slug.replace("inbox_manager:", "").replace("inbox_manager", "(default)")
            has_token = slug in tokens
            status = "✓ Has token" if has_token else "✗ No token"
            print(f"  {client_slug:<40} {status}")
        
        print(f"\nTokens stored: {len(tokens)}/{len(inbox_agents)}")
        return
    
    # Determine which agents to refresh
    agents_to_refresh = {}
    
    if args.client:
        # Find specific client
        possible_slugs = [
            f"inbox_manager:{args.client}",
            f"inbox-manager:{args.client}",
            args.client,
        ]
        
        found = False
        for slug in possible_slugs:
            if slug in inbox_agents:
                agents_to_refresh[slug] = inbox_agents[slug]
                found = True
                break
        
        if not found:
            print(f"❌ Agent not found for client: {args.client}")
            print("\nAvailable clients:")
            for slug in sorted(inbox_agents.keys())[:10]:
                client_slug = slug.replace("inbox_manager:", "")
                print(f"  - {client_slug}")
            return
    
    elif args.all:
        agents_to_refresh = inbox_agents
    
    else:
        print("❌ Please specify --client <slug>, --all, or --list")
        return
    
    print(f"Refreshing tokens for {len(agents_to_refresh)} agent(s):\n")
    for slug, rec in agents_to_refresh.items():
        client_slug = slug.replace("inbox_manager:", "").replace("inbox_manager", "(default)")
        print(f"  - {client_slug}")
    
    if args.dry_run:
        print("\n[DRY RUN] No tokens will be generated.")
        return
    
    if not args.yes:
        print(f"\n{'='*60}")
        input("Press Enter to continue or Ctrl+C to cancel...")
        print(f"{'='*60}\n")
    
    # Load existing tokens
    all_tokens = await load_tokens_from_spaces()
    
    # Refresh tokens
    success_count = 0
    fail_count = 0
    
    for idx, (slug, rec) in enumerate(agents_to_refresh.items(), 1):
        client_slug = slug.replace("inbox_manager:", "").replace("inbox_manager", "(default)")
        print(f"\n[{idx}/{len(agents_to_refresh)}] {client_slug}")
        
        # Generate new key
        api_key = await refresh_token_for_agent(slug, rec.agent_uuid, rec.agent_name or slug)
        
        if api_key:
            # Save to tokens dict
            all_tokens[slug] = api_key
            
            # Update agent file in Spaces
            await update_agent_file_in_spaces(slug, api_key)
            
            # Update local registry cache
            registry.upsert_for(
                client_slug=slug.replace("inbox_manager:", "").replace("inbox_manager", "default"),
                agent_type="inbox_manager",
                agent_uuid=rec.agent_uuid,
                endpoint_url=rec.endpoint_url,
                api_key=api_key,
            )
            
            success_count += 1
        else:
            fail_count += 1
        
        # Small delay to avoid rate limits
        if idx < len(agents_to_refresh):
            await asyncio.sleep(0.5)
    
    # Save all tokens to Spaces
    print(f"\n{'='*60}")
    print("Saving tokens to Spaces...")
    if await save_tokens_to_spaces(all_tokens):
        print("✓ All tokens saved successfully")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"=== SUMMARY ===")
    print(f"{'='*60}")
    print(f"Total processed: {len(agents_to_refresh)}")
    print(f"✓ Success: {success_count}")
    print(f"✗ Failed: {fail_count}")
    print(f"Total tokens stored: {len(all_tokens)}")
    print(f"{'='*60}\n")
    
    if success_count > 0:
        print("✓ Tokens refreshed and saved to:")
        print("  - mintleads-agents-store/agent-api-tokens.json")
        print("  - mintleads-agents-store/agents/{agent}.json")
        print("\nYou can now test agents with:")
        print("  python scripts/test_inbox_manager.py --client <slug>")


if __name__ == "__main__":
    asyncio.run(main())

