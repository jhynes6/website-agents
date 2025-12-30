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
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Literal
import sys
import re

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.clients.digital_ocean_client import DigitalOceanClient
from app.clients.do_agent_registry import AgentRegistry
from app.clients.llm import llm_client
from app.config import get_settings
import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test queries with expected intent
TEST_QUERIES = [
    {
        "query": "What can you do for me?",
        "expected_intent": "MORE_INFO",
        "expected_tags": ["services_products", "case_studies", "about", "capabilities_overview", "pitch_decks"]
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
        "query": "Have you worked with any similar companies?",
        "expected_intent": "CASE_STUDY_REQUEST",
        "expected_tags": ["case_studies", "testimonials", "markets_industries", "capabilities_overview", "pitch_decks"]
    },
    {
        "query": "Do also do other services?",
        "expected_intent": "MORE_INFO",
        "expected_tags": [ "services_products", "case_studies",'markets_industries', 'capabilities_overview', "pitch_decks"]
    }
]


class ABTestRunner:
    def __init__(self, client_slug: str, *, retrieval_backend: Literal["auto", "digitalocean", "pinecone"] = "auto"):
        self.client_slug = client_slug
        self.do_client = DigitalOceanClient()
        self.settings = get_settings()
        self.registry = AgentRegistry()
        self.token_cache = self._load_token_cache()
        self.results = []
        self.retrieval_backend = retrieval_backend
        
        # Load triage agent prompt
        triage_prompt_path = Path(__file__).parent.parent / "app" / "clients" / "agent_templates" / "triage_agent.md"
        with open(triage_prompt_path) as f:
            self.triage_system_prompt_template = f.read()
        
        # Load client metadata
        self.client_metadata = self._load_client_metadata()
        
        # Build available content types list
        self.available_content_types = self._get_available_content_types()
        
        # Inject into triage prompt
        content_types_text = "\n".join([f"- {ct}" for ct in self.available_content_types])
        self.triage_system_prompt = self.triage_system_prompt_template.replace(
            "{available_content_types}",
            content_types_text
        )
    
    def _load_client_metadata(self) -> Dict[str, Any]:
        """Load client metadata from Spaces."""
        try:
            s3 = boto3.client(
                's3',
                endpoint_url='https://tor1.digitaloceanspaces.com',
                aws_access_key_id=self.settings.digitalocean_spaces_key,
                aws_secret_access_key=self.settings.digitalocean_spaces_secret,
                region_name='tor1'
            )
            
            key = f'{self.client_slug}/metadata.json'
            response = s3.get_object(Bucket='mintleads-clients-kb', Key=key)
            metadata = json.loads(response['Body'].read().decode('utf-8'))
            
            logger.info(f"✓ Loaded metadata for {self.client_slug}")
            return metadata
        except Exception as e:
            logger.warning(f"Could not load metadata for {self.client_slug}: {e}")
            return {}
    
    def _get_available_content_types(self) -> List[str]:
        """Extract available content types from client metadata."""
        content_types = set()
        
        if 'website_docs' in self.client_metadata:
            by_type = self.client_metadata['website_docs'].get('by_content_type', {})
            content_types.update(by_type.keys())
        
        if 'drive_docs' in self.client_metadata:
            by_type = self.client_metadata['drive_docs'].get('by_content_type', {})
            content_types.update(by_type.keys())
        
        if self.client_metadata.get('intake_form_docs', 0) > 0:
            content_types.add('intake_form')
        
        # Convert to sorted list
        return sorted(list(content_types))


    def _load_token_cache(self) -> Dict[str, Any]:
        """Best-effort load of cached agent endpoints/keys from Spaces."""
        try:
            # digital_ocean_client initializes a Spaces client if creds exist
            s3 = getattr(self.do_client, "s3_client", None)
            if not s3:
                return {}

            obj = s3.get_object(
                Bucket="mintleads-agents-store",
                Key="agent-api-tokens.json",
            )
            content = obj["Body"].read().decode("utf-8")
            data = json.loads(content)
            return data.get("tokens", data) if isinstance(data, dict) else {}
        except Exception as exc:
            logger.warning(f"Could not load token cache: {exc}")
            return {}


    def _lookup_cached_credentials(self, slug: str) -> Optional[Dict[str, Any]]:
        """
        Try several slug variants to find cached endpoint/api_key.
        Handles legacy/inconsistent naming like inbox-manager vs inbox_manager.
        """
        candidates = {slug}
        if slug.startswith("inbox_manager:"):
            client = slug.split(":", 1)[1]
            candidates.add(f"inbox-manager:{client}")
            candidates.add(client)
        elif slug == "inbox_manager":
            candidates.add("inbox_manager:default")
            candidates.add("inbox-manager:default")

        for key in candidates:
            if key in self.token_cache:
                return self.token_cache.get(key)
        return None

        
    async def ensure_agent_ready(self, agent_type: str) -> Optional[Dict]:
        """
        Ensure we have a reachable endpoint and valid API key for the agent.
        If either is missing, try to fetch/regenerate it and update the registry.
        """
        slug = f"{agent_type}:{self.client_slug}"
        agent = self.registry.get(slug)
        
        if not agent:
            logger.warning(f"Agent not found: {slug}")
            return None

        endpoint = agent.endpoint_url
        api_key = agent.api_key
        updated = False

        # Try cached credentials first
        cached = self._lookup_cached_credentials(slug)
        if cached:
            if not endpoint:
                endpoint = cached.get("endpoint")
            if not api_key:
                api_key = cached.get("api_key")

        # Ensure endpoint exists
        if not endpoint:
            endpoint = await self.do_client.get_agent_chat_endpoint(agent.agent_uuid)
            if endpoint:
                updated = True

        # Ensure API key exists
        if not api_key:
            api_key = await self.do_client.create_agent_api_key(agent.agent_uuid)
            if api_key:
                updated = True

        # Persist any refreshed credentials
        if updated:
            self.registry.upsert(
                slug=slug,
                agent_uuid=agent.agent_uuid,
                endpoint_url=endpoint,
                api_key=api_key,
                agent_name=agent.agent_name,
                region=agent.region,
                model=agent.model,
                knowledge_base_uuids=agent.knowledge_base_uuids,
                retrieval_method=agent.retrieval_method,
            )

        return {
            "uuid": agent.agent_uuid,
            "name": agent.agent_name,
            "endpoint": endpoint,
            "api_key": api_key,
            "client_slug": slug,
        }
    
    async def test_single_agent(self, query: str) -> Dict[str, Any]:
        """Test current single-agent approach"""
        agent = await self.ensure_agent_ready("inbox_manager")
        
        if not agent or not agent["endpoint"]:
            return {"error": "Agent not configured"}
        
        start_time = time.time()
        
        try:
            import httpx

            async def _send(api_key: str) -> httpx.Response:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    return await client.post(
                        f"{agent['endpoint']}/api/v1/chat/completions",
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {api_key}"
                        },
                        json={
                            "model": "n/a",
                            "messages": [
                                {"role": "user", "content": query}
                            ]
                        }
                    )

            # Call agent endpoint (retry once on 401 by regenerating key)
            response = await _send(agent.get("api_key", ""))
            if response.status_code == 401:
                new_key = await self.do_client.create_agent_api_key(agent["uuid"])
                if new_key:
                    # Update registry and retry once
                    self.registry.upsert(
                        slug=agent["client_slug"],
                        agent_uuid=agent["uuid"],
                        endpoint_url=agent["endpoint"],
                        api_key=new_key,
                        agent_name=agent.get("name"),
                    )
                    agent["api_key"] = new_key
                    response = await _send(new_key)
            
            latency = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                return {
                    "success": True,
                    "latency": latency,
                    "response": data["choices"][0]["message"]["content"],
                    "usage": data.get("usage", {}),
                    "model": "single-agent",
                    "matched_files": []
                }
            else:
                return {
                    "success": False,
                    "error": f"Status {response.status_code}",
                    "latency": latency,
                    "matched_files": []
                }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "latency": time.time() - start_time,
                "matched_files": []
            }
    
    async def test_hybrid_system(self, query: str) -> Dict[str, Any]:
        """Test hybrid 2-agent approach with client-side filtering"""
        # Step 1: Triage agent (using actual LLM with client metadata)
        triage_start = time.time()
        triage_result = await self._simulate_triage(query)
        triage_latency = time.time() - triage_start
        
        # Step 2: KB Retrieval with client-side YAML filtering
        retrieval_start = time.time()
        filtered_chunks = await self._retrieve_with_filtering(query, triage_result)
        retrieval_latency = time.time() - retrieval_start
        matched_files = self._extract_chunk_files(filtered_chunks)
        
        # Step 3: Enhanced response agent
        agent = await self.ensure_agent_ready("inbox_manager")

        if not agent or not agent["endpoint"]:
            return {"error": "Agent not configured"}
        
        response_start = time.time()
        
        try:
            # Build context from filtered chunks
            context_text = self._build_context_from_chunks(filtered_chunks)
            
            # Build enhanced prompt with triage context and filtered KB chunks
            enhanced_query = f"""[TRIAGE_CONTEXT]
Intent: {triage_result['intent']}
Document Types Retrieved: {', '.join(triage_result.get('suggested_doc_types', [])[:3])}
Confidence: {triage_result.get('confidence', 0.0)}

[KNOWLEDGE BASE CONTEXT]
{context_text}

[USER_QUERY]
{query}"""
            
            import httpx

            async def _send(api_key: str) -> httpx.Response:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    return await client.post(
                        f"{agent['endpoint']}/api/v1/chat/completions",
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {api_key}"
                        },
                        json={
                            "model": "n/a",
                            "messages": [
                                {"role": "user", "content": enhanced_query}
                            ]
                        }
                    )

            response = await _send(agent.get("api_key", ""))
            if response.status_code == 401:
                new_key = await self.do_client.create_agent_api_key(agent["uuid"])
                if new_key:
                    self.registry.upsert(
                        slug=agent["client_slug"],
                        agent_uuid=agent["uuid"],
                        endpoint_url=agent["endpoint"],
                        api_key=new_key,
                        agent_name=agent.get("name"),
                    )
                    agent["api_key"] = new_key
                    response = await _send(new_key)
            
            response_latency = time.time() - response_start
            total_latency = triage_latency + retrieval_latency + response_latency
            
            if response.status_code == 200:
                data = response.json()
                
                return {
                    "success": True,
                    "latency": total_latency,
                    "triage_latency": triage_latency,
                    "retrieval_latency": retrieval_latency,
                    "response_latency": response_latency,
                    "response": data["choices"][0]["message"]["content"],
                    "usage": data.get("usage", {}),
                    "triage_result": triage_result,
                    "chunks_retrieved": len(filtered_chunks),
                    "model": "hybrid-2-agent",
                    "matched_files": matched_files
                }
            else:
                return {
                    "success": False,
                    "error": f"Status {response.status_code}",
                    "latency": total_latency,
                    "triage_latency": triage_latency,
                    "retrieval_latency": retrieval_latency,
                    "response_latency": response_latency,
                    "matched_files": matched_files
                }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "latency": time.time() - triage_start,
                "matched_files": matched_files
            }
    
    async def _retrieve_with_filtering(self, query: str, triage_result: Dict[str, Any]) -> List:
        """
        Retrieve from KB using K=10 and filter by suggested document types.
        """
        suggested_types = triage_result.get("suggested_doc_types", []) or []

        # -----------------------------
        # Helper: Pinecone fallback
        # -----------------------------
        @dataclass(frozen=True)
        class SimpleChunk:
            text_content: str
            metadata: Dict[str, Any]

        async def _retrieve_from_pinecone() -> List[SimpleChunk]:
            from app.clients.pinecone_client import pinecone_kb_client

            # Apply doc-type filtering directly via Pinecone metadata filtering when available
            pc_filter: Optional[Dict[str, Any]] = None
            if suggested_types:
                pc_filter = {"content_type": {"$in": list(suggested_types)}}

            hits = pinecone_kb_client.search(
                client_slug=self.client_slug,
                query=query,
                top_k=10,
                filter=pc_filter,
                fields=["text", "file_key", "content_type", "document_source", "source_bucket", "source_key"],
            )
            out: List[SimpleChunk] = []
            for h in hits[:5]:
                text = str(h.fields.get("text") or "").strip()
                if not text:
                    continue
                file_key = h.fields.get("file_key") or h.fields.get("source_key") or h.record_id
                meta = {
                    "item_name": file_key,
                    "file_key": h.fields.get("file_key"),
                    "content_type": h.fields.get("content_type"),
                    "document_source": h.fields.get("document_source"),
                    "source_bucket": h.fields.get("source_bucket"),
                    "source_key": h.fields.get("source_key"),
                    "score": h.score,
                }
                out.append(SimpleChunk(text_content=text, metadata=meta))
            return out

        # -----------------------------
        # DigitalOcean KB retrieval
        # -----------------------------
        async def _retrieve_from_do_kb() -> List:
            from gradient import Gradient
            from app.clients.do_kb_registry import KnowledgeBaseRegistry
            from app.utils.kb_filters import filter_chunks_by_yaml

            client = Gradient(access_token=self.settings.digitalocean_token)
            kb_registry = KnowledgeBaseRegistry()
            kb = kb_registry.get(self.client_slug)

            if not kb:
                logger.warning(f"No KB found for {self.client_slug}")
                return []

            try:
                response = client.retrieve.documents(
                    knowledge_base_id=kb.kb_uuid,
                    num_results=10,
                    query=query,
                )
            except Exception as e:
                # Most common: 404 knowledge base details not found.
                logger.warning(f"[DO KB] retrieval failed for {self.client_slug} kb_uuid={kb.kb_uuid}: {e}")
                raise

            if not suggested_types:
                return response.results[:5]

            # Filter by suggested doc types (in priority order)
            filtered = []
            seen_chunks = set()

            for doc_type in suggested_types:
                chunks = filter_chunks_by_yaml(response.results, content_type=doc_type)
                for chunk in chunks:
                    chunk_id = chunk.metadata.get("item_name", "")
                    if chunk_id and chunk_id not in seen_chunks:
                        filtered.append(chunk)
                        seen_chunks.add(chunk_id)
                    if len(filtered) >= 5:
                        break
                if len(filtered) >= 5:
                    break

            # If we didn't get enough filtered chunks, add unfiltered ones
            if len(filtered) < 5:
                for chunk in response.results:
                    chunk_id = chunk.metadata.get("item_name", "")
                    if chunk_id and chunk_id not in seen_chunks:
                        if hasattr(chunk, "original_chunk"):
                            filtered.append(chunk)
                        else:
                            from app.utils.kb_filters import FilteredChunk, parse_yaml_frontmatter

                            parent_text = chunk.metadata.get("parent_chunk_text", "")
                            yaml_meta = parse_yaml_frontmatter(parent_text)
                            wrapped = FilteredChunk(
                                original_chunk=chunk,
                                metadata=chunk.metadata,
                                yaml_metadata=yaml_meta,
                                text_content=getattr(chunk, "text_content", ""),
                            )
                            filtered.append(wrapped)
                        seen_chunks.add(chunk_id)
                    if len(filtered) >= 5:
                        break

            return filtered[:5]

        # -----------------------------
        # Backend selection
        # -----------------------------
        backend = self.retrieval_backend
        if backend == "pinecone":
            return await _retrieve_from_pinecone()
        if backend == "digitalocean":
            try:
                return await _retrieve_from_do_kb()
            except Exception:
                return []

        # auto: try DO KB first, then Pinecone fallback
        try:
            return await _retrieve_from_do_kb()
        except Exception:
            pc_chunks = await _retrieve_from_pinecone()
            if pc_chunks:
                logger.info(f"[KB fallback] Using Pinecone retrieval for {self.client_slug} (DO KB not available).")
            return pc_chunks

    def _extract_chunk_files(self, chunks: List) -> List[str]:
        """Return unique file names from retrieved/filtered chunks."""
        files = []
        for chunk in chunks or []:
            meta = getattr(chunk, "metadata", {}) or {}
            name = meta.get("item_name") or meta.get("filename") or meta.get("file_name")
            if name and name not in files:
                files.append(name)
        return files
    
    def _build_context_from_chunks(self, chunks: List) -> str:
        """Build context text from filtered chunks."""
        if not chunks:
            return "(No relevant documents found)"
        
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            # Extract text content
            if hasattr(chunk, 'text_content'):
                text = chunk.text_content
            elif hasattr(chunk, 'original_chunk') and hasattr(chunk.original_chunk, 'text_content'):
                text = chunk.original_chunk.text_content
            else:
                continue
            
            # Truncate if too long
            if len(text) > 500:
                text = text[:500] + "..."
            
            context_parts.append(f"[Document {i}]\n{text}")
        
        return "\n\n".join(context_parts)
    
    async def _simulate_triage(self, query: str) -> Dict[str, Any]:
        """
        Run actual triage using LLM with triage_agent.md prompt
        """
        try:
            response = await llm_client.chat(
                messages=[
                    {"role": "system", "content": self.triage_system_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            # Extract JSON from response
            content = response["choices"][0]["message"]["content"]
            
            # Try to find JSON in the response (in case LLM adds extra text)
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                triage_data = json.loads(json_match.group())
            else:
                triage_data = json.loads(content)
            
            logging.info(f"✓ Triage result: intent={triage_data.get('intent')}, confidence={triage_data.get('confidence')}")
            
            # Add 'urgency' field for backward compatibility with hybrid system
            if 'urgency' not in triage_data:
                # Map intents to urgency
                urgency_map = {
                    "BOOKING_REQUEST": "high",
                    "PRICING": "high",
                    "CASE_STUDY_REQUEST": "medium",
                    "MORE_INFO": "medium",
                    "LONG_FOLLOW_UP": "low",
                    "OTHER": "medium"
                }
                triage_data['urgency'] = urgency_map.get(triage_data.get('intent'), 'medium')
            
            return triage_data
            
        except Exception as e:
            logging.error(f"✗ Triage failed: {e}")
            # Fallback to simple rule-based triage
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
        # Handle both absolute and relative paths
        output_path = Path(output_file)
        if not output_path.is_absolute():
            output_path = Path(__file__).parent / "io" / output_file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
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
        
        # Avoid division by zero
        if summary['single_agent']['avg_latency'] > 0:
            latency_pct = (latency_diff / summary['single_agent']['avg_latency']) * 100
            print(f"  Latency Δ:  {latency_diff:+.2f}s ({latency_pct:+.1f}%)")
        else:
            print(f"  Latency Δ:  {latency_diff:+.2f}s (N/A)")
        
        if summary['single_agent']['total_tokens'] > 0:
            token_pct = (token_diff / summary['single_agent']['total_tokens']) * 100
            print(f"  Token Δ:    {token_diff:+d} ({token_pct:+.1f}%)")
        else:
            print(f"  Token Δ:    {token_diff:+d} (N/A)")
        
        print("="*60 + "\n")


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="A/B test single vs hybrid agent system")
    parser.add_argument("--client", required=True, help="Client slug to test")
    parser.add_argument("--output", default="ab_test_results.json", help="Output file name")
    parser.add_argument(
        "--retrieval-backend",
        default="auto",
        choices=["auto", "digitalocean", "pinecone"],
        help="KB retrieval backend for the hybrid system. auto=try DO KB then fallback to Pinecone.",
    )
    
    args = parser.parse_args()
    
    runner = ABTestRunner(args.client, retrieval_backend=args.retrieval_backend)
    await runner.run_ab_test(args.output)


if __name__ == "__main__":
    asyncio.run(main())

