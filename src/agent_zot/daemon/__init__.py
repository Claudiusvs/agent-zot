"""
Agent-Zot Daemon - Auto-sync for Zotero library changes.

This module provides:
- Update queue with deduplication
- File system watcher for Zotero SQLite database
- Polling service for Zotero API changes
- Daemon process management
"""

from agent_zot.daemon.queue import UpdateQueue
from agent_zot.daemon.watcher import FileWatcher
from agent_zot.daemon.poller import APIPoller
from agent_zot.daemon.manager import DaemonManager

__all__ = [
    "UpdateQueue",
    "FileWatcher",
    "APIPoller",
    "DaemonManager",
]
