"""
Background task executor for async MCP operations.

Executes long-running operations (search, summarize, explore_graph) in background threads
with progress reporting to the task manager.
"""

import logging
import threading
import traceback
from typing import Dict, Any, Optional, Callable

from .task_manager import AsyncTaskManager

logger = logging.getLogger(__name__)


class AsyncTaskExecutor:
    """Executes async tasks (search, summarize, explore_graph) in background threads."""

    def __init__(self, task_manager: AsyncTaskManager):
        """
        Initialize executor.

        Args:
            task_manager: Task manager for state persistence
        """
        self.task_manager = task_manager
        self._running_tasks: Dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

        # Lazy-loaded dependencies (set by server on startup)
        self._zot_client = None
        self._neo4j_client = None
        self._format_metadata_func = None
        self._get_attachment_func = None
        self._extract_fulltext_func = None

    def set_dependencies(
        self,
        zot_client=None,
        neo4j_client=None,
        format_metadata_func=None,
        get_attachment_func=None,
        extract_fulltext_func=None
    ):
        """Set dependencies needed for summarize and explore_graph tasks."""
        self._zot_client = zot_client
        self._neo4j_client = neo4j_client
        self._format_metadata_func = format_metadata_func
        self._get_attachment_func = get_attachment_func
        self._extract_fulltext_func = extract_fulltext_func

    def _create_progress_callback(self, task_id: str) -> Callable[[int, str], None]:
        """
        Create a progress callback function for a specific task.

        Args:
            task_id: Task ID to update

        Returns:
            Callback function that updates task progress
        """
        def callback(progress: int, message: str):
            try:
                self.task_manager.update_progress(task_id, progress, message)
            except Exception as e:
                logger.error(f"Failed to update progress for task {task_id}: {e}")

        return callback

    def start_task(self, task_id: str) -> bool:
        """
        Start a task execution in a background thread.

        Args:
            task_id: Task ID to start

        Returns:
            True if task was started, False if already running
        """
        with self._lock:
            if task_id in self._running_tasks:
                thread = self._running_tasks[task_id]
                if thread.is_alive():
                    logger.warning(f"Task {task_id} is already running")
                    return False

        task = self.task_manager.get_task(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return False

        task_type = task.task_type

        def run_in_thread():
            """Run the task synchronously in a background thread."""
            task = self.task_manager.get_task(task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return

            if task.status != "pending":
                logger.warning(f"Task {task_id} is not pending (status: {task.status})")
                return

            # Mark task as running
            self.task_manager.start_task(task_id)
            progress_callback = self._create_progress_callback(task_id)

            try:
                if task.task_type == "search":
                    results = self._run_search_task(task, progress_callback)
                elif task.task_type == "summarize":
                    results = self._run_summarize_task(task, progress_callback)
                elif task.task_type == "explore_graph":
                    results = self._run_explore_graph_task(task, progress_callback)
                else:
                    raise ValueError(f"Unknown task type: {task.task_type}")

                # Mark completed with results
                self.task_manager.complete_task(task_id, results)
                logger.info(f"Task {task_id} ({task.task_type}) completed")

            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)}"
                logger.error(f"Task {task_id} failed: {error_msg}")
                logger.debug(traceback.format_exc())
                self.task_manager.fail_task(task_id, error_msg)

            finally:
                # Remove from running tasks dict
                with self._lock:
                    self._running_tasks.pop(task_id, None)

        # Start in background thread
        thread = threading.Thread(
            target=run_in_thread,
            name=f"async_{task_type}_{task_id[:8]}",
            daemon=True
        )

        with self._lock:
            self._running_tasks[task_id] = thread

        thread.start()
        logger.info(f"Started background thread for {task_type} task {task_id}")
        return True

    def _run_search_task(self, task, progress_callback: Callable) -> Dict[str, Any]:
        """Execute a search task."""
        from agent_zot.search.semantic import create_semantic_search
        from agent_zot.search.unified_smart import smart_search

        progress_callback(10, "Initializing search engine...")
        semantic_search = create_semantic_search()

        # skip_decomposition=True avoids nested ThreadPoolExecutor deadlock
        results = smart_search(
            semantic_search,
            task.query,
            limit=task.limit,
            force_mode=task.force_mode,
            progress_callback=progress_callback,
            skip_decomposition=True
        )
        return results

    def _run_summarize_task(self, task, progress_callback: Callable) -> Dict[str, Any]:
        """Execute a summarize task."""
        import os
        import tempfile
        from agent_zot.search.semantic import create_semantic_search
        from agent_zot.search.unified_summarize import smart_summarize
        from agent_zot.clients.zotero import (
            get_zotero_client,
            format_item_metadata,
            get_attachment_details,
            convert_to_markdown,
        )

        progress_callback(10, "Initializing summarization engine...")

        # Get extra params
        extra = task.get_extra_params()
        item_key = task.query  # For summarize, query holds the item_key
        question = extra.get("question")  # Optional question for targeted mode
        top_k = extra.get("top_k", 5)

        progress_callback(20, "Loading Zotero client...")
        zot = get_zotero_client()

        # Create PDF extraction wrapper (same as server.py)
        def extract_fulltext_wrapper(zot_client, attachment):
            """Extract full text from PDF attachment."""
            with tempfile.TemporaryDirectory() as tmpdir:
                file_path = os.path.join(tmpdir, attachment.filename or f"{attachment.key}.pdf")
                zot_client.dump(attachment.key, filename=os.path.basename(file_path), path=tmpdir)

                if os.path.exists(file_path):
                    converted_text = convert_to_markdown(file_path)
                    if converted_text:
                        return converted_text
                    else:
                        raise Exception("Could not extract text from PDF")
                else:
                    raise Exception("PDF download failed")

        progress_callback(30, "Initializing semantic search...")
        semantic_search = create_semantic_search()

        progress_callback(40, f"Summarizing paper {item_key}...")

        results = smart_summarize(
            item_key=item_key,
            query=question,
            force_mode=task.force_mode,
            semantic_search_instance=semantic_search,
            zot_client=zot,
            format_metadata_func=format_item_metadata,
            get_attachment_func=get_attachment_details,
            extract_fulltext_func=extract_fulltext_wrapper,
            top_k=top_k,
            progress_callback=progress_callback
        )

        progress_callback(90, "Formatting results...")
        return results

    def _run_explore_graph_task(self, task, progress_callback: Callable) -> Dict[str, Any]:
        """Execute a graph exploration task."""
        from agent_zot.search.semantic import create_semantic_search
        from agent_zot.search.unified_graph import smart_explore_graph
        from agent_zot.clients.zotero import get_zotero_client
        from agent_zot.clients.neo4j_graphrag import get_neo4j_client

        progress_callback(10, "Initializing graph exploration engine...")

        # Get extra params
        extra = task.get_extra_params()
        paper_key = extra.get("paper_key")
        author = extra.get("author")
        concept = extra.get("concept")
        start_year = extra.get("start_year")
        end_year = extra.get("end_year")
        field = extra.get("field")
        max_hops = extra.get("max_hops", 2)

        progress_callback(20, "Loading Neo4j client...")
        neo4j_client = get_neo4j_client()

        progress_callback(30, "Loading Zotero client...")
        zot = get_zotero_client()

        progress_callback(40, "Initializing semantic search...")
        semantic_search = create_semantic_search()

        progress_callback(50, f"Exploring graph for: {task.query[:50]}...")

        results = smart_explore_graph(
            query=task.query,
            neo4j_client=neo4j_client,
            semantic_search_instance=semantic_search,
            zotero_client=zot,
            paper_key=paper_key,
            author=author,
            concept=concept,
            start_year=start_year,
            end_year=end_year,
            field=field,
            force_mode=task.force_mode,
            limit=task.limit,
            max_hops=max_hops,
            progress_callback=progress_callback
        )

        progress_callback(90, "Formatting results...")
        return results

    def is_task_running(self, task_id: str) -> bool:
        """
        Check if a task is currently running.

        Args:
            task_id: Task ID

        Returns:
            True if task is running in this executor
        """
        with self._lock:
            if task_id not in self._running_tasks:
                return False
            return self._running_tasks[task_id].is_alive()

    def get_running_count(self) -> int:
        """Get number of currently running tasks."""
        with self._lock:
            return sum(1 for t in self._running_tasks.values() if t.is_alive())

    def shutdown(self):
        """
        Shutdown executor.

        Note: Since threads are daemon threads, they will be terminated
        when the main process exits. We just mark any running tasks as failed.
        """
        with self._lock:
            for task_id, thread in list(self._running_tasks.items()):
                if thread.is_alive():
                    # Can't forcefully stop threads, but mark task as failed
                    self.task_manager.fail_task(task_id, "Server shutdown")
            self._running_tasks.clear()

        logger.info("AsyncSearchExecutor shut down")
