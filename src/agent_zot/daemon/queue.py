"""
Update queue with deduplication for agent-zot daemon.

Prevents duplicate processing when multiple triggers (file watcher + API polling)
detect the same new items within a short time window.
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class UpdateJob:
    """Represents a database update job."""
    item_keys: List[str]
    source: str  # "file_watcher", "api_polling", or "manual"
    timestamp: float
    extract_fulltext: bool = True


class UpdateQueue:
    """
    Thread-safe update queue with deduplication.

    Features:
    - Deduplicates item keys within configurable time window
    - Tracks source of each update for monitoring
    - Batch processing support
    - Metrics tracking
    """

    def __init__(self, dedup_window_seconds: int = 60, max_batch_size: int = 50):
        """
        Initialize update queue.

        Args:
            dedup_window_seconds: Time window for deduplication (default: 60s)
            max_batch_size: Maximum items per batch (default: 50)
        """
        self.queue: asyncio.Queue = asyncio.Queue()
        self.seen: Dict[str, float] = {}  # item_key -> timestamp
        self.dedup_window = dedup_window_seconds
        self.max_batch_size = max_batch_size

        # Metrics
        self.stats = {
            "total_enqueued": 0,
            "total_deduped": 0,
            "total_processed": 0,
            "by_source": {
                "file_watcher": 0,
                "api_polling": 0,
                "manual": 0,
            },
            "last_enqueue": None,
            "last_process": None,
        }

        # Thread safety
        self._lock = asyncio.Lock()

    async def enqueue(
        self,
        item_keys: List[str],
        source: str,
        extract_fulltext: bool = True
    ) -> int:
        """
        Add items to queue with deduplication.

        Args:
            item_keys: List of Zotero item keys to update
            source: Source of update ("file_watcher", "api_polling", "manual")
            extract_fulltext: Whether to extract full PDF text

        Returns:
            Number of new items added (after deduplication)
        """
        async with self._lock:
            now = time.time()
            new_items: List[str] = []
            deduped_count = 0

            for key in item_keys:
                last_seen = self.seen.get(key)

                # Check if item was seen recently
                if last_seen and (now - last_seen) < self.dedup_window:
                    deduped_count += 1
                    logger.debug(
                        f"Deduplicating {key} from {source} "
                        f"(seen {int(now - last_seen)}s ago)"
                    )
                    continue

                # Mark as seen and add to new items
                new_items.append(key)
                self.seen[key] = now

            # Clean up old entries from seen dict (older than dedup window)
            cutoff = now - self.dedup_window
            self.seen = {k: v for k, v in self.seen.items() if v > cutoff}

            # Enqueue if we have new items
            if new_items:
                job = UpdateJob(
                    item_keys=new_items,
                    source=source,
                    timestamp=now,
                    extract_fulltext=extract_fulltext
                )
                await self.queue.put(job)

                # Update metrics
                self.stats["total_enqueued"] += len(new_items)
                self.stats["total_deduped"] += deduped_count
                self.stats["by_source"][source] += len(new_items)
                self.stats["last_enqueue"] = datetime.now().isoformat()

                logger.info(
                    f"{source} triggered update for {len(new_items)} new items "
                    f"(deduped: {deduped_count})"
                )
            else:
                logger.debug(
                    f"{source} triggered but all {len(item_keys)} items "
                    f"already queued/processed recently"
                )
                self.stats["total_deduped"] += deduped_count

            return len(new_items)

    async def dequeue(self) -> Optional[UpdateJob]:
        """
        Get next update job from queue.

        Returns:
            UpdateJob or None if queue is empty (non-blocking)
        """
        try:
            job = await asyncio.wait_for(self.queue.get(), timeout=0.1)
            self.stats["last_process"] = datetime.now().isoformat()
            return job
        except asyncio.TimeoutError:
            return None

    async def get_next_batch(self, timeout: float = 1.0) -> Optional[UpdateJob]:
        """
        Get next batch of items to process.

        Args:
            timeout: How long to wait for items (seconds)

        Returns:
            UpdateJob or None if timeout
        """
        try:
            job = await asyncio.wait_for(self.queue.get(), timeout=timeout)
            self.stats["total_processed"] += len(job.item_keys)
            self.stats["last_process"] = datetime.now().isoformat()
            return job
        except asyncio.TimeoutError:
            return None

    def get_stats(self) -> Dict:
        """Get queue statistics."""
        return {
            **self.stats,
            "queue_size": self.queue.qsize(),
            "dedup_window": self.dedup_window,
            "max_batch_size": self.max_batch_size,
        }

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self.queue.empty()

    async def clear(self):
        """Clear the queue (for testing or shutdown)."""
        async with self._lock:
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            self.seen.clear()
            logger.info("Queue cleared")
