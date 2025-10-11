"""
SQLite cache for parsed PDF documents.

Stores raw Docling parse output before chunking, enabling:
- Fast re-chunking with different parameters
- Fast re-embedding with different models
- Preservation of document structure (headings, tables, etc.)
- Vector DB independence (can switch from Qdrant to others)
"""

import json
import sqlite3
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class ParseCache:
    """Manages SQLite cache of parsed PDF documents."""

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize parse cache.

        Args:
            cache_dir: Directory for cache database. Defaults to ~/.cache/agent-zot/
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "agent-zot"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.cache_dir / "parsed_docs.db"
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS parsed_documents (
                    item_key TEXT PRIMARY KEY,
                    parse_timestamp DATETIME NOT NULL,
                    docling_version TEXT,
                    pdf_md5 TEXT,
                    full_text TEXT NOT NULL,
                    structure JSON,
                    chunks JSON NOT NULL,
                    chunk_config JSON,
                    parse_duration_sec REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Index for common queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_parse_timestamp
                ON parsed_documents(parse_timestamp)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at
                ON parsed_documents(created_at)
            """)

            conn.commit()

        logger.info(f"Parse cache initialized at {self.db_path}")

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def has_cached_parse(self, item_key: str, pdf_md5: Optional[str] = None) -> bool:
        """
        Check if parsed document exists in cache.

        Args:
            item_key: Zotero item key
            pdf_md5: MD5 hash of PDF file (optional, for invalidation)

        Returns:
            True if cached parse exists and is valid
        """
        with self._get_connection() as conn:
            if pdf_md5:
                # Check if cached parse matches current PDF
                result = conn.execute(
                    "SELECT 1 FROM parsed_documents WHERE item_key = ? AND pdf_md5 = ?",
                    (item_key, pdf_md5)
                ).fetchone()
            else:
                # Just check if any parse exists
                result = conn.execute(
                    "SELECT 1 FROM parsed_documents WHERE item_key = ?",
                    (item_key,)
                ).fetchone()

            return result is not None

    def get_cached_parse(self, item_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached parse for item.

        Args:
            item_key: Zotero item key

        Returns:
            Dict with full_text, structure, chunks, or None if not cached
        """
        with self._get_connection() as conn:
            result = conn.execute("""
                SELECT full_text, structure, chunks, chunk_config,
                       parse_timestamp, docling_version
                FROM parsed_documents
                WHERE item_key = ?
            """, (item_key,)).fetchone()

            if result:
                return {
                    "full_text": result["full_text"],
                    "structure": json.loads(result["structure"]) if result["structure"] else None,
                    "chunks": json.loads(result["chunks"]),
                    "chunk_config": json.loads(result["chunk_config"]) if result["chunk_config"] else None,
                    "parse_timestamp": result["parse_timestamp"],
                    "docling_version": result["docling_version"]
                }

            return None

    def cache_parse(
        self,
        item_key: str,
        full_text: str,
        chunks: List[Dict[str, Any]],
        structure: Optional[Dict[str, Any]] = None,
        chunk_config: Optional[Dict[str, Any]] = None,
        pdf_md5: Optional[str] = None,
        docling_version: str = "2.0",
        parse_duration_sec: Optional[float] = None
    ):
        """
        Cache parsed document.

        Args:
            item_key: Zotero item key
            full_text: Full document text before chunking
            chunks: List of chunks with text and metadata
            structure: Document structure (headings, tables, etc.)
            chunk_config: Chunking parameters used
            pdf_md5: MD5 hash of PDF file
            docling_version: Docling version used for parsing
            parse_duration_sec: Time taken to parse (for stats)
        """
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO parsed_documents
                (item_key, parse_timestamp, docling_version, pdf_md5, full_text,
                 structure, chunks, chunk_config, parse_duration_sec)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item_key,
                datetime.now().isoformat(),
                docling_version,
                pdf_md5,
                full_text,
                json.dumps(structure) if structure else None,
                json.dumps(chunks),
                json.dumps(chunk_config) if chunk_config else None,
                parse_duration_sec
            ))
            conn.commit()

        logger.debug(f"Cached parse for item {item_key} ({len(chunks)} chunks, {len(full_text)} chars)")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with count, total_size, oldest, newest
        """
        with self._get_connection() as conn:
            result = conn.execute("""
                SELECT
                    COUNT(*) as count,
                    SUM(LENGTH(full_text)) as total_chars,
                    MIN(parse_timestamp) as oldest,
                    MAX(parse_timestamp) as newest,
                    AVG(parse_duration_sec) as avg_parse_sec
                FROM parsed_documents
            """).fetchone()

            if result and result["count"] > 0:
                return {
                    "cached_documents": result["count"],
                    "total_chars": result["total_chars"],
                    "total_mb": round(result["total_chars"] / 1024 / 1024, 2) if result["total_chars"] else 0,
                    "oldest_parse": result["oldest"],
                    "newest_parse": result["newest"],
                    "avg_parse_duration_sec": round(result["avg_parse_sec"], 2) if result["avg_parse_sec"] else None
                }

            return {
                "cached_documents": 0,
                "total_chars": 0,
                "total_mb": 0,
                "oldest_parse": None,
                "newest_parse": None,
                "avg_parse_duration_sec": None
            }

    def clear_cache(self, older_than_days: Optional[int] = None):
        """
        Clear cache entries.

        Args:
            older_than_days: If specified, only clear entries older than this many days
        """
        with self._get_connection() as conn:
            if older_than_days:
                cutoff = datetime.now() - timedelta(days=older_than_days)
                conn.execute(
                    "DELETE FROM parsed_documents WHERE parse_timestamp < ?",
                    (cutoff.isoformat(),)
                )
                logger.info(f"Cleared cache entries older than {older_than_days} days")
            else:
                conn.execute("DELETE FROM parsed_documents")
                logger.info("Cleared all cache entries")

            conn.commit()

    def invalidate_item(self, item_key: str):
        """
        Remove cached parse for specific item.

        Args:
            item_key: Zotero item key to invalidate
        """
        with self._get_connection() as conn:
            conn.execute("DELETE FROM parsed_documents WHERE item_key = ?", (item_key,))
            conn.commit()

        logger.debug(f"Invalidated cache for item {item_key}")


def compute_pdf_md5(pdf_path: str) -> str:
    """
    Compute MD5 hash of PDF file for cache invalidation.

    Args:
        pdf_path: Path to PDF file

    Returns:
        MD5 hash as hex string
    """
    md5 = hashlib.md5()
    with open(pdf_path, 'rb') as f:
        # Read in chunks to handle large files
        for chunk in iter(lambda: f.read(8192), b''):
            md5.update(chunk)
    return md5.hexdigest()
