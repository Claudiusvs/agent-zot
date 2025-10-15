"""
Local Zotero database reader for semantic search.

Provides direct SQLite access to Zotero's local database for faster semantic search
when running in local mode.
"""

import os
import sqlite3
import platform
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from agent_zot.utils.common import is_local_mode
from agent_zot.database.parse_cache import ParseCache


@dataclass
class ZoteroItem:
    """Represents a Zotero item with text content for semantic search."""
    item_id: int
    key: str
    item_type_id: int
    item_type: Optional[str] = None
    doi: Optional[str] = None
    title: Optional[str] = None
    abstract: Optional[str] = None
    creators: Optional[str] = None
    fulltext: Optional[str] = None
    fulltext_source: Optional[str] = None  # 'pdf' or 'html'
    notes: Optional[str] = None
    extra: Optional[str] = None
    date_added: Optional[str] = None
    date_modified: Optional[str] = None
    
    def get_searchable_text(self) -> str:
        """
        Combine all text fields into a single searchable string.
        
        Returns:
            Combined text content for semantic search indexing.
        """
        parts = []
        
        if self.title:
            parts.append(f"Title: {self.title}")
        
        if self.creators:
            parts.append(f"Authors: {self.creators}")
            
        if self.abstract:
            parts.append(f"Abstract: {self.abstract}")
            
        if self.extra:
            parts.append(f"Extra: {self.extra}")
            
        if self.notes:
            parts.append(f"Notes: {self.notes}")
            
        if self.fulltext:
            # PATCH: Remove character limit - store full content for comprehensive search
            parts.append(f"Content: {self.fulltext}")
            
        return "\n\n".join(parts)


class LocalZoteroReader:
    """
    Direct SQLite reader for Zotero's local database.
    
    Provides fast access to item metadata and fulltext for semantic search
    without going through the Zotero API.
    """
    
    def __init__(self, db_path: Optional[str] = None, pdf_max_pages: Optional[int] = None):
        """
        Initialize the local database reader.

        Args:
            db_path: Optional path to zotero.sqlite. If None, auto-detect.
        """
        self.db_path = db_path or self._find_zotero_db()
        self._connection: Optional[sqlite3.Connection] = None
        self.pdf_max_pages: Optional[int] = pdf_max_pages

        # Initialize ParseCache for storing extracted/parsed text
        self.parse_cache = ParseCache()
        logging.info(f"ParseCache initialized at {self.parse_cache.db_path}")

        # Reduce noise from pdfminer warnings
        try:
            logging.getLogger("pdfminer").setLevel(logging.ERROR)
        except Exception:
            pass
        
    def _find_zotero_db(self) -> str:
        """
        Auto-detect the Zotero database location based on OS.
        
        Returns:
            Path to zotero.sqlite file.
            
        Raises:
            FileNotFoundError: If database cannot be located.
        """
        # PATCH: Check custom location first (common for power users)
        custom_db_path = Path.home() / "zotero_database" / "zotero.sqlite"
        if custom_db_path.exists():
            return str(custom_db_path)
        
        system = platform.system()
        
        if system == "Darwin":  # macOS
            db_path = Path.home() / "Zotero" / "zotero.sqlite"
        elif system == "Windows":
            # Try Windows 7+ location first
            db_path = Path.home() / "Zotero" / "zotero.sqlite"
            if not db_path.exists():
                # Fallback to XP/2000 location
                db_path = Path(os.path.expanduser("~/Documents and Settings")) / os.getenv("USERNAME", "") / "Zotero" / "zotero.sqlite"
        else:  # Linux and others
            db_path = Path.home() / "Zotero" / "zotero.sqlite"
            
        if not db_path.exists():
            raise FileNotFoundError(
                f"Zotero database not found at {db_path} or {custom_db_path}. "
                "Please ensure Zotero is installed and has been run at least once."
            )
            
        return str(db_path)
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection, creating if needed."""
        if self._connection is None:
            # Open in read-only mode for safety
            uri = f"file:{self.db_path}?mode=ro"
            self._connection = sqlite3.connect(uri, uri=True)
            self._connection.row_factory = sqlite3.Row
        return self._connection

    def _get_storage_dir(self) -> Path:
        """Return the Zotero storage directory path."""
        # PATCH: Use the same directory as the database, but with 'storage' subdirectory
        if self.db_path:
            db_dir = Path(self.db_path).parent
            storage_dir = db_dir / "storage"
            if storage_dir.exists():
                return storage_dir
        
        # Fallback to default Zotero data dir on macOS/Linux
        return Path.home() / "Zotero" / "storage"

    def _iter_parent_attachments(self, parent_item_id: int):
        """Yield tuples (attachment_key, path, content_type) for a parent item."""
        conn = self._get_connection()
        query = (
            """
            SELECT ia.itemID as attachmentItemID,
                   ia.parentItemID as parentItemID,
                   ia.path as path,
                   ia.contentType as contentType,
                   att.key as attachmentKey
            FROM itemAttachments ia
            JOIN items att ON att.itemID = ia.itemID
            WHERE ia.parentItemID = ?
            """
        )
        for row in conn.execute(query, (parent_item_id,)):
            yield row["attachmentKey"], row["path"], row["contentType"]

    def _resolve_attachment_path(self, attachment_key: str, zotero_path: str) -> Optional[Path]:
        """Resolve a Zotero attachment path like 'storage:filename.pdf' to a filesystem path."""
        if not zotero_path:
            return None
        storage_dir = self._get_storage_dir()
        if zotero_path.startswith("storage:"):
            rel = zotero_path.split(":", 1)[1]
            # Handle nested paths if present
            parts = [p for p in rel.split("/") if p]
            intended_path = storage_dir / attachment_key / Path(*parts)
            
            # PATCH: If the intended path exists, use it
            if intended_path.exists():
                return intended_path
            
            # PATCH: If intended path doesn't exist, look for any PDF or file in the directory
            attachment_dir = storage_dir / attachment_key
            if attachment_dir.exists() and attachment_dir.is_dir():
                # First priority: Look for PDF files
                pdf_files = list(attachment_dir.glob("*.pdf"))
                if pdf_files:
                    return pdf_files[0]  # Return first PDF found
                
                # Second priority: Look for any file (handles files without extensions)
                all_files = [f for f in attachment_dir.iterdir() if f.is_file() and not f.name.startswith('.')]
                if all_files:
                    # Check if any file is actually a PDF (by content)
                    for file_path in all_files:
                        try:
                            # Read first few bytes to check for PDF signature
                            with open(file_path, 'rb') as f:
                                header = f.read(8)
                                if header.startswith(b'%PDF'):
                                    return file_path
                        except Exception:
                            continue
                    # If no PDF found by content, return first file
                    return all_files[0]
            
            return None
        # External links not supported in first pass
        return None

    def _compute_pdf_md5(self, file_path: Path) -> str:
        """Compute MD5 hash of PDF file for cache validation."""
        md5_hash = hashlib.md5()
        with open(file_path, 'rb') as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(8192), b''):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()

    def _extract_text_from_pdf(self, file_path: Path) -> str:
        """
        Extract text from a PDF using Docling with subprocess isolation.

        CRITICAL FIX (Oct 2025): Docling's pypdfium2 C++ backend can crash with AssertionErrors.
        Even with proper cleanup in threads, C++ exceptions bypass Python exception handling,
        causing semaphore leaks and crashes after 150-200 PDFs.

        Solution: Run Docling in isolated subprocess. If subprocess crashes or times out,
        main process continues unaffected. Configurable timeout supports large documents.

        Strategy: Docling-only (no fallback) to ensure consistent high-quality output
        with HybridChunker, structural metadata, and proper reading order.

        ParseCache Integration: Before parsing, check if we have cached results.
        After parsing, cache the results. Cache is invalidated if PDF MD5 changes.
        """
        import json
        import subprocess
        import sys
        import tempfile

        # Extract item_key from file path (Zotero stores PDFs in /storage/ABC123XY/file.pdf)
        item_key = file_path.parent.name if file_path.parent.name != "storage" else None

        # Check ParseCache before expensive Docling parsing
        if item_key:
            pdf_md5 = self._compute_pdf_md5(file_path)
            if self.parse_cache.has_cached_parse(item_key, pdf_md5):
                cached = self.parse_cache.get_cached_parse(item_key)
                if cached:
                    logging.info(f"✓ Cache hit for {file_path.name} ({item_key})")
                    result = {
                        "text": cached["full_text"],
                        "chunks": cached["chunks"]
                    }
                    return (result, "docling")  # Return cached result in same format

        # Load config from standard location
        config_path = Path.home() / ".config" / "agent-zot" / "config.json"
        parser_config = {}
        subprocess_timeout = 3600  # Default: 1 hour (handles large textbooks)

        if config_path.exists():
            try:
                with open(config_path) as f:
                    full_config = json.load(f)
                    parser_config = full_config.get("semantic_search", {}).get("docling", {})
                    # Get configurable timeout (null = infinite, int = seconds)
                    subprocess_timeout = parser_config.get("subprocess_timeout", 3600)
            except Exception:
                pass

        # Docling subprocess (ONLY PARSER - no fallback)
        try:
            ocr_config = parser_config.get("ocr", {})

            # Create temp file for result (safer than pickle with complex objects)
            import json as _json
            import uuid
            result_id = str(uuid.uuid4())
            result_file = Path(tempfile.gettempdir()) / f"docling_{result_id}.json"

            # Subprocess code: run Docling parser and serialize result as JSON
            subprocess_code = f'''
import sys
import json
from pathlib import Path

try:
    # Import from installed package
    from agent_zot.parsers.docling import DoclingParser

    parser = DoclingParser(
        tokenizer="{parser_config.get("tokenizer", "BAAI/bge-m3")}",
        max_tokens={parser_config.get("max_tokens", 512)},
        merge_peers={parser_config.get("merge_peers", True)},
        num_threads={parser_config.get("num_threads", 2)},
        do_formula_enrichment={parser_config.get("do_formula_enrichment", False)},
        do_table_structure={parser_config.get("parse_tables", False)},
        enable_ocr_fallback={ocr_config.get("fallback_enabled", False)},
        ocr_min_text_threshold={ocr_config.get("min_text_threshold", 100)}
    )

    result = parser.parse_pdf("{str(file_path)}", force_ocr=False)

    if result and result.get("chunks"):
        # Convert to JSON-serializable format
        output = {{
            "text": result.get("text", ""),
            "chunks": [
                {{
                    "text": chunk["text"],
                    "meta": chunk.get("meta", {{}})
                }}
                for chunk in result["chunks"]
            ]
        }}
        with open("{str(result_file)}", "w") as f:
            json.dump(output, f)
        sys.exit(0)
    else:
        sys.exit(1)  # No chunks extracted

except Exception as e:
    import traceback
    with open("{str(result_file)}.err", "w") as f:
        f.write(str(e) + "\\n" + traceback.format_exc())
    sys.exit(2)
'''

            try:
                # Run with configurable timeout (default: 3600s = 1 hour)
                if subprocess_timeout is None:
                    # No timeout - wait forever (for extremely large documents)
                    logging.info(f"Docling parsing {file_path.name} (no timeout)")
                    proc = subprocess.run(
                        [sys.executable, "-c", subprocess_code],
                        capture_output=True
                    )
                else:
                    # With timeout (recommended)
                    timeout_mins = subprocess_timeout / 60
                    logging.info(f"Docling parsing {file_path.name} (timeout: {timeout_mins:.0f}min)")
                    proc = subprocess.run(
                        [sys.executable, "-c", subprocess_code],
                        timeout=subprocess_timeout,
                        capture_output=True
                    )

                if proc.returncode == 0 and result_file.exists():
                    # Success - load JSON result
                    with open(result_file) as f:
                        result = _json.load(f)
                    result_file.unlink()
                    logging.info(f"✓ Docling parsed {file_path.name} ({len(result['chunks'])} chunks)")

                    # Cache the parsed result for future re-chunking without re-parsing
                    if item_key:
                        chunk_config = {
                            "tokenizer": parser_config.get("tokenizer", "BAAI/bge-m3"),
                            "max_tokens": parser_config.get("max_tokens", 512),
                            "merge_peers": parser_config.get("merge_peers", True)
                        }
                        self.parse_cache.cache_parse(
                            item_key=item_key,
                            full_text=result.get("text", ""),
                            chunks=result.get("chunks", []),
                            chunk_config=chunk_config,
                            pdf_md5=pdf_md5
                        )
                        logging.info(f"✓ Cached parse for {item_key}")

                    return (result, "docling")
                else:
                    # Check for error file
                    err_file = Path(str(result_file) + ".err")
                    if err_file.exists():
                        error_msg = err_file.read_text()[:500]
                        logging.error(f"✗ Docling failed for {file_path.name}: {error_msg}")
                        err_file.unlink()
                    else:
                        logging.error(f"✗ Docling failed for {file_path.name} (no chunks extracted)")

                    # No fallback - fail loudly so user knows to investigate
                    return ("", "failed")

            except subprocess.TimeoutExpired:
                timeout_mins = subprocess_timeout / 60 if subprocess_timeout else "∞"
                logging.error(f"✗ Docling timeout ({timeout_mins}min) for {file_path.name}")
                return ("", "timeout")

            finally:
                # Cleanup temp files
                for f in [result_file, Path(str(result_file) + ".err")]:
                    if f.exists():
                        try:
                            f.unlink()
                        except:
                            pass

        except Exception as e:
            logging.error(f"✗ Docling subprocess setup failed for {file_path.name}: {e}")
            return ("", "error")
    
    def _extract_text_with_ocr(self, file_path: Path) -> str:
        """Extract text from PDF using OCR (for scanned PDFs)."""
        try:
            # Try pymupdf4llm first (handles both text and OCR)
            try:
                import pymupdf4llm
                return pymupdf4llm.to_markdown(str(file_path))
            except ImportError:
                pass
            
            # Fallback to pytesseract + pdf2image
            try:
                import pytesseract
                from pdf2image import convert_from_path
                
                # Convert PDF to images
                pages = convert_from_path(str(file_path), dpi=200)
                
                # Extract text from each page
                text_parts = []
                for page in pages[:10]:  # Limit to first 10 pages for speed
                    text = pytesseract.image_to_string(page)
                    if text.strip():
                        text_parts.append(text)
                
                return "\n\n".join(text_parts)
            except ImportError:
                pass
            
            return ""
        except Exception:
            return ""

    def _extract_text_from_html(self, file_path: Path) -> str:
        """Extract text from HTML using markitdown if available; fallback to stripping tags."""
        # Try markitdown first
        try:
            from markitdown import MarkItDown
            md = MarkItDown()
            result = md.convert(str(file_path))
            return result.text_content or ""
        except Exception:
            pass
        # Fallback using a simple parser
        try:
            from bs4 import BeautifulSoup  # type: ignore
            html = file_path.read_text(errors="ignore")
            return BeautifulSoup(html, "html.parser").get_text(" ")
        except Exception:
            return ""

    def _extract_text_from_file(self, file_path: Path):
        """Extract text content from a file based on extension, with fallbacks.

        For PDFs: Returns tuple (data, source) where data is dict (Docling) or str (pdfminer)
        For other files: Returns str (plain text)
        """
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            # PDFs return tuple format from _extract_text_from_pdf - pass through as-is
            return self._extract_text_from_pdf(file_path)
        if suffix in {".html", ".htm"}:
            return self._extract_text_from_html(file_path)
        # Generic best-effort
        try:
            return file_path.read_text(errors="ignore")
        except Exception:
            return ""

    def _extract_fulltext_for_item(self, item_id: int) -> Optional[tuple[str, str]]:
        """Attempt to extract fulltext and source from the item's best attachment.

        Preference: use PDF when available; fall back to HTML when no PDF exists.
        Returns (text, source) where source is 'pdf' or 'html'.
        """
        # PATCH: Check if this item IS an attachment first
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT key, itemTypeID FROM items WHERE itemID = ?', (item_id,))
        item_result = cursor.fetchone()
        
        if item_result:
            item_key, item_type_id = item_result
            
            # Check if this is an attachment item (itemTypeID = 3)
            if item_type_id == 3:
                # This IS an attachment - check if it's a PDF we can extract from
                cursor.execute('SELECT path, contentType FROM itemAttachments WHERE itemID = ?', (item_id,))
                attachment_result = cursor.fetchone()
                if attachment_result:
                    path, content_type = attachment_result
                    if content_type == 'application/pdf':
                        resolved = self._resolve_attachment_path(item_key, path or "")
                        if resolved and resolved.exists():
                            # For PDFs, _extract_text_from_file already returns tuple format
                            return self._extract_text_from_file(resolved)
                return None
        
        # Original logic for parent items
        best_pdf = None
        best_html = None
        for key, path, ctype in self._iter_parent_attachments(item_id):
            resolved = self._resolve_attachment_path(key, path or "")
            if not resolved or not resolved.exists():
                continue
            if ctype == "application/pdf" and best_pdf is None:
                best_pdf = resolved
            elif (ctype or "").startswith("text/html") and best_html is None:
                best_html = resolved
        # Prefer PDF, otherwise fall back to HTML
        target = best_pdf or best_html
        if not target:
            return None

        # For PDFs, _extract_text_from_file already returns tuple format
        if target.suffix.lower() == ".pdf":
            return self._extract_text_from_file(target)

        # For non-PDFs (HTML, etc.), returns plain text - wrap in tuple
        text = self._extract_text_from_file(target)
        if not text:
            return None
        source = "html" if target.suffix.lower() in {".html", ".htm"} else "file"
        return (text, source)
    
    def close(self):
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def get_item_count(self) -> int:
        """
        Get total count of non-attachment items.
        
        Returns:
            Number of items in the library.
        """
        conn = self._get_connection()
        cursor = conn.execute(
            """
            SELECT COUNT(*)
            FROM items i
            JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
            WHERE it.typeName = 'attachment'
            """
        )
        return cursor.fetchone()[0]
    
    def get_items_with_text(self, limit: Optional[int] = None, include_fulltext: bool = False) -> List[ZoteroItem]:
        """
        Get all items with their text content for semantic search.
        
        Args:
            limit: Optional limit on number of items to return.
            
        Returns:
            List of ZoteroItem objects with text content.
        """
        conn = self._get_connection()
        
        # Query to get items with their text content (simplified for now)
        query = """
        SELECT 
            i.itemID,
            i.key,
            i.itemTypeID,
            it.typeName as item_type,
            i.dateAdded,
            i.dateModified,
            title_val.value as title,
            abstract_val.value as abstract,
            extra_val.value as extra,
            doi_val.value as doi,
            GROUP_CONCAT(n.note, ' ') as notes,
            GROUP_CONCAT(
                CASE 
                    WHEN c.firstName IS NOT NULL AND c.lastName IS NOT NULL 
                    THEN c.lastName || ', ' || c.firstName
                    WHEN c.lastName IS NOT NULL 
                    THEN c.lastName
                    ELSE NULL
                END, '; '
            ) as creators
        FROM items i
        JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
        
        -- Get title
        LEFT JOIN itemData title_data ON i.itemID = title_data.itemID AND title_data.fieldID = 1
        LEFT JOIN itemDataValues title_val ON title_data.valueID = title_val.valueID
        
        -- Get abstract  
        LEFT JOIN itemData abstract_data ON i.itemID = abstract_data.itemID AND abstract_data.fieldID = 2
        LEFT JOIN itemDataValues abstract_val ON abstract_data.valueID = abstract_val.valueID
        
        -- Get extra field
        LEFT JOIN itemData extra_data ON i.itemID = extra_data.itemID AND extra_data.fieldID = 16
        LEFT JOIN itemDataValues extra_val ON extra_data.valueID = extra_val.valueID

        -- Get DOI field via fields table
        LEFT JOIN fields doi_f ON doi_f.fieldName = 'DOI'
        LEFT JOIN itemData doi_data ON i.itemID = doi_data.itemID AND doi_data.fieldID = doi_f.fieldID
        LEFT JOIN itemDataValues doi_val ON doi_data.valueID = doi_val.valueID
        
        -- Get notes
        LEFT JOIN itemNotes n ON i.itemID = n.parentItemID OR i.itemID = n.itemID
        
        -- Get creators
        LEFT JOIN itemCreators ic ON i.itemID = ic.itemID
        LEFT JOIN creators c ON ic.creatorID = c.creatorID
        
        WHERE it.typeName = 'attachment'
        
        GROUP BY i.itemID, i.key, i.itemTypeID, it.typeName, i.dateAdded, i.dateModified,
                 title_val.value, abstract_val.value, extra_val.value
        
        ORDER BY i.dateModified DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor = conn.execute(query)
        items = []
        
        for row in cursor:
            item = ZoteroItem(
                item_id=row['itemID'],
                key=row['key'],
                item_type_id=row['itemTypeID'],
                item_type=row['item_type'],
                doi=row['doi'],
                title=row['title'],
                abstract=row['abstract'],
                creators=row['creators'],
                fulltext=(res := (self._extract_fulltext_for_item(row['itemID']) if include_fulltext else None)) and res[0],
                fulltext_source=res[1] if include_fulltext and res else None,
                notes=row['notes'],
                extra=row['extra'],
                date_added=row['dateAdded'],
                date_modified=row['dateModified']
            )
            items.append(item)
            
        return items

    # Public helper to extract fulltext on demand for a specific item
    def extract_fulltext_for_item(self, item_id: int) -> Optional[tuple[str, str]]:
        return self._extract_fulltext_for_item(item_id)
    
    def get_item_by_key(self, key: str) -> Optional[ZoteroItem]:
        """
        Get a specific item by its Zotero key.
        
        Args:
            key: The Zotero item key.
            
        Returns:
            ZoteroItem if found, None otherwise.
        """
        items = self.get_items_with_text()
        for item in items:
            if item.key == key:
                return item
        return None
    
    def search_items_by_text(self, query: str, limit: int = 50) -> List[ZoteroItem]:
        """
        Simple text search through item content.
        
        Args:
            query: Search query string.
            limit: Maximum number of results.
            
        Returns:
            List of matching ZoteroItem objects.
        """
        items = self.get_items_with_text()
        matching_items = []
        
        query_lower = query.lower()
        
        for item in items:
            searchable_text = item.get_searchable_text().lower()
            if query_lower in searchable_text:
                matching_items.append(item)
                if len(matching_items) >= limit:
                    break
                    
        return matching_items


def get_local_zotero_reader() -> Optional[LocalZoteroReader]:
    """
    Get a LocalZoteroReader instance if in local mode.
    
    Returns:
        LocalZoteroReader instance if in local mode and database exists,
        None otherwise.
    """
    if not is_local_mode():
        return None
        
    try:
        return LocalZoteroReader()
    except FileNotFoundError:
        return None


def is_local_db_available() -> bool:
    """
    Check if local Zotero database is available.
    
    Returns:
        True if local database can be accessed, False otherwise.
    """
    reader = get_local_zotero_reader()
    if reader:
        reader.close()
        return True
    return False