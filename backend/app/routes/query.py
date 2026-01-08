import json
import asyncio
import re
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
        return "kb_chat"
    return t.replace("-", "_")

def _parse_requested_case_study_count(q: str) -> int:
    """
    Best-effort parse of requests like:
      - "summarize 5 case studies"
      - "summarise 3 case studies"
      - "summarize a few case studies"
    """
    text = (q or "").strip().lower()
    # Explicit number
    m = re.search(r"\b(?:summarize|summarise)\s+(\d+)\s+case\s+stud", text)
    if m:
        try:
            n = int(m.group(1))
            return max(1, min(10, n))
        except Exception:
            pass
    # Vague counts
    if re.search(r"\b(?:a\s+few|few|some|several)\s+case\s+stud", text):
        return 3
    return 3

def _looks_like_case_study_summary_request(q: str) -> bool:
    text = (q or "").strip().lower()
    if "case stud" not in text:
        return False
    # Summarization intent
    return any(x in text for x in ["summarize", "summarise", "summary", "summaries", "highlight", "highlights", "overview"])

def _build_case_study_summaries_context(
    *,
    hits: List[Any],
    max_docs: int,
    chunks_per_doc: int = 3,
) -> tuple[List[Dict[str, Any]], List[str]]:
    """
    Convert chunk-level hits into doc-level sources and numbered context blocks.

    We dedupe by `file_key` and then take up to `chunks_per_doc` chunks per doc (ordered by chunk_index).
    """
    # file_key -> list of hits
    by_fk: Dict[str, List[Any]] = {}
    for h in hits:
        f = getattr(h, "fields", {}) or {}
        fk = str(f.get("file_key") or "").strip()
        if not fk:
            continue
        by_fk.setdefault(fk, []).append(h)

    # Rank docs by best score
    ranked: List[tuple[str, float]] = []
    for fk, hs in by_fk.items():
        best = 0.0
        for h in hs:
            try:
                best = max(best, float(getattr(h, "score", 0.0) or 0.0))
            except Exception:
                continue
        ranked.append((fk, best))
    ranked.sort(key=lambda x: x[1], reverse=True)
    top_fks = [fk for fk, _ in ranked[: max_docs]]

    sources: List[Dict[str, Any]] = []
    context_blocks: List[str] = []
    for i, fk in enumerate(top_fks, start=1):
        hs = by_fk.get(fk, [])
        # Order chunks by chunk_index to preserve narrative flow
        def _chunk_idx(h: Any) -> int:
            try:
                return int((getattr(h, "fields", {}) or {}).get("chunk_index") or 0)
            except Exception:
                return 0
        hs_sorted = sorted(hs, key=_chunk_idx)[: max(1, chunks_per_doc)]
        # Pick representative metadata
        first_fields = (getattr(hs_sorted[0], "fields", {}) or {}) if hs_sorted else {}
        title = str(first_fields.get("title") or first_fields.get("file_key") or f"Case study {i}").strip()
        url_out = str(first_fields.get("url") or first_fields.get("file_key") or "").strip()
        combined = "\n\n".join([str((getattr(h, "fields", {}) or {}).get("text") or "").strip() for h in hs_sorted]).strip()
        snippet = (combined[:250] + "…") if len(combined) > 250 else combined
        sources.append({"title": title, "url": url_out, "snippet": snippet})
        context_blocks.append(f"[{i}] Title: {title}\nURL: {url_out}\nContent:\n{combined}")

    return sources, context_blocks


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

    # Special handling: "summarize N case studies" needs doc-level retrieval, not just 5 random chunks.
    case_study_mode = _looks_like_case_study_summary_request(query_text)
    requested_n = _parse_requested_case_study_count(query_text) if case_study_mode else 0
    if case_study_mode and not content_type:
        # If caller didn't explicitly filter, strongly bias to case studies.
        pc_filter["content_type"] = {"$eq": "case_studies"}

    # Retrieve context from Pinecone
    top_k_in = int(payload.get("topK") or 5)
    # For case study summaries we need enough chunks to cover multiple distinct docs.
    top_k = top_k_in
    if case_study_mode:
        top_k = max(top_k_in, min(60, max(20, requested_n * 10)))

    hits = pinecone_kb_client.search(
        client_slug=client_slug,
        query=query_text,
        top_k=top_k,
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
            top_k=top_k,
            filter=pc_filter or None,
            fields=["text", "title", "url", "file_key", "content_type", "document_source", "chunk_index"],
            wait_after_upsert_s=0.0,
        )

    # Build sources + context string
    sources: List[Dict[str, Any]] = []
    context_blocks: List[str] = []
    if case_study_mode:
        # Prefer doc-level, numbered context so the model can actually summarize multiple distinct case studies.
        sources, context_blocks = _build_case_study_summaries_context(hits=hits, max_docs=requested_n, chunks_per_doc=3)
        if sources:
            # Strong instruction: produce N summaries, cite using [n]
            query_text = (
                f"{query_text}\n\n"
                f"IMPORTANT: Summarize {len(sources)} distinct case studies from the context below. "
                "For each, include 2-4 bullets: (1) client/problem, (2) what was done, (3) measurable outcomes if present. "
                "Cite sources as [1], [2], etc.\n"
            )
    else:
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
