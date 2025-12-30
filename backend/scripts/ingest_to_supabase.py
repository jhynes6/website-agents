"""
Ingest client files to Supabase Storage by calling the backend create_chatbot function.

This ensures we use the same cleaning, categorization, and file naming logic as the UI.
"""
import asyncio
import csv
import logging
import os
import sys
import httpx
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

# Import the actual backend function
from app.routes.create import create_chatbot
from app.config import get_settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("supabase_ingest.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("supabase_ingest")


def _ensure_project_root_cwd() -> Path:
    """Make relative paths deterministic by changing to project root."""
    project_root = backend_dir.parent
    try:
        os.chdir(project_root)
    except Exception:
        pass
    return project_root


def _load_environment():
    """Load environment variables from backend/.env"""
    project_root = backend_dir.parent
    env_path = project_root / "backend" / ".env"
    
    if env_path.exists():
        logger.info(f"Loading environment from: {env_path}")
        load_dotenv(env_path)
    else:
        logger.warning(f"No .env file found at: {env_path}")


def verify_bucket_exists() -> bool:
    """
    Verify that the main 'client-data-sources' bucket exists.
    
    This is a one-time setup - all clients use the same bucket.
    """
    BUCKET_NAME = "client-data-sources"
    
    # Check if we have service role key (needed to verify bucket)
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not service_role_key:
        logger.warning(
            f"No SUPABASE_SERVICE_ROLE_KEY found. Cannot verify bucket exists.\n"
            f"If you get errors, ensure the bucket exists by running this SQL:\n"
            f"INSERT INTO storage.buckets (id, name, public, file_size_limit) "
            f"VALUES ('{BUCKET_NAME}', '{BUCKET_NAME}', false, 104857600) "
            f"ON CONFLICT (id) DO NOTHING;"
        )
        return False
    
    # Use service role key to check bucket via Storage API
    base_url = os.getenv("SUPABASE_AGENT_URL", "").rstrip("/")
    storage_url = f"{base_url}/storage/v1"
    
    headers = {
        "Authorization": f"Bearer {service_role_key}",
        "apikey": service_role_key
    }
    
    # Try to get the bucket
    try:
        response = httpx.get(
            f"{storage_url}/bucket/{BUCKET_NAME}",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            logger.info(f"✓ Bucket verified: {BUCKET_NAME}")
            return True
        else:
            logger.error(
                f"Bucket {BUCKET_NAME} not found: {response.status_code} - {response.text}\n"
                f"Create it with SQL:\n"
                f"INSERT INTO storage.buckets (id, name, public, file_size_limit) "
                f"VALUES ('{BUCKET_NAME}', '{BUCKET_NAME}', false, 104857600) "
                f"ON CONFLICT (id) DO NOTHING;"
            )
            return False
    except Exception as e:
        logger.error(f"Error verifying bucket {BUCKET_NAME}: {e}")
        return False


async def ingest_client(row: Dict[str, str]) -> Dict[str, Any]:
    """
    Ingest a client by calling the backend's create_chatbot function.
    
    This ensures we use the same logic as the UI:
    - LLM-based markdown cleaning
    - Content categorization
    - Proper file naming
    - Upload to Supabase Storage
    """
    client_slug = row.get("client-slug", "").strip()
    drive_url = row.get("drive-folder", "").strip()
    website = row.get("client-website", "").strip()
    
    if not client_slug:
        raise ValueError("client-slug is required")
    
    if not drive_url and not website:
        raise ValueError(f"Client {client_slug} must have either drive-folder or client-website")
    
    logger.info(f"Processing client: {client_slug}")
    logger.info(f"  Website: {website or 'N/A'}")
    logger.info(f"  Drive: {drive_url or 'N/A'}")
    
    # Normalize website URL
    website_url = None
    if website:
        website_url = f"https://{website}" if not website.startswith("http") else website
    
    # Build payload for create_chatbot (same as UI sends)
    payload = {
        "url": website_url,
        "clientSlug": client_slug,
        "clientDriveFolder": drive_url,
        "driveFolderId": drive_url,
        "driveFolder": drive_url,
        "limit": 100,  # Adjust as needed
        "maxDepth": 3,
        "blogLimit": 50,
        "skipRedisSave": True,  # Don't save to Redis
    }
    
    # Call the backend function (uses all the proper logic)
    result = await create_chatbot(payload)
    
    logger.info(f"✅ Client '{client_slug}' ingestion complete!")
    logger.info(f"   Website docs: {result.get('pages_processed', 0)}")
    logger.info(f"   Drive docs: {result.get('drive_docs_processed', 0)}")
    logger.info(f"   Total docs: {result.get('total_documents', 0)}")
    
    ingestion = result.get('ingestion', {})
    logger.info(f"   Uploaded to Supabase: {ingestion.get('uploaded_to_supabase', 0)}")
    
    return {
        "client_slug": client_slug,
        "success": True,
        "pages_processed": result.get('pages_processed', 0),
        "drive_docs_processed": result.get('drive_docs_processed', 0),
        "total_documents": result.get('total_documents', 0),
        "uploaded_to_supabase": ingestion.get('uploaded_to_supabase', 0),
    }


async def main():
    """Main entry point for ingesting client data."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest client files using backend logic")
    parser.add_argument(
        "--client-slug",
        type=str,
        help="Process specific client by slug (e.g., abundantly). If not provided, processes first client."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all clients from CSV"
    )
    args = parser.parse_args()
    
    project_root = _ensure_project_root_cwd()
    logger.info("=" * 80)
    logger.info("Supabase Client Ingestion Script (via Backend)")
    logger.info("=" * 80)
    logger.info(f"Project root: {project_root}")
    
    # Load environment
    _load_environment()
    
    # Verify configuration
    s = get_settings()
    if not s.supabase_agent_url or not s.supabase_agent_key:
        logger.warning("⚠️  SUPABASE_AGENT_URL and SUPABASE_AGENT_KEY not configured")
        logger.warning("    Files will not be uploaded to Supabase Storage")
    else:
        logger.info(f"✓ Supabase Agent configured: {s.supabase_agent_url}")
        # Verify the main bucket exists
        logger.info("\nVerifying Supabase Storage bucket...")
        verify_bucket_exists()
    
    if not s.firecrawl_api_key:
        logger.error("❌ FIRECRAWL_API_KEY must be configured")
        return
    
    logger.info(f"✓ Firecrawl configured")
    
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
    
    # Determine which clients to process
    clients_to_process = []
    
    if args.all:
        clients_to_process = clients
        logger.info("=" * 80)
        logger.info(f"Processing ALL {len(clients)} CLIENTS")
        logger.info("=" * 80)
    elif args.client_slug:
        target_client = None
        for client in clients:
            if client.get("client-slug") == args.client_slug:
                target_client = client
                break
        
        if target_client:
            clients_to_process = [target_client]
            logger.info("=" * 80)
            logger.info(f"Processing SPECIFIC CLIENT: {args.client_slug}")
            logger.info("=" * 80)
        else:
            logger.error(f"Client '{args.client_slug}' not found in CSV")
            logger.info(f"Available clients: {', '.join([c.get('client-slug', '') for c in clients[:5]])}...")
            return
    else:
        if clients:
            clients_to_process = [clients[0]]
            logger.info("=" * 80)
            logger.info("Processing FIRST CLIENT ONLY (test mode)")
            logger.info("=" * 80)
    
    # Process the selected clients
    success_count = 0
    failed_count = 0
    
    for i, client in enumerate(clients_to_process, 1):
        client_slug = client.get("client-slug", "unknown")
        logger.info(f"\n{'=' * 80}")
        logger.info(f"[{i}/{len(clients_to_process)}] {client_slug}")
        logger.info(f"{'=' * 80}")
        
        try:
            result = await ingest_client(client)
            success_count += 1
        except Exception as e:
            logger.error(f"\n❌ FAILED for {client_slug}: {str(e)}", exc_info=True)
            failed_count += 1
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total processed: {len(clients_to_process)}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {failed_count}")
    logger.info("=" * 80)
    logger.info("\nScript complete. Check supabase_ingest.log for details.")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
