"""
Graphiti Episode Cache - Deduplication for Graphiti ingestion.

Tracks which papers have been ingested to Graphiti to prevent reprocessing.
Similar to ParseCache for agent-zot's main pipeline.
"""

import logging
import sqlite3
import time
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class GraphitiEpisodeCache:
    """
    SQLite-based cache tracking Graphiti episode ingestion.

    Prevents duplicate processing by recording which papers have been
    ingested to Graphiti. This is the deduplication layer for Graphiti,
    analogous to ParseCache for the main pipeline.

    Schema:
        - paper_key: Zotero item key (primary key)
        - episode_count: Number of episodes created
        - chunks_processed: Total chunks ingested
        - timestamp: Unix timestamp of ingestion
        - success: Whether ingestion succeeded
    """

    def __init__(self, cache_path: Optional[str] = None):
        """
        Initialize episode cache.

        Args:
            cache_path: Path to SQLite database (defaults to ~/.cache/agent-zot/graphiti_episodes.db)
        """
        if cache_path is None:
            cache_dir = Path.home() / ".cache" / "agent-zot"
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_path = str(cache_dir / "graphiti_episodes.db")

        self.cache_path = cache_path
        self._init_database()

        logger.info(f"GraphitiEpisodeCache initialized at {self.cache_path}")

    def _init_database(self):
        """Create cache database and table if not exists."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    paper_key TEXT PRIMARY KEY,
                    episode_count INTEGER NOT NULL,
                    chunks_processed INTEGER NOT NULL,
                    timestamp REAL NOT NULL,
                    success INTEGER NOT NULL
                )
            """)

            # Create index on timestamp for cleanup queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON episodes(timestamp)
            """)

            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connection with automatic close."""
        conn = sqlite3.connect(self.cache_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def has_paper(self, paper_key: str) -> bool:
        """
        Check if paper has been successfully ingested to Graphiti.

        Args:
            paper_key: Zotero item key

        Returns:
            True if paper already ingested successfully, False otherwise
        """
        with self._get_connection() as conn:
            result = conn.execute(
                "SELECT success FROM episodes WHERE paper_key = ? AND success = 1",
                (paper_key,)
            ).fetchone()

            return result is not None

    def get_paper_info(self, paper_key: str) -> Optional[Dict[str, Any]]:
        """
        Get ingestion info for a paper.

        Args:
            paper_key: Zotero item key

        Returns:
            Dict with episode_count, chunks_processed, timestamp, success
            None if paper not in cache
        """
        with self._get_connection() as conn:
            result = conn.execute(
                """
                SELECT paper_key, episode_count, chunks_processed, timestamp, success
                FROM episodes
                WHERE paper_key = ?
                """,
                (paper_key,)
            ).fetchone()

            if result is None:
                return None

            return {
                "paper_key": result["paper_key"],
                "episode_count": result["episode_count"],
                "chunks_processed": result["chunks_processed"],
                "timestamp": result["timestamp"],
                "success": bool(result["success"]),
            }

    def add_paper(
        self,
        paper_key: str,
        episode_count: int,
        chunks_processed: int,
        success: bool = True,
    ):
        """
        Add or update paper ingestion record.

        Args:
            paper_key: Zotero item key
            episode_count: Number of episodes created
            chunks_processed: Total chunks ingested
            success: Whether ingestion succeeded
        """
        timestamp = time.time()

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO episodes
                (paper_key, episode_count, chunks_processed, timestamp, success)
                VALUES (?, ?, ?, ?, ?)
                """,
                (paper_key, episode_count, chunks_processed, timestamp, int(success))
            )
            conn.commit()

        logger.debug(
            f"Added to episode cache: {paper_key} "
            f"(episodes={episode_count}, chunks={chunks_processed}, success={success})"
        )

    def remove_paper(self, paper_key: str):
        """
        Remove paper from cache (force re-ingestion).

        Args:
            paper_key: Zotero item key
        """
        with self._get_connection() as conn:
            conn.execute("DELETE FROM episodes WHERE paper_key = ?", (paper_key,))
            conn.commit()

        logger.info(f"Removed from episode cache: {paper_key}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with total_papers, successful, failed, total_chunks
        """
        with self._get_connection() as conn:
            result = conn.execute("""
                SELECT
                    COUNT(*) as total_papers,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed,
                    SUM(chunks_processed) as total_chunks
                FROM episodes
            """).fetchone()

            return {
                "total_papers": result["total_papers"] or 0,
                "successful": result["successful"] or 0,
                "failed": result["failed"] or 0,
                "total_chunks": result["total_chunks"] or 0,
            }

    def clear_failed(self):
        """Remove all failed ingestion records (to retry)."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM episodes WHERE success = 0")
            conn.commit()

        logger.info("Cleared all failed ingestion records from episode cache")

    def clear_all(self):
        """Clear entire cache (force re-ingest everything)."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM episodes")
            conn.commit()

        logger.warning("Cleared entire episode cache - all papers will be re-ingested")


# Global cache instance (lazy initialization)
_episode_cache: Optional[GraphitiEpisodeCache] = None


def get_episode_cache(cache_path: Optional[str] = None) -> GraphitiEpisodeCache:
    """
    Get or create global episode cache instance.

    Args:
        cache_path: Optional custom cache path

    Returns:
        GraphitiEpisodeCache instance
    """
    global _episode_cache

    if _episode_cache is None:
        _episode_cache = GraphitiEpisodeCache(cache_path)

    return _episode_cache
