"""
Sync legacy JSON report files from DigitalOcean Spaces into Pinecone "report" indexes.

Targets (via env / backend/app/config.py):
- CLIENT_KB_REPORTS index, namespace CLIENT_KB_REPORTS_NAMESPACE (default: _client_kb_summary)
  - Pulls from Spaces bucket: mintleads-clients-kb/_client_kb_master/**
  - IDs preserve folder structure, e.g. "_client_kb_master/summary.json"

- AGENT_REPORTS index, namespace AGENT_REPORTS_NAMESPACE (default: agents)
  - Pulls from Spaces bucket: mintleads-agents-store/{agent-api-tokens.json, agent_registry.json, agents/**}
  - IDs preserve folder structure, e.g. "agent-api-tokens.json", "agent_registry.json", "agents/inbox_manager_foo.json"

Implementation notes:
- Uses Pinecone integrated embedding via `upsert_records` so we can store JSON as searchable text.
- Stores raw JSON as a compact string in the mapped text field (`text`) and keeps a few flat fields for convenience.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import boto3

from app.config import get_settings


def _spaces_client():
    s = get_settings()
    if not s.digitalocean_spaces_key or not s.digitalocean_spaces_secret:
        raise SystemExit("DIGITALOCEAN_SPACES_KEY/SECRET not configured")
    region = s.digitalocean_spaces_region or "tor1"
    return boto3.client(
        "s3",
        region_name=region,
        endpoint_url=f"https://{region}.digitaloceanspaces.com",
        aws_access_key_id=s.digitalocean_spaces_key,
        aws_secret_access_key=s.digitalocean_spaces_secret,
    )


def _list_keys(bucket: str, prefix: str, limit: Optional[int] = None) -> List[str]:
    s3 = _spaces_client()
    out: List[str] = []
    token: Optional[str] = None
    while True:
        kwargs: Dict[str, Any] = {"Bucket": bucket, "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token
        resp = s3.list_objects_v2(**kwargs)
        for obj in resp.get("Contents", []) or []:
            k = obj.get("Key")
            if k:
                out.append(k)
                if limit and len(out) >= limit:
                    return out
        if resp.get("IsTruncated"):
            token = resp.get("NextContinuationToken")
        else:
            break
    return out


def _get_text(bucket: str, key: str, max_bytes: int = 2_000_000) -> str:
    s3 = _spaces_client()
    resp = s3.get_object(Bucket=bucket, Key=key)
    raw = resp["Body"].read(max_bytes)
    return raw.decode("utf-8", errors="ignore")


def _pinecone_index(index_name: str):
    from pinecone import Pinecone

    s = get_settings()
    if not s.pinecone_api_key:
        raise SystemExit("PINECONE_API_KEY not configured")
    pc = Pinecone(api_key=s.pinecone_api_key)
    desc = pc.describe_index(index_name)
    return pc.Index(host=desc.host)


def _ensure_report_index_exists(index_name: str, text_field: str = "text") -> None:
    """
    Ensure a serverless integrated-embedding index exists for storing report docs.
    If it already exists, this is a no-op.
    """
    from pinecone import Pinecone, CloudProvider, AwsRegion, EmbedModel, IndexEmbed

    s = get_settings()
    if not s.pinecone_api_key:
        raise SystemExit("PINECONE_API_KEY not configured")

    pc = Pinecone(api_key=s.pinecone_api_key)
    try:
        pc.describe_index(index_name)
        return
    except Exception:
        pass

    region_norm = (s.pinecone_region or "us-east-1").strip().lower().replace("-", "_")
    aws_region = getattr(AwsRegion, region_norm.upper(), None)
    if aws_region is None:
        raise SystemExit(f"Unsupported AWS region for Pinecone SDK enum: {s.pinecone_region}")

    pc.create_index_for_model(
        name=index_name,
        cloud=CloudProvider.AWS,
        region=aws_region,
        embed=IndexEmbed(model=EmbedModel.Multilingual_E5_Large, field_map={"text": text_field}, metric="cosine"),
    )


def _build_record(*, doc_id: str, text: str, extra: Dict[str, Any]) -> Dict[str, Any]:
    # Pinecone Records API allows `_id` as identifier.
    record: Dict[str, Any] = {"_id": doc_id, "text": text}
    record.update(extra)
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Spaces report JSONs into Pinecone report indexes")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of files per section (debug)")
    args = parser.parse_args()

    s = get_settings()
    now = datetime.now(timezone.utc).isoformat()

    # ---------------------------------------------------------------------
    # 1) Client KB master reports -> Pinecone CLIENT_KB_REPORTS
    # ---------------------------------------------------------------------
    kb_reports_index = s.pinecone_client_kb_reports_index_name
    kb_reports_ns = s.pinecone_client_kb_reports_namespace
    kb_bucket = "mintleads-clients-kb"
    kb_prefix = "_client_kb_master/"

    _ensure_report_index_exists(kb_reports_index, text_field="text")
    kb_idx = _pinecone_index(kb_reports_index)

    kb_keys = _list_keys(kb_bucket, kb_prefix, limit=args.limit)
    kb_records: List[Dict[str, Any]] = []
    for key in kb_keys:
        if not key.endswith(".json"):
            continue
        raw = _get_text(kb_bucket, key)
        # store compact json string for consistent embeddings
        try:
            parsed = json.loads(raw)
            compact = json.dumps(parsed, separators=(",", ":"), ensure_ascii=False)
        except Exception:
            compact = raw.strip()
        doc_id = key  # preserve folder structure
        kb_records.append(
            _build_record(
                doc_id=doc_id,
                text=compact,
                extra={
                    "doc_kind": "client_kb_report",
                    "source_bucket": kb_bucket,
                    "source_key": key,
                    "ingested_at": now,
                },
            )
        )

    # ---------------------------------------------------------------------
    # 2) Agent reports -> Pinecone AGENT_REPORTS
    # ---------------------------------------------------------------------
    agent_reports_index = s.pinecone_agent_reports_index_name
    agent_reports_ns = s.pinecone_agent_reports_namespace
    agents_bucket = "mintleads-agents-store"

    _ensure_report_index_exists(agent_reports_index, text_field="text")
    agent_idx = _pinecone_index(agent_reports_index)

    agent_roots = ["agent-api-tokens.json", "agent_registry.json", "agents/"]
    agent_keys: List[str] = []
    for p in agent_roots:
        if p.endswith(".json"):
            agent_keys.append(p)
        else:
            agent_keys.extend(_list_keys(agents_bucket, p, limit=args.limit))

    agent_records: List[Dict[str, Any]] = []
    for key in agent_keys:
        if not key.endswith(".json"):
            continue
        raw = _get_text(agents_bucket, key)
        try:
            parsed = json.loads(raw)
            compact = json.dumps(parsed, separators=(",", ":"), ensure_ascii=False)
        except Exception:
            parsed = None
            compact = raw.strip()

        extra: Dict[str, Any] = {
            "doc_kind": "agent_report",
            "source_bucket": agents_bucket,
            "source_key": key,
            "ingested_at": now,
        }
        # If this is an agent doc, also project a few top-level fields (flat)
        if isinstance(parsed, dict) and "agent_uuid" in parsed:
            extra["agent_uuid"] = parsed.get("agent_uuid")
            extra["slug"] = parsed.get("slug")
            extra["agent_name"] = parsed.get("agent_name")
            extra["endpoint_url"] = parsed.get("endpoint_url")
            extra["region"] = parsed.get("region")
            extra["model"] = parsed.get("model")

        # Standardize doc IDs (user-facing)
        # - agent_registry.json (Spaces) -> agent-registry.json (Pinecone)
        doc_id = key
        if key == "agent_registry.json":
            doc_id = "agent-registry.json"

        agent_records.append(_build_record(doc_id=doc_id, text=compact, extra=extra))

    # ---------------------------------------------------------------------
    # Upsert (batch <= 96)
    # ---------------------------------------------------------------------
    def upsert_batches(idx, ns: str, records: List[Dict[str, Any]]) -> int:
        total = 0
        for i in range(0, len(records), 96):
            batch = records[i : i + 96]
            if args.dry_run:
                total += len(batch)
                continue
            idx.upsert_records(namespace=ns, records=batch)
            total += len(batch)
        return total

    kb_count = upsert_batches(kb_idx, kb_reports_ns, kb_records)
    agent_count = upsert_batches(agent_idx, agent_reports_ns, agent_records)

    print(
        json.dumps(
            {
                "dry_run": bool(args.dry_run),
                "kb_reports": {"index": kb_reports_index, "namespace": kb_reports_ns, "records": kb_count},
                "agent_reports": {"index": agent_reports_index, "namespace": agent_reports_ns, "records": agent_count},
                "verify": {
                    "kb_sample_ids": [r.get("_id") for r in kb_records[:10]],
                    "agent_sample_ids": [r.get("_id") for r in agent_records[:10]],
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()


