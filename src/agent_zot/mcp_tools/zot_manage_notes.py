"""
MCP Tool: zot_manage_notes - Unified notes and annotations management.

This module provides unified notes and annotations management with automatic
intent detection, supporting four execution modes:
- List Annotations Mode: Get PDF highlights and comments
- List Notes Mode: Get notes attached to items or library
- Search Mode: Search notes by text content
- Create Mode: Create new note for an item

Usage Examples:
    from agent_zot.mcp_tools.zot_manage_notes import zot_manage_notes

    # List annotations
    result = zot_manage_notes(
        query="list annotations for ABC12345",
        item_key="ABC12345"
    )

    # List notes
    result = zot_manage_notes(
        query="show my notes"
    )

    # Search notes
    result = zot_manage_notes(
        query="search for notes about methodology",
        query_text="methodology"
    )

    # Create note
    result = zot_manage_notes(
        query="create a note for ABC12345 titled 'Review comments'",
        item_key="ABC12345",
        note_title="Review comments",
        note_text="This paper presents a novel approach..."
    )

Parameters:
    query (str): Natural language query describing the operation
    item_key (Optional[str]): Zotero item key (8-character alphanumeric)
    note_title (Optional[str]): Title for new note (Create Mode)
    note_text (Optional[str]): Content for new note (Create Mode)
    tags (Optional[List[str]]): Tags to apply to new note (Create Mode)
    query_text (Optional[str]): Text to search for (Search Mode)
    limit (Optional[int]): Maximum number of results to return
    force_mode (Optional[str]): Force specific mode (annotations/notes/search/create)

Returns:
    dict: Result dictionary with keys:
        - success (bool): Whether the operation succeeded
        - content (str): Formatted results or confirmation message
        - error (Optional[str]): Error message if success is False
        - mode (str): Execution mode used

Execution Modes:
    1. List Annotations Mode - Get PDF highlights and comments
       - Query patterns: "list annotations", "show highlights"
       - Returns: Annotations with text, comments, page numbers

    2. List Notes Mode - Get notes attached to items or library
       - Query patterns: "show my notes", "list notes"
       - Returns: Notes with snippets and keys

    3. Search Mode - Search notes by text content
       - Query patterns: "search for notes", "find notes containing"
       - Returns: Matching notes with context

    4. Create Mode - Create new note for an item
       - Query patterns: "create a note", "add note"
       - Requires: item_key, note_title, note_text
       - Returns: Confirmation with note key

Smart Features:
    ✅ Automatic intent detection
    ✅ Works with items or entire library
    ✅ HTML formatting for rich notes
    ✅ Tag support for note organization
"""

from typing import Dict, List, Optional

from agent_zot.clients.zotero import get_zotero_client
from agent_zot.search.unified_notes import smart_manage_notes


def zot_manage_notes(
    query: str,
    item_key: Optional[str] = None,
    note_title: Optional[str] = None,
    note_text: Optional[str] = None,
    tags: Optional[List[str]] = None,
    query_text: Optional[str] = None,
    limit: Optional[int] = None,
    force_mode: Optional[str] = None,
) -> Dict:
    """
    Smart notes management with automatic intent detection.

    Args:
        query: Natural language query describing the operation
        item_key: Zotero item key (8-character alphanumeric)
        note_title: Title for new note (Create Mode)
        note_text: Content for new note (Create Mode)
        tags: Tags to apply to new note (Create Mode)
        query_text: Text to search for (Search Mode)
        limit: Maximum number of results to return
        force_mode: Force specific mode (annotations/notes/search/create)

    Returns:
        dict: Result dictionary with success, content, error, and mode keys

    Raises:
        ValueError: If required parameters are missing for the detected mode
        RuntimeError: If Zotero client initialization fails

    Examples:
        >>> # List annotations
        >>> result = zot_manage_notes(
        ...     query="list annotations for ABC12345",
        ...     item_key="ABC12345"
        ... )
        >>> print(result["content"])

        >>> # Search notes
        >>> result = zot_manage_notes(
        ...     query="search for notes about methodology",
        ...     query_text="methodology"
        ... )
        >>> print(result["content"])

        >>> # Create note
        >>> result = zot_manage_notes(
        ...     query="create a note for ABC12345",
        ...     item_key="ABC12345",
        ...     note_title="Review comments",
        ...     note_text="This paper presents...",
        ...     tags=["important", "review"]
        ... )
        >>> print(result["content"])
    """
    try:
        zot = get_zotero_client()
        result = smart_manage_notes(
            query=query,
            zotero_client=zot,
            item_key=item_key,
            note_title=note_title,
            note_text=note_text,
            tags=tags,
            query_text=query_text,
            limit=limit,
            force_mode=force_mode
        )
        return result
    except Exception as e:
        return {
            "success": False,
            "error": f"Error in zot_manage_notes: {str(e)}",
            "content": "",
            "mode": "error"
        }


__all__ = ["zot_manage_notes"]
