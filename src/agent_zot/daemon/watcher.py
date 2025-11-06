"""
File system watcher for Zotero SQLite database.

Monitors the zotero.sqlite file for modifications and triggers updates
when changes are detected. Uses debouncing to batch rapid changes.
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

from agent_zot.daemon.queue import UpdateQueue

logger = logging.getLogger(__name__)


class ZoteroDBHandler(FileSystemEventHandler):
    """Handler for Zotero database file changes."""

    def __init__(
        self,
        db_path: Path,
        update_queue: UpdateQueue,
        debounce_seconds: int = 30
    ):
        """
        Initialize database file handler.

        Args:
            db_path: Path to zotero.sqlite file
            update_queue: Queue to enqueue updates
            debounce_seconds: Wait time before triggering update
        """
        super().__init__()
        self.db_path = db_path
        self.update_queue = update_queue
        self.debounce_seconds = debounce_seconds

        self.last_trigger_time: Optional[float] = None
        self.pending_trigger: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        """Set the event loop for async operations."""
        self._loop = loop

    def on_modified(self, event):
        """
        Handle file modification events.

        Args:
            event: FileSystemEvent from watchdog
        """
        # Ignore directory modifications
        if event.is_directory:
            return

        # Check if it's the zotero.sqlite file
        if Path(event.src_path) != self.db_path:
            return

        logger.debug(f"Zotero DB modified: {event.src_path}")

        # Schedule debounced trigger
        self._schedule_trigger()

    def _schedule_trigger(self):
        """Schedule a debounced update trigger."""
        now = time.time()

        # Cancel any pending trigger
        if self.pending_trigger and not self.pending_trigger.done():
            self.pending_trigger.cancel()
            logger.debug("Cancelled previous pending trigger")

        # Check if we recently triggered
        if self.last_trigger_time:
            elapsed = now - self.last_trigger_time
            if elapsed < self.debounce_seconds:
                wait_time = self.debounce_seconds - elapsed
                logger.debug(
                    f"Last trigger was {elapsed:.1f}s ago, "
                    f"waiting {wait_time:.1f}s before next trigger"
                )

        # Schedule new trigger
        if self._loop:
            self.pending_trigger = self._loop.create_task(
                self._debounced_trigger()
            )
            logger.debug(f"Scheduled trigger in {self.debounce_seconds}s")

    async def _debounced_trigger(self):
        """Wait and then trigger update (debounced)."""
        try:
            # Wait for debounce period
            await asyncio.sleep(self.debounce_seconds)

            # Trigger update
            now = time.time()
            self.last_trigger_time = now

            logger.info(
                f"File watcher triggering update after {self.debounce_seconds}s "
                f"debounce period"
            )

            # We don't have specific item keys from file change,
            # so we trigger a full incremental update
            # The pipeline will use cache and API filtering to only process new items
            await self._trigger_update()

        except asyncio.CancelledError:
            logger.debug("Debounced trigger was cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in debounced trigger: {e}", exc_info=True)

    async def _trigger_update(self):
        """Trigger an update in the queue."""
        # For file watcher, we don't know which specific items changed
        # So we pass an empty list and let the pipeline handle discovery
        # The pipeline will query Zotero for new/modified items

        # This is a marker to tell the orchestrator to do a full scan
        # for new items (the pipeline already does this efficiently)
        await self.update_queue.enqueue(
            item_keys=["_file_watcher_scan"],  # Special marker
            source="file_watcher",
            extract_fulltext=True
        )


class FileWatcher:
    """
    Watches Zotero SQLite database for changes.

    Provides:
    - File system monitoring using watchdog
    - Debouncing to batch rapid changes
    - Async integration with update queue
    """

    def __init__(
        self,
        db_path: str,
        update_queue: UpdateQueue,
        debounce_seconds: int = 30
    ):
        """
        Initialize file watcher.

        Args:
            db_path: Path to zotero.sqlite file
            update_queue: Queue to enqueue updates
            debounce_seconds: Debounce period (default: 30s)
        """
        self.db_path = Path(db_path)
        self.update_queue = update_queue
        self.debounce_seconds = debounce_seconds

        # Validate path
        if not self.db_path.exists():
            raise FileNotFoundError(f"Zotero database not found: {db_path}")

        # Create handler and observer
        self.handler = ZoteroDBHandler(
            db_path=self.db_path,
            update_queue=update_queue,
            debounce_seconds=debounce_seconds
        )
        self.observer = Observer()

        # State
        self.running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        logger.info(
            f"File watcher initialized: watching {self.db_path} "
            f"(debounce: {debounce_seconds}s)"
        )

    async def start(self):
        """Start watching the database file."""
        if self.running:
            logger.warning("File watcher already running")
            return

        # Get event loop
        self._loop = asyncio.get_running_loop()
        self.handler.set_event_loop(self._loop)

        # Schedule observer on parent directory
        watch_dir = self.db_path.parent
        self.observer.schedule(
            self.handler,
            path=str(watch_dir),
            recursive=False
        )

        # Start observer
        self.observer.start()
        self.running = True

        logger.info(f"File watcher started: monitoring {watch_dir}")

    async def stop(self):
        """Stop watching the database file."""
        if not self.running:
            logger.warning("File watcher not running")
            return

        # Cancel pending trigger
        if self.handler.pending_trigger and not self.handler.pending_trigger.done():
            self.handler.pending_trigger.cancel()

        # Stop observer
        self.observer.stop()
        self.observer.join(timeout=5.0)

        self.running = False
        logger.info("File watcher stopped")

    def get_status(self) -> dict:
        """Get watcher status."""
        return {
            "running": self.running,
            "watching": str(self.db_path),
            "debounce_seconds": self.debounce_seconds,
            "last_trigger": datetime.fromtimestamp(
                self.handler.last_trigger_time
            ).isoformat() if self.handler.last_trigger_time else None,
            "pending_trigger": (
                self.handler.pending_trigger is not None and
                not self.handler.pending_trigger.done()
            ),
        }
