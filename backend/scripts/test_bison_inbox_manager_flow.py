"""
One-off test harness:
  - Load FIRST nested Email Bison webhook payload from test_data
  - Map event.workspace_name -> client_slug via Supabase table bison_client_db
  - Send reply.text_body to inbox_manager agent
  - Run inbox_manager_qa agent on (webhook payload + proposed reply)
  - Print final formatted email (if present)

Usage:
  cd /Users/hynes/dev/website-agents
  backend/venv/bin/python backend/scripts/test_bison_inbox_manager_flow.py
"""

from __future__ import annotations

import asyncio
import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional

from openai import AsyncOpenAI

# Ensure backend/app import works when running from repo root
import sys

repo_root = Path(__file__).resolve().parents[2]
backend_dir = repo_root / "backend"
sys.path.insert(0, str(backend_dir))

from app.clients.supabase_client import supabase_client  # noqa: E402
from app.clients.supabase_client import SupabaseClient  # noqa: E402
from app.services.do_agent_manager import ensure_agent  # noqa: E402
from app.clients.llm import llm_client  # noqa: E402
from app.clients.pinecone_client import pinecone_kb_client  # noqa: E402
from app.clients.agent_templates.loader import load_agent_template  # noqa: E402
from app.config import get_settings  # noqa: E402


SAMPLE_PATH = repo_root / "test_data" / "bison_webhook_lead_interested_mintLeads_nested.json"


def _safe_get(d: Dict[str, Any], path: str) -> Any:
    cur: Any = d
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


async def _run_agent(client_slug: str, agent_type: str, user_content: str) -> str:
    rec = await ensure_agent(client_slug, agent_type=agent_type)
    if not rec.endpoint_url or not rec.api_key:
        raise RuntimeError(f"Missing endpoint/key for {agent_type}:{client_slug}")
    client = AsyncOpenAI(base_url=f"{rec.endpoint_url}/api/v1", api_key=rec.api_key)
    resp = await client.chat.completions.create(
        model="n/a",
        messages=[{"role": "user", "content": user_content}],
        stream=False,
        extra_body={"include_retrieval_info": False},
    )
    return (resp.choices[0].message.content or "").strip()

async def _draft_with_pinecone(client_slug: str, reply_text: str) -> str:
    """
    Draft reply using Pinecone retrieval + direct LLM (no DO agents).
    Mirrors /api/firestarter/inbox-manager/draft logic.
    """
    settings = get_settings()
    try:
        inbox_manager_prompt = load_agent_template("inbox_manager")
    except Exception:
        inbox_manager_prompt = settings.ai_system_prompt

    hits = pinecone_kb_client.search(
        client_slug=client_slug,
        query=reply_text,
        top_k=8,
        filter=None,
        fields=["text", "title", "url", "file_key", "content_type", "document_source", "chunk_index"],
        wait_after_upsert_s=0.0,
    )
    context_blocks = []
    for h in hits:
        f = h.fields
        title = f.get("title") or f.get("file_key") or "Source"
        snippet = (f.get("text") or "")[:350]
        context_blocks.append(f"[{title}] {snippet}")

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
    resp = await llm_client.chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=settings.ai_temperature,
        max_tokens=min(settings.ai_max_tokens, 600),
        model="gpt-4o-mini",
    )
    return (resp["choices"][0]["message"]["content"] or "").strip()


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-index", type=int, default=0, help="Which sample payload to use from the JSON array")
    parser.add_argument("--supabase-project-url", type=str, default=None, help="Override Supabase project URL")
    parser.add_argument("--supabase-api-key", type=str, default=None, help="Override Supabase API key (anon or service role)")
    parser.add_argument("--supabase-schema", type=str, default=None, help="Override schema (default public)")
    parser.add_argument(
        "--draft-engine",
        type=str,
        default="pinecone",
        choices=["pinecone", "do-agent"],
        help="How to generate the draft reply: pinecone (default) or do-agent.",
    )
    args = parser.parse_args()

    arr = json.loads(SAMPLE_PATH.read_text())
    if not isinstance(arr, list) or not arr:
        raise SystemExit(f"Expected non-empty list in {SAMPLE_PATH}")

    if args.sample_index < 0 or args.sample_index >= len(arr):
        raise SystemExit(f"--sample-index out of range (0..{len(arr)-1})")

    webhook_payload = arr[args.sample_index]
    if not isinstance(webhook_payload, dict):
        raise SystemExit("First record is not an object")

    workspace_name = _safe_get(webhook_payload, "event.workspace_name")
    workspace_id = _safe_get(webhook_payload, "event.workspace_id")
    reply_text_body = _safe_get(webhook_payload, "data.reply.text_body")

    if not workspace_name and workspace_id is None:
        raise SystemExit("Missing event.workspace_name and event.workspace_id in sample payload")
    if not reply_text_body:
        raise SystemExit("Missing data.reply.text_body in sample payload")

    sb = (
        SupabaseClient(
            project_url=args.supabase_project_url,
            api_key=args.supabase_api_key,
            schema=args.supabase_schema,
        )
        if (args.supabase_project_url or args.supabase_api_key or args.supabase_schema)
        else supabase_client
    )
    client_slug = await sb.get_client_slug_for_workspace(
        workspace_id=int(workspace_id) if workspace_id is not None else None,
        workspace_name=str(workspace_name) if workspace_name else None,
    )
    if not client_slug:
        raise SystemExit(
            f"No client_slug found in Supabase for workspace_id={workspace_id!r} workspace_name={workspace_name!r}"
        )

    print("=" * 100)
    print("workspace_name:", workspace_name)
    print("workspace_id:", workspace_id)
    print("mapped client_slug:", client_slug)
    print("=" * 100)

    # 1) Draft reply
    if args.draft_engine == "do-agent":
        proposed_reply = await _run_agent(client_slug, "inbox_manager", str(reply_text_body))
    else:
        proposed_reply = await _draft_with_pinecone(client_slug, str(reply_text_body))
    print("\n--- inbox_manager proposed_reply (raw) ---\n")
    print(proposed_reply)

    # 2) QA pass: provide full webhook payload + draft
    qa_prompt = (
        "You are the inbox_manager_qa agent.\n\n"
        "Evaluate the proposed reply against the full webhook payload.\n"
        "Return JSON only.\n\n"
        "webhook payload (variable name `res`):\n"
        f"{json.dumps(webhook_payload, ensure_ascii=False)}\n\n"
        "proposed_reply:\n"
        f"{proposed_reply}\n"
    )
    qa_raw = await _run_agent(client_slug, "inbox_manager_qa", qa_prompt)

    print("\n--- inbox_manager_qa output (raw) ---\n")
    print(qa_raw)

    qa: Optional[Dict[str, Any]] = None
    try:
        qa = json.loads(qa_raw)
    except Exception:
        qa = None

    formatted_email = None
    if isinstance(qa, dict):
        formatted_email = _safe_get(qa, "task_2.formatted_email")

    print("\n--- FINAL formatted_email ---\n")
    if formatted_email:
        print(formatted_email)
    else:
        print("(No task_2.formatted_email found; see QA raw output above.)")


if __name__ == "__main__":
    asyncio.run(main())


