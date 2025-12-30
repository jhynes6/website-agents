#!/usr/bin/env python3
"""
Bulk test all inbox-manager agents with standard queries.

Usage:
    python backend/scripts/bulk_test_agents.py
    python backend/scripts/bulk_test_agents.py --limit 5
    python backend/scripts/bulk_test_agents.py --client pi-lit
    python backend/scripts/bulk_test_agents.py --agent-uuid <uuid> --agent-uuid <uuid>
    python backend/scripts/bulk_test_agents.py --agent-uuids <uuid1,uuid2,uuid3>
    python backend/scripts/bulk_test_agents.py --output results.json
"""

import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import httpx
from openai import AsyncOpenAI

from app.clients.do_agent_registry import AgentRegistry
from app.config import get_settings

# Test queries to send to each agent
TEST_QUERIES = [
    "what does your company do?",
    "tell me what you sell",
    "what do you sell and what industries have you worked with?",
    "do you have any case studies?",
]


async def load_agent_api_tokens() -> Dict[str, Any]:
    """Load agent API tokens from Spaces."""
    settings = get_settings()
    
    try:
        from app.clients.digital_ocean_client import do_client
        
        if not do_client.s3_client:
            return {"tokens": {}, "total_agents": 0}
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: do_client.s3_client.get_object(
                Bucket="mintleads-agents-store",
                Key="agent-api-tokens.json"
            )
        )
        content = response['Body'].read().decode('utf-8')
        return json.loads(content)
    except Exception as e:
        print(f"Warning: Could not load agent-api-tokens.json: {e}")
        return {"tokens": {}, "total_agents": 0}


async def test_agent_query(
    agent_name: str,
    client_slug: str,
    endpoint_url: str,
    api_key: str,
    query: str,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Send a single query to an agent and record the response.
    
    Returns:
        Dict with query, response, timing, and error info
    """
    result = {
        "query": query,
        "response": None,
        "error": None,
        "duration_ms": 0,
        "status": "pending"
    }
    
    if not endpoint_url or not api_key:
        result["error"] = "Missing endpoint_url or api_key"
        result["status"] = "error"
        return result
    
    start_time = time.time()
    
    try:
        client = AsyncOpenAI(
            base_url=f"{endpoint_url}/api/v1",
            api_key=api_key,
            timeout=timeout
        )
        
        response = await client.chat.completions.create(
            model="n/a",  # Model is defined in agent
            messages=[{"role": "user", "content": query}],
            stream=False
        )
        
        duration = (time.time() - start_time) * 1000  # Convert to ms
        result["duration_ms"] = round(duration, 2)
        result["response"] = response.choices[0].message.content
        result["status"] = "success"
        
        # Extract token usage if available
        if hasattr(response, 'usage') and response.usage:
            result["tokens"] = {
                "prompt": response.usage.prompt_tokens,
                "completion": response.usage.completion_tokens,
                "total": response.usage.total_tokens
            }
        
    except asyncio.TimeoutError:
        result["error"] = f"Timeout after {timeout}s"
        result["status"] = "timeout"
        result["duration_ms"] = timeout * 1000
    except Exception as e:
        result["error"] = str(e)
        result["status"] = "error"
        result["duration_ms"] = round((time.time() - start_time) * 1000, 2)
    
    return result


async def test_agent(
    agent_name: str,
    client_slug: str,
    endpoint_url: str,
    api_key: str,
    queries: List[str] = TEST_QUERIES,
    delay_between_queries: float = 1.0
) -> Dict[str, Any]:
    """
    Test an agent with all queries.
    
    Returns:
        Dict with agent info and all query results
    """
    print(f"\n{'='*80}")
    print(f"Testing: {agent_name} ({client_slug})")
    print(f"{'='*80}")
    
    results = {
        "agent_name": agent_name,
        "client_slug": client_slug,
        "endpoint_url": endpoint_url,
        "has_api_key": bool(api_key),
        "tested_at": datetime.now(timezone.utc).isoformat(),
        "queries": []
    }
    
    for i, query in enumerate(queries, 1):
        print(f"\n[{i}/{len(queries)}] Query: {query}")
        
        query_result = await test_agent_query(
            agent_name=agent_name,
            client_slug=client_slug,
            endpoint_url=endpoint_url,
            api_key=api_key,
            query=query
        )
        
        results["queries"].append(query_result)
        
        # Print result summary
        status_icon = {
            "success": "✓",
            "error": "✗",
            "timeout": "⏱",
            "pending": "⋯"
        }.get(query_result["status"], "?")
        
        print(f"  {status_icon} Status: {query_result['status']}")
        print(f"  ⏱  Duration: {query_result['duration_ms']:.0f}ms")
        
        if query_result["status"] == "success":
            response_preview = query_result["response"][:200] + "..." if len(query_result["response"]) > 200 else query_result["response"]
            print(f"  💬 Response: {response_preview}")
            if "tokens" in query_result:
                print(f"  🔢 Tokens: {query_result['tokens']['total']} total ({query_result['tokens']['prompt']} prompt + {query_result['tokens']['completion']} completion)")
        elif query_result["error"]:
            print(f"  ❌ Error: {query_result['error']}")
        
        # Delay between queries to avoid rate limiting
        if i < len(queries):
            await asyncio.sleep(delay_between_queries)
    
    # Calculate summary stats
    success_count = sum(1 for q in results["queries"] if q["status"] == "success")
    error_count = sum(1 for q in results["queries"] if q["status"] == "error")
    timeout_count = sum(1 for q in results["queries"] if q["status"] == "timeout")
    avg_duration = sum(q["duration_ms"] for q in results["queries"]) / len(results["queries"]) if results["queries"] else 0
    
    results["summary"] = {
        "total_queries": len(queries),
        "successful": success_count,
        "errors": error_count,
        "timeouts": timeout_count,
        "success_rate": round(success_count / len(queries) * 100, 1) if queries else 0,
        "avg_duration_ms": round(avg_duration, 2)
    }
    
    print(f"\n{'─'*80}")
    print(f"Summary: {success_count}/{len(queries)} successful ({results['summary']['success_rate']}%)")
    print(f"Average duration: {results['summary']['avg_duration_ms']:.0f}ms")
    
    return results


async def bulk_test_agents(
    client_slug: Optional[str] = None,
    agent_uuids: Optional[List[str]] = None,
    limit: Optional[int] = None,
    queries: List[str] = TEST_QUERIES,
    delay_between_agents: float = 2.0,
    delay_between_queries: float = 1.0
) -> Dict[str, Any]:
    """
    Test all inbox-manager agents (or filtered subset).
    
    Args:
        client_slug: Only test this specific client
        limit: Max number of agents to test
        queries: List of queries to test
        delay_between_agents: Seconds to wait between testing different agents
        delay_between_queries: Seconds to wait between queries to the same agent
    
    Returns:
        Dict with all test results
    """
    print("="*80)
    print("BULK AGENT TESTING")
    print("="*80)
    
    # Load agent registry
    registry = AgentRegistry()
    all_agents = registry.list_all()
    
    # Filter to inbox-manager agents (default behavior)
    inbox_agents = {
        slug: agent
        for slug, agent in all_agents.items()
        if agent.agent_name and "inbox-manager" in agent.agent_name
    }
    
    print(f"\nFound {len(inbox_agents)} inbox-manager agents")
    
    # If explicit agent UUIDs provided, select those instead (still supports inbox-manager naming)
    if agent_uuids:
        wanted = {u.strip() for u in agent_uuids if u and u.strip()}
        inbox_agents = {
            slug: agent
            for slug, agent in inbox_agents.items()
            if agent.agent_uuid and agent.agent_uuid in wanted
        }
        print(f"Filtered to {len(inbox_agents)} agents by UUIDs")
    
    # Filter by client slug if specified
    if client_slug:
        inbox_agents = {
            slug: agent for slug, agent in inbox_agents.items()
            if client_slug in slug
        }
        print(f"Filtered to {len(inbox_agents)} agents for client: {client_slug}")
    
    # Apply limit
    if limit:
        inbox_agents = dict(list(inbox_agents.items())[:limit])
        print(f"Limited to first {limit} agents")
    
    if not inbox_agents:
        print("\n❌ No agents to test!")
        return {"results": [], "summary": {}}
    
    # Load API tokens for missing keys
    tokens_data = await load_agent_api_tokens()
    
    # Test each agent
    results = []
    for i, (slug, agent) in enumerate(inbox_agents.items(), 1):
        print(f"\n[{i}/{len(inbox_agents)}] Agent: {agent.agent_name}")
        
        # Get endpoint and API key
        endpoint_url = agent.endpoint_url
        api_key = agent.api_key
        
        # Fallback to centralized tokens if missing
        if not endpoint_url or not api_key:
            agent_creds = tokens_data.get("tokens", {}).get(slug)
            if agent_creds:
                if not endpoint_url:
                    endpoint_url = agent_creds.get("endpoint")
                if not api_key:
                    api_key = agent_creds.get("api_key")
        
        if not endpoint_url:
            print(f"  ⚠️  Skipping: No endpoint URL")
            results.append({
                "agent_name": agent.agent_name,
                "client_slug": slug.split(":")[-1] if ":" in slug else slug,
                "error": "No endpoint URL available",
                "queries": []
            })
            continue
        
        if not api_key:
            print(f"  ⚠️  Skipping: No API key")
            results.append({
                "agent_name": agent.agent_name,
                "client_slug": slug.split(":")[-1] if ":" in slug else slug,
                "error": "No API key available",
                "queries": []
            })
            continue
        
        # Extract client slug from agent slug (format: inbox_manager:client-slug)
        client_slug_part = slug.split(":")[-1] if ":" in slug else slug
        
        # Test the agent
        agent_result = await test_agent(
            agent_name=agent.agent_name,
            client_slug=client_slug_part,
            endpoint_url=endpoint_url,
            api_key=api_key,
            queries=queries,
            delay_between_queries=delay_between_queries
        )
        
        results.append(agent_result)
        
        # Delay between agents
        if i < len(inbox_agents):
            await asyncio.sleep(delay_between_agents)
    
    # Calculate overall summary
    total_agents = len(results)
    agents_with_results = sum(1 for r in results if "summary" in r)
    total_queries = sum(r.get("summary", {}).get("total_queries", 0) for r in results)
    successful_queries = sum(r.get("summary", {}).get("successful", 0) for r in results)
    
    overall_summary = {
        "total_agents_tested": total_agents,
        "agents_with_results": agents_with_results,
        "total_queries_sent": total_queries,
        "successful_queries": successful_queries,
        "overall_success_rate": round(successful_queries / total_queries * 100, 1) if total_queries > 0 else 0,
        "tested_at": datetime.now(timezone.utc).isoformat()
    }
    
    return {
        "test_queries": queries,
        "results": results,
        "summary": overall_summary
    }


def save_results(results: Dict[str, Any], output_file: str):
    """Save test results to JSON file."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"Results saved to: {output_path}")
    print(f"{'='*80}")


async def main():
    parser = argparse.ArgumentParser(description="Bulk test inbox-manager agents")
    parser.add_argument("--client", type=str, help="Only test this specific client slug")
    parser.add_argument(
        "--agent-uuid",
        action="append",
        dest="agent_uuid",
        help="Agent UUID to test (repeatable). Example: --agent-uuid <uuid>",
    )
    parser.add_argument(
        "--agent-uuids",
        type=str,
        help="Comma-separated list of agent UUIDs to test. Example: --agent-uuids uuid1,uuid2,uuid3",
    )
    parser.add_argument("--limit", type=int, help="Limit number of agents to test")
    parser.add_argument("--output", type=str, default="backend/scripts/io/bulk_agent_test_results.json", help="Output file path")
    parser.add_argument("--delay-agents", type=float, default=2.0, help="Seconds to wait between agents")
    parser.add_argument("--delay-queries", type=float, default=1.0, help="Seconds to wait between queries")
    
    args = parser.parse_args()
    
    # Normalize agent UUID inputs
    agent_uuids: List[str] = []
    if args.agent_uuid:
        agent_uuids.extend(args.agent_uuid)
    if args.agent_uuids:
        agent_uuids.extend([p.strip() for p in args.agent_uuids.split(",") if p.strip()])
    
    # Run bulk test
    results = await bulk_test_agents(
        client_slug=args.client,
        agent_uuids=agent_uuids if agent_uuids else None,
        limit=args.limit,
        queries=TEST_QUERIES,
        delay_between_agents=args.delay_agents,
        delay_between_queries=args.delay_queries
    )
    
    # Save results
    save_results(results, args.output)
    
    # Print final summary
    summary = results["summary"]
    print(f"\n{'='*80}")
    print("FINAL SUMMARY")
    print(f"{'='*80}")
    print(f"Agents tested: {summary['total_agents_tested']}")
    print(f"Total queries: {summary['total_queries_sent']}")
    print(f"Successful: {summary['successful_queries']}/{summary['total_queries_sent']} ({summary['overall_success_rate']}%)")
    print(f"Results saved: {args.output}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())

