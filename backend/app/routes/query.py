import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from ..clients.llm import llm_client
from ..clients.upstash_search import upstash_search_client
from ..config import get_settings
from ..logging import log

router = APIRouter()


def build_context(docs: List[Dict[str, Any]], max_context_len: int) -> str:
    return (
        "\n\n---\n\n".join(
            [
                doc.get("content", "")[:max_context_len] + "..."
                for doc in docs
                if doc.get("content")
            ]
        )
        if docs
        else ""
    )


@router.post("/query")
async def query(payload: Dict[str, Any]) -> StreamingResponse:
    settings = get_settings()

    query_text: Optional[str] = payload.get("query")
    namespace: Optional[str] = payload.get("namespace")
    index_name: Optional[str] = payload.get("index")
    stream: bool = bool(payload.get("stream", False))

    if not query_text or not namespace:
        raise HTTPException(status_code=400, detail="Query and namespace are required")

    search_query = f"{query_text} {namespace}"
    try:
        search_results = await upstash_search_client.search(
            query=search_query,
            limit=settings.search_max_results,
            filter_expr=f'metadata.namespace = "{namespace}"',
            reranking=True,
            index_name=index_name,
        )
    except Exception as exc:
        log("query.search.failed", {"error": str(exc)})
        raise HTTPException(status_code=500, detail="Search failed") from exc

    if not search_results:
        answer = "I don't have any indexed content for this website. Please crawl first."
        return StreamingResponse(iter([answer]), media_type="text/plain")

    transformed_docs = []
    for result in search_results:
        metadata = result.get("metadata", {}) or {}
        content_obj = result.get("content", {}) or {}
        title = metadata.get("title") or metadata.get("pageTitle") or "Untitled"
        description = metadata.get("description") or ""
        url = metadata.get("url") or metadata.get("sourceURL") or content_obj.get("url") or ""
        raw_content = metadata.get("fullContent") or content_obj.get("text") or ""
        structured = f"TITLE: {title}\nDESCRIPTION: {description}\nSOURCE: {url}\n\n{raw_content}"
        transformed_docs.append(
            {
                "content": structured,
                "url": url,
                "title": title,
                "description": description,
                "score": result.get("score") or 0,
            }
        )

    relevant = sorted(transformed_docs, key=lambda d: d.get("score", 0), reverse=True)[
        : settings.search_max_sources_display
    ]
    docs_to_use = relevant if relevant else transformed_docs[:10]
    context_docs = docs_to_use[: settings.search_max_context_docs]

    context = build_context(context_docs, settings.search_max_context_length)
    if not context or len(context) < 100:
        answer = (
            "I found some relevant pages but couldn't extract enough content to answer. "
            "Try crawling again with a higher page limit."
        )
        sources_min = [
            {"url": d["url"], "title": d["title"], "snippet": (d["content"] or "")[: settings.search_snippet_length] + "..."}
            for d in docs_to_use
        ]
        return StreamingResponse(iter([answer, "\n\nSources:\n", str(sources_min)]), media_type="text/plain")

    sources = [
        {
            "url": d["url"],
            "title": d["title"],
            "snippet": (d["content"] or "")[: settings.search_snippet_length] + "...",
        }
        for d in docs_to_use
    ]

    user_prompt = f"Question: {query_text}\n\nRelevant content from the website:\n{context}\n\nProvide a comprehensive answer based on this information."

    async def streamer():
        # initial sources line as in TS implementation
        yield f"8:{json.dumps({'sources': sources})}\n"
        try:
            async for delta in llm_client.stream_answer(
                system_prompt=settings.ai_system_prompt,
                user_prompt=user_prompt,
                temperature=settings.ai_temperature,
                max_tokens=settings.ai_max_tokens,
            ):
                yield f"0:{json.dumps(delta)}\n"
        except Exception as exc:  # noqa: BLE001
            log("query.stream.error", {"error": str(exc)})
            yield '0:"[error generating response]"\n'

    if stream:
        return StreamingResponse(streamer(), media_type="text/plain; charset=utf-8")

    # Non-streaming: concatenate content
    chunks: List[str] = []
    async for delta in llm_client.stream_answer(
        system_prompt=settings.ai_system_prompt,
        user_prompt=user_prompt,
        temperature=settings.ai_temperature,
        max_tokens=settings.ai_max_tokens,
    ):
        chunks.append(delta)

    answer = "".join(chunks)
    payload = {"answer": answer, "sources": sources}
    return JSONResponse(payload)

