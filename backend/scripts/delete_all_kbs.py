import asyncio
import os
import sys
import logging
import httpx

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.clients.digital_ocean_client import do_client
from app.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def delete_all_kbs():
    settings = get_settings()
    if not settings.digitalocean_token:
        print("DIGITALOCEAN_TOKEN not configured. Aborting.")
        return

    async with httpx.AsyncClient() as client:
        # List KBs
        kbs = await do_client.list_knowledge_bases()
        print(f"Found {len(kbs)} knowledge bases.")

        for kb in kbs:
            kb_uuid = kb.get("uuid")
            kb_name = kb.get("name")
            if not kb_uuid:
                continue
            print(f"Deleting KB: {kb_name} ({kb_uuid}) ...")
            try:
                resp = await client.delete(
                    f"{do_client.base_url}/knowledge_bases/{kb_uuid}",
                    headers=do_client.headers,
                )
                if resp.status_code in (200, 204):
                    print(f"  Deleted.")
                else:
                    print(f"  Failed: {resp.status_code} - {resp.text}")
            except Exception as e:
                print(f"  Error deleting {kb_uuid}: {e}")


if __name__ == "__main__":
    asyncio.run(delete_all_kbs())

