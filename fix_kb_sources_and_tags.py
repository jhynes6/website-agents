import asyncio
import sys
import logging
from pathlib import Path

# Add project root to sys.path so we can import backend modules
sys.path.append(str(Path.cwd()))

from backend.app.clients.digital_ocean_client import do_client, httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fix_kbs")

async def update_kb_tags(kb_uuid, tags):
    """Update KB tags (requires separate endpoint if supported, or update endpoint)."""
    # Based on API docs/patterns, usually PUT /v2/gen-ai/knowledge_bases/{uuid}
    # Payload: { "tags": [...] }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{do_client.base_url}/knowledge_bases/{kb_uuid}",
                headers=do_client.headers,
                json={"tags": tags}
            )
            if response.status_code == 200:
                logger.info(f"✅ Tags updated for {kb_uuid}")
                return True
            else:
                logger.error(f"❌ Failed to update tags for {kb_uuid}: {response.text}")
                return False
    except Exception as e:
        logger.error(f"❌ Error updating tags: {e}")
        return False

async def fix_knowledge_bases():
    print("Fetching Knowledge Bases...")
    kbs = await do_client.list_knowledge_bases()
    print(f"Found {len(kbs)} Knowledge Bases.")
    
    bucket = do_client.settings.digitalocean_spaces_bucket
    if not bucket:
        print("❌ Spaces bucket not configured.")
        return

    for kb in kbs:
        name = kb.get('name')
        uuid = kb.get('uuid')
        
        if name == "copywriting":
            print(f"Skipping 'copywriting' ({uuid})")
            continue
            
        print(f"\nProcessing KB: {name} ({uuid})")
        
        # 1. Update Tags
        # Assuming we want to ADD 'client-information' if missing, or just SET it.
        # Let's set it to ["client-information"] to be safe/consistent.
        # current_tags = kb.get('tags', []) # API might return tags in list response?
        # Let's just blindly update to ensure compliance.
        await update_kb_tags(uuid, ["client-information"])
        
        # 2. Fix Data Sources
        # We want ONLY the source {bucket}/{name}/
        expected_prefix = f"{name}/"
        
        logger.info(f"Ensuring source: {bucket}/{expected_prefix}")
        
        # List current sources
        sources = await do_client.list_data_sources(uuid)
        
        correct_source_exists = False
        
        for s in sources:
            s_details = s.get("spaces_data_source", {})
            s_bucket = s_details.get("bucket_name")
            s_prefix = s_details.get("item_path") or s_details.get("prefix", "")
            s_uuid = s.get("uuid")
            
            # Check if this IS the correct source
            if s_bucket == bucket and s_prefix.rstrip('/') == expected_prefix.rstrip('/'):
                correct_source_exists = True
                logger.info(f"✅ Correct source already exists: {s_prefix}")
            else:
                # INCORRECT SOURCE -> DELETE
                # Especially if it's the root path "" or "/"
                logger.warning(f"⚠️ Found incorrect/extra source: bucket={s_bucket}, prefix='{s_prefix}'. DELETING.")
                deleted = await do_client.delete_data_source(uuid, s_uuid)
                if deleted:
                    logger.info("🗑️ Deleted incorrect source.")
                else:
                    logger.error("❌ Failed to delete incorrect source.")
        
        # If correct source was missing, add it
        if not correct_source_exists:
            logger.info(f"➕ Adding correct source: {expected_prefix}")
            added = await do_client.add_spaces_source(uuid, bucket, expected_prefix)
            if added:
                logger.info("✅ Added correct source.")
            else:
                logger.error("❌ Failed to add correct source.")

if __name__ == "__main__":
    asyncio.run(fix_knowledge_bases())

