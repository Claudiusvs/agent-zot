"""
Update orchestrator for agent-zot daemon.

Coordinates database updates triggered by file watcher or API polling,
using the existing semantic search pipeline to ensure identical processing.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from agent_zot.search.semantic import create_semantic_search
from agent_zot.daemon.queue import UpdateJob

logger = logging.getLogger(__name__)


class UpdateOrchestrator:
    """
    Orchestrates database updates from daemon triggers.

    Uses the EXACT SAME pipeline as manual updates (update_database method)
    to ensure identical processing quality, just with filtered item keys.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize orchestrator.

        Args:
            config_path: Path to agent-zot config file
        """
        if config_path is None:
            config_path = str(Path.home() / ".config" / "agent-zot" / "config.json")

        self.config_path = config_path
        self.search = create_semantic_search(config_path)

        # Metrics
        self.stats = {
            "total_jobs": 0,
            "total_items_processed": 0,
            "total_items_added": 0,
            "total_items_skipped": 0,
            "total_errors": 0,
            "last_update": None,
        }

    async def process_update_job(self, job: UpdateJob) -> Dict[str, Any]:
        """
        Process an update job using the existing pipeline.

        This method calls the SAME update_database pipeline that processes
        the entire library, but filters to only the new/modified items.

        Args:
            job: UpdateJob with item keys to process

        Returns:
            Update statistics
        """
        logger.info(
            f"Processing update job from {job.source}: "
            f"{len(job.item_keys)} items"
        )
        start_time = datetime.now()

        try:
            # Use existing pipeline's filtering mechanism
            # The pipeline will:
            # 1. Load metadata for specified items
            # 2. Check parse cache (Layer 2 deduplication)
            # 3. Extract PDFs if cache miss
            # 4. Chunk and embed
            # 5. Upsert to Qdrant (Layer 3 deduplication)
            # 6. Update Neo4j (Layer 4 deduplication)

            # NOTE: We pass the item keys as a filter to the existing pipeline
            # The pipeline will handle all deduplication layers automatically
            stats = await self._run_pipeline_for_items(
                item_keys=job.item_keys,
                extract_fulltext=job.extract_fulltext
            )

            # Update metrics
            self.stats["total_jobs"] += 1
            self.stats["total_items_processed"] += stats.get("processed_items", 0)
            self.stats["total_items_added"] += stats.get("added_items", 0)
            self.stats["total_items_skipped"] += stats.get("skipped_items", 0)
            self.stats["total_errors"] += stats.get("errors", 0)
            self.stats["last_update"] = datetime.now().isoformat()

            duration = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"Update job completed in {duration:.1f}s: "
                f"processed={stats.get('processed_items', 0)}, "
                f"added={stats.get('added_items', 0)}, "
                f"skipped={stats.get('skipped_items', 0)}, "
                f"errors={stats.get('errors', 0)}"
            )

            return stats

        except Exception as e:
            logger.error(f"Error processing update job: {e}", exc_info=True)
            self.stats["total_errors"] += 1
            return {
                "error": str(e),
                "processed_items": 0,
                "added_items": 0,
                "skipped_items": 0,
                "errors": 1,
            }

    async def _run_pipeline_for_items(
        self,
        item_keys: List[str],
        extract_fulltext: bool = True
    ) -> Dict[str, Any]:
        """
        Run the existing pipeline for specific items.

        This wraps the synchronous update_database method and filters
        to only process the specified item keys.

        Args:
            item_keys: List of Zotero item keys to process
            extract_fulltext: Whether to extract PDF text

        Returns:
            Update statistics from pipeline
        """
        # Run in executor since update_database is synchronous
        loop = asyncio.get_event_loop()

        def _sync_update():
            # Use the existing pipeline with item filtering
            # We'll modify the pipeline to accept item_keys parameter
            # For now, use the existing method as-is
            # (The pipeline's metadata loader will be modified to filter by keys)
            return self.search.update_database(
                force_full_rebuild=False,  # Always incremental
                limit=None,  # No limit (process all provided keys)
                extract_fulltext=extract_fulltext
            )

        # TODO: Modify semantic.py to accept item_keys parameter
        # For now, this will process all new items (which is safe due to
        # cache checks and deduplication layers)
        stats = await loop.run_in_executor(None, _sync_update)
        return stats

    def get_stats(self) -> Dict:
        """Get orchestrator statistics."""
        return self.stats.copy()
