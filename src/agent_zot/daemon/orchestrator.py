"""
Update orchestrator for agent-zot daemon.

Coordinates database updates triggered by file watcher or API polling,
using the existing semantic search pipeline to ensure identical processing.

Also handles optional Graphiti ingestion for autonomous entity extraction.
"""

import asyncio
import logging
import json
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

        # Load config for Graphiti integration
        self.config = self._load_config()

        # Metrics
        self.stats = {
            "total_jobs": 0,
            "total_items_processed": 0,
            "total_items_added": 0,
            "total_items_skipped": 0,
            "total_errors": 0,
            "last_update": None,
            "graphiti_items_processed": 0,
            "graphiti_chunks_processed": 0,
            "graphiti_episodes_created": 0,
        }

    def _load_config(self) -> Dict[str, Any]:
        """Load agent-zot configuration."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load config from {self.config_path}: {e}")
            return {}

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

            # Optional: Graphiti ingestion (Phase 1 - experimental)
            # Run asynchronously after main pipeline to avoid blocking
            graphiti_stats = await self._run_graphiti_ingestion(
                item_keys=job.item_keys,
                extract_fulltext=job.extract_fulltext
            )

            # Merge Graphiti stats
            stats["graphiti"] = graphiti_stats
            self.stats["graphiti_items_processed"] += graphiti_stats.get("items_processed", 0)
            self.stats["graphiti_chunks_processed"] += graphiti_stats.get("chunks_processed", 0)
            self.stats["graphiti_episodes_created"] += graphiti_stats.get("episodes_created", 0)

            duration = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"Update job completed in {duration:.1f}s: "
                f"processed={stats.get('processed_items', 0)}, "
                f"added={stats.get('added_items', 0)}, "
                f"skipped={stats.get('skipped_items', 0)}, "
                f"errors={stats.get('errors', 0)}, "
                f"graphiti_items={graphiti_stats.get('items_processed', 0)}"
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
            # ✅ IMPLEMENTED: semantic.py now accepts item_keys parameter (ADR-016)
            return self.search.update_database(
                force_full_rebuild=False,  # Always incremental
                limit=None,  # No limit (process all provided keys)
                item_keys=item_keys,  # ✅ Pass filtered item keys for true incremental update
                extract_fulltext=extract_fulltext
            )

        # ✅ COMPLETE: True incremental processing now enabled
        # Only the specified item_keys will be loaded and processed
        stats = await loop.run_in_executor(None, _sync_update)
        return stats

    async def _run_graphiti_ingestion(
        self,
        item_keys: List[str],
        extract_fulltext: bool = True
    ) -> Dict[str, Any]:
        """
        Run Graphiti ingestion for specified items (experimental).

        This method:
        1. Checks if Graphiti is enabled
        2. Loads chunks for each item from Qdrant or semantic search
        3. Calls graphiti_ingestion.ingest_to_graphiti for each item
        4. Tracks metrics and errors

        Runs asynchronously to avoid blocking main pipeline. Failures are
        logged but don't block main ingestion.

        Args:
            item_keys: List of Zotero item keys
            extract_fulltext: Whether fulltext was extracted (for context)

        Returns:
            Graphiti ingestion statistics
        """
        try:
            # Check if Graphiti enabled
            graphiti_config = self.config.get("graphiti", {})
            if not graphiti_config.get("enabled", False):
                logger.debug("Graphiti disabled, skipping ingestion")
                return {
                    "items_processed": 0,
                    "chunks_processed": 0,
                    "episodes_created": 0,
                    "errors": 0,
                    "skipped": len(item_keys),
                }

            from agent_zot.ingestion.graphiti_ingestion import (
                ingest_to_graphiti,
                should_ingest_to_graphiti,
            )
            from agent_zot.clients.zotero import get_zotero_client

            logger.info(f"Starting Graphiti ingestion for {len(item_keys)} items")

            # Get Zotero client for metadata
            zot = get_zotero_client()

            items_processed = 0
            chunks_processed = 0
            episodes_created = 0
            errors = 0
            skipped = 0

            for item_key in item_keys:
                try:
                    # Get item metadata
                    item = zot.item(item_key)
                    item_data = item.get("data", {})

                    metadata = {
                        "title": item_data.get("title", ""),
                        "authors": item_data.get("creators", []),
                        "tags": [tag.get("tag") for tag in item_data.get("tags", [])],
                    }

                    # Check if should ingest
                    if not should_ingest_to_graphiti(item_key, metadata, self.config):
                        skipped += 1
                        continue

                    # Get chunks from Qdrant
                    # For now, we'll extract chunks from the search instance
                    # Future: optimize by getting chunks directly from Qdrant client
                    chunks = await self._get_chunks_for_item(item_key)

                    if not chunks:
                        logger.warning(f"No chunks found for {item_key}, skipping")
                        skipped += 1
                        continue

                    # Ingest to Graphiti
                    result = await ingest_to_graphiti(
                        paper_key=item_key,
                        chunks=chunks,
                        metadata=metadata,
                        config=self.config,
                    )

                    if result.success:
                        items_processed += 1
                        chunks_processed += result.chunks_processed
                        episodes_created += result.episodes_created
                    else:
                        errors += 1
                        logger.warning(
                            f"Graphiti ingestion failed for {item_key}: "
                            f"{result.error}"
                        )

                except Exception as e:
                    logger.error(
                        f"Error during Graphiti ingestion for {item_key}: {e}",
                        exc_info=True
                    )
                    errors += 1

            logger.info(
                f"Graphiti ingestion complete: "
                f"processed={items_processed}, "
                f"chunks={chunks_processed}, "
                f"episodes={episodes_created}, "
                f"errors={errors}, "
                f"skipped={skipped}"
            )

            return {
                "items_processed": items_processed,
                "chunks_processed": chunks_processed,
                "episodes_created": episodes_created,
                "errors": errors,
                "skipped": skipped,
            }

        except Exception as e:
            logger.error(f"Fatal error in Graphiti ingestion: {e}", exc_info=True)
            return {
                "items_processed": 0,
                "chunks_processed": 0,
                "episodes_created": 0,
                "errors": 1,
                "skipped": len(item_keys),
            }

    async def _get_chunks_for_item(self, item_key: str) -> List[str]:
        """
        Get text chunks for an item from Qdrant.

        This retrieves the chunked text that was ingested during the main
        pipeline, so we can send it to Graphiti for entity extraction.

        Args:
            item_key: Zotero item key

        Returns:
            List of text chunks
        """
        try:
            # Access Qdrant client from semantic search instance
            qdrant_client = self.search.qdrant

            # Search for chunks matching this item key
            # Qdrant stores item_key in metadata
            results = qdrant_client.client.scroll(
                collection_name=self.search.collection_name,
                scroll_filter={
                    "must": [
                        {
                            "key": "item_key",
                            "match": {"value": item_key}
                        }
                    ]
                },
                limit=1000,  # Max chunks per paper
                with_payload=True,
                with_vectors=False,
            )

            # Extract text from points
            chunks = []
            for point in results[0]:  # results is tuple (points, next_page_offset)
                payload = point.payload
                text = payload.get("text", "")
                if text:
                    chunks.append(text)

            logger.debug(f"Retrieved {len(chunks)} chunks for {item_key}")
            return chunks

        except Exception as e:
            logger.error(f"Error retrieving chunks for {item_key}: {e}")
            return []

    def get_stats(self) -> Dict:
        """Get orchestrator statistics."""
        return self.stats.copy()
