"""
MCP Tool: zot_manage_collections - Unified collections and library browsing management.

This module provides importable Python function for direct code execution,
following Anthropic's MCP code execution pattern. This enables:
- 95-98% token reduction for large dataset workflows
- Direct data processing in execution environment
- Efficient filtering before results enter context

**Replaces 6 legacy tools:**
- zot_get_collections → List Mode
- zot_create_collection → Create Mode
- zot_get_collection_items → Show Items Mode
- zot_add_to_collection → Add Mode
- zot_remove_from_collection → Remove Mode
- zot_get_recent → Recent Mode (library maintenance utility)

**Six Execution Modes (automatic detection):**

**1. List Mode** - List all collections
   - Query: "list all collections", "show my collections", "what collections do I have"
   - Returns: All collections with hierarchy and item counts

**2. Create Mode** - Create a new collection
   - Query: "create a new collection called 'Machine Learning'", "make collection Research"
   - Requires: collection_name parameter or extracted from query
   - Optional: parent_collection_key for nested collections
   - Returns: Confirmation with new collection key

**3. Show Items Mode** - Show items in a specific collection
   - Query: "show items in ML collection", "what's in the Research collection"
   - Requires: collection_key or collection_name
   - Optional: limit for result count
   - Returns: Items in collection with metadata

**4. Add Mode** - Add items to a collection
   - Query: "add ABC12345 to ML collection", "add items to Research collection"
   - Requires: collection_key (or collection_name) and item_keys
   - Returns: Confirmation with added item count

**5. Remove Mode** - Remove items from a collection
   - Query: "remove ABC12345 from ML collection", "remove items from collection"
   - Requires: collection_key (or collection_name) and item_keys
   - Returns: Confirmation with removed item count

**6. Recent Mode** - Show recently added/modified items (library maintenance utility)
   - Query: "show recent items", "what did I just import", "recently added papers"
   - Optional: limit for result count (default: 10)
   - Returns: Items sorted by date added to Zotero (not publication date)

**Smart Features:**
✅ Automatic intent detection from natural language
✅ Parameter extraction (collection names, item keys) from query text
✅ Collection key lookup by name
✅ Hierarchical collection support (parent/child)
✅ Batch operations for adding/removing multiple items

Usage:
    from agent_zot.mcp_tools.zot_manage_collections import zot_manage_collections

    # List all collections
    result = zot_manage_collections(query="list all collections")

    # Create new collection
    result = zot_manage_collections(
        query="create collection",
        collection_name="Machine Learning"
    )

    # Show items in collection
    result = zot_manage_collections(
        query="show items",
        collection_key="ABC123XYZ"
    )

    # Add items to collection
    result = zot_manage_collections(
        query="add items to collection",
        collection_key="ABC123XYZ",
        item_keys=["ITEM1", "ITEM2", "ITEM3"]
    )

    # Show recent items
    result = zot_manage_collections(
        query="show recent items",
        limit=20
    )
"""

from typing import Optional, List, Dict, Any
from agent_zot.search.unified_collections import smart_manage_collections
from agent_zot.clients.zotero import get_zotero_client


def zot_manage_collections(
    query: str,
    collection_key: Optional[str] = None,
    collection_name: Optional[str] = None,
    item_keys: Optional[List[str]] = None,
    parent_collection_key: Optional[str] = None,
    limit: Optional[int] = None,
    force_mode: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Unified collections and library browsing management with automatic intent detection.

    This function intelligently routes your query to the appropriate collection operation:
    List, Create, Show Items, Add, Remove, or Recent Mode.

    Args:
        query: Natural language query describing the desired operation
               Examples:
               - "list all collections"
               - "create collection called Research"
               - "show items in ML collection"
               - "add ABC12345 to collection"
               - "remove XYZ67890 from collection"
               - "show recent items"

        collection_key: Optional collection key for operations requiring a specific collection
                       Used for: Show Items, Add, Remove modes

        collection_name: Optional collection name (alternative to collection_key)
                        System will look up the key by name
                        Used for: Create, Show Items, Add, Remove modes

        item_keys: Optional list of item keys for batch operations
                  Used for: Add, Remove modes
                  Example: ["ABC12345", "XYZ67890", "DEF34567"]

        parent_collection_key: Optional parent collection key for nested collections
                              Used for: Create mode to create subcollections

        limit: Optional result limit for Show Items and Recent modes
              Default varies by mode (typically 10-100)

        force_mode: Optional mode override to skip intent detection
                   Valid values: "list", "create", "show_items", "add", "remove", "recent"
                   Use sparingly - automatic detection is preferred

    Returns:
        Dict with structure:
        {
            "success": bool,
            "content": str,  # Formatted output (when success=True)
            "error": str,    # Error message (when success=False)
            "mode": str,     # Detected/executed mode
            "data": dict     # Raw data (optional, mode-dependent)
        }

    Examples:
        >>> # List all collections
        >>> result = zot_manage_collections("list collections")
        >>> print(result["content"])

        >>> # Create nested collection
        >>> result = zot_manage_collections(
        ...     query="create new collection",
        ...     collection_name="Deep Learning",
        ...     parent_collection_key="ML_PARENT_KEY"
        ... )

        >>> # Show items with limit
        >>> result = zot_manage_collections(
        ...     query="show items",
        ...     collection_key="ABC123XYZ",
        ...     limit=50
        ... )

        >>> # Add multiple items
        >>> result = zot_manage_collections(
        ...     query="add items to collection",
        ...     collection_name="Research Papers",
        ...     item_keys=["ITEM1", "ITEM2", "ITEM3"]
        ... )

        >>> # Recent items with custom limit
        >>> result = zot_manage_collections(
        ...     query="what did I just import",
        ...     limit=25
        ... )

    Raises:
        Exception: If Zotero client initialization fails or underlying operation fails
                  All exceptions are caught and returned in result["error"]
    """
    try:
        zot = get_zotero_client()
        result = smart_manage_collections(
            query=query,
            zotero_client=zot,
            collection_key=collection_key,
            collection_name=collection_name,
            item_keys=item_keys,
            parent_collection_key=parent_collection_key,
            limit=limit,
            force_mode=force_mode
        )
        return result
    except Exception as e:
        return {
            "success": False,
            "error": f"Error in zot_manage_collections: {str(e)}",
            "content": ""
        }
