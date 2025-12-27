#!/usr/bin/env python3
"""
Google Drive Helper Script
--------------------------
A standalone Python script to get file contents from Google Drive.
Uses the same APIs as the Google Workspace MCP server but can be called directly from Python.

Usage:
    # List files
    uv run python google_drive_helper.py --list
    
    # Get file by ID
    uv run python google_drive_helper.py --file-id "1abc123xyz"
    
    # Search for files
    uv run python google_drive_helper.py --search "budget.xlsx"
    
    # Get file and save to local file
    uv run python google_drive_helper.py --file-id "1abc123" --output "output.txt"
"""

import argparse
import io
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

try:
    from markitdown import MarkItDown
    MARKITDOWN_AVAILABLE = True
except ImportError:
    MARKITDOWN_AVAILABLE = False
    print("⚠️  MarkItDown not available. Install with: uv pip install markitdown")


class GoogleDriveHelper:
    """Helper class to interact with Google Drive API"""
    
    def __init__(self, credentials_file: str = "service_account.json"):
        """
        Initialize Google Drive client
        
        Args:
            credentials_file: Path to service account JSON file
        """
        self.credentials_file = credentials_file
        self.drive_service = None
        self.docs_service = None
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize Google Drive and Docs services"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_file,
                scopes=[
                    'https://www.googleapis.com/auth/drive',
                    'https://www.googleapis.com/auth/documents',
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/presentations',
                    'https://www.googleapis.com/auth/docs',
                ]
            )
            
            self.drive_service = build('drive', 'v3', credentials=credentials)
            self.docs_service = build('docs', 'v1', credentials=credentials)
            
            print("✅ Successfully initialized Google Drive API")
            
        except Exception as e:
            print(f"❌ Error initializing Google Drive API: {e}")
            sys.exit(1)
    
    def list_files(self, query: Optional[str] = None, max_results: int = 20) -> List[Dict]:
        """
        List files in Google Drive
        
        Args:
            query: Optional search query (e.g., "name contains 'budget'")
            max_results: Maximum number of files to return
            
        Returns:
            List of file metadata dictionaries
        """
        print("🔧 Using: list_files")
        
        try:
            # Build query
            if query:
                full_query = f"{query} and trashed=false"
            else:
                full_query = "trashed=false"
            
            results = self.drive_service.files().list(
                q=full_query,
                pageSize=max_results,
                fields="files(id, name, mimeType, size, modifiedTime, webViewLink, owners)"
            ).execute()
            
            files = results.get('files', [])
            
            if not files:
                print("No files found.")
                return []
            
            print(f"\n📁 Found {len(files)} file(s):\n")
            for i, file in enumerate(files, 1):
                print(f"{i}. {file['name']}")
                print(f"   ID: {file['id']}")
                print(f"   Type: {file['mimeType']}")
                print(f"   Size: {file.get('size', 'N/A')} bytes")
                print(f"   Modified: {file.get('modifiedTime', 'N/A')}")
                print(f"   Link: {file.get('webViewLink', 'N/A')}")
                print()
            
            return files
            
        except HttpError as e:
            print(f"❌ Error listing files: {e}")
            return []
    
    def search_files(self, search_term: str, max_results: int = 20) -> List[Dict]:
        """
        Search for files by name
        
        Args:
            search_term: Term to search for in file names
            max_results: Maximum number of results
            
        Returns:
            List of matching files
        """
        print("🔧 Using: search_files")
        query = f"name contains '{search_term}'"
        return self.list_files(query=query, max_results=max_results)
    
    def get_file_metadata(self, file_id: str) -> Optional[Dict]:
        """
        Get file metadata by ID
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            File metadata dictionary or None
        """
        print("🔧 Using: get_file_metadata")
        
        try:
            file = self.drive_service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, size, modifiedTime, webViewLink, owners"
            ).execute()
            
            print(f"\n📄 File Metadata:")
            print(f"   Name: {file['name']}")
            print(f"   ID: {file['id']}")
            print(f"   Type: {file['mimeType']}")
            print(f"   Size: {file.get('size', 'N/A')} bytes")
            print(f"   Modified: {file.get('modifiedTime', 'N/A')}")
            print(f"   Link: {file.get('webViewLink', 'N/A')}")
            print()
            
            return file
            
        except HttpError as e:
            print(f"❌ Error getting file metadata: {e}")
            return None
    
    def convert_presentation_to_markdown(self, file_path: str) -> Optional[str]:
        """
        Convert a PowerPoint presentation to Markdown using MarkItDown
        
        Args:
            file_path: Path to the .pptx file
            
        Returns:
            Markdown content as string or None if conversion fails
        """
        print("🔧 Using: convert_presentation_to_markdown")
        
        if not MARKITDOWN_AVAILABLE:
            print("❌ MarkItDown is not available. Cannot convert presentation.")
            return None
        
        try:
            print("   Converting to Markdown with MarkItDown...")
            md = MarkItDown()
            result = md.convert(file_path)
            print(f"   ✅ Converted to Markdown ({len(result.text_content)} characters)")
            return result.text_content
        except Exception as e:
            print(f"❌ Error converting presentation to Markdown: {e}")
            return None
    
    def get_file_content(self, file_id: str, output_file: Optional[str] = None, 
                        convert_to_markdown: bool = False) -> Optional[str]:
        """
        Get file content by ID
        
        Supports:
        - Google Docs (exported as plain text)
        - Google Sheets (exported as CSV)
        - Google Slides (exported as plain text or markdown)
        - PowerPoint files (downloaded as binary or converted to markdown)
        - PDFs (downloaded as binary)
        - Text files (downloaded as text)
        - Other files (downloaded as binary)
        
        Args:
            file_id: Google Drive file ID
            output_file: Optional path to save content to file
            convert_to_markdown: If True, convert presentations to Markdown format
            
        Returns:
            File content as string (or None if binary saved to file)
        """
        print("🔧 Using: get_file_content")
        
        try:
            # Get file metadata first
            file = self.get_file_metadata(file_id)
            if not file:
                return None
            
            mime_type = file['mimeType']
            file_name = file['name']
            
            print(f"📥 Downloading: {file_name}")
            print(f"   Type: {mime_type}")
            
            content = None
            
            # Handle Google Docs
            if mime_type == 'application/vnd.google-apps.document':
                print("   Format: Google Doc → Plain Text")
                request = self.drive_service.files().export_media(
                    fileId=file_id,
                    mimeType='text/plain'
                )
                content = request.execute().decode('utf-8')
            
            # Handle Google Sheets
            elif mime_type == 'application/vnd.google-apps.spreadsheet':
                print("   Format: Google Sheet → CSV")
                request = self.drive_service.files().export_media(
                    fileId=file_id,
                    mimeType='text/csv'
                )
                content = request.execute().decode('utf-8')
            
            # Handle Google Slides
            elif mime_type == 'application/vnd.google-apps.presentation':
                if convert_to_markdown:
                    try:
                        print("   Format: Google Slides → PowerPoint → Markdown")
                        # Export as PPTX first, then convert to markdown
                        request = self.drive_service.files().export_media(
                            fileId=file_id,
                            mimeType='application/vnd.openxmlformats-officedocument.presentationml.presentation'
                        )
                        pptx_content = request.execute()
                        
                        # Save to temp file for MarkItDown processing
                        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pptx', delete=False) as tmp:
                            tmp.write(pptx_content)
                            temp_path = tmp.name
                        
                        try:
                            content = self.convert_presentation_to_markdown(temp_path)
                        finally:
                            # Clean up temp file
                            try:
                                os.unlink(temp_path)
                            except:
                                pass
                    except HttpError as e:
                        if 'exportSizeLimitExceeded' in str(e):
                            print(f"   ⚠️  File too large to export as PPTX ({file.get('size', 'unknown')} bytes)")
                            print("   Falling back to plain text export...")
                            # Fallback to plain text
                            request = self.drive_service.files().export_media(
                                fileId=file_id,
                                mimeType='text/plain'
                            )
                            content = request.execute().decode('utf-8')
                        else:
                            raise
                else:
                    print("   Format: Google Slides → Plain Text")
                    request = self.drive_service.files().export_media(
                        fileId=file_id,
                        mimeType='text/plain'
                    )
                    content = request.execute().decode('utf-8')
            
            # Handle text files
            elif mime_type.startswith('text/'):
                print("   Format: Text file")
                request = self.drive_service.files().get_media(fileId=file_id)
                content = request.execute().decode('utf-8')
            
            # Handle binary files (PDFs, images, etc.)
            else:
                print("   Format: Binary file")
                request = self.drive_service.files().get_media(fileId=file_id)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        print(f"   Download: {int(status.progress() * 100)}%")
                
                binary_content = fh.getvalue()
                
                # Check if it's a PowerPoint file and should be converted to markdown
                is_presentation = mime_type in [
                    'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # .pptx
                    'application/vnd.ms-powerpoint'  # .ppt
                ]
                
                if is_presentation and convert_to_markdown:
                    print("   Converting PowerPoint to Markdown...")
                    # Save to temp file for MarkItDown processing
                    with tempfile.NamedTemporaryFile(mode='wb', suffix='.pptx', delete=False) as tmp:
                        tmp.write(binary_content)
                        temp_path = tmp.name
                    
                    try:
                        content = self.convert_presentation_to_markdown(temp_path)
                        
                        # If output file specified and ends with .md, use it
                        # Otherwise create .md extension
                        if output_file:
                            if not output_file.endswith('.md'):
                                output_file = output_file.rsplit('.', 1)[0] + '.md'
                    finally:
                        # Clean up temp file
                        try:
                            os.unlink(temp_path)
                        except:
                            pass
                elif output_file:
                    with open(output_file, 'wb') as f:
                        f.write(binary_content)
                    print(f"✅ Saved to: {output_file}")
                    return None
                else:
                    try:
                        content = binary_content.decode('utf-8')
                    except UnicodeDecodeError:
                        print("⚠️  Binary file cannot be displayed as text. Use --output to save to file.")
                        return None
            
            # Save content to file if specified
            if output_file and content:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✅ Saved to: {output_file}")
            
            # Display content preview if not saving to file
            if content and not output_file:
                print("\n" + "=" * 80)
                print("FILE CONTENT:")
                print("=" * 80)
                if len(content) > 1000:
                    print(content[:1000])
                    print(f"\n... (showing first 1000 of {len(content)} characters)")
                else:
                    print(content)
                print("=" * 80)
            
            return content
            
        except HttpError as e:
            print(f"❌ Error getting file content: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return None
    
    def get_folder_contents(self, folder_id: str, recursive: bool = False) -> List[Dict]:
        """
        List contents of a folder
        
        Args:
            folder_id: Google Drive folder ID
            recursive: If True, list contents recursively
            
        Returns:
            List of files in the folder
        """
        print("🔧 Using: get_folder_contents")
        
        try:
            query = f"'{folder_id}' in parents and trashed=false"
            
            results = self.drive_service.files().list(
                q=query,
                pageSize=100,
                fields="files(id, name, mimeType, size, modifiedTime)"
            ).execute()
            
            files = results.get('files', [])
            
            print(f"\n📁 Folder contents ({len(files)} items):\n")
            
            all_files = []
            for file in files:
                icon = '📁' if file['mimeType'] == 'application/vnd.google-apps.folder' else '📄'
                print(f"  {icon} {file['name']}")
                print(f"     ID: {file['id']}")
                print(f"     Type: {file['mimeType']}")
                print()
                
                all_files.append(file)
                
                if recursive and file['mimeType'] == 'application/vnd.google-apps.folder':
                    print(f"  ↳ Scanning subfolder: {file['name']}")
                    subfolder_files = self.get_folder_contents(file['id'], recursive=True)
                    all_files.extend(subfolder_files)
            
            return all_files
            
        except HttpError as e:
            print(f"❌ Error listing folder contents: {e}")
            return []


def main():
    parser = argparse.ArgumentParser(
        description='Google Drive Helper - Get file contents from Google Drive',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List recent files
  uv run python google_drive_helper.py --list
  
  # Search for files
  uv run python google_drive_helper.py --search "budget"
  
  # Get file content by ID
  uv run python google_drive_helper.py --file-id "1abc123xyz"
  
  # Get file and save to local file
  uv run python google_drive_helper.py --file-id "1abc123" --output "document.txt"
  
  # Get PowerPoint presentation and convert to Markdown
  uv run python google_drive_helper.py --file-id "1pptxId" --convert-to-markdown --output "presentation.md"
  
  # List folder contents
  uv run python google_drive_helper.py --folder-id "1xyz789abc"
  
  # List folder contents recursively
  uv run python google_drive_helper.py --folder-id "1xyz789abc" --recursive
        """
    )
    
    parser.add_argument('--credentials', default='service_account.json',
                       help='Path to service account credentials file')
    parser.add_argument('--list', action='store_true',
                       help='List recent files')
    parser.add_argument('--search', type=str,
                       help='Search for files by name')
    parser.add_argument('--file-id', type=str,
                       help='Get content of file by ID')
    parser.add_argument('--folder-id', type=str,
                       help='List contents of folder by ID')
    parser.add_argument('--recursive', action='store_true',
                       help='Recursively list folder contents')
    parser.add_argument('--output', type=str,
                       help='Save file content to specified path')
    parser.add_argument('--convert-to-markdown', action='store_true',
                       help='Convert presentations (PPTX, Google Slides) to Markdown format')
    parser.add_argument('--max-results', type=int, default=20,
                       help='Maximum number of results for list/search (default: 20)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.credentials):
        print(f"❌ Credentials file not found: {args.credentials}")
        print("   Please ensure service_account.json exists in the current directory")
        sys.exit(1)
    
    print("🚀 Google Drive Helper")
    print("=" * 80)
    
    helper = GoogleDriveHelper(credentials_file=args.credentials)
    
    if args.list:
        helper.list_files(max_results=args.max_results)
    elif args.search:
        helper.search_files(args.search, max_results=args.max_results)
    elif args.file_id:
        helper.get_file_content(args.file_id, output_file=args.output, 
                               convert_to_markdown=args.convert_to_markdown)
    elif args.folder_id:
        helper.get_folder_contents(args.folder_id, recursive=args.recursive)
    else:
        parser.print_help()
        print("\n⚠️  Please specify an action: --list, --search, --file-id, or --folder-id")


if __name__ == "__main__":
    main()
