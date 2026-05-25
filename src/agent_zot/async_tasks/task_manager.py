"""
SQLite-based task state manager for async MCP operations.

Persists task state to survive server restarts and provide
status/progress tracking for long-running operations.
"""

import json
import sqlite3
import logging
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class AsyncSearchTask:
    """Represents an async search task."""
    task_id: str
    status: str  # pending, running, completed, failed
    task_type: str  # search, summarize, explore_graph
    query: str
    limit: int
    force_mode: Optional[str]

    # Additional parameters stored as JSON
    extra_params: Optional[str] = None  # JSON string for task-specific params

    created_at: str = ""  # ISO format
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    progress: int = 0  # 0-100
    progress_message: str = "Pending..."

    results: Optional[str] = None  # JSON string when completed
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    def get_extra_params(self) -> Dict[str, Any]:
        """Parse extra_params JSON."""
        if self.extra_params:
            return json.loads(self.extra_params)
        return {}

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "AsyncSearchTask":
        """Create from SQLite row."""
        return cls(
            task_id=row["task_id"],
            status=row["status"],
            task_type=row["task_type"] if "task_type" in row.keys() else "search",
            query=row["query"],
            limit=row["limit_count"],
            force_mode=row["force_mode"],
            extra_params=row["extra_params"] if "extra_params" in row.keys() else None,
            created_at=row["created_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            progress=row["progress"],
            progress_message=row["progress_message"] or "Pending...",
            results=row["results"],
            error=row["error"]
        )


class AsyncTaskManager:
    """Manages async task state in SQLite."""

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize task manager.

        Args:
            cache_dir: Directory for database. Defaults to ~/.cache/agent-zot/
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "agent-zot"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.cache_dir / "async_tasks.db"
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            # Check if table exists and has the task_type column
            cursor = conn.execute("PRAGMA table_info(async_tasks)")
            columns = [row[1] for row in cursor.fetchall()]

            if "task_type" not in columns and "task_id" in columns:
                # Migrate: add task_type and extra_params columns
                logger.info("Migrating async_tasks table: adding task_type and extra_params columns")
                conn.execute("ALTER TABLE async_tasks ADD COLUMN task_type TEXT DEFAULT 'search'")
                conn.execute("ALTER TABLE async_tasks ADD COLUMN extra_params TEXT")
                conn.commit()

            conn.execute("""
                CREATE TABLE IF NOT EXISTS async_tasks (
                    task_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL CHECK(status IN ('pending', 'running', 'completed', 'failed')),
                    task_type TEXT NOT NULL DEFAULT 'search',

                    -- Input parameters
                    query TEXT NOT NULL,
                    limit_count INTEGER NOT NULL,
                    force_mode TEXT,
                    extra_params TEXT,  -- JSON for task-specific params

                    -- Timestamps
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    started_at DATETIME,
                    completed_at DATETIME,

                    -- Progress tracking
                    progress INTEGER NOT NULL DEFAULT 0 CHECK(progress >= 0 AND progress <= 100),
                    progress_message TEXT,

                    -- Results
                    results TEXT,  -- JSON string
                    error TEXT     -- Error message if failed
                )
            """)

            # Indexes for common queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_async_tasks_status
                ON async_tasks(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_async_tasks_created_at
                ON async_tasks(created_at)
            """)

            conn.commit()

        logger.info(f"Async task database initialized at {self.db_path}")

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
        finally:
            conn.close()

    def create_task(
        self,
        query: str,
        limit: int = 10,
        force_mode: Optional[str] = None,
        task_type: str = "search",
        extra_params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new pending task.

        Args:
            query: Search query or item_key (for summarize)
            limit: Result limit
            force_mode: Optional forced mode
            task_type: Type of task ("search", "summarize", "explore_graph")
            extra_params: Additional task-specific parameters

        Returns:
            task_id (UUID string)
        """
        task_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()
        extra_params_json = json.dumps(extra_params) if extra_params else None

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO async_tasks
                (task_id, status, task_type, query, limit_count, force_mode, extra_params, created_at, progress, progress_message)
                VALUES (?, 'pending', ?, ?, ?, ?, ?, ?, 0, 'Task created, waiting to start...')
            """, (task_id, task_type, query, limit, force_mode, extra_params_json, created_at))
            conn.commit()

        logger.info(f"Created async {task_type} task {task_id} for: {query[:50]}...")
        return task_id

    def start_task(self, task_id: str) -> bool:
        """
        Mark task as running.

        Args:
            task_id: Task ID

        Returns:
            True if task was updated, False if not found
        """
        started_at = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.execute("""
                UPDATE async_tasks
                SET status = 'running',
                    started_at = ?,
                    progress = 5,
                    progress_message = 'Starting search...'
                WHERE task_id = ? AND status = 'pending'
            """, (started_at, task_id))
            conn.commit()

            updated = cursor.rowcount > 0

        if updated:
            logger.info(f"Started task {task_id}")
        return updated

    def update_progress(self, task_id: str, progress: int, message: str):
        """
        Update task progress.

        Args:
            task_id: Task ID
            progress: Progress percentage (0-100)
            message: Human-readable status message
        """
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE async_tasks
                SET progress = ?, progress_message = ?
                WHERE task_id = ? AND status = 'running'
            """, (min(max(progress, 0), 100), message, task_id))
            conn.commit()

        logger.debug(f"Task {task_id}: {progress}% - {message}")

    def complete_task(self, task_id: str, results: Dict[str, Any]):
        """
        Mark task as completed with results.

        Args:
            task_id: Task ID
            results: Search results dictionary
        """
        completed_at = datetime.now().isoformat()
        results_json = json.dumps(results)

        with self._get_connection() as conn:
            conn.execute("""
                UPDATE async_tasks
                SET status = 'completed',
                    completed_at = ?,
                    progress = 100,
                    progress_message = 'Search complete',
                    results = ?
                WHERE task_id = ?
            """, (completed_at, results_json, task_id))
            conn.commit()

        logger.info(f"Completed task {task_id}")

    def fail_task(self, task_id: str, error: str):
        """
        Mark task as failed.

        Args:
            task_id: Task ID
            error: Error message
        """
        completed_at = datetime.now().isoformat()

        with self._get_connection() as conn:
            conn.execute("""
                UPDATE async_tasks
                SET status = 'failed',
                    completed_at = ?,
                    progress_message = 'Task failed',
                    error = ?
                WHERE task_id = ?
            """, (completed_at, error, task_id))
            conn.commit()

        logger.error(f"Failed task {task_id}: {error}")

    def get_task(self, task_id: str) -> Optional[AsyncSearchTask]:
        """
        Get task by ID.

        Args:
            task_id: Task ID

        Returns:
            AsyncSearchTask or None if not found
        """
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM async_tasks WHERE task_id = ?
            """, (task_id,)).fetchone()

            if row:
                return AsyncSearchTask.from_row(row)
            return None

    def get_task_results(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task results if completed.

        Args:
            task_id: Task ID

        Returns:
            Results dict or None if not completed
        """
        task = self.get_task(task_id)
        if task and task.status == "completed" and task.results:
            return json.loads(task.results)
        return None

    def get_running_tasks(self) -> List[AsyncSearchTask]:
        """
        Get all tasks with 'running' status.

        Used on startup to mark interrupted tasks as failed.

        Returns:
            List of running tasks
        """
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM async_tasks WHERE status = 'running'
            """).fetchall()

            return [AsyncSearchTask.from_row(row) for row in rows]

    def get_pending_tasks(self) -> List[AsyncSearchTask]:
        """
        Get all tasks with 'pending' status.

        Returns:
            List of pending tasks
        """
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM async_tasks WHERE status = 'pending'
                ORDER BY created_at ASC
            """).fetchall()

            return [AsyncSearchTask.from_row(row) for row in rows]

    def cleanup_old_tasks(self, max_age_hours: int = 1):
        """
        Delete tasks older than specified age.

        Args:
            max_age_hours: Maximum age in hours (default 1)
        """
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        cutoff_str = cutoff.isoformat()

        with self._get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM async_tasks WHERE created_at < ?
            """, (cutoff_str,))
            deleted = cursor.rowcount
            conn.commit()

        if deleted > 0:
            logger.info(f"Cleaned up {deleted} tasks older than {max_age_hours} hours")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get task statistics.

        Returns:
            Dict with counts by status, oldest/newest timestamps
        """
        with self._get_connection() as conn:
            result = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    MIN(created_at) as oldest,
                    MAX(created_at) as newest
                FROM async_tasks
            """).fetchone()

            return {
                "total": result["total"] or 0,
                "pending": result["pending"] or 0,
                "running": result["running"] or 0,
                "completed": result["completed"] or 0,
                "failed": result["failed"] or 0,
                "oldest": result["oldest"],
                "newest": result["newest"]
            }
