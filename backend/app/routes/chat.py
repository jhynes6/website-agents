from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import get_settings
from ..logging import log
from ..clients.llm import llm_client
from ..clients.pinecone_client import pinecone_kb_client

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    client_slug: str
    messages: List[ChatMessage]
    top_k: Optional[int] = 5
    model: Optional[str] = "gpt-4o-mini"


class ChatResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]]
    namespace: str


@router.post("/chat", response_model=ChatResponse)
async def chat_with_client(request: ChatRequest) -> ChatResponse:
    """
    Legacy typed chat endpoint.

    Uses Pinecone retrieval (Records API via `pinecone_kb_client`) and the configured LLM
    (`llm_client`) to answer using retrieved context.
    """
    settings = get_settings()
    
    namespace = request.client_slug
    
    # Get the latest user message
    user_message = request.messages[-1].content if request.messages else ""
    if not user_message:
        raise HTTPException(status_code=400, detail="No user message provided")
    
    log("chat.request", {
        "client": request.client_slug,
        "message_length": len(user_message),
        "top_k": request.top_k
    })
    
    try:
        # Retrieve context from Pinecone (Records API, index configured via Settings)
        hits = pinecone_kb_client.search(
            client_slug=namespace,
            query=user_message,
            top_k=int(request.top_k or 5),
            filter=None,
            fields=["text", "title", "url", "file_key", "content_type", "document_source", "chunk_index"],
            wait_after_upsert_s=0.0,
        )

        sources: List[Dict[str, Any]] = []
        context_blocks: List[str] = []
        for h in hits:
            f = h.fields
            title = f.get("title") or f.get("file_key") or "Source"
            url_out = f.get("url") or f.get("file_key") or ""
            snippet = (f.get("text") or "")[:350]
            sources.append(
                {
                    "doc_id": f.get("file_key") or "",
                    "url": url_out,
                    "title": title,
                    "content_type": f.get("content_type") or "",
                    "score": h.score,
                    "chunk_index": f.get("chunk_index", 0),
                }
            )
            context_blocks.append(f"[{title}] {snippet}")

        if not context_blocks:
            log("chat.no_context", {"client": request.client_slug})
            return ChatResponse(
                response="I don't have enough information to answer that question.",
                sources=[],
                namespace=namespace
            )
        
        system_prompt = (
            f"You are a helpful assistant answering questions about {request.client_slug}.\n"
            "Use the provided context snippets for factual claims.\n"
            "If the context is insufficient, say so and ask a clarifying question.\n"
        )
        user_prompt = (
            "User question:\n"
            f"{user_message}\n\n"
            "Context:\n"
            + ("\n\n".join(context_blocks) if context_blocks else "(No relevant context found)")
        )

        resp = await llm_client.chat(
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=settings.ai_temperature,
            max_tokens=settings.ai_max_tokens,
            model=request.model or "gpt-4o-mini",
        )
        response_text = resp["choices"][0]["message"]["content"]
        
        log("chat.success", {
            "client": request.client_slug,
            "sources_found": len(sources),
            "response_length": len(response_text or "")
        })
        
        return ChatResponse(
            response=response_text or "I couldn't generate a response.",
            sources=sources,
            namespace=namespace
        )
    
    except Exception as e:
        log("chat.error", {"client": request.client_slug, "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

