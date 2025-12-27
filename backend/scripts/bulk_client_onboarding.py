import asyncio
import csv
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any

# Add backend directory to path so we can import app modules
# Assumes script is in backend/scripts/
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from app.routes.create import create_chatbot
from app.config import get_settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bulk_onboarding.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("bulk_onboarding")

async def process_client(row: Dict[str, str]):
    client_slug = row.get("client-slug")
    drive_id = row.get("drive-folder")
    website = row.get("client-website")

    # Validate required fields: must have slug and at least one content source
    if not client_slug or not (website or drive_id):
        logger.warning(f"Skipping row due to missing slug or both website/drive: {row}")
        return

    logger.info(f"Starting onboarding for client: {client_slug}")
    logger.info(f"  - Website: {website or 'N/A'}")
    logger.info(f"  - Drive ID: {drive_id or 'N/A'}")

    url_value = None
    if website:
        url_value = f"https://{website}" if not website.startswith("http") else website

    # Keep payload aligned with create.py expectations
    payload = {
        "url": url_value,
        "clientSlug": client_slug,
        # Support all accepted drive folder keys to avoid mismatch
        "clientDriveFolder": drive_id,
        "driveFolderId": drive_id,
        "driveFolder": drive_id,
        "skipRedisSave": True,  # no-op but kept for compatibility
    }

    try:
        result = await create_chatbot(payload)
        logger.info(f"Successfully processed {client_slug}")
        logger.info(f"  - Pages Processed: {result.get('pages_processed')}")
        logger.info(f"  - Drive Docs: {result.get('drive_docs_processed')}")
        logger.info(f"  - Total Docs: {result.get('total_documents')}")
        
        do_info = result.get("digital_ocean", {})
        logger.info(f"  - DO KB UUID: {do_info.get('kb_uuid')}")
        logger.info(f"  - Source Added: {do_info.get('source_added')}")

    except Exception as e:
        logger.error(f"Failed to onboard {client_slug}: {str(e)}", exc_info=True)

async def main():
    # Path to CSV file (in root of project, two levels up from scripts/)
    csv_path = backend_dir.parent / "backend/scripts/io/bulk_onboarding_run_file.csv"

    if not csv_path.exists():
        logger.error(f"CSV file not found at: {csv_path}")
        return

    logger.info(f"Reading clients from {csv_path}")

    clients = []
    with open(csv_path, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            clients.append(row)

    logger.info(f"Found {len(clients)} clients to process.")

    for i, client in enumerate(clients, 1):
        logger.info(f"[{i}/{len(clients)}] Processing {client.get('client-slug')}...")
        await process_client(client)
        # Optional: Add a small delay between clients to avoid rate limits if needed
        # await asyncio.sleep(5) 

if __name__ == "__main__":
    asyncio.run(main())

