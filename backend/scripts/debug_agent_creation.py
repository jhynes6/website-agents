import os
import sys
import logging
import json
import httpx

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.clients.digital_ocean_client import do_client
from app.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_agent_creation():
    # Target KB provided by user
    target_kb_uuid = "239d76f2-e314-11f0-b074-4e013e2ddde4"
    # agent_name = "inbox-manager-vew-media"
    
    print(f"--- Debugging Agent Creation for KB {target_kb_uuid} ---")
    
    # 1. Fetch KB Details
    kb = None
    try:
        with httpx.Client() as client:
            resp = client.get(
                f"{do_client.base_url}/knowledge_bases/{target_kb_uuid}",
                headers=do_client.headers,
                timeout=30,
            )
            if resp.status_code == 200:
                kb = resp.json().get("knowledge_base")
                print(f"KB Found: {kb.get('name')}")
                print(f"  Region: {kb.get('region')}")
                print(f"  Project ID: {kb.get('project_id')}")
                print(f"  Status: {kb.get('status')}")
            else:
                print(f"Failed to fetch KB: {resp.status_code} - {resp.text}")
                return
    except Exception as e:
        print(f"Error fetching KB: {e}")
        return

    agent_name = "inbox-manager-" + kb.get("name")

    # 2. Attempt Agent Creation in 'sfo2'
    # We use the KB's project_id to ensure match
    project_id = kb.get("project_id")
    target_region = "tor1"  # Try sfo2
    print(f"\nAttempting to create Agent '{agent_name}' in '{target_region}'...")
    
    payload = {
        # required/essential fields
        "name": agent_name,
        "instruction": "You are a customer support representative that handles inquiries for people that are interested in buying our services. If the potential customer engages in small talk, respond politely without referencing the website. For questions about the services or products we sell or anything else about the business, answer ONLY using the provided context below. Do NOT use any other knowledge. If the context isn't sufficientg, say so expliciity.",
        "knowledge_base_uuid": [target_kb_uuid],
        # Use a DO-managed model that doesn't require a provider key
        # "model_uuid": "9a3644c7-f300-11ef-bf8f-4e013e2ddde4", # 4o-mini
        "model_uuid": "1b07e52b-73c5-11f0-b074-4e013e2ddde4", # GPT-5   
        "open_ai_key_uuid": "65d060eb-0336-40ca-87a3-7074c99da71b",
        # "model_provider_key_uuid": "11f0e2f6-66fa-00d6-b074-4e013e2ddde4", 
        "project_id": project_id,
        "region": target_region,
        # optional fields kept minimal; add more only if needed
        "description": "Debug agent for testing cross-region attachment.",
        "workspace_uuid": "11f0df43-69be-eb71-b074-4e013e2ddde4", 
    }
    # Remove None fields to avoid server-side validation errors
    payload = {k: v for k, v in payload.items() if v}

    try:
        with httpx.Client() as client:
            print(f"Sending payload: {json.dumps(payload, indent=2)}")
            response = client.post(
                f"{do_client.base_url}/agents",
                headers=do_client.headers,
                json=payload,
                timeout=60,
            )

            if response.status_code in [200, 201]:
                agent = response.json().get("agent")
                print(f"\nSUCCESS: Created Agent {agent.get('uuid')}")
                print(f"  Region: {agent.get('region')}")
                print(f"  Attached KBs:{[t['name'] for t in agent['knowledge_bases']]})")

                agent_uuid = agent.get("uuid")

                # Force retrieval settings via update call
                if agent_uuid:
                    update_payload = {
                        "retrieval_method": "RETRIEVAL_METHOD_REWRITE",
                        "provide_citations": True,
                        "k": 10,
                    }
                    try:
                        update_resp = client.put(
                            f"{do_client.base_url}/agents/{agent_uuid}",
                            headers=do_client.headers,
                            json=update_payload,
                            timeout=30,
                        )
                        if update_resp.status_code in [200, 201]:
                            print("\nUpdate call to force retrieval settings succeeded.")
                        else:
                            print(f"\nWARNING: Retrieval update failed: {update_resp.status_code} - {update_resp.text}")
                    except Exception as e:
                        print(f"\nERROR: Could not force retrieval settings: {e}")

                # Verify retrieval settings via a retrieve call
                if agent_uuid:
                    try:
                        verify_resp = client.get(
                            f"{do_client.base_url}/agents/{agent_uuid}",
                            headers=do_client.headers,
                            timeout=30,
                        )
                        if verify_resp.status_code == 200:
                            verified = verify_resp.json().get("agent", {})
                            retrieval_method = verified.get("retrieval_method")
                            provide_citations = verified.get("provide_citations")
                            k_value = verified.get("k")
                            print("\nVerification (retrieval settings):")
                            print(f"  retrieval_method: {retrieval_method}")
                            print(f"  provide_citations: {provide_citations}")
                            print(f"  k: {k_value}")
                        else:
                            print(f"\nWARNING: Retrieval verification failed: {verify_resp.status_code} - {verify_resp.text}")
                    except Exception as e:
                        print(f"\nERROR: Could not verify agent retrieval settings: {e}")
            else:
                print(f"\nFAILURE: {response.status_code}")
                print(f"Response: {response.text}")

    except Exception as e:
        print(f"Error creating agent: {e}")

if __name__ == "__main__":
    debug_agent_creation()

