import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from app.clients.pinecone_assistant_client import pinecone_assistant_client
from app.config import get_settings


def _build_inbox_manager_prompt(reply_text: str) -> str:
    reply_text = (reply_text or "").strip()
    return (
        "You are an inbox manager. Draft a concise, friendly, professional email reply to a prospect.\n"
        "Constraints:\n"
        "- Keep it under 150 words.\n"
        "- Ask 1-2 crisp follow-up questions.\n"
        "- No marketing fluff.\n"
        "- Output ONLY the email body (no subject line).\n\n"
        f"Prospect reply:\n{reply_text}\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Test Pinecone Assistant for inbox_manager-style drafting.")
    parser.add_argument("--assistant-name", default=None, help="Pinecone assistant name (or env PINECONE_INBOX_MANAGER_ASSISTANT_NAME).")
    parser.add_argument("--model", default=None, help="Optional LLM model override (e.g. gpt-4.1).")
    parser.add_argument("--text", default=None, help="Prospect reply text (if omitted, reads stdin).")
    parser.add_argument("--stream", action="store_true", help="Stream the response.")
    parser.add_argument("--list", action="store_true", help="List assistants and exit.")
    parser.add_argument("--describe", action="store_true", help="Describe the assistant and exit (requires --assistant-name or env default).")
    args = parser.parse_args()

    settings = get_settings()
    assistant_name = (args.assistant_name or settings.pinecone_inbox_manager_assistant_name or "").strip() or None

    if args.list:
        resp = pinecone_assistant_client.list_assistants()
        print(resp)
        return 0

    if args.describe:
        if not assistant_name:
            print("assistant_name is required for --describe", file=sys.stderr)
            return 2
        resp = pinecone_assistant_client.describe_assistant(assistant_name)
        print(resp)
        return 0

    # Chat path
    text = args.text
    if text is None:
        text = sys.stdin.read()
    text = (text or "").strip()
    if not text:
        print("No prospect reply text provided. Pass --text or pipe stdin.", file=sys.stderr)
        return 2

    prompt = _build_inbox_manager_prompt(text)
    messages: List[Dict[str, str]] = [{"role": "user", "content": prompt}]

    if args.stream:
        for delta in pinecone_assistant_client.stream_text(
            assistant_name=assistant_name,
            messages=messages,
            model=args.model,
        ):
            print(delta, end="", flush=True)
        print()
    else:
        out = pinecone_assistant_client.chat_text(
            assistant_name=assistant_name,
            messages=messages,
            model=args.model,
        )
        print(out)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


