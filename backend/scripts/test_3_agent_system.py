#!/usr/bin/env python3
"""
Test the 3-Agent Reply System using Pinecone Assistants

This script demonstrates the complete pipeline:
1. Draft Agent - Creates initial reply
2. QA Agent - Quality checks for accuracy
3. Finalize Agent - Polishes for tone and style
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

import httpx
import json


async def test_3_agent_pipeline(client_slug: str = "a-perfect-promotion"):
    """Test the complete 3-agent system."""
    backend_url = "http://localhost:8000/api/mintagent"
    
    print(f"🤖 Testing 3-Agent Reply System")
    print(f"Client: {client_slug}")
    print("=" * 80)
    
    # Test message
    test_message = {
        "clientSlug": client_slug,
        "messages": [
            {
                "role": "user",
                "content": "I'm interested in promotional products for our upcoming trade show. Can you help me with custom branded items? What's your process?"
            }
        ]
    }
    
    # ===================================================================
    # Stage 1: Draft
    # ===================================================================
    print("\n1️⃣  STAGE 1: DRAFT AGENT")
    print("-" * 80)
    print("Generating initial reply...")
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{backend_url}/assistant-chat/draft",
                json=test_message,
                timeout=60
            )
            
            if resp.status_code != 200:
                print(f"❌ Draft failed: {resp.status_code} - {resp.text}")
                return False
            
            draft_result = resp.json()
            draft_text = draft_result.get("draft", "")
            citations = draft_result.get("citations", [])
            
            print(f"✅ Draft generated ({len(draft_text)} chars)")
            print(f"📚 Citations: {len(citations)}")
            print(f"\n📝 Draft:\n{draft_text[:500]}...")
            print(f"\nUsage: {draft_result.get('usage', {})}")
    except Exception as e:
        print(f"❌ Draft stage failed: {e}")
        return False
    
    # ===================================================================
    # Stage 2: QA
    # ===================================================================
    print("\n\n2️⃣  STAGE 2: QA AGENT")
    print("-" * 80)
    print("Quality checking draft for accuracy...")
    
    try:
        qa_payload = {
            "clientSlug": client_slug,
            "draft": draft_text,
            "originalMessage": test_message["messages"][0]["content"]
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{backend_url}/assistant-chat/qa",
                json=qa_payload,
                timeout=60
            )
            
            if resp.status_code != 200:
                print(f"❌ QA failed: {resp.status_code} - {resp.text}")
                return False
            
            qa_result = resp.json()
            is_accurate = qa_result.get("is_accurate", False)
            confidence = qa_result.get("confidence", 0)
            suggestions = qa_result.get("suggestions", [])
            qa_data = qa_result.get("qa_result", {})
            
            print(f"✅ QA complete")
            print(f"📊 Accuracy: {'✓ PASS' if is_accurate else '✗ FAIL'}")
            print(f"📊 Confidence: {confidence:.1%}")
            
            if qa_data.get("inaccuracies"):
                print(f"⚠️  Inaccuracies found: {len(qa_data['inaccuracies'])}")
                for i, inaccuracy in enumerate(qa_data["inaccuracies"][:3], 1):
                    print(f"   {i}. {inaccuracy}")
            
            if qa_data.get("missing_info"):
                print(f"ℹ️  Missing info: {len(qa_data['missing_info'])}")
                for i, missing in enumerate(qa_data["missing_info"][:3], 1):
                    print(f"   {i}. {missing}")
            
            if suggestions:
                print(f"💡 Suggestions: {len(suggestions)}")
                for i, suggestion in enumerate(suggestions[:3], 1):
                    print(f"   {i}. {suggestion}")
            
            print(f"\n📋 Overall: {qa_data.get('overall_assessment', 'N/A')}")
    except Exception as e:
        print(f"❌ QA stage failed: {e}")
        # Continue to finalize even if QA fails
        pass
    
    # ===================================================================
    # Stage 3: Finalize
    # ===================================================================
    print("\n\n3️⃣  STAGE 3: FINALIZE AGENT")
    print("-" * 80)
    print("Polishing reply for tone and style...")
    
    try:
        finalize_payload = {
            "clientSlug": client_slug,
            "draft": draft_text,
            "qaFeedback": qa_result.get("qa_result"),
            "tone": "professional"
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{backend_url}/assistant-chat/finalize",
                json=finalize_payload,
                timeout=60
            )
            
            if resp.status_code != 200:
                print(f"❌ Finalize failed: {resp.status_code} - {resp.text}")
                return False
            
            finalize_result = resp.json()
            final_reply = finalize_result.get("finalReply", "")
            changes = finalize_result.get("changes", [])
            reasoning = finalize_result.get("reasoning", "")
            
            print(f"✅ Finalization complete")
            print(f"✏️  Changes made: {len(changes)}")
            
            if changes:
                print(f"\n📝 Changes:")
                for i, change in enumerate(changes[:5], 1):
                    print(f"   {i}. {change}")
            
            print(f"\n💭 Reasoning: {reasoning}")
            print(f"\n📧 Final Reply:\n{final_reply[:500]}...")
            
    except Exception as e:
        print(f"❌ Finalize stage failed: {e}")
        return False
    
    # ===================================================================
    # Summary
    # ===================================================================
    print("\n\n" + "=" * 80)
    print("✅ 3-AGENT PIPELINE COMPLETE")
    print("=" * 80)
    print(f"\n📊 Pipeline Summary:")
    print(f"   1. Draft:    ✓ Generated ({len(draft_text)} chars)")
    print(f"   2. QA:       ✓ Checked (accuracy: {confidence:.1%})")
    print(f"   3. Finalize: ✓ Polished ({len(changes)} changes)")
    print(f"\n🎯 Final reply ready for sending!")
    
    return True


async def test_full_pipeline_endpoint(client_slug: str = "a-perfect-promotion"):
    """Test the orchestrated full pipeline endpoint."""
    backend_url = "http://localhost:8000/api/mintagent"
    
    print(f"\n\n🚀 Testing Full Pipeline Endpoint (Orchestrated)")
    print("=" * 80)
    
    payload = {
        "clientSlug": client_slug,
        "messages": [
            {
                "role": "user",
                "content": "What services do you offer and how much do they cost?"
            }
        ],
        "tone": "professional"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{backend_url}/assistant-chat/full-pipeline",
                json=payload,
                timeout=120
            )
            
            if resp.status_code != 200:
                print(f"❌ Pipeline failed: {resp.status_code} - {resp.text}")
                return False
            
            result = resp.json()
            
            print(f"✅ Pipeline complete")
            print(f"\n📋 Pipeline Trace:")
            for stage in result.get("pipeline_trace", []):
                status_icon = "✓" if stage["status"] == "success" else "✗"
                print(f"   {status_icon} {stage['stage']}: {stage['status']}")
            
            final_reply = result.get("final", {}).get("finalReply", "")
            print(f"\n📧 Final Reply:\n{final_reply[:300]}...")
            
            return True
    except Exception as e:
        print(f"❌ Full pipeline test failed: {e}")
        return False


async def main():
    """Run all tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the 3-agent reply system")
    parser.add_argument("--client", default="a-perfect-promotion", help="Client slug to test")
    parser.add_argument("--orchestrated", action="store_true", help="Test orchestrated endpoint only")
    
    args = parser.parse_args()
    
    if args.orchestrated:
        success = await test_full_pipeline_endpoint(args.client)
    else:
        # Test individual stages first
        success = await test_3_agent_pipeline(args.client)
        
        # Then test orchestrated endpoint
        if success:
            await test_full_pipeline_endpoint(args.client)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

