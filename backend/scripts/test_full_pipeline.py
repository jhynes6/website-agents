#!/usr/bin/env python3
"""
Test the full pipeline: Ingest → Supabase Storage → Pinecone → Chatbot

This script tests end-to-end functionality for a client.
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

import httpx
from app.config import get_settings

async def test_pipeline(client_slug: str = "a-perfect-promotion"):
    """Test the complete pipeline for a client."""
    settings = get_settings()
    backend_url = "http://localhost:8000/api/mintagent"
    
    print(f"🧪 Testing Full Pipeline for: {client_slug}")
    print("=" * 80)
    
    # Test 1: Check Supabase Storage
    print("\n1️⃣ Testing Supabase Storage...")
    try:
        from app.clients.supabase_agent_storage_client import SupabaseAgentStorageClient
        supabase_client = SupabaseAgentStorageClient()
        
        # List files in client folder
        list_url = f"{settings.supabase_agent_url}/storage/v1/object/list/client-data-sources"
        headers = {
            "Authorization": f"Bearer {settings.supabase_agent_key}",
            "apikey": settings.supabase_agent_key
        }
        payload = {
            "prefix": f"{client_slug}/website",
            "limit": 5
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(list_url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                files = resp.json()
                print(f"   ✓ Found {len(files)} files in Supabase Storage")
            else:
                print(f"   ❌ Failed to list files: {resp.status_code}")
                return False
    except Exception as e:
        print(f"   ❌ Supabase Storage test failed: {e}")
        return False
    
    # Test 2: Check Pinecone Namespace
    print("\n2️⃣ Testing Pinecone Namespace...")
    try:
        from pinecone import Pinecone
        pc = Pinecone(api_key=settings.pinecone_api_key)
        index = pc.Index("sb-knowledge-bases")
        
        stats = index.describe_index_stats()
        namespace_stats = stats.namespaces.get(client_slug)
        
        if namespace_stats:
            print(f"   ✓ Namespace '{client_slug}' exists")
            print(f"   ✓ Vector count: {namespace_stats.record_count}")
        else:
            print(f"   ❌ Namespace '{client_slug}' not found")
            return False
    except Exception as e:
        print(f"   ❌ Pinecone test failed: {e}")
        return False
    
    # Test 3: Test Chat Endpoint
    print("\n3️⃣ Testing Chatbot...")
    try:
        chat_url = f"{backend_url}/chat"
        chat_data = {
            "client_slug": client_slug,
            "messages": [
                {"role": "user", "content": "What does this company do?"}
            ],
            "top_k": 3
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(chat_url, json=chat_data, timeout=30)
            if resp.status_code == 200:
                result = resp.json()
                print(f"   ✓ Chat successful")
                print(f"   ✓ Sources retrieved: {len(result['sources'])}")
                print(f"   📝 Response preview: {result['response'][:150]}...")
                
                # Show sources
                if result['sources']:
                    print(f"\n   📚 Top sources:")
                    for i, source in enumerate(result['sources'][:3], 1):
                        print(f"      {i}. {source['title'] or source['doc_id']} (score: {source['score']:.3f})")
            else:
                print(f"   ❌ Chat failed: {resp.status_code} - {resp.text}")
                return False
    except Exception as e:
        print(f"   ❌ Chat test failed: {e}")
        return False
    
    # Test 4: Test Multi-turn Conversation
    print("\n4️⃣ Testing Multi-turn Conversation...")
    try:
        chat_data = {
            "client_slug": client_slug,
            "messages": [
                {"role": "user", "content": "What products do they offer?"},
                {"role": "assistant", "content": "They offer promotional products and custom merchandise."},
                {"role": "user", "content": "How can I contact them?"}
            ],
            "top_k": 3
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(chat_url, json=chat_data, timeout=30)
            if resp.status_code == 200:
                result = resp.json()
                print(f"   ✓ Multi-turn chat successful")
                print(f"   📝 Response: {result['response'][:150]}...")
            else:
                print(f"   ❌ Multi-turn chat failed: {resp.status_code}")
                return False
    except Exception as e:
        print(f"   ❌ Multi-turn chat test failed: {e}")
        return False
    
    print("\n" + "=" * 80)
    print("✅ All pipeline tests passed!")
    print(f"\n📊 Summary:")
    print(f"   - Storage: ✓ Files in Supabase")
    print(f"   - Vectors: ✓ {namespace_stats.record_count} chunks in Pinecone")
    print(f"   - Chatbot: ✓ RAG working correctly")
    print(f"   - Conversation: ✓ Multi-turn chat working")
    
    return True


async def main():
    """Run pipeline tests."""
    import argparse
    parser = argparse.ArgumentParser(description="Test the full pipeline for a client")
    parser.add_argument("--client", default="a-perfect-promotion", help="Client slug to test")
    args = parser.parse_args()
    
    success = await test_pipeline(args.client)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

