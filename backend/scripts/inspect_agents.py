#!/usr/bin/env python3
"""
Inspect DigitalOcean agents - list all or get detailed info for specific agent.

Usage:
    # List all agents
    python backend/scripts/inspect_agents.py
    
    # Inspect specific agent by name
    python backend/scripts/inspect_agents.py --agent inbox-manager-pi-lit
    
    # List with filters
    python backend/scripts/inspect_agents.py --filter inbox-manager
    python backend/scripts/inspect_agents.py --no-kb  # Show agents with no KBs
    
    # Output formats
    python backend/scripts/inspect_agents.py --json
    python backend/scripts/inspect_agents.py --agent pi-lit --json > agent.json
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from app.clients.digital_ocean_client import do_client
from app.clients.do_kb_registry import KnowledgeBaseRegistry


def format_agent_list(agents: List[Dict[str, Any]], show_kbs: bool = True) -> str:
    """Format agents as a readable list."""
    if not agents:
        return "No agents found."
    
    lines = []
    lines.append("\n" + "="*80)
    lines.append(f"AGENTS ({len(agents)})")
    lines.append("="*80 + "\n")
    
    for agent in agents:
        name = agent.get('name', 'unknown')
        uuid = agent.get('uuid', 'N/A')
        model = agent.get('model', {}).get('inference_name', 'N/A')
        region = agent.get('region', 'N/A')
        kb_count = len(agent.get('knowledge_base_uuids', []))
        status = agent.get('deployment', {}).get('status', 'UNKNOWN')
        
        lines.append(f"📦 {name}")
        lines.append(f"   UUID: {uuid}")
        lines.append(f"   Model: {model}")
        lines.append(f"   Region: {region}")
        lines.append(f"   KBs: {kb_count}")
        lines.append(f"   Status: {status}")
        
        if show_kbs and kb_count > 0:
            kbs = agent.get('knowledge_bases', [])
            if kbs:
                for kb in kbs:
                    kb_name = kb.get('name', 'unknown')
                    kb_uuid = kb.get('uuid', 'N/A')
                    lines.append(f"      └─ {kb_name} ({kb_uuid})")
        
        lines.append("")
    
    return "\n".join(lines)


def format_agent_detail(agent: Dict[str, Any]) -> str:
    """Format detailed agent information."""
    lines = []
    lines.append("\n" + "="*80)
    lines.append(f"AGENT DETAILS: {agent.get('name', 'unknown')}")
    lines.append("="*80 + "\n")
    
    # Basic Info
    lines.append("📋 BASIC INFORMATION")
    lines.append(f"   Name: {agent.get('name', 'N/A')}")
    lines.append(f"   UUID: {agent.get('uuid', 'N/A')}")
    lines.append(f"   Created: {agent.get('created_at', 'N/A')}")
    lines.append(f"   Updated: {agent.get('updated_at', 'N/A')}")
    lines.append(f"   User ID: {agent.get('user_id', 'N/A')}")
    lines.append(f"   Project ID: {agent.get('project_id', 'N/A')}")
    lines.append("")
    
    # Model Info
    model = agent.get('model', {})
    lines.append("🤖 MODEL")
    lines.append(f"   Name: {model.get('name', 'N/A')}")
    lines.append(f"   Inference Name: {model.get('inference_name', 'N/A')}")
    lines.append(f"   UUID: {model.get('uuid', 'N/A')}")
    lines.append(f"   Provider: {model.get('provider', 'N/A')}")
    lines.append("")
    
    # Generation Parameters
    lines.append("⚙️  GENERATION PARAMETERS")
    lines.append(f"   Temperature: {agent.get('temperature', 'N/A')}")
    lines.append(f"   Top-P: {agent.get('top_p', 'N/A')}")
    lines.append(f"   Top-K: {agent.get('top_k', 'N/A')}")
    lines.append(f"   Max Tokens: {agent.get('max_tokens', 'N/A')}")
    lines.append("")
    
    # Retrieval Configuration
    lines.append("🔍 RETRIEVAL CONFIGURATION")
    lines.append(f"   K (retrieval): {agent.get('k', 'N/A')}")
    lines.append(f"   Method: {agent.get('retrieval_method', 'N/A')}")
    lines.append(f"   Citations: {agent.get('provide_citations', False)}")
    lines.append(f"   Conversation Logs: {agent.get('conversation_logs_enabled', False)}")
    lines.append("")
    
    # Deployment Info
    deployment = agent.get('deployment', {})
    lines.append("🚀 DEPLOYMENT")
    lines.append(f"   UUID: {deployment.get('uuid', 'N/A')}")
    lines.append(f"   Status: {deployment.get('status', 'N/A')}")
    lines.append(f"   Visibility: {deployment.get('visibility', 'N/A')}")
    lines.append(f"   URL: {deployment.get('url', 'N/A')}")
    lines.append(f"   Region: {agent.get('region', 'N/A')}")
    lines.append("")
    
    # Knowledge Bases
    kbs = agent.get('knowledge_bases', [])
    kb_uuids = agent.get('knowledge_base_uuids', [])
    lines.append(f"📚 KNOWLEDGE BASES ({len(kbs)})")
    if kbs:
        for kb in kbs:
            lines.append(f"   • {kb.get('name', 'unknown')}")
            lines.append(f"     UUID: {kb.get('uuid', 'N/A')}")
            lines.append(f"     Region: {kb.get('region', 'N/A')}")
            lines.append(f"     Embedding Model: {kb.get('embedding_model_uuid', 'N/A')}")
            lines.append(f"     Added to Agent: {kb.get('added_to_agent_at', 'N/A')}")
            
            # Last indexing job
            last_job = kb.get('last_indexing_job', {})
            if last_job:
                lines.append(f"     Last Index:")
                lines.append(f"       Status: {last_job.get('status', 'N/A')}")
                lines.append(f"       Phase: {last_job.get('phase', 'N/A')}")
                lines.append(f"       Finished: {last_job.get('finished_at', 'N/A')}")
            lines.append("")
    elif kb_uuids:
        lines.append(f"   ⚠️  Agent has {len(kb_uuids)} KB UUIDs but no detailed KB info")
        for kb_uuid in kb_uuids:
            lines.append(f"     • {kb_uuid}")
        lines.append("")
    else:
        lines.append("   ⚠️  No knowledge bases attached!")
        lines.append("")
    
    # Chatbot Config
    chatbot = agent.get('chatbot', {})
    if chatbot:
        lines.append("💬 CHATBOT CONFIGURATION")
        lines.append(f"   Name: {chatbot.get('name', 'N/A')}")
        lines.append(f"   Primary Color: {chatbot.get('primary_color', 'N/A')}")
        lines.append(f"   Secondary Color: {chatbot.get('secondary_color', 'N/A')}")
        lines.append(f"   Starting Message: {chatbot.get('starting_message', 'N/A')}")
        lines.append(f"   Button BG Color: {chatbot.get('button_background_color', 'N/A')}")
        lines.append("")
    
    # System Instruction
    instruction = agent.get('instruction', '')
    lines.append("📝 SYSTEM INSTRUCTION")
    lines.append(f"   Length: {len(instruction)} characters")
    if instruction:
        lines.append(f"   Preview:")
        preview_lines = instruction[:300].split('\n')
        for line in preview_lines:
            lines.append(f"      {line}")
        if len(instruction) > 300:
            lines.append(f"      ... ({len(instruction) - 300} more characters)")
    lines.append("")
    
    return "\n".join(lines)


async def list_agents(
    filter_name: Optional[str] = None,
    no_kb: bool = False,
    output_json: bool = False
) -> List[Dict[str, Any]]:
    """List all agents with optional filtering."""
    print("Fetching agents...", file=sys.stderr)
    agents = await do_client.list_agents()
    
    # Apply filters
    if filter_name:
        agents = [a for a in agents if filter_name.lower() in a.get('name', '').lower()]
    
    if no_kb:
        agents = [a for a in agents if len(a.get('knowledge_base_uuids', [])) == 0]
    
    # Sort by name
    agents.sort(key=lambda x: x.get('name', ''))
    
    if output_json:
        print(json.dumps(agents, indent=2))
    else:
        print(format_agent_list(agents))
    
    return agents


async def inspect_agent(agent_name: str, output_json: bool = False) -> Optional[Dict[str, Any]]:
    """Get detailed information about a specific agent."""
    print(f"Fetching agent: {agent_name}...", file=sys.stderr)
    agents = await do_client.list_agents()
    
    # Find agent (support partial name match)
    agent = None
    for a in agents:
        name = a.get('name', '')
        if agent_name == name or agent_name in name:
            agent = a
            break
    
    if not agent:
        print(f"\n❌ Agent not found: {agent_name}", file=sys.stderr)
        print(f"\nTry one of these:", file=sys.stderr)
        matching = [a.get('name') for a in agents if agent_name.lower() in a.get('name', '').lower()]
        for m in matching[:5]:
            print(f"  • {m}", file=sys.stderr)
        return None
    
    if output_json:
        print(json.dumps(agent, indent=2))
    else:
        print(format_agent_detail(agent))
    
    return agent


async def compare_with_registry(agent_uuid: str) -> Dict[str, Any]:
    """Compare agent data with registry data."""
    from app.clients.do_agent_registry import AgentRegistry
    
    registry = AgentRegistry()
    all_agents = registry.list_all()
    
    # Find in registry
    registry_data = None
    for slug, record in all_agents.items():
        if record.agent_uuid == agent_uuid:
            registry_data = record
            break
    
    return {
        "in_registry": registry_data is not None,
        "registry_data": registry_data.to_dict() if registry_data else None
    }


async def main():
    parser = argparse.ArgumentParser(
        description="Inspect DigitalOcean agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all agents
  python backend/scripts/inspect_agents.py
  
  # List only inbox-manager agents
  python backend/scripts/inspect_agents.py --filter inbox-manager
  
  # Show agents with no KBs
  python backend/scripts/inspect_agents.py --no-kb
  
  # Inspect specific agent
  python backend/scripts/inspect_agents.py --agent pi-lit
  python backend/scripts/inspect_agents.py --agent inbox-manager-pi-lit
  
  # JSON output
  python backend/scripts/inspect_agents.py --json
  python backend/scripts/inspect_agents.py --agent pi-lit --json
        """
    )
    
    parser.add_argument(
        "--agent", "-a",
        type=str,
        help="Inspect specific agent by name (supports partial match)"
    )
    parser.add_argument(
        "--filter", "-f",
        type=str,
        help="Filter agents by name substring"
    )
    parser.add_argument(
        "--no-kb",
        action="store_true",
        help="Show only agents with no knowledge bases"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )
    parser.add_argument(
        "--compare-registry",
        action="store_true",
        help="Compare with registry data (requires --agent)"
    )
    
    args = parser.parse_args()
    
    if args.agent:
        # Inspect specific agent
        agent = await inspect_agent(args.agent, output_json=args.json)
        
        if agent and args.compare_registry:
            comparison = await compare_with_registry(agent.get('uuid'))
            print("\n" + "="*80, file=sys.stderr)
            print("REGISTRY COMPARISON", file=sys.stderr)
            print("="*80, file=sys.stderr)
            print(f"In Registry: {comparison['in_registry']}", file=sys.stderr)
            if comparison['registry_data']:
                print(json.dumps(comparison['registry_data'], indent=2), file=sys.stderr)
    else:
        # List agents
        agents = await list_agents(
            filter_name=args.filter,
            no_kb=args.no_kb,
            output_json=args.json
        )
        
        if not args.json:
            print(f"\n{'='*80}")
            print(f"Total: {len(agents)} agents")
            print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())

