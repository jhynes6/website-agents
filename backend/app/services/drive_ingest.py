import asyncio
import logging
import os
import io
import tempfile
import re
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

INTAKE_PLACEHOLDER_PATTERNS = [
    "type your answer",
    "your answer",
    "insert answer",
    "add answer",
    "n/a",
    "na",
    "none",
    "tbd",
    "example answer",
    "placeholder",
]

INTAKE_ADMIN_SECTIONS = {
    "basic information",
    "contact information",
    "preferred methods of communication",
}

INTAKE_MARKETING_QUESTIONS: List[Tuple[str, str]] = [
    ("TARGETING", "Describe your top three target personas (clients):"),
    ("TARGETING", "Are there industries you won’t sell to?"),
    ("PRODUCTS_SERVICES", "What services do you sell to your top 3 target personas?"),
    ("OFFERS", "For each service, what are your top offers (packages/examples) that you would be willing to pitch them?"),
    ("PRICING", "What is your average order value? What are your “Starting At” costs for your services?"),
    ("DIFFERENTIATORS", "What makes you different from your competitors? What is your “special sauce”?"),
    ("PAIN_POINTS", "How would your customer describe their problem in their own words? What do you do to improve their business?"),
    ("CASE_STUDIES", "For each service, what are case studies or recent customer successes that you use to highlight your expertise in your field?"),
]


def _normalize_line(value: str) -> str:
    return " ".join((value or "").replace("\t", " ").strip().split())


def _strip_example_parentheticals(value: str) -> str:
    """
    Remove inline placeholder/example hints like "(ex: ...)" from form text.
    """
    text = value or ""
    # Remove parenthetical blocks that are examples/placeholders.
    text = re.sub(r"\((?:(?:ex(?:ample)?|e\.g)\s*[:.]?)[^)]*\)", "", text, flags=re.IGNORECASE)
    # Remove stray "ex:" fragments that may appear without a closing parenthesis.
    text = re.sub(r"\bex(?:ample)?\s*[:.]\s*$", "", text, flags=re.IGNORECASE)
    return _normalize_line(text)


def _strip_multiline_example_blocks(raw_text: str) -> str:
    """
    Remove example blocks that start with "(ex:" and may span multiple lines.
    """
    lines = (raw_text or "").splitlines()
    out: List[str] = []
    skipping = False
    marker = re.compile(r"\(\s*(?:ex(?:ample)?|e\.g)\s*[:.]", flags=re.IGNORECASE)

    for line in lines:
        cur = line or ""
        if not skipping:
            m = marker.search(cur)
            if not m:
                out.append(cur)
                continue

            # If example block closes on same line, remove just that segment.
            close_idx = cur.find(")", m.start())
            if close_idx != -1:
                cleaned = (cur[: m.start()] + cur[close_idx + 1 :]).rstrip()
                if cleaned.strip():
                    out.append(cleaned)
                continue

            # Start multiline skip; preserve any prefix before "(ex:"
            prefix = cur[: m.start()].rstrip()
            if prefix.strip():
                out.append(prefix)
            skipping = True
            continue

        # Currently skipping example block until the first closing paren.
        close_idx = cur.find(")")
        if close_idx == -1:
            continue
        suffix = cur[close_idx + 1 :].strip()
        if suffix:
            out.append(suffix)
        skipping = False

    return "\n".join(out)


def _strip_example_parentheticals_preserve(value: str) -> str:
    """Remove example hints while preserving markdown indentation/bullets."""
    text = value or ""
    text = re.sub(r"\((?:(?:ex(?:ample)?|e\.g)\s*[:.]?)[^)]*\)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bex(?:ample)?\s*[:.]\s*$", "", text, flags=re.IGNORECASE)
    # Collapse repeated spaces but keep leading indentation.
    lead = re.match(r"^\s*", text).group(0) if text else ""
    core = text[len(lead):]
    core = re.sub(r"[ \t]{2,}", " ", core).strip()
    return f"{lead}{core}".rstrip()


def _normalize_form_line(value: str) -> str:
    text = _strip_example_parentheticals(value)
    # Old formatted markdown may include bullets; strip marker for parsing.
    text = re.sub(r"^\s*[-*]\s+", "", text)
    return _normalize_line(text)


def _canonicalize(value: str) -> str:
    return _strip_example_parentheticals(value).lower().rstrip(":").rstrip("?")


def _is_placeholder_answer(value: str) -> bool:
    v = _canonicalize(value)
    if not v:
        return True
    if v in {"-", "--", "---"}:
        return True
    return any(p in v for p in INTAKE_PLACEHOLDER_PATTERNS)


def _is_suppression_list_line(value: str) -> bool:
    c = _canonicalize(value)
    return c in {
        "suppression list",
        "example suppression list",
        "if you have a list of companies that we should not be sending any emails to, please let us know",
        "one .xls or .csv file of these company’s domains needed. if domains are not provided, these contacts could be reached",
    }


def _format_intake_form_markdown(raw_text: str) -> str:
    """
    Convert intake form text to an LLM-friendly structure and strip placeholders.
    """
    cleaned_raw = _strip_multiline_example_blocks(raw_text or "")

    if "client_intake_form" in cleaned_raw.lower():
        cleaned_lines: List[str] = []
        prev_blank = False
        skip_suppression = False
        for line in cleaned_raw.splitlines():
            cleaned = _strip_example_parentheticals_preserve(line)
            probe = re.sub(r"^\s*[-*]\s+", "", cleaned).strip()
            if _canonicalize(probe).startswith("### "):
                skip_suppression = False
            if _is_suppression_list_line(probe):
                skip_suppression = True
                continue
            if skip_suppression:
                continue
            if _is_placeholder_answer(probe):
                continue
            is_blank = not cleaned.strip()
            if is_blank and prev_blank:
                continue
            cleaned_lines.append(cleaned)
            prev_blank = is_blank
        return "\n".join(cleaned_lines).strip()

    lines = [_normalize_form_line(l) for l in cleaned_raw.splitlines()]
    lines = [l for l in lines if l]
    if not lines:
        return ""

    canon_to_idx: Dict[str, int] = {}
    for i, line in enumerate(lines):
        canon_to_idx.setdefault(_canonicalize(line), i)

    # Build ADMIN section from specified source sections only.
    admin_entries: List[Tuple[str, str]] = []
    for i, line in enumerate(lines):
        if _canonicalize(line) not in INTAKE_ADMIN_SECTIONS:
            continue
        j = i + 1
        current_question: Optional[str] = None
        while j < len(lines):
            cur = lines[j]
            cur_canon = _canonicalize(cur)
            # Stop at next top-level section heading.
            if cur_canon in INTAKE_ADMIN_SECTIONS or cur_canon in {"campaign criteria", "targeting", "offerings", "cost of services", "service differentiation", "client pain points", "case studies and previous customer successes"}:
                break
            if cur.endswith(":") or cur.endswith("?"):
                current_question = cur
                admin_entries.append((current_question, ""))
                j += 1
                continue
            if current_question:
                if _is_placeholder_answer(cur):
                    j += 1
                    continue
                # Attach to latest question
                q, prev = admin_entries[-1]
                merged = f"{prev} {cur}".strip() if prev else cur
                admin_entries[-1] = (q, merged)
            j += 1

    # Build MARKETING section from explicit question mapping.
    marketing_answers: Dict[str, List[Tuple[str, str]]] = {
        "TARGETING": [],
        "PRODUCTS_SERVICES": [],
        "OFFERS": [],
        "CASE_STUDIES": [],
        "PRICING": [],
        "DIFFERENTIATORS": [],
        "PAIN_POINTS": [],
    }
    question_canons = [_canonicalize(q) for _, q in INTAKE_MARKETING_QUESTIONS]
    stop_heads = {
        "targeting",
        "offerings",
        "cost of services",
        "service differentiation",
        "client pain points",
        "case studies and previous customer successes",
        "basic information",
        "contact information",
        "preferred methods of communication",
    }
    for key, question in INTAKE_MARKETING_QUESTIONS:
        qcanon = _canonicalize(question)
        start = canon_to_idx.get(qcanon)
        answer = ""
        if start is not None:
            k = start + 1
            answer_lines: List[str] = []
            while k < len(lines):
                cur = lines[k]
                c = _canonicalize(cur)
                if c in question_canons or c in stop_heads:
                    break
                if _is_suppression_list_line(cur):
                    break
                if _is_placeholder_answer(cur):
                    k += 1
                    continue
                answer_lines.append(cur)
                k += 1
            answer = "\n".join(answer_lines).strip()
        marketing_answers[key].append((question, answer))

    out: List[str] = []
    out.append("# CLIENT_INTAKE_FORM")
    out.append("")
    out.append("## CLIENT_ADMIN_INFO")
    if admin_entries:
        for q, a in admin_entries:
            out.append(f"- {q}")
            if a:
                out.append(f"  - {a}")
    else:
        out.append("- No non-placeholder admin responses provided.")
    out.append("")
    out.append("## CLIENT_MARKETING_INFO")
    for section in ["TARGETING", "PRODUCTS_SERVICES", "OFFERS", "CASE_STUDIES", "PRICING", "DIFFERENTIATORS", "PAIN_POINTS"]:
        out.append(f"### {section}")
        for q, a in marketing_answers.get(section, []):
            out.append(f"- {q}")
            if a:
                out.append(f"  - {a}")
        out.append("")
    return "\n".join(out).strip()


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
            content = _format_intake_form_markdown(content)

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
