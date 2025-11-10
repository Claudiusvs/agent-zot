"""
Smart intent-driven search tool for agent-zot.

This module provides the zot_search tool, which automatically:
- Detects query intent (entity/relationship/metadata/semantic)
- Expands vague queries with domain-specific terms
- Selects optimal backend combination
- Escalates to comprehensive search if results are inadequate
- Provides result provenance (which backends found each paper)

Example usage:
    # Fast semantic search
    zot_search("papers about attention mechanisms", limit=10)

    # Entity-enriched search
    zot_search("which methods appear in papers about transformers?")

    # Metadata-enriched search
    zot_search("papers by Vaswani published in 2017")

    # Comprehensive search (automatic escalation)
    zot_search("comprehensive analysis of neural architectures")

    # Force specific mode
    zot_search("attention papers", force_mode="comprehensive")
"""

from typing import Optional
from pathlib import Path
from fastmcp import Context


def zot_search(
    query: str,
    limit: int = 10,
    force_mode: Optional[str] = None,
    *,
    ctx: Context
) -> str:
    """
    Perform intent-driven smart search with automatic backend selection.

    This is the recommended default search tool that replaces:
    - zot_semantic_search (Fast Mode)
    - zot_unified_search (Comprehensive Mode)
    - zot_refine_search (includes refinement)

    Args:
        query: Search query text
        limit: Maximum number of results to return (default: 10)
        force_mode: Optional mode override - "fast" or "comprehensive"
        ctx: MCP context

    Returns:
        Markdown-formatted search results with intent, mode, and provenance

    Examples:
        >>> # Simple concept search
        >>> zot_search("papers about neural networks", limit=5)

        >>> # Author-specific search
        >>> zot_search("papers by Geoffrey Hinton")

        >>> # Methodology search
        >>> zot_search("which methods are used in deep learning papers?")

        >>> # Force comprehensive mode
        >>> zot_search("attention mechanisms", force_mode="comprehensive")
    """
    try:
        if not query.strip():
            return "Error: Search query cannot be empty"

        ctx.info(f"Performing smart search for: '{query}'")

        # Import smart search module
        from agent_zot.search.unified_smart import smart_search
        from agent_zot.search.semantic import create_semantic_search

        # Determine config path
        config_path = Path.home() / ".config" / "agent-zot" / "config.json"

        # Create semantic search instance (needed by smart_search)
        search_instance = create_semantic_search(str(config_path))

        # Perform smart search
        results = smart_search(
            search_instance,
            query=query,
            limit=limit,
            force_mode=force_mode
        )

        if results.get("error"):
            return f"Smart search error: {results['error']}"

        search_results = results.get("results", [])

        if not search_results:
            return f"No items found for query: '{query}'"

        # Format results as markdown
        output = [f"# Smart Search Results for '{query}'", ""]

        # Show query expansion if it happened
        if expanded_query := results.get("expanded_query"):
            output.append(f"**Query expanded**: `{query}` → `{expanded_query}`")
            output.append("")

        # Show intent and mode
        intent = results.get("intent", "unknown")
        intent_confidence = results.get("intent_confidence", 0)
        mode = results.get("mode", "unknown")
        backends_used = results.get("backends_used", [])

        output.append(f"**Intent detected**: {intent} (confidence: {intent_confidence:.2f})")
        output.append(f"**Mode**: {mode}")
        output.append(f"**Backends used**: {', '.join(backends_used)}")
        output.append("")

        # Show quality metrics
        if quality := results.get("quality_metrics"):
            output.append(f"**Quality**: Confidence={quality['confidence']}, Coverage={quality['coverage']:.0%}")
            output.append("")

        output.append(f"Found {len(search_results)} items:")
        output.append("")

        for i, result in enumerate(search_results, 1):
            item_key = result.get("item_key", "")

            # Get Zotero item data
            zotero_item = result.get("zotero_item", {})
            data = zotero_item.get("data", {})

            title = data.get("title", "Untitled")
            creators = data.get("creators", [])

            # Format creators
            from agent_zot.utils.common import format_creators
            creators_str = format_creators(creators)

            # Get scores
            similarity = result.get("similarity_score")
            rrf_score = result.get("rrf_score")

            # Get provenance
            found_in = result.get("found_in", [])

            output.append(f"## {i}. {title}")
            output.append("")
            output.append(f"- **Item Key**: `{item_key}`")
            if creators_str:
                output.append(f"- **Authors**: {creators_str}")

            # Show scores
            if similarity:
                output.append(f"- **Similarity**: {similarity:.3f}")
            if rrf_score:
                output.append(f"- **RRF Score**: {rrf_score:.4f}")

            # Show provenance
            if found_in:
                output.append(f"- **Found in**: {', '.join(found_in)}")

            # Add year and type
            if year := data.get("date"):
                output.append(f"- **Year**: {year}")
            if item_type := data.get("itemType"):
                output.append(f"- **Type**: {item_type}")

            output.append("")

        # Show any errors
        if errors := results.get("errors_by_backend"):
            output.append("## Backend Errors")
            output.append("")
            for backend, error in errors.items():
                output.append(f"- **{backend}**: {error}")
            output.append("")

        output.append("---")
        output.append(f"💡 **Tip**: Use `zot_summarize(item_key, query)` to read specific papers")

        return "\n".join(output)

    except Exception as e:
        ctx.error(f"Smart search failed: {str(e)}")
        import traceback
        return f"Error performing smart search: {str(e)}\n\n{traceback.format_exc()}"
