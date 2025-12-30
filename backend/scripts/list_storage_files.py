#!/usr/bin/env python3
"""
Helper script to list all files in a Supabase Storage folder.
Shows raw API response.

Usage:
    python list_storage_files.py <folder_path>
    
Examples:
    python list_storage_files.py a-perfect-promotion
    python list_storage_files.py a-perfect-promotion/website
    python list_storage_files.py a-perfect-promotion/website/blog
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


def list_files(folder_path: str = "", limit: int = 1000, offset: int = 0):
    """
    List all files in a Supabase Storage folder.
    
    Args:
        folder_path: Path within the bucket (e.g., "a-perfect-promotion" or "a-perfect-promotion/website")
        limit: Maximum number of objects to return
        offset: Number of objects to skip
    """
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
    
    # Build the list URL with query parameters
    list_url = f"{storage_url}/object/list/{BUCKET_NAME}"
    
    # Prepare payload
    payload = {
        "limit": limit,
        "offset": offset,
        "prefix": folder_path.strip("/") if folder_path else "",  # Always include prefix (required by API)
        "search": "",  # Empty search to get all files
        "sortBy": {
            "column": "name",
            "order": "asc"
        }
    }
    
    print(f"🔍 Listing files in bucket: {BUCKET_NAME}")
    if folder_path:
        print(f"📁 Folder: {folder_path}")
    else:
        print(f"📁 Folder: / (root)")
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
        print(f"📝 Headers: {json.dumps(dict(response.headers), indent=2)}")
        print("\n" + "="*80 + "\n")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS - Raw API Response:")
            print(json.dumps(data, indent=2))
            
            # Print summary
            if isinstance(data, list):
                print("\n" + "="*80)
                print(f"\n📈 Summary:")
                print(f"   Total items returned: {len(data)}")
                
                folders = [item for item in data if item.get("metadata") is None]
                files = [item for item in data if item.get("metadata") is not None]
                
                if folders:
                    print(f"\n   📁 Folders ({len(folders)}):")
                    for item in folders:
                        print(f"      - {item.get('name', 'unknown')}/")
                
                if files:
                    print(f"\n   📄 Files ({len(files)}):")
                    for item in files:
                        name = item.get("name", "unknown")
                        metadata = item.get("metadata", {})
                        size = metadata.get("size", "unknown") if metadata else "unknown"
                        mimetype = metadata.get("mimetype", "") if metadata else ""
                        print(f"      - {name} ({size} bytes) {mimetype}")
            
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
        description="List files in Supabase Storage folder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  List all files for a client:
    python list_storage_files.py a-perfect-promotion
    
  List only website files:
    python list_storage_files.py a-perfect-promotion/website
    
  List specific subfolder:
    python list_storage_files.py a-perfect-promotion/website/blog
    
  List everything (root):
    python list_storage_files.py
        """
    )
    
    parser.add_argument(
        "folder_path",
        nargs="?",
        default="",
        help="Folder path to list (e.g., 'a-perfect-promotion' or 'a-perfect-promotion/website')"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Maximum number of files to return (default: 1000)"
    )
    
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Number of files to skip (default: 0)"
    )
    
    args = parser.parse_args()
    
    list_files(
        folder_path=args.folder_path,
        limit=args.limit,
        offset=args.offset
    )


if __name__ == "__main__":
    main()

