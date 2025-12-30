#!/usr/bin/env python3
"""
Test script to verify Supabase Storage upload functionality.
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from dotenv import load_dotenv
from app.clients.supabase_agent_storage_client import SupabaseAgentStorageClient

# Load environment
env_path = backend_dir / ".env"
load_dotenv(env_path)

def test_upload():
    """Test basic upload functionality."""
    print("=" * 80)
    print("Testing Supabase Storage Upload")
    print("=" * 80)
    
    # Initialize client
    try:
        client = SupabaseAgentStorageClient()
        print(f"✓ Client initialized: {client.project_url}")
    except Exception as e:
        print(f"✗ Failed to initialize client: {e}")
        return False
    
    bucket_name = "a-perfect-promotion"
    
    # Test 1: Check if bucket exists
    print(f"\n1. Checking if bucket '{bucket_name}' exists...")
    try:
        exists = client.bucket_exists(bucket_name)
        print(f"   {'✓' if exists else '✗'} Bucket exists: {exists}")
    except Exception as e:
        print(f"   ✗ Error checking bucket: {e}")
        return False
    
    # Test 2: Upload a simple test file
    print(f"\n2. Uploading test file...")
    test_content = b"# Test Document\n\nThis is a test."
    test_path = "test/test-file.md"
    
    try:
        result = client.upload_bytes(
            bucket=bucket_name,
            path=test_path,
            data=test_content,
            content_type="text/markdown; charset=utf-8",
            upsert=True
        )
        print(f"   ✓ Upload successful!")
        print(f"   Result: {result}")
    except Exception as e:
        print(f"   ✗ Upload failed: {e}")
        return False
    
    # Test 3: List objects in bucket
    print(f"\n3. Listing objects in bucket...")
    try:
        objects = client.list_objects(bucket=bucket_name, prefix="test/")
        print(f"   ✓ Found {len(objects)} objects")
        for obj in objects:
            print(f"     - {obj.get('name')}")
    except Exception as e:
        print(f"   ✗ Failed to list objects: {e}")
    
    # Test 4: Upload with YAML frontmatter (like real docs)
    print(f"\n4. Uploading document with YAML frontmatter...")
    yaml_content = """---
doc_id: "aperfectpromotion.com/test.md"
client_slug: "a-perfect-promotion"
document_source: "website"
url: "https://aperfectpromotion.com/test"
title: "Test Page"
content_type: "other"
ingested_at: "2025-12-29T20:45:00.000000+00:00"
---

# Test Page

This is a test page with YAML frontmatter.
""".encode("utf-8")
    
    try:
        result = client.upload_bytes(
            bucket=bucket_name,
            path="website/aperfectpromotion.com_test.md",
            data=yaml_content,
            content_type="text/markdown; charset=utf-8",
            upsert=True
        )
        print(f"   ✓ Upload with frontmatter successful!")
    except Exception as e:
        print(f"   ✗ Upload failed: {e}")
        return False
    
    print("\n" + "=" * 80)
    print("✓ All tests passed!")
    print("=" * 80)
    return True

if __name__ == "__main__":
    success = test_upload()
    sys.exit(0 if success else 1)

