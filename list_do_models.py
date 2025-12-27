import asyncio
import sys
import os
import logging
from pathlib import Path

# Add project root to sys.path so we can import backend modules
# Assuming script is run from project root
sys.path.append(str(Path.cwd()))

from backend.app.clients.digital_ocean_client import do_client
import httpx

# Configure logging to show info
logging.basicConfig(level=logging.INFO)

async def list_models():
    print("Fetching models from Digital Ocean...")
    async with httpx.AsyncClient() as client:
        try:
            # Manually call the endpoint to see everything
            response = await client.get(
                f"{do_client.base_url}/models",
                headers=do_client.headers,
            )
            response.raise_for_status()
            data = response.json()
            models = data.get("models", [])
            
            print(f"\nFound {len(models)} models:")
            print("-" * 50)
            for m in models:
                name = m.get('name')
                uuid = m.get('uuid')
                usecases = m.get('usecases', [])
                print(f"Name: {name}")
                print(f"UUID: {uuid}")
                print(f"Use cases: {usecases}")
                print("-" * 50)
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(list_models())

