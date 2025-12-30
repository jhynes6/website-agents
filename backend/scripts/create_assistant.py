#!/usr/bin/env python3
"""
Create a Pinecone Assistant for a client's knowledge base.

This script creates a new assistant and uploads all markdown files
from Supabase Storage to populate the assistant's knowledge base.
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any, List
from urllib.parse import quote

import httpx

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from pinecone import Pinecone
from app.config import get_settings
from app.clients.supabase_storage_client import SupabaseStorageClient


def _resolve_storage_key(settings) -> str:
    # Prefer service role if present (more reliable for list/download)
    for k in ("SUPABASE_AGENT_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_ROLE_KEY"):
        v = (os.getenv(k) or "").strip()
        if v:
            return v
    return (settings.supabase_agent_key or "").strip()


def _supabase_storage_client(settings) -> SupabaseStorageClient:
    api_key = _resolve_storage_key(settings)
    return SupabaseStorageClient(project_url=str(settings.supabase_agent_url or ""), service_role_key=api_key)


def _detect_storage_layout(settings, client_slug: str) -> tuple[str, str]:
    """
    Returns (bucket_name, prefix_base)

    - bucket-per-client: bucket = client_slug, prefix_base = ""
    - shared bucket: bucket = client-data-sources, prefix_base = f"{client_slug}/"
    """
    c = _supabase_storage_client(settings)
    bucket_ids = {str(b.get("id") or b.get("name") or "").strip() for b in c.list_buckets() if isinstance(b, dict)}
    if client_slug in bucket_ids:
        return client_slug, ""
    return "client-data-sources", f"{client_slug}/"


async def list_client_markdown_files(client_slug: str) -> List[tuple[str, str, str]]:
    """
    List all markdown files for a client from Supabase Storage.

    Returns tuples: (bucket, object_path, filename)
    """
    settings = get_settings()
    c = _supabase_storage_client(settings)
    bucket, base = _detect_storage_layout(settings, client_slug)

    all_files: List[tuple[str, str, str]] = []
    for subfolder in ["website", "drive", "intake_form"]:
        prefix = f"{base}{subfolder}/"
        try:
            objects = c.list_objects(bucket, prefix=prefix, limit=1000, offset=0, sort_by={"column": "name", "order": "asc"})
            for obj in objects:
                if not isinstance(obj, dict):
                    continue
                name = str(obj.get("name") or "").strip()
                if not name or name == ".keep" or not name.endswith(".md"):
                    continue
                object_path = f"{prefix}{name}"
                all_files.append((bucket, object_path, name))
        except Exception as e:
            print(f"  ⚠️  Error listing {subfolder}: {e}")

    return all_files


async def create_assistant_for_client(
    client_slug: str,
    instructions: str = None,
    force_recreate: bool = False
) -> Dict[str, Any]:
    """
    Create a Pinecone Assistant for a client and upload their documents.
    
    Args:
        client_slug: Client identifier (becomes assistant name)
        instructions: Custom instructions for the assistant
        force_recreate: If True, delete existing assistant and create new one
    
    Returns:
        Dictionary with assistant info and upload stats
    """
    settings = get_settings()
    
    if not settings.pinecone_api_key:
        print("❌ PINECONE_API_KEY not configured")
        return {"success": False, "error": "Missing Pinecone API key"}
    
    print(f"\n🤖 Creating Pinecone Assistant for: {client_slug}")
    print("=" * 80)
    
    # Initialize Pinecone
    pc = Pinecone(api_key=settings.pinecone_api_key)
    
    # Assistant name is the client slug
    assistant_name = client_slug
    
    # Check if assistant already exists
    try:
        existing_assistants = pc.assistant.list_assistants()
        # Handle both dict and list responses
        if isinstance(existing_assistants, dict):
            assistants_list = existing_assistants.get("assistants", [])
        elif isinstance(existing_assistants, list):
            assistants_list = existing_assistants
        else:
            assistants_list = []
        
        assistant_exists = any(
            a.name == assistant_name 
            for a in assistants_list
        )
        
        if assistant_exists:
            if force_recreate:
                print(f"  🗑️  Deleting existing assistant: {assistant_name}")
                pc.assistant.delete_assistant(assistant_name=assistant_name)
                print(f"  ✓ Deleted")
            else:
                print(f"  ⚠️  Assistant '{assistant_name}' already exists")
                print(f"      Use --force to recreate")
                return {
                    "success": True,
                    "skipped": True,
                    "reason": "Assistant already exists",
                    "assistant_name": assistant_name,
                }
    except Exception as e:
        print(f"  ⚠️  Error checking existing assistants: {e}")
    
    # Default instructions
    if not instructions:
        instructions = f"""You are a helpful AI assistant with knowledge about {client_slug}.
Answer questions based on the provided documents about this organization.
Be concise, accurate, and cite sources when possible.
If you don't know the answer, say so clearly."""
    
    # Create the assistant
    print(f"\n1️⃣ Creating assistant...")
    try:
        assistant = pc.assistant.create_assistant(
            assistant_name=assistant_name,
            instructions=instructions,
            timeout=30
        )
        print(f"  ✓ Assistant '{assistant_name}' created")
        print(f"  ✓ Status: {assistant.status}")
    except Exception as e:
        print(f"  ❌ Failed to create assistant: {e}")
        return {"success": False, "error": str(e)}
    
    # Get Supabase client
    supabase_client = _supabase_storage_client(settings)
    
    # List all markdown files
    print(f"\n2️⃣ Listing files from Supabase Storage...")
    files = await list_client_markdown_files(client_slug)
    print(f"  ✓ Found {len(files)} markdown files")
    
    if not files:
        print(f"  ⚠️  No files found for {client_slug}")
        return {
            "success": True,
            "assistant_name": assistant_name,
            "files_uploaded": 0,
            "warning": "No files to upload"
        }
    
    # Download and upload files to assistant
    print(f"\n3️⃣ Uploading files to assistant...")
    uploaded_count = 0
    failed_count = 0
    
    # Create temp directory for downloads
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        for bucket, file_path, file_name in files:
            try:
                # Download from Supabase (Storage API)
                content_bytes = httpx.get(
                    f"{supabase_client.base_url}/object/{bucket}/{quote(file_path, safe='/')}",
                    headers=supabase_client._headers(),
                    timeout=60,
                ).content
                if not content_bytes:
                    print(f"  ⚠️  Skipped (empty): {file_name}")
                    failed_count += 1
                    continue
                
                # Save to temp file
                safe_filename = file_name.replace("/", "_")
                local_file = temp_path / safe_filename
                local_file.write_bytes(content_bytes)
                
                # Upload to assistant
                pc.assistant.Assistant(assistant_name=assistant_name).upload_file(
                    file_path=str(local_file),
                    timeout=None  # Wait for processing
                )
                
                uploaded_count += 1
                print(f"  ✓ Uploaded: {file_name} ({len(content_bytes)} bytes)")
                
            except Exception as e:
                print(f"  ❌ Failed to upload {file_name}: {e}")
                failed_count += 1
    
    print(f"\n" + "=" * 80)
    print(f"✅ Assistant creation complete!")
    print(f"\n📊 Summary:")
    print(f"   - Assistant Name: {assistant_name}")
    print(f"   - Files Uploaded: {uploaded_count}")
    print(f"   - Failed: {failed_count}")
    print(f"   - Status: {assistant.status}")
    
    print(f"\n💬 Test your assistant:")
    print(f"   - Console: https://app.pinecone.io/organizations/-/projects/-/assistant")
    print(f"   - API: POST /assistant/chat/{assistant_name}")
    
    return {
        "success": True,
        "assistant_name": assistant_name,
        "files_uploaded": uploaded_count,
        "files_failed": failed_count,
        "assistant_status": assistant.status
    }


async def main():
    """Run assistant creation."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Create a Pinecone Assistant for a client's knowledge base"
    )
    parser.add_argument(
        "client_slug",
        help="Client slug (becomes assistant name)"
    )
    parser.add_argument(
        "--instructions",
        help="Custom instructions for the assistant",
        default=None
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete and recreate if assistant exists"
    )
    
    args = parser.parse_args()
    
    result = await create_assistant_for_client(
        client_slug=args.client_slug,
        instructions=args.instructions,
        force_recreate=args.force
    )
    
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    asyncio.run(main())

