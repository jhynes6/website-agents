#!/usr/bin/env python3
"""
List all client folders in Supabase Storage.

Usage:
    python list_clients.py
"""
import sys
import json
import httpx
from pathlib import Path
from dotenv import load_dotenv
import os

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

# Load environment
env_path = backend_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)

from app.config import get_settings


def list_clients():
    """List all client folders in the bucket (top-level folders only)."""
    settings = get_settings()
    
    if not settings.supabase_agent_url or not settings.supabase_agent_key:
        print("❌ Error: SUPABASE_AGENT_URL and SUPABASE_AGENT_KEY must be set")
        return
    
    BUCKET_NAME = "client-data-sources"
    base_url = str(settings.supabase_agent_url).rstrip("/")
    storage_url = f"{base_url}/storage/v1"
    
    headers = {
        "Authorization": f"Bearer {settings.supabase_agent_key}",
        "apikey": settings.supabase_agent_key
    }
    
    # Build the list URL
    list_url = f"{storage_url}/object/list/{BUCKET_NAME}"
    
    # Request only folders at root level
    payload = {
        "limit": 1000,
        "offset": 0,
        "prefix": "",  # Empty prefix for root level
        "sortBy": {
            "column": "name",
            "order": "asc"
        }
    }
    
    print(f"🔍 Listing client folders in bucket: {BUCKET_NAME}")
    print(f"🌐 API URL: {list_url}")
    print(f"📤 Payload: {json.dumps(payload, indent=2)}")
    print("\n" + "="*80 + "\n")
    
    try:
        # Make the API request
        response = httpx.post(
            list_url,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"📊 Status Code: {response.status_code}")
        print("\n" + "="*80 + "\n")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS - Raw API Response:")
            print(json.dumps(data, indent=2))
            
            # Filter and display only folders (client folders)
            if isinstance(data, list):
                # Folders have metadata = null
                client_folders = [
                    item.get("name") 
                    for item in data 
                    if item.get("metadata") is None and item.get("name")
                ]
                
                print("\n" + "="*80)
                print(f"\n📁 Client Folders ({len(client_folders)}):\n")
                
                for idx, folder in enumerate(client_folders, 1):
                    print(f"   {idx}. {folder}")
                
                print(f"\n   Total: {len(client_folders)} clients")
            
        else:
            print(f"❌ ERROR - Response:")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        import traceback
        traceback.print_exc()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="List all client folders in Supabase Storage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This shows all top-level folders in the client-data-sources bucket.
Each folder represents a client (by their client-slug).
        """
    )
    
    args = parser.parse_args()
    list_clients()


if __name__ == "__main__":
    main()

