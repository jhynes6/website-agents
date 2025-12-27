"""
Test script for DigitalOcean Gradient KB retrieval endpoint.

This script allows you to test document retrieval from Knowledge Bases
without going through an agent.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from app.clients.do_kb_registry import KnowledgeBaseRegistry
from app.config import get_settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_retrieval")


def test_retrieval(kb_uuid: str, query: str, num_results: int = 5):
    """Test document retrieval from a Knowledge Base."""
    from gradient import Gradient
    
    settings = get_settings()
    
    # Check for required token
    if not settings.digitalocean_token:
        logger.error("✗ DIGITALOCEAN_TOKEN not set in environment")
        return False
    
    print(f"\n{'='*80}")
    print(f"Testing KB Retrieval")
    print(f"{'='*80}")
    print(f"KB UUID: {kb_uuid}")
    print(f"Query: {query}")
    print(f"Num Results: {num_results}")
    print(f"{'='*80}\n")
    
    try:
        # Initialize Gradient client with access token
        client = Gradient(access_token=settings.digitalocean_token)
        
        response = client.retrieve.documents(
            knowledge_base_id=kb_uuid,
            num_results=num_results,
            query=query,
        )
        
        print(f"✓ Successfully retrieved {len(response.results)} results\n")
        
        for idx, result in enumerate(response.results, 1):
            print(f"{'='*80}")
            print(f"Result {idx}")
            print(f"{'='*80}")
            
            # Handle different response formats
            if hasattr(result, 'score'):
                print(f"Score: {result.score}")
            
            if hasattr(result, 'document_id'):
                print(f"Document ID: {result.document_id}")
            
            if hasattr(result, 'metadata'):
                print(f"Metadata: {json.dumps(result.metadata, indent=2)}")
            
            if hasattr(result, 'content'):
                content = result.content
                # Truncate if very long
                if len(content) > 500:
                    print(f"Content (truncated):\n{content[:500]}...")
                else:
                    print(f"Content:\n{content}")
            elif hasattr(result, 'text'):
                text = result.text
                if len(text) > 500:
                    print(f"Text (truncated):\n{text[:500]}...")
                else:
                    print(f"Text:\n{text}")
            
            print()
        
        # Also print raw response for debugging
        print(f"\n{'='*80}")
        print("Raw Response (for debugging):")
        print(f"{'='*80}")
        print(json.dumps(response.model_dump() if hasattr(response, 'model_dump') else str(response), indent=2, default=str))
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Error retrieving documents: {e}")
        import traceback
        traceback.print_exc()
        return False


def list_available_kbs():
    """List all available Knowledge Bases from registry."""
    registry = KnowledgeBaseRegistry()
    kbs = registry._data
    
    print("\n" + "="*80)
    print("Available Knowledge Bases")
    print("="*80)
    
    for idx, (slug, rec) in enumerate(sorted(kbs.items()), 1):
        print(f"{idx:3}. {slug:40} | {rec.kb_uuid}")
    
    print("="*80 + "\n")
    
    return kbs


def interactive_mode():
    """Interactive mode to test retrieval."""
    kbs = list_available_kbs()
    
    while True:
        print("\nOptions:")
        print("  1. Test retrieval by client slug")
        print("  2. Test retrieval by KB UUID")
        print("  3. List all KBs")
        print("  q. Quit")
        
        choice = input("\nChoice: ").strip().lower()
        
        if choice == 'q':
            break
        elif choice == '3':
            list_available_kbs()
            continue
        elif choice in ['1', '2']:
            if choice == '1':
                slug = input("Client slug: ").strip()
                if slug not in kbs:
                    print(f"✗ Client '{slug}' not found in registry")
                    continue
                kb_uuid = kbs[slug].kb_uuid
            else:
                kb_uuid = input("KB UUID: ").strip()
            
            query = input("Query: ").strip()
            if not query:
                print("✗ Query cannot be empty")
                continue
            
            num_results = input("Number of results [5]: ").strip()
            num_results = int(num_results) if num_results else 5
            
            test_retrieval(kb_uuid, query, num_results)
        else:
            print("Invalid choice")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test DigitalOcean Gradient KB retrieval",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python test_kb_retrieval.py
  
  # Quick test with client slug
  python test_kb_retrieval.py --client pi-lit --query "What services do you offer?"
  
  # Test with KB UUID
  python test_kb_retrieval.py --kb-uuid 550e8400-e29b-41d4-a716-446655440000 --query "pricing"
  
  # List all available KBs
  python test_kb_retrieval.py --list
        """
    )
    
    parser.add_argument("--client", help="Client slug to test", type=str)
    parser.add_argument("--kb-uuid", help="KB UUID to test", type=str)
    parser.add_argument("--query", help="Query to test", type=str)
    parser.add_argument("--num-results", "-n", help="Number of results to retrieve (default: 5)", type=int, default=5)
    parser.add_argument("--list", help="List all available KBs and exit", action="store_true")
    
    args = parser.parse_args()
    
    # List mode
    if args.list:
        list_available_kbs()
        return
    
    # Command-line mode
    if args.client or args.kb_uuid:
        if not args.query:
            print("✗ Error: --query is required when using --client or --kb-uuid")
            parser.print_help()
            return
        
        if args.client:
            registry = KnowledgeBaseRegistry()
            rec = registry.get(args.client)
            if not rec:
                print(f"✗ Error: Client '{args.client}' not found in registry")
                print("\nRun with --list to see available clients")
                return
            kb_uuid = rec.kb_uuid
        else:
            kb_uuid = args.kb_uuid
        
        test_retrieval(kb_uuid, args.query, args.num_results)
    
    # Interactive mode (default)
    else:
        print("\n" + "="*80)
        print("DigitalOcean Gradient KB Retrieval Test Tool")
        print("="*80)
        interactive_mode()


if __name__ == "__main__":
    main()

