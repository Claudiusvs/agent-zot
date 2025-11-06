"""
API polling service for Zotero library changes.

Periodically queries the Zotero API for new or modified items using the
'since' parameter for efficient incremental updates.
"""

import asyncio
import logging
import time
from typing import Optional, List
from datetime import datetime

from agent_zot.clients.zotero import get_zotero_client
from agent_zot.daemon.queue import UpdateQueue

logger = logging.getLogger(__name__)


class APIPoller:
    """
    Polls Zotero API for new/modified items.

    Features:
    - Uses 'since' parameter for efficient incremental updates
    - Rate limit handling with exponential backoff
    - Graceful degradation on API errors
    - Automatic recovery
    """

    def __init__(
        self,
        update_queue: UpdateQueue,
        poll_interval_seconds: int = 300,  # 5 minutes
        use_since_param: bool = True
    ):
        """
        Initialize API poller.

        Args:
            update_queue: Queue to enqueue updates
            poll_interval_seconds: Polling interval (default: 300s = 5 min)
            use_since_param: Whether to use 'since' parameter (default: True)
        """
        self.update_queue = update_queue
        self.poll_interval = poll_interval_seconds
        self.use_since_param = use_since_param

        # Zotero API state
        self.zotero_client = get_zotero_client()
        self.last_library_version: Optional[int] = None
        self.last_poll_time: Optional[float] = None

        # Rate limiting
        self.backoff_seconds = 1  # Start at 1 minute
        self.max_backoff = 60  # Cap at 60 minutes
        self.consecutive_errors = 0

        # State
        self.running = False
        self._poll_task: Optional[asyncio.Task] = None

        logger.info(
            f"API poller initialized: interval={poll_interval_seconds}s, "
            f"use_since={use_since_param}"
        )

    async def start(self):
        """Start polling the Zotero API."""
        if self.running:
            logger.warning("API poller already running")
            return

        self.running = True

        # Initialize library version
        await self._init_library_version()

        # Start polling loop
        self._poll_task = asyncio.create_task(self._poll_loop())

        logger.info(
            f"API poller started: polling every {self.poll_interval}s, "
            f"library version: {self.last_library_version}"
        )

    async def stop(self):
        """Stop polling the API."""
        if not self.running:
            logger.warning("API poller not running")
            return

        self.running = False

        # Cancel poll task
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass

        logger.info("API poller stopped")

    async def _init_library_version(self):
        """Initialize the last library version from API."""
        try:
            # Get current library version without fetching all items
            # We'll use a very small request to get version header
            result = await asyncio.to_thread(
                self.zotero_client.items,
                limit=1
            )

            # Extract library version from last response headers
            # pyzotero stores this in the client's request property
            if hasattr(self.zotero_client, 'request') and self.zotero_client.request:
                version_header = self.zotero_client.request.headers.get('Last-Modified-Version')
                if version_header:
                    self.last_library_version = int(version_header)
                    logger.info(f"Initialized library version: {self.last_library_version}")
                    return

            # Fallback: assume version 0 (will fetch all items on first poll)
            self.last_library_version = 0
            logger.warning("Could not determine library version, starting from 0")

        except Exception as e:
            logger.error(f"Error initializing library version: {e}", exc_info=True)
            self.last_library_version = 0

    async def _poll_loop(self):
        """Main polling loop."""
        while self.running:
            try:
                # Wait for poll interval
                await asyncio.sleep(self.poll_interval)

                # Check for new items
                await self._check_for_updates()

                # Reset backoff on success
                if self.consecutive_errors > 0:
                    logger.info("Polling successful, resetting error count")
                    self.consecutive_errors = 0
                    self.backoff_seconds = 1

            except asyncio.CancelledError:
                logger.debug("Poll loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in poll loop: {e}", exc_info=True)
                self.consecutive_errors += 1

                # Apply exponential backoff
                await self._handle_error()

    async def _check_for_updates(self):
        """Check Zotero API for new/modified items."""
        logger.debug(f"Polling Zotero API (since version: {self.last_library_version})")

        try:
            # Build query parameters
            params = {"limit": 100}  # Fetch up to 100 new items per poll

            if self.use_since_param and self.last_library_version:
                # Use 'since' parameter for incremental update
                params["since"] = self.last_library_version

            # Query API (run in thread to avoid blocking)
            items = await asyncio.to_thread(
                self.zotero_client.items,
                **params
            )

            # Update last poll time
            self.last_poll_time = time.time()

            # Check if we got any new items
            if not items:
                logger.debug("No new items found")
                return

            # Extract item keys
            new_item_keys = [
                item.get("data", {}).get("key")
                for item in items
                if item.get("data", {}).get("key")
            ]

            if not new_item_keys:
                logger.debug("No valid item keys in response")
                return

            logger.info(f"API polling found {len(new_item_keys)} new/modified items")

            # Enqueue items for processing
            enqueued = await self.update_queue.enqueue(
                item_keys=new_item_keys,
                source="api_polling",
                extract_fulltext=True
            )

            # Update library version from response headers
            if hasattr(self.zotero_client, 'request') and self.zotero_client.request:
                version_header = self.zotero_client.request.headers.get('Last-Modified-Version')
                if version_header:
                    new_version = int(version_header)
                    if new_version > self.last_library_version:
                        logger.debug(
                            f"Updated library version: "
                            f"{self.last_library_version} → {new_version}"
                        )
                        self.last_library_version = new_version

            logger.info(f"API polling enqueued {enqueued} new items (deduped some)")

        except Exception as e:
            # Let the poll loop handle the error (backoff, etc.)
            raise

    async def _handle_error(self):
        """Handle API error with exponential backoff."""
        # Increase backoff exponentially
        self.backoff_seconds = min(self.backoff_seconds * 2, self.max_backoff)

        logger.warning(
            f"API polling error (consecutive: {self.consecutive_errors}), "
            f"backing off for {self.backoff_seconds} minutes"
        )

        # Wait before next attempt
        await asyncio.sleep(self.backoff_seconds * 60)

    def get_status(self) -> dict:
        """Get poller status."""
        return {
            "running": self.running,
            "poll_interval_seconds": self.poll_interval,
            "last_library_version": self.last_library_version,
            "last_poll": datetime.fromtimestamp(
                self.last_poll_time
            ).isoformat() if self.last_poll_time else None,
            "next_poll": datetime.fromtimestamp(
                self.last_poll_time + self.poll_interval
            ).isoformat() if self.last_poll_time else None,
            "consecutive_errors": self.consecutive_errors,
            "backoff_seconds": self.backoff_seconds if self.consecutive_errors > 0 else 0,
        }
