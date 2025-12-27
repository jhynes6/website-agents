import asyncio
import sys
import json
import logging
from pathlib import Path

# Add project root to sys.path so we can import backend modules
sys.path.append(str(Path.cwd()))

from backend.app.clients.digital_ocean_client import do_client

# Configure logging
logging.basicConfig(level=logging.INFO)

async def test_list_kbs():
    print("Testing list_knowledge_bases with pagination...")
    try:
        kbs = await do_client.list_knowledge_bases()
        print(f"\nSuccess! Found {len(kbs)} Knowledge Bases.")
        print("-" * 50)
        
        # Sort for readability
        names = sorted([kb.get('name') for kb in kbs])
        
        # Print names in columns or list
        for i, name in enumerate(names, 1):
            print(f"{i}. {name}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_list_kbs())

