#!/usr/bin/env python3
"""
Generate a Markdown table of immediate subfolders in a given Google Drive
folder, and link any "client-materials" subfolder if present.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account

# Default parent folder provided by the user
PARENT_FOLDER_ID = "1fBj-xUtWCDntjpHRxM4K5R98lPOHALw9"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def resolve_credentials_path() -> Path:
    """
    Locate service_account.json. Checks (in order):
    1) GOOGLE_APPLICATION_CREDENTIALS env var (if set)
    2) ./service_account.json (repo root)
    3) ../service_account.json (when running from backend/)
    4) service_account.json at repo root relative to this file
    """
    candidates: List[Path] = []

    env_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if env_path:
        candidates.append(Path(env_path))

    candidates.extend(
        [
            Path("service_account.json"),
            Path("../service_account.json"),
            Path(__file__).resolve().parent.parent.parent / "service_account.json",
        ]
    )

    for path in candidates:
        if path and path.exists():
            return path

    raise FileNotFoundError(
        "service_account.json not found. Set GOOGLE_APPLICATION_CREDENTIALS or "
        "place service_account.json in the project root."
    )


def build_drive_service(creds_path: Path):
    creds = service_account.Credentials.from_service_account_file(
        str(creds_path), scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


def list_child_folders(drive, parent_id: str) -> List[Dict]:
    query = (
        f"'{parent_id}' in parents and "
        "mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    )

    folders: List[Dict] = []
    page_token: Optional[str] = None

    while True:
        resp = (
            drive.files()
            .list(
                q=query,
                fields="nextPageToken, files(id, name)",
                pageSize=1000,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                pageToken=page_token,
            )
            .execute()
        )
        folders.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return folders


def find_client_materials(drive, folder_id: str) -> Optional[Dict]:
    query = (
        f"'{folder_id}' in parents and "
        "mimeType = 'application/vnd.google-apps.folder' and "
        "name = 'client-materials' and trashed = false"
    )
    resp = (
        drive.files()
        .list(
            q=query,
            fields="files(id, name)",
            pageSize=1,
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
        )
        .execute()
    )
    files = resp.get("files", [])
    return files[0] if files else None


def link_for(fid: str) -> str:
    return f"https://drive.google.com/drive/folders/{fid}"


def print_table(rows: Iterable[Dict]) -> None:
    print("| folder name | folder link | client-materials |")
    print("| --- | --- | --- |")
    for row in rows:
        print(
            f"| {row['name']} | {row['folder_link']} | {row.get('client_materials_link', '')} |"
        )


def main():
    parent_id = PARENT_FOLDER_ID
    if len(sys.argv) > 1 and sys.argv[1].strip():
        parent_id = sys.argv[1].strip()

    try:
        creds_path = resolve_credentials_path()
        drive = build_drive_service(creds_path)

        children = list_child_folders(drive, parent_id)
        rows = []
        for child in sorted(children, key=lambda c: c["name"].lower()):
            cm = find_client_materials(drive, child["id"])
            rows.append(
                {
                    "name": child["name"],
                    "folder_link": link_for(child["id"]),
                    "client_materials_link": link_for(cm["id"]) if cm else "",
                }
            )

        print_table(rows)

    except FileNotFoundError as e:
        sys.stderr.write(f"{e}\n")
        sys.exit(1)
    except HttpError as e:
        sys.stderr.write(f"Google Drive API error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

