"""
Read client rows (client-slug, drive-folder, client-website) and attempt to
find an intake file in the Drive folder, extract the website domain, and write
an output CSV with the derived domain.
"""
import argparse
import csv
import logging
import re
import sys
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List

# Ensure we can import the Drive helper
REPO_ROOT = Path(__file__).resolve().parents[2]
CONTEXT_DIR = REPO_ROOT / "context"
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))
if str(CONTEXT_DIR) not in sys.path:
    sys.path.append(str(CONTEXT_DIR))

from context.google_drive_helper import GoogleDriveHelper  # type: ignore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("extract_intake_domains")

WEBSITE_KEYS = [r"website", r"company\s*website"]


def normalize_domain(raw: str) -> str:
    raw = raw.strip().lower()
    if raw.startswith(("http://", "https://")):
        raw = raw.split("://", 1)[1]
    if raw.startswith("www."):
        raw = raw[4:]
    raw = raw.split("/", 1)[0]
    return raw.rstrip(".,;:)")


def extract_domain_from_text(text: str) -> Optional[str]:
    # 1) key-based capture
    for line in text.splitlines():
        if any(re.search(k, line, re.IGNORECASE) for k in WEBSITE_KEYS):
            m = re.search(
                r"(https?://[^\s]+|www\.[^\s]+|[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
                line,
                re.IGNORECASE,
            )
            if m:
                return normalize_domain(m.group(1))
    # 2) fallback: first URL-ish token anywhere
    m = re.search(
        r"(https?://[^\s]+|www\.[^\s]+|[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
        text,
        re.IGNORECASE,
    )
    return normalize_domain(m.group(1)) if m else None


def folder_id_from_url(url: str) -> Optional[str]:
    m = re.search(r"/folders/([A-Za-z0-9_-]+)", url)
    return m.group(1) if m else None


def find_intake_file(helper: GoogleDriveHelper, folder_id: str) -> Optional[Dict[str, Any]]:
    """Find the first file in folder whose name contains 'intake' (case-insensitive)."""
    query = f"'{folder_id}' in parents and trashed=false and name contains 'intake'"
    try:
        results = helper.drive_service.files().list(
            q=query,
            pageSize=5,
            fields="files(id, name, mimeType)",
        ).execute()
        files = results.get("files", [])
        if not files:
            return None
        # Prefer Google Docs first for easier text export
        docs = [f for f in files if f.get("mimeType") == "application/vnd.google-apps.document"]
        return docs[0] if docs else files[0]
    except Exception as exc:  # pragma: no cover - network/API
        logger.error("Failed to search folder %s: %s", folder_id, exc)
        return None


def fetch_intake_text(helper: GoogleDriveHelper, file_id: str) -> Optional[str]:
    try:
        return helper.get_file_content(file_id)
    except Exception as exc:  # pragma: no cover - network/API
        logger.error("Failed to fetch file %s: %s", file_id, exc)
        return None


def process_row(helper: GoogleDriveHelper, row: Dict[str, str]) -> Tuple[str, Optional[str], str]:
    slug = (row.get("client-slug") or row.get("client_slug") or "").strip()
    drive_url = (row.get("drive-folder") or row.get("drive_folder") or "").strip()

    if not slug or not drive_url:
        return slug, None, "missing slug or drive-folder"

    folder_id = folder_id_from_url(drive_url)
    if not folder_id:
        return slug, None, "could not parse folder id"

    intake_file = find_intake_file(helper, folder_id)
    if not intake_file:
        return slug, None, "no intake file found"

    content = fetch_intake_text(helper, intake_file["id"])
    if not content:
        return slug, None, "could not read intake file"

    domain = extract_domain_from_text(content)
    if not domain:
        return slug, None, "website domain not found"

    return slug, domain, "ok"


def main():
    parser = argparse.ArgumentParser(description="Extract intake website domains from Drive folders.")
    parser.add_argument("--csv", required=True, help="Input CSV with columns: client-slug, drive-folder, client-website")
    default_output = Path(__file__).resolve().parent / "io" / "intake_domains.csv"
    parser.add_argument("--output", default=str(default_output), help="Output CSV path")
    parser.add_argument("--credentials", default="service_account.json", help="Path to service account JSON")
    args = parser.parse_args()

    helper = GoogleDriveHelper(credentials_file=args.credentials)

    input_path = Path(args.csv)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, str]] = []
    with input_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    results = []
    for row in rows:
        slug, domain, status = process_row(helper, row)
        results.append(
            {
                "client-slug": slug,
                "drive-folder": row.get("drive-folder") or row.get("drive_folder") or "",
                "original-client-website": row.get("client-website") or row.get("client_website") or "",
                "intake-domain": domain or "",
                "status": status,
            }
        )
        logger.info("[%s] status=%s domain=%s", slug, status, domain or "")

    fieldnames = [
        "client-slug",
        "drive-folder",
        "original-client-website",
        "intake-domain",
        "status",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    logger.info("Done. Wrote %s rows to %s", len(results), output_path)


if __name__ == "__main__":
    main()

