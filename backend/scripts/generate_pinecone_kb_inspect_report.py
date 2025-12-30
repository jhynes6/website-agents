#!/usr/bin/env python3
"""
Generate a DO-style kb_inspect (KB summary) report for a Pinecone-ingested client.

Why:
- For new clients that were never indexed in DigitalOcean KBs, we still want a
  consistent "KB summary" artifact for the UI/reporting layer.
- We store the report into Pinecone report namespace so it can be fetched like legacy:
  doc_id = "_client_kb_master/reports/kb_inspect/{client_slug}.json"
  index  = CLIENT_KB_REPORTS (default: client-knowledge-bases)
  ns     = CLIENT_KB_REPORTS_NAMESPACE (default: REPORTING)

This report is *Pinecone-era*:
- It uses Pinecone namespace stats for vector counts.
- It optionally uses Spaces (raw objects) for source/prefix visibility (not DO KBs).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend dir for imports when run from repo root
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from app.clients.digital_ocean_client import do_client  # noqa: E402
from app.config import get_settings  # noqa: E402


YAML_FM_RE = re.compile(r"(?s)^---\n(.*?)\n---\n")


def _parse_yaml_frontmatter(text: str) -> Dict[str, str]:
    m = YAML_FM_RE.match(text or "")
    if not m:
        return {}
    block = m.group(1)
    out: Dict[str, str] = {}
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        k, v = line.split(":", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _spaces_list_keys(bucket: str, prefix: str, limit: Optional[int] = None) -> List[str]:
    if not do_client.s3_client:
        raise RuntimeError("Spaces client not configured (DIGITALOCEAN_SPACES_KEY/SECRET)")
    out: List[str] = []
    token: Optional[str] = None
    while True:
        kwargs: Dict[str, Any] = {"Bucket": bucket, "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token
        resp = do_client.s3_client.list_objects_v2(**kwargs)
        for obj in resp.get("Contents", []) or []:
            k = obj.get("Key")
            if not k or k.endswith("/"):
                continue
            if k.endswith("metadata.json"):
                # skip old per-client metadata.json
                continue
            out.append(k)
            if limit and len(out) >= limit:
                return out
        if not resp.get("IsTruncated"):
            return out
        token = resp.get("NextContinuationToken")


def _spaces_head_text(bucket: str, key: str, max_bytes: int = 2048) -> str:
    if not do_client.s3_client:
        raise RuntimeError("Spaces client not configured (DIGITALOCEAN_SPACES_KEY/SECRET)")
    resp = do_client.s3_client.get_object(
        Bucket=bucket,
        Key=key,
        Range=f"bytes=0-{max_bytes-1}",
    )
    raw = resp["Body"].read()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="ignore")


def _pinecone_index(index_name: str):
    from pinecone import Pinecone

    s = get_settings()
    if not s.pinecone_api_key:
        raise SystemExit("PINECONE_API_KEY not configured")
    pc = Pinecone(api_key=s.pinecone_api_key)
    desc = pc.describe_index(index_name)
    return pc.Index(host=desc.host)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a Pinecone-era kb_inspect report for a client.")
    parser.add_argument("--client-slug", required=True, help="Client slug / Pinecone namespace.")
    parser.add_argument("--kb-index", default=None, help="KB Pinecone index (default env PINECONE_KB_INDEX).")
    parser.add_argument("--report-index", default=None, help="Report Pinecone index (default env CLIENT_KB_REPORTS).")
    parser.add_argument("--report-namespace", default=None, help="Report namespace (default env CLIENT_KB_REPORTS_NAMESPACE).")
    parser.add_argument("--spaces-bucket", default=None, help="Spaces bucket (default env DIGITALOCEAN_SPACES_BUCKET).")
    parser.add_argument("--spaces-prefix", default=None, help="Spaces prefix to scan (default '{client_slug}/').")
    parser.add_argument("--scan-files-limit", type=int, default=0, help="Limit Spaces files scanned (0 = no limit).")
    parser.add_argument("--dry-run", action="store_true", help="Do not upsert; just print JSON.")
    args = parser.parse_args()

    s = get_settings()
    client_slug = args.client_slug.strip()
    if not client_slug:
        raise SystemExit("--client-slug is required")

    kb_index_name = args.kb_index or s.pinecone_kb_index_name
    report_index_name = args.report_index or s.pinecone_client_kb_reports_index_name
    report_ns = args.report_namespace or s.pinecone_client_kb_reports_namespace

    # 1) Pinecone KB stats
    kb_idx = _pinecone_index(kb_index_name)
    stats = kb_idx.describe_index_stats()
    ns_stats = (stats.namespaces or {}).get(client_slug) if hasattr(stats, "namespaces") else None
    vector_count = int(getattr(ns_stats, "vector_count", 0) or 0) if ns_stats else 0

    # 2) Spaces (optional, but helps mirror DO-era "sources" and counts)
    spaces_bucket = args.spaces_bucket or s.digitalocean_spaces_bucket
    spaces_prefix = (args.spaces_prefix or f"{client_slug}/").lstrip("/")
    scan_limit = args.scan_files_limit if args.scan_files_limit and args.scan_files_limit > 0 else None

    sources: List[str] = []
    file_counts: Dict[str, Any] = {
        "spaces_prefix": spaces_prefix.rstrip("/") + "/",
        "total_files": 0,
        "content_types": {},
        "document_sources": {},
    }

    if spaces_bucket and do_client.s3_client:
        sources = [f"{spaces_bucket}/{spaces_prefix.rstrip('/')}/"]
        keys = _spaces_list_keys(spaces_bucket, spaces_prefix, limit=scan_limit)

        ct = defaultdict(int)
        ds = defaultdict(int)
        total_files = 0
        for k in keys:
            total_files += 1
            # Only inspect frontmatter from the first ~2KB to keep this cheap.
            head = _spaces_head_text(spaces_bucket, k, max_bytes=2048)
            fm = _parse_yaml_frontmatter(head)
            content_type = (fm.get("content_type") or "unknown").strip()
            document_source = (fm.get("document_source") or "").strip()
            if not document_source:
                # Best-effort infer from path: client_slug/<source>/...
                parts = k.split("/", 2)
                document_source = parts[1] if len(parts) >= 2 else "unknown"
            ct[content_type] += 1
            ds[document_source] += 1

        file_counts["total_files"] = total_files
        file_counts["content_types"] = dict(sorted(ct.items(), key=lambda x: (-x[1], x[0])))
        file_counts["document_sources"] = dict(sorted(ds.items(), key=lambda x: (-x[1], x[0])))

    now = datetime.now(timezone.utc).isoformat()

    # 3) Build DO-like kb_inspect report shape
    report: Dict[str, Any] = {
        "knowledge_base": {
            "uuid": f"pinecone:{kb_index_name}:{client_slug}",
            "name": client_slug,
            "created_at": now,
            "updated_at": now,
            "tags": ["client-docs", client_slug],
            # Keep a "region" field for parity; this is Pinecone region, not DO.
            "region": s.pinecone_region,
            "embedding_model_uuid": None,
            "project_id": None,
            "database_id": None,
            "last_indexing_job": {
                "uuid": None,
                "created_at": now,
                "updated_at": now,
                "started_at": now,
                "finished_at": now,
                "phase": "PINECONE_INGEST_COMPLETE" if vector_count > 0 else "PINECONE_NO_VECTORS",
                "status": "INDEX_JOB_STATUS_COMPLETED" if vector_count > 0 else "INDEX_JOB_STATUS_EMPTY",
                "indexed_item_count": str(vector_count),
                "is_report_available": True,
            },
        },
        "sources": sources,
        "status": {
            "is_correctly_configured": bool(vector_count > 0),
            "pointing_to_root": False,
        },
        # Extra Pinecone-era diagnostics (safe additions)
        "pinecone": {
            "kb_index": kb_index_name,
            "namespace": client_slug,
            "vector_count": vector_count,
        },
        "spaces": file_counts,
        "generated_at": now,
    }

    doc_id = f"_client_kb_master/reports/kb_inspect/{client_slug}.json"
    file_key = f"reports/kb_inspect/{client_slug}.json"

    if args.dry_run:
        print(json.dumps({"doc_id": doc_id, "index": report_index_name, "namespace": report_ns, "report": report}, indent=2))
        print(json.dumps({"verify": {"id": doc_id, "file_key": file_key, "namespace": report_ns}}, indent=2))
        return 0

    # 4) Upsert report doc into report namespace
    report_idx = _pinecone_index(report_index_name)
    compact = json.dumps(report, separators=(",", ":"), ensure_ascii=False)
    report_idx.upsert_records(
        namespace=report_ns,
        records=[
            {
                "_id": doc_id,
                "text": compact,
                "doc_kind": "kb_inspect_report",
                "client_slug": client_slug,
                "ingested_at": now,
            }
        ],
    )

    print(json.dumps({"upserted": True, "doc_id": doc_id, "index": report_index_name, "namespace": report_ns}, indent=2))
    print(json.dumps({"verify": {"id": doc_id, "file_key": file_key, "namespace": report_ns}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


