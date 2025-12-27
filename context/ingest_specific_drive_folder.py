#!/usr/bin/env python3
"""
Folder-Specific Google Drive Content Scraper

This script downloads and categorizes files from a SPECIFIC PUBLIC Google Drive folder 
and its subdirectories, saving them locally with LLM-based content categorization.
Works with publicly shared folders - no domain-wide delegation required.

Usage:
    python ingest_specific_drive_folder.py --folder-id 1ABC123...

Required:
    --folder-id: Google Drive folder ID to crawl (folder must be publicly accessible)

Optional:
    --credentials: Path to Google service account JSON file (default: ./service_account.json)
    --days-back: Number of days back to crawl modified files (default: 0=all files)
    --output-dir: Output directory for client materials (default: ./ingestion/client_ingestion_outputs)
    --no-llm-categories: Disable LLM categorization (LLM is enabled by default)

Note: The Google Drive folder must be shared as "Anyone with the link can view" for this to work.
"""


import os
import sys
import argparse
import logging
import json
import io
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
from typing import List, Optional, Set, Dict
from slugify import slugify

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from google.auth.transport.requests import Request

# PDF processing imports
import PyPDF2
from io import BytesIO
import pdfplumber
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
import tempfile
import time

# Import PDF processing methods (add current directory to path)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from pdf_process_gpt import process_pdf_with_gpt
from pdf_process_markitdown import process_pdf_with_markitdown, process_pdf_batch_markitdown

# Import Google Drive Helper for presentation conversion
try:
    from google_drive_helper import GoogleDriveHelper
    DRIVE_HELPER_AVAILABLE = True
except ImportError:
    DRIVE_HELPER_AVAILABLE = False
    # Logger will be initialized later, warning will be shown during processing if needed

# LLM-based content categorization system (same as website scraper)
CATEGORIZATION_SYSTEM_PROMPT = """
You are helping categorize document content based on the type of information in each document.

Categories and definitions:

- capabilities_overview: content that provides an overview of the company's capabilities
- case_studies: content with case studies detailing success stories or project examples
- brochures_newsletters: content with brochures or newsletters
- pitch_decks: content with pitch decks
- other: use this if you cannot confidently assign the content to one of the provided categories


Your output should contain only the category name with no other text.
"""

VALID_CATEGORIES = [
    'capabilities_overview', 'case_studies', 'brochures_newsletters', 'other', 'pitch_decks'
]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/presentations',
    'https://www.googleapis.com/auth/docs',
]

def get_credentials(delegated_user: str, credentials_file: str) -> service_account.Credentials:
    """Get delegated credentials for Google Drive API"""
    credentials = service_account.Credentials.from_service_account_file(
        credentials_file, scopes=SCOPES)
    delegated_credentials = credentials.with_subject(delegated_user)
    return delegated_credentials

def get_gdrive_url(file_id: str, mime_type: str = '') -> str:
    """Generate Google Drive URL for a file"""
    if mime_type == 'application/vnd.google-apps.document':
        url = f'https://docs.google.com/document/d/{file_id}/view'
    elif mime_type == 'application/vnd.google-apps.spreadsheet':
        url = f'https://docs.google.com/spreadsheets/d/{file_id}/view'
    elif mime_type == 'application/vnd.google-apps.presentation':
        url = f'https://docs.google.com/presentation/d/{file_id}/view'
    else:
        url = f'https://drive.google.com/file/d/{file_id}/view'
    return url

def categorize_single_document_with_llm(content: str, filename: str, client) -> str:
    """Categorize a single document using LLM based on its content"""
    try:
        # Limit content size for LLM processing (first 4000 chars)
        truncated_content = content[:4000] + "..." if len(content) > 4000 else content
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": CATEGORIZATION_SYSTEM_PROMPT},
                {"role": "user", "content": f"Categorize this document content. Filename: {filename}\n\nContent: {truncated_content}"}
            ],
            temperature=0.1,
            max_tokens=20,
            top_p=1
        )
        
        category = response.choices[0].message.content.strip().lower()
        
        if category not in VALID_CATEGORIES:
            logger.warning(f"⚠️  Invalid category '{category}' for {filename}, defaulting to 'other'")
            category = 'other'
            
        return category
        
    except Exception as e:
        logger.error(f"❌ Error categorizing {filename}: {e}")
        return 'other'

def categorize_document_simple(filename: str, content: str = "") -> str:
    """Simple keyword-based categorization as fallback"""
    filename_lower = filename.lower()
    content_lower = content.lower()
    
    # Check filename and content for keywords
    combined_text = f"{filename_lower} {content_lower}"
    
    if any(keyword in combined_text for keyword in ['case study', 'case-study', 'success story', 'portfolio']):
        return 'case_studies'
    elif any(keyword in combined_text for keyword in ['pitch deck', 'pitch-deck', 'presentation', 'slide deck']):
        return 'pitch_decks'
    elif any(keyword in combined_text for keyword in ['brochure', 'newsletter', 'flyer', 'leaflet']):
        return 'brochures_newsletters'
    elif any(keyword in combined_text for keyword in ['capabilities', 'capability', 'overview', 'services overview', 'what we do']):
        return 'capabilities_overview'
    else:
        return 'other'

class FolderSpecificDriveCrawler:
    def __init__(self, credentials_file: str, delegated_user: str, folder_id: str, 
                 days_back: int = 30, output_dir: str = "./ingestion/client_ingestion_outputs",
                 pdf_processor: str = "gpt", client_name: str = ""):
        self.credentials_file = credentials_file
        self.delegated_user = delegated_user
        self.folder_id = folder_id
        self.days_back = days_back
        self.output_dir = output_dir
        self.crawled_files = []
        self.failed_files = []  # Track files that failed processing
        self.pdf_temp_dir = None
        self.pdf_files_to_process = []  # List of (file_info, temp_path) tuples
        self.pdf_processor = pdf_processor  # 'gpt', 'markitdown', or 'pdfplumber'
        self.client_name = client_name  # Client name for metadata
        
        # Initialize services (public folder access - no delegation needed)
        self.credentials = service_account.Credentials.from_service_account_file(
            credentials_file,
            scopes=[
                'https://www.googleapis.com/auth/drive.readonly',
                'https://www.googleapis.com/auth/documents.readonly'
            ]
        )
        
        self.drive_service = build('drive', 'v3', credentials=self.credentials)
        self.docs_service = build('docs', 'v1', credentials=self.credentials)
        
        # Date threshold for filtering files
        self.date_threshold = datetime.now() - timedelta(days=days_back)
        
    def setup(self):
        """Initialize output directory"""
        logger.info(f"🔑 Setting up Google Drive service for public folder access")
        os.makedirs(self.output_dir, exist_ok=True)
        
    def get_folder_info(self, folder_id: str) -> Optional[dict]:
        """Get folder information"""
        try:
            folder = self.drive_service.files().get(
                fileId=folder_id,
                fields='id, name, mimeType, parents'
            ).execute()
            return folder
        except HttpError as e:
            logger.error(f"Error accessing folder {folder_id}: {e}")
            return None
            
    def list_files_in_folder(self, folder_id: str, recursive: bool = True) -> List[dict]:
        """List all files in a specific folder and optionally its subdirectories"""
        all_files = []
        folders_to_process = [folder_id]
        processed_folders = set()
        
        while folders_to_process:
            current_folder_id = folders_to_process.pop(0)
            
            if current_folder_id in processed_folders:
                continue
                
            processed_folders.add(current_folder_id)
            logger.info(f"📁 Crawling folder: {current_folder_id}")
            
            # Get folder info for logging
            folder_info = self.get_folder_info(current_folder_id)
            if folder_info:
                logger.info(f"📂 Folder name: {folder_info.get('name', 'Unknown')}")
            
            # Query for files in this specific folder
            page_token = None
            query = f"'{current_folder_id}' in parents and trashed=false"
            
            # Add date filter if specified
            if self.days_back > 0:
                date_str = self.date_threshold.isoformat() + 'Z'
                query += f" and modifiedTime > '{date_str}'"
            
            while True:
                try:
                    params = {
                        'q': query,
                        'fields': 'nextPageToken, files(id, name, mimeType, modifiedTime, createdTime, owners, size, parents, shortcutDetails(targetId,targetMimeType))',
                        'supportsAllDrives': True,
                        'includeItemsFromAllDrives': True
                    }
                    if page_token:
                        params['pageToken'] = page_token
                        
                    response = self.drive_service.files().list(**params).execute()
                    files = response.get('files', [])
                    
                    for file in files:
                        if file['mimeType'] == 'application/vnd.google-apps.folder':
                            # It's a subfolder - add to processing queue if recursive
                            if recursive:
                                folders_to_process.append(file['id'])
                                logger.info(f"📁 Found subfolder: {file['name']} ({file['id']})")
                        elif file['mimeType'] == 'application/vnd.google-apps.shortcut':
                            # Resolve shortcut to its target
                            shortcut = file.get('shortcutDetails', {}) or {}
                            target_id = shortcut.get('targetId')
                            target_mime = shortcut.get('targetMimeType')
                            if not target_id:
                                logger.warning(f"⚠️  Skipping Drive shortcut with no target: {file.get('name','(no name)')} ({file.get('id')})")
                                continue
                            try:
                                target_meta = self.drive_service.files().get(
                                    fileId=target_id,
                                    fields='id, name, mimeType, modifiedTime, createdTime, owners, size, parents',
                                    supportsAllDrives=True
                                ).execute()
                                # Preserve that this came via a shortcut
                                target_meta['shortcut'] = True
                                target_meta['shortcut_id'] = file.get('id')
                                # Use the shortcut's name if it differs (so user intent is visible)
                                if file.get('name') and file.get('name') != target_meta.get('name'):
                                    target_meta['name'] = file.get('name')
                                all_files.append(target_meta)
                                logger.info(f"🔗 Resolved shortcut → {target_meta.get('name')} [{target_meta.get('mimeType')}] ({target_id})")
                            except HttpError as e:
                                logger.warning(f"⚠️  Failed to resolve shortcut {file.get('id')}: {e}")
                                continue
                        else:
                            # It's a regular file - add to results
                            all_files.append(file)
                            logger.info(f"📄 Found file: {file['name']} ({file.get('size', 'N/A')} bytes)")
                    
                    page_token = response.get('nextPageToken')
                    if not page_token:
                        break
                        
                except HttpError as e:
                    logger.error(f"Error listing files in folder {current_folder_id}: {e}")
                    break
        
        return all_files
    
    def find_client_intake_files(self, folder_id: str) -> List[dict]:
        """Find Client Intake files in the main directory only (not subdirectories)"""
        intake_files = []
        
        try:
            # Query for files in main folder only with "Client Intake" in the name
            query = f"'{folder_id}' in parents and trashed=false and name contains 'Client Intake'"
            
            # Add date filter if specified
            if self.days_back > 0:
                date_str = self.date_threshold.isoformat() + 'Z'
                query += f" and modifiedTime > '{date_str}'"
            
            response = self.drive_service.files().list(
                q=query,
                fields='files(id, name, mimeType, modifiedTime, createdTime, owners, size, parents)',
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            files = response.get('files', [])
            
            for file in files:
                if file['mimeType'] == 'application/vnd.google-apps.document':
                    logger.info(f"📋 Found Client Intake file: {file['name']}")
                    intake_files.append(file)
                else:
                    logger.warning(f"⚠️  Client Intake file is not a Google Doc: {file['name']} ({file['mimeType']})")
            
        except HttpError as e:
            logger.error(f"Error finding Client Intake files: {e}")
        
        return intake_files
    
    
    def export_google_slides_as_pptx(self, file_id: str) -> bytes:
        """Export Google Slides as PowerPoint"""
        try:
            request = self.drive_service.files().export_media(
                fileId=file_id,
                mimeType='application/vnd.openxmlformats-officedocument.presentationml.presentation'
            )
            return request.execute()
        except HttpError as e:
            logger.error(f"Error exporting Google Slides {file_id}: {e}")
            raise

    def export_google_sheets_as_xlsx(self, file_id: str) -> bytes:
        """Export Google Sheets as Excel"""
        try:
            request = self.drive_service.files().export_media(
                fileId=file_id,
                mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            return request.execute()
        except HttpError as e:
            logger.error(f"Error exporting Google Sheets {file_id}: {e}")
            raise
    
    def get_document_text(self, doc_id: str) -> str:
        """Get all text from a Google Doc as plain text."""
        try:
            document = self.docs_service.documents().get(documentId=doc_id).execute()
            
            # Extract all text
            content = document.get('body', {}).get('content', [])
            full_text = []
            
            for element in content:
                # Handle paragraphs
                if 'paragraph' in element:
                    text = self._get_paragraph_text(element['paragraph'])
                    if text.strip():
                        full_text.append(text)
                
                # Handle tables
                elif 'table' in element:
                    table_text = self._get_table_text(element['table'])
                    if table_text.strip():
                        full_text.append(table_text)
                
                # Handle lists
                elif 'list' in element:
                    list_text = self._get_list_text(element['list'])
                    if list_text.strip():
                        full_text.append(list_text)
            
            # Join with double newlines for better separation
            return '\n\n'.join(full_text)
            
        except Exception as e:
            logger.error(f"Error getting document text: {str(e)}")
            return ""
    
    def _get_paragraph_text(self, paragraph: Dict) -> str:
        """Extract text from a paragraph element"""
        text = []
        for element in paragraph.get('elements', []):
            if 'textRun' in element:
                content = element['textRun'].get('content', '')
                # Preserve important whitespace
                if content.strip() or '\n' in content:
                    text.append(content)
        return ''.join(text)

    def _get_table_text(self, table: Dict) -> str:
        """Extract text from a table element"""
        rows = []
        for row in table.get('tableRows', []):
            cells = []
            for cell in row.get('tableCells', []):
                cell_text = []
                for content in cell.get('content', []):
                    if 'paragraph' in content:
                        text = self._get_paragraph_text(content['paragraph'])
                        if text.strip():
                            cell_text.append(text)
                cells.append(' '.join(cell_text))
            rows.append(' | '.join(filter(None, cells)))
        return '\n'.join(filter(None, rows))

    def _get_list_text(self, list_item: Dict) -> str:
        """Extract text from a list element"""
        items = []
        for item in list_item.get('listItems', []):
            if 'paragraph' in item:
                text = self._get_paragraph_text(item['paragraph'])
                if text.strip():
                    items.append(f"• {text}")
        return '\n'.join(items)

    def _download_and_process_file(self, file: Dict) -> str:
        """Download and extract content from a file based on its type"""
        try:
            mime_type = file['mimeType']
            file_name = file['name']
            
            # Handle Google Docs (text extraction)
            if mime_type == 'application/vnd.google-apps.document':
                return self.get_document_text(file['id'])
            
            # Handle Google Slides (use GoogleDriveHelper)
            elif mime_type == 'application/vnd.google-apps.presentation':
                logger.info(f"📊 Processing Google Slides: {file_name}")
                if DRIVE_HELPER_AVAILABLE:
                    try:
                        helper = GoogleDriveHelper(credentials_file=self.credentials_file)
                        content = helper.get_file_content(file['id'], convert_to_markdown=True)
                        return content
                    except Exception as e:
                        logger.error(f"❌ Error processing Google Slides with GoogleDriveHelper: {e}")
                        return None
                else:
                    logger.warning(f"⚠️  GoogleDriveHelper not available, saving for batch processing: {file_name}")
                    try:
                        pptx_content = self.export_google_slides_as_pptx(file['id'])
                        return self._save_file_for_markitdown_processing(file, pptx_content, '.pptx')
                    except HttpError as e:
                        if 'exportSizeLimitExceeded' in str(e):
                            logger.warning(f"⚠️  File too large to export as PPTX, trying plain text: {file_name}")
                            try:
                                request = self.drive_service.files().export_media(
                                    fileId=file['id'],
                                    mimeType='text/plain'
                                )
                                content = request.execute().decode('utf-8')
                                return content
                            except Exception as text_error:
                                logger.error(f"❌ Plain text export also failed: {text_error}")
                                logger.info(f"⚠️  Skipping large Google Slides file: {file_name}")
                                return None
                        else:
                            logger.error(f"❌ Error exporting Google Slides: {e}")
                            return None
            
            # Handle Google Sheets (export as XLSX and process with MarkItDown)
            elif mime_type == 'application/vnd.google-apps.spreadsheet':
                logger.info(f"📈 Processing Google Sheets: {file_name}")
                try:
                    # Try to export as XLSX first
                    xlsx_content = self.export_google_sheets_as_xlsx(file['id'])
                    return self._save_file_for_markitdown_processing(file, xlsx_content, '.xlsx')
                except HttpError as e:
                    if 'exportSizeLimitExceeded' in str(e):
                        logger.warning(f"⚠️  File too large to export as XLSX, trying CSV: {file_name}")
                        # Fallback to CSV export for large files
                        try:
                            request = self.drive_service.files().export_media(
                                fileId=file['id'],
                                mimeType='text/csv'
                            )
                            content = request.execute().decode('utf-8')
                            return content
                        except Exception as csv_error:
                            logger.error(f"❌ CSV export also failed: {csv_error}")
                            logger.info(f"⚠️  Skipping large Google Sheets file: {file_name}")
                            return None
                    else:
                        logger.error(f"❌ Error exporting Google Sheets: {e}")
                        return None
            
            # Handle plain text files (direct processing)
            elif mime_type in ['text/plain', 'text/markdown', 'text/html']:
                request = self.drive_service.files().get_media(fileId=file['id'])
                content = request.execute().decode('utf-8')
                return content
            
            # Handle PDFs - save for batch processing
            elif mime_type == 'application/pdf':
                return self._save_pdf_for_batch_processing(file)
            
            # Handle Microsoft Office presentations (PPTX, PPT) - use GoogleDriveHelper
            elif mime_type in [
                'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # .pptx
                'application/vnd.ms-powerpoint',  # .ppt
            ]:
                logger.info(f"📊 Processing PowerPoint file: {file_name}")
                if DRIVE_HELPER_AVAILABLE:
                    try:
                        helper = GoogleDriveHelper(credentials_file=self.credentials_file)
                        content = helper.get_file_content(file['id'], convert_to_markdown=True)
                        return content
                    except Exception as e:
                        logger.error(f"❌ Error processing PowerPoint with GoogleDriveHelper: {e}")
                        return None
                else:
                    logger.warning(f"⚠️  GoogleDriveHelper not available, saving for batch processing: {file_name}")
                    return self._save_file_for_markitdown_processing(file)
            
            # Handle Microsoft Office documents (DOCX, XLSX, DOC, XLS)
            elif mime_type in [
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
                'application/msword',  # .doc
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
                'application/vnd.ms-excel'  # .xls
            ]:
                logger.info(f"📄 Processing Office file: {file_name}")
                return self._save_file_for_markitdown_processing(file)
            
            # Handle images (MarkItDown can OCR)
            elif mime_type.startswith('image/') and mime_type in [
                'image/jpeg', 'image/png', 'image/gif', 'image/bmp'
            ]:
                logger.info(f"🖼️  Processing image (OCR): {file_name}")
                return self._save_file_for_markitdown_processing(file)
            
            # Handle audio files (MarkItDown can transcribe)
            elif mime_type in ['audio/mpeg', 'audio/wav', 'audio/mp4']:
                logger.info(f"🎵 Processing audio file (transcription): {file_name}")
                return self._save_file_for_markitdown_processing(file)
            
            # Handle archives (ZIP)
            elif mime_type == 'application/zip':
                logger.info(f"📦 Processing ZIP archive: {file_name}")
                return self._save_file_for_markitdown_processing(file)
            
            # Handle other text-based files
            elif mime_type in ['text/csv', 'application/json', 'text/xml', 'application/rtf']:
                logger.info(f"📝 Processing text-based file: {file_name}")
                return self._save_file_for_markitdown_processing(file)
            
            else:
                logger.warning(f"Unsupported file type {mime_type}: {file_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading file {file['name']}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def _save_file_for_markitdown_processing(self, file: Dict, file_content: bytes = None, extension: str = None) -> str:
        """Save any file to temp directory for later batch processing with MarkItDown
        
        Args:
            file: File metadata from Google Drive
            file_content: Optional pre-downloaded file content (for Google Workspace exports)
            extension: Optional file extension override (for Google Workspace exports)
        """
        try:
            # Create temp directory if it doesn't exist
            if self.pdf_temp_dir is None:
                self.pdf_temp_dir = tempfile.mkdtemp(prefix="drive_files_")
                logger.info(f"📁 Created temp directory for files: {self.pdf_temp_dir}")
            
            file_id = file['id']
            file_name = file['name']
            
            # Determine file extension
            if extension:
                file_ext = extension
            else:
                file_ext = os.path.splitext(file_name)[1] or '.bin'
            
            # Create sanitized filename
            safe_name = slugify(os.path.splitext(file_name)[0])[:100]
            temp_filename = f"{safe_name}_{file_id}{file_ext}"
            temp_path = os.path.join(self.pdf_temp_dir, temp_filename)
            
            # Download file if not provided
            if file_content is None:
                request = self.drive_service.files().get_media(fileId=file_id)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                fh.seek(0)
                file_content = fh.read()
            
            # Save to temp directory
            with open(temp_path, 'wb') as f:
                f.write(file_content)
            
            logger.info(f"📥 Saved for MarkItDown processing: {temp_filename}")
            
            # Track this file for batch processing (use tuple format for consistency)
            self.pdf_files_to_process.append((file, temp_path))
            
            # Return placeholder - actual content will be processed in batch
            return f"[File saved for MarkItDown processing: {file_name}]"
            
        except Exception as e:
            logger.error(f"Error saving file for processing: {str(e)}")
            return None

    def _save_pdf_for_batch_processing(self, file: Dict) -> str:
        """Save PDF file to temp directory for later batch processing with vectorize"""
        try:
            # Create temp directory if it doesn't exist
            if self.pdf_temp_dir is None:
                self.pdf_temp_dir = tempfile.mkdtemp(prefix="drive_pdfs_")
                logger.info(f"📁 Created temp directory for PDFs: {self.pdf_temp_dir}")
            
            # Download the PDF file
            file_id = file['id']
            file_name = file['name']
            temp_path = os.path.join(self.pdf_temp_dir, file_name)
            
            request = self.drive_service.files().get_media(fileId=file_id)
            file_content = request.execute()
            
            with open(temp_path, 'wb') as f:
                f.write(file_content)
                
            logger.info(f"📄 Saved PDF for batch processing: {file_name}")
            
            # Add to processing queue
            self.pdf_files_to_process.append((file, temp_path))
            
            # Return placeholder text - will be replaced after vectorize processing
            return f"[PDF_PLACEHOLDER_{file_id}]"
                
        except Exception as e:
            logger.error(f"Error saving PDF {file['name']}: {str(e)}")
            return None

    def _extract_pdf_text(self, file_id: str) -> str:
        """Extract text, tables, and images from a PDF file"""
        try:
            # Download the PDF file
            request = self.drive_service.files().get_media(fileId=file_id)
            file_content = request.execute()
            
            text_content = []
            
            # Process with pdfplumber for text and tables
            with pdfplumber.open(BytesIO(file_content)) as pdf:
                for page in pdf.pages:
                    # Extract regular text
                    text = page.extract_text()
                    if text:
                        text_content.append(text)
                    
                    # Extract tables
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            table_text = self._format_table(table)
                            text_content.append(table_text)
                    
                    # Check if page needs OCR
                    if not text and not tables:
                        ocr_text = self._process_page_with_ocr(page)
                        if ocr_text:
                            text_content.append(ocr_text)
            
            return '\n\n'.join(text_content)
            
        except Exception as e:
            logger.error(f"Error extracting PDF text: {str(e)}")
            return None

    def _format_table(self, table: List[List[str]]) -> str:
        """Format a table into a readable string"""
        # Remove empty cells and clean whitespace
        cleaned_table = [
            [str(cell).strip() if cell else '' for cell in row]
            for row in table
        ]
        
        # Get maximum width for each column
        col_widths = [
            max(len(str(row[i])) for row in cleaned_table)
            for i in range(len(cleaned_table[0]))
        ]
        
        # Format rows with proper spacing
        formatted_rows = []
        for row in cleaned_table:
            formatted_row = " | ".join(
                str(cell).ljust(width) for cell, width in zip(row, col_widths)
            )
            formatted_rows.append(formatted_row)
        
        # Add separator line after header
        separator = "-" * len(formatted_rows[0])
        formatted_rows.insert(1, separator)
        
        return "\n".join(formatted_rows)

    def _process_page_with_ocr(self, page) -> str:
        """Process a page with OCR to extract text from images"""
        try:
            # Use pdfplumber's built-in capability to get a PIL Image
            # Increase resolution for potentially better OCR quality
            page_image = page.to_image(resolution=300) 
            
            # pdfplumber's to_image returns an object with a .original attribute holding the PIL Image
            pil_image = page_image.original 

            if not pil_image:
                logger.warning(f"Could not convert page {page.page_number} to image for OCR.")
                return ""

            # Enhance the PIL image directly
            enhanced = self._enhance_image(pil_image)
            
            # Perform OCR on the enhanced PIL image
            text = pytesseract.image_to_string(enhanced)
            
            return text.strip() # Return stripped text
            
        except Exception as e:
            logger.error(f"Error in OCR processing for page {page.page_number}: {str(e)}", exc_info=True)
            return ""

    def _enhance_image(self, image: Image) -> Image:
        """Enhance image for better OCR results"""
        # Convert to grayscale
        image = image.convert('L')
        
        # Increase contrast
        enhanced = Image.eval(image, lambda x: 255 if x > 128 else 0)
        
        return enhanced

    def _batch_process_pdfs_with_gpt(self, openai_client) -> Dict[str, str]:
        """Process all collected PDFs using GPT-4o image analysis"""
        if not self.pdf_files_to_process:
            return {}
            
        logger.info(f"🚀 Starting batch PDF processing with GPT-4o for {len(self.pdf_files_to_process)} PDFs")
        
        if not openai_client and self.pdf_processor == 'gpt':
            logger.warning("⚠️  No OpenAI client available, falling back to pdfplumber for PDF processing")
            return self._fallback_pdf_processing()
        
        extracted_content = {}
        
        for file_info, temp_path in self.pdf_files_to_process:
            file_name = file_info['name']
            file_id = file_info['id']
            
            try:
                logger.info(f"🤖 Processing PDF with GPT-4o: {file_name}")
                
                # Process with GPT-4o
                result = process_pdf_with_gpt(temp_path, openai_client, include_first_page=False)
                
                if result['success']:
                    # Combine extracted text and GPT analysis
                    combined_content = []
                    
                    # Add extracted text if available
                    if result['extracted_text'].strip():
                        combined_content.append("## Extracted Text\n")
                        cleaned_text = result['extracted_text'].replace('\f', '\n\n---\n\n')
                        combined_content.append(cleaned_text)
                    
                    # Add GPT-4o page analysis
                    if result['pages_description']:
                        combined_content.append("\n\n## LLM Page Analysis\n")
                        for i, description in enumerate(result['pages_description'], 1):
                            combined_content.append(f"\n### Page {i + 1}\n")
                            combined_content.append(description)
                            combined_content.append("\n---\n")
                    
                    extracted_content[file_id] = '\n'.join(combined_content)
                    logger.info(f"✅ GPT processing completed: {file_name} ({result['pages_analyzed']} pages analyzed)")
                    
                else:
                    logger.error(f"❌ GPT processing failed for {file_name}: {result.get('error', 'Unknown error')}")
                    # Try fallback processing
                    fallback_content = self._extract_pdf_with_fallback(file_id)
                    if fallback_content:
                        extracted_content[file_id] = fallback_content
                        logger.info(f"✅ Fallback processing successful for {file_name}")
                    
            except Exception as e:
                logger.error(f"❌ Error processing {file_name} with GPT: {e}")
                # Try fallback processing
                try:
                    fallback_content = self._extract_pdf_with_fallback(file_id)
                    if fallback_content:
                        extracted_content[file_id] = fallback_content
                        logger.info(f"✅ Fallback processing successful for {file_name}")
                except Exception as fallback_error:
                    logger.error(f"❌ Fallback processing also failed for {file_name}: {fallback_error}")
        
        logger.info(f"🎉 PDF batch processing completed: {len(extracted_content)}/{len(self.pdf_files_to_process)} successful")
        return extracted_content

    def _batch_process_pdfs_with_markitdown(self) -> Dict[str, str]:
        """Process all collected files using MarkItDown (PDFs, Office docs, images, audio, etc.)"""
        if not self.pdf_files_to_process:
            return {}
            
        # Count different file types
        file_types = {}
        for item in self.pdf_files_to_process:
            if isinstance(item, tuple):
                file_meta, _ = item
                mime = file_meta.get('mimeType', 'unknown')
            else:
                mime = item.get('mime_type', 'unknown')
            file_types[mime] = file_types.get(mime, 0) + 1
        
        logger.info(f"🚀 Starting batch processing with MarkItDown for {len(self.pdf_files_to_process)} files:")
        for mime, count in file_types.items():
            logger.info(f"   • {mime}: {count} file(s)")
        
        try:
            extracted_content = process_pdf_batch_markitdown(self.pdf_files_to_process)
            return extracted_content
        except Exception as e:
            logger.error(f"❌ MarkItDown batch processing failed: {e}")
            logger.warning("⚠️  Falling back to pdfplumber for PDF files")
            return self._fallback_pdf_processing()
    
    def _fallback_pdf_processing(self) -> Dict[str, str]:
        """Fallback PDF processing using pdfplumber if other methods fail"""
        logger.info("🔄 Using fallback pdfplumber processing for PDFs...")
        extracted_content = {}
        
        for file_info, temp_path in self.pdf_files_to_process:
            try:
                file_id = file_info['id']
                # Read the temporary file and process with pdfplumber
                with open(temp_path, 'rb') as f:
                    file_content = f.read()
                
                text_content = []
                with pdfplumber.open(BytesIO(file_content)) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            text_content.append(text)
                
                if text_content:
                    extracted_content[file_id] = '\n\n'.join(text_content)
                    logger.info(f"✅ Fallback processing completed: {file_info['name']}")
                    
            except Exception as e:
                logger.error(f"❌ Fallback processing failed for {file_info['name']}: {e}")
        
        return extracted_content

    def _extract_pdf_with_fallback(self, file_id: str) -> str:
        """Extract content from a specific PDF using fallback method"""
        for file_info, temp_path in self.pdf_files_to_process:
            if file_info['id'] == file_id:
                try:
                    with open(temp_path, 'rb') as f:
                        file_content = f.read()
                    
                    text_content = []
                    with pdfplumber.open(BytesIO(file_content)) as pdf:
                        for page in pdf.pages:
                            text = page.extract_text()
                            if text:
                                text_content.append(text)
                    
                    return '\n\n'.join(text_content) if text_content else ""
                except Exception as e:
                    logger.error(f"❌ Fallback extraction failed: {e}")
                    return ""
        return ""

    def _cleanup_temp_files(self):
        """Clean up temporary PDF files"""
        if self.pdf_temp_dir and os.path.exists(self.pdf_temp_dir):
            try:
                shutil.rmtree(self.pdf_temp_dir)
                logger.info(f"🧹 Cleaned up temp directory: {self.pdf_temp_dir}")
            except Exception as e:
                logger.warning(f"⚠️  Could not clean up temp directory: {e}")
    
    def is_supported_file_type(self, mime_type: str, file_name: str) -> bool:
        """Check if file type is supported for processing (MarkItDown-compatible)"""
        supported_mime_types = [
            # Documents
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # .pptx
            'application/vnd.ms-powerpoint',  # .ppt
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
            'application/vnd.ms-excel',  # .xls
            
            # Text-based formats
            'text/plain',
            'text/markdown',
            'text/html',
            'text/xml',
            'application/json',
            'text/csv',
            
            # Google Workspace files
            'application/vnd.google-apps.document',
            'application/vnd.google-apps.presentation',
            'application/vnd.google-apps.spreadsheet',
            
            # RTF
            'application/rtf',
            
            # Images (MarkItDown can OCR these)
            'image/jpeg',
            'image/png',
            'image/gif',
            'image/bmp',
            
            # Audio (MarkItDown can transcribe)
            'audio/mpeg',  # .mp3
            'audio/wav',
            'audio/mp4',  # .m4a
            
            # Archives
            'application/zip'
        ]
        
        supported_extensions = [
            # Documents
            '.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx',
            # Text
            '.txt', '.md', '.html', '.xml', '.json', '.csv',
            # Images
            '.jpg', '.jpeg', '.png', '.gif', '.bmp',
            # Audio
            '.mp3', '.wav', '.m4a',
            # Archives
            '.zip',
            # Other
            '.rtf'
        ]
        
        mime_supported = any(mime_type.startswith(supported) or mime_type == supported 
                           for supported in supported_mime_types)
        extension_supported = any(file_name.lower().endswith(ext) for ext in supported_extensions)
        
        return mime_supported or extension_supported
    
    def crawl_and_save_locally(self, use_llm_categories: bool = False):
        """Crawl folder and save files locally with metadata"""
        logger.info(f"🚀 Starting folder-specific crawl of: {self.folder_id}")
        
        # Create output directories
        client_materials_dir = os.path.join(self.output_dir, "client_materials")
        client_intake_dir = os.path.join(self.output_dir, "client_intake_form")
        os.makedirs(client_materials_dir, exist_ok=True)
        os.makedirs(client_intake_dir, exist_ok=True)
        
        # First, look for Client Intake form in the main directory (not subdirectories)
        intake_files = self.find_client_intake_files(self.folder_id)
        
        # Then get all other files from the folder and subfolders
        files = self.list_files_in_folder(self.folder_id, recursive=True)
        logger.info(f"📊 Found {len(files)} total files to process")
        logger.info(f"📋 Found {len(intake_files)} Client Intake files")
        
        # Filter to supported file types
        supported_files = [f for f in files if self.is_supported_file_type(f['mimeType'], f['name'])]
        logger.info(f"📋 {len(supported_files)} files are supported for processing")
        
        # Setup LLM client for both categorization and PDF processing
        openai_client = None
        try:
            load_dotenv()
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                # Use regular OpenAI client (not AsyncOpenAI) for PDF processing compatibility
                from openai import OpenAI
                openai_client = OpenAI(api_key=api_key)
                
                if use_llm_categories:
                    logger.info("🤖 LLM categorization and GPT PDF processing enabled")
                else:
                    logger.info("🤖 GPT PDF processing enabled (categorization disabled)")
            else:
                logger.warning("⚠️  OPENAI_API_KEY not found")
                if use_llm_categories:
                    logger.warning("⚠️  Using simple categorization")
                logger.warning("⚠️  PDF processing will fall back to pdfplumber")
        except Exception as e:
            logger.error(f"❌ Failed to initialize OpenAI client: {e}")
            if use_llm_categories:
                logger.warning("⚠️  Falling back to simple categorization")
            logger.warning("⚠️  PDF processing will fall back to pdfplumber")
        
        # Phase 1: Process Client Intake files separately
        intake_processed_count = 0
        if intake_files:
            logger.info(f"\n📋 PHASE 1: Processing {len(intake_files)} Client Intake files...")
            for file in intake_files:
                try:
                    file_id = file['id']
                    name = file['name']
                    mime_type = file['mimeType']
                    
                    logger.info(f"📋 Processing Client Intake: {name}")
                    
                    # Extract content (should be Google Doc)
                    if mime_type == 'application/vnd.google-apps.document':
                        file_content = self.get_document_text(file_id)
                    else:
                        logger.warning(f"⚠️  Client Intake file is not a Google Doc, skipping: {name}")
                        continue
                    
                    if not file_content:
                        logger.warning(f"❌ Failed to extract content from Client Intake: {name}")
                        continue
                    
                    # Special metadata for Client Intake files
                    intake_metadata = {
                        'source': 'client_intake',
                        'content_type': 'client_intake',
                        'client_name': self.client_name,
                        'id': file_id,
                        'name': name,
                        'title': name,
                        'created_at': file.get('createdTime', 'N/A'),
                        'last_updated': file.get('modifiedTime', 'N/A'),
                        'owners': ', '.join([owner.get('displayName', owner.get('emailAddress', 'Unknown')) 
                                           for owner in file.get('owners', [])]),
                        'size': file.get('size', 'N/A'),
                        'url': get_gdrive_url(file_id, mime_type),
                        'folder_id': self.folder_id,
                        'mime_type': mime_type,
                        'scraped_time': datetime.now().isoformat(),
                        'word_count': len(file_content.split()) if file_content else 0
                    }
                    
                    # Save to client_intake_form directory
                    safe_name = slugify(os.path.splitext(name)[0])
                    final_filename = f"client_intake_{safe_name}.md"
                    final_file_path = os.path.join(client_intake_dir, final_filename)
                    
                    # Save extracted content
                    with open(final_file_path, 'w', encoding='utf-8') as f:
                        f.write(file_content)
                    
                    # Save metadata
                    metadata_file_path = final_file_path + '.metadata.json'
                    with open(metadata_file_path, 'w') as f:
                        json.dump(intake_metadata, f, indent=2)
                    
                    intake_processed_count += 1
                    logger.info(f"📋 ✅ Client Intake saved: {name} → {final_filename} ({intake_processed_count}/{len(intake_files)})")
                    
                    # Add to crawled files list for reporting
                    self.crawled_files.append({
                        'name': name,
                        'final_filename': final_filename,
                        'id': file_id,
                        'size': file.get('size', 'N/A'),
                        'mime_type': mime_type,
                        'content_type': 'client_intake',
                        'url': get_gdrive_url(file_id, mime_type),
                        'word_count': intake_metadata['word_count'],
                        'special_category': 'client_intake'
                    })
                    
                except Exception as e:
                    logger.error(f"❌ Error processing Client Intake {file.get('name', 'unknown')}: {e}")
                    # Track failed file
                    self.failed_files.append({
                        'name': file.get('name', 'unknown'),
                        'id': file.get('id', 'unknown'),
                        'mime_type': file.get('mimeType', 'unknown'),
                        'size': file.get('size', 'N/A'),
                        'url': get_gdrive_url(file.get('id', ''), file.get('mimeType', '')),
                        'error': str(e),
                        'error_type': type(e).__name__,
                        'file_category': 'client_intake',
                        'timestamp': datetime.now().isoformat()
                    })
        
        # Filter out intake files from regular processing to avoid duplicates
        intake_file_ids = {f['id'] for f in intake_files}
        regular_files = [f for f in files if f['id'] not in intake_file_ids]
        
        # Also filter by name to catch any missed intake files
        regular_files = [f for f in regular_files if 'client intake' not in f['name'].lower()]
        
        # Filter to supported file types
        supported_files = [f for f in regular_files if self.is_supported_file_type(f['mimeType'], f['name'])]
        logger.info(f"📋 {len(supported_files)} regular files are supported for processing (Client Intake files excluded)")
        
        # Phase 2: Process regular client materials files
        processed_count = 0
        error_count = 0
        
        if supported_files:
            logger.info(f"\n📄 PHASE 2: Processing {len(supported_files)} regular client materials...")
        
        for file in supported_files:
            try:
                file_id = file['id']
                name = file['name']
                mime_type = file['mimeType']
                
                logger.info(f"📄 Processing: {name}")
                
                # Extract content using the enhanced processing methods
                file_content = self._download_and_process_file(file)
                
                if not file_content:
                    logger.warning(f"❌ Failed to extract content from: {name}")
                    error_count += 1
                    # Track failed file
                    self.failed_files.append({
                        'name': name,
                        'id': file_id,
                        'mime_type': mime_type,
                        'size': file.get('size', 'N/A'),
                        'url': get_gdrive_url(file_id, mime_type),
                        'error': 'Failed to extract content (returned None)',
                        'error_type': 'ContentExtractionError',
                        'file_category': 'client_materials',
                        'timestamp': datetime.now().isoformat()
                    })
                    continue
                
                # Categorize content
                if openai_client and file_content:
                    content_type = categorize_single_document_with_llm(file_content, name, openai_client)
                else:
                    content_type = categorize_document_simple(name, file_content)
                
                # Prepare comprehensive metadata
                file_metadata = {
                    'source': 'client_materials',
                    'content_type': content_type,
                    'client_name': self.client_name,
                    'id': file_id,
                    'name': name,
                    'title': name,
                    'created_at': file.get('createdTime', 'N/A'),
                    'last_updated': file.get('modifiedTime', 'N/A'),
                    'owners': ', '.join([owner.get('displayName', owner.get('emailAddress', 'Unknown')) 
                                       for owner in file.get('owners', [])]),
                    'size': file.get('size', 'N/A'),
                    'url': get_gdrive_url(file_id, mime_type),
                    'folder_id': self.folder_id,
                    'mime_type': mime_type,
                    'scraped_time': datetime.now().isoformat(),
                    'word_count': len(file_content.split()) if file_content else 0
                }
                
                # Create final filename with category prefix for organization
                safe_name = slugify(os.path.splitext(name)[0])
                file_extension = ".md"  # Save extracted content as markdown
                final_filename = f"{content_type}_{safe_name}{file_extension}"
                final_file_path = os.path.join(client_materials_dir, final_filename)
                
                # Save extracted content as markdown file
                with open(final_file_path, 'w', encoding='utf-8') as f:
                    f.write(file_content)
                
                # Save metadata as JSON sidecar file
                metadata_file_path = final_file_path + '.metadata.json'
                with open(metadata_file_path, 'w') as f:
                    json.dump(file_metadata, f, indent=2)
                
                processed_count += 1
                logger.info(f"✅ Successfully processed: {name} → {final_filename} [{content_type}] ({processed_count}/{len(supported_files)})")
                
                # Add to crawled files list for reporting
                self.crawled_files.append({
                    'name': name,
                    'final_filename': final_filename,
                    'id': file_id,
                    'size': file.get('size', 'N/A'),
                    'mime_type': mime_type,
                    'content_type': content_type,
                    'url': get_gdrive_url(file_id, mime_type),
                    'word_count': file_metadata['word_count']
                })
                
            except Exception as e:
                logger.error(f"❌ Error processing {file.get('name', 'unknown')}: {e}")
                error_count += 1
                # Track failed file
                self.failed_files.append({
                    'name': file.get('name', 'unknown'),
                    'id': file.get('id', 'unknown'),
                    'mime_type': file.get('mimeType', 'unknown'),
                    'size': file.get('size', 'N/A'),
                    'url': get_gdrive_url(file.get('id', ''), file.get('mimeType', '')),
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'file_category': 'client_materials',
                    'timestamp': datetime.now().isoformat()
                })
        
        # Phase 3: Process files based on selected processor
        pdf_extracted_content = {}
        markitdown_failed_files = []
        if self.pdf_files_to_process:
            if self.pdf_processor == 'markitdown':
                logger.info(f"\n📄 PHASE 3: Processing {len(self.pdf_files_to_process)} files with MarkItDown...")
                logger.info("   Supported: PDFs, Office docs (PPTX, DOCX, XLSX), images, audio, and more!")
                pdf_extracted_content, markitdown_failed_files = self._batch_process_pdfs_with_markitdown()
            elif self.pdf_processor == 'pdfplumber':
                logger.info(f"\n📄 PHASE 3: Processing {len(self.pdf_files_to_process)} PDFs with pdfplumber...")
                pdf_extracted_content = self._fallback_pdf_processing()
            else:  # default to 'gpt'
                logger.info(f"\n📄 PHASE 3: Processing {len(self.pdf_files_to_process)} PDFs with GPT-4o...")
                pdf_extracted_content = self._batch_process_pdfs_with_gpt(openai_client)
            
            # Update the processed files with actual PDF content (only for regular client materials, not intake forms)
            for crawled_file in self.crawled_files:
                # Skip Client Intake files - they don't have PDFs
                if crawled_file.get('special_category') == 'client_intake':
                    continue
                    
                if crawled_file['final_filename'].endswith('.md'):
                    # Check if this is a PDF placeholder
                    file_path = os.path.join(client_materials_dir, crawled_file['final_filename'])
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Look for placeholders (PDF or MarkItDown processing)
                        if content.startswith('[PDF_PLACEHOLDER_'):
                            file_id = content.replace('[PDF_PLACEHOLDER_', '').replace(']', '')
                            if file_id in pdf_extracted_content:
                                # Replace with actual extracted content
                                actual_content = pdf_extracted_content[file_id]
                                with open(file_path, 'w', encoding='utf-8') as f:
                                    f.write(actual_content)
                                
                                # Update metadata
                                metadata_file_path = file_path + '.metadata.json'
                                if os.path.exists(metadata_file_path):
                                    with open(metadata_file_path, 'r') as f:
                                        metadata = json.load(f)
                                    metadata['word_count'] = len(actual_content.split())
                                    with open(metadata_file_path, 'w') as f:
                                        json.dump(metadata, f, indent=2)
                                
                                # Update crawled file info
                                crawled_file['word_count'] = len(actual_content.split())
                                logger.info(f"📄 Updated PDF content: {crawled_file['name']}")
                            else:
                                logger.warning(f"⚠️  No extracted content found for PDF: {crawled_file['name']}")
                        elif content.startswith('[File saved for MarkItDown processing:'):
                            # Extract file ID from the placeholder text
                            # Format: [File saved for MarkItDown processing: filename]
                            # We need to find the file_id from the crawled_file info
                            file_id = crawled_file['id']
                            
                            if file_id in pdf_extracted_content:
                                # Replace with actual extracted content
                                actual_content = pdf_extracted_content[file_id]
                                with open(file_path, 'w', encoding='utf-8') as f:
                                    f.write(actual_content)
                                
                                # Update metadata
                                metadata_file_path = file_path + '.metadata.json'
                                if os.path.exists(metadata_file_path):
                                    with open(metadata_file_path, 'r') as f:
                                        metadata = json.load(f)
                                    metadata['word_count'] = len(actual_content.split())
                                    with open(metadata_file_path, 'w') as f:
                                        json.dump(metadata, f, indent=2)
                                
                                # Update crawled file info
                                crawled_file['word_count'] = len(actual_content.split())
                                logger.info(f"📄 Updated MarkItDown content: {crawled_file['name']}")
                            else:
                                logger.warning(f"⚠️  No extracted content found for MarkItDown file: {crawled_file['name']} (file_id: {file_id})")
                    except Exception as e:
                        logger.error(f"❌ Error updating PDF content for {crawled_file['name']}: {e}")
        
        # Clean up temporary files
        try:
            self._cleanup_temp_files()
        except Exception as e:
            logger.warning(f"⚠️  Error during cleanup: {e}")
        
        # Generate summary report
        total_processed = processed_count + intake_processed_count
        self.generate_report(total_processed, error_count, len(files), markitdown_failed_files)
        
        logger.info(f"\n🎉 Drive folder processing completed!")
        logger.info(f"📊 Total files found: {len(files)}")
        logger.info(f"📋 Client Intake files: {intake_processed_count}")
        logger.info(f"📄 Regular client materials: {processed_count}")
        logger.info(f"✅ Total successfully processed: {total_processed}")
        logger.info(f"📄 PDFs processed with vectorize: {len(pdf_extracted_content)}")
        logger.info(f"❌ Errors: {error_count + len(markitdown_failed_files)}")
        logger.info(f"📂 Client materials saved to: {client_materials_dir}")
        logger.info(f"📋 Client intake saved to: {client_intake_dir}")
        logger.info(f"📋 Report saved to: {self.output_dir}/crawl_summary.json")
    
    def generate_report(self, processed_count: int, error_count: int, total_files: int, markitdown_failed_files: list = None):
        """Generate a summary report of the crawl"""
        # Combine all failed files (including MarkItDown failures)
        all_failed_files = self.failed_files + (markitdown_failed_files or [])
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'folder_id': self.folder_id,
            'delegated_user': self.delegated_user,
            'days_back': self.days_back,
            'summary': {
                'total_files_found': total_files,
                'supported_files': len(self.crawled_files),
                'successfully_processed': processed_count,
                'failed_files_count': len(all_failed_files),
                'errors': len(all_failed_files)
            },
            'successfully_crawled_files': self.crawled_files,
            'failed_files': all_failed_files
        }
        
        report_file = os.path.join(self.output_dir, 'crawl_summary.json')
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📋 Report saved: {report_file}")
        
        # Log failed files summary if any
        if self.failed_files:
            logger.warning(f"\n⚠️  Failed Files Summary ({len(self.failed_files)} files):")
            for failed in self.failed_files:
                logger.warning(f"   ❌ {failed['name']}")
                logger.warning(f"      Error: {failed['error_type']} - {failed['error']}")
                logger.warning(f"      Link: {failed['url']}")

def extract_folder_id_from_url(folder_input: str) -> str:
    """Extract folder ID from Google Drive URL or return the ID if already provided"""
    if folder_input.startswith('http'):
        if '/folders/' in folder_input:
            folder_id = folder_input.split('/folders/')[1].split('?')[0].split('#')[0]
            return folder_id
        else:
            raise ValueError("Invalid Google Drive folder URL format")
    else:
        return folder_input

def validate_credentials_file(credentials_path: str) -> bool:
    """Validate Google service account credentials file"""
    if not os.path.exists(credentials_path):
        logger.error(f"Credentials file not found: {credentials_path}")
        return False
    
    try:
        with open(credentials_path, 'r') as f:
            creds = json.load(f)
        
        required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
        missing_fields = [field for field in required_fields if field not in creds]
        
        if missing_fields:
            logger.error(f"Invalid credentials file. Missing fields: {', '.join(missing_fields)}")
            return False
        
        if creds.get('type') != 'service_account':
            logger.error("Credentials file must be for a service account")
            return False
            
        return True
        
    except json.JSONDecodeError:
        logger.error("Credentials file is not valid JSON")
        return False
    except Exception as e:
        logger.error(f"Error validating credentials file: {e}")
        return False

def extract_pdf_with_pdfplumber(file_path: str) -> str:
    """Extract text from a local PDF file using pdfplumber.
    Returns a single string with page contents separated by double newlines.
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"PDF not found: {file_path}")
            return ""
        text_content = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                if text.strip():
                    text_content.append(text)
        return '\n\n'.join(text_content).strip()
    except Exception as e:
        logger.error(f"Error extracting PDF with pdfplumber from {file_path}: {e}")
        return ""

def main_sync():
    """Main function to handle LLM categorization and PDF processing"""
    parser = argparse.ArgumentParser(
        description='Download files from a specific Google Drive folder with LLM categorization',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Required arguments
    parser.add_argument('--folder-id', '-f', required=True,
                       help='Google Drive folder ID or full folder URL (must be publicly accessible)')
    
    # Optional arguments  
    parser.add_argument('--credentials', '-k', default='./service_account.json',
                       help='Path to Google service account JSON file (default: ./service_account.json)')
    parser.add_argument('--days-back', '-d', type=int, default=0,
                       help='Number of days back to crawl modified files (default: 0=all files)')
    parser.add_argument('--output-dir', '-o', default='./ingestion/client_ingestion_outputs',
                       help='Output directory for client materials (default: ./ingestion/client_ingestion_outputs)')
    parser.add_argument('--no-llm-categories', action='store_true',
                       help='Disable LLM categorization and use simple keyword-based categorization instead')
    parser.add_argument('--pdf-processor', '-p', choices=['gpt', 'markitdown', 'pdfplumber'], default='gpt',
                       help='PDF processing method: gpt (GPT-4o), markitdown (MarkItDown), or pdfplumber (default: gpt)')
    parser.add_argument('--client-name', default='',
                       help='Client name to add to metadata for all processed files')
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Extract folder ID from URL if needed
    try:
        folder_id = extract_folder_id_from_url(args.folder_id)
        logger.info(f"📁 Target folder ID: {folder_id}")
    except ValueError as e:
        logger.error(f"Invalid folder ID/URL: {e}")
        return 1
    
    # Validate credentials file
    if not validate_credentials_file(args.credentials):
        logger.error("Please provide a valid Google service account credentials file")
        return 1
    
    credentials_path = os.path.abspath(args.credentials)
    
    logger.info(f"🚀 Starting folder-specific Google Drive processing")
    logger.info(f"📁 Folder ID: {folder_id}")
    logger.info(f"📅 Days back: {args.days_back}")
    use_llm_categories = not args.no_llm_categories
    logger.info(f"🤖 LLM Categorization: {'Enabled' if use_llm_categories else 'Disabled (--no-llm-categories flag used)'}")
    logger.info(f"📄 PDF Processor: {args.pdf_processor}")
    logger.info(f"🔑 Credentials: {credentials_path}")
    logger.info(f"📁 Output directory: {args.output_dir}/client_materials/")
    logger.info(f"🔓 Public folder access - no delegation required")
    
    try:
        # Initialize crawler
        crawler = FolderSpecificDriveCrawler(
            credentials_file=credentials_path,
            delegated_user=None,  # No user delegation needed for public folders
            folder_id=folder_id,
            days_back=args.days_back,
            output_dir=args.output_dir,
            pdf_processor=args.pdf_processor,
            client_name=args.client_name
        )
        
        # Setup and crawl
        crawler.setup()
        crawler.crawl_and_save_locally(use_llm_categories=use_llm_categories)
        
        logger.info("✅ Google Drive folder processing completed successfully!")
        return 0
        
    except KeyboardInterrupt:
        logger.info("🛑 Processing interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Error during Google Drive processing: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return 1

async def main_async(folder_id: str, output_dir: str = "./ingestion/client_ingestion_outputs", 
                    credentials_file: str = "./service_account.json", use_llm_categories: bool = True):
    """Async main function for use by other modules"""
    try:
        # Initialize crawler
        crawler = FolderSpecificDriveCrawler(
            credentials_file=credentials_file,
            delegated_user=None,  # No user delegation needed for public folders
            folder_id=folder_id,
            days_back=0,
            output_dir=output_dir,
            pdf_processor="markitdown",
            client_name=""
        )
        
        # Setup and crawl
        crawler.setup()
        crawler.crawl_and_save_locally(use_llm_categories=use_llm_categories)
        
        return {"status": "success", "folder_id": folder_id, "output_dir": output_dir}
        
    except Exception as e:
        logger.error(f"❌ Error during Google Drive processing: {e}")
        return {"status": "error", "error": str(e)}

def main():
    """Main entry point"""
    return main_sync()

if __name__ == "__main__":
    sys.exit(main())
