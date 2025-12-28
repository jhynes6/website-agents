"""
A/B Testing: Single Agent vs Hybrid 2-Agent System

Compares:
- Control: Current single inbox-manager agent
- Variant: Triage agent + enhanced inbox-manager-v2

Metrics:
- Response time (latency)
- Token usage (cost)
- Response quality (human eval + auto metrics)
- Retrieval accuracy
"""

import asyncio
import json
import time
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.clients.digital_ocean_client import DigitalOceanClient
from app.clients.do_agent_registry import AgentRegistry
from app.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test queries with expected intent
TEST_QUERIES = [
    {
        "query": "What does your company do?",
        "expected_intent": "MORE_INFO",
        "expected_tags": ["about", "services_products"]
    },
    {
        "query": "Do you have any case studies or success stories?",
        "expected_intent": "CASE_STUDY_REQUEST",
        "expected_tags": ["case_studies", "testimonials"]
    },
    {
        "query": "How much does this cost?",
        "expected_intent": "PRICING",
        "expected_tags": ["pricing", "services_products"]
    },
    {
        "query": "Can we schedule a call to discuss this?",
        "expected_intent": "BOOKING_REQUEST",
        "expected_tags": ["about", "contact"]
    },
    {
        "query": "What industries have you worked with?",
        "expected_intent": "MORE_INFO",
        "expected_tags": ["industry_markets", "case_studies"]
    },
    {
        "query": "Can you follow up with me in 2 months?",
        "expected_intent": "LONG_FOLLOW_UP",
        "expected_tags": []
    },
    {
        "query": "Tell me about your services and what makes you different",
        "expected_intent": "MORE_INFO",
        "expected_tags": ["services_products", "about"]
    },
    {
        "query": "Show me examples of your work",
        "expected_intent": "CASE_STUDY_REQUEST",
        "expected_tags": ["case_studies", "portfolio"]
    }
]


class ABTestRunner:
    def __init__(self, client_slug: str):
        self.client_slug = client_slug
        self.do_client = DigitalOceanClient()
        self.settings = get_settings()
        self.registry = AgentRegistry()
        self.results = []
        
    async def get_agent_details(self, agent_type: str) -> Optional[Dict]:
        """Get agent UUID and endpoint for testing"""
        slug = f"{agent_type}:{self.client_slug}"
        agent = self.registry.get(slug)
        
        if not agent:
            logger.warning(f"Agent not found: {slug}")
            return None
            
        return {
            "uuid": agent.agent_uuid,
            "name": agent.agent_name,
            "endpoint": agent.endpoint_url,
            "api_key": agent.api_key
        }
    
    async def test_single_agent(self, query: str) -> Dict[str, Any]:
        """Test current single-agent approach"""
        agent = await self.get_agent_details("inbox_manager")
        
        if not agent or not agent["endpoint"]:
            return {"error": "Agent not configured"}
        
        start_time = time.time()
        
        try:
            # Call agent endpoint
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{agent['endpoint']}/api/v1/chat/completions",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {agent.get('api_key', 'test')}"
                    },
                    json={
                        "model": "n/a",
                        "messages": [
                            {"role": "user", "content": query}
                        ]
                    }
                )
                
                latency = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    
                    return {
                        "success": True,
                        "latency": latency,
                        "response": data["choices"][0]["message"]["content"],
                        "usage": data.get("usage", {}),
                        "model": "single-agent"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Status {response.status_code}",
                        "latency": latency
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "latency": time.time() - start_time
            }
    
    async def test_hybrid_system(self, query: str) -> Dict[str, Any]:
        """Test hybrid 2-agent approach"""
        # Step 1: Triage agent (would be a separate fast agent)
        triage_start = time.time()
        
        # For now, simulate triage with simple heuristics
        # TODO: Create actual triage agent
        triage_result = self._simulate_triage(query)
        triage_latency = time.time() - triage_start
        
        # Step 2: Enhanced response agent
        agent = await self.get_agent_details("inbox_manager")
        
        if not agent or not agent["endpoint"]:
            return {"error": "Agent not configured"}
        
        response_start = time.time()
        
        try:
            # Build enhanced prompt with triage context
            enhanced_query = f"""[TRIAGE_CONTEXT]
Intent: {triage_result['intent']}
Urgency: {triage_result['urgency']}
Focus Areas: {', '.join(triage_result['kb_tags'])}

[USER_QUERY]
{query}"""
            
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{agent['endpoint']}/api/v1/chat/completions",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {agent.get('api_key', 'test')}"
                    },
                    json={
                        "model": "n/a",
                        "messages": [
                            {"role": "user", "content": enhanced_query}
                        ]
                    }
                )
                
                response_latency = time.time() - response_start
                total_latency = triage_latency + response_latency
                
                if response.status_code == 200:
                    data = response.json()
                    
                    return {
                        "success": True,
                        "latency": total_latency,
                        "triage_latency": triage_latency,
                        "response_latency": response_latency,
                        "response": data["choices"][0]["message"]["content"],
                        "usage": data.get("usage", {}),
                        "triage_result": triage_result,
                        "model": "hybrid-2-agent"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Status {response.status_code}",
                        "latency": total_latency
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "latency": time.time() - response_start + triage_latency
            }
    
    def _simulate_triage(self, query: str) -> Dict[str, Any]:
        """Simulate triage agent (placeholder for actual triage)"""
        query_lower = query.lower()
        
        # Simple rule-based triage
        if any(word in query_lower for word in ["case study", "case studies", "success", "results", "examples", "work"]):
            return {
                "intent": "CASE_STUDY_REQUEST",
                "urgency": "medium",
                "kb_tags": ["case_studies", "testimonials"],
                "confidence": 0.8
            }
        elif any(word in query_lower for word in ["cost", "price", "pricing", "how much", "budget"]):
            return {
                "intent": "PRICING",
                "urgency": "high",
                "kb_tags": ["pricing", "services_products"],
                "confidence": 0.9
            }
        elif any(word in query_lower for word in ["schedule", "call", "meeting", "book", "demo"]):
            return {
                "intent": "BOOKING_REQUEST",
                "urgency": "high",
                "kb_tags": ["about", "contact"],
                "confidence": 0.95
            }
        elif any(word in query_lower for word in ["follow up", "later", "months", "weeks"]):
            return {
                "intent": "LONG_FOLLOW_UP",
                "urgency": "low",
                "kb_tags": [],
                "confidence": 0.85
            }
        else:
            return {
                "intent": "MORE_INFO",
                "urgency": "medium",
                "kb_tags": ["about", "services_products"],
                "confidence": 0.7
            }
    
    async def run_ab_test(self, output_file: str = "ab_test_results.json"):
        """Run complete A/B test"""
        logger.info(f"Starting A/B test for client: {self.client_slug}")
        logger.info(f"Testing {len(TEST_QUERIES)} queries")
        
        results = []
        
        for i, test_case in enumerate(TEST_QUERIES, 1):
            query = test_case["query"]
            logger.info(f"\n[{i}/{len(TEST_QUERIES)}] Testing: {query[:50]}...")
            
            # Test single agent
            logger.info("  → Testing single agent...")
            single_result = await self.test_single_agent(query)
            
            # Wait a bit to avoid rate limiting
            await asyncio.sleep(1)
            
            # Test hybrid system
            logger.info("  → Testing hybrid system...")
            hybrid_result = await self.test_hybrid_system(query)
            
            # Compare results
            comparison = {
                "query": query,
                "expected_intent": test_case["expected_intent"],
                "expected_tags": test_case["expected_tags"],
                "single_agent": single_result,
                "hybrid_system": hybrid_result,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            results.append(comparison)
            
            # Log summary
            if single_result.get("success") and hybrid_result.get("success"):
                logger.info(f"  ✓ Single agent: {single_result['latency']:.2f}s")
                logger.info(f"  ✓ Hybrid system: {hybrid_result['latency']:.2f}s")
                logger.info(f"    (triage: {hybrid_result.get('triage_latency', 0):.2f}s, response: {hybrid_result.get('response_latency', 0):.2f}s)")
            
            # Wait between queries
            await asyncio.sleep(2)
        
        # Save results
        output_path = Path(__file__).parent / "io" / output_file
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump({
                "client_slug": self.client_slug,
                "test_date": datetime.now(timezone.utc).isoformat(),
                "total_queries": len(TEST_QUERIES),
                "results": results,
                "summary": self._generate_summary(results)
            }, f, indent=2)
        
        logger.info(f"\n✓ Results saved to: {output_path}")
        self._print_summary(results)
        
        return results
    
    def _generate_summary(self, results: List[Dict]) -> Dict[str, Any]:
        """Generate summary statistics"""
        single_successes = [r for r in results if r["single_agent"].get("success")]
        hybrid_successes = [r for r in results if r["hybrid_system"].get("success")]
        
        return {
            "single_agent": {
                "success_rate": len(single_successes) / len(results),
                "avg_latency": sum(r["single_agent"]["latency"] for r in single_successes) / len(single_successes) if single_successes else 0,
                "total_tokens": sum(r["single_agent"].get("usage", {}).get("total_tokens", 0) for r in single_successes)
            },
            "hybrid_system": {
                "success_rate": len(hybrid_successes) / len(results),
                "avg_latency": sum(r["hybrid_system"]["latency"] for r in hybrid_successes) / len(hybrid_successes) if hybrid_successes else 0,
                "avg_triage_latency": sum(r["hybrid_system"].get("triage_latency", 0) for r in hybrid_successes) / len(hybrid_successes) if hybrid_successes else 0,
                "avg_response_latency": sum(r["hybrid_system"].get("response_latency", 0) for r in hybrid_successes) / len(hybrid_successes) if hybrid_successes else 0,
                "total_tokens": sum(r["hybrid_system"].get("usage", {}).get("total_tokens", 0) for r in hybrid_successes)
            }
        }
    
    def _print_summary(self, results: List[Dict]):
        """Print summary to console"""
        summary = self._generate_summary(results)
        
        print("\n" + "="*60)
        print("A/B TEST SUMMARY")
        print("="*60)
        
        print("\nSINGLE AGENT (Control):")
        print(f"  Success Rate: {summary['single_agent']['success_rate']:.1%}")
        print(f"  Avg Latency:  {summary['single_agent']['avg_latency']:.2f}s")
        print(f"  Total Tokens: {summary['single_agent']['total_tokens']}")
        
        print("\nHYBRID SYSTEM (Variant):")
        print(f"  Success Rate: {summary['hybrid_system']['success_rate']:.1%}")
        print(f"  Avg Latency:  {summary['hybrid_system']['avg_latency']:.2f}s")
        print(f"    - Triage:   {summary['hybrid_system']['avg_triage_latency']:.2f}s")
        print(f"    - Response: {summary['hybrid_system']['avg_response_latency']:.2f}s")
        print(f"  Total Tokens: {summary['hybrid_system']['total_tokens']}")
        
        print("\nCOMPARISON:")
        latency_diff = summary['hybrid_system']['avg_latency'] - summary['single_agent']['avg_latency']
        token_diff = summary['hybrid_system']['total_tokens'] - summary['single_agent']['total_tokens']
        
        print(f"  Latency Δ:  {latency_diff:+.2f}s ({latency_diff/summary['single_agent']['avg_latency']*100:+.1f}%)")
        print(f"  Token Δ:    {token_diff:+d} ({token_diff/summary['single_agent']['total_tokens']*100:+.1f}%)")
        
        print("="*60 + "\n")


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="A/B test single vs hybrid agent system")
    parser.add_argument("--client", required=True, help="Client slug to test")
    parser.add_argument("--output", default="ab_test_results.json", help="Output file name")
    
    args = parser.parse_args()
    
    runner = ABTestRunner(args.client)
    await runner.run_ab_test(args.output)


if __name__ == "__main__":
    asyncio.run(main())

