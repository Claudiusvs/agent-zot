"""
MCP tools module - importable tool implementations for code execution pattern.

This module provides importable Python functions that can be executed directly
in the user's environment, following Anthropic's MCP code execution pattern.

Each tool is exposed as a standalone Python module that can be imported and
executed without going through Claude's context window, enabling:
- 95-98% token reduction for large dataset workflows
- Direct data processing in execution environment
- Efficient filtering before results enter context

Usage:
    from agent_zot.mcp_tools.zot_search import zot_search

    results = zot_search(query="neural networks", limit=10)

Available Tools:
    - zot_search: Smart intent-driven paper search
    - zot_summarize: Multi-mode paper summarization
    - zot_explore_graph: Graph exploration and network analysis
    - zot_manage_collections: Collection management operations
    - zot_manage_tags: Tag management operations
    - zot_manage_notes: Notes and annotations management
    - zot_export: Export to markdown/bibtex/graphml
    - zot_manage_database: Database management operations
"""

__all__ = [
    "zot_search",
    "zot_summarize",
    "zot_explore_graph",
    "zot_manage_collections",
    "zot_manage_tags",
    "zot_manage_notes",
    "zot_export",
    "zot_manage_database",
]
