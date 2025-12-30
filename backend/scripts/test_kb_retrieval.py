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


def test_retrieval(
    kb_uuid: str, 
    query: str, 
    num_results: int = 5,
    content_type: str = None,
    document_source: str = None,
    alpha: float = None,
    custom_filters: dict = None
):
    """Test document retrieval from a Knowledge Base with optional metadata filters."""
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
    if alpha is not None:
        print(f"Alpha (hybrid search): {alpha}")
    if content_type:
        print(f"Filter - Content Type: {content_type}")
    if document_source:
        print(f"Filter - Document Source: {document_source}")
    if custom_filters:
        print(f"Custom Filters: {json.dumps(custom_filters, indent=2)}")
    print(f"{'='*80}\n")
    
    try:
        # Initialize Gradient client with access token
        client = Gradient(access_token=settings.digitalocean_token)
        
        # Build filters dictionary
        filters = None
        if content_type or document_source or custom_filters:
            # The filters parameter expects a dict with 'must', 'must_not', 'should' arrays
            # But we need to check if the SDK serializes this correctly
            filters_list = []
            
            if content_type:
                filters_list.append({
                    "field": "content_type",
                    "operator": "eq",
                    "value": content_type
                })
            
            if document_source:
                filters_list.append({
                    "field": "document_source",
                    "operator": "eq",
                    "value": document_source
                })
            
            # Try passing filters as a list for 'must' conditions
            if filters_list:
                filters = {"must": filters_list}
            
            # Merge custom filters if provided
            if custom_filters:
                if not filters:
                    filters = {}
                for key, filter_list in custom_filters.items():
                    if key in ["must", "must_not", "should"]:
                        if key not in filters:
                            filters[key] = []
                        filters[key].extend(filter_list)
        
        # Build request parameters
        params = {
            "knowledge_base_id": kb_uuid,
            "num_results": num_results,
            "query": query,
        }
        
        if filters:
            params["filters"] = filters
        
        if alpha is not None:
            params["alpha"] = alpha
        
        print(f"📤 Request parameters:")
        print(json.dumps(params, indent=2))
        print()
        
        response = client.retrieve.documents(**params)
        
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
        print("  3. Test with metadata filters")
        print("  4. List all KBs")
        print("  q. Quit")
        
        choice = input("\nChoice: ").strip().lower()
        
        if choice == 'q':
            break
        elif choice == '4':
            list_available_kbs()
            continue
        elif choice in ['1', '2', '3']:
            if choice == '1':
                slug = input("Client slug: ").strip()
                if slug not in kbs:
                    print(f"✗ Client '{slug}' not found in registry")
                    continue
                kb_uuid = kbs[slug].kb_uuid
            elif choice == '2':
                kb_uuid = input("KB UUID: ").strip()
            else:  # choice == '3'
                slug = input("Client slug (for KB lookup): ").strip()
                if slug not in kbs:
                    print(f"✗ Client '{slug}' not found in registry")
                    continue
                kb_uuid = kbs[slug].kb_uuid
            
            query = input("Query: ").strip()
            if not query:
                print("✗ Query cannot be empty")
                continue
            
            num_results = input("Number of results [5]: ").strip()
            num_results = int(num_results) if num_results else 5
            
            # Metadata filters (only for choice 3)
            content_type = None
            document_source = None
            alpha = None
            
            if choice == '3':
                print("\nMetadata Filters (press Enter to skip):")
                print("Common content_types: case_studies, services_products, about, blogs_resources, pricing, homepage")
                content_type = input("  content_type: ").strip() or None
                
                print("Common document_sources: website, intake_form, google_drive")
                document_source = input("  document_source: ").strip() or None
                
                alpha_input = input("  alpha (0=keyword, 1=vector, 0.5=hybrid) [1]: ").strip()
                if alpha_input:
                    alpha = float(alpha_input)
            
            test_retrieval(
                kb_uuid, 
                query, 
                num_results,
                content_type=content_type,
                document_source=document_source,
                alpha=alpha
            )
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
  
  # Filter by content_type (case studies only)
  python test_kb_retrieval.py --client x-agency --query "success stories" --content-type case_studies
  
  # Filter by document_source (website only)
  python test_kb_retrieval.py --client x-agency --query "services" --document-source website
  
  # Hybrid search (50% keyword + 50% vector)
  python test_kb_retrieval.py --client x-agency --query "pricing" --alpha 0.5
  
  # Pure keyword search (BM25)
  python test_kb_retrieval.py --client x-agency --query "pricing" --alpha 0
  
  # Custom filters (must be valid JSON)
  python test_kb_retrieval.py --client x-agency --query "pricing" --filters '{"should": [{"field": "content_type", "operator": "in", "value": ["pricing", "services_products"]}]}'
  
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
    
    # Metadata filtering options
    parser.add_argument("--content-type", help="Filter by content_type metadata (e.g., case_studies, services_products)", type=str)
    parser.add_argument("--document-source", help="Filter by document_source metadata (e.g., website, intake_form)", type=str)
    parser.add_argument("--alpha", help="Hybrid search weight: 0=keyword (BM25), 1=vector (default), 0.5=hybrid", type=float)
    parser.add_argument("--filters", help="Custom filters as JSON", type=str)
    
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
        
        # Parse custom filters if provided
        custom_filters = None
        if args.filters:
            try:
                custom_filters = json.loads(args.filters)
            except json.JSONDecodeError as e:
                print(f"✗ Error: Invalid JSON for --filters: {e}")
                return
        
        test_retrieval(
            kb_uuid, 
            args.query, 
            args.num_results,
            content_type=args.content_type,
            document_source=args.document_source,
            alpha=args.alpha,
            custom_filters=custom_filters
        )
    
    # Interactive mode (default)
    else:
        print("\n" + "="*80)
        print("DigitalOcean Gradient KB Retrieval Test Tool")
        print("="*80)
        interactive_mode()


if __name__ == "__main__":
    main()

