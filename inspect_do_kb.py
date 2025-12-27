import asyncio
import sys
import json
import logging
from pathlib import Path

# Add project root to sys.path so we can import backend modules
# Assuming script is run from project root
sys.path.append(str(Path.cwd()))

from backend.app.clients.digital_ocean_client import do_client

# Configure logging
logging.basicConfig(level=logging.INFO)

async def inspect_kb(name):
    print(f"Inspecting Knowledge Base: {name}")
    kb = await do_client.get_knowledge_base_by_name(name)
    
    if kb:
        print("\n--- Knowledge Base Details ---")
        print(json.dumps(kb, indent=2))
        
        print("\n--- Data Sources ---")
        sources = await do_client.list_data_sources(kb['uuid'])
        print(json.dumps(sources, indent=2))
    else:
        print(f"KB '{name}' not found.")

    # Also check available models to see why creation might be failing
    print("\n--- Checking Model Availability ---")
    model_uuid = await do_client.get_embedding_model_uuid()
    print(f"Resolved Embedding Model UUID: {model_uuid}")

if __name__ == "__main__":
    asyncio.run(inspect_kb('beistle'))

