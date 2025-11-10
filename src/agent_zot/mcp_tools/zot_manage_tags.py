"""
MCP Tool: zot_manage_tags

Unified tags management with natural language interface.

This tool consolidates 3 legacy tag tools into a single intelligent interface:
- zot_get_tags → List Mode
- zot_search_by_tag → Search Mode
- zot_batch_update_tags → Add/Remove Mode

Four Execution Modes (automatic detection):
1. List Mode - List all tags in library
2. Search Mode - Find items by tag(s) with advanced operators
3. Add Mode - Add tag(s) to items (batch operation)
4. Remove Mode - Remove tag(s) from items (batch operation)

Created: 2025-11-10
Part of: MCP Tools Extraction (OpenSpec 2025-11-10-002)
"""

from typing import Optional, List
from mcp.server.fastmcp import Context


def zot_manage_tags(
    query: str,
    tags: Optional[List[str]] = None,
    item_keys: Optional[List[str]] = None,
    item_type: Optional[str] = "-attachment",
    limit: Optional[int] = None,
    force_mode: Optional[str] = None,
    *,
    ctx: Context
) -> str:
    """
    Smart tags management with automatic intent detection.

    This unified tool automatically detects your intent from natural language queries
    and executes the appropriate tag operation.

    Args:
        query: Natural language query describing the tag operation
        tags: Optional list of tag names (extracted automatically from query if not provided)
        item_keys: Optional list of Zotero item keys for Add/Remove operations
        item_type: Item type filter for Search mode (default: "-attachment")
        limit: Maximum number of results for List/Search modes
        force_mode: Force specific mode ("list", "search", "add", "remove")
        ctx: MCP context

    Returns:
        str: Formatted result or error message

    Examples:
        List Mode:
            >>> zot_manage_tags("list all tags")
            >>> zot_manage_tags("show my tags")
            >>> zot_manage_tags("what tags do I have")

        Search Mode:
            >>> zot_manage_tags("find papers tagged with 'important'")
            >>> zot_manage_tags("items with tag urgent")
            >>> zot_manage_tags("search tag:important || tag:review")
            >>> zot_manage_tags("items tagged -draft")  # Exclude draft tag

        Add Mode:
            >>> zot_manage_tags("add tag 'reviewed' to ABC12345")
            >>> zot_manage_tags("tag XYZ67890 as important")
            >>> zot_manage_tags("apply tags", tags=["reviewed", "final"], item_keys=["ABC12345"])

        Remove Mode:
            >>> zot_manage_tags("remove tag 'draft' from ABC12345")
            >>> zot_manage_tags("untag XYZ67890")
            >>> zot_manage_tags("delete tags", tags=["draft"], item_keys=["ABC12345"])

    Smart Features:
        ✅ Automatic intent detection from natural language
        ✅ Parameter extraction (tags, item keys) from query text
        ✅ Batch operations across multiple items
        ✅ Advanced search operators (||, -)
        ✅ Duplicate prevention when adding tags

    Mode Selection Logic:
        - List Mode: Queries like "list tags", "show tags", "all tags"
        - Search Mode: Queries with "find", "search", "tagged with"
        - Add Mode: Queries with "add tag", "tag as", "apply tag"
        - Remove Mode: Queries with "remove tag", "delete tag", "untag"

    Raises:
        Exception: On Zotero API errors or invalid parameters
    """
    try:
        from agent_zot.search.unified_tags import smart_manage_tags
        from agent_zot.core.server import get_zotero_client

        zot = get_zotero_client()
        result = smart_manage_tags(
            query=query,
            zotero_client=zot,
            tags=tags,
            item_keys=item_keys,
            item_type=item_type,
            limit=limit,
            force_mode=force_mode
        )
        return result.get("content", "Error") if result.get("success") else f"❌ {result.get('error')}"
    except Exception as e:
        return f"Error: {str(e)}"
