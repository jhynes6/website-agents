"""
Script to add document_source='website' to ALL documents across ALL indexes.
Scans common index names and updates all documents found.
"""
import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import httpx
from app.logging import logger


SEARCH_URL = "https://assuring-stingray-92074-gcp-usc1-search.upstash.io"
SEARCH_TOKEN = "ACAFMGFzc3VyaW5nLXN0aW5ncmF5LTkyMDc0LWdjcC11c2MxYWRtaW5ZVGt5WXpCbU5qY3RNamRtT0MwME1XTTBMV0k1T1RrdFpUY3pNR05pTWpjM01qZzM="

# Common index names to scan
INDEX_NAMES = ["firestarter", "mintleads", "ml", "default"]


async def process_index(client: httpx.AsyncClient, index_name: str):
    """Process all documents in a single index."""
    headers = {
        "Authorization": f"Bearer {SEARCH_TOKEN}",
        "Content-Type": "application/json",
    }
    
    # Fetch all documents using range API
    all_docs = []
    cursor = "0"
    
    logger.info(f"\n📂 Scanning index: '{index_name}'")
    
    while True:
        range_url = f"{SEARCH_URL}/range/{index_name}"
        params = {"cursor": cursor, "limit": 100}
        
        response = await client.get(range_url, headers=headers, params=params)
        
        if response.status_code == 404:
            logger.info(f"  ℹ️  Index '{index_name}' doesn't exist - skipping")
            return 0
        
        if response.status_code != 200:
            logger.error(f"  ❌ Range failed: {response.status_code} - {response.text}")
            return 0
        
        data = response.json()
        result = data.get("result", {})
        documents = result.get("vectors", [])  # Upstash Search uses "vectors" not "documents"
        all_docs.extend(documents)
        
        next_cursor = result.get("nextCursor", "")
        
        if not next_cursor or next_cursor == "0" or not documents:
            break
        
        cursor = next_cursor
    
    if not all_docs:
        logger.info(f"  ℹ️  No documents in index '{index_name}'")
        return 0
    
    logger.info(f"  ✓ Found {len(all_docs)} documents")
    
    # Filter documents needing update
    to_update = []
    for doc in all_docs:
        metadata = doc.get("metadata", {})
        
        # Skip if already has document_source
        if "document_source" in metadata:
            continue
        
        # Add document_source
        metadata["document_source"] = "website"
        
        to_update.append({
            "id": doc.get("id"),
            "data": doc.get("data", {}),
            "metadata": metadata
        })
    
    if not to_update:
        logger.info(f"  ✓ All documents already have document_source")
        return 0
    
    # Update in batches of 50
    batch_size = 50
    updated_count = 0
    
    for i in range(0, len(to_update), batch_size):
        batch = to_update[i:i+batch_size]
        
        upsert_url = f"{SEARCH_URL}/upsert/{index_name}"
        response = await client.post(upsert_url, headers=headers, json=batch)
        
        if response.status_code != 200:
            logger.error(f"  ❌ Batch upsert failed: {response.status_code} - {response.text}")
            continue
        
        updated_count += len(batch)
        logger.info(f"  ✓ Updated batch {i//batch_size + 1} ({len(batch)} docs)")
    
    logger.info(f"  ✅ Total updated in '{index_name}': {updated_count}")
    return updated_count


async def main():
    logger.info("\n" + "="*70)
    logger.info("🚀 document_source Migration Tool")
    logger.info(f"🎯 Target: {SEARCH_URL}")
    logger.info("="*70)
    
    total_updated = 0
    
    async with httpx.AsyncClient(timeout=60) as client:
        for index_name in INDEX_NAMES:
            count = await process_index(client, index_name)
            total_updated += count
    
    logger.info(f"\n" + "="*70)
    logger.info(f"🎉 Migration Complete!")
    logger.info(f"📊 Total documents updated across all indexes: {total_updated}")
    logger.info("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
