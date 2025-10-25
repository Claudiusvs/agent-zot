"""
Unified intelligent collections management tool for Agent-Zot.

Consolidates all collection management tools into a single intelligent interface that
automatically detects intent and executes the appropriate collection operation.

Six Execution Modes:
1. List Mode - List all collections in the library
2. Create Mode - Create a new collection
3. Show Items Mode - Show items in a specific collection
4. Add Mode - Add items to a collection
5. Remove Mode - Remove items from a collection
6. Recent Mode - Show recently added/modified items (library maintenance utility)

Replaces 6 legacy tools:
- zot_get_collections → List Mode
- zot_create_collection → Create Mode
- zot_get_collection_items → Show Items Mode
- zot_add_to_collection → Add Mode
- zot_remove_from_collection → Remove Mode
- zot_get_recent → Recent Mode
"""

import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Intent detection patterns
LIST_PATTERNS = [
    r'\b(list|show|get|display)\s+(all\s+)?(my\s+)?collections?\b',
    r'\bwhat\s+collections?\s+(do\s+I\s+have|exist)\b',
    r'\bcollections?\s+list\b',
]

CREATE_PATTERNS = [
    r'\bcreate\s+(a\s+)?(new\s+)?collection\b',
    r'\bmake\s+(a\s+)?(new\s+)?collection\b',
    r'\badd\s+(a\s+)?(new\s+)?collection\b',
    r'\bnew\s+collection\s+(called|named)\b',
]

SHOW_ITEMS_PATTERNS = [
    r'\bshow\s+(items?|papers?|contents?)\s+(in|of|from)\s+.*\bcollection\b',  # Must mention collection
    r'\b(list|get|display)\s+(items?|papers?|contents?)\s+(in|of|from)\s+.*\bcollection\b',  # Must mention collection
    r'\bwhat\'?s\s+in\s+(the\s+)?.*\bcollection\b',  # "what's in the ML collection"
    r'\bcollection\s+contents?\b',  # "collection contents"
]

ADD_PATTERNS = [
    r'\badd\s+(papers?|items?)\b.*\b(to|into)\s+.*\bcollection\b',  # "add items X to the ML collection"
    r'\bput\s+(papers?|items?)\b.*\b(in|into)\s+.*\bcollection\b',  # "put paper X in the Research collection"
    r'\bmove\s+(papers?|items?)\b.*\bto\s+.*\bcollection\b',  # "move items X to collection Y"
]

REMOVE_PATTERNS = [
    r'\bremove\s+(papers?|items?)\b.*\bfrom\s+.*\bcollection\b',  # "remove items X from the ML collection"
    r'\bdelete\s+(papers?|items?)\b.*\bfrom\s+.*\bcollection\b',  # "delete papers X from collection Y"
    r'\btake\s+(papers?|items?)\b.*\bout\s+of\s+.*\bcollection\b',  # "take items out of collection"
    r'\btake\s+out\b.*\bfrom\s+.*\bcollection\b',  # "take out X from the NLP collection" (phrasal verb)
]

RECENT_PATTERNS = [
    r'\b(recent|latest)\s+(items?|papers?|additions?)\b',  # "recent papers", "latest items"
    r'\b(show|list|get|display)\s+.*\b(recent|latest)\b',  # "show 20 recent", "list recent papers"
    r'\bwhat\s+(did\s+i|have\s+i)\s+.*(add|import|just)',  # "what did I just import" (lowercase i)
    r'\brecent(ly)?\s+added\b',  # "recently added"
    r'\bjust\s+(added|imported)\b',  # "just added"
]


def detect_collection_intent(query: str) -> tuple[str, float, Dict[str, Any]]:
    """
    Detect what collection operation the user wants to perform.

    Returns:
        Tuple of (intent, confidence, extracted_params) where intent is one of:
        - "list" - List all collections
        - "create" - Create a new collection
        - "show_items" - Show items in a collection
        - "add" - Add items to a collection
        - "remove" - Remove items from a collection
        - "recent" - Show recently added items
    """
    query_lower = query.lower()
    extracted_params = {}

    # Check Recent patterns (high priority - specific intent)
    for pattern in RECENT_PATTERNS:
        if re.search(pattern, query_lower):
            # Extract limit if specified
            limit_match = re.search(r'(\d+)\s+(recent|latest|last)', query_lower)
            if limit_match:
                extracted_params["limit"] = int(limit_match.group(1))
            logger.info(f"Detected RECENT intent: pattern '{pattern}' matched")
            return ("recent", 0.90, extracted_params)

    # Check List patterns (highest priority for simple queries)
    for pattern in LIST_PATTERNS:
        if re.search(pattern, query_lower):
            logger.info(f"Detected LIST intent: pattern '{pattern}' matched")
            return ("list", 0.90, extracted_params)

    # Check Create patterns
    for pattern in CREATE_PATTERNS:
        if re.search(pattern, query_lower):
            # Extract collection name
            # Try "collection called/named 'X'" pattern
            name_match = re.search(r'collection\s+(?:called|named)\s+["\']?([^"\']+?)["\']?(?:\s|$)', query_lower)
            if not name_match:
                # Try "create collection 'X'" pattern
                name_match = re.search(r'(?:create|make|add|new)\s+(?:a\s+)?(?:new\s+)?collection\s+["\']?([^"\']+?)["\']?(?:\s|$)', query_lower)

            if name_match:
                extracted_params["collection_name"] = name_match.group(1).strip()

            logger.info(f"Detected CREATE intent: pattern '{pattern}' matched")
            return ("create", 0.85, extracted_params)

    # Check Show Items patterns
    for pattern in SHOW_ITEMS_PATTERNS:
        if re.search(pattern, query_lower):
            # Extract collection name
            name_match = re.search(r'(?:in|of|from)\s+(?:the\s+)?(?:collection\s+)?["\']?([^"\']+?)["\']?(?:\s|$)', query_lower)
            if name_match:
                extracted_params["collection_name"] = name_match.group(1).strip()

            logger.info(f"Detected SHOW_ITEMS intent: pattern '{pattern}' matched")
            return ("show_items", 0.85, extracted_params)

    # Check Add patterns
    for pattern in ADD_PATTERNS:
        if re.search(pattern, query_lower):
            # Extract collection name
            name_match = re.search(r'(?:to|into)\s+(?:the\s+)?(?:collection\s+)?["\']?([^"\']+?)["\']?(?:\s|$)', query_lower)
            if name_match:
                extracted_params["collection_name"] = name_match.group(1).strip()

            # Extract item keys (format: ABCD1234 or similar 8-char uppercase alphanumeric)
            item_keys = re.findall(r'\b([A-Z0-9]{8})\b', query)
            if item_keys:
                extracted_params["item_keys"] = item_keys

            logger.info(f"Detected ADD intent: pattern '{pattern}' matched")
            return ("add", 0.85, extracted_params)

    # Check Remove patterns
    for pattern in REMOVE_PATTERNS:
        if re.search(pattern, query_lower):
            # Extract collection name
            name_match = re.search(r'from\s+(?:the\s+)?(?:collection\s+)?["\']?([^"\']+?)["\']?(?:\s|$)', query_lower)
            if name_match:
                extracted_params["collection_name"] = name_match.group(1).strip()

            # Extract item keys
            item_keys = re.findall(r'\b([A-Z0-9]{8})\b', query)
            if item_keys:
                extracted_params["item_keys"] = item_keys

            logger.info(f"Detected REMOVE intent: pattern '{pattern}' matched")
            return ("remove", 0.85, extracted_params)

    # Default: list collections (safest fallback)
    logger.info("No specific intent detected, defaulting to LIST")
    return ("list", 0.60, extracted_params)


def fuzzy_match_collection(zotero_client, collection_name: str) -> Optional[Dict[str, Any]]:
    """
    Fuzzy match collection name to actual collection.

    Returns collection dict with 'key' and 'data' fields, or None if not found.
    """
    try:
        collections = zotero_client.collections()

        # First try exact match (case-insensitive)
        for coll in collections:
            coll_name = coll.get('data', {}).get('name', '')
            if coll_name.lower() == collection_name.lower():
                return coll

        # Then try partial match
        for coll in collections:
            coll_name = coll.get('data', {}).get('name', '')
            if collection_name.lower() in coll_name.lower():
                return coll

        return None
    except Exception as e:
        logger.error(f"Error fuzzy matching collection: {e}")
        return None


def run_list_mode(zotero_client, limit: Optional[int] = None) -> Dict[str, Any]:
    """List Mode: List all collections in the library."""
    logger.info("Running LIST Mode")

    try:
        collections = zotero_client.collections()

        if limit:
            collections = collections[:limit]

        if not collections:
            return {
                "success": True,
                "mode": "list",
                "content": "# Collections\n\nNo collections found in your library.",
                "collections_found": 0
            }

        # Format as markdown
        output = [f"# Collections ({len(collections)} total)\n"]

        for i, coll in enumerate(collections, 1):
            name = coll.get('data', {}).get('name', 'Unnamed')
            key = coll.get('key', '')
            parent_key = coll.get('data', {}).get('parentCollection', None)

            indent = "  " if parent_key else ""
            output.append(f"{indent}{i}. **{name}**")
            output.append(f"{indent}   - **Key**: `{key}`")
            if parent_key:
                output.append(f"{indent}   - **Parent**: `{parent_key}`")
            output.append("")

        return {
            "success": True,
            "mode": "list",
            "content": "\n".join(output),
            "collections_found": len(collections)
        }

    except Exception as e:
        logger.error(f"List Mode failed: {e}")
        return {
            "success": False,
            "mode": "list",
            "error": str(e)
        }


def run_create_mode(zotero_client, collection_name: str, parent_collection_key: Optional[str] = None) -> Dict[str, Any]:
    """Create Mode: Create a new collection."""
    logger.info(f"Running CREATE Mode: collection_name='{collection_name}'")

    if not collection_name:
        return {
            "success": False,
            "mode": "create",
            "error": "Collection name is required. Example: 'Create collection \"My Papers\"'"
        }

    try:
        # Create collection
        from pyzotero import zotero

        template = zotero_client.collection_template()
        template['name'] = collection_name

        if parent_collection_key:
            template['parentCollection'] = parent_collection_key

        result = zotero_client.create_collections([template])

        if not result or not result.get('success'):
            return {
                "success": False,
                "mode": "create",
                "error": f"Failed to create collection '{collection_name}'"
            }

        # Get the created collection key
        created_key = result.get('success', {}).get('0', '')

        output = [f"# Collection Created\n"]
        output.append(f"Successfully created collection: **{collection_name}**")
        output.append(f"- **Key**: `{created_key}`")
        if parent_collection_key:
            output.append(f"- **Parent Collection**: `{parent_collection_key}`")

        return {
            "success": True,
            "mode": "create",
            "content": "\n".join(output),
            "collection_name": collection_name,
            "collection_key": created_key
        }

    except Exception as e:
        logger.error(f"Create Mode failed: {e}")
        return {
            "success": False,
            "mode": "create",
            "error": str(e)
        }


def run_show_items_mode(zotero_client, collection_key: str, limit: Optional[int] = 50) -> Dict[str, Any]:
    """Show Items Mode: Show items in a specific collection."""
    logger.info(f"Running SHOW_ITEMS Mode: collection_key='{collection_key}'")

    if not collection_key:
        return {
            "success": False,
            "mode": "show_items",
            "error": "Collection key is required. Use 'list collections' to find the key."
        }

    try:
        items = zotero_client.collection_items(collection_key, limit=limit)

        if not items:
            return {
                "success": True,
                "mode": "show_items",
                "content": f"# Collection Items\n\nNo items found in collection `{collection_key}`.",
                "items_found": 0
            }

        # Format as markdown
        output = [f"# Collection Items ({len(items)} items)\n"]
        output.append(f"**Collection Key**: `{collection_key}`\n")

        for i, item in enumerate(items, 1):
            title = item.get('data', {}).get('title', 'Untitled')
            key = item.get('key', '')
            item_type = item.get('data', {}).get('itemType', 'unknown')

            creators = item.get('data', {}).get('creators', [])
            authors_str = ", ".join([c.get('lastName', '') for c in creators[:3]])
            if len(creators) > 3:
                authors_str += " et al."

            year = item.get('data', {}).get('date', '')
            if year and len(year) >= 4:
                year = year[:4]

            output.append(f"## {i}. {title}")
            if authors_str:
                output.append(f"- **Authors**: {authors_str}")
            if year:
                output.append(f"- **Year**: {year}")
            output.append(f"- **Type**: {item_type}")
            output.append(f"- **Key**: `{key}`")
            output.append("")

        return {
            "success": True,
            "mode": "show_items",
            "content": "\n".join(output),
            "items_found": len(items),
            "collection_key": collection_key
        }

    except Exception as e:
        logger.error(f"Show Items Mode failed: {e}")
        return {
            "success": False,
            "mode": "show_items",
            "error": str(e)
        }


def run_add_mode(zotero_client, collection_key: str, item_keys: List[str]) -> Dict[str, Any]:
    """Add Mode: Add items to a collection."""
    logger.info(f"Running ADD Mode: collection_key='{collection_key}', item_keys={item_keys}")

    if not collection_key:
        return {
            "success": False,
            "mode": "add",
            "error": "Collection key is required."
        }

    if not item_keys:
        return {
            "success": False,
            "mode": "add",
            "error": "At least one item key is required."
        }

    try:
        # Add items to collection
        result = zotero_client.addto_collection(collection_key, item_keys)

        output = [f"# Items Added to Collection\n"]
        output.append(f"Successfully added {len(item_keys)} item(s) to collection `{collection_key}`")
        output.append(f"\n**Items added:**")
        for key in item_keys:
            output.append(f"- `{key}`")

        return {
            "success": True,
            "mode": "add",
            "content": "\n".join(output),
            "collection_key": collection_key,
            "items_added": len(item_keys)
        }

    except Exception as e:
        logger.error(f"Add Mode failed: {e}")
        return {
            "success": False,
            "mode": "add",
            "error": str(e)
        }


def run_remove_mode(zotero_client, collection_key: str, item_keys: List[str]) -> Dict[str, Any]:
    """Remove Mode: Remove items from a collection."""
    logger.info(f"Running REMOVE Mode: collection_key='{collection_key}', item_keys={item_keys}")

    if not collection_key:
        return {
            "success": False,
            "mode": "remove",
            "error": "Collection key is required."
        }

    if not item_keys:
        return {
            "success": False,
            "mode": "remove",
            "error": "At least one item key is required."
        }

    try:
        # Remove items from collection
        result = zotero_client.deletefromcollection(collection_key, item_keys)

        output = [f"# Items Removed from Collection\n"]
        output.append(f"Successfully removed {len(item_keys)} item(s) from collection `{collection_key}`")
        output.append(f"\n**Items removed:**")
        for key in item_keys:
            output.append(f"- `{key}`")

        return {
            "success": True,
            "mode": "remove",
            "content": "\n".join(output),
            "collection_key": collection_key,
            "items_removed": len(item_keys)
        }

    except Exception as e:
        logger.error(f"Remove Mode failed: {e}")
        return {
            "success": False,
            "mode": "remove",
            "error": str(e)
        }


def run_recent_mode(zotero_client, limit: int = 10) -> Dict[str, Any]:
    """Recent Mode: Show recently added/modified items from your library."""
    logger.info(f"Running RECENT Mode: limit={limit}")

    try:
        # Ensure limit is reasonable
        if limit <= 0:
            limit = 10
        elif limit > 100:
            limit = 100

        # Get recent items sorted by dateAdded
        items = zotero_client.items(limit=limit, sort="dateAdded", direction="desc")

        if not items:
            return {
                "success": True,
                "mode": "recent",
                "content": "No items found in your Zotero library.",
                "items_found": 0
            }

        # Format creators helper
        def format_creators(creators):
            if not creators:
                return "No authors"
            author_list = []
            for creator in creators[:3]:  # Limit to first 3 authors
                last = creator.get("lastName", "")
                first = creator.get("firstName", "")
                if last and first:
                    author_list.append(f"{last}, {first}")
                elif last:
                    author_list.append(last)
            if len(creators) > 3:
                author_list.append("et al.")
            return "; ".join(author_list) if author_list else "No authors"

        # Format as markdown
        output = [f"# {limit} Most Recently Added Items\n"]

        for i, item in enumerate(items, 1):
            data = item.get("data", {})
            title = data.get("title", "Untitled")
            item_type = data.get("itemType", "unknown")
            date = data.get("date", "No date")
            key = item.get("key", "")
            date_added = data.get("dateAdded", "Unknown")

            creators_str = format_creators(data.get("creators", []))

            output.append(f"## {i}. {title}")
            output.append(f"**Type:** {item_type}")
            output.append(f"**Item Key:** `{key}`")
            output.append(f"**Date:** {date}")
            output.append(f"**Added:** {date_added}")
            output.append(f"**Authors:** {creators_str}")
            output.append("")  # Empty line between items

        return {
            "success": True,
            "mode": "recent",
            "content": "\n".join(output),
            "items_found": len(items)
        }

    except Exception as e:
        logger.error(f"Recent Mode failed: {e}")
        return {
            "success": False,
            "mode": "recent",
            "error": str(e)
        }


def smart_manage_collections(
    query: str,
    zotero_client,
    collection_key: Optional[str] = None,
    collection_name: Optional[str] = None,
    item_keys: Optional[List[str]] = None,
    parent_collection_key: Optional[str] = None,
    limit: Optional[int] = None,
    force_mode: Optional[str] = None
) -> Dict[str, Any]:
    """
    Intelligent unified collections management tool.

    Automatically detects intent and executes the appropriate collection operation:
    - List all collections
    - Create a new collection
    - Show items in a collection
    - Add items to a collection
    - Remove items from a collection
    - Show recently added items (library maintenance utility)

    Args:
        query: User's natural language query
        zotero_client: Pyzotero client instance
        collection_key: Optional collection key (overrides name-based lookup)
        collection_name: Optional collection name for fuzzy matching
        item_keys: Optional list of item keys to add/remove
        parent_collection_key: Optional parent collection for nested collections
        limit: Optional limit for list/show/recent operations
        force_mode: Optional mode override ("list", "create", "show_items", "add", "remove", "recent")

    Returns:
        Dict with:
        - success: bool
        - mode: str (which mode was used)
        - content: str (formatted markdown output)
        - error: str (if failed)
        - Additional metadata
    """
    logger.info(f"smart_manage_collections called with query: '{query}'")

    # Detect intent
    if force_mode:
        mode = force_mode
        confidence = 1.0
        extracted_params = {}
        logger.info(f"Force mode: {mode}")
    else:
        mode, confidence, extracted_params = detect_collection_intent(query)
        logger.info(f"Detected intent: {mode} (confidence: {confidence:.2f})")

    # Override with explicit parameters if provided
    if collection_name and "collection_name" not in extracted_params:
        extracted_params["collection_name"] = collection_name
    if item_keys and "item_keys" not in extracted_params:
        extracted_params["item_keys"] = item_keys

    # Route to appropriate mode
    if mode == "list":
        return run_list_mode(zotero_client, limit=limit)

    elif mode == "create":
        coll_name = extracted_params.get("collection_name", collection_name)
        return run_create_mode(zotero_client, coll_name, parent_collection_key)

    elif mode == "recent":
        # Use extracted limit if available, otherwise use explicit parameter
        recent_limit = extracted_params.get("limit", limit if limit else 10)
        return run_recent_mode(zotero_client, limit=recent_limit)

    elif mode in ["show_items", "add", "remove"]:
        # Resolve collection key (either explicit or fuzzy match from name)
        resolved_key = collection_key

        if not resolved_key:
            coll_name = extracted_params.get("collection_name", collection_name)
            if coll_name:
                matched_coll = fuzzy_match_collection(zotero_client, coll_name)
                if matched_coll:
                    resolved_key = matched_coll.get('key')
                    logger.info(f"Fuzzy matched '{coll_name}' to collection '{resolved_key}'")
                else:
                    return {
                        "success": False,
                        "mode": mode,
                        "error": f"Could not find collection matching '{coll_name}'. Use 'list collections' to see available collections."
                    }
            else:
                return {
                    "success": False,
                    "mode": mode,
                    "error": "Collection name or key is required. Example: 'Show items in collection \"Literature Review\"'"
                }

        if mode == "show_items":
            return run_show_items_mode(zotero_client, resolved_key, limit=limit)

        elif mode == "add":
            items = extracted_params.get("item_keys", item_keys)
            return run_add_mode(zotero_client, resolved_key, items)

        elif mode == "remove":
            items = extracted_params.get("item_keys", item_keys)
            return run_remove_mode(zotero_client, resolved_key, items)

    else:
        return {
            "success": False,
            "error": f"Unknown mode: {mode}. Must be one of: list, create, show_items, add, remove, recent"
        }
