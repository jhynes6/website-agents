"""
Test script demonstrating client-side YAML filtering for KB retrieval.

This shows how to filter KB results by content_type, document_source, or custom criteria
by parsing YAML frontmatter from the parent_chunk_text field.
"""

import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from gradient import Gradient
from app.config import get_settings
from app.clients.do_kb_registry import KnowledgeBaseRegistry
from app.utils.kb_filters import (
    retrieve_with_yaml_filter,
    filter_chunks_by_yaml,
    get_available_content_types,
    get_available_document_sources,
    parse_yaml_frontmatter
)


def demo_basic_filtering():
    """Demo: Basic filtering by content_type"""
    print("\n" + "="*80)
    print("DEMO 1: Basic Filtering by content_type")
    print("="*80 + "\n")
    
    settings = get_settings()
    client = Gradient(access_token=settings.digitalocean_token)
    registry = KnowledgeBaseRegistry()
    
    kb = registry.get('wendt-partners')
    
    # Retrieve and filter in one call
    print("Query: 'company services'")
    print("Filter: content_type='homepage'")
    print()
    
    results = retrieve_with_yaml_filter(
        client,
        kb.kb_uuid,
        query='company services',
        num_results=20,  # Retrieve 20 to filter from
        content_type='homepage',
        max_filtered_results=3  # Return top 3
    )
    
    print(f"✅ Found {len(results)} results matching content_type='homepage'")
    print()
    
    for i, chunk in enumerate(results, 1):
        print(f"Result {i}:")
        print(f"  File: {chunk.metadata.get('item_name')}")
        print(f"  YAML Metadata: {chunk.yaml_metadata}")
        print(f"  Text preview: {chunk.text_content[:150]}...")
        print()


def demo_two_step_filtering():
    """Demo: Two-step filtering (retrieve, then filter)"""
    print("\n" + "="*80)
    print("DEMO 2: Two-Step Filtering")
    print("="*80 + "\n")
    
    settings = get_settings()
    client = Gradient(access_token=settings.digitalocean_token)
    registry = KnowledgeBaseRegistry()
    
    kb = registry.get('wendt-partners')
    
    print("Step 1: Retrieve from KB")
    response = client.retrieve.documents(
        knowledge_base_id=kb.kb_uuid,
        num_results=30,
        query='company case studies success'
    )
    print(f"  Retrieved {len(response.results)} chunks")
    print()
    
    print("Step 2: Analyze available content types")
    content_types = get_available_content_types(response.results)
    print(f"  Content types found: {content_types}")
    print()
    
    print("Step 3: Filter for case_studies only")
    filtered = filter_chunks_by_yaml(
        response.results,
        content_type='case_studies'
    )
    print(f"  ✅ Filtered to {len(filtered)} case study chunks")
    print()
    
    if filtered:
        print("Sample result:")
        chunk = filtered[0]
        print(f"  File: {chunk.metadata.get('item_name')}")
        print(f"  Content Type: {chunk.yaml_metadata.get('content_type')}")
        print(f"  URL: {chunk.yaml_metadata.get('url')}")
        print()


def demo_custom_filter():
    """Demo: Custom filter function"""
    print("\n" + "="*80)
    print("DEMO 3: Custom Filter (Multiple Content Types)")
    print("="*80 + "\n")
    
    settings = get_settings()
    client = Gradient(access_token=settings.digitalocean_token)
    registry = KnowledgeBaseRegistry()
    
    kb = registry.get('wendt-partners')
    
    # Custom filter: case_studies OR testimonials OR services_products
    def high_value_content(yaml_meta):
        content_type = yaml_meta.get('content_type', '')
        return content_type in ['case_studies', 'testimonials', 'services_products']
    
    print("Query: 'customer success'")
    print("Custom Filter: content_type in ['case_studies', 'testimonials', 'services_products']")
    print()
    
    results = retrieve_with_yaml_filter(
        client,
        kb.kb_uuid,
        query='customer success',
        num_results=30,
        custom_filter=high_value_content,
        max_filtered_results=5
    )
    
    print(f"✅ Found {len(results)} high-value content chunks")
    print()
    
    for i, chunk in enumerate(results, 1):
        print(f"  {i}. {chunk.yaml_metadata.get('content_type')} - {chunk.metadata.get('item_name')}")


def demo_combined_filters():
    """Demo: Combine content_type and document_source filters"""
    print("\n" + "="*80)
    print("DEMO 4: Combined Filters (content_type + document_source)")
    print("="*80 + "\n")
    
    settings = get_settings()
    client = Gradient(access_token=settings.digitalocean_token)
    registry = KnowledgeBaseRegistry()
    
    kb = registry.get('x-agency')  # Using x-agency which has more data
    
    print("Query: 'services'")
    print("Filters: content_type='case_studies' AND document_source='website'")
    print()
    
    results = retrieve_with_yaml_filter(
        client,
        kb.kb_uuid,
        query='services',
        num_results=50,
        content_type='case_studies',
        document_source='website',
        max_filtered_results=5
    )
    
    print(f"✅ Found {len(results)} website case studies")
    print()
    
    for i, chunk in enumerate(results, 1):
        print(f"Result {i}:")
        print(f"  File: {chunk.metadata.get('item_name')}")
        print(f"  Type: {chunk.yaml_metadata.get('content_type')}")
        print(f"  Source: {chunk.yaml_metadata.get('document_source')}")
        print()


def demo_analysis():
    """Demo: Analyze content distribution"""
    print("\n" + "="*80)
    print("DEMO 5: Content Analysis")
    print("="*80 + "\n")
    
    settings = get_settings()
    client = Gradient(access_token=settings.digitalocean_token)
    registry = KnowledgeBaseRegistry()
    
    kb = registry.get('x-agency')
    
    print("Retrieving 50 chunks...")
    response = client.retrieve.documents(
        knowledge_base_id=kb.kb_uuid,
        num_results=50,
        query='company business'
    )
    
    content_types = get_available_content_types(response.results)
    doc_sources = get_available_document_sources(response.results)
    
    print(f"\n📊 Content Type Distribution:")
    for ctype, count in sorted(content_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {ctype:30} {count:3} chunks")
    
    print(f"\n📊 Document Source Distribution:")
    for source, count in sorted(doc_sources.items(), key=lambda x: x[1], reverse=True):
        print(f"  {source:30} {count:3} chunks")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test client-side YAML filtering for KB retrieval",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--demo",
        type=int,
        choices=[1, 2, 3, 4, 5],
        help="Run specific demo (1-5), or run all if not specified"
    )
    
    args = parser.parse_args()
    
    if args.demo:
        demos = {
            1: demo_basic_filtering,
            2: demo_two_step_filtering,
            3: demo_custom_filter,
            4: demo_combined_filters,
            5: demo_analysis
        }
        demos[args.demo]()
    else:
        # Run all demos
        demo_basic_filtering()
        demo_two_step_filtering()
        demo_custom_filter()
        demo_combined_filters()
        demo_analysis()
        
        print("\n" + "="*80)
        print("✅ All demos completed!")
        print("="*80)


if __name__ == "__main__":
    main()

