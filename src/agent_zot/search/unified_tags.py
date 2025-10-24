"""
Unified Tags Management Tool

Consolidates 3 legacy tag tools into a single intelligent tool:
- zot_get_tags → smart_manage_tags (List Mode)
- zot_search_by_tag → smart_manage_tags (Search Mode)
- zot_batch_update_tags → smart_manage_tags (Add/Remove Mode)

Created: 2025-10-25
Architecture: Natural language intent detection + automatic mode selection
"""

import re
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


# ========== Intent Detection Patterns ==========

# List Mode patterns
LIST_PATTERNS = [
    r'\b(list|show|get|display)\s+(all\s+)?(my\s+)?tags?\b',
    r'\bwhat\s+tags?\s+(do\s+I\s+have|exist)\b',
    r'\btags?\s+in\s+(my\s+)?library\b',
    r'\ball\s+tags?\b',
]

# Search Mode patterns
SEARCH_PATTERNS = [
    r'\bsearch\s+(for\s+)?(items?|papers?)\s+(by|with|tagged)\s+tag',
    r'\bfind\s+(items?|papers?)\s+(with|tagged)\s+tag',
    r'\b(items?|papers?)\s+tagged\s+(with\s+)?',
    r'\btag\s+filter',
    r'\bwhere\s+tag',
]

# Add Mode patterns
ADD_PATTERNS = [
    r'\badd\s+tag',
    r'\btag\s+(items?|papers?)\s+(as|with)',
    r'\bapply\s+tag',
    r'\bset\s+tag',
]

# Remove Mode patterns
REMOVE_PATTERNS = [
    r'\bremove\s+tag',
    r'\bdelete\s+tag',
    r'\buntag',
    r'\bclear\s+tag',
]


def detect_tag_intent(query: str) -> tuple[str, float, Dict[str, Any]]:
    """
    Detect tag operation intent from natural language query.

    Args:
        query: Natural language query

    Returns:
        Tuple of (intent, confidence, extracted_params)
        - intent: "list", "search", "add", "remove"
        - confidence: 0.0-1.0
        - extracted_params: Dict with extracted tags, keys, etc.
    """
    query_lower = query.lower()
    extracted_params = {}

    # Extract tags from query (look for quoted strings or words after "tag")
    tag_pattern = r'(?:tag[s]?\s+)(?:"([^"]+)"|\'([^\']+)\'|(\S+))'
    tag_matches = re.findall(tag_pattern, query_lower)
    if tag_matches:
        tags = [m[0] or m[1] or m[2] for m in tag_matches]
        extracted_params["tags"] = tags

    # Extract item keys (8-character uppercase alphanumeric)
    key_pattern = r'\b([A-Z0-9]{8})\b'
    key_matches = re.findall(key_pattern, query)
    if key_matches:
        extracted_params["item_keys"] = key_matches

    # Check Add patterns first (most specific)
    for pattern in ADD_PATTERNS:
        if re.search(pattern, query_lower):
            return ("add", 0.90, extracted_params)

    # Check Remove patterns
    for pattern in REMOVE_PATTERNS:
        if re.search(pattern, query_lower):
            return ("remove", 0.90, extracted_params)

    # Check Search patterns
    for pattern in SEARCH_PATTERNS:
        if re.search(pattern, query_lower):
            return ("search", 0.85, extracted_params)

    # Check List patterns
    for pattern in LIST_PATTERNS:
        if re.search(pattern, query_lower):
            return ("list", 0.80, extracted_params)

    # Default to list if query is very short
    if len(query.split()) <= 2:
        return ("list", 0.60, extracted_params)

    # Default fallback
    return ("list", 0.50, extracted_params)


# ========== Mode Implementations ==========

def run_list_mode(
    zotero_client,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    List Mode: List all tags in the library.

    Args:
        zotero_client: Zotero API client
        limit: Maximum number of tags to return

    Returns:
        Dict with success, mode, content, tags_found
    """
    try:
        logger.info(f"List Mode: Fetching all tags (limit={limit})")

        # Get tags from Zotero
        tags = zotero_client.tags(limit=limit)

        if not tags:
            return {
                "success": True,
                "mode": "list",
                "content": "No tags found in your Zotero library.",
                "tags_found": 0
            }

        # Build output
        output = ["# Zotero Tags", ""]

        # Sort by tag name
        sorted_tags = sorted(tags, key=lambda x: x.get("tag", "").lower())

        for tag_data in sorted_tags:
            tag = tag_data.get("tag", "")
            # Some tags have metadata like numItems
            if "meta" in tag_data:
                num_items = tag_data["meta"].get("numItems", "?")
                output.append(f"- **{tag}** ({num_items} items)")
            else:
                output.append(f"- **{tag}**")

        output.append("")
        output.append(f"**Total Tags:** {len(sorted_tags)}")

        return {
            "success": True,
            "mode": "list",
            "content": "\n".join(output),
            "tags_found": len(sorted_tags)
        }

    except Exception as e:
        logger.error(f"List Mode error: {e}")
        return {
            "success": False,
            "mode": "list",
            "error": f"Failed to list tags: {str(e)}"
        }


def run_search_mode(
    zotero_client,
    tags: List[str],
    item_type: str = "-attachment",
    limit: Optional[int] = 50
) -> Dict[str, Any]:
    """
    Search Mode: Search for items by tag(s).

    Supports advanced operators:
    - Disjunction: "tag1 || tag2" (OR)
    - Exclusion: "-tag" (NOT)
    - AND logic across separate tag conditions

    Args:
        zotero_client: Zotero API client
        tags: List of tag expressions (can include ||, -)
        item_type: Item type filter (default: "-attachment")
        limit: Maximum number of items to return

    Returns:
        Dict with success, mode, content, items_found
    """
    try:
        logger.info(f"Search Mode: Searching by tags={tags}, limit={limit}")

        if not tags:
            return {
                "success": False,
                "mode": "search",
                "error": "No tags provided for search"
            }

        # Search using Zotero API
        items = zotero_client.items(tag=tags, itemType=item_type, limit=limit)

        if not items:
            tag_str = ", ".join(tags)
            return {
                "success": True,
                "mode": "search",
                "content": f"No items found with tag(s): {tag_str}",
                "items_found": 0
            }

        # Build output
        tag_str = ", ".join(tags)
        output = [f"# Items Tagged with: {tag_str}", ""]

        for i, item in enumerate(items, 1):
            data = item.get("data", {})
            title = data.get("title", "Untitled")
            item_type_val = data.get("itemType", "unknown")
            key = item.get("key", "")

            # Format creators
            creators = data.get("creators", [])
            if creators:
                authors = []
                for creator in creators[:3]:  # Limit to first 3
                    last = creator.get("lastName", "")
                    first = creator.get("firstName", "")
                    if last:
                        authors.append(f"{last}, {first}" if first else last)
                creators_str = "; ".join(authors)
                if len(creators) > 3:
                    creators_str += " et al."
            else:
                creators_str = "No authors"

            # Item tags
            item_tags = data.get("tags", [])
            tag_names = [t.get("tag", "") for t in item_tags]
            tags_str = ", ".join(tag_names) if tag_names else "No tags"

            output.append(f"## {i}. {title}")
            output.append(f"**Item Key:** {key}")
            output.append(f"**Type:** {item_type_val}")
            output.append(f"**Authors:** {creators_str}")
            output.append(f"**Tags:** {tags_str}")
            output.append("")

        output.append(f"**Total Items:** {len(items)}")

        return {
            "success": True,
            "mode": "search",
            "content": "\n".join(output),
            "items_found": len(items)
        }

    except Exception as e:
        logger.error(f"Search Mode error: {e}")
        return {
            "success": False,
            "mode": "search",
            "error": f"Failed to search by tag: {str(e)}"
        }


def run_add_mode(
    zotero_client,
    item_keys: List[str],
    tags: List[str]
) -> Dict[str, Any]:
    """
    Add Mode: Add tag(s) to specified items.

    Args:
        zotero_client: Zotero API client
        item_keys: List of item keys to tag
        tags: List of tags to add

    Returns:
        Dict with success, mode, content, items_updated
    """
    try:
        logger.info(f"Add Mode: Adding tags {tags} to {len(item_keys)} items")

        if not item_keys:
            return {
                "success": False,
                "mode": "add",
                "error": "No item keys provided"
            }

        if not tags:
            return {
                "success": False,
                "mode": "add",
                "error": "No tags provided"
            }

        # Update each item
        updated_count = 0
        errors = []

        for key in item_keys:
            try:
                # Get current item
                item = zotero_client.item(key)
                data = item.get("data", {})

                # Get existing tags
                existing_tags = data.get("tags", [])
                existing_tag_names = {t.get("tag", "").lower() for t in existing_tags}

                # Add new tags (avoid duplicates)
                for tag in tags:
                    if tag.lower() not in existing_tag_names:
                        existing_tags.append({"tag": tag})

                # Update item
                data["tags"] = existing_tags
                zotero_client.update_item(data)
                updated_count += 1

            except Exception as e:
                errors.append(f"Failed to update {key}: {str(e)}")
                logger.warning(f"Failed to update item {key}: {e}")

        # Build output
        output = []
        tags_str = ", ".join(tags)

        if updated_count > 0:
            output.append(f"✓ Successfully added tag(s) '{tags_str}' to {updated_count} item(s)")

        if errors:
            output.append(f"\n⚠️ Errors ({len(errors)}):")
            for err in errors[:5]:  # Limit to first 5 errors
                output.append(f"  - {err}")
            if len(errors) > 5:
                output.append(f"  ... and {len(errors) - 5} more errors")

        return {
            "success": updated_count > 0,
            "mode": "add",
            "content": "\n".join(output),
            "items_updated": updated_count,
            "errors": len(errors)
        }

    except Exception as e:
        logger.error(f"Add Mode error: {e}")
        return {
            "success": False,
            "mode": "add",
            "error": f"Failed to add tags: {str(e)}"
        }


def run_remove_mode(
    zotero_client,
    item_keys: List[str],
    tags: List[str]
) -> Dict[str, Any]:
    """
    Remove Mode: Remove tag(s) from specified items.

    Args:
        zotero_client: Zotero API client
        item_keys: List of item keys to untag
        tags: List of tags to remove

    Returns:
        Dict with success, mode, content, items_updated
    """
    try:
        logger.info(f"Remove Mode: Removing tags {tags} from {len(item_keys)} items")

        if not item_keys:
            return {
                "success": False,
                "mode": "remove",
                "error": "No item keys provided"
            }

        if not tags:
            return {
                "success": False,
                "mode": "remove",
                "error": "No tags provided"
            }

        # Update each item
        updated_count = 0
        errors = []
        tags_lower = {t.lower() for t in tags}

        for key in item_keys:
            try:
                # Get current item
                item = zotero_client.item(key)
                data = item.get("data", {})

                # Get existing tags
                existing_tags = data.get("tags", [])

                # Remove specified tags
                filtered_tags = [
                    t for t in existing_tags
                    if t.get("tag", "").lower() not in tags_lower
                ]

                # Only update if tags were actually removed
                if len(filtered_tags) < len(existing_tags):
                    data["tags"] = filtered_tags
                    zotero_client.update_item(data)
                    updated_count += 1

            except Exception as e:
                errors.append(f"Failed to update {key}: {str(e)}")
                logger.warning(f"Failed to update item {key}: {e}")

        # Build output
        output = []
        tags_str = ", ".join(tags)

        if updated_count > 0:
            output.append(f"✓ Successfully removed tag(s) '{tags_str}' from {updated_count} item(s)")
        else:
            output.append(f"ℹ️ No items were updated (tags may not exist on specified items)")

        if errors:
            output.append(f"\n⚠️ Errors ({len(errors)}):")
            for err in errors[:5]:  # Limit to first 5 errors
                output.append(f"  - {err}")
            if len(errors) > 5:
                output.append(f"  ... and {len(errors) - 5} more errors")

        return {
            "success": updated_count > 0 or len(errors) == 0,
            "mode": "remove",
            "content": "\n".join(output),
            "items_updated": updated_count,
            "errors": len(errors)
        }

    except Exception as e:
        logger.error(f"Remove Mode error: {e}")
        return {
            "success": False,
            "mode": "remove",
            "error": f"Failed to remove tags: {str(e)}"
        }


# ========== Main Unified Function ==========

def smart_manage_tags(
    query: str,
    zotero_client,
    tags: Optional[List[str]] = None,
    item_keys: Optional[List[str]] = None,
    item_type: Optional[str] = "-attachment",
    limit: Optional[int] = None,
    force_mode: Optional[str] = None
) -> Dict[str, Any]:
    """
    Intelligent unified tags management tool.

    Automatically detects intent and routes to appropriate mode:
    - List Mode: List all tags in library
    - Search Mode: Search items by tag(s)
    - Add Mode: Add tag(s) to items
    - Remove Mode: Remove tag(s) from items

    Args:
        query: Natural language query describing desired operation
        zotero_client: Zotero API client instance
        tags: Optional list of tags (extracted from query if not provided)
        item_keys: Optional list of item keys (extracted from query if not provided)
        item_type: Item type filter for search (default: "-attachment")
        limit: Maximum results for list/search operations
        force_mode: Force specific mode ("list", "search", "add", "remove")

    Returns:
        Dict with:
        - success: bool
        - mode: str (execution mode used)
        - content: str (formatted output) OR error: str
        - Additional mode-specific fields

    Examples:
        >>> smart_manage_tags("list all tags", zot)
        # Lists all tags in library

        >>> smart_manage_tags("find papers tagged with 'important'", zot)
        # Searches items with 'important' tag

        >>> smart_manage_tags("add tag 'reviewed' to ABC12345", zot)
        # Adds 'reviewed' tag to specified item

        >>> smart_manage_tags("remove tag 'draft' from ABC12345 XYZ67890", zot)
        # Removes 'draft' tag from two items
    """
    try:
        # Detect intent if not forced
        if force_mode:
            intent = force_mode
            confidence = 1.0
            extracted_params = {}
            logger.info(f"Forced mode: {force_mode}")
        else:
            intent, confidence, extracted_params = detect_tag_intent(query)
            logger.info(f"Detected intent: {intent} (confidence: {confidence:.2f})")

        # Merge extracted parameters with explicit parameters
        # Explicit parameters take precedence
        final_tags = tags or extracted_params.get("tags", [])
        final_item_keys = item_keys or extracted_params.get("item_keys", [])

        # Route to appropriate mode
        if intent == "list":
            return run_list_mode(
                zotero_client=zotero_client,
                limit=limit
            )

        elif intent == "search":
            if not final_tags:
                return {
                    "success": False,
                    "mode": "search",
                    "error": "No tags found in query. Provide tags explicitly or in query text."
                }

            return run_search_mode(
                zotero_client=zotero_client,
                tags=final_tags,
                item_type=item_type,
                limit=limit or 50
            )

        elif intent == "add":
            if not final_tags:
                return {
                    "success": False,
                    "mode": "add",
                    "error": "No tags found in query. Provide tags to add."
                }

            if not final_item_keys:
                return {
                    "success": False,
                    "mode": "add",
                    "error": "No item keys found in query. Provide item keys to tag."
                }

            return run_add_mode(
                zotero_client=zotero_client,
                item_keys=final_item_keys,
                tags=final_tags
            )

        elif intent == "remove":
            if not final_tags:
                return {
                    "success": False,
                    "mode": "remove",
                    "error": "No tags found in query. Provide tags to remove."
                }

            if not final_item_keys:
                return {
                    "success": False,
                    "mode": "remove",
                    "error": "No item keys found in query. Provide item keys to untag."
                }

            return run_remove_mode(
                zotero_client=zotero_client,
                item_keys=final_item_keys,
                tags=final_tags
            )

        else:
            return {
                "success": False,
                "error": f"Unknown intent: {intent}"
            }

    except Exception as e:
        logger.error(f"smart_manage_tags error: {e}")
        return {
            "success": False,
            "error": f"Unified tags management failed: {str(e)}"
        }
