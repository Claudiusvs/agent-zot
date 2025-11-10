"""
Unified graph exploration tool for agent-zot MCP server.

This module provides intelligent graph exploration with automatic intent detection
and strategy selection across nine different exploration modes:
- Citation Chain Mode: Extended citation network traversal
- Influence Mode: PageRank-based influential paper ranking
- Content Similarity Mode: Vector-based 'More Like This' search
- Related Papers Mode: Shared entity connections
- Collaboration Mode: Co-authorship network exploration
- Concept Network Mode: Multi-hop concept relationship exploration
- Temporal Mode: Topic evolution tracking over time
- Venue Analysis Mode: Publication outlet ranking and statistics
- Comprehensive Mode: Multi-strategy combined exploration

The tool automatically detects query intent, extracts parameters, and selects
the optimal Neo4j traversal strategy for the given exploration task.
"""

from typing import Optional
from pathlib import Path
from fastmcp import Context


def zot_explore_graph(
    query: str,
    paper_key: Optional[str] = None,
    author: Optional[str] = None,
    concept: Optional[str] = None,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    field: Optional[str] = None,
    force_mode: Optional[str] = None,
    limit: int = 10,
    max_hops: int = 2,
    *,
    ctx: Context
) -> str:
    """
    Intelligent unified graph exploration tool.

    Automatically detects intent and selects optimal graph traversal strategy
    from nine different exploration modes. Handles citation networks, collaboration
    analysis, concept relationships, temporal trends, and more.

    Args:
        query: Natural language query describing what to explore
        paper_key: Optional paper key for citation/related paper queries
        author: Optional author name for collaboration queries
        concept: Optional concept for network/evolution queries
        start_year: Optional start year for temporal queries
        end_year: Optional end year for temporal queries
        field: Optional field filter for influence/venue queries
        force_mode: Optional mode override ("citation", "influence", "content_similarity",
                   "related", "collaboration", "concept", "temporal", "venue", "comprehensive")
        limit: Maximum number of results (default: 10)
        max_hops: Number of hops for multi-hop traversals (default: 2)
        ctx: MCP context for logging

    Returns:
        Markdown-formatted graph exploration results with mode and strategy info

    Examples:
        >>> # Citation chain exploration
        >>> zot_explore_graph("Find papers citing papers that cite ABC123", paper_key="ABC123")

        >>> # Find influential papers in a field
        >>> zot_explore_graph("Most influential papers in machine learning", field="machine learning")

        >>> # Content similarity search
        >>> zot_explore_graph("Find papers similar to XYZ456", paper_key="XYZ456")

        >>> # Collaboration network
        >>> zot_explore_graph("Who collaborated with John Smith?", author="John Smith")

        >>> # Concept evolution over time
        >>> zot_explore_graph("Track neural networks from 2010 to 2020",
        ...                   concept="neural networks", start_year=2010, end_year=2020)

        >>> # Venue analysis
        >>> zot_explore_graph("Top AI conferences", field="artificial intelligence")

        >>> # Comprehensive multi-strategy exploration
        >>> zot_explore_graph("Explore everything about deep learning", concept="deep learning")
    """
    try:
        from agent_zot.clients.zotero import get_zotero_client
        from agent_zot.search.semantic import create_semantic_search
        from agent_zot.search.unified_graph import smart_explore_graph

        ctx.info(f"Smart graph exploration: {query} (force_mode: {force_mode})")

        # Initialize Neo4j client
        config_path = Path.home() / ".config" / "agent-zot" / "config.json"
        search = create_semantic_search(str(config_path))

        # Check if Neo4j is available
        if not hasattr(search, 'neo4j_client') or search.neo4j_client is None:
            return """❌ Neo4j graph database is not available.

**Graph exploration requires Neo4j to be running.**

To enable graph features:
1. Start Neo4j: `docker start agent-zot-neo4j`
2. Verify connection: `docker exec agent-zot-neo4j cypher-shell -u neo4j -p demodemo "MATCH (n) RETURN count(n)"`

For content-based search, use `zot_search` instead."""

        neo4j_client = search.neo4j_client

        # Get Zotero client for Content Similarity Mode
        zot = get_zotero_client()

        # Call the smart exploration function
        result = smart_explore_graph(
            query=query,
            neo4j_client=neo4j_client,
            semantic_search_instance=search,  # For Content Similarity Mode
            zotero_client=zot,  # For Content Similarity Mode metadata
            paper_key=paper_key,
            author=author,
            concept=concept,
            start_year=start_year,
            end_year=end_year,
            field=field,
            force_mode=force_mode,
            limit=limit,
            max_hops=max_hops
        )

        # Format response
        if not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            suggestion = result.get("suggestion", "")
            return f"❌ Error: {error_msg}\n\n{suggestion}"

        # Build output
        output_parts = []

        # Add metadata header
        mode = result.get("mode", "unknown")
        strategy = result.get("strategy", "unknown")

        output_parts.append(f"# Graph Exploration (Mode: {mode.upper()})\n")
        output_parts.append(f"**Strategy:** {strategy}")

        if result.get("strategies_executed"):
            output_parts.append(f"**Strategies executed:** {result['strategies_executed']}")

        if result.get("extracted_params"):
            params = result["extracted_params"]
            if params:
                param_str = ", ".join(f"{k}={v}" for k, v in params.items())
                output_parts.append(f"**Extracted parameters:** {param_str}")

        if result.get("warning"):
            output_parts.append(f"\n⚠️ {result['warning']}")

        output_parts.append("\n---\n")

        # Add content
        output_parts.append(result.get("content", ""))

        # Add confidence info if available
        if "intent_confidence" in result:
            conf = result["intent_confidence"]
            output_parts.append(f"\n---\n\n*Intent detected with {conf:.0%} confidence*")

        return "\n".join(output_parts)

    except Exception as e:
        import traceback
        ctx.error(f"Smart graph exploration failed: {str(e)}")
        ctx.error(f"Traceback: {traceback.format_exc()}")
        return f"""❌ Error: {str(e)}

💡 Suggestion:
- Verify Neo4j is running: `docker ps | grep agent-zot-neo4j`
- For content search, use `zot_search` instead
- For specific graph operations, use individual tools like `zot_find_related_papers`"""
