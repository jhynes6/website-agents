#!/usr/bin/env python3
"""
Generate Pinecone REPORTING namespace artifacts:

1) One per-client report record for every KB namespace (except REPORTING):
   - namespace: REPORTING
   - _id: clients/{client_slug}
   - file_key: client_kb_reports/{client_slug}.json
   - content_type: REPORTS
   - document_source: REPORTS
   - text: compact JSON of the client report payload

2) A summary.json record that aggregates health across namespaces:
   - namespace: REPORTING
   - _id: summary
   - file_key: client_kb_reports/summary.json
   - content_type: REPORTS
   - document_source: REPORTS

This mirrors the legacy DO-era `_client_kb_master/summary.json` shape as closely as possible,
but uses Pinecone namespace stats as the source of truth.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Allow running from repo root
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from app.clients.pinecone_client import pinecone_kb_client  # noqa: E402
from app.config import get_settings  # noqa: E402


def _pinecone_kb_index():
    from pinecone import Pinecone

    s = get_settings()
    if not s.pinecone_api_key:
        raise SystemExit("PINECONE_API_KEY not configured")
    pc = Pinecone(api_key=s.pinecone_api_key)
    desc = pc.describe_index(s.pinecone_kb_index_name)
    return pc.Index(host=desc.host)


def _namespace_stats() -> List[Tuple[str, int]]:
    """
    Return [(namespace, recordCount)] for all namespaces in the KB index.
    """
    idx = _pinecone_kb_index()
    stats = idx.describe_index_stats()
    namespaces = getattr(stats, "namespaces", None) or {}
    out: List[Tuple[str, int]] = []
    for ns, info in namespaces.items():
        # SDK v8: info has vector_count; MCP returns recordCount. Handle both.
        rc = getattr(info, "vector_count", None)
        if rc is None and isinstance(info, dict):
            rc = info.get("recordCount") or info.get("vector_count")
        out.append((str(ns), int(rc or 0)))
    out.sort(key=lambda x: x[0])
    return out


def _build_summary(ns_rows: List[Tuple[str, int]]) -> Dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat()
    client_rows = [(ns, c) for (ns, c) in ns_rows if ns != get_settings().pinecone_client_kb_reports_namespace]

    clients = len(client_rows)
    kbs_ok = sum(1 for _, c in client_rows if c > 0)
    kbs_missing = sum(1 for _, c in client_rows if c == 0)

    top_warnings = [{"client_slug": ns, "warning": "KB status: missing"} for (ns, c) in client_rows if c == 0][:25]

    return {
        "generated_at": generated_at,
        "totals": {
            "clients": clients,
            "kbs_ok": kbs_ok,
            "kbs_misconfigured": 0,
            "kbs_root": 0,
            "kbs_missing": kbs_missing,
            "clients_zero_files": 0,
            "clients_missing_intake": 0,
            "region_mismatches": 0,
        },
        "agents": {
            "total": 0,
            "by_region": {},
            "with_kb_region_mismatch": 0,
        },
        "top_warnings": top_warnings,
        "reports": {
            "client_audit_results_json": "reports/client_audit_results.json",
            "kb_inspect_dir": "reports/kb_inspect/",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Pinecone REPORTING client reports + summary")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Skip per-namespace enumeration (writes minimal placeholder client reports).",
    )
    parser.add_argument("--limit-clients", type=int, default=0, help="Optional limit for debugging (0 = no limit).")
    args = parser.parse_args()

    ns_rows = _namespace_stats()
    report_ns = get_settings().pinecone_client_kb_reports_namespace

    client_namespaces = [ns for (ns, _) in ns_rows if ns != report_ns]
    if args.limit_clients and args.limit_clients > 0:
        client_namespaces = client_namespaces[: args.limit_clients]

    wrote: List[Dict[str, str]] = []

    # Per-client reports
    for client_slug in client_namespaces:
        if not args.fast:
            report = pinecone_kb_client.build_onboarding_metadata_report(
                client_slug=client_slug,
                website_url=None,
                drive_url=None,
                wait_after_upsert_s=0.0,
            )
        else:
            # Lightweight report (still conforms to the same top-level shape)
            report = {
                "website_url": None,
                "drive_url": None,
                "client_slug": client_slug,
                "website_docs": {"total": 0, "by_content_type": {}},
                "intake_form_docs": 0,
                "drive_docs": {"total": 0, "by_content_type": {}},
                "page_breakdowns": {},
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "metadata": {"title": client_slug},
            }

        doc_id = f"clients/{client_slug}"
        file_key = f"client_kb_reports/{client_slug}.json"

        if args.dry_run:
            print(f"[dry-run] would upsert client report: clients/{client_slug}")
        else:
            pinecone_kb_client.upsert_client_report(client_slug=client_slug, report=report)
        wrote.append({"id": doc_id, "file_key": file_key})

    # Summary
    summary = _build_summary(ns_rows)
    summary_id = "summary"
    summary_file_key = "client_kb_reports/summary.json"
    if args.dry_run:
        print("[dry-run] would upsert summary: summary")
    else:
        pinecone_kb_client.upsert_reports_summary(summary=summary)

    # Verification footer
    sample = wrote[:10]
    print(
        json.dumps(
            {
                "verify": {
                    "client_reports_sample": sample,
                    "summary": {"id": summary_id, "file_key": summary_file_key},
                    "reporting_namespace": get_settings().pinecone_client_kb_reports_namespace,
                }
            },
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


