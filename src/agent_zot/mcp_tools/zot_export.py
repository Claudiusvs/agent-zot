"""
Export Tool - Unified export functionality with automatic format detection.

This module provides the zot_export tool that consolidates three legacy export tools:
- zot_export_markdown → Markdown Mode
- zot_export_bibtex → BibTeX Mode
- zot_export_graph → GraphML Mode

The tool automatically detects the output format from file extensions or explicit parameters
and routes to the appropriate export mode implementation.

Created: 2025-01-10
Extracted from: server.py (unified export section)
Part of: MCP tools extraction project
"""

from typing import Optional, List
from fastmcp import Context


def zot_export(
    output_file: str,
    format: Optional[str] = None,
    query: Optional[str] = None,
    collection_key: Optional[str] = None,
    include_fulltext: bool = False,
    node_types: Optional[List[str]] = None,
    max_nodes: Optional[int] = None,
    limit: int = 1000,
    *,
    ctx: Context
) -> str:
    """
    Smart export with automatic format detection.

    Unified export tool that automatically detects the output format and routes
    to the appropriate export mode:

    **Three Execution Modes (automatic detection):**

    **1. Markdown Mode** - Export to markdown files with YAML frontmatter
       - File extension: .md, .markdown OR format="markdown"
       - Query: "export to papers.md", output_file="research/"
       - Returns: Individual .md files with frontmatter
       - Obsidian-compatible format

    **2. BibTeX Mode** - Export to .bib file
       - File extension: .bib, .bibtex OR format="bibtex"
       - Query: "export to refs.bib", output_file="citations.bib"
       - Returns: Single .bib file with all entries
       - LaTeX-compatible format

    **3. GraphML Mode** - Export Neo4j knowledge graph
       - File extension: .graphml, .xml OR format="graphml"
       - Query: "export graph to network.graphml"
       - Returns: GraphML file for Gephi/Cytoscape
       - Requires Neo4j GraphRAG enabled

    Args:
        output_file: Output file path (or directory for markdown mode)
        format: Optional explicit format ("markdown", "bibtex", "graphml")
        query: Search query to filter items (markdown/bibtex modes)
        collection_key: Collection key to export from (markdown/bibtex modes)
        include_fulltext: Include full PDF text (markdown mode only)
        node_types: Node types to export (graphml mode only)
        max_nodes: Maximum nodes to export (graphml mode only)
        limit: Maximum items to export (default: 1000)
        ctx: MCP context

    Returns:
        Success message with export details or error message

    Examples:
        >>> # Export collection to markdown
        >>> zot_export(
        ...     output_file="papers/",
        ...     collection_key="ABC123",
        ...     format="markdown",
        ...     ctx=ctx
        ... )
        "✓ Exported 50 items to Markdown..."

        >>> # Export search results to BibTeX
        >>> zot_export(
        ...     output_file="refs.bib",
        ...     query="machine learning",
        ...     ctx=ctx
        ... )
        "✓ Exported 25 items to BibTeX..."

        >>> # Export graph to GraphML
        >>> zot_export(
        ...     output_file="network.graphml",
        ...     node_types=["Paper", "Author"],
        ...     max_nodes=100,
        ...     ctx=ctx
        ... )
        "✓ Exported Neo4j graph to GraphML..."

    **Smart Features:**
    ✅ Automatic format detection from file extension
    ✅ Filter by query or collection
    ✅ Optional full-text inclusion (markdown)
    ✅ Node type filtering (graphml)
    ✅ Batch export (up to 1000 items default)

    **Use for:** All export operations - citations, documentation, network analysis
    """
    try:
        from agent_zot.core.server import get_zotero_client, get_neo4j_client
        from agent_zot.search.unified_export import smart_export

        zot = get_zotero_client()

        # Get Neo4j client if available
        neo4j = None
        try:
            neo4j = get_neo4j_client()
        except:
            pass  # Neo4j not available

        result = smart_export(
            output_file=output_file,
            zotero_client=zot,
            neo4j_client=neo4j,
            format=format,
            query=query,
            collection_key=collection_key,
            include_fulltext=include_fulltext,
            node_types=node_types,
            max_nodes=max_nodes,
            limit=limit
        )
        return result.get("content", "Error") if result.get("success") else f"❌ {result.get('error')}"
    except Exception as e:
        return f"Error: {str(e)}"
