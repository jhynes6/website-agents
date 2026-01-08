"""
Bulk onboard clients from `backend/scripts/io/bulk_onboarding_run_file.csv` by calling the
same backend ingestion function used by the UI (`app.routes.create.create_chatbot`).

This performs:
- website crawl + markdown cleaning/categorization
- upload markdown artifacts to Supabase Storage
- vectorize/chunk/embed and upsert to Pinecone

Usage (repo root, venv active):
  backend/venv/bin/python backend/scripts/bulk_client_onboarding.py --all
  backend/venv/bin/python backend/scripts/bulk_client_onboarding.py --client-slug mintleads
"""

# NOTE: Kept as a separate file name for clarity. Implementation lives in ingest_to_supabase.py.
# This wrapper uses runpy to avoid import/package issues when executed as a standalone script.

from __future__ import annotations

import runpy
from pathlib import Path

if __name__ == "__main__":
    script = Path(__file__).with_name("ingest_to_supabase.py")
    runpy.run_path(str(script), run_name="__main__")


