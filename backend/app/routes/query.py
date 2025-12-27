import json
import os
from typing import Any, Dict, List, Optional
import httpx
from openai import AsyncOpenAI

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from ..clients.digital_ocean_client import do_client
from ..config import get_settings
from ..logging import log

router = APIRouter()


@router.post("/query")
async def query(payload: Dict[str, Any]) -> StreamingResponse:
    settings = get_settings()

    query_text: Optional[str] = payload.get("query")
    client_slug: Optional[str] = payload.get("clientSlug") or payload.get("namespace")
    index_name: Optional[str] = payload.get("index")
    stream: bool = bool(payload.get("stream", False))

    # Support chat-style payloads
    if not query_text:
        messages = payload.get("messages")
        if isinstance(messages, list):
            user_messages = [m for m in messages if isinstance(m, dict) and m.get("role") == "user"]
            if user_messages:
                query_text = user_messages[-1].get("content")

    # Use client_slug as the KB name
    kb_name = client_slug or index_name
    if not query_text or not kb_name:
        raise HTTPException(status_code=400, detail="Query and clientSlug/index are required")

    log("query.start", {"client_slug": kb_name, "query_len": len(query_text)})

    # 1. Resolve Knowledge Base
    kb = await do_client.get_knowledge_base_by_name(kb_name)
    if not kb:
        answer = "I don't have any indexed content for this website (Knowledge Base not found)."
        return StreamingResponse(iter([answer]), media_type="text/plain")
    
    kb_uuid = kb["uuid"]
    # Agent Name: inbox-manager-{client_slug}
    agent_name = f"inbox-manager-{kb_name}"

    # 2. Resolve or Create Agent
    # We check if an agent with this name exists
    agent = None
    agents = await do_client.list_agents()
    for a in agents:
        if a.get("name") == agent_name:
            agent = a
            break
            
    if not agent:
        log("query.agent_create", {"name": agent_name})
        agent = await do_client.create_agent(agent_name, [kb_uuid])
        if not agent:
            raise HTTPException(status_code=500, detail="Failed to create agent for this chatbot")

    agent_uuid = agent["uuid"]
    
    # 3. Get Agent Endpoint & Key
    # Ideally, we should cache these
    agent_endpoint = await do_client.get_agent_chat_endpoint(agent_uuid)
    if not agent_endpoint:
        raise HTTPException(status_code=500, detail="Failed to retrieve agent endpoint")
        
    # We need a key to talk to the agent.
    # We'll create a transient key or reuse one if we had a store.
    # For now, create one.
    agent_key = await do_client.create_agent_api_key(agent_uuid)
    if not agent_key:
         raise HTTPException(status_code=500, detail="Failed to create agent API key")

    # 4. Chat with Agent
    try:
        # The DO Agent endpoint is OpenAI compatible
        client = AsyncOpenAI(
            base_url=f"{agent_endpoint}/api/v1",
            api_key=agent_key
        )
        
        log("query.chat_start", {"agent_uuid": agent_uuid})
        
        # We only pass the user query for now, handling history is an improvement for later
        messages = [{"role": "user", "content": query_text}]

        if stream:
            async def streamer():
                # We can't easily get "sources" upfront from DO Agent streaming response usually,
                # unless we parse the chunks carefully or if they send it at start/end.
                # DO Agent usually sends citations in the final chunk or metadata.
                # For now, we'll just stream the text.
                # To simulate the "sources" format the frontend expects:
                # yield f"8:{json.dumps({'sources': []})}\n" 
                
                # Actually, let's try to get sources if possible.
                # If not, we send empty sources to satisfy frontend.
                yield f"8:{json.dumps({'sources': []})}\n"
                
                try:
                    stream_resp = await client.chat.completions.create(
                        model="n/a", # Model is defined in Agent
                        messages=messages,
                        stream=True,
                        extra_body={"include_retrieval_info": True} 
                    )
                    
                    async for chunk in stream_resp:
                        if chunk.choices and chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            yield f"0:{json.dumps(content)}\n"
                            
                        # Check for retrieval info in chunks if available (provider specific)
                        # Usually it's in the final chunk or a specific tool call chunk.
                        
                except Exception as e:
                     log("query.stream.error", {"error": str(e)})
                     yield '0:"[error generating response]"\n'

            return StreamingResponse(streamer(), media_type="text/plain; charset=utf-8")

        else:
            # Non-streaming
            resp = await client.chat.completions.create(
                model="n/a",
                messages=messages,
                stream=False,
                extra_body={"include_retrieval_info": True}
            )
            
            answer = resp.choices[0].message.content
            
            # Extract citations if available
            # DO response usually has a 'retrieval' dict in the raw response dict
            sources = []
            try:
                raw_resp = resp.to_dict()
                retrieval = raw_resp.get("retrieval", {}).get("retrieved_data", [])
                for item in retrieval:
                    sources.append({
                        "title": item.get("metadata", {}).get("title") or item.get("filename") or "Source",
                        "url": item.get("metadata", {}).get("url") or item.get("filename") or "",
                        "snippet": item.get("page_content", "")[:200] + "..."
                    })
            except Exception as e:
                log("query.citations.error", {"error": str(e)})

            payload = {"answer": answer, "sources": sources}
            return JSONResponse(payload)

    except Exception as exc:
        log("query.agent.failed", {"error": str(exc)})
        raise HTTPException(status_code=500, detail=f"Agent interaction failed: {str(exc)}")
