import asyncio
import logging
import os
import io
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from ..clients.llm import llm_client

# Optional PDF helpers
try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None

try:
    import pytesseract
    from PIL import Image  # noqa: WPS433
except ImportError:  # pragma: no cover
    pytesseract = None
    Image = None  # type: ignore

DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
]

DRIVE_CONTENT_SYSTEM_PROMPT = """
You are helping categorize document content based on the type of information in each document.

Categories and definitions:

- capabilities_overview: content that provides an overview of the company's capabilities
- case_studies: content with case studies detailing success stories or project examples
- brochures_newsletters: content with brochures or newsletters
- pitch_decks: content with pitch decks
- other: use this if you cannot confidently assign the content to one of the provided categories

Return ONLY the category name.
"""

DRIVE_VALID_CATEGORIES = [
    "capabilities_overview",
    "case_studies",
    "brochures_newsletters",
    "pitch_decks",
    "other",
]


def extract_drive_folder_id(raw_input: Optional[str]) -> Optional[str]:
    if not raw_input:
        return None
    value = raw_input.strip()
    if "folders/" in value:
        after = value.split("folders/", 1)[-1]
        return after.split("?")[0].split("/")[0]
    return value


def drive_service(credentials_path: Path):
    creds = service_account.Credentials.from_service_account_file(
        str(credentials_path),
        scopes=DRIVE_SCOPES,
    )
    return build("drive", "v3", credentials=creds)


def list_drive_files(drive, folder_id: str, recursive: bool = True) -> List[Dict[str, Any]]:
    """List all files in a folder (optionally recurse)."""
    items: List[Dict[str, Any]] = []
    queue: List[str] = [folder_id]
    visited = set()

    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)

        page_token = None
        query = f"'{current}' in parents and trashed=false"
        while True:
            resp = (
                drive.files()
                .list(
                    q=query,
                    fields="nextPageToken, files(id,name,mimeType,modifiedTime,size,webViewLink)",
                    pageToken=page_token,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                .execute()
            )
            for f in resp.get("files", []):
                mime = f.get("mimeType") or ""
                if recursive and mime == "application/vnd.google-apps.folder":
                    queue.append(f.get("id"))
                else:
                    items.append(f)
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
    return items


def download_drive_file_text(drive, file_meta: Dict[str, Any], logger: Optional[logging.Logger] = None) -> str:
    """Download file content as text when possible (ported from google_drive_helper)."""
    file_id = file_meta.get("id")
    mime_type = file_meta.get("mimeType") or ""
    name = file_meta.get("name") or ""
    if not file_id:
        return ""

    def log_info(msg: str) -> None:
        if logger:
            logger.info("[drive] %s", msg)

    try:
        # Google Docs
        if mime_type == "application/vnd.google-apps.document":
            log_info(f"doc -> text: {name}")
            request = drive.files().export_media(fileId=file_id, mimeType="text/plain")
            data = request.execute()
            return data.decode("utf-8")

        # Google Sheets
        if mime_type == "application/vnd.google-apps.spreadsheet":
            log_info(f"sheet -> csv: {name}")
            request = drive.files().export_media(fileId=file_id, mimeType="text/csv")
            data = request.execute()
            return data.decode("utf-8")

        # Google Slides
        if mime_type == "application/vnd.google-apps.presentation":
            log_info(f"slides -> text: {name}")
            request = drive.files().export_media(fileId=file_id, mimeType="text/plain")
            data = request.execute()
            return data.decode("utf-8")

        # PDFs
        if mime_type == "application/pdf":
            log_info(f"pdf -> text (pdfplumber/ocr): {name}")
            request = drive.files().get_media(fileId=file_id)
            data = request.execute()
            if not isinstance(data, (bytes, bytearray)):
                return ""
            return _extract_pdf_text(data, name, logger=logger)

        # Text files
        if mime_type.startswith("text/"):
            log_info(f"text file: {name}")
            request = drive.files().get_media(fileId=file_id)
            data = request.execute()
            return data.decode("utf-8")

        # Binary (pdf, images, pptx, etc.)
        log_info(f"binary download: {name} ({mime_type})")
        request = drive.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        binary_content = fh.getvalue()

        # Best-effort decode
        try:
            return binary_content.decode("utf-8")
        except UnicodeDecodeError:
            return ""

    except HttpError as exc:
        log_info(f"download error {file_id}: {exc}")
        return ""
    except Exception as exc:
        log_info(f"download unexpected {file_id}: {exc}")
        return ""


def _extract_pdf_text(file_bytes: bytes, name: str, logger: Optional[logging.Logger] = None) -> str:
    """Extract PDF text using pdfplumber and optional OCR fallback."""
    if not pdfplumber:
        if logger:
            logger.info("[drive] pdfplumber not available; skipping pdf extraction for %s", name)
        return ""

    texts: List[str] = []
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text_chunks: List[str] = []
                text = page.extract_text()
                if text:
                    page_text_chunks.append(text)

                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        rows = []
                        for row in table:
                            clean_row = [str(cell).strip() if cell else "" for cell in row]
                            rows.append(" | ".join(clean_row))
                        page_text_chunks.append("\n".join(rows))

                if not page_text_chunks and pytesseract and Image:
                    try:
                        img_obj = page.to_image(resolution=300)
                        pil_img = getattr(img_obj, "original", None)
                        if pil_img:
                            gray = pil_img.convert("L")
                            enhanced = Image.eval(gray, lambda x: 255 if x > 128 else 0)
                            ocr_text = pytesseract.image_to_string(enhanced)
                            if ocr_text.strip():
                                page_text_chunks.append(ocr_text.strip())
                    except Exception as ocr_exc:  # noqa: BLE001
                        if logger:
                            logger.info("[drive] ocr error on pdf page (%s): %s", name, ocr_exc)

                if page_text_chunks:
                    texts.append("\n\n".join(page_text_chunks))
    except Exception as exc:  # noqa: BLE001
        if logger:
            logger.info("[drive] pdf extract error %s: %s", name, exc)
        return ""

    return "\n\n---\n\n".join(texts)


async def categorize_drive_documents(documents: List[Dict[str, Any]]) -> None:
    """Categorize client_materials drive docs using LLM; intake_form stays as-is."""
    tasks = []
    targets = []
    for doc in documents:
        meta = doc.get("metadata", {}) or {}
        if meta.get("document_source") != "client_materials":
            continue
        title = meta.get("title") or "Untitled"
        content = meta.get("fullContent") or ""
        user_prompt = f"Filename: {title}\n\nContent (truncated): {content[:4000]}"
        tasks.append(
            llm_client.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": DRIVE_CONTENT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=20,
                top_p=1,
            )
        )
        targets.append(doc)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for doc, result in zip(targets, results):
        meta = doc.get("metadata", {}) or {}
        category = "other"
        if not isinstance(result, Exception):
            try:
                category_raw = (result.choices[0].message.content or "").strip().lower()
                if category_raw in DRIVE_VALID_CATEGORIES:
                    category = category_raw
            except Exception:
                category = "other"
        meta["content_type"] = category
        doc["metadata"] = meta


def build_drive_documents(
    folder_input: str,
    namespace: str,
    credentials_path: Path,
    logger: Optional[logging.Logger] = None,
    *,
    # Default to full content; callers can opt into truncation if they need lighter payloads.
    text_max_chars: Optional[int] = None,
    fullcontent_max_chars: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], List[Dict[str, Any]]]:
    """Fetch all files from a Drive folder and return documents ready for upsert."""
    folder_id = extract_drive_folder_id(folder_input)
    if not folder_id:
        raise ValueError("Invalid Google Drive folder input")

    if not credentials_path.exists():
        raise FileNotFoundError(f"service_account.json not found at {credentials_path}")

    drive = drive_service(credentials_path)
    files = list_drive_files(drive, folder_id)

    if logger:
        logger.info("[drive] files_to_process count=%s", len(files))

    documents: List[Dict[str, Any]] = []
    intake_count = 0

    for file_meta in files:
        name = file_meta.get("name") or "Untitled Drive File"
        file_id = file_meta.get("id")
        content = download_drive_file_text(drive, file_meta, logger=logger)
        doc_source = "intake_form" if "intake" in name.lower() else "client_materials"
        if doc_source == "intake_form":
            intake_count += 1

        view_url = file_meta.get("webViewLink") or f"https://drive.google.com/file/d/{file_id}/view"
        full_text = f"namespace:{namespace} {name}\n\n{content or ''}".strip()
        preview_text = full_text[:1000]
        doc_text = full_text if text_max_chars is None else full_text[: max(0, int(text_max_chars))]
        md_full = (content or "")
        md_full = md_full if fullcontent_max_chars is None else md_full[: max(0, int(fullcontent_max_chars))]
        
        # Use file_id to ensure uniqueness
        doc_id = f"drive_{file_id}"

        documents.append(
            {
                "id": doc_id,
                "content": {
                    # NOTE: Downstream behavior depends on this field:
                    # - When building `.md` files for Supabase Storage, callers should pass text_max_chars=None.
                    # - For lightweight previews (e.g., onboarding JSON manifests), keep defaults.
                    "text": doc_text,
                    # Kept for quick inspection / UIs that don't want megabytes of text
                    "preview": preview_text,
                    "url": view_url,
                    "title": name,
                    "description": "",
                },
                "metadata": {
                    "namespace": namespace,
                    "title": name,
                    "url": view_url,
                    "sourceURL": view_url,
                    # Store raw extracted text (unprefixed). This is mainly used for categorization/debugging.
                    "fullContent": md_full,
                    "document_source": doc_source,
                    "content_type": "intake_form" if doc_source == "intake_form" else "uncategorized",
                    "driveFileId": file_meta.get("id"),
                    "mimeType": file_meta.get("mimeType"),
                    "modifiedTime": file_meta.get("modifiedTime"),
                },
            }
        )

    summary = {
        "requestedFolder": folder_id,
        "filesFound": len(files),
        "intakeForms": intake_count,
        "documentsCreated": len(documents),
    }
    return documents, summary, files
