"""
Async task infrastructure for long-running MCP operations.

Provides background execution to avoid Claude Desktop's 60-second timeout.
Supports: search, summarize, explore_graph
"""

from .task_manager import AsyncTaskManager, AsyncSearchTask
from .executor import AsyncTaskExecutor

# Backwards compatibility alias
AsyncSearchExecutor = AsyncTaskExecutor

__all__ = ["AsyncTaskManager", "AsyncSearchTask", "AsyncTaskExecutor", "AsyncSearchExecutor"]
