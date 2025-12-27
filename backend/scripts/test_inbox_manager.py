"""
Test an inbox-manager agent endpoint with a sample query.

Usage:
    python test_inbox_manager.py --client abundantly
    python test_inbox_manager.py --list
"""

import asyncio
import httpx
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from app.clients.do_agent_registry import AgentRegistry


async def test_agent(endpoint_url: str, api_key: str, query: str):
    """Send a test query to an agent endpoint using OpenAI-compatible API."""
    print(f"\n{'='*60}")
    print(f"Testing endpoint: {endpoint_url}")
    print(f"Query: {query}")
    print(f"{'='*60}\n")
    
    # Agent endpoints use OpenAI-compatible format
    # Endpoint format: https://xxx.agents.do-ai.run/api/v1/chat/completions
    chat_endpoint = f"{endpoint_url}/api/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
    }
    
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    # OpenAI-compatible payload
    payload = {
        "model": "n/a",  # Model is ignored for agent endpoints
        "messages": [
            {"role": "user", "content": query}
        ],
        "extra_body": {"include_retrieval_info": True}
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            print(f"Sending request to: {chat_endpoint}")
            response = await client.post(
                chat_endpoint,
                headers=headers,
                json=payload,
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"\n{'='*60}")
                print("AGENT RESPONSE:")
                print(f"{'='*60}")
                
                # Extract message content from OpenAI format
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0].get("message", {}).get("content", "")
                    print(content)
                else:
                    print(result)
                
                print(f"{'='*60}\n")
                
                # Show retrieval info if available
                if "retrieval" in result:
                    print("Retrieval Info:")
                    retrieval = result["retrieval"]
                    print(f"  KB Results: {retrieval.get('num_results', 'N/A')}")
                    print(f"  Method: {retrieval.get('method', 'N/A')}")
                    
                    if "results" in retrieval:
                        print(f"\n  Top Sources:")
                        for i, res in enumerate(retrieval["results"][:3], 1):
                            print(f"    {i}. {res.get('filename', 'Unknown')} (score: {res.get('score', 'N/A')})")
            else:
                print(f"\nError: {response.text}")
                
    except httpx.TimeoutException:
        print("\n❌ Request timed out (60s)")
    except Exception as e:
        print(f"\n❌ Error: {e}")


def list_agents():
    """List all available inbox-manager agents."""
    registry = AgentRegistry()
    agents = [(slug, rec) for slug, rec in registry._data.items() 
              if 'inbox-manager' in slug or 'inbox_manager' in slug]
    
    print(f"\nAvailable inbox-manager agents ({len(agents)}):\n")
    
    for slug, rec in sorted(agents):
        client_slug = slug.replace("inbox_manager:", "").replace("inbox_manager", "(default)")
        status = "✓ Ready" if rec.endpoint_url and rec.api_key else "⚠ Missing credentials"
        print(f"  {client_slug:<40} {status}")
    
    print()


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Test inbox-manager agent endpoints")
    parser.add_argument("--client", help="Client slug to test (e.g., abundantly)")
    parser.add_argument("--query", help="Query to send", 
                       default="What services does this company offer?")
    parser.add_argument("--list", help="List all available agents", action="store_true")
    args = parser.parse_args()
    
    if args.list:
        list_agents()
        return
    
    if not args.client:
        print("❌ Please specify --client or use --list to see available agents")
        list_agents()
        return
    
    # Load registry and find agent
    registry = AgentRegistry()
    
    # Try different slug formats
    possible_slugs = [
        f"inbox_manager:{args.client}",
        f"inbox-manager:{args.client}",
        args.client,
    ]
    
    agent_record = None
    agent_slug = None
    for slug in possible_slugs:
        if slug in registry._data:
            agent_record = registry._data[slug]
            agent_slug = slug
            break
    
    if not agent_record:
        print(f"❌ Agent not found for client: {args.client}")
        print("\nAvailable clients:")
        list_agents()
        return
    
    if not agent_record.endpoint_url:
        print(f"❌ No endpoint URL found for {args.client}")
        print("   The agent may not have been made public yet.")
        return
    
    # Try to get API key from registry first, then from centralized token store
    api_key = agent_record.api_key
    
    if not api_key:
        # Try loading from centralized token store
        print(f"⚠️  No API key in registry, checking centralized token store...")
        try:
            from app.config import get_settings
            import boto3
            import json
            
            settings = get_settings()
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
            tokens_data = json.loads(obj['Body'].read().decode('utf-8'))
            tokens = tokens_data.get('tokens', tokens_data)
            
            agent_creds = tokens.get(agent_slug, {})
            api_key = agent_creds.get('api_key')
            
            if api_key:
                print(f"✓ Found credentials in centralized store")
                # Also use endpoint from token store if available
                if agent_creds.get('endpoint') and not agent_record.endpoint_url:
                    agent_record.endpoint_url = agent_creds['endpoint']
        except Exception as e:
            print(f"⚠️  Could not load from token store: {e}")
    
    if not api_key:
        print(f"❌ No API key found for {args.client}")
        print("   Generate one with: python scripts/refresh_agent_tokens.py --client", args.client)
        return
    
    await test_agent(
        endpoint_url=agent_record.endpoint_url,
        api_key=api_key,
        query=args.query,
    )


if __name__ == "__main__":
    asyncio.run(main())

