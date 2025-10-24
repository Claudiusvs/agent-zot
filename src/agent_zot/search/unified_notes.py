"""
Unified Notes Management Tool

Consolidates 4 legacy note tools into a single intelligent tool:
- zot_get_annotations → smart_manage_notes (List Annotations Mode)
- zot_get_notes → smart_manage_notes (List Notes Mode)
- zot_search_notes → smart_manage_notes (Search Mode)
- zot_create_note → smart_manage_notes (Create Mode)

Created: 2025-10-25
Architecture: Natural language intent detection + automatic mode selection
"""

import re
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


# ========== Intent Detection Patterns ==========

# List Annotations Mode patterns
LIST_ANNOTATIONS_PATTERNS = [
    r'\b(list|show|get|display)\s+(all\s+)?(my\s+)?annotations?\b',
    r'\bhighlights?\s+(from|in|for)\b',
    r'\bPDF\s+annotations?\b',
    r'\bextract\s+annotations?\b',
]

# List Notes Mode patterns
LIST_NOTES_PATTERNS = [
    r'\b(list|show|get|display)\s+(all\s+)?(my\s+)?notes?\b',
    r'\bwhat\s+notes?\s+(do\s+I\s+have|exist)\b',
    r'\bnotes?\s+in\s+(my\s+)?library\b',
    r'\bnotes?\s+for\s+(item|paper)\b',
]

# Search Mode patterns
SEARCH_PATTERNS = [
    r'\bsearch\s+(for\s+)?notes?\b',
    r'\bfind\s+notes?\s+(with|containing)\b',
    r'\blook\s+for\s+notes?\b',
]

# Create Mode patterns
CREATE_PATTERNS = [
    r'\bcreate\s+(a\s+)?(new\s+)?note\b',
    r'\badd\s+(a\s+)?(new\s+)?note\b',
    r'\bmake\s+(a\s+)?(new\s+)?note\b',
    r'\bwrite\s+(a\s+)?(new\s+)?note\b',
]


def detect_note_intent(query: str) -> tuple[str, float, Dict[str, Any]]:
    """
    Detect note operation intent from natural language query.

    Args:
        query: Natural language query

    Returns:
        Tuple of (intent, confidence, extracted_params)
        - intent: "list_annotations", "list_notes", "search", "create"
        - confidence: 0.0-1.0
        - extracted_params: Dict with extracted item keys, text, etc.
    """
    query_lower = query.lower()
    extracted_params = {}

    # Extract item keys (8-character uppercase alphanumeric)
    key_pattern = r'\b([A-Z0-9]{8})\b'
    key_matches = re.findall(key_pattern, query)
    if key_matches:
        extracted_params["item_key"] = key_matches[0]  # Take first match

    # Check Create patterns first (most specific)
    for pattern in CREATE_PATTERNS:
        if re.search(pattern, query_lower):
            return ("create", 0.90, extracted_params)

    # Check Search patterns
    for pattern in SEARCH_PATTERNS:
        if re.search(pattern, query_lower):
            return ("search", 0.85, extracted_params)

    # Check List Annotations patterns
    for pattern in LIST_ANNOTATIONS_PATTERNS:
        if re.search(pattern, query_lower):
            return ("list_annotations", 0.80, extracted_params)

    # Check List Notes patterns
    for pattern in LIST_NOTES_PATTERNS:
        if re.search(pattern, query_lower):
            return ("list_notes", 0.80, extracted_params)

    # Default to list notes if query is short
    if len(query.split()) <= 2:
        return ("list_notes", 0.60, extracted_params)

    # Default fallback
    return ("list_notes", 0.50, extracted_params)


# ========== Mode Implementations ==========

def run_list_annotations_mode(
    zotero_client,
    item_key: Optional[str] = None,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    List Annotations Mode: Get annotations for item or entire library.

    Args:
        zotero_client: Zotero API client
        item_key: Optional item key to get annotations for
        limit: Maximum number of annotations to return

    Returns:
        Dict with success, mode, content, annotations_found
    """
    try:
        if item_key:
            logger.info(f"List Annotations Mode: Fetching for item {item_key}")
        else:
            logger.info(f"List Annotations Mode: Fetching all annotations (limit={limit})")

        # Get annotations
        if item_key:
            # Get annotations for specific item
            item = zotero_client.item(item_key)
            children = zotero_client.children(item_key)
            annotations = [
                child for child in children
                if child.get("data", {}).get("itemType") == "annotation"
            ]
        else:
            # Get all annotations across library
            annotations = zotero_client.items(itemType="annotation", limit=limit)

        if not annotations:
            scope = f"item {item_key}" if item_key else "your library"
            return {
                "success": True,
                "mode": "list_annotations",
                "content": f"No annotations found for {scope}.",
                "annotations_found": 0
            }

        # Build output
        if item_key:
            output = [f"# Annotations for Item: {item_key}", ""]
        else:
            output = ["# Zotero Annotations", ""]

        for i, annotation in enumerate(annotations, 1):
            data = annotation.get("data", {})
            annotation_text = data.get("annotationText", "")
            annotation_comment = data.get("annotationComment", "")
            annotation_color = data.get("annotationColor", "")
            annotation_type = data.get("annotationType", "highlight")
            page_label = data.get("annotationPageLabel", "")

            output.append(f"## Annotation {i}")

            if annotation_type:
                output.append(f"**Type:** {annotation_type}")

            if page_label:
                output.append(f"**Page:** {page_label}")

            if annotation_color:
                output.append(f"**Color:** {annotation_color}")

            if annotation_text:
                output.append(f"**Text:** {annotation_text}")

            if annotation_comment:
                output.append(f"**Comment:** {annotation_comment}")

            output.append("")

        output.append(f"**Total Annotations:** {len(annotations)}")

        return {
            "success": True,
            "mode": "list_annotations",
            "content": "\n".join(output),
            "annotations_found": len(annotations)
        }

    except Exception as e:
        logger.error(f"List Annotations Mode error: {e}")
        return {
            "success": False,
            "mode": "list_annotations",
            "error": f"Failed to list annotations: {str(e)}"
        }


def run_list_notes_mode(
    zotero_client,
    item_key: Optional[str] = None,
    limit: Optional[int] = 20
) -> Dict[str, Any]:
    """
    List Notes Mode: Get notes for item or entire library.

    Args:
        zotero_client: Zotero API client
        item_key: Optional item key to get notes for
        limit: Maximum number of notes to return

    Returns:
        Dict with success, mode, content, notes_found
    """
    try:
        if item_key:
            logger.info(f"List Notes Mode: Fetching for item {item_key}")
        else:
            logger.info(f"List Notes Mode: Fetching all notes (limit={limit})")

        # Get notes
        if item_key:
            # Get notes for specific item
            children = zotero_client.children(item_key)
            notes = [
                child for child in children
                if child.get("data", {}).get("itemType") == "note"
            ]
        else:
            # Get all notes across library
            notes = zotero_client.items(itemType="note", limit=limit)

        if not notes:
            scope = f"item {item_key}" if item_key else "your library"
            return {
                "success": True,
                "mode": "list_notes",
                "content": f"No notes found for {scope}.",
                "notes_found": 0
            }

        # Build output
        if item_key:
            output = [f"# Notes for Item: {item_key}", ""]
        else:
            output = ["# Zotero Notes", ""]

        for i, note in enumerate(notes, 1):
            data = note.get("data", {})
            note_text = data.get("note", "")
            key = note.get("key", "")

            # Extract title from note content (first line or first 50 chars)
            if note_text:
                # Remove HTML tags for title
                import re
                plain_text = re.sub(r'<[^>]+>', '', note_text)
                title = plain_text.split('\n')[0][:50]
                if len(plain_text.split('\n')[0]) > 50:
                    title += "..."
            else:
                title = "Empty note"

            output.append(f"## {i}. {title}")
            output.append(f"**Note Key:** {key}")

            if note_text:
                # Show snippet of note content
                snippet = note_text[:200] + "..." if len(note_text) > 200 else note_text
                output.append(f"**Content:**\n{snippet}")

            output.append("")

        output.append(f"**Total Notes:** {len(notes)}")

        return {
            "success": True,
            "mode": "list_notes",
            "content": "\n".join(output),
            "notes_found": len(notes)
        }

    except Exception as e:
        logger.error(f"List Notes Mode error: {e}")
        return {
            "success": False,
            "mode": "list_notes",
            "error": f"Failed to list notes: {str(e)}"
        }


def run_search_mode(
    zotero_client,
    query_text: str,
    limit: Optional[int] = 20
) -> Dict[str, Any]:
    """
    Search Mode: Search for notes by text content.

    Args:
        zotero_client: Zotero API client
        query_text: Text to search for in notes
        limit: Maximum number of results to return

    Returns:
        Dict with success, mode, content, notes_found
    """
    try:
        logger.info(f"Search Mode: Searching for notes with '{query_text}'")

        # Search notes
        zotero_client.add_parameters(q=query_text, itemType="note", limit=limit)
        notes = zotero_client.items()

        if not notes:
            return {
                "success": True,
                "mode": "search",
                "content": f"No notes found matching: '{query_text}'",
                "notes_found": 0
            }

        # Build output
        output = [f"# Notes Matching: '{query_text}'", ""]

        for i, note in enumerate(notes, 1):
            data = note.get("data", {})
            note_text = data.get("note", "")
            key = note.get("key", "")

            # Extract title
            if note_text:
                import re
                plain_text = re.sub(r'<[^>]+>', '', note_text)
                title = plain_text.split('\n')[0][:50]
                if len(plain_text.split('\n')[0]) > 50:
                    title += "..."
            else:
                title = "Empty note"

            output.append(f"## {i}. {title}")
            output.append(f"**Note Key:** {key}")

            if note_text:
                # Show snippet with search context
                snippet = note_text[:300] + "..." if len(note_text) > 300 else note_text
                output.append(f"**Content:**\n{snippet}")

            output.append("")

        output.append(f"**Total Matches:** {len(notes)}")

        return {
            "success": True,
            "mode": "search",
            "content": "\n".join(output),
            "notes_found": len(notes)
        }

    except Exception as e:
        logger.error(f"Search Mode error: {e}")
        return {
            "success": False,
            "mode": "search",
            "error": f"Failed to search notes: {str(e)}"
        }


def run_create_mode(
    zotero_client,
    item_key: str,
    note_title: str,
    note_text: str,
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Create Mode: Create a new note for an item.

    Args:
        zotero_client: Zotero API client
        item_key: Item key to attach note to
        note_title: Title of the note
        note_text: Content of the note
        tags: Optional list of tags for the note

    Returns:
        Dict with success, mode, content, note_key
    """
    try:
        logger.info(f"Create Mode: Creating note for item {item_key}")

        # Build note content (combine title and text)
        full_note_content = f"<h1>{note_title}</h1>\n<p>{note_text}</p>"

        # Build note payload
        note_template = zotero_client.item_template("note")
        note_template["note"] = full_note_content
        note_template["parentItem"] = item_key

        if tags:
            note_template["tags"] = [{"tag": tag} for tag in tags]

        # Create the note
        result = zotero_client.create_items([note_template])

        if result and "successful" in result and result["successful"]:
            note_key = result["successful"]["0"]["key"]
            return {
                "success": True,
                "mode": "create",
                "content": f"✓ Note created successfully\n**Title:** {note_title}\n**Note Key:** {note_key}\n**Parent Item:** {item_key}",
                "note_key": note_key
            }
        else:
            return {
                "success": False,
                "mode": "create",
                "error": f"Failed to create note. Result: {result}"
            }

    except Exception as e:
        logger.error(f"Create Mode error: {e}")
        return {
            "success": False,
            "mode": "create",
            "error": f"Failed to create note: {str(e)}"
        }


# ========== Main Unified Function ==========

def smart_manage_notes(
    query: str,
    zotero_client,
    item_key: Optional[str] = None,
    note_title: Optional[str] = None,
    note_text: Optional[str] = None,
    tags: Optional[List[str]] = None,
    query_text: Optional[str] = None,
    limit: Optional[int] = None,
    force_mode: Optional[str] = None
) -> Dict[str, Any]:
    """
    Intelligent unified notes management tool.

    Automatically detects intent and routes to appropriate mode:
    - List Annotations Mode: Get annotations from PDFs
    - List Notes Mode: Get notes for item or library
    - Search Mode: Search notes by text
    - Create Mode: Create new note

    Args:
        query: Natural language query describing desired operation
        zotero_client: Zotero API client instance
        item_key: Optional item key (for list modes and create)
        note_title: Note title (for create mode)
        note_text: Note content (for create mode)
        tags: Optional tags for note (for create mode)
        query_text: Search query text (for search mode)
        limit: Maximum results for list/search operations
        force_mode: Force specific mode ("list_annotations", "list_notes", "search", "create")

    Returns:
        Dict with:
        - success: bool
        - mode: str (execution mode used)
        - content: str (formatted output) OR error: str
        - Additional mode-specific fields

    Examples:
        >>> smart_manage_notes("list all annotations for ABC12345", zot)
        # Lists annotations for specified item

        >>> smart_manage_notes("show my notes", zot)
        # Lists all notes in library

        >>> smart_manage_notes("search for notes about machine learning", zot)
        # Searches notes for matching text

        >>> smart_manage_notes("create a note for ABC12345 titled 'Review comments'", zot,
                               note_text="This paper is excellent")
        # Creates new note attached to item
    """
    try:
        # Detect intent if not forced
        if force_mode:
            intent = force_mode
            confidence = 1.0
            extracted_params = {}
            logger.info(f"Forced mode: {force_mode}")
        else:
            intent, confidence, extracted_params = detect_note_intent(query)
            logger.info(f"Detected intent: {intent} (confidence: {confidence:.2f})")

        # Merge extracted parameters with explicit parameters
        final_item_key = item_key or extracted_params.get("item_key")

        # Route to appropriate mode
        if intent == "list_annotations":
            return run_list_annotations_mode(
                zotero_client=zotero_client,
                item_key=final_item_key,
                limit=limit
            )

        elif intent == "list_notes":
            return run_list_notes_mode(
                zotero_client=zotero_client,
                item_key=final_item_key,
                limit=limit or 20
            )

        elif intent == "search":
            # Extract search query from the query text if not provided
            if not query_text:
                # Try to extract text after "search for notes" or similar
                match = re.search(r'search.*?notes?\s+(?:for|about|containing)\s+(.+)', query.lower())
                if match:
                    query_text = match.group(1).strip()
                else:
                    # Fallback: use entire query
                    query_text = query

            return run_search_mode(
                zotero_client=zotero_client,
                query_text=query_text,
                limit=limit or 20
            )

        elif intent == "create":
            if not final_item_key:
                return {
                    "success": False,
                    "mode": "create",
                    "error": "No item key found. Provide item key to attach note to."
                }

            if not note_title:
                return {
                    "success": False,
                    "mode": "create",
                    "error": "No note title provided. Provide a title for the note."
                }

            if not note_text:
                return {
                    "success": False,
                    "mode": "create",
                    "error": "No note text provided. Provide content for the note."
                }

            return run_create_mode(
                zotero_client=zotero_client,
                item_key=final_item_key,
                note_title=note_title,
                note_text=note_text,
                tags=tags
            )

        else:
            return {
                "success": False,
                "error": f"Unknown intent: {intent}"
            }

    except Exception as e:
        logger.error(f"smart_manage_notes error: {e}")
        return {
            "success": False,
            "error": f"Unified notes management failed: {str(e)}"
        }
