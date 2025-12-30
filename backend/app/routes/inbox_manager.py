import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from openai import AsyncOpenAI

from ..logging import log
from ..config import get_settings
from ..clients.agent_templates.loader import load_agent_template
from ..clients.llm import llm_client
from ..clients.pinecone_client import pinecone_kb_client
from ..services.do_agent_manager import ensure_agent


router = APIRouter()

def _safe_get(d: Dict[str, Any], path: str) -> Any:
    cur: Any = d
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


@router.post("/inbox-manager/draft")
async def inbox_manager_draft(payload: Dict[str, Any]) -> JSONResponse:
    """
    Draft an inbox-manager reply using Pinecone retrieval + direct LLM (no DigitalOcean agent provisioning).

    Expected payload:
      - clientSlug (or namespace)
      - replyText (or query) OR webhookPayload/res (from which we extract data.reply.text_body)

    Returns:
      - draft: string email body
      - sources: list of {title, url, snippet}
    """
    settings = get_settings()
    client_slug: Optional[str] = payload.get("clientSlug") or payload.get("client_slug") or payload.get("namespace")
    if not client_slug:
        raise HTTPException(status_code=400, detail="clientSlug is required")

    # Prefer a dedicated replyText, else fall back to query/messages, else extract from webhook payload.
    reply_text: Optional[str] = payload.get("replyText") or payload.get("reply_text") or payload.get("query")
    if not reply_text:
        messages = payload.get("messages")
        if isinstance(messages, list):
            user_messages = [m for m in messages if isinstance(m, dict) and m.get("role") == "user"]
            if user_messages:
                reply_text = user_messages[-1].get("content")

    res: Optional[Dict[str, Any]] = payload.get("webhookPayload") or payload.get("res")
    if not reply_text and isinstance(res, dict):
        reply_text = _safe_get(res, "data.reply.text_body")

    reply_text = (reply_text or "").strip()
    if not reply_text:
        raise HTTPException(status_code=400, detail="replyText (or webhookPayload.data.reply.text_body) is required")

    # Retrieve context from Pinecone
    hits = pinecone_kb_client.search(
        client_slug=client_slug,
        query=reply_text,
        top_k=int(payload.get("topK") or 8),
        filter=None,
        fields=["text", "title", "url", "file_key", "content_type", "document_source", "chunk_index"],
        wait_after_upsert_s=0.0,
    )

    sources: list[Dict[str, Any]] = []
    context_blocks: list[str] = []
    for h in hits:
        f = h.fields
        title = f.get("title") or f.get("file_key") or "Source"
        url_out = f.get("url") or f.get("file_key") or ""
        snippet = (f.get("text") or "")[:350]
        sources.append({"title": title, "url": url_out, "snippet": snippet})
        context_blocks.append(f"[{title}] {snippet}")

    # Agent instructions (same prompt DO agents use by default)
    try:
        inbox_manager_prompt = load_agent_template("inbox_manager")
    except Exception:
        inbox_manager_prompt = settings.ai_system_prompt

    system_prompt = (
        f"{inbox_manager_prompt}\n\n"
        "You will be given a prospect reply and a small set of knowledge-base context snippets.\n"
        "- Use ONLY that context for factual claims.\n"
        "- If context is insufficient, provide the best safe high-level info and ask if that answers their question.\n"
        "- Output ONLY the email body (no subject line, no JSON).\n"
    )

    user_prompt = (
        "Prospect reply:\n"
        f"{reply_text}\n\n"
        "Knowledge base context:\n"
        + ("\n\n".join(context_blocks) if context_blocks else "(No relevant context found)")
    )

    log("inbox_manager.draft.start", {"client_slug": client_slug, "reply_len": len(reply_text), "sources": len(sources)})

    resp = await llm_client.chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=settings.ai_temperature,
        max_tokens=min(settings.ai_max_tokens, 600),
        model=str(payload.get("model") or "gpt-4o-mini"),
    )
    draft = (resp["choices"][0]["message"]["content"] or "").strip()

    return JSONResponse({"draft": draft, "sources": sources})


@router.post("/inbox-manager/qa")
async def inbox_manager_qa(payload: Dict[str, Any]) -> JSONResponse:
    """
    Run the inbox_manager_qa agent to quality-check a proposed draft reply.

    Expected payload:
      - clientSlug (or namespace): KB/client slug to route the agent
      - webhookPayload (or res): the *nested* webhook payload (our canonical structure)
      - proposedReply (or proposed_reply): draft email text from inbox_manager agent

    Returns:
      - qa_raw: raw model output
      - qa: parsed JSON if possible (else null)
    """
    client_slug: Optional[str] = payload.get("clientSlug") or payload.get("client_slug") or payload.get("namespace")
    res: Optional[Dict[str, Any]] = payload.get("webhookPayload") or payload.get("res")
    proposed_reply: Optional[str] = payload.get("proposedReply") or payload.get("proposed_reply")

    if not client_slug:
        raise HTTPException(status_code=400, detail="clientSlug is required")
    if not isinstance(res, dict):
        raise HTTPException(status_code=400, detail="webhookPayload (res) must be an object")
    if not proposed_reply:
        raise HTTPException(status_code=400, detail="proposedReply is required")

    # Ensure QA agent exists for this client
    agent_rec = await ensure_agent(client_slug, agent_type="inbox_manager_qa")
    if not agent_rec.endpoint_url or not agent_rec.api_key:
        raise HTTPException(status_code=500, detail="Failed to resolve QA agent endpoint/key")

    workspace_name = (res.get("event") or {}).get("workspace_name")
    prospect_name = ((res.get("data") or {}).get("reply") or {}).get("from_name")

    user_content = (
        "You are the inbox_manager_qa agent.\n\n"
        "Evaluate the proposed reply against the full webhook payload.\n\n"
        f"workspace_name: {workspace_name}\n"
        f"prospect_name: {prospect_name}\n\n"
        "webhook payload (variable name `res`):\n"
        f"{json.dumps(res, ensure_ascii=False)}\n\n"
        "proposed_reply:\n"
        f"{proposed_reply}\n"
    )

    client = AsyncOpenAI(base_url=f"{agent_rec.endpoint_url}/api/v1", api_key=agent_rec.api_key)

    log(
        "inbox_manager.qa.start",
        {"client_slug": client_slug, "agent_uuid": agent_rec.agent_uuid, "has_workspace": bool(workspace_name)},
    )

    resp = await client.chat.completions.create(
        model="n/a",
        messages=[{"role": "user", "content": user_content}],
        stream=False,
        extra_body={"include_retrieval_info": False},
    )

    qa_raw = (resp.choices[0].message.content or "").strip()

    qa: Optional[Dict[str, Any]] = None
    try:
        qa = json.loads(qa_raw)
    except Exception:
        qa = None

    return JSONResponse({"qa_raw": qa_raw, "qa": qa})


