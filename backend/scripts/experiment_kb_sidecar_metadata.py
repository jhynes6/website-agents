#!/usr/bin/env python3
"""
Experiment: try "sidecar metadata" ingestion with DigitalOcean Gradient Knowledge Bases.

Goal:
  Upload ONE document plus a sidecar file named "<doc>.metadata.json" into a *new* client folder
  in Spaces, then trigger a KB reindex, and check whether the metadata becomes filterable fields.

Important:
  - DigitalOcean Gradient KB docs do NOT clearly document sidecar metadata support.
  - This script helps you test the hypothesis quickly with real indexing.

What it does:
  1) Uploads:
       <client_slug>/<folder>/<doc_name>
       <client_slug>/<folder>/<doc_name>.metadata.json
  2) Ensures the KB has a Spaces data source pointing at that folder prefix
  3) Triggers a reindex by deleting/re-adding the data source (best-effort)

How to run (from repo root):
  backend/venv/bin/python backend/scripts/experiment_kb_sidecar_metadata.py \
    --client-slug sidecar-test \
    --kb-slug sidecar-test \
    --doc-name example.md \
    --folder sidecar_metadata_test

Then verify in OpenSearch Dashboards:
  - In the KB index (named by kb_uuid), find documents whose metadata.item_name == your doc.
  - Check if your sidecar keys appear as real fields anywhere, vs being indexed as a separate file.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional

import sys

# Add backend dir for imports when run from repo root
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from app.clients.digital_ocean_client import do_client  # noqa: E402
from app.clients.do_kb_registry import KnowledgeBaseRegistry  # noqa: E402
from app.config import get_settings  # noqa: E402


def _key(client_slug: str, folder: str, name: str) -> str:
    return f"{client_slug.strip().strip('/')}/{folder.strip().strip('/')}/{name}"


def _default_doc_body(client_slug: str) -> str:
    # We include YAML frontmatter too, since we already know YAML parsing works in our app-layer filters.
    return (
        "---\n"
        f"client_slug: {client_slug}\n"
        "content_type: sidecar_test\n"
        "document_source: sidecar_experiment\n"
        "---\n\n"
        "This is a single-document experiment to test whether DigitalOcean Knowledge Bases\n"
        "attach <doc>.metadata.json sidecar metadata as filterable fields.\n"
    )


def _default_sidecar_metadata(client_slug: str) -> Dict[str, Any]:
    # Flat JSON only (strings/numbers/bools)
    return {
        "client_slug": client_slug,
        "content_type": "sidecar_test",
        "document_source": "sidecar_experiment",
        "is_active": True,
        "version": 1,
    }


async def ensure_spaces_source(kb_uuid: str, prefix: str) -> None:
    settings = get_settings()
    bucket = settings.digitalocean_spaces_bucket
    if not bucket:
        raise SystemExit("DIGITALOCEAN_SPACES_BUCKET not configured")

    # Ensure source exists (and is correct), then reindex by replace (delete+add).
    # This is the most reliable path we currently have in this repo.
    ok, _created = await do_client.ensure_correct_spaces_source(
        kb_uuid=kb_uuid,
        bucket=bucket,
        expected_prefix=prefix,
    )
    if not ok:
        raise SystemExit("Failed to ensure Spaces data source for KB")

    # Trigger reindex by replacing the data source
    replaced = await do_client.trigger_reindexing(kb_uuid=kb_uuid, bucket=bucket, prefix=prefix)
    if not replaced:
        raise SystemExit("Failed to trigger reindexing")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Experiment: KB sidecar metadata ingestion")
    parser.add_argument("--client-slug", required=True, help="Client slug (creates a new folder under this slug)")
    parser.add_argument(
        "--kb-slug",
        required=True,
        help="KB name/slug to reindex (must already exist in DO; typically equals client slug)",
    )
    parser.add_argument("--kb-uuid", default=None, help="Optional KB UUID override (else looked up in do_kb_registry.json)")
    parser.add_argument(
        "--create-kb",
        action="store_true",
        default=True,
        help="Create the KB if it does not exist (default: true)",
    )
    parser.add_argument(
        "--no-create-kb",
        dest="create_kb",
        action="store_false",
        help="Do not create the KB if missing; error instead",
    )
    parser.add_argument("--folder", default="sidecar_metadata_test", help="Subfolder under client slug")
    parser.add_argument("--doc-name", default="example.md", help="Document filename (e.g. example.md)")
    parser.add_argument(
        "--doc-body-file",
        default=None,
        help="Optional path to a local file to upload as the document body",
    )
    args = parser.parse_args()

    settings = get_settings()

    if not do_client.s3_client:
        raise SystemExit("Spaces client not configured (DIGITALOCEAN_SPACES_KEY/SECRET/REGION missing?)")
    if not settings.digitalocean_spaces_bucket:
        raise SystemExit("DIGITALOCEAN_SPACES_BUCKET not configured")

    client_slug = args.client_slug.strip()
    kb_slug = args.kb_slug.strip()
    folder = args.folder.strip().strip("/")
    doc_name = args.doc_name.strip()

    kb_uuid: Optional[str] = args.kb_uuid
    if not kb_uuid:
        reg = KnowledgeBaseRegistry()
        rec = reg.get(kb_slug)
        kb_uuid = rec.kb_uuid if rec else None
    if not kb_uuid:
        # fallback: attempt fetch by name, optionally create
        kb = await do_client.get_knowledge_base_by_name(kb_slug)
        if not kb and args.create_kb:
            kb = await do_client.ensure_client_kb(kb_slug)
        kb_uuid = (kb or {}).get("uuid")
    if not kb_uuid:
        raise SystemExit(f"Could not resolve kb_uuid for kb-slug '{kb_slug}'")

    # Build content
    if args.doc_body_file:
        doc_body = Path(args.doc_body_file).read_text(encoding="utf-8")
    else:
        doc_body = _default_doc_body(client_slug)
    sidecar = _default_sidecar_metadata(client_slug)

    doc_key = _key(client_slug, folder, doc_name)
    sidecar_key = _key(client_slug, folder, f"{doc_name}.metadata.json")

    # Upload both
    ok1 = do_client.upload_file_content(doc_body, doc_key, content_type="text/markdown")
    ok2 = do_client.upload_file_content(json.dumps(sidecar, ensure_ascii=False, indent=2), sidecar_key, content_type="application/json")
    if not (ok1 and ok2):
        raise SystemExit("Failed uploading doc and/or sidecar to Spaces")

    prefix = f"{client_slug}/{folder}"
    await ensure_spaces_source(kb_uuid=kb_uuid, prefix=prefix)

    print("\n" + "=" * 100)
    print("Uploaded + triggered reindex")
    print("=" * 100)
    print(f"KB slug:  {kb_slug}")
    print(f"KB uuid:  {kb_uuid}")
    print(f"Bucket:   {settings.digitalocean_spaces_bucket}")
    print(f"Prefix:   {prefix}/")
    print(f"Doc key:  {doc_key}")
    print(f"Sidecar:  {sidecar_key}")
    print("\nNext: in OpenSearch Dashboards, search for metadata.item_name == "
          f"{json.dumps(doc_name)} and also look for your sidecar keys (content_type/document_source).")
    print("If the platform treats sidecar as a separate file, you’ll see a second file with item_name like "
          f"{json.dumps(doc_name + '.metadata.json')}.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())


