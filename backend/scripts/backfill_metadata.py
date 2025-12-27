import asyncio
import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime

# Add backend directory to path to import app modules
# Script is in backend/scripts/, so we need to add backend/
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.clients.digital_ocean_client import do_client
from app.config import get_settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def backfill_metadata():
    settings = get_settings()
    if not settings.digitalocean_spaces_bucket or not do_client.s3_client:
        logger.error("Spaces not configured or client initialization failed.")
        return

    bucket = settings.digitalocean_spaces_bucket
    logger.info(f"Scanning bucket: {bucket} for existing clients...")

    # List all objects
    paginator = do_client.s3_client.get_paginator('list_objects_v2')
    
    clients = defaultdict(list)
    existing_metadata = set()

    object_count = 0
    for page in paginator.paginate(Bucket=bucket):
        if 'Contents' not in page:
            continue
            
        for obj in page['Contents']:
            object_count += 1
            key = obj['Key']
            # Expected structure: client_slug/...
            parts = key.split('/')
            if len(parts) < 2:
                continue
                
            client_slug = parts[0]
            if key.endswith('metadata.json') and len(parts) == 2:
                existing_metadata.add(client_slug)
            else:
                clients[client_slug].append(obj)

    logger.info(f"Scanned {object_count} objects.")
    logger.info(f"Found {len(clients)} potential clients/namespaces.")
    logger.info(f"Found {len(existing_metadata)} existing metadata.json files.")

    for client_slug, objects in clients.items():
        # Force update even if exists to fix the key name
        # if client_slug in existing_metadata:
        #     logger.info(f"Skipping {client_slug} (metadata.json already exists)")
        #     continue

        logger.info(f"Processing {client_slug}...")
        
        pages_crawled = 0
        created_at = None
        representative_doc_key = None
        
        # Analyze objects for this client
        for obj in objects:
            key = obj['Key']
            
            # Count pages (markdown files)
            if key.endswith('.md'):
                pages_crawled += 1
                
                # Determine creation time (earliest file modified time)
                ts = obj['LastModified']
                if created_at is None or ts < created_at:
                    created_at = ts
                
                # Select a representative document to extract metadata
                # Prefer website pages over others
                if 'website' in key and not representative_doc_key:
                    representative_doc_key = key
                elif not representative_doc_key:
                    representative_doc_key = key

        if not created_at:
            created_at = datetime.now()

        # Initialize default metadata
        metadata = {
            "title": client_slug,
            "indexName": client_slug,
            "favicon": None
        }
        url = f"https://{client_slug}.com" # Fallback URL
        
        # New counters
        website_docs = 0
        intake_form_docs = 0
        drive_docs = 0

        # 1. Try to extract metadata from the representative markdown file and count docs
        if representative_doc_key:
            try:
                # We need to process ALL objects to count categories correctly
                for obj in objects:
                    key = obj['Key']
                    if not key.endswith('.md'): continue
                    
                    if 'website' in key:
                        website_docs += 1
                    elif 'intake_form' in key or 'intake-form' in key:
                        intake_form_docs += 1
                    elif 'drive' in key or 'client_materials' in key:
                        drive_docs += 1
                
                resp = do_client.s3_client.get_object(Bucket=bucket, Key=representative_doc_key)
                content = resp['Body'].read().decode('utf-8', errors='ignore')
                
                # Parse Frontmatter (simple parsing)
                if content.startswith('---'):
                    end_idx = content.find('---', 3)
                    if end_idx != -1:
                        frontmatter = content[3:end_idx]
                        for line in frontmatter.split('\n'):
                            if ':' in line:
                                k, v = line.split(':', 1)
                                k = k.strip()
                                v = v.strip()
                                if k == 'title': metadata['title'] = v.strip('"\'')
                                if k == 'url': url = v.strip('"\'')
            except Exception as e:
                logger.warning(f"Failed to read representative doc {representative_doc_key}: {e}")

        # 2. Look for a specific icon document (created by create.py)
        icon_key = f"{client_slug}/{client_slug}_icon.md"
        # Check if this key exists in our objects list
        icon_obj = next((o for o in objects if o['Key'] == icon_key), None)
        if icon_obj:
             try:
                resp = do_client.s3_client.get_object(Bucket=bucket, Key=icon_key)
                content = resp['Body'].read().decode('utf-8', errors='ignore')
                for line in content.split('\n'):
                    if 'icon_url:' in line:
                        metadata['favicon'] = line.split('icon_url:', 1)[1].strip()
                        break
             except Exception as e:
                 logger.warning(f"Failed to read icon doc {icon_key}: {e}")

        # Construct the metadata.json content
        metadata_file = {
            "website_url": url,
            "drive_url": "", # Cannot infer drive url easily from backfill
            "client_slug": client_slug,
            "website_docs": website_docs,
            "intake_form_docs": intake_form_docs,
            "drive_docs": drive_docs,
            "createdAt": created_at.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "metadata": metadata
        }

        # Upload metadata.json
        try:
            do_client.upload_file_content(
                json.dumps(metadata_file, indent=2),
                f"{client_slug}/metadata.json",
                content_type="application/json"
            )
            logger.info(f"Successfully generated metadata.json for {client_slug}")
        except Exception as e:
            logger.error(f"Failed to upload metadata.json for {client_slug}: {e}")

if __name__ == "__main__":
    backfill_metadata()

