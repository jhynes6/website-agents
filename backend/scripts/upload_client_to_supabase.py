"""
Upload client onboarding data to Supabase Agent Storage.

This script reads client information and uploads it as JSON to Supabase Storage
for processing by agent workflows.
"""
import asyncio
import csv
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from app.clients.supabase_agent_storage_client import SupabaseAgentStorageClient
from app.config import get_settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("supabase_upload.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("supabase_upload")


def _ensure_project_root_cwd() -> Path:
    """
    Make relative paths deterministic by changing to project root.
    """
    project_root = backend_dir.parent
    try:
        os.chdir(project_root)
    except Exception:
        pass
    return project_root


def _load_environment():
    """
    Load environment variables from backend/.env
    """
    project_root = backend_dir.parent
    env_path = project_root / "backend" / ".env"
    
    if env_path.exists():
        logger.info(f"Loading environment from: {env_path}")
        load_dotenv(env_path)
    else:
        logger.warning(f"No .env file found at: {env_path}")
        
    # Also try loading from project root
    root_env = project_root / ".env"
    if root_env.exists():
        logger.info(f"Also loading from: {root_env}")
        load_dotenv(root_env)


def _verify_supabase_connection() -> SupabaseAgentStorageClient:
    """
    Validate Supabase Agent configuration and return storage client.
    """
    s = get_settings()
    
    if not s.supabase_agent_url:
        raise RuntimeError("SUPABASE_AGENT_URL is not configured (check backend/.env)")
    
    if not s.supabase_agent_key:
        raise RuntimeError("SUPABASE_AGENT_KEY is not configured (check backend/.env)")
    
    logger.info(f"Supabase Agent URL: {s.supabase_agent_url}")
    logger.info("Supabase Agent Key: ***configured***")
    
    client = SupabaseAgentStorageClient()
    
    # List buckets to verify connection
    try:
        buckets = client.list_buckets()
        logger.info(f"Connected to Supabase. Found {len(buckets)} buckets:")
        for bucket in buckets:
            logger.info(f"  - {bucket.get('name')} (public: {bucket.get('public', False)})")
    except Exception as e:
        logger.error(f"Failed to connect to Supabase: {e}")
        raise
    
    return client


def extract_drive_folder_id(drive_url: str) -> Optional[str]:
    """
    Extract Google Drive folder ID from a URL.
    
    Supports formats:
    - https://drive.google.com/drive/folders/1vKv7hXOxc2-Z9lOhQrqhNKCRqzPNrEED
    - 1vKv7hXOxc2-Z9lOhQrqhNKCRqzPNrEED (raw ID)
    """
    if not drive_url:
        return None
    
    drive_url = drive_url.strip()
    
    # If it's already just an ID (no slashes)
    if '/' not in drive_url:
        return drive_url
    
    # Extract from URL
    if '/folders/' in drive_url:
        parts = drive_url.split('/folders/')
        if len(parts) > 1:
            folder_id = parts[1].split('?')[0].strip()
            return folder_id
    
    return None


def prepare_metadata_json(row: Dict[str, str]) -> Dict[str, Any]:
    """
    Prepare metadata.json structure for a client bucket.
    
    Initially contains just URLs and placeholders for document counts.
    Stats will be populated after document processing.
    """
    client_slug = row.get("client-slug", "").strip()
    drive_url = row.get("drive-folder", "").strip()
    website = row.get("client-website", "").strip()
    
    # Normalize website URL
    website_url = None
    if website:
        website_url = f"https://{website}" if not website.startswith("http") else website
    
    metadata = {
        "client_slug": client_slug,
        "website_url": website_url,
        "drive_url": drive_url if drive_url else None,
        "website_docs": {
            "total": 0,
            "by_content_type": {}
        },
        "drive_docs": {
            "total": 0,
            "by_content_type": {}
        },
        "intake_form_docs": 0,
        "page_breakdowns": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "initialized",
        "metadata": {}
    }
    
    return metadata


async def setup_client_bucket(
    storage_client: SupabaseAgentStorageClient,
    row: Dict[str, str]
) -> Dict[str, Any]:
    """
    Set up a complete client folder in the shared bucket with folder structure and metadata.
    
    Structure:
    client-data-sources/       (bucket)
    └── {client-slug}/
        ├── metadata.json
        ├── website/
        ├── drive/
        └── intake_form/
    """
    client_slug = row.get("client-slug", "").strip()
    
    if not client_slug:
        raise ValueError("client-slug is required")
    
    # Validate required data
    drive_url = row.get("drive-folder", "").strip()
    website = row.get("client-website", "").strip()
    
    if not drive_url and not website:
        raise ValueError(f"Client {client_slug} must have either drive-folder or client-website")
    
    logger.info(f"Setting up bucket for client: {client_slug}")
    logger.info(f"  Website: {website or 'N/A'}")
    logger.info(f"  Drive: {drive_url or 'N/A'}")
    
    # Prepare metadata
    metadata = prepare_metadata_json(row)
    
    # Shared bucket
    bucket_name = "client-data-sources"
    logger.info(f"  Ensuring shared bucket: {bucket_name}")
    
    try:
        storage_client.ensure_bucket(bucket_name, public=False)
        logger.info(f"  ✓ Bucket '{bucket_name}' ready (shared)")
    except Exception as e:
        logger.warning(f"  Could not create bucket (may already exist): {e}")
    
    # 2. Create folder structure by uploading .keep files
    folders = ["website", "drive", "intake_form"]
    for folder in folders:
        try:
            keep_path = f"{client_slug}/{folder}/.keep"
            storage_client.upload_bytes(
                bucket=bucket_name,
                path=keep_path,
                data=b"# This file ensures the folder exists in Supabase Storage\n",
                content_type="text/plain; charset=utf-8"
            )
            logger.info(f"  ✓ Created folder: {client_slug}/{folder}/")
        except Exception as e:
            logger.warning(f"  Could not create folder {folder}: {e}")
    
    # 3. Upload metadata.json to client folder root
    try:
        result = storage_client.upload_json(
            bucket=bucket_name,
            path=f"{client_slug}/metadata.json",
            payload=metadata
        )
        logger.info(f"  ✓ Uploaded: metadata.json")
    except Exception as e:
        logger.error(f"  Failed to upload metadata.json: {e}")
        raise
    
    logger.info(f"✅ Client '{client_slug}' bucket setup complete!")
    
    return {
        "client_slug": client_slug,
        "bucket_name": bucket_name,
        "folders_created": folders,
        "metadata": metadata
    }


async def main():
    """
    Main entry point for uploading client data to Supabase.
    """
    project_root = _ensure_project_root_cwd()
    logger.info("=" * 80)
    logger.info("Supabase Client Upload Script")
    logger.info("=" * 80)
    logger.info(f"Project root: {project_root}")
    
    # Load environment
    _load_environment()
    
    # Verify connection
    storage_client = _verify_supabase_connection()
    
    # Path to CSV file
    csv_path = backend_dir / "scripts" / "io" / "bulk_onboarding_run_file.csv"
    
    if not csv_path.exists():
        logger.error(f"CSV file not found at: {csv_path}")
        return
    
    logger.info(f"\nReading clients from: {csv_path}")
    
    # Read CSV
    clients = []
    with open(csv_path, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            clients.append(row)
    
    logger.info(f"Found {len(clients)} clients in CSV\n")
    
    # For testing: process just the first client
    if clients:
        logger.info("=" * 80)
        logger.info("Processing FIRST CLIENT ONLY (test mode)")
        logger.info("=" * 80)
        
        first_client = clients[0]
        try:
            result = await setup_client_bucket(storage_client, first_client)
            logger.info("\n✅ SUCCESS!")
            logger.info(f"Client: {result['client_slug']}")
            logger.info(f"Bucket: {result['bucket_name']}")
            logger.info(f"Folders: {', '.join(result['folders_created'])}")
            logger.info(f"\nMetadata:")
            logger.info(json.dumps(result['metadata'], indent=2))
        except Exception as e:
            logger.error(f"\n❌ FAILED: {str(e)}", exc_info=True)
    
    logger.info("\n" + "=" * 80)
    logger.info("Script complete. Check supabase_upload.log for details.")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

