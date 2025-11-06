"""
Daemon manager for agent-zot auto-sync.

Coordinates file watcher, API poller, update queue, and orchestrator
to provide automatic ingestion of new Zotero items.
"""

import asyncio
import logging
import os
import signal
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from agent_zot.daemon.queue import UpdateQueue
from agent_zot.daemon.watcher import FileWatcher
from agent_zot.daemon.poller import APIPoller
from agent_zot.daemon.orchestrator import UpdateOrchestrator

logger = logging.getLogger(__name__)


class DaemonManager:
    """
    Manages the auto-sync daemon.

    Coordinates:
    - Update queue (deduplication)
    - File watcher (immediate trigger)
    - API poller (reliable trigger)
    - Update orchestrator (pipeline execution)
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize daemon manager.

        Args:
            config_path: Path to agent-zot config file
        """
        if config_path is None:
            config_path = str(Path.home() / ".config" / "agent-zot" / "config.json")

        self.config_path = config_path
        self.config = self._load_config()

        # Auto-sync configuration
        auto_sync_config = self.config.get("auto_sync", {})
        if not auto_sync_config.get("enabled", False):
            raise ValueError(
                "Auto-sync is not enabled in config. "
                "Set auto_sync.enabled = true in ~/.config/agent-zot/config.json"
            )

        mode = auto_sync_config.get("mode", "hybrid")
        if mode not in ["hybrid", "watcher", "polling"]:
            raise ValueError(f"Invalid auto_sync mode: {mode}")

        # Initialize components
        queue_config = auto_sync_config.get("queue", {})
        self.update_queue = UpdateQueue(
            dedup_window_seconds=queue_config.get("dedup_window_seconds", 60),
            max_batch_size=queue_config.get("max_batch_size", 50)
        )

        self.orchestrator = UpdateOrchestrator(config_path=config_path)

        # File watcher (if enabled)
        self.file_watcher: Optional[FileWatcher] = None
        watcher_config = auto_sync_config.get("watcher", {})
        if mode in ["hybrid", "watcher"] and watcher_config.get("enabled", True):
            db_path = watcher_config.get("watch_path")
            if not db_path:
                raise ValueError(
                    "File watcher enabled but watch_path not configured. "
                    "Set auto_sync.watcher.watch_path in config"
                )

            self.file_watcher = FileWatcher(
                db_path=db_path,
                update_queue=self.update_queue,
                debounce_seconds=watcher_config.get("debounce_seconds", 30)
            )

        # API poller (if enabled)
        self.api_poller: Optional[APIPoller] = None
        polling_config = auto_sync_config.get("polling", {})
        if mode in ["hybrid", "polling"]:
            self.api_poller = APIPoller(
                update_queue=self.update_queue,
                poll_interval_seconds=polling_config.get("interval_seconds", 300),
                use_since_param=polling_config.get("use_since_param", True)
            )

        # State
        self.running = False
        self.mode = mode
        self._processor_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

        # Statistics
        self.stats = {
            "started_at": None,
            "total_jobs_processed": 0,
            "total_items_processed": 0,
        }

        logger.info(f"Daemon manager initialized (mode: {mode})")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            with open(self.config_path) as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {self.config_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            return {}

    def _cleanup_orphaned_processes(self) -> int:
        """
        Clean up orphaned 'agent-zot serve' processes.

        This prevents accumulation of old MCP server processes that can
        consume memory and cause issues. Mentioned in bugs.md Limitation #001.

        Returns:
            Number of processes killed
        """
        try:
            # Get current process PID to avoid killing ourselves
            current_pid = os.getpid()

            # Find all agent-zot serve processes
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                check=True
            )

            orphaned_pids: List[int] = []
            for line in result.stdout.splitlines():
                if "agent-zot serve" in line and str(current_pid) not in line:
                    # Extract PID (second column in ps aux output)
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            pid = int(parts[1])
                            orphaned_pids.append(pid)
                        except ValueError:
                            continue

            if orphaned_pids:
                logger.info(f"Found {len(orphaned_pids)} orphaned 'agent-zot serve' process(es): {orphaned_pids}")
                for pid in orphaned_pids:
                    try:
                        os.kill(pid, signal.SIGTERM)
                        logger.info(f"Killed orphaned process PID {pid}")
                    except ProcessLookupError:
                        logger.debug(f"Process {pid} already terminated")
                    except PermissionError:
                        logger.warning(f"No permission to kill process {pid}")

                return len(orphaned_pids)
            else:
                logger.debug("No orphaned 'agent-zot serve' processes found")
                return 0

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to check for orphaned processes: {e}")
            return 0
        except Exception as e:
            logger.error(f"Unexpected error during orphaned process cleanup: {e}")
            return 0

    async def start(self):
        """Start the daemon."""
        if self.running:
            logger.warning("Daemon already running")
            return

        # Clean up orphaned MCP server processes before starting
        cleaned = self._cleanup_orphaned_processes()
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} orphaned 'agent-zot serve' process(es)")

        self.running = True
        self.stats["started_at"] = datetime.now().isoformat()

        logger.info("Starting daemon components...")

        # Start file watcher
        if self.file_watcher:
            await self.file_watcher.start()
            logger.info("✓ File watcher started")

        # Start API poller
        if self.api_poller:
            await self.api_poller.start()
            logger.info("✓ API poller started")

        # Start processor loop
        self._processor_task = asyncio.create_task(self._process_loop())
        logger.info("✓ Processor loop started")

        # Setup signal handlers
        self._setup_signal_handlers()

        logger.info("🚀 Daemon started successfully")
        logger.info(
            f"Mode: {self.mode} | "
            f"File watcher: {self.file_watcher is not None} | "
            f"API poller: {self.api_poller is not None}"
        )

    async def stop(self):
        """Stop the daemon."""
        if not self.running:
            logger.warning("Daemon not running")
            return

        logger.info("Stopping daemon...")
        self.running = False
        self._shutdown_event.set()

        # Stop components
        if self.file_watcher:
            await self.file_watcher.stop()
            logger.info("✓ File watcher stopped")

        if self.api_poller:
            await self.api_poller.stop()
            logger.info("✓ API poller stopped")

        # Stop processor
        if self._processor_task and not self._processor_task.done():
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
            logger.info("✓ Processor stopped")

        logger.info("Daemon stopped")

    async def _process_loop(self):
        """Main processing loop - consumes queue and runs pipeline."""
        logger.info("Processor loop started")

        while self.running:
            try:
                # Wait for next job (with timeout to check shutdown)
                job = await self.update_queue.get_next_batch(timeout=1.0)

                if not job:
                    # No job available, continue waiting
                    continue

                # Process the job
                logger.info(
                    f"Processing job from {job.source}: "
                    f"{len(job.item_keys)} items"
                )

                stats = await self.orchestrator.process_update_job(job)

                # Update statistics
                self.stats["total_jobs_processed"] += 1
                self.stats["total_items_processed"] += stats.get("processed_items", 0)

                logger.info(
                    f"Job completed: processed={stats.get('processed_items', 0)}, "
                    f"added={stats.get('added_items', 0)}, "
                    f"skipped={stats.get('skipped_items', 0)}"
                )

            except asyncio.CancelledError:
                logger.debug("Processor loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in processor loop: {e}", exc_info=True)
                # Continue processing despite errors
                await asyncio.sleep(5)  # Brief pause before retry

        logger.info("Processor loop stopped")

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            # Schedule shutdown in event loop
            asyncio.create_task(self.stop())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def run(self):
        """Run the daemon (blocking)."""
        await self.start()

        # Wait for shutdown signal
        await self._shutdown_event.wait()

        await self.stop()

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive daemon status."""
        status = {
            "running": self.running,
            "mode": self.mode,
            "started_at": self.stats.get("started_at"),
            "queue": self.update_queue.get_stats(),
            "orchestrator": self.orchestrator.get_stats(),
            "file_watcher": self.file_watcher.get_status() if self.file_watcher else None,
            "api_poller": self.api_poller.get_status() if self.api_poller else None,
            "stats": {
                "total_jobs_processed": self.stats["total_jobs_processed"],
                "total_items_processed": self.stats["total_items_processed"],
            },
        }

        return status


async def run_daemon(config_path: Optional[str] = None):
    """
    Run the daemon (entry point for CLI).

    Args:
        config_path: Path to agent-zot config file
    """
    manager = DaemonManager(config_path=config_path)
    await manager.run()
