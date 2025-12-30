import json
import asyncio
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from ..config import get_settings
from ..logging import log
from ..clients.agent_templates.loader import load_agent_template
from ..clients.llm import llm_client
from ..clients.pinecone_client import pinecone_kb_client

router = APIRouter()

def _normalize_agent_type(agent_type: str) -> str:
    t = (agent_type or "").strip().lower()
    if not t:
        return "inbox_manager"
    return t.replace("-", "_")


def _system_prompt_for(agent_type: str) -> str:
    """
    Prefer the agent template (if present) so behavior matches our intended "agentic" roles.
    Fallback to a generic QA-safe assistant prompt.
    """
    normalized = _normalize_agent_type(agent_type)
    try:
        base = load_agent_template(normalized)
    except Exception:
        base = (
            "You are a helpful assistant. Answer the user's question using the provided context.\n"
            "If the context is insufficient, say so and ask a clarifying question.\n"
            "Be concise and specific."
        )

    # Common guardrails: keep output clean, don't cite raw filenames unless asked
    return (
        f"{base}\n\n"
        "You will be given a small set of retrieved context snippets.\n"
        "- Use ONLY that context for factual claims.\n"
        "- If context is insufficient, say what is missing and ask ONE clarifying question.\n"
        "- Do not mention internal tool names, record IDs, or retrieval mechanics.\n"
    )


@router.post("/query")
async def query(payload: Dict[str, Any]) -> StreamingResponse:
    settings = get_settings()

    query_text: Optional[str] = payload.get("query")
    client_slug: Optional[str] = payload.get("clientSlug") or payload.get("namespace")
    index_name: Optional[str] = payload.get("index")
    agent_type: str = str(payload.get("agentType") or payload.get("agent_type") or "inbox_manager")
    stream: bool = bool(payload.get("stream", False))
    # Optional filters
    content_type: Optional[str] = payload.get("contentType") or payload.get("content_type")
    document_source: Optional[str] = payload.get("documentSource") or payload.get("document_source")
    keywords_in: Any = payload.get("keywords") or payload.get("keyword") or payload.get("keywordsAny")

    # Support chat-style payloads
    if not query_text:
        messages = payload.get("messages")
        if isinstance(messages, list):
            user_messages = [m for m in messages if isinstance(m, dict) and m.get("role") == "user"]
            if user_messages:
                query_text = user_messages[-1].get("content")

    if not query_text or not client_slug:
        raise HTTPException(status_code=400, detail="Query and clientSlug/index are required")

    log("query.start", {"client_slug": client_slug, "query_len": len(query_text), "agent_type": agent_type})

    # Build Pinecone filter (metadata filtering)
    pc_filter: Dict[str, Any] = {}
    if content_type:
        pc_filter["content_type"] = {"$eq": str(content_type)}
    if document_source:
        pc_filter["document_source"] = {"$eq": str(document_source)}
    # keywords is stored as a string list; support filtering where ANY keyword matches
    keywords_list: List[str] = []
    if isinstance(keywords_in, str) and keywords_in.strip():
        # allow "a,b,c" or single
        keywords_list = [k.strip().lower() for k in keywords_in.split(",") if k.strip()]
    elif isinstance(keywords_in, list):
        keywords_list = [str(k).strip().lower() for k in keywords_in if str(k).strip()]
    if keywords_list:
        pc_filter["keywords"] = {"$in": keywords_list}

    # Retrieve context from Pinecone
    hits = pinecone_kb_client.search(
        client_slug=client_slug,
        query=query_text,
        top_k=int(payload.get("topK") or 5),
        filter=pc_filter or None,
        fields=["text", "title", "url", "file_key", "content_type", "document_source", "chunk_index"],
        # Pinecone eventual consistency: if user queries right after ingestion, retry once after 10s
        wait_after_upsert_s=0.0,
    )
    if not hits:
        await asyncio.sleep(10)
        hits = pinecone_kb_client.search(
            client_slug=client_slug,
            query=query_text,
            top_k=int(payload.get("topK") or 5),
            filter=pc_filter or None,
            fields=["text", "title", "url", "file_key", "content_type", "document_source", "chunk_index"],
            wait_after_upsert_s=0.0,
        )

    # Build sources + context string
    sources: List[Dict[str, Any]] = []
    context_blocks: List[str] = []
    for h in hits:
        f = h.fields
        title = f.get("title") or f.get("file_key") or "Source"
        url_out = f.get("url") or f.get("file_key") or ""
        snippet = (f.get("text") or "")[:250]
        sources.append({"title": title, "url": url_out, "snippet": snippet})
        context_blocks.append(f"[{title}] {snippet}")

    system_prompt = _system_prompt_for(agent_type)
    user_prompt = f"User question:\n{query_text}\n\nContext:\n" + "\n\n".join(context_blocks)

    if stream:
        async def streamer():
            # Send sources up-front in the format the frontend expects.
            yield f"8:{json.dumps({'sources': sources})}\n"
            try:
                async for delta in llm_client.stream_answer(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=settings.ai_temperature,
                    max_tokens=settings.ai_max_tokens,
                ):
                    yield f"0:{json.dumps(delta)}\n"
            except Exception as e:
                log("query.stream.error", {"error": str(e)})
                yield '0:"[error generating response]"\n'

        return StreamingResponse(streamer(), media_type="text/plain; charset=utf-8")

    resp = await llm_client.chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=settings.ai_temperature,
        max_tokens=settings.ai_max_tokens,
        model="gpt-4o-mini",
    )
    answer = resp["choices"][0]["message"]["content"]
    return JSONResponse({"answer": answer, "sources": sources})
