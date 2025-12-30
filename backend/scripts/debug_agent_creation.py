"""
Create/manage Pinecone “inbox manager” assistants and load client docs from DigitalOcean Spaces.

Why this script exists:
- DigitalOcean “agents” (GenAI) were the original runtime. This repo is moving to Pinecone
  for vector storage and (optionally) Pinecone Assistant for chat-time RAG.

Key design choice:
- Prefer a *single shared assistant* for all clients.
- Upload each client’s docs with file metadata: {"client_slug": "<slug>"}.
- At chat time, pass filter={"client_slug": "<slug>"} to restrict citations/grounding.

This avoids creating N assistants and plays nicely with plan limits.

Typical usage (repo root, venv active):
  # 1) Ensure assistant exists
  backend/venv/bin/python backend/scripts/debug_agent_creation.py ensure-assistant \
    --assistant-name mintleads-inbox-manager \
    --region us

  # 2) Upload one client’s files from Spaces into that assistant (metadata includes client_slug)
  backend/venv/bin/python backend/scripts/debug_agent_creation.py upload-client \
    --assistant-name mintleads-inbox-manager \
    --client-slug vew-media \
    --prefix vew-media/ \
    --limit-files 50

  # 3) Chat against only that client’s files (filter={client_slug})
  backend/venv/bin/python backend/scripts/debug_agent_creation.py chat-test \
    --assistant-name mintleads-inbox-manager \
    --client-slug vew-media \
    --prompt "Summarize our deliverables and pricing in 5 bullets."
"""

from __future__ import annotations

import argparse
import os
import sys
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# Add backend directory to path (run from repo root)
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from app.clients.digital_ocean_client import do_client  # noqa: E402
from app.config import get_settings  # noqa: E402


SUPPORTED_EXTS = {".txt", ".md", ".json", ".pdf", ".docx"}


def _require_pinecone() -> Any:
    settings = get_settings()
    if not settings.pinecone_api_key:
        raise SystemExit("Missing PINECONE_API_KEY in env (needed to create assistants/upload/chat).")
    try:
        from pinecone import Pinecone
    except Exception as e:
        raise SystemExit(
            f"Missing pinecone SDK. Install in backend venv: pip install --upgrade pinecone pinecone-plugin-assistant (error: {e})"
        )
    return Pinecone(api_key=settings.pinecone_api_key)


def _assistant_name(args: argparse.Namespace) -> str:
    s = get_settings()
    name = (args.assistant_name or s.pinecone_inbox_manager_assistant_name or "").strip()
    if not name:
        raise SystemExit("assistant name required: pass --assistant-name or set PINECONE_INBOX_MANAGER_ASSISTANT_NAME.")
    return name


def _ensure_spaces_client() -> Tuple[Any, str]:
    s = get_settings()
    if not do_client.s3_client:
        raise SystemExit("Spaces client not configured. Set DIGITALOCEAN_SPACES_KEY/SECRET/REGION.")
    bucket = (s.digitalocean_spaces_bucket or "").strip()
    if not bucket:
        raise SystemExit("Missing DIGITALOCEAN_SPACES_BUCKET (must point at your KB bucket, e.g. mintleads-clients-kb).")
    return do_client.s3_client, bucket


def _list_keys(bucket: str, prefix: str, limit: Optional[int] = None) -> List[str]:
    s3, _ = _ensure_spaces_client()
    out: List[str] = []
    token: Optional[str] = None
    while True:
        kwargs: Dict[str, Any] = {"Bucket": bucket, "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token
        resp = s3.list_objects_v2(**kwargs)
        for obj in (resp.get("Contents") or []):
            k = obj.get("Key")
            if not k or k.endswith("/"):
                continue
            out.append(str(k))
            if limit and len(out) >= limit:
                return out
        token = resp.get("NextContinuationToken")
        if not token:
            break
    return out


def _read_object_bytes(bucket: str, key: str) -> bytes:
    s3, _ = _ensure_spaces_client()
    resp = s3.get_object(Bucket=bucket, Key=key)
    body = resp["Body"].read()
    return body if isinstance(body, (bytes, bytearray)) else bytes(body)


def _safe_file_name(client_slug: str, key: str, max_len: int = 180) -> str:
    # Pinecone Assistant stores a "name" per file; keep it unique-ish and readable.
    base = key.strip("/").replace("/", "__")
    name = f"{client_slug}__{base}"
    if len(name) > max_len:
        # keep last segment (often filename) and trim from the left
        tail = base.split("__")[-1]
        name = f"{client_slug}__{tail}"
        if len(name) > max_len:
            name = name[-max_len:]
    return name


def cmd_ensure_assistant(args: argparse.Namespace) -> int:
    pc = _require_pinecone()
    name = _assistant_name(args)
    region = (args.region or "us").strip().lower()
    instructions = (args.instructions or "").strip() or None
    metadata: Dict[str, Any] = {"purpose": "inbox_manager", "shared": True}

    # If it exists, just describe.
    try:
        existing = pc.assistant.describe_assistant(assistant_name=name)
        print({"exists": True, "assistant": existing})
        return 0
    except Exception:
        pass

    created = pc.assistant.create_assistant(
        assistant_name=name,
        instructions=instructions,
        metadata=metadata,
        region=region,
        timeout=args.timeout,
    )
    print({"created": True, "assistant": created})
    return 0


def cmd_upload_client(args: argparse.Namespace) -> int:
    pc = _require_pinecone()
    assistant_name = _assistant_name(args)
    client_slug = (args.client_slug or "").strip()
    if not client_slug:
        raise SystemExit("--client-slug is required.")

    prefix = (args.prefix if args.prefix is not None else f"{client_slug}/").strip()
    if prefix and not prefix.endswith("/"):
        prefix = f"{prefix}/"

    s3, bucket = _ensure_spaces_client()
    # allow override bucket, but default to env bucket
    if args.bucket:
        bucket = args.bucket.strip()

    keys = _list_keys(bucket, prefix, limit=args.limit_files)
    if not keys:
        raise SystemExit(f"No objects found in bucket={bucket} prefix={prefix!r}")

    # Filter to supported file types
    selected: List[str] = []
    for k in keys:
        ext = os.path.splitext(k.lower())[1]
        if ext in SUPPORTED_EXTS:
            selected.append(k)
    if args.limit_files:
        selected = selected[: args.limit_files]

    print(
        {
            "bucket": bucket,
            "prefix": prefix,
            "candidate_keys": len(keys),
            "selected_supported": len(selected),
            "assistant": assistant_name,
            "client_slug": client_slug,
            "dry_run": bool(args.dry_run),
        }
    )

    if args.dry_run:
        print({"first_keys": selected[:10]})
        return 0

    # Ensure assistant exists (create if missing)
    try:
        pc.assistant.describe_assistant(assistant_name=assistant_name)
    except Exception:
        pc.assistant.create_assistant(
            assistant_name=assistant_name,
            instructions=(args.instructions or "").strip() or None,
            metadata={"purpose": "inbox_manager", "shared": True},
            region=(args.region or "us").strip().lower(),
            timeout=args.timeout,
        )

    assistant = pc.assistant.Assistant(assistant_name=assistant_name)

    uploaded = 0
    skipped = 0
    for k in selected:
        # Check size cheaply via HeadObject if requested
        if args.max_bytes:
            try:
                head = s3.head_object(Bucket=bucket, Key=k)
                size = int(head.get("ContentLength") or 0)
                if size and size > args.max_bytes:
                    skipped += 1
                    continue
            except Exception:
                # if head fails, fall back to download
                pass

        data = _read_object_bytes(bucket, k)
        if args.max_bytes and len(data) > args.max_bytes:
            skipped += 1
            continue

        file_name = _safe_file_name(client_slug, k)
        meta = {
            "client_slug": client_slug,
            "source_bucket": bucket,
            "source_key": k,
            "doc_kind": "kb_source",
        }
        stream = BytesIO(data)
        assistant.upload_bytes_stream(stream=stream, file_name=file_name, metadata=meta, timeout=args.file_timeout)
        uploaded += 1

    print({"uploaded": uploaded, "skipped": skipped, "assistant": assistant_name, "client_slug": client_slug})
    return 0


def cmd_list_files(args: argparse.Namespace) -> int:
    pc = _require_pinecone()
    assistant_name = _assistant_name(args)
    assistant = pc.assistant.Assistant(assistant_name=assistant_name)
    filt: Optional[Dict[str, Any]] = None
    if args.client_slug:
        filt = {"client_slug": args.client_slug}
    resp = assistant.list_files(filter=filt) if filt else assistant.list_files()
    print(resp)
    return 0


def cmd_chat_test(args: argparse.Namespace) -> int:
    pc = _require_pinecone()
    assistant_name = _assistant_name(args)
    client_slug = (args.client_slug or "").strip()
    if not client_slug:
        raise SystemExit("--client-slug is required.")
    prompt = (args.prompt or "").strip()
    if not prompt:
        raise SystemExit("--prompt is required.")
    try:
        from pinecone_plugins.assistant.models.chat import Message
    except Exception as e:
        raise SystemExit(f"pinecone assistant plugin not available (pip install --upgrade pinecone pinecone-plugin-assistant). error={e}")
    assistant = pc.assistant.Assistant(assistant_name=assistant_name)
    msg = Message(role="user", content=prompt)
    resp = assistant.chat(messages=[msg], filter={"client_slug": client_slug}, stream=False)
    print(resp)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Create Pinecone inbox-manager assistant and load per-client docs from Spaces.")
    parser.add_argument("--assistant-name", default=None, help="Assistant name (or env PINECONE_INBOX_MANAGER_ASSISTANT_NAME).")
    parser.add_argument("--region", default="us", help="Assistant region: 'us' or 'eu'.")
    parser.add_argument("--instructions", default=None, help="Optional assistant instructions (used when creating).")
    parser.add_argument("--timeout", type=int, default=30, help="Assistant create timeout (seconds).")

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ensure = sub.add_parser("ensure-assistant", help="Create assistant if missing (else describe).")
    p_ensure.set_defaults(func=cmd_ensure_assistant)

    p_upload = sub.add_parser("upload-client", help="Upload one client’s files from Spaces into the assistant with client_slug metadata.")
    p_upload.add_argument("--client-slug", required=True)
    p_upload.add_argument("--bucket", default=None, help="Override Spaces bucket (defaults to DIGITALOCEAN_SPACES_BUCKET).")
    p_upload.add_argument("--prefix", default=None, help="Spaces prefix (defaults to '<client-slug>/').")
    p_upload.add_argument("--limit-files", type=int, default=50, help="Max number of files to consider/upload.")
    p_upload.add_argument("--max-bytes", type=int, default=8_000_000, help="Skip files larger than this many bytes (default 8MB).")
    p_upload.add_argument("--file-timeout", type=int, default=-1, help="Upload timeout: -1 returns immediately; None waits (SDK-specific).")
    p_upload.add_argument("--dry-run", action="store_true")
    p_upload.set_defaults(func=cmd_upload_client)

    p_files = sub.add_parser("list-files", help="List files in assistant (optionally filtered by client_slug).")
    p_files.add_argument("--client-slug", default=None)
    p_files.set_defaults(func=cmd_list_files)

    p_chat = sub.add_parser("chat-test", help="Chat with assistant using filter={'client_slug': ...}.")
    p_chat.add_argument("--client-slug", required=True)
    p_chat.add_argument("--prompt", required=True)
    p_chat.set_defaults(func=cmd_chat_test)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

