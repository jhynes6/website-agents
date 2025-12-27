import asyncio
import os
import sys
import logging
import json

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.clients.digital_ocean_client import do_client
from app.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_kb_then_add_source():
    """
    Debug helper:
      1) Try to create a KB without data sources (will fail if API requires them)
      2) On failure, create KB with the data source
      3) Add a Spaces data source with chunking options (redundant if step 2 succeeds)
    """
    settings = get_settings()

    # Inputs for this test run
    target_name = "push-analytics-nyc"
    bucket = "mintleads-clients-kb"
    prefix = "push-analytics-nyc/"

    if not settings.digitalocean_token:
        print("DIGITALOCEAN_TOKEN not configured.")
        return

    # Step 1: Create KB without data sources
    print(f"Creating KB '{target_name}' with NO data sources...")
    kb = await do_client.create_knowledge_base(name=target_name, data_sources=None)
    if not kb:
        print("\nInitial creation failed (expected if API requires datasources). Retrying with data source included...")
        data_sources = [
            {
                "spaces_data_source": {
                    "bucket_name": bucket,
                    "region": settings.digitalocean_spaces_region,
                    "item_path": prefix,
                }
            }
        ]
        kb = await do_client.create_knowledge_base(name=target_name, data_sources=data_sources)
        if not kb:
            print("\nFAILURE: KB creation with data source also failed.")
            return

    kb_uuid = kb.get("uuid")
    print("\nKB created (or retrieved):")
    print(json.dumps(kb, indent=2))

    # Ensure advanced chunking flag is on (if feature is enabled)
    print(f"\nAdvanced chunking flag: {settings.digitalocean_enable_advanced_chunking}")
    if not settings.digitalocean_enable_advanced_chunking:
        print("WARNING: Advanced chunking flag is false; enable DIGITAL_OCEAN_ENABLE_ADVANCED_CHUNKING=true to include chunking fields.")

    # Step 2: Add data source with chunking via add_spaces_source
    print(f"\nAdding data source: bucket={bucket}, prefix={prefix}")
    ok = await do_client.add_spaces_source(kb_uuid, bucket, prefix)
    if ok:
        print("\nSUCCESS: Data source added (chunking applied if enabled).")
    else:
        print("\nFAILURE: add_spaces_source returned False")


if __name__ == "__main__":
    asyncio.run(create_kb_then_add_source())

