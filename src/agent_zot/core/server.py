"""
Zotero MCP server implementation.

Note: ChatGPT requires specific tool names "search" and "fetch", and so they
are defined and used and piped through to the main server tools. See bottom of file for details.
"""

from typing import Dict, List, Optional
import os
import sys
import uuid
import asyncio
import json
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastmcp import Context, FastMCP

from agent_zot.clients.zotero import (
    convert_to_markdown,
    format_item_metadata,
    generate_bibtex,
    get_attachment_details,
    get_zotero_client,
)
from agent_zot.utils.common import format_creators


def get_item_with_fallback(zot, item_key: str) -> Optional[Dict]:
    """
    Get item from Zotero API with fallback to local SQLite database.

    When ZOTERO_LOCAL=true, some items may exist in the local SQLite database
    but not be served by the local API server (e.g., unsynced items). This
    function tries the API first, then falls back to direct SQLite access.

    Args:
        zot: Zotero client instance
        item_key: Item key to fetch

    Returns:
        Item dict in pyzotero format, or None if not found
    """
    try:
        # Try API first
        return zot.item(item_key)
    except Exception as e:
        # Check if it's a 404 (ResourceNotFoundError)
        if "404" in str(e) or "Not found" in str(e):
            # Fall back to local SQLite database
            try:
                from agent_zot.database.local_zotero import LocalZoteroReader

                reader = LocalZoteroReader()
                zot_item = reader.get_item_by_key(item_key)

                if zot_item is None:
                    return None

                # Convert ZoteroItem to pyzotero dict format
                return {
                    "key": zot_item.key,
                    "data": {
                        "key": zot_item.key,
                        "itemType": zot_item.item_type or "unknown",
                        "title": zot_item.title or "",
                        "abstractNote": zot_item.abstract or "",
                        "creators": format_creators(zot_item.creators) if zot_item.creators else [],
                        "DOI": zot_item.doi or "",
                        "extra": zot_item.extra or "",
                        "dateAdded": zot_item.date_added or "",
                        "dateModified": zot_item.date_modified or "",
                    },
                    "meta": {},
                    "links": {},
                }
            except Exception as fallback_error:
                # If fallback also fails, re-raise original error
                raise e
        else:
            # Not a 404, re-raise
            raise

@asynccontextmanager
async def server_lifespan(server: FastMCP):
    """Manage server startup and shutdown lifecycle."""
    sys.stderr.write("Starting Zotero MCP server...\n")

    # DISABLED: Auto-update check removed for instant server startup
    # The initialization of semantic search (loading embeddings, connecting to databases)
    # adds 3-5 seconds to startup time, making agent-zot slower than other MCP servers.
    #
    # To update the search database manually, run:
    #   agent-zot update-db --force-rebuild --fulltext
    #
    # Original auto-update code commented out below:

    # try:
    #     from agent_zot.search.semantic import create_semantic_search
    #
    #     config_path = Path.home() / ".config" / "agent-zot" / "config.json"
    #
    #     if config_path.exists():
    #         search = create_semantic_search(str(config_path))
    #
    #         if search.should_update_database():
    #             sys.stderr.write("Auto-updating semantic search database with full-text extraction...\n")
    #
    #             # Run update in background to avoid blocking server startup
    #             async def background_update():
    #                 try:
    #                     stats = search.update_database(extract_fulltext=True)
    #                     sys.stderr.write(f"Database update completed: {stats.get('processed_items', 0)} items processed\n")
    #                 except Exception as e:
    #                     sys.stderr.write(f"Background database update failed: {e}\n")
    #
    #             # Start background task
    #             asyncio.create_task(background_update())
    #
    # except Exception as e:
    #     sys.stderr.write(f"Warning: Could not check semantic search auto-update: {e}\n")

    yield {}

    sys.stderr.write("Shutting down Zotero MCP server...\n")


# Create an MCP server with appropriate dependencies
mcp = FastMCP(
    "Zotero",
    dependencies=["pyzotero", "mcp[cli]", "python-dotenv", "markitdown", "fastmcp", "chromadb", "sentence-transformers", "openai", "google-genai"],
    lifespan=server_lifespan,
    instructions="""
# Agent-Zot Tool Coordination Guide

## Query-Driven Tool Selection

Agent-Zot provides 36 tools across 3 backends. Tool selection should be **query-driven**, not hierarchical. Choose tools based on what the query asks for:

### Content/Semantic Queries ("papers about [topic]", "research on [concept]", "what does [author] say about [topic]")
**Primary:** 🔵 Qdrant tools
- zot_semantic_search - discover papers by meaning/content (Figure 1)
- zot_enhanced_semantic_search - discover papers WITH chunk-level entities (Figure 3) 🆕
- zot_ask_paper - read and analyze paper content

**Often combined with:** Neo4j tools to explore relationships between found papers

**Search Pattern Levels:**
- **Level 1 (Figure 1):** `zot_semantic_search` - Basic semantic search with metadata
- **Level 2 (Figure 2):** `zot_hybrid_vector_graph_search` - Paper-level entity linking
- **Level 3 (Figure 3):** `zot_enhanced_semantic_search` - Chunk-level entity enrichment ⭐ MOST PRECISE

### Relationship/Network Queries ("who collaborated with [author]", "how are [topic A] and [topic B] connected", "citation network for [paper]")
**Primary:** 🟢 Neo4j knowledge graph tools
- zot_graph_search - relationship discovery
- zot_find_related_papers, zot_find_citation_chain, zot_explore_concept_network, etc.

**Often combined with:** zot_semantic_search to first find papers, then explore connections

### Complex Multi-Dimensional Queries
**Orchestrate multiple backends together:**
- Use zot_semantic_search (Qdrant) for content discovery
- Use zot_enhanced_semantic_search (Qdrant + Neo4j) for precision entity discovery 🆕
- Use Neo4j tools for relationship analysis
- Use zot_ask_paper (Qdrant) for content summarization
- Use Zotero API tools for metadata/collections/tags/export

### Specialized Tasks (collections, tags, notes, export)
**Use Zotero API tools** - these are the only options for:
- Collection management (create/add/remove)
- Tag management (get/update)
- Notes and annotations (get/create/search)
- Export (markdown/bibtex/graph)

## Anti-Patterns to Avoid

❌ **DON'T:** Use zot_search_items after zot_semantic_search (redundant - you already have item keys)
❌ **DON'T:** Use zot_get_item for paper content (use zot_ask_paper instead - much more efficient)
❌ **DON'T:** Call Neo4j tools when query is purely content-based (use Qdrant instead)
❌ **DON'T:** Use include_fulltext=True unless comprehensive summarization requires it (rare)
❌ **DON'T:** Use zot_enhanced_semantic_search when Neo4j is unpopulated (use zot_semantic_search instead)

## Efficient Patterns

✅ Semantic discovery → Ask paper for content
✅ Semantic discovery → Graph tools for relationships
✅ **Enhanced semantic search → Get chunk-level entities → Graph exploration** 🆕
✅ Semantic + Graph tools together for comprehensive analysis
✅ Multiple zot_ask_paper calls for comprehensive paper summarization
✅ zot_literature_review for end-to-end research synthesis (orchestrates all backends)

## Backend Capabilities

**Qdrant (Vector DB):** Semantic search over 2,411+ papers, full-text chunked, BGE-M3 embeddings
**Neo4j (Knowledge Graph):** Citation networks, author collaborations, concept relationships, **chunk-level entities** (0.5% populated currently)
**Zotero API:** Metadata, collections, tags, notes, annotations, export

## GraphRAG Architecture (Qdrant Documentation Alignment)

Agent-Zot fully implements the Qdrant GraphRAG patterns:
- **Figure 1:** Basic vector search → `zot_semantic_search`
- **Figure 2:** Paper-level hybrid → `zot_hybrid_vector_graph_search`
- **Figure 3:** Chunk-level enrichment → `zot_enhanced_semantic_search` ⭐ MOST ADVANCED

## Advanced Search Tools (Flexible Query-Driven Use)

**These tools can be used DIRECTLY for appropriate queries - no need to try basic search first.**

### Query Pattern Recognition

**Multi-concept query** (e.g., "X AND Y", "X, Y, Z") → `zot_decompose_query`
- Automatically breaks into sub-queries and merges results
- Use directly when you see boolean operators (AND, OR) or multiple distinct concepts
- Example: "fMRI studies of working memory AND aging"

**Multi-faceted comprehensive search** → `zot_unified_search`
- Merges Qdrant + Neo4j + Zotero API using Reciprocal Rank Fusion (RRF)
- Use directly when need maximum coverage across all backends
- Example: "neural mechanisms AND clinical applications" (benefits from multi-backend)

**Query needs improvement** → `zot_refine_search`
- Automatic iterative refinement based on result quality
- Use directly if you anticipate low-quality results
- Also triggered automatically when quality metrics show confidence=low or coverage<40%

### Multi-Tool Workflow Examples

**Example 1 - Complex query recognized upfront:**
```
Query: "fMRI studies of working memory AND aging"
→ zot_decompose_query (handles multi-concept directly)
→ zot_ask_paper (read content from found papers)
→ zot_find_related_papers (explore connections)
```

**Example 2 - Comprehensive then targeted:**
```
Query: "neural mechanisms of decision making"
→ zot_unified_search (maximize coverage across backends)
→ zot_ask_paper (extract specific findings)
→ zot_graph_search (explore relationships)
```

**Example 3 - Iterative refinement:**
```
Query: "attention networks"
→ zot_semantic_search (fast first attempt)
→ Quality metrics: confidence=low, coverage=25%
→ zot_refine_search (automatic improvement)
```

**Example 4 - Direct to advanced:**
```
Query: "methods used in machine learning AND neuroscience"
→ zot_decompose_query (obvious multi-concept from start)
  No need to try zot_semantic_search first
```

**Key Principle: QUERY-DRIVEN selection, not hierarchical ordering.**
Choose tools based on what the query needs, not a predetermined sequence.
"""
)



# ============================================================================
# QUERY TOOLS - Semantic/Vector Search (Qdrant)
# ============================================================================
@mcp.tool(
    name="zot_semantic_search",
    description="🔥 HIGH PRIORITY - 🔵 PRIMARY for simple content/topic discovery.\n\nFast semantic search over 2,400+ papers using BGE-M3 embeddings.\n\n💡 Use when:\n✓ Simple, well-formed query about specific concept/topic\n✓ You want fast results (single backend)\n✓ \"papers about [topic]\" or \"research on [method]\"\n✓ User requests \"quick\" or \"fast\" search\n✓ You expect good Qdrant coverage for this topic\n\nNOT for:\n✗ Complex multi-backend queries → use zot_unified_search (recommended default)\n✗ Poor initial results → use zot_refine_search  \n✗ Relationship queries → use zot_graph_search\n\n💡 Often combines with:\n- zot_ask_paper - Read content from found papers\n- zot_refine_search - If results need improvement\n- zot_unified_search - If coverage seems incomplete\n\n⚠️ Limitation: Only searches Qdrant vector DB. For comprehensive coverage, use zot_unified_search.\n\n📊 Search Levels:\n- Level 1 (THIS): Basic semantic search - fastest\n- Level 2 (zot_hybrid_vector_graph_search): Semantic + graph relationships\n- Level 3 (zot_enhanced_semantic_search): Semantic + chunk-level entities\n\nExample queries:\n✓ \"papers about [concept/topic]\"\n✓ \"research on [method/approach]\"\n✓ \"studies using [technique]\"\n\nUse for: Fast, simple semantic discovery when you expect good coverage",
    annotations={
        "readOnlyHint": True,
        "title": "Semantic Search (Vector)"
    }
)
def semantic_search(
    query: str,
    limit: int = 10,
    filters: Optional[str] = None,
    *,
    ctx: Context
) -> str:
    """
    Perform semantic search over your Zotero library.
    
    Args:
        query: Search query text - can be concepts, topics, or natural language descriptions
        limit: Maximum number of results to return (default: 10)
        filters: Optional metadata filters as dict or JSON string. Example: {"item_type": "note"}
        ctx: MCP context
    
    Returns:
        Markdown-formatted search results with similarity scores
    """
    try:
        if not query.strip():
            return "Error: Search query cannot be empty"
        
        # Parse and validate filters parameter
        if filters is not None:
            # Handle JSON string input
            if isinstance(filters, str):
                try:
                    filters = json.loads(filters)
                    ctx.info(f"Parsed JSON string filters: {filters}")
                except json.JSONDecodeError as e:
                    return f"Error: Invalid JSON in filters parameter: {str(e)}"
            
            # Validate it's a dictionary
            if not isinstance(filters, dict):
                return "Error: filters parameter must be a dictionary or JSON string. Example: {\"item_type\": \"note\"}"
            
            # Automatically translate common field names
            if "itemType" in filters:
                filters["item_type"] = filters.pop("itemType")
                ctx.info(f"Automatically translated 'itemType' to 'item_type': {filters}")
            
            # Additional field name translations can be added here
            # Example: if "creatorType" in filters:
            #     filters["creator_type"] = filters.pop("creatorType")
        
        ctx.info(f"Performing semantic search for: '{query}'")
        
        # Import semantic search module
        from agent_zot.search.semantic import create_semantic_search
        from pathlib import Path
        
        # Determine config path
        config_path = Path.home() / ".config" / "agent-zot" / "config.json"
        
        # Create semantic search instance
        search = create_semantic_search(str(config_path))
        
        # Perform search
        results = search.search(query=query, limit=limit, filters=filters)
        
        if results.get("error"):
            return f"Semantic search error: {results['error']}"
        
        search_results = results.get("results", [])
        
        if not search_results:
            return f"No semantically similar items found for query: '{query}'"
        
        # Format results as markdown
        output = [f"# Semantic Search Results for '{query}'", ""]
        output.append(f"Found {len(search_results)} similar items:")
        output.append("")
        
        for i, result in enumerate(search_results, 1):
            similarity_score = result.get("similarity_score", 0)
            _ = result.get("metadata", {})
            zotero_item = result.get("zotero_item", {})
            
            if zotero_item:
                data = zotero_item.get("data", {})
                title = data.get("title", "Untitled")
                item_type = data.get("itemType", "unknown")
                key = result.get("item_key", "")
                
                # Format creators
                creators = data.get("creators", [])
                creators_str = format_creators(creators)
                
                output.append(f"## {i}. {title}")
                output.append(f"**Similarity Score:** {similarity_score:.3f}")
                output.append(f"**Type:** {item_type}")
                output.append(f"**Item Key:** {key}")
                output.append(f"**Authors:** {creators_str}")
                
                # Add date if available
                if date := data.get("date"):
                    output.append(f"**Date:** {date}")
                
                # Add abstract snippet if present
                if abstract := data.get("abstractNote"):
                    abstract_snippet = abstract[:200] + "..." if len(abstract) > 200 else abstract
                    output.append(f"**Abstract:** {abstract_snippet}")
                
                # Add tags if present
                if tags := data.get("tags"):
                    tag_list = [f"`{tag['tag']}`" for tag in tags]
                    if tag_list:
                        output.append(f"**Tags:** {' '.join(tag_list)}")
                
                # Show matched text snippet
                matched_text = result.get("matched_text", "")
                if matched_text:
                    snippet = matched_text[:300] + "..." if len(matched_text) > 300 else matched_text
                    output.append(f"**Matched Content:** {snippet}")
                
                output.append("")  # Empty line between items
            else:
                # Fallback if full Zotero item not available
                output.append(f"## {i}. Item {result.get('item_key', 'Unknown')}")
                output.append(f"**Similarity Score:** {similarity_score:.3f}")
                if error := result.get("error"):
                    output.append(f"**Error:** {error}")
                output.append("")

        # Add quality metrics if available
        if quality_metrics := results.get("quality_metrics"):
            output.append("---")
            output.append("")
            output.append("## Search Quality Metrics")
            output.append("")
            output.append(f"- **Mean Similarity**: {quality_metrics['mean_similarity']:.3f}")
            output.append(f"- **Range**: {quality_metrics['min_similarity']:.3f} - {quality_metrics['max_similarity']:.3f}")
            output.append(f"- **Standard Deviation**: {quality_metrics['std_similarity']:.3f}")
            output.append(f"- **High Quality Results** (≥0.75): {quality_metrics['high_quality_count']}/{len(search_results)} ({quality_metrics['coverage']*100:.1f}%)")
            output.append(f"- **Search Confidence**: {quality_metrics['confidence'].title()}")
            output.append("")

            # Provide adaptive search recommendations
            if quality_metrics['confidence'] == 'low':
                output.append("💡 **Recommendation**: Consider refining your query or using `zot_refine_search` for better results.")
            elif quality_metrics['coverage'] < 0.5:
                output.append("💡 **Recommendation**: Many results have low relevance. Try a more specific query.")

        return "\n".join(output)
    
    except Exception as e:
        ctx.error(f"Error in semantic search: {str(e)}")
        return f"Error in semantic search: {str(e)}"


@mcp.tool(
    name="zot_unified_search",
    description="🔥 HIGH PRIORITY - 🔵 RECOMMENDED DEFAULT - Unified search using Reciprocal Rank Fusion.\n\n**Use this as your primary research discovery tool.**\n\nCombines three backends for maximum coverage:\n- Qdrant (semantic vector search) - content similarity\n- Neo4j (knowledge graph) - relationship discovery  \n- Zotero API (metadata search) - keyword matching\n\nResults merged using Reciprocal Rank Fusion (RRF):\n- Papers appearing in multiple backends rank higher\n- Balances relevance across different retrieval methods\n- Often outperforms single-backend search\n\n💡 Best for:\n✓ Comprehensive research queries (recommended default)\n✓ Multi-faceted topics requiring diverse retrieval methods\n✓ Maximizing recall (finding ALL relevant papers)\n✓ When semantic search alone has poor coverage\n✓ Complex queries like 'neural mechanisms AND clinical applications'\n\nNOT for:\n✗ Simple queries where speed > completeness → use zot_semantic_search (faster)\n✗ Purely relationship-based queries → use zot_graph_search\n\n💡 Often combines with:\n- zot_ask_paper - Read content from found papers\n- zot_find_related_papers - Explore citation connections\n- Neo4j graph tools - Analyze relationships between results\n\n💡 Example: 'dissociation cognitive control' finds papers across content, citations, and metadata that might be missed by semantic search alone.\n\n⚠️ Note: This is now the recommended starting point for most research queries. Use zot_semantic_search only when speed is critical and you expect good Qdrant coverage.\n\nUse for: Comprehensive multi-backend search with intelligent result merging",
    annotations={
        "readOnlyHint": True,
        "title": "Unified Search (RRF)"
    }
)
def unified_search_tool(
    query: str,
    limit: int = 10,
    *,
    ctx: Context
) -> str:
    """
    Perform unified search across all backends using Reciprocal Rank Fusion.

    Args:
        query: Search query text
        limit: Maximum number of results to return (default: 10)
        ctx: MCP context

    Returns:
        Markdown-formatted unified search results with RRF scores
    """
    try:
        if not query.strip():
            return "Error: Search query cannot be empty"

        ctx.info(f"Performing unified search for: '{query}'")

        # Import required modules
        from agent_zot.search.semantic import create_semantic_search
        from agent_zot.search.unified import unified_search
        from pathlib import Path

        # Determine config path
        config_path = Path.home() / ".config" / "agent-zot" / "config.json"

        # Create semantic search instance (provides access to all backends)
        search = create_semantic_search(str(config_path))

        # Perform unified search
        results = unified_search(search, query, limit)

        if results.get("error"):
            error_msg = f"Unified search error: {results['error']}"
            if backend_errors := results.get("errors_by_backend"):
                error_msg += f"\n\nBackend errors:\n"
                for backend, error in backend_errors.items():
                    error_msg += f"- {backend}: {error}\n"
            return error_msg

        search_results = results.get("results", [])

        if not search_results:
            return f"No results found for query: '{query}'"

        # Format results as markdown
        output = [f"# Unified Search Results for '{query}'", ""]

        # Show backend contributions
        if contributions := results.get("backend_contributions"):
            output.append("## Search Backends Used")
            output.append("")
            for backend, count in contributions.items():
                output.append(f"- **{backend.title()}**: {count} papers contributed")
            output.append("")

        output.append(f"Found {len(search_results)} papers (merged using Reciprocal Rank Fusion):")
        output.append("")

        for i, result in enumerate(search_results, 1):
            rrf_score = result.get("rrf_score", 0)
            zotero_item = result.get("zotero_item", {})

            if zotero_item:
                data = zotero_item.get("data", {})
                title = data.get("title", "Untitled")
                item_type = data.get("itemType", "unknown")
                key = result.get("item_key", "")

                # Format creators
                creators = data.get("creators", [])
                creators_str = format_creators(creators)

                output.append(f"## {i}. {title}")
                output.append(f"**RRF Score:** {rrf_score:.4f}")
                output.append(f"**Type:** {item_type}")
                output.append(f"**Item Key:** {key}")
                output.append(f"**Authors:** {creators_str}")

                # Add date if available
                if date := data.get("date"):
                    output.append(f"**Date:** {date}")

                # Add abstract snippet if present
                if abstract := data.get("abstractNote"):
                    abstract_snippet = abstract[:200] + "..." if len(abstract) > 200 else abstract
                    output.append(f"**Abstract:** {abstract_snippet}")

                # Add tags if present
                if tags := data.get("tags"):
                    tag_list = [f"`{tag['tag']}`" for tag in tags]
                    if tag_list:
                        output.append(f"**Tags:** {' '.join(tag_list)}")

                output.append("")  # Empty line between items
            else:
                # Fallback if full item not available
                output.append(f"## {i}. Item {result.get('item_key', 'Unknown')}")
                output.append(f"**RRF Score:** {rrf_score:.4f}")
                if error := result.get("error"):
                    output.append(f"**Error:** {error}")
                output.append("")

        # Add explanation of RRF score
        output.append("---")
        output.append("")
        output.append("## About RRF Scores")
        output.append("")
        output.append("Reciprocal Rank Fusion (RRF) scores indicate how relevant a paper is across multiple search backends.")
        output.append("Higher scores mean the paper appeared in multiple backends and/or ranked highly in those backends.")
        output.append("")

        return "\n".join(output)

    except Exception as e:
        ctx.error(f"Error in unified search: {str(e)}")
        return f"Error in unified search: {str(e)}"


@mcp.tool(
    name="zot_refine_search",
    description="🔥 HIGH PRIORITY - 🔵 ADVANCED - Iterative retrieval with automatic query refinement and intelligent fallback.\n\n💡 Use when:\n✓ Initial search returned poor-quality results (low confidence/coverage)\n✓ Query is vague or exploratory and needs automatic improvement\n✓ You want the system to learn from initial results and improve the query\n✓ Quality metrics indicate need for refinement\n\nHow it works:\n1. Performs initial semantic search (Qdrant vector DB)\n2. Analyzes quality metrics (confidence, coverage, similarity)\n3. If quality is low:\n   - Extracts key concepts from top results\n   - Adds domain-specific terms (e.g., 'dissociation' → 'depersonalization, derealization')\n   - Detects methodology/domain from paper content (e.g., adds 'fMRI' if papers mention neuroimaging)\n   - Generates refined query variants\n4. Re-searches with improved queries\n5. Merges and ranks all results\n6. **🆕 Smart Fallback**: If semantic search finds 0 results after refinement, automatically escalates to unified search (Qdrant + Neo4j + Zotero API)\n\nRefinement strategies:\n- Domain-specific expansion (cognitive neuroscience/psychology terms)\n- Methodology extraction (fMRI, EEG, behavioral, clinical)\n- Concept extraction from relevant papers\n- Synonym expansion for cognitive/clinical terms\n\nOften more effective than manual query reformulation because it learns from actual paper content.\n\nNOT for:\n✗ High-quality initial results (confidence=high, coverage>60%) → unnecessary\n✗ When you want exact control over query formulation → use zot_semantic_search\n\n💡 Often combines with:\n- zot_semantic_search - Start here first, then refine if quality is low\n- zot_ask_paper - Read content from refined results\n- zot_unified_search - Or use this directly for maximum coverage from the start\n\n⚠️ Note: Primarily uses semantic search. For maximum coverage across all backends from the start, use zot_unified_search instead.\n\nUse for: Automatic query improvement when initial search quality is insufficient, with intelligent fallback to multi-backend search",
    annotations={
        "readOnlyHint": True,
        "title": "Iterative Search (Auto-Refine)"
    }
)
def refine_search_tool(
    query: str,
    limit: int = 10,
    max_iterations: int = 2,
    *,
    ctx: Context
) -> str:
    """
    Perform iterative search with automatic query refinement.

    Args:
        query: Initial search query
        limit: Number of final results to return (default: 10)
        max_iterations: Maximum refinement iterations (default: 2)
        ctx: MCP context

    Returns:
        Formatted search results with refinement metadata
    """
    try:
        ctx.info(f"Starting iterative search for: '{query}'")

        # Import modules
        from agent_zot.search.semantic import create_semantic_search
        from agent_zot.search.iterative import iterative_search
        from pathlib import Path

        # Determine config path (must match unified_search tool)
        config_path = Path.home() / ".config" / "agent-zot" / "config.json"

        # Create semantic search instance
        search = create_semantic_search(str(config_path))

        # Perform iterative search
        results = iterative_search(
            semantic_search_instance=search,
            query=query,
            limit=limit,
            max_iterations=max_iterations
        )

        # Format output
        output = []
        output.append(f"# Iterative Search Results: '{query}'")
        output.append("")

        # Show iteration metadata
        iterations = results.get("iterations", 1)
        refinements = results.get("refinements", [])

        output.append("## Search Process")
        output.append("")
        output.append(f"- **Iterations**: {iterations}")
        output.append(f"- **Refinements Attempted**: {len(refinements)}")
        output.append(f"- **Final Results**: {results.get('total_found', 0)}")
        output.append(f"- **Total Unique Papers Found**: {results.get('final_result_count', 0)}")
        output.append("")

        # Show initial quality
        if initial_quality := results.get("initial_quality"):
            output.append("### Initial Search Quality")
            output.append("")
            output.append(f"- **Confidence**: {initial_quality.get('confidence', 'unknown').title()}")
            output.append(f"- **Coverage**: {initial_quality.get('coverage', 0)*100:.1f}%")
            output.append(f"- **Mean Similarity**: {initial_quality.get('mean_similarity', 0):.3f}")
            output.append("")

        # Show refinements if any
        if refinements:
            output.append("### Query Refinements")
            output.append("")
            for ref in refinements:
                iter_num = ref.get("iteration", 0)
                ref_query = ref.get("query", "")
                results_found = ref.get("results_found", 0)

                output.append(f"**Iteration {iter_num}**: `{ref_query}`")

                if error := ref.get("error"):
                    output.append(f"  - ❌ Error: {error}")
                else:
                    output.append(f"  - Found {results_found} results")

                    if ref_quality := ref.get("quality_metrics"):
                        ref_confidence = ref_quality.get("confidence", "unknown")
                        ref_coverage = ref_quality.get("coverage", 0)
                        output.append(f"  - Quality: {ref_confidence.title()} confidence, {ref_coverage*100:.1f}% coverage")

                output.append("")

        # Show results
        output.append("---")
        output.append("")
        output.append("## Papers Found")
        output.append("")

        search_results = results.get("results", [])

        if not search_results:
            output.append("No results found.")
        else:
            for idx, result in enumerate(search_results, 1):
                item_key = result.get("item_key", "unknown")
                similarity = result.get("similarity_score", 0.0)
                zotero_item = result.get("zotero_item", {})
                data = zotero_item.get("data", {})

                title = data.get("title", "Untitled")
                creators = format_creators(data.get("creators", []))
                year = data.get("date", "")[:4] if data.get("date") else "n.d."

                output.append(f"### {idx}. {title}")
                output.append("")
                output.append(f"- **Authors**: {creators}")
                output.append(f"- **Year**: {year}")
                output.append(f"- **Item Key**: `{item_key}`")
                output.append(f"- **Similarity**: {similarity:.3f}")

                if abstract := data.get("abstractNote"):
                    abstract_preview = abstract[:200] + "..." if len(abstract) > 200 else abstract
                    output.append(f"- **Abstract**: {abstract_preview}")

                output.append("")

        # Add recommendation
        output.append("---")
        output.append("")

        # Check if fallback was used
        if fallback_message := results.get("message"):
            output.append(fallback_message)
            output.append("")
            if fallback_backends := results.get("fallback_backends"):
                output.append(f"**Backends used in fallback**: {', '.join(fallback_backends)}")
                output.append("")

        if iterations > 1:
            output.append("✅ **Query refinement was applied** to improve result quality.")
        elif results.get("final_result_count", 0) == 0:
            output.append("⚠️ **No results found** - Consider using broader query terms or alternative search backends.")
        else:
            output.append("ℹ️ **No refinement needed** - initial results were sufficient.")

        if results.get("total_found", 0) < limit and not results.get("fallback_used"):
            output.append("")
            output.append("💡 **Tip**: If more results are needed, try:")
            output.append("  - Using broader query terms")
            output.append("  - Using `zot_unified_search` to search across multiple backends")
            output.append("  - Using `zot_decompose_query` to break down the query into components")

        ctx.info(f"Iterative search completed: {results.get('total_found', 0)} results from {iterations} iterations")

        return "\n".join(output)

    except Exception as e:
        ctx.error(f"Error in iterative search: {str(e)}")
        return f"Error in iterative search: {str(e)}"


@mcp.tool(
    name="zot_decompose_query",
    description="🔥 HIGH PRIORITY - 🔵 ADVANCED - Query decomposition for complex multi-concept queries.\n\n💡 Use when:\n✓ Query contains multiple distinct concepts (e.g., 'neural networks AND decision making')\n✓ Query uses boolean operators (AND, OR)\n✓ Query has natural conjunctions (and, with, or, versus)\n✓ Query combines different domains/methods (e.g., 'fMRI studies of memory in aging')\n✓ You want comprehensive coverage of multi-faceted topics\n\nHow it works:\n1. Analyzes query structure to identify multiple concepts\n2. Decomposes into simpler sub-queries based on patterns:\n   - Boolean operators (AND, OR)\n   - Natural conjunctions (and, with, plus, or, versus)\n   - Prepositions (in, about, regarding, concerning)\n   - Comma-separated concepts\n   - Multiple noun phrases\n3. Executes sub-queries in parallel\n4. Merges results using weighted scoring:\n   - Required concepts (AND) have higher importance (1.0)\n   - Optional concepts (OR) have lower importance (0.7)\n   - Supporting concepts have moderate importance (0.4-0.6)\n   - Papers appearing in multiple sub-queries rank higher\n\nDecomposition patterns:\n- 'X AND Y' → searches for X, Y separately (both required)\n- 'X OR Y' → searches for X, Y separately (either acceptable)\n- 'X in Y' → searches for 'X in Y', X, Y separately\n- 'X, Y, Z' → searches for full query + individual concepts\n\nOften finds more comprehensive results than single complex query because it:\n- Reduces query complexity for better matching\n- Increases recall by searching variants\n- Balances precision (full query) with coverage (sub-queries)\n\nNOT for:\n✗ Simple single-concept queries → use zot_semantic_search (faster)\n✗ Queries that shouldn't be split (e.g., proper names like 'New York') → use zot_semantic_search\n\n💡 Often combines with:\n- zot_unified_search - Combine for maximum multi-backend coverage\n- zot_ask_paper - Read content from papers found via sub-queries\n- zot_find_related_papers - Explore connections between results\n\nUse for: Complex multi-concept queries requiring comprehensive coverage across concepts",
    annotations={
        "readOnlyHint": True,
        "title": "Query Decomposition (Multi-Concept)"
    }
)
def decompose_query_tool(query: str, limit: int = 10, *, ctx: Context) -> str:
    """
    Decompose complex query into sub-queries and merge results.

    Args:
        query: Complex multi-concept search query
        limit: Number of final results to return (default: 10)
        ctx: MCP context

    Returns:
        Formatted search results with decomposition metadata
    """
    try:
        ctx.info(f"Starting decomposed search for: '{query}'")

        # Import modules
        from agent_zot.search.semantic import create_semantic_search
        from agent_zot.search.decomposition import decomposed_search
        from pathlib import Path

        # Determine config path (must match unified_search tool)
        config_path = Path.home() / ".config" / "agent-zot" / "config.json"

        # Create semantic search instance
        search = create_semantic_search(str(config_path))

        # Perform decomposed search
        results = decomposed_search(
            semantic_search_instance=search,
            query=query,
            limit=limit
        )

        # Format output
        output = []
        output.append(f"# Decomposed Search Results: '{query}'")
        output.append("")

        # Show decomposition metadata
        decomposition = results.get("decomposition", {})
        was_decomposed = decomposition.get("decomposed", False)

        output.append("## Query Decomposition")
        output.append("")

        if not was_decomposed:
            output.append(f"ℹ️ **No decomposition applied**: {decomposition.get('reason', 'Query is already simple')}")
            output.append("")
        else:
            sub_queries = decomposition.get("sub_queries", [])
            output.append(f"- **Sub-queries Generated**: {len(sub_queries)}")
            output.append(f"- **Total Results from Sub-queries**: {decomposition.get('total_sub_results', 0)}")
            output.append(f"- **Unique Papers Found**: {decomposition.get('unique_papers_found', 0)}")
            output.append(f"- **Final Results**: {results.get('total_found', 0)}")
            output.append("")

            # Show sub-queries
            output.append("### Sub-queries")
            output.append("")

            for idx, sq in enumerate(sub_queries, 1):
                sq_text = sq.get("query", "")
                sq_type = sq.get("type", "unknown")
                sq_importance = sq.get("importance", 0.0)

                # Format type
                type_emoji = {
                    "primary": "🎯",
                    "required": "✅",
                    "optional": "🔷",
                    "supporting": "📎"
                }.get(sq_type, "•")

                output.append(f"{idx}. {type_emoji} **{sq_type.title()}**: `{sq_text}`")
                output.append(f"   - Importance weight: {sq_importance}")
                output.append("")

            # Show errors if any
            if errors := decomposition.get("errors"):
                output.append("### Errors")
                output.append("")
                for subquery, error in errors.items():
                    output.append(f"- `{subquery}`: {error}")
                output.append("")

        # Show results
        output.append("---")
        output.append("")
        output.append("## Papers Found")
        output.append("")

        search_results = results.get("results", [])

        if not search_results:
            output.append("No results found.")
        else:
            for idx, result in enumerate(search_results, 1):
                item_key = result.get("item_key", "unknown")
                similarity = result.get("similarity_score", 0.0)
                combined_score = result.get("combined_score")
                zotero_item = result.get("zotero_item", {})
                data = zotero_item.get("data", {})

                title = data.get("title", "Untitled")
                creators = format_creators(data.get("creators", []))
                year = data.get("date", "")[:4] if data.get("date") else "n.d."

                output.append(f"### {idx}. {title}")
                output.append("")
                output.append(f"- **Authors**: {creators}")
                output.append(f"- **Year**: {year}")
                output.append(f"- **Item Key**: `{item_key}`")

                if combined_score is not None:
                    output.append(f"- **Combined Score**: {combined_score:.3f} (from multiple sub-queries)")
                else:
                    output.append(f"- **Similarity**: {similarity:.3f}")

                if abstract := data.get("abstractNote"):
                    abstract_preview = abstract[:200] + "..." if len(abstract) > 200 else abstract
                    output.append(f"- **Abstract**: {abstract_preview}")

                output.append("")

        # Add explanation
        output.append("---")
        output.append("")

        if was_decomposed:
            output.append("✅ **Query decomposition applied** to increase coverage across multiple concepts.")
            output.append("")
            output.append("Papers appearing in multiple sub-queries receive higher combined scores, indicating relevance to multiple aspects of your query.")
        else:
            output.append("ℹ️ **Simple query** - no decomposition needed.")

        if results.get("total_found", 0) < limit:
            output.append("")
            output.append("💡 **Tip**: To find more results, try:")
            output.append("  - Using broader query terms")
            output.append("  - Using `zot_unified_search` for multi-backend search")
            output.append("  - Using `zot_refine_search` for automatic query refinement")

        ctx.info(f"Decomposed search completed: {results.get('total_found', 0)} results")

        return "\n".join(output)

    except Exception as e:
        ctx.error(f"Error in decomposed search: {str(e)}")
        return f"Error in decomposed search: {str(e)}"


@mcp.tool(
    name="zot_update_search_database",
    description="🔧 LOW PRIORITY - ⚪ FALLBACK - Index or re-index the Zotero library for semantic search. Extracts full PDF text using AI-powered parsing (Docling with OCR). Use this when the user asks to 'index my library', 'update the search database', or 'enable semantic search'. Automatically handles full-text extraction from PDFs.\n\nUse for: Rebuilding semantic search database after adding new papers",
    annotations={
        "readOnlyHint": False,
        "title": "Update Search Index (Vector)"
    }
)
def update_search_database(
    force_rebuild: bool = False,
    extract_fulltext: bool = True,
    limit: Optional[int] = None,
    *,
    ctx: Context
) -> str:
    """
    Index or re-index the Zotero library for AI-powered semantic search.

    This tool extracts content from your Zotero library and creates searchable embeddings.
    By default, it extracts full PDF text for comprehensive semantic search.

    Args:
        force_rebuild: Set to True to rebuild entire database from scratch. False = incremental update (default: False)
        extract_fulltext: Set to True for full PDF text extraction, False for metadata-only (default: True)
        limit: Optional limit for testing (e.g., 10 for quick test). None = process all items (default: None)
        ctx: MCP context

    Returns:
        Detailed statistics about the indexing process
    """
    try:
        # Handle string-to-int conversion for limit parameter (Claude sometimes sends strings)
        if limit is not None and isinstance(limit, str):
            try:
                limit = int(limit)
            except ValueError:
                return f"Error: limit must be a number, got '{limit}'"

        mode = "full-text PDF extraction" if extract_fulltext else "metadata-only"
        ctx.info(f"Starting semantic search database update ({mode})...")

        # Import semantic search module
        from agent_zot.search.semantic import create_semantic_search
        from pathlib import Path

        # Determine config path
        config_path = Path.home() / ".config" / "agent-zot" / "config.json"

        # Create semantic search instance
        search = create_semantic_search(str(config_path))

        # Perform update
        stats = search.update_database(
            force_full_rebuild=force_rebuild,
            limit=limit,
            extract_fulltext=extract_fulltext
        )
        
        # Format results
        output = ["# Database Update Results", ""]
        
        if stats.get("error"):
            output.append(f"**Error:** {stats['error']}")
        else:
            output.append(f"**Total items:** {stats.get('total_items', 0)}")
            output.append(f"**Processed:** {stats.get('processed_items', 0)}")
            output.append(f"**Added:** {stats.get('added_items', 0)}")
            output.append(f"**Updated:** {stats.get('updated_items', 0)}")
            output.append(f"**Skipped:** {stats.get('skipped_items', 0)}")
            output.append(f"**Errors:** {stats.get('errors', 0)}")
            output.append(f"**Duration:** {stats.get('duration', 'Unknown')}")
            
            if stats.get('start_time'):
                output.append(f"**Started:** {stats['start_time']}")
            if stats.get('end_time'):
                output.append(f"**Completed:** {stats['end_time']}")
        
        return "\n".join(output)
    
    except Exception as e:
        ctx.error(f"Error updating search database: {str(e)}")
        return f"Error updating search database: {str(e)}"


@mcp.tool(
    name="zot_get_search_database_status",
    description="🔧 LOW PRIORITY - ⚪ FALLBACK - Get status information about the semantic search database.\n\nUse for: Verifying semantic search database health and statistics"
,
    annotations={
        "readOnlyHint": True,
        "title": "Get Search Database Status (Vector)"
    }
)
def get_search_database_status(*, ctx: Context) -> str:
    """
    Get semantic search database status.
    
    Args:
        ctx: MCP context
    
    Returns:
        Database status information
    """
    try:
        ctx.info("Getting semantic search database status...")
        
        # Import semantic search module
        from agent_zot.search.semantic import create_semantic_search
        from pathlib import Path
        
        # Determine config path
        config_path = Path.home() / ".config" / "agent-zot" / "config.json"
        
        # Create semantic search instance
        search = create_semantic_search(str(config_path))
        
        # Get status
        status = search.get_database_status()
        
        # Format results
        output = ["# Semantic Search Database Status", ""]
        
        collection_info = status.get("collection_info", {})
        output.append("## Collection Information")
        output.append(f"**Name:** {collection_info.get('name', 'Unknown')}")
        output.append(f"**Document Count:** {collection_info.get('count', 0)}")
        output.append(f"**Embedding Model:** {collection_info.get('embedding_model', 'Unknown')}")
        output.append(f"**Database Path:** {collection_info.get('persist_directory', 'Unknown')}")
        
        if collection_info.get('error'):
            output.append(f"**Error:** {collection_info['error']}")
        
        output.append("")
        
        update_config = status.get("update_config", {})
        output.append("## Update Configuration")
        output.append(f"**Auto Update:** {update_config.get('auto_update', False)}")
        output.append(f"**Frequency:** {update_config.get('update_frequency', 'manual')}")
        output.append(f"**Last Update:** {update_config.get('last_update', 'Never')}")
        output.append(f"**Should Update Now:** {status.get('should_update', False)}")
        
        if update_config.get('update_days'):
            output.append(f"**Update Interval:** Every {update_config['update_days']} days")
        
        return "\n".join(output)
    
    except Exception as e:
        ctx.error(f"Error getting database status: {str(e)}")
        return f"Error getting database status: {str(e)}"


# --- Minimal wrappers for ChatGPT connectors ---
# These are required for ChatGPT custom MCP servers via web "connectors"
# specific tools required are "search" and "fetch"
# See: https://platform.openai.com/docs/mcp

def _extract_item_key_from_input(value: str) -> Optional[str]:
    """Extract a Zotero item key from a Zotero URL, web URL, or bare key.
    Returns None if no plausible key is found.
    """
    if not value:
        return None
    text = value.strip()

    # Common patterns:
    # - zotero://select/items/<KEY>
    # - zotero://select/library/items/<KEY>
    # - https://www.zotero.org/.../items/<KEY>
    # - bare <KEY>
    patterns = [
        r"zotero://select/(?:library/)?items/([A-Za-z0-9]{8})",
        r"/items/([A-Za-z0-9]{8})(?:[^A-Za-z0-9]|$)",
        r"\b([A-Za-z0-9]{8})\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


@mcp.tool(
    name="zot_hybrid_vector_graph_search",
    description="🔥 HIGH PRIORITY - 🔵 PRIMARY - Combines semantic search with relationship discovery. Use when you want both content relevance AND network connections in results. Requires Neo4j.\n\n💡 Preferred over zot_unified_search for most queries combining content and relationships.\n⚠️ For content-only queries, use zot_semantic_search instead (faster).\n\nUse for: Combined semantic+relationship queries when both content and connections matter"
,
    annotations={
        "readOnlyHint": True,
        "title": "Hybrid Vector+Graph Search (Vector/Graph)"
    }
)
def hybrid_vector_graph_search(
    query: str,
    limit: int = 10,
    vector_weight: float = 0.7,
    *,
    ctx: Context
) -> str:
    """
    Perform hybrid search combining Qdrant vector search with Neo4j graph relationships.

    Args:
        query: Search query
        limit: Maximum number of results (default: 10)
        vector_weight: Weight for vector results 0-1, graph weight is (1 - vector_weight) (default: 0.7)
        ctx: MCP context

    Returns:
        Markdown-formatted hybrid search results with combined scoring
    """
    try:
        from agent_zot.search.semantic import create_semantic_search
        from pathlib import Path

        config_path = Path.home() / ".config" / "agent-zot" / "config.json"
        search = create_semantic_search(str(config_path))

        # Perform hybrid search
        results = search.hybrid_vector_graph_search(
            query=query,
            limit=limit,
            vector_weight=vector_weight
        )

        if results.get("error"):
            return f"Hybrid search error: {results['error']}"

        search_type = results.get("search_type", "unknown")
        papers = results.get("results", [])
        graph_enabled = results.get("graph_enabled", False)

        if not papers:
            return f"No results found for query: '{query}'"

        # Format results
        output = [f"# Hybrid Search Results for '{query}'", ""]
        output.append(f"**Search Type:** {search_type}")
        output.append(f"**Graph Enhancement:** {'Enabled' if graph_enabled else 'Disabled'}")
        output.append(f"Found {len(papers)} papers:")
        output.append("")

        for i, paper in enumerate(papers, 1):
            zotero_item = paper.get("zotero_item", {})
            item_data = zotero_item.get("data", {})

            title = item_data.get("title", "Untitled")
            item_key = paper.get("item_key", "N/A")
            vector_score = paper.get("similarity_score", 0)
            combined_score = paper.get("combined_score", vector_score)
            related_count = paper.get("related_papers_count", 0)
            sample_related = paper.get("sample_related", [])

            output.append(f"## {i}. {title}")
            output.append(f"**Item Key:** {item_key}")
            output.append(f"**Combined Score:** {combined_score:.3f}")
            output.append(f"**Vector Score:** {vector_score:.3f}")

            if graph_enabled:
                output.append(f"**Related Papers (Graph):** {related_count}")
                if sample_related:
                    output.append(f"**Sample Connections:** {', '.join(sample_related)}")

            # Add authors and year
            creators = item_data.get("creators", [])
            if creators:
                authors = [f"{c.get('lastName', '')}" for c in creators[:3]]
                output.append(f"**Authors:** {', '.join(authors)}")

            year = item_data.get("date", "")[:4] if item_data.get("date") else "N/A"
            output.append(f"**Year:** {year}")

            output.append("")

        return "\n".join(output)

    except Exception as e:
        ctx.error(f"Error in hybrid search: {str(e)}")
        return f"Error in hybrid search: {str(e)}"


def deduplicate_chunks(chunks: List[Dict]) -> List[Dict]:
    """
    Remove duplicate chunks based on normalized text content.

    Duplicate chunks can occur when:
    - Same text appears in overlapping chunks
    - Text is extracted multiple times with slight formatting differences
    - Vector search returns near-identical content from different positions

    Args:
        chunks: List of chunk dictionaries with 'matched_text' field

    Returns:
        Deduplicated list of chunks, preserving order by relevance
    """
    seen_hashes = set()
    unique_chunks = []
    duplicates_removed = 0

    for chunk in chunks:
        # Normalize text for comparison: strip whitespace, lowercase
        text = chunk.get('matched_text', '').strip().lower()

        # Skip empty chunks
        if not text:
            continue

        # Use hash for efficient duplicate detection
        # Note: Hash collisions are rare and acceptable for this use case
        chunk_hash = hash(text)

        if chunk_hash not in seen_hashes:
            seen_hashes.add(chunk_hash)
            unique_chunks.append(chunk)
        else:
            duplicates_removed += 1

    if duplicates_removed > 0:
        logger.info(f"Removed {duplicates_removed} duplicate chunks from results")

    return unique_chunks


@mcp.tool(
    name="zot_ask_paper",
    description="🔥 HIGH PRIORITY - 🔵 PRIMARY tool for accessing paper content. Uses semantic search to retrieve relevant text chunks from a paper's full text. Much more efficient than zot_get_item(include_fulltext=True). This does NOT generate AI answers - it returns source text chunks for you to analyze.\n\n✅ Use this when you need to read, analyze, or extract information from a paper's actual content.\n💡 For comprehensive paper summarization, call this multiple times with different questions (e.g., methods, results, conclusions) or use high top_k value.\n\nExample questions:\n✓ \"What methodology did the authors use?\"\n✓ \"What were the main findings?\"\n✓ \"How did they measure [variable]?\"\n\nNOT for:\n✗ \"find papers about [topic]\" → use zot_semantic_search\n✗ \"who are the authors\" → use zot_get_item\n\nUse for: Reading paper content, extracting findings, analyzing methodology, understanding results, comprehensive summarization",
    annotations={
        "readOnlyHint": True,
        "title": "Ask Paper (Vector)"
    }
)
def ask_paper(
    item_key: str,
    question: str,
    top_k: int = 5,
    *,
    ctx: Context
) -> str:
    """
    Ask questions about a specific paper's content using semantic search over its chunks.

    This tool returns relevant text chunks from the paper - it does NOT generate AI-written answers.
    Use the returned context chunks to formulate your own answer or pass to an LLM.

    Args:
        item_key: Zotero item key of the paper to query
        question: Your question about the paper's content
        top_k: Number of relevant chunks to return (default: 5)
        ctx: MCP context

    Returns:
        Markdown-formatted relevant text chunks from the paper
    """
    try:
        from agent_zot.search.semantic import create_semantic_search
        from pathlib import Path

        ctx.info(f"Searching paper {item_key} for: {question}")

        config_path = Path.home() / ".config" / "agent-zot" / "config.json"
        search = create_semantic_search(str(config_path))

        # Search with parent_item_key filter to only get chunks from this specific paper
        results = search.search(
            query=question,
            limit=top_k,
            filters={"parent_item_key": item_key}
        )

        if results.get("error"):
            return f"Error searching paper: {results['error']}"

        # Get paper metadata for context
        zot = get_zotero_client()
        try:
            item = get_item_with_fallback(zot, item_key)
            paper_data = item.get("data", {}) if item else {}
            paper_title = paper_data.get("title", "Unknown")
        except Exception:
            paper_title = item_key

        # Check if we got results (search.search returns enriched results in "results" field)
        search_results = results.get("results", [])

        # Apply deduplication to remove duplicate chunks (Fix #3)
        # This prevents showing the same or nearly-identical content multiple times
        search_results = deduplicate_chunks(search_results)

        if not search_results:
            return f"No relevant content found in paper '{paper_title}' for question: '{question}'\n\nThis may mean:\n- The paper's full text hasn't been indexed yet (run zot_update_search_database)\n- The question topic isn't discussed in this paper\n- Try rephrasing your question"

        # Format results
        output = [f"# Relevant Content from '{paper_title}'"]
        output.append(f"\n**Question:** {question}")
        output.append(f"**Item Key:** {item_key}")
        output.append(f"\n**Found {len(search_results)} relevant chunks:**\n")

        for i, result in enumerate(search_results):
            # Extract from enriched result format
            chunk_text = result.get("matched_text", "")
            similarity = result.get("similarity_score", 0.0)

            output.append(f"## Chunk {i+1} (Relevance: {similarity:.3f})")
            output.append(f"{chunk_text}")
            output.append("")

        output.append("\n---")
        output.append("*Note: These are extracted text chunks from the paper. Use them as context to formulate your answer.*")

        return "\n".join(output)

    except Exception as e:
        ctx.error(f"Error in ask_paper: {str(e)}")
        return f"Error querying paper: {str(e)}"


@mcp.tool(
    name="zot_find_similar_papers",
    description="""🔥 HIGH PRIORITY - 🔵 PRIMARY - Find papers similar to a given paper using content-based vector similarity (More Like This query).

Uses the paper's actual document embedding to find semantically similar papers. More accurate than semantic_search(abstract) because it uses the full document vector.

💡 Different from zot_find_related_papers:
- THIS TOOL: Content similarity via Qdrant vectors (what the paper discusses)
- find_related_papers: Graph relationships via Neo4j (who/what it cites, shared authors)

Use when:
✓ 'Find papers similar to this one'
✓ 'More papers like ABC123'
✓ 'Papers with similar methodology/approach'

NOT for:
✗ 'Papers citing this' → use zot_find_citation_chain
✗ 'Papers by same author' → use zot_find_collaborator_network

Use for: Content-based 'More Like This' discovery using document vectors""",
    annotations={
        "readOnlyHint": True,
        "title": "Find Similar Papers (Vector)"
    }
)
def find_similar_papers(
    item_key: str,
    limit: int = 10,
    *,
    ctx: Context
) -> str:
    """
    Find papers similar to the given paper using vector similarity.

    Args:
        item_key: Zotero item key of the reference paper
        limit: Maximum number of similar papers to return (default: 10)
        ctx: MCP context

    Returns:
        Markdown-formatted list of similar papers with similarity scores
    """
    try:
        from pathlib import Path
        from agent_zot.search.semantic import create_semantic_search

        config_path = Path.home() / ".config" / "agent-zot" / "config.json"
        search = create_semantic_search(str(config_path))

        if not search or not search.qdrant_client:
            return "Semantic search is not initialized. Please run 'agent-zot update-db' first."

        ctx.info(f"Finding papers similar to {item_key}")

        # Fallback approach: Get the item and use its abstract for search
        ctx.info("Using abstract-based semantic search for similarity")
        zot = get_zotero_client()
        item = get_item_with_fallback(zot, item_key)

        if not item:
            return f"No item found with key: {item_key}"

        abstract = item.get("data", {}).get("abstractNote", "")
        if not abstract:
            return f"Item {item_key} has no abstract for similarity search.\n\n💡 Suggestion: Use zot_find_related_papers for graph-based relationships instead."

        # Use semantic search with the abstract
        results = search.search(query=abstract, limit=limit + 1)  # +1 to exclude the source paper

        # Format results
        output = [f"# Papers Similar to: {item_key}", ""]

        if "results" in results and results["results"]:
            # Filter out the source paper if it appears in results
            filtered_results = [p for p in results["results"] if p.get("item_key") != item_key][:limit]

            for i, paper in enumerate(filtered_results, 1):
                title = paper.get("title", "Untitled")
                authors = paper.get("creators_str", "Unknown authors")
                year = paper.get("year", "N/A")
                key = paper.get("item_key", "")
                score = paper.get("similarity_score", 0.0)

                output.append(f"## {i}. {title}")
                output.append(f"**Authors:** {authors}")
                output.append(f"**Year:** {year}")
                output.append(f"**Item Key:** `{key}`")
                output.append(f"**Similarity:** {score:.3f}")

                # Include abstract preview if available
                abs_text = paper.get("abstract", "")
                if abs_text:
                    preview = abs_text[:200] + "..." if len(abs_text) > 200 else abs_text
                    output.append(f"**Abstract:** {preview}")

                output.append("")

            output.append(f"\n**Total found:** {len(filtered_results)}")
        else:
            output.append("No similar papers found.")
            output.append("\n💡 Try:")
            output.append("- zot_semantic_search for topic-based discovery")
            output.append("- zot_find_related_papers for graph-based relationships")

        return "\n".join(output)

    except Exception as e:
        import traceback
        ctx.error(f"Error finding similar papers: {str(e)}")
        ctx.error(f"Traceback: {traceback.format_exc()}")
        return f"Error finding similar papers: {str(e)}"


@mcp.tool(
    name="zot_enhanced_semantic_search",
    description="🔥 HIGH PRIORITY - 🔵 ADVANCED - Implements Figure 3 pattern from Qdrant GraphRAG documentation.\n\nHow it works (4 steps):\n1. Semantic search in Qdrant finds relevant chunks\n2. Extracts chunk IDs (e.g., 'ABCD1234_chunk_5')\n3. Queries Neo4j for entities in those EXACT chunks\n4. Returns papers + matched text + entities from that text\n\n💡 Most precise search available. Use when you need to know:\n- 'Which concepts appear in papers about [topic]?'\n- 'What methods are used for [purpose] in the literature?'\n- 'Which theories are discussed alongside [concept]?'\n\nExample queries:\n✓ \"which methods appear in papers about [topic]?\"\n✓ \"what theories are discussed in [field] research?\"\n✓ \"which techniques are used for [purpose]?\"\n\nNOT for:\n✗ \"just find papers about [topic]\" → use zot_semantic_search (faster)\n✗ \"who worked with [author]\" → use zot_graph_search\n\n⚠️ Requires Neo4j population. If unpopulated (currently 0.5%), uses standard semantic search instead.\n\nUse for: Entity-aware semantic search, discovering what concepts/methods/theories appear in relevant passages",
    annotations={
        "readOnlyHint": True,
        "title": "Enhanced Semantic Search (Vector)"
    }
)
def enhanced_semantic_search(
    query: str,
    limit: int = 10,
    include_chunk_entities: bool = True,
    filters: Optional[str] = None,
    *,
    ctx: Context
) -> str:
    """
    Enhanced semantic search with chunk-level entity enrichment (Figure 3 pattern).

    This implements the full Qdrant GraphRAG architecture:
    1. Semantic search in Qdrant for relevant chunks
    2. Extract Qdrant point IDs from results
    3. Use those IDs to query Neo4j for chunk-specific entities
    4. Enrich each result with entities, types, and relationships

    Args:
        query: Search query text
        limit: Maximum number of results (default: 10)
        include_chunk_entities: Whether to enrich with Neo4j entities (default: True)
        filters: Optional metadata filters as JSON string
        ctx: MCP context

    Returns:
        Markdown-formatted results with chunk-level entities and entity types
    """
    try:
        from agent_zot.search.semantic import create_semantic_search
        from pathlib import Path

        if not query.strip():
            return "Error: Search query cannot be empty"

        ctx.info(f"Performing enhanced semantic search for: {query}")

        # Parse filters if provided
        parsed_filters = None
        if filters:
            if isinstance(filters, str):
                try:
                    parsed_filters = json.loads(filters)
                except json.JSONDecodeError as e:
                    return f"Error: Invalid JSON in filters parameter: {str(e)}"
            else:
                parsed_filters = filters

        config_path = Path.home() / ".config" / "agent-zot" / "config.json"
        search = create_semantic_search(str(config_path))

        # Call the enhanced_semantic_search method
        results = search.enhanced_semantic_search(
            query=query,
            limit=limit,
            include_chunk_entities=include_chunk_entities,
            filters=parsed_filters
        )

        if results.get("error"):
            return f"Error during enhanced search: {results['error']}"

        if not results.get("results"):
            return f"No results found for query: '{query}'\n\nTry:\n- Broadening your search terms\n- Running zot_update_search_database if you haven't indexed recently\n- Checking if Neo4j is populated (run with include_chunk_entities=False to test Qdrant only)"

        # Format results
        output = [f"# Enhanced Semantic Search Results"]
        output.append(f"\n**Query:** {query}")
        output.append(f"**Search Type:** {results.get('search_type', 'enhanced_semantic')}")
        output.append(f"**Neo4j Enabled:** {results.get('neo4j_enabled', False)}")
        output.append(f"**Results:** {results['total_found']}\n")

        for i, result in enumerate(results["results"], 1):
            # Extract result data
            item_key = result.get("item_key", "unknown")
            similarity = result.get("similarity_score", 0)
            matched_text = result.get("matched_text", "")[:300]  # First 300 chars

            # Get paper title from zotero_item
            title = "Unknown"
            if result.get("zotero_item"):
                zotero_data = result["zotero_item"].get("data", {})
                title = zotero_data.get("title", "Unknown")

            output.append(f"## {i}. {title}")
            output.append(f"**Item Key:** {item_key}")
            output.append(f"**Relevance:** {similarity:.3f}")

            # Show chunk entities if available
            if result.get("chunk_entities"):
                entities = result["chunk_entities"]
                entity_types = result.get("entity_types", [])
                sample_entities = result.get("sample_entities", [])

                output.append(f"\n**Entities Found in This Chunk:** {len(entities)}")
                if entity_types:
                    output.append(f"**Entity Types:** {', '.join(entity_types)}")
                if sample_entities:
                    output.append(f"**Key Entities:** {', '.join(sample_entities[:5])}")

                # Show detailed entities
                output.append(f"\n**Detailed Entities:**")
                for entity in entities[:10]:  # Show first 10
                    entity_name = entity.get("name", "Unknown")
                    entity_types_list = entity.get("types", [])
                    entity_desc = entity.get("description", "")

                    # Filter out base "Entity" type
                    types_str = ", ".join([t for t in entity_types_list if t != "Entity"])

                    output.append(f"- **{entity_name}** ({types_str})")
                    if entity_desc:
                        output.append(f"  └─ {entity_desc[:100]}")

                if len(entities) > 10:
                    output.append(f"  ... and {len(entities) - 10} more entities")

            elif include_chunk_entities and results.get("neo4j_enabled"):
                output.append(f"\n*No entities found for this chunk (Neo4j may not have data for this paper yet)*")

            # Show matched text snippet
            output.append(f"\n**Matched Text Snippet:**")
            output.append(f"> {matched_text}...")
            output.append("")

        output.append("\n---")
        output.append("**💡 Tips:**")
        output.append("- Use `zot_ask_paper(item_key, question)` to read more content from specific papers")
        output.append("- Use `zot_graph_search(entity_name)` to explore entity relationships")
        output.append("- Entities are extracted from the exact chunks that matched your query")

        return "\n".join(output)

    except Exception as e:
        import traceback
        ctx.error(f"Error in enhanced_semantic_search: {str(e)}")
        ctx.error(f"Traceback: {traceback.format_exc()}")
        return f"Error performing enhanced semantic search: {str(e)}"


# DEPRECATED - Removed for pure agentic approach
# Workflow orchestration tools are "training wheels" in agentic systems
# Agents should learn to chain primitives: semantic_search → graph operations → synthesis
# @mcp.tool(
#     name="zot_literature_review",
#     description="🔵 WORKFLOW - Automated literature review workflow: search papers → analyze themes → identify gaps → generate structured summary. Coordinates multiple tools (semantic search, graph analysis, temporal trends) for comprehensive research synthesis.\n\n💡 This orchestrates Qdrant, Neo4j, and Zotero API tools automatically for comprehensive reviews.\n\nUse for: Generating structured literature reviews on research topics (end-to-end workflow)",
#     annotations={
#         "readOnlyHint": True,
#         "title": "Literature Review (Workflow)"
#     }
# )

# ============================================================================
# GRAPH TOOLS - Knowledge Graph Operations (Neo4j)
# ============================================================================
@mcp.tool(
    name="zot_graph_search",
    description="📊 MEDIUM PRIORITY - 🟢 PRIMARY for relationship/network queries. Use when query involves connections, collaborations, or \"who/what is related to X\". Neo4j knowledge graph search for finding relationships between authors, institutions, concepts, methods, or other entities.\n\n💡 Often combines with zot_semantic_search to first discover papers by content, then explore their relationships.\n\nExample queries:\n✓ \"who collaborated with [author]?\"\n✓ \"institutions working on [topic]\"\n✓ \"authors researching [concept]\"\n\nNOT for:\n✗ \"papers about [topic]\" → use zot_semantic_search\n✗ \"what is [concept]\" → use zot_ask_paper\n\nUse for: Exploring relationships like \"who collaborated with [author]?\" or \"institutions working on [topic]\"",
    annotations={
        "readOnlyHint": True,
        "title": "Graph Search (Graph)"
    }
)
def graph_search(
    query: str,
    entity_types: Optional[str] = None,
    limit: int = 10,
    *,
    ctx: Context
) -> str:
    """
    Search the Neo4j knowledge graph for entities and concepts.

    Args:
        query: Search query for entities (e.g., "transformer architecture", "attention mechanism")
        entity_types: Comma-separated entity types to filter (e.g., "Concept,Method")
        limit: Maximum number of results (default: 10)
        ctx: MCP context

    Returns:
        Markdown-formatted graph search results
    """
    try:
        from agent_zot.search.semantic import create_semantic_search
        from pathlib import Path

        config_path = Path.home() / ".config" / "agent-zot" / "config.json"
        search = create_semantic_search(str(config_path))

        # Parse entity types
        entity_types_list = None
        if entity_types:
            entity_types_list = [t.strip() for t in entity_types.split(",")]

        # Perform graph search
        results = search.graph_search(
            query=query,
            entity_types=entity_types_list,
            limit=limit
        )

        if results.get("error"):
            return f"Graph search error: {results['error']}"

        entities = results.get("results", [])

        if not entities:
            return f"No entities found in knowledge graph for query: '{query}'"

        # Format results
        output = [f"# Knowledge Graph Search Results for '{query}'", ""]
        output.append(f"Found {len(entities)} entities:")
        output.append("")

        for i, entity in enumerate(entities, 1):
            entity_name = entity.get("name", "Unknown")
            entity_types = ", ".join(entity.get("types", []))
            description = entity.get("description", "No description")

            output.append(f"## {i}. {entity_name}")
            output.append(f"**Type:** {entity_types}")
            output.append(f"**Description:** {description}")
            output.append("")

        return "\n".join(output)

    except Exception as e:
        ctx.error(f"Error in graph search: {str(e)}")
        return f"Error in graph search: {str(e)}"


@mcp.tool(
    name="zot_find_related_papers",
    description="📊 MEDIUM PRIORITY - 🟢 SECONDARY - Find papers related to a given paper via shared entities in the knowledge graph. Use when you want to discover connections through citations, authors, or concepts.\n\n💡 Best used AFTER zot_semantic_search to discover relationships between found papers.\n⚠️ For content-based similarity, use zot_semantic_search instead.\n\nExample use cases:\n✓ After finding key paper: \"What else cites this?\"\n✓ \"Papers by same authors or on related concepts\"\n✓ \"Follow citation trail from this paper\"\n\nNOT for:\n✗ \"papers similar to [broad concept]\" → use zot_semantic_search\n✗ \"broad topic discovery\" → use zot_semantic_search first\n\nUse for: Discovering papers connected through citations, authors, or shared concepts (relationship-based, not content-based)",
    annotations={
        "readOnlyHint": True,
        "title": "Find Related Papers (Graph)"
    }
)
def find_related_papers(
    item_key: str,
    limit: int = 10,
    *,
    ctx: Context
) -> str:
    """
    Find papers related to a given paper using the knowledge graph.

    Args:
        item_key: Zotero item key of the source paper
        limit: Maximum number of related papers to return (default: 10)
        ctx: MCP context

    Returns:
        Markdown-formatted related papers with shared entities
    """
    try:
        from agent_zot.search.semantic import create_semantic_search
        from pathlib import Path

        config_path = Path.home() / ".config" / "agent-zot" / "config.json"
        search = create_semantic_search(str(config_path))

        # Find related papers
        results = search.find_related_papers(paper_key=item_key, limit=limit)

        if results.get("error"):
            return f"Error finding related papers: {results['error']}"

        related_papers = results.get("results", [])

        if not related_papers:
            return f"No related papers found for item: {item_key}"

        # Format results
        output = [f"# Papers Related to {item_key}", ""]
        output.append(f"Found {len(related_papers)} related papers via knowledge graph:")
        output.append("")

        for i, paper in enumerate(related_papers, 1):
            title = paper.get("title", "Untitled")
            year = paper.get("year", "N/A")
            authors = paper.get("authors", [])
            shared_count = paper.get("shared_entities", 0)
            sample_entities = paper.get("sample_entities", [])

            output.append(f"## {i}. {title}")
            output.append(f"**Year:** {year}")
            if authors:
                output.append(f"**Authors:** {', '.join(authors[:3])}")
            output.append(f"**Shared Entities:** {shared_count}")
            if sample_entities:
                output.append(f"**Sample Connections:** {', '.join(sample_entities)}")
            output.append(f"**Item Key:** {paper.get('item_key', 'N/A')}")
            output.append("")

        return "\n".join(output)

    except Exception as e:
        ctx.error(f"Error finding related papers: {str(e)}")
        return f"Error finding related papers: {str(e)}"


@mcp.tool(
    name="zot_find_citation_chain",
    description="📊 MEDIUM PRIORITY - 🟢 SECONDARY - Find papers citing papers that cite a given paper (multi-hop citation analysis). Use for discovering extended citation networks.\n\n💡 Best used AFTER zot_semantic_search to discover relationships between found papers.\n⚠️ Requires Neo4j knowledge graph. For content-based discovery, use zot_semantic_search instead.\n\nUse for: Tracing how ideas propagate through citation networks (relationship analysis, not content analysis)",
    annotations={
        "readOnlyHint": True,
        "title": "Find Citation Chain (Graph)"
    }
)
def find_citation_chain(
    paper_key: str,
    max_hops: int = 2,
    limit: int = 10,
    *,
    ctx: Context
) -> str:
    """
    Find citation chains showing how papers cite papers that cite the given paper.

    Args:
        paper_key: Zotero item key of the starting paper
        max_hops: Maximum citation hops (1-3, default: 2)
        limit: Maximum papers to return (default: 10)
        ctx: MCP context

    Returns:
        Markdown-formatted citation chain with hop distances
    """
    try:
        from pathlib import Path
        from agent_zot.clients.neo4j_graphrag import create_neo4j_graphrag_client

        config_path = Path.home() / ".config" / "agent-zot" / "config.json"
        graph_client = create_neo4j_graphrag_client(str(config_path))

        if not graph_client:
            return "Neo4j GraphRAG is not enabled. Please configure it in config.json."

        ctx.info(f"Finding citation chain for paper: {paper_key} (max hops: {max_hops})")

        results = graph_client.find_citation_chain(
            paper_key=paper_key,
            max_hops=max_hops,
            limit=limit
        )

        if not results:
            return f"No citation chain found for paper: {paper_key}"

        # Format results as markdown
        output = [f"# Citation Chain for {paper_key}\n"]
        output.append(f"Found {len(results)} papers in citation network (max {max_hops} hops):\n")

        for paper in results:
            hops = paper.get("citation_hops", 0)
            title = paper.get("title", "Unknown")
            year = paper.get("year", "N/A")
            key = paper.get("item_key", "")
            path = paper.get("citation_path", [])

            output.append(f"## {title} ({year})")
            output.append(f"- **Key**: {key}")
            output.append(f"- **Citation Distance**: {hops} hop{'s' if hops != 1 else ''}")
            if path:
                output.append(f"- **Citation Path**: {' → '.join(path[:3])}{'...' if len(path) > 3 else ''}")
            output.append("")

        return "\n".join(output)

    except Exception as e:
        ctx.error(f"Error finding citation chain: {str(e)}")
        return f"Error finding citation chain: {str(e)}"


@mcp.tool(
    name="zot_explore_concept_network",
    description="📊 MEDIUM PRIORITY - 🟢 SECONDARY - Find concepts related through intermediate concepts (concept propagation). Discovers conceptual relationships by traversing the knowledge graph.\n\n💡 Best used AFTER zot_semantic_search to discover relationships between found papers.\n⚠️ Requires Neo4j knowledge graph. For content-based concept discovery, use zot_semantic_search instead.\n\nUse for: Mapping how concepts connect through shared papers (network analysis, not content analysis)",
    annotations={
        "readOnlyHint": True,
        "title": "Explore Concept Network (Graph)"
    }
)
def explore_concept_network(
    concept: str,
    max_hops: int = 2,
    limit: int = 15,
    *,
    ctx: Context
) -> str:
    """
    Explore related concepts through multi-hop graph traversal.

    Args:
        concept: Starting concept name
        max_hops: Maximum relationship hops (1-3, default: 2)
        limit: Maximum concepts to return (default: 15)
        ctx: MCP context

    Returns:
        Markdown-formatted related concepts with relationship paths
    """
    try:
        from pathlib import Path
        from agent_zot.clients.neo4j_graphrag import create_neo4j_graphrag_client

        config_path = Path.home() / ".config" / "agent-zot" / "config.json"
        graph_client = create_neo4j_graphrag_client(str(config_path))

        if not graph_client:
            return "Neo4j GraphRAG is not enabled. Please configure it in config.json."

        ctx.info(f"Exploring concept network for: {concept} (max hops: {max_hops})")

        results = graph_client.find_related_concepts(
            concept=concept,
            max_hops=max_hops,
            limit=limit
        )

        if not results:
            return f"No related concepts found for: {concept}"

        # Format results as markdown
        output = [f"# Related Concepts for '{concept}'\n"]
        output.append(f"Found {len(results)} related concepts (max {max_hops} hops):\n")

        for item in results:
            concept_name = item.get("concept", "Unknown")
            hops = item.get("relationship_hops", 0)
            paper_count = item.get("paper_count", 0)
            sample_papers = item.get("sample_papers", [])

            output.append(f"## {concept_name}")
            output.append(f"- **Relationship Distance**: {hops} hop{'s' if hops != 1 else ''}")
            output.append(f"- **Papers Discussing Both**: {paper_count}")
            if sample_papers:
                output.append(f"- **Sample Papers**:")
                for paper in sample_papers[:3]:
                    output.append(f"  - {paper}")
            output.append("")

        return "\n".join(output)

    except Exception as e:
        ctx.error(f"Error exploring concept network: {str(e)}")
        return f"Error exploring concept network: {str(e)}"


@mcp.tool(
    name="zot_find_collaborator_network",
    description="📊 MEDIUM PRIORITY - 🟢 SECONDARY - Find collaborators of collaborators (co-authorship network). Discovers extended collaboration networks by traversing author relationships.\n\n💡 Best used AFTER zot_semantic_search to discover relationships between found papers.\n⚠️ Requires Neo4j knowledge graph. For simpler author queries, use zot_semantic_search with author filters instead.\n\nUse for: Analyzing multi-hop author collaboration patterns and networks (network analysis)",
    annotations={
        "readOnlyHint": True,
        "title": "Find Collaborator Network (Graph)"
    }
)
def find_collaborator_network(
    author: str,
    max_hops: int = 2,
    limit: int = 20,
    *,
    ctx: Context
) -> str:
    """
    Find extended collaboration network for an author.

    Args:
        author: Author name to start from
        max_hops: Maximum collaboration hops (1-3, default: 2)
        limit: Maximum collaborators to return (default: 20)
        ctx: MCP context

    Returns:
        Markdown-formatted collaborator network with distances
    """
    try:
        from pathlib import Path
        from agent_zot.clients.neo4j_graphrag import create_neo4j_graphrag_client

        config_path = Path.home() / ".config" / "agent-zot" / "config.json"
        graph_client = create_neo4j_graphrag_client(str(config_path))

        if not graph_client:
            return "Neo4j GraphRAG is not enabled. Please configure it in config.json."

        ctx.info(f"Finding collaborator network for: {author} (max hops: {max_hops})")

        results = graph_client.find_collaborator_network(
            author=author,
            max_hops=max_hops,
            limit=limit
        )

        if not results:
            return f"No collaborators found for: {author}"

        # Format results as markdown
        output = [f"# Collaborator Network for '{author}'\n"]
        output.append(f"Found {len(results)} collaborators (max {max_hops} hops):\n")

        for item in results:
            collab_name = item.get("author", "Unknown")
            hops = item.get("collaboration_hops", 0)
            collab_count = item.get("collaboration_count", 0)
            sample_papers = item.get("sample_papers", [])

            output.append(f"## {collab_name}")
            output.append(f"- **Collaboration Distance**: {hops} hop{'s' if hops != 1 else ''}")
            output.append(f"- **Shared Papers**: {collab_count}")
            if sample_papers:
                output.append(f"- **Sample Collaborations**:")
                for paper in sample_papers[:3]:
                    output.append(f"  - {paper}")
            output.append("")

        return "\n".join(output)

    except Exception as e:
        ctx.error(f"Error finding collaborator network: {str(e)}")
        return f"Error finding collaborator network: {str(e)}"


@mcp.tool(
    name="zot_find_seminal_papers",
    description="📊 MEDIUM PRIORITY - 🟢 SECONDARY - Find most influential papers using citation-based analysis. Identifies highly-cited foundational papers using graph metrics.\n\n💡 Best used AFTER zot_semantic_search to discover relationships between found papers.\n⚠️ Requires Neo4j knowledge graph. For content-based importance, use zot_semantic_search with relevance ranking instead.\n\nUse for: Identifying papers by citation impact (citation-based ranking, not content-based relevance)",
    annotations={
        "readOnlyHint": True,
        "title": "Find Seminal Papers (Graph)"
    }
)
def find_seminal_papers(
    field: str = None,
    top_n: int = 10,
    *,
    ctx: Context
) -> str:
    """
    Find seminal/influential papers based on citation network analysis.

    Args:
        field: Optional field name to filter papers (default: None, all fields)
        top_n: Number of top papers to return (default: 10)
        ctx: MCP context

    Returns:
        Markdown-formatted list of influential papers with influence scores
    """
    try:
        from pathlib import Path
        from agent_zot.clients.neo4j_graphrag import create_neo4j_graphrag_client

        config_path = Path.home() / ".config" / "agent-zot" / "config.json"
        graph_client = create_neo4j_graphrag_client(str(config_path))

        if not graph_client:
            return "Neo4j GraphRAG is not enabled. Please configure it in config.json."

        field_info = f" in field: {field}" if field else " across all fields"
        ctx.info(f"Finding seminal papers{field_info} (top {top_n})")

        results = graph_client.find_seminal_papers(
            field=field,
            top_n=top_n
        )

        if not results:
            return f"No seminal papers found{field_info}"

        # Format results as markdown
        output = [f"# Seminal Papers{field_info.title()}\n"]
        output.append(f"Top {len(results)} most influential papers by citation analysis:\n")

        for i, paper in enumerate(results, 1):
            title = paper.get("title", "Unknown")
            year = paper.get("year", "N/A")
            key = paper.get("item_key", "")
            influence = paper.get("influence_score", 0)

            output.append(f"## {i}. {title} ({year})")
            output.append(f"- **Key**: {key}")
            output.append(f"- **Influence Score**: {influence:.2f} citations")
            output.append("")

        output.append("\n*Note: Influence score based on citation count (proxy for PageRank)*")

        return "\n".join(output)

    except Exception as e:
        ctx.error(f"Error finding seminal papers: {str(e)}")
        return f"Error finding seminal papers: {str(e)}"


@mcp.tool(
    name="zot_track_topic_evolution",
    description="📊 MEDIUM PRIORITY - 🟢 SECONDARY - Track how a research topic/concept has evolved over time using graph analysis. Shows yearly paper counts, related concepts, and trends.\n\n💡 Best used AFTER zot_semantic_search to discover relationships between found papers.\n⚠️ Requires Neo4j knowledge graph. For simpler temporal queries, use zot_find_recent_developments instead.\n\nUse for: Analyzing research trajectory and concept emergence over time (temporal network analysis)",
    annotations={
        "readOnlyHint": True,
        "title": "Track Topic Evolution (Graph)"
    }
)
def track_topic_evolution(
    concept: str,
    start_year: int,
    end_year: int,
    *,
    ctx: Context
) -> str:
    """
    Track temporal evolution of a research topic with yearly breakdown.

    Args:
        concept: Concept name to track (must exist in knowledge graph)
        start_year: Start year for analysis
        end_year: End year for analysis
        ctx: MCP context

    Returns:
        Markdown-formatted evolution analysis with yearly data and trends
    """
    try:
        from pathlib import Path
        from agent_zot.clients.neo4j_graphrag import create_neo4j_graphrag_client

        config_path = Path.home() / ".config" / "agent-zot" / "config.json"
        graph_client = create_neo4j_graphrag_client(str(config_path))

        if not graph_client:
            return "Neo4j GraphRAG is not enabled. Please configure it in config.json."

        ctx.info(f"Tracking evolution of '{concept}' from {start_year}-{end_year}")

        result = graph_client.track_topic_evolution(
            concept=concept,
            start_year=start_year,
            end_year=end_year
        )

        if result.get("error"):
            return f"Error tracking topic evolution: {result['error']}"

        if result.get("total_papers", 0) == 0:
            return f"No papers found discussing '{concept}' from {start_year}-{end_year}"

        # Format results as markdown
        output = [f"# Topic Evolution: '{concept}' ({start_year}-{end_year})\n"]
        output.append(f"**Total Papers**: {result['total_papers']}")
        output.append(f"**Trend**: {result['trend'].upper()}\n")

        # Yearly breakdown
        yearly_data = result.get("yearly_breakdown", [])
        if yearly_data:
            output.append("## Yearly Breakdown\n")
            for year_info in yearly_data:
                year = year_info.get("year", "Unknown")
                count = year_info.get("paper_count", 0)
                samples = year_info.get("sample_papers", [])

                output.append(f"### {year}: {count} paper{'s' if count != 1 else ''}")
                if samples:
                    output.append("Sample papers:")
                    for paper in samples[:2]:
                        output.append(f"- {paper}")
                output.append("")

        # Related concepts
        related = result.get("related_concepts", [])
        if related:
            output.append("## Related Concepts (Co-occurring)\n")
            for item in related[:5]:
                concept_name = item.get("concept", "Unknown")
                count = item.get("co_occurrence_count", 0)
                first_year = item.get("first_appeared", "Unknown")

                output.append(f"- **{concept_name}**: {count} papers (first appeared: {first_year})")

        return "\n".join(output)

    except Exception as e:
        ctx.error(f"Error tracking topic evolution: {str(e)}")
        return f"Error tracking topic evolution: {str(e)}"


# DEPRECATED - Use zot_semantic_search with date filters instead
# Redundant tool - just calls semantic_search with year filter
# Agents should use: semantic_search(query="topic", filters={"year": {"$gte": 2023}})
# @mcp.tool(
#     name="zot_find_recent_developments",
#     description="🟢 SECONDARY - Find recent papers on a topic (default: last 2 years). Uses hybrid semantic search with temporal filtering.\n\n💡 This combines Qdrant semantic search with temporal filtering - good for \"recent papers about X\" queries.\n\nUse for: Discovering latest research developments on established topics (time-filtered semantic search)",
#     annotations={
#         "readOnlyHint": True,
#         "title": "Find Recent Developments (Temporal)"
#     }
# )


@mcp.tool(
    name="zot_analyze_venues",
    description="🔧 LOW PRIORITY - 🟢 SECONDARY - Analyze publication venues (journals/conferences) to identify top outlets using graph analysis. Shows paper counts and sample publications.\n\n💡 Best used AFTER zot_semantic_search to discover relationships between found papers.\n⚠️ Requires Neo4j knowledge graph. For content queries, use zot_semantic_search instead.\n\nUse for: Examining publication venue patterns and outlet rankings (venue analysis, not content analysis)",
    annotations={
        "readOnlyHint": True,
        "title": "Analyze Venues (Graph)"
    }
)
def analyze_venues(
    field: str = None,
    top_n: int = 10,
    *,
    ctx: Context
) -> str:
    """
    Analyze most common publication venues.

    Args:
        field: Optional field name to filter by (default: None, all fields)
        top_n: Number of top venues to return (default: 10)
        ctx: MCP context

    Returns:
        Markdown-formatted venue analysis with paper counts
    """
    try:
        from pathlib import Path
        from agent_zot.clients.neo4j_graphrag import create_neo4j_graphrag_client

        config_path = Path.home() / ".config" / "agent-zot" / "config.json"
        graph_client = create_neo4j_graphrag_client(str(config_path))

        if not graph_client:
            return "Neo4j GraphRAG is not enabled. Please configure it in config.json."

        field_info = f" in field: {field}" if field else " across all fields"
        ctx.info(f"Analyzing publication venues{field_info} (top {top_n})")

        results = graph_client.analyze_publication_venues(
            field=field,
            top_n=top_n
        )

        if not results:
            return f"No publication venues found{field_info}"

        # Format results as markdown
        output = [f"# Top Publication Venues{field_info.title()}\n"]
        output.append(f"Found {len(results)} top venues by publication count:\n")

        for i, venue_data in enumerate(results, 1):
            venue = venue_data.get("venue", "Unknown")
            count = venue_data.get("paper_count", 0)
            samples = venue_data.get("sample_papers", [])

            output.append(f"## {i}. {venue}")
            output.append(f"- **Papers Published**: {count}")

            if samples:
                output.append(f"- **Sample Publications**:")
                for paper in samples[:3]:
                    output.append(f"  - {paper}")

            output.append("")

        return "\n".join(output)

    except Exception as e:
        ctx.error(f"Error analyzing venues: {str(e)}")
        return f"Error analyzing venues: {str(e)}"



# ============================================================================
# ZOTERO TOOLS - Metadata & CRUD Operations
# ============================================================================
@mcp.tool(
    name="zot_search_items",
    description="📊 MEDIUM PRIORITY - ⚪ FALLBACK - Direct Zotero API keyword-based metadata search. Use ONLY for exact title/author/year lookups when you don't have item keys yet.\n\n⚠️ DO NOT use after zot_semantic_search - you already have item keys! Use zot_get_item() for metadata or zot_ask_paper() for content instead.\n\n⚠️ This is literal keyword matching, NOT semantic. Always try zot_semantic_search first for research queries.\n\nUse for: Finding papers when you know exact author name/title phrase but don't have item key yet",
    annotations={
        "readOnlyHint": True,
        "title": "Search Items (Zotero)"
    }
)
def search_items(
    query: str,
    qmode: str = "titleCreatorYear",
    item_type: str = "-attachment",  # Exclude attachments by default
    limit: int = 10,
    tag: Optional[List[str]] = None,
    *,
    ctx: Context
) -> str:
    """
    Search for items in your Zotero library.

    Args:
        query: Search query string
        qmode: Query mode - must be "titleCreatorYear" or "everything" (default: "titleCreatorYear")
        item_type: Type of items to search for. Use "-attachment" to exclude attachments.
        limit: Maximum number of results to return
        tag: List of tags conditions to filter by
        ctx: MCP context

    Returns:
        Markdown-formatted search results
    """
    try:
        if not query.strip():
            return "Error: Search query cannot be empty"

        # Validate qmode parameter
        if qmode not in ["titleCreatorYear", "everything"]:
            return f"Error: Invalid qmode '{qmode}'. Must be 'titleCreatorYear' or 'everything'"
        
        tag_condition_str = ""
        if tag:
            tag_condition_str = f" with tags: '{', '.join(tag)}'"    
        else :
            tag = []

        ctx.info(f"Searching Zotero for '{query}'{tag_condition_str}")
        zot = get_zotero_client()

        # Search using the query parameters
        zot.add_parameters(q=query, qmode=qmode, itemType=item_type, limit=limit, tag=tag)
        results = zot.items()

        if not results:
            return f"No items found matching query: '{query}'{tag_condition_str}"
        
        # Format results as markdown
        output = [f"# Search Results for '{query}'", f"{tag_condition_str}", ""]
        
        for i, item in enumerate(results, 1):
            data = item.get("data", {})
            title = data.get("title", "Untitled")
            item_type = data.get("itemType", "unknown")
            date = data.get("date", "No date")
            key = item.get("key", "")
            
            # Format creators
            creators = data.get("creators", [])
            creators_str = format_creators(creators)
            
            # Build the formatted entry
            output.append(f"## {i}. {title}")
            output.append(f"**Type:** {item_type}")
            output.append(f"**Item Key:** {key}")
            output.append(f"**Date:** {date}")
            output.append(f"**Authors:** {creators_str}")
            
            # Add abstract snippet if present
            if abstract := data.get("abstractNote"):
                # Limit abstract length for search results
                abstract_snippet = abstract[:200] + "..." if len(abstract) > 200 else abstract
                output.append(f"**Abstract:** {abstract_snippet}")
            
            # Add tags if present
            if tags := data.get("tags"):
                tag_list = [f"`{tag['tag']}`" for tag in tags]
                if tag_list:
                    output.append(f"**Tags:** {' '.join(tag_list)}")
            
            output.append("")  # Empty line between items
        
        return "\n".join(output)
    
    except Exception as e:
        ctx.error(f"Error searching Zotero: {str(e)}")
        return f"Error searching Zotero: {str(e)}"

@mcp.tool(
    name="zot_search_by_tag",
    description="📊 MEDIUM PRIORITY - ⚪ FALLBACK - Search for items by tag with advanced operators. Use when filtering by tags/metadata, not for semantic content search.\n\nSupports disjunction (tag1 || tag2), exclusion (-tag), and AND logic across conditions.\n\n⚠️ For semantic research queries, use zot_semantic_search first.\n\nUse for: Complex tag-based filtering like ['important || urgent', '-draft'] for (important OR urgent) AND NOT draft",
    annotations={
        "readOnlyHint": True,
        "title": "Search by Tag (Zotero)"
    }
)
def search_by_tag(
    tag: List[str],
    item_type: str = "-attachment",
    limit: Optional[int] = 10,
    *,
    ctx: Context
) -> str:
    """
    Search for items in your Zotero library by tag。
    Conditions are ANDed, each term supports disjunction`||` and exclusion`-`.
    
    Args:
        tag: List of tag conditions. Items are returned only if they satisfy 
            ALL conditions in the list. Each tag condition can be expressed 
            in two ways:
                As alternatives: tag1 || tag2 (matches items with either tag1 OR tag2)
                As exclusions: -tag (matches items that do NOT have this tag)
            For example, a tag field with ["research || important", "-draft"] would 
            return items that:
                Have either "research" OR "important" tags, AND
                Do NOT have the "draft" tag
        item_type: Type of items to search for. Use "-attachment" to exclude attachments.
        limit: Maximum number of results to return
        ctx: MCP context
    
    Returns:
        Markdown-formatted search results
    """
    try:
        if not tag:
            return "Error: Tag cannot be empty"

        ctx.info(f"Searching Zotero for tag '{tag}'")
        zot = get_zotero_client()
        
        
        # Search using the query parameters
        zot.add_parameters(q="", tag=tag, itemType=item_type, limit=limit)
        results = zot.items()
        
        if not results:
            return f"No items found with tag: '{tag}'"
        
        # Format results as markdown
        output = [f"# Search Results for Tag: '{tag}'", ""]
        
        for i, item in enumerate(results, 1):
            data = item.get("data", {})
            title = data.get("title", "Untitled")
            item_type = data.get("itemType", "unknown")
            date = data.get("date", "No date")
            key = item.get("key", "")
            
            # Format creators
            creators = data.get("creators", [])
            creators_str = format_creators(creators)
            
            # Build the formatted entry
            output.append(f"## {i}. {title}")
            output.append(f"**Type:** {item_type}")
            output.append(f"**Item Key:** {key}")
            output.append(f"**Date:** {date}")
            output.append(f"**Authors:** {creators_str}")
            
            # Add abstract snippet if present
            if abstract := data.get("abstractNote"):
                # Limit abstract length for search results
                abstract_snippet = abstract[:200] + "..." if len(abstract) > 200 else abstract
                output.append(f"**Abstract:** {abstract_snippet}")
            
            # Add tags if present
            if tags := data.get("tags"):
                tag_list = [f"`{tag['tag']}`" for tag in tags]
                if tag_list:
                    output.append(f"**Tags:** {' '.join(tag_list)}")
            
            output.append("")  # Empty line between items
        
        return "\n".join(output)
    
    except Exception as e:
        ctx.error(f"Error searching Zotero: {str(e)}")
        return f"Error searching Zotero: {str(e)}"

# DEPRECATED - Use zot_get_item() instead
# @mcp.tool(
#     name="zot_get_item_metadata",
#     description="⚠️ DEPRECATED: Use zot_get_item() instead for unified retrieval.\n\nGet detailed metadata for a specific Zotero item by its key.\n\nUse for: Retrieving bibliographic details (title, authors, date, abstract) for a known item key",
#     annotations={
#         "readOnlyHint": True,
#         "title": "Get Item Metadata (Deprecated)"
#     }
# )


@mcp.tool(
    name="zot_get_collections",
    description="📊 MEDIUM PRIORITY - 🔸 SECONDARY - List all collections in your Zotero library.\n\nUse for: Browsing library organization structure and collection hierarchy"
,
    annotations={
        "readOnlyHint": True,
        "title": "Get Collections (Zotero)"
    }
)
def get_collections(
    limit: Optional[int] = None,
    *,
    ctx: Context
) -> str:
    """
    List all collections in your Zotero library.
    
    Args:
        limit: Maximum number of collections to return
        ctx: MCP context
    
    Returns:
        Markdown-formatted list of collections
    """
    try:
        ctx.info("Fetching collections")
        zot = get_zotero_client()
        
        
        collections = zot.collections(limit=limit)
        
        # Always return the header, even if empty
        output = ["# Zotero Collections", ""]
        
        if not collections:
            output.append("No collections found in your Zotero library.")
            return "\n".join(output)
        
        # Create a mapping of collection IDs to their data
        collection_map = {c["key"]: c for c in collections}
        
        # Create a mapping of parent to child collections
        # Only add entries for collections that actually exist
        hierarchy = {}
        for coll in collections:
            parent_key = coll["data"].get("parentCollection")
            # Handle various representations of "no parent"
            if parent_key in ["", None] or not parent_key:
                parent_key = None  # Normalize to None
            
            if parent_key not in hierarchy:
                hierarchy[parent_key] = []
            hierarchy[parent_key].append(coll["key"])
        
        # Function to recursively format collections
        def format_collection(key, level=0):
            if key not in collection_map:
                return []
            
            coll = collection_map[key]
            name = coll["data"].get("name", "Unnamed Collection")
            
            # Create indentation for hierarchy
            indent = "  " * level
            lines = [f"{indent}- **{name}** (Key: {key})"]
            
            # Add children if they exist
            child_keys = hierarchy.get(key, [])
            for child_key in sorted(child_keys):  # Sort for consistent output
                lines.extend(format_collection(child_key, level + 1))
            
            return lines
        
        # Start with top-level collections (those with None as parent)
        top_level_keys = hierarchy.get(None, [])
        
        if not top_level_keys:
            # If no clear hierarchy, just list all collections
            output.append("Collections (flat list):")
            for coll in sorted(collections, key=lambda x: x["data"].get("name", "")):
                name = coll["data"].get("name", "Unnamed Collection")
                key = coll["key"]
                output.append(f"- **{name}** (Key: {key})")
        else:
            # Display hierarchical structure
            for key in sorted(top_level_keys):
                output.extend(format_collection(key))
        
        return "\n".join(output)
    
    except Exception as e:
        ctx.error(f"Error fetching collections: {str(e)}")
        error_msg = f"Error fetching collections: {str(e)}"
        return f"# Zotero Collections\n\n{error_msg}"


@mcp.tool(
    name="zot_get_collection_items",
    description="📊 MEDIUM PRIORITY - 🔸 SECONDARY - Get all items in a specific Zotero collection.\n\nUse for: Retrieving all papers in a specific collection by collection key"
,
    annotations={
        "readOnlyHint": True,
        "title": "Get Collection Items (Zotero)"
    }
)
def get_collection_items(
    collection_key: str,
    limit: Optional[int] = 50,
    *,
    ctx: Context
) -> str:
    """
    Get all items in a specific Zotero collection.
    
    Args:
        collection_key: The collection key/ID
        limit: Maximum number of items to return
        ctx: MCP context
    
    Returns:
        Markdown-formatted list of items in the collection
    """
    try:
        ctx.info(f"Fetching items for collection {collection_key}")
        zot = get_zotero_client()
        
        # First get the collection details
        try:
            collection = zot.collection(collection_key)
            collection_name = collection["data"].get("name", "Unnamed Collection")
        except Exception:
            collection_name = f"Collection {collection_key}"
        
        
        # Then get the items
        items = zot.collection_items(collection_key, limit=limit)
        if not items:
            return f"No items found in collection: {collection_name} (Key: {collection_key})"
        
        # Format items as markdown
        output = [f"# Items in Collection: {collection_name}", ""]
        
        for i, item in enumerate(items, 1):
            data = item.get("data", {})
            title = data.get("title", "Untitled")
            item_type = data.get("itemType", "unknown")
            date = data.get("date", "No date")
            key = item.get("key", "")
            
            # Format creators
            creators = data.get("creators", [])
            creators_str = format_creators(creators)
            
            # Build the formatted entry
            output.append(f"## {i}. {title}")
            output.append(f"**Type:** {item_type}")
            output.append(f"**Item Key:** {key}")
            output.append(f"**Date:** {date}")
            output.append(f"**Authors:** {creators_str}")
            
            output.append("")  # Empty line between items
        
        return "\n".join(output)

    except Exception as e:
        ctx.error(f"Error fetching collection items: {str(e)}")
        return f"Error fetching collection items: {str(e)}"


@mcp.tool(
    name="zot_create_collection",
    description="📊 MEDIUM PRIORITY - 🔸 SECONDARY - Create a new collection in your Zotero library.\n\nUse for: Organizing papers into new collection like 'Machine Learning 2024'"
,
    annotations={
        "readOnlyHint": True,
        "title": "Create Collection (Zotero)"
    }
)
def create_collection(
    name: str,
    parent_collection_key: Optional[str] = None,
    *,
    ctx: Context
) -> str:
    """
    Create a new collection in your Zotero library.

    Args:
        name: Name of the new collection
        parent_collection_key: Optional parent collection key to nest this collection under
        ctx: MCP context

    Returns:
        Success message with the new collection's key
    """
    try:
        if not name.strip():
            return "Error: Collection name cannot be empty"

        ctx.info(f"Creating collection '{name}'")
        zot = get_zotero_client()

        # Build the collection payload
        payload = [{
            "name": name,
            "parentCollection": parent_collection_key if parent_collection_key else False
        }]

        # Create the collection
        result = zot.create_collections(payload)

        if result and "successful" in result and result["successful"]:
            new_key = result["successful"]["0"]["key"]
            parent_msg = f" under parent {parent_collection_key}" if parent_collection_key else ""
            return f"✓ Collection '{name}' created successfully{parent_msg}\nCollection Key: {new_key}"
        else:
            return f"Failed to create collection '{name}'. Result: {result}"

    except Exception as e:
        ctx.error(f"Error creating collection: {str(e)}")
        return f"Error creating collection: {str(e)}"


@mcp.tool(
    name="zot_add_to_collection",
    description="📊 MEDIUM PRIORITY - 🔸 SECONDARY - Add one or more items to a collection.\n\nUse for: Batch adding multiple paper keys to an existing collection"
,
    annotations={
        "readOnlyHint": True,
        "title": "Add to Collection (Zotero)"
    }
)
def add_to_collection(
    collection_key: str,
    item_keys: List[str],
    *,
    ctx: Context
) -> str:
    """
    Add one or more items to a collection.

    Args:
        collection_key: The collection key/ID to add items to
        item_keys: List of item keys to add to the collection
        ctx: MCP context

    Returns:
        Success message
    """
    try:
        if not item_keys:
            return "Error: Must provide at least one item key"

        if not collection_key.strip():
            return "Error: Collection key cannot be empty"

        ctx.info(f"Adding {len(item_keys)} items to collection {collection_key}")
        zot = get_zotero_client()

        # Get collection name for confirmation message
        try:
            collection = zot.collection(collection_key)
            collection_name = collection["data"].get("name", f"Collection {collection_key}")
        except Exception:
            collection_name = f"Collection {collection_key}"

        # Add items to collection
        # pyzotero expects item keys as a list
        result = zot.addto_collection(collection_key, item_keys)

        # Check if successful
        if result:
            items_str = f"{len(item_keys)} item(s)" if len(item_keys) > 1 else "item"
            return f"✓ Successfully added {items_str} to collection '{collection_name}'\nCollection Key: {collection_key}"
        else:
            return f"Failed to add items to collection '{collection_name}'"

    except Exception as e:
        ctx.error(f"Error adding items to collection: {str(e)}")
        return f"Error adding items to collection: {str(e)}"


@mcp.tool(
    name="zot_remove_from_collection",
    description="🔧 LOW PRIORITY - ⚪ FALLBACK - Remove one or more items from a collection.\n\nUse for: Batch removing papers from a collection without deleting them"
,
    annotations={
        "readOnlyHint": True,
        "title": "Remove from Collection (Zotero)"
    }
)
def remove_from_collection(
    collection_key: str,
    item_keys: List[str],
    *,
    ctx: Context
) -> str:
    """
    Remove one or more items from a collection.

    Args:
        collection_key: The collection key/ID to remove items from
        item_keys: List of item keys to remove from the collection
        ctx: MCP context

    Returns:
        Success message
    """
    try:
        if not item_keys:
            return "Error: Must provide at least one item key"

        if not collection_key.strip():
            return "Error: Collection key cannot be empty"

        ctx.info(f"Removing {len(item_keys)} items from collection {collection_key}")
        zot = get_zotero_client()

        # Get collection name for confirmation message
        try:
            collection = zot.collection(collection_key)
            collection_name = collection["data"].get("name", f"Collection {collection_key}")
        except Exception:
            collection_name = f"Collection {collection_key}"

        # Remove items from collection
        result = zot.deletefrom_collection(collection_key, item_keys)

        # Check if successful
        if result:
            items_str = f"{len(item_keys)} item(s)" if len(item_keys) > 1 else "item"
            return f"✓ Successfully removed {items_str} from collection '{collection_name}'\nCollection Key: {collection_key}"
        else:
            return f"Failed to remove items from collection '{collection_name}'"

    except Exception as e:
        ctx.error(f"Error removing items from collection: {str(e)}")
        return f"Error removing items from collection: {str(e)}"


# DEPRECATED - Use zot_get_item(include_children=True) instead
# @mcp.tool(
#     name="zot_get_item_children",
#     description="⚠️ DEPRECATED: Use zot_get_item(include_children=True) instead for unified retrieval.\n\nGet all child items (attachments, notes) for a specific Zotero item.\n\nUse for: Listing attachments, notes, and related items for a parent item",
#     annotations={
#         "readOnlyHint": True,
#         "title": "Get Item Children (Deprecated)"
#     }
# )


@mcp.tool(
    name="zot_get_item",
    description="""🔥 HIGH PRIORITY - 🔵 PRIMARY - Get bibliographic metadata for a Zotero item (title, authors, journal, abstract, DOI, etc.) plus list of child items (attachments, notes).

⚠️ For paper CONTENT analysis, use zot_ask_paper instead (more efficient, targeted chunk retrieval).
⚠️ For raw full PDF text, use zot_get_item_fulltext (expensive operation, 10k-100k tokens).

Returns:
- Bibliographic metadata (title, authors, year, journal, DOI)
- Abstract (if available)
- List of child items (attachments, notes)
- Tags, collections

~500-800 tokens, fast.

Use for: Bibliographic information, citations, checking what attachments exist""",
    annotations={
        "readOnlyHint": True,
        "title": "Get Item (Zotero)"
    }
)
def get_item(
    item_key: str,
    include_children: bool = True,
    include_abstract: bool = True,
    format: str = "markdown",
    *,
    ctx: Context
) -> str:
    """
    Get bibliographic metadata for a Zotero item.

    Args:
        item_key: Zotero item key/ID
        include_children: Whether to include child items like attachments and notes (default: True)
        include_abstract: Whether to include abstract in metadata (default: True)
        format: Output format - "markdown" or "bibtex" (default: "markdown")
        ctx: MCP context

    Returns:
        Comprehensive item metadata with child items list
    """
    try:
        # Validate format parameter
        if format not in ["markdown", "bibtex"]:
            return f"Error: Invalid format '{format}'. Must be 'markdown' or 'bibtex'"

        ctx.info(f"Fetching complete item data for {item_key}")
        zot = get_zotero_client()

        # Get the main item
        item = get_item_with_fallback(zot, item_key)
        if not item:
            return f"No item found with key: {item_key}"

        # For BibTeX format, just return BibTeX (no other sections)
        if format == "bibtex":
            return generate_bibtex(item)

        # Build comprehensive markdown output
        output_parts = []

        # 1. Metadata section
        metadata = format_item_metadata(item, include_abstract)
        output_parts.append(metadata)

        # 2. Children section (if requested)
        if include_children:
            try:
                children = zot.children(item_key)
                if children:
                    output_parts.append("\n---\n\n## Attachments & Notes")

                    # Group children by type
                    attachments = [c for c in children if c.get("data", {}).get("itemType") == "attachment"]
                    notes = [c for c in children if c.get("data", {}).get("itemType") == "note"]

                    # Format attachments
                    if attachments:
                        output_parts.append("\n### Attachments")
                        for i, att in enumerate(attachments, 1):
                            data = att.get("data", {})
                            title = data.get("title", "Untitled")
                            key = att.get("key", "")
                            content_type = data.get("contentType", "Unknown")
                            filename = data.get("filename", "")

                            output_parts.append(f"\n{i}. **{title}**")
                            output_parts.append(f"   - Key: {key}")
                            output_parts.append(f"   - Type: {content_type}")
                            if filename:
                                output_parts.append(f"   - Filename: {filename}")

                    # Format notes
                    if notes:
                        output_parts.append("\n### Notes")
                        for i, note in enumerate(notes, 1):
                            data = note.get("data", {})
                            key = note.get("key", "")
                            note_text = data.get("note", "")

                            # Clean up HTML in notes
                            note_text = note_text.replace("<p>", "").replace("</p>", "\n\n")
                            note_text = note_text.replace("<br/>", "\n").replace("<br>", "\n")

                            # Limit note length for display
                            if len(note_text) > 500:
                                note_text = note_text[:500] + "...\n\n(Note truncated)"

                            output_parts.append(f"\n{i}. Note (Key: {key})")
                            output_parts.append(f"```\n{note_text}\n```")
            except Exception as children_error:
                ctx.info(f"Could not fetch children: {str(children_error)}")

        return "\n".join(output_parts)

    except Exception as e:
        ctx.error(f"Error fetching item: {str(e)}")
        return f"Error fetching item: {str(e)}"


@mcp.tool(
    name="zot_get_item_fulltext",
    description="""🔧 LOW PRIORITY - ⚪ FALLBACK - ⚠️ EXPENSIVE FALLBACK (10,000-100,000 tokens) - Get complete raw PDF text from a Zotero item.

💡 Try these MORE EFFICIENT options FIRST:
- zot_ask_paper(item_key, question) → Retrieves relevant text chunks for Q&A (recommended)
- zot_semantic_search(query) → Find papers by content/topic
- zot_get_item(item_key) → Get metadata only

✅ Use this ONLY when you need:
- Comprehensive full-paper summarization (entire document context)
- Semantic search failed but you know paper is relevant
- Non-semantic tasks (word count, extract all references, find all equations)
- Complete text export for external processing
- Absoluteness > relevance (need ALL methodology, not excerpts)

⚠️ WARNING: Returns 10k-100k tokens. Cost is 20-200x higher than zot_get_item.

Returns:
- All metadata (same as zot_get_item)
- Complete extracted PDF text
- Processing may take 10-30 seconds

Use for: Complete text retrieval when targeted tools insufficient""",
    annotations={
        "readOnlyHint": True,
        "title": "Get Item Full Text (Zotero)"
    }
)
def get_item_fulltext(
    item_key: str,
    *,
    ctx: Context
) -> str:
    """
    Get the full text content of a Zotero item.

    WARNING: This is an expensive operation that can return 10k-100k tokens.
    Consider using zot_ask_paper for targeted content retrieval instead.

    Args:
        item_key: Zotero item key/ID
        ctx: MCP context

    Returns:
        Markdown-formatted item metadata + complete full text
    """
    try:
        ctx.info(f"Fetching full text for item {item_key} (this may take a while)")
        zot = get_zotero_client()

        # First get the item metadata
        item = get_item_with_fallback(zot, item_key)
        if not item:
            return f"No item found with key: {item_key}"

        # Get item metadata in markdown format
        metadata = format_item_metadata(item, include_abstract=True)

        # Try to get attachment details
        attachment = get_attachment_details(zot, item)
        if not attachment:
            return f"{metadata}\n\n---\n\n⚠️ No suitable PDF attachment found for this item.\n\n💡 Suggestion: Use zot_get_item to verify attachments exist."

        ctx.info(f"Found attachment: {attachment.key} ({attachment.content_type})")

        # Try fetching full text from Zotero's full text index first
        try:
            full_text_data = zot.fulltext_item(attachment.key)
            if full_text_data and "content" in full_text_data and full_text_data["content"]:
                ctx.info("Successfully retrieved full text from Zotero's index")
                return f"{metadata}\n\n---\n\n## Full Text\n\n{full_text_data['content']}"
        except Exception as fulltext_error:
            ctx.info(f"Zotero index unavailable, will parse PDF: {str(fulltext_error)}")

        # Fallback: Download and parse PDF
        ctx.info(f"Downloading and parsing PDF for {attachment.key}...")

        # Download the file to a temporary location
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, attachment.filename or f"{attachment.key}.pdf")
            zot.dump(attachment.key, filename=os.path.basename(file_path), path=tmpdir)

            if os.path.exists(file_path):
                # Extract text from PDF using convert_to_markdown
                ctx.info(f"Extracting text from PDF...")
                converted_text = convert_to_markdown(file_path)

                if converted_text:
                    ctx.info(f"Successfully extracted text from PDF")
                    return f"{metadata}\n\n---\n\n## Full Text (Extracted from PDF)\n\n{converted_text}"
                else:
                    return f"{metadata}\n\n---\n\n⚠️ Could not extract text from PDF. File may be scanned/image-based.\n\n💡 Suggestion: Try zot_ask_paper if this paper was indexed successfully."

    except Exception as e:
        import traceback
        ctx.error(f"Error fetching full text: {str(e)}")
        ctx.error(f"Traceback: {traceback.format_exc()}")
        return f"Error fetching full text: {str(e)}\n\n💡 Suggestion: Use zot_ask_paper or zot_semantic_search instead."


@mcp.tool(
    name="zot_get_tags",
    description="📊 MEDIUM PRIORITY - 🔸 SECONDARY - Get all tags used in your Zotero library.\n\nUse for: Exploring tag vocabulary and frequency across library"
,
    annotations={
        "readOnlyHint": True,
        "title": "Get Tags (Zotero)"
    }
)
def get_tags(
    limit: Optional[int] = None,
    *,
    ctx: Context
) -> str:
    """
    Get all tags used in your Zotero library.
    
    Args:
        limit: Maximum number of tags to return
        ctx: MCP context
    
    Returns:
        Markdown-formatted list of tags
    """
    try:
        ctx.info("Fetching tags")
        zot = get_zotero_client()
        
        
        tags = zot.tags(limit=limit)
        if not tags:
            return "No tags found in your Zotero library."
        
        # Format tags as markdown
        output = ["# Zotero Tags", ""]
        
        # Sort tags alphabetically
        sorted_tags = sorted(tags)
        
        # Group tags alphabetically
        current_letter = None
        for tag in sorted_tags:
            first_letter = tag[0].upper() if (tag and len(tag) > 0) else "#"
            
            if first_letter != current_letter:
                current_letter = first_letter
                output.append(f"## {current_letter}")
            
            output.append(f"- `{tag}`")
        
        return "\n".join(output)
    
    except Exception as e:
        ctx.error(f"Error fetching tags: {str(e)}")
        return f"Error fetching tags: {str(e)}"


@mcp.tool(
    name="zot_get_recent",
    description="📊 MEDIUM PRIORITY - ⚪ FALLBACK - Get recently added/modified items from Zotero API by timestamp.\n\n⚠️ For semantic queries about recent research on a topic, use zot_find_recent_developments instead.\n\nUse for: Chronologically listing items you recently added to your library (not topic-specific)",
    annotations={
        "readOnlyHint": True,
        "title": "Get Recent Items (Zotero)"
    }
)
def get_recent(
    limit: int = 10,
    *,
    ctx: Context
) -> str:
    """
    Get recently added items to your Zotero library.
    
    Args:
        limit: Number of items to return
        ctx: MCP context
    
    Returns:
        Markdown-formatted list of recent items
    """
    try:
        ctx.info(f"Fetching {limit} recent items")
        zot = get_zotero_client()
        
        
        # Ensure limit is a reasonable number
        if limit <= 0:
            limit = 10
        elif limit > 100:
            limit = 100
        
        # Get recent items
        items = zot.items(limit=limit, sort="dateAdded", direction="desc")
        if not items:
            return "No items found in your Zotero library."
        
        # Format items as markdown
        output = [f"# {limit} Most Recently Added Items", ""]
        
        for i, item in enumerate(items, 1):
            data = item.get("data", {})
            title = data.get("title", "Untitled")
            item_type = data.get("itemType", "unknown")
            date = data.get("date", "No date")
            key = item.get("key", "")
            date_added = data.get("dateAdded", "Unknown")
            
            # Format creators
            creators = data.get("creators", [])
            creators_str = format_creators(creators)
            
            # Build the formatted entry
            output.append(f"## {i}. {title}")
            output.append(f"**Type:** {item_type}")
            output.append(f"**Item Key:** {key}")
            output.append(f"**Date:** {date}")
            output.append(f"**Added:** {date_added}")
            output.append(f"**Authors:** {creators_str}")
            
            output.append("")  # Empty line between items
        
        return "\n".join(output)
    
    except Exception as e:
        ctx.error(f"Error fetching recent items: {str(e)}")
        return f"Error fetching recent items: {str(e)}"


@mcp.tool(
    name="zot_batch_update_tags",
    description="📊 MEDIUM PRIORITY - 🔸 SECONDARY - Batch update tags across multiple items matching a search query.\n\nUse for: Adding/removing tags across multiple items efficiently"
,
    annotations={
        "readOnlyHint": True,
        "title": "Batch Update Tags (Zotero)"
    }
)
def batch_update_tags(
    query: str,
    add_tags: Optional[str] = None,
    remove_tags: Optional[str] = None,
    limit: int = 50,
    *,
    ctx: Context
) -> str:
    """
    Batch update tags across multiple items matching a search query.
    
    Args:
        query: Search query to find items to update
        add_tags: List of tags to add to matched items (can be list or JSON string)
        remove_tags: List of tags to remove from matched items (can be list or JSON string)
        limit: Maximum number of items to process
        ctx: MCP context
    
    Returns:
        Summary of the batch update
    """
    try:
        if not query:
            return "Error: Search query cannot be empty"
        
        if not add_tags and not remove_tags:
            return "Error: You must specify either tags to add or tags to remove"
        
        # Debug logging... commented out for now but could be useful in future.
        # ctx.info(f"add_tags type: {type(add_tags)}, value: {add_tags}")
        # ctx.info(f"remove_tags type: {type(remove_tags)}, value: {remove_tags}")
        
        # Handle case where add_tags might be a JSON string instead of list
        if add_tags and isinstance(add_tags, str):
            try:
                import json
                add_tags = json.loads(add_tags)
                ctx.info(f"Parsed add_tags from JSON string: {add_tags}")
            except json.JSONDecodeError:
                return f"Error: add_tags appears to be malformed JSON string: {add_tags}"
        
        # Handle case where remove_tags might be a JSON string instead of list  
        if remove_tags and isinstance(remove_tags, str):
            try:
                import json
                remove_tags = json.loads(remove_tags)
                ctx.info(f"Parsed remove_tags from JSON string: {remove_tags}")
            except json.JSONDecodeError:
                return f"Error: remove_tags appears to be malformed JSON string: {remove_tags}"
        
        ctx.info(f"Batch updating tags for items matching '{query}'")
        zot = get_zotero_client()
        
        
        # Search for items matching the query
        zot.add_parameters(q=query, limit=limit)
        items = zot.items()
        
        if not items:
            return f"No items found matching query: '{query}'"
        
        # Initialize counters
        updated_count = 0
        skipped_count = 0
        added_tag_counts = {tag: 0 for tag in (add_tags or [])}
        removed_tag_counts = {tag: 0 for tag in (remove_tags or [])}
        
        # Process each item
        for item in items:
            # Skip attachments if they were included in the results
            if item["data"].get("itemType") == "attachment":
                skipped_count += 1
                continue
                
            # Get current tags
            current_tags = item["data"].get("tags", [])
            current_tag_values = {t["tag"] for t in current_tags}
            
            # Track if this item needs to be updated
            needs_update = False
            
            # Process tags to remove
            if remove_tags:
                new_tags = []
                for tag_obj in current_tags:
                    tag = tag_obj["tag"]
                    if tag in remove_tags:
                        removed_tag_counts[tag] += 1
                        needs_update = True
                    else:
                        new_tags.append(tag_obj)
                current_tags = new_tags
            
            # Process tags to add
            if add_tags:
                for tag in add_tags:
                    if tag and tag not in current_tag_values:
                        current_tags.append({"tag": tag})
                        added_tag_counts[tag] += 1
                        needs_update = True
            
            # Update the item if needed
            # Since we are logging errors we might as well log the update.
            if needs_update:
                try:
                    item["data"]["tags"] = current_tags
                    ctx.info(f"Updating item {item.get('key', 'unknown')} with tags: {current_tags}")
                    result = zot.update_item(item)
                    ctx.info(f"Update result: {result}")
                    updated_count += 1
                except Exception as e:
                    ctx.error(f"Failed to update item {item.get('key', 'unknown')}: {str(e)}")
                    # Continue with other items instead of failing completely
                    skipped_count += 1
            else:
                skipped_count += 1
        
        # Format the response
        response = ["# Batch Tag Update Results", ""]
        response.append(f"Query: '{query}'")
        response.append(f"Items processed: {len(items)}")
        response.append(f"Items updated: {updated_count}")
        response.append(f"Items skipped: {skipped_count}")
        
        if add_tags:
            response.append("\n## Tags Added")
            for tag, count in added_tag_counts.items():
                response.append(f"- `{tag}`: {count} items")
        
        if remove_tags:
            response.append("\n## Tags Removed")
            for tag, count in removed_tag_counts.items():
                response.append(f"- `{tag}`: {count} items")
        
        return "\n".join(response)
    
    except Exception as e:
        ctx.error(f"Error in batch tag update: {str(e)}")
        return f"Error in batch tag update: {str(e)}"


@mcp.tool(
    name="zot_get_annotations",
    description="📊 MEDIUM PRIORITY - 🔸 SECONDARY - Get all annotations for a specific item or across your entire Zotero library.\n\nUse for: Retrieving highlights and comments from PDF annotations"
,
    annotations={
        "readOnlyHint": True,
        "title": "Get Annotations (Zotero)"
    }
)
def get_annotations(
    item_key: Optional[str] = None,
    use_pdf_extraction: bool = False,
    limit: Optional[int] = None,
    *,
    ctx: Context
) -> str:
    """
    Get annotations from your Zotero library.
    
    Args:
        item_key: Optional Zotero item key/ID to filter annotations by parent item
        use_pdf_extraction: Whether to attempt direct PDF extraction as a fallback
        limit: Maximum number of annotations to return
        ctx: MCP context
    
    Returns:
        Markdown-formatted list of annotations
    """
    try:
        # Initialize Zotero client
        zot = get_zotero_client()
        
        # Prepare annotations list
        annotations = []
        parent_title = "Untitled Item"
        
        # If an item key is provided, use specialized retrieval
        if item_key:
            # First, verify the item exists and get its details
            try:
                parent = get_item_with_fallback(zot, item_key)
                parent_title = parent["data"].get("title", "Untitled Item")
                ctx.info(f"Fetching annotations for item: {parent_title}")
            except Exception:
                return f"Error: No item found with key: {item_key}"
            
            # Initialize annotation sources
            better_bibtex_annotations = []
            zotero_api_annotations = []
            pdf_annotations = []
            
            # Try Better BibTeX method (local Zotero only)
            if os.environ.get("ZOTERO_LOCAL", "").lower() in ["true", "yes", "1"]:
                try:
                    # Import Better BibTeX dependencies
                    from agent_zot.clients.better_bibtex import (
                        ZoteroBetterBibTexAPI, 
                        process_annotation, 
                        get_color_category
                    )
                    
                    # Initialize Better BibTeX client
                    bibtex = ZoteroBetterBibTexAPI()
                    
                    # Check if Zotero with Better BibTeX is running
                    if bibtex.is_zotero_running():
                        # Extract citation key
                        citation_key = None
                        
                        # Try to find citation key in Extra field
                        try:
                            extra_field = parent["data"].get("extra", "")
                            for line in extra_field.split("\n"):
                                if line.lower().startswith("citation key:"):
                                    citation_key = line.replace("Citation Key:", "").strip()
                                    break
                                elif line.lower().startswith("citationkey:"):
                                    citation_key = line.replace("citationkey:", "").strip()
                                    break
                        except Exception as e:
                            ctx.warn(f"Error extracting citation key from Extra field: {e}")
                        
                        # Fallback to searching by title if no citation key found
                        if not citation_key:
                            title = parent["data"].get("title", "")
                            try:
                                if title:
                                    # Use the search_citekeys method
                                    search_results = bibtex.search_citekeys(title)
                                    
                                    # Find the matching item
                                    for result in search_results:
                                        ctx.info(f"Checking result: {result}")
                                        
                                        # Try to match with item key if possible
                                        if result.get('citekey'):
                                            citation_key = result['citekey']
                                            break
                            except Exception as e:
                                ctx.warn(f"Error searching for citation key: {e}")
                        
                        # Process annotations if citation key found
                        if citation_key:
                            try:
                                # Determine library ID
                                library_id = 1  # Default to personal library
                                search_results = bibtex._make_request("item.search", [citation_key])
                                if search_results and isinstance(search_results, list):
                                    matched_item = next((item for item in search_results if item.get('citekey') == citation_key), None)
                                    if matched_item:
                                        library_id = matched_item.get('libraryID', 1)
                                
                                # Get attachments
                                attachments = bibtex.get_attachments(citation_key, library_id)
                                
                                # Process annotations from attachments
                                for attachment in attachments:
                                    annotations = bibtex.get_annotations_from_attachment(attachment)
                                    
                                    for anno in annotations:
                                        processed = process_annotation(anno, attachment)
                                        if processed:
                                            # Create Zotero-like annotation object
                                            bibtex_anno = {
                                                "key": processed.get("id", ""),
                                                "data": {
                                                    "itemType": "annotation",
                                                    "annotationType": processed.get("type", "highlight"),
                                                    "annotationText": processed.get("annotatedText", ""),
                                                    "annotationComment": processed.get("comment", ""),
                                                    "annotationColor": processed.get("color", ""),
                                                    "parentItem": item_key,
                                                    "tags": [],
                                                    "_pdf_page": processed.get("page", 0),
                                                    "_pageLabel": processed.get("pageLabel", ""),
                                                    "_attachment_title": attachment.get("title", ""),
                                                    "_color_category": get_color_category(processed.get("color", "")),
                                                    "_from_better_bibtex": True
                                                }
                                            }
                                            better_bibtex_annotations.append(bibtex_anno)
                                
                                ctx.info(f"Retrieved {len(better_bibtex_annotations)} annotations via Better BibTeX")
                            except Exception as e:
                                ctx.warn(f"Error processing Better BibTeX annotations: {e}")
                except Exception as bibtex_error:
                    ctx.warn(f"Error initializing Better BibTeX: {bibtex_error}")
            
            # Fallback to Zotero API annotations
            if not better_bibtex_annotations:
                try:
                    # Get child annotations via Zotero API
                    children = zot.children(item_key)
                    zotero_api_annotations = [
                        item for item in children 
                        if item.get("data", {}).get("itemType") == "annotation"
                    ]
                    ctx.info(f"Retrieved {len(zotero_api_annotations)} annotations via Zotero API")
                except Exception as api_error:
                    ctx.warn(f"Error retrieving Zotero API annotations: {api_error}")
            
            # PDF Extraction fallback
            if use_pdf_extraction and not (better_bibtex_annotations or zotero_api_annotations):
                try:
                    from pdfannots_helper import extract_annotations_from_pdf, ensure_pdfannots_installed
                    import tempfile
                    import uuid
                    
                    # Ensure PDF annotation tool is installed
                    if ensure_pdfannots_installed():
                        # Get PDF attachments
                        children = zot.children(item_key)
                        pdf_attachments = [
                            item for item in children 
                            if item.get("data", {}).get("contentType") == "application/pdf"
                        ]
                        
                        # Extract annotations from PDFs
                        for attachment in pdf_attachments:
                            with tempfile.TemporaryDirectory() as tmpdir:
                                att_key = attachment.get("key", "")
                                file_path = os.path.join(tmpdir, f"{att_key}.pdf")
                                zot.dump(att_key, file_path)
                                
                                if os.path.exists(file_path):
                                    extracted = extract_annotations_from_pdf(file_path, tmpdir)
                                    
                                    for ext in extracted:
                                        # Skip empty annotations
                                        if not ext.get("annotatedText") and not ext.get("comment"):
                                            continue
                                        
                                        # Create Zotero-like annotation object
                                        pdf_anno = {
                                            "key": f"pdf_{att_key}_{ext.get('id', uuid.uuid4().hex[:8])}",
                                            "data": {
                                                "itemType": "annotation",
                                                "annotationType": ext.get("type", "highlight"),
                                                "annotationText": ext.get("annotatedText", ""),
                                                "annotationComment": ext.get("comment", ""),
                                                "annotationColor": ext.get("color", ""),
                                                "parentItem": item_key,
                                                "tags": [],
                                                "_pdf_page": ext.get("page", 0),
                                                "_from_pdf_extraction": True,
                                                "_attachment_title": attachment.get("data", {}).get("title", "PDF")
                                            }
                                        }
                                        
                                        # Handle image annotations
                                        if ext.get("type") == "image" and ext.get("imageRelativePath"):
                                            pdf_anno["data"]["_image_path"] = os.path.join(tmpdir, ext.get("imageRelativePath"))
                                        
                                        pdf_annotations.append(pdf_anno)
                        
                        ctx.info(f"Retrieved {len(pdf_annotations)} annotations via PDF extraction")
                except Exception as pdf_error:
                    ctx.warn(f"Error during PDF annotation extraction: {pdf_error}")
            
            # Combine annotations from all sources
            annotations = better_bibtex_annotations + zotero_api_annotations + pdf_annotations
        
        else:
            # Retrieve all annotations in the library
            zot.add_parameters(itemType="annotation", limit=limit or 50)
            annotations = zot.everything(zot.items())
        
        # Handle no annotations found
        if not annotations:
            return f"No annotations found{f' for item: {parent_title}' if item_key else ''}."
        
        # Generate markdown output
        output = [f"# Annotations{f' for: {parent_title}' if item_key else ''}", ""]
        
        for i, anno in enumerate(annotations, 1):
            data = anno.get("data", {})
            
            # Annotation details
            anno_type = data.get("annotationType", "Unknown type")
            anno_text = data.get("annotationText", "")
            anno_comment = data.get("annotationComment", "")
            anno_color = data.get("annotationColor", "")
            anno_key = anno.get("key", "")
            
            # Parent item context for library-wide retrieval
            parent_info = ""
            if not item_key and (parent_key := data.get("parentItem")):
                try:
                    parent = get_item_with_fallback(zot, parent_key)
                    parent_title = parent["data"].get("title", "Untitled")
                    parent_info = f" (from \"{parent_title}\")"
                except Exception:
                    parent_info = f" (parent key: {parent_key})"
            
            # Annotation source details
            source_info = ""
            if data.get("_from_better_bibtex", False):
                source_info = " (extracted via Better BibTeX)"
            elif data.get("_from_pdf_extraction", False):
                source_info = " (extracted directly from PDF)"
            
            # Attachment context
            attachment_info = ""
            if "_attachment_title" in data and data["_attachment_title"]:
                attachment_info = f" in {data['_attachment_title']}"
            
            # Build markdown annotation entry
            output.append(f"## Annotation {i}{parent_info}{attachment_info}{source_info}")
            output.append(f"**Type:** {anno_type}")
            output.append(f"**Key:** {anno_key}")
            
            # Color information
            if anno_color:
                output.append(f"**Color:** {anno_color}")
                if "_color_category" in data and data["_color_category"]:
                    output.append(f"**Color Category:** {data['_color_category']}")
            
            # Page information
            if "_pdf_page" in data:
                label = data.get("_pageLabel", str(data["_pdf_page"]))
                output.append(f"**Page:** {data['_pdf_page']} (Label: {label})")
            
            # Annotation content
            if anno_text:
                output.append(f"**Text:** {anno_text}")
            
            if anno_comment:
                output.append(f"**Comment:** {anno_comment}")
            
            # Image annotation
            if "_image_path" in data and os.path.exists(data["_image_path"]):
                output.append("**Image:** This annotation includes an image (not displayed in this interface)")
            
            # Tags
            if tags := data.get("tags"):
                tag_list = [f"`{tag['tag']}`" for tag in tags]
                if tag_list:
                    output.append(f"**Tags:** {' '.join(tag_list)}")
            
            output.append("")  # Empty line between annotations
        
        return "\n".join(output)
    
    except Exception as e:
        ctx.error(f"Error fetching annotations: {str(e)}")
        return f"Error fetching annotations: {str(e)}"


@mcp.tool(
    name="zot_get_notes",
    description="📊 MEDIUM PRIORITY - 🔸 SECONDARY - Retrieve notes from your Zotero library, with options to filter by parent item.\n\nUse for: Fetching standalone notes or notes attached to items"
,
    annotations={
        "readOnlyHint": True,
        "title": "Get Notes (Zotero)"
    }
)
def get_notes(
    item_key: Optional[str] = None,
    limit: Optional[int] = 20,
    *,
    ctx: Context
) -> str:
    """
    Retrieve notes from your Zotero library.
    
    Args:
        item_key: Optional Zotero item key/ID to filter notes by parent item
        limit: Maximum number of notes to return
        ctx: MCP context
    
    Returns:
        Markdown-formatted list of notes
    """
    try:
        ctx.info(f"Fetching notes{f' for item {item_key}' if item_key else ''}")
        zot = get_zotero_client()
        
        # Prepare search parameters
        params = {"itemType": "note"}
        if item_key:
            params["parentItem"] = item_key
        
        
        # Get notes
        notes = zot.items(**params) if not limit else zot.items(limit=limit, **params)
        
        if not notes:
            return f"No notes found{f' for item {item_key}' if item_key else ''}."
        
        # Generate markdown output
        output = [f"# Notes{f' for Item: {item_key}' if item_key else ''}", ""]
        
        for i, note in enumerate(notes, 1):
            data = note.get("data", {})
            note_key = note.get("key", "")
            
            # Parent item context
            parent_info = ""
            if parent_key := data.get("parentItem"):
                try:
                    parent = get_item_with_fallback(zot, parent_key)
                    parent_title = parent["data"].get("title", "Untitled")
                    parent_info = f" (from \"{parent_title}\")"
                except Exception:
                    parent_info = f" (parent key: {parent_key})"
            
            # Prepare note text
            note_text = data.get("note", "")
            
            # Clean up HTML formatting
            note_text = note_text.replace("<p>", "").replace("</p>", "\n\n")
            note_text = note_text.replace("<br/>", "\n").replace("<br>", "\n")
            
            # Limit note length for display
            if len(note_text) > 500:
                note_text = note_text[:500] + "..."
            
            # Build markdown entry
            output.append(f"## Note {i}{parent_info}")
            output.append(f"**Key:** {note_key}")
            
            # Tags
            if tags := data.get("tags"):
                tag_list = [f"`{tag['tag']}`" for tag in tags]
                if tag_list:
                    output.append(f"**Tags:** {' '.join(tag_list)}")
            
            output.append(f"**Content:**\n{note_text}")
            output.append("")  # Empty line between notes
        
        return "\n".join(output)
    
    except Exception as e:
        ctx.error(f"Error fetching notes: {str(e)}")
        return f"Error fetching notes: {str(e)}"


@mcp.tool(
    name="zot_search_notes",
    description="📊 MEDIUM PRIORITY - 🔸 SECONDARY - Search for notes across your Zotero library.\n\nUse for: Finding notes by text content across library"
,
    annotations={
        "readOnlyHint": True,
        "title": "Search Notes (Zotero)"
    }
)
def search_notes(
    query: str,
    limit: Optional[int] = 20,
    *,
    ctx: Context
) -> str:
    """
    Search for notes in your Zotero library.
    
    Args:
        query: Search query string
        limit: Maximum number of results to return
        ctx: MCP context
    
    Returns:
        Markdown-formatted search results
    """
    try:
        if not query.strip():
            return "Error: Search query cannot be empty"
        
        ctx.info(f"Searching Zotero notes for '{query}'")
        zot = get_zotero_client()
        
        # Search for notes and annotations
        
        
        # First search notes
        zot.add_parameters(q=query, itemType="note", limit=limit or 20)
        notes = zot.items()
        
        # Then search annotations (reusing the get_annotations function)
        annotation_results = get_annotations(
            item_key=None,  # Search all annotations
            use_pdf_extraction=True,
            limit=limit or 20,
            ctx=ctx
        )
        
        # Parse the annotation results to extract annotation items
        # This is a bit hacky and depends on the exact formatting of get_annotations
        # You might want to modify get_annotations to return a more structured result
        annotation_lines = annotation_results.split("\n")
        current_annotation = None
        annotations = []
        
        for line in annotation_lines:
            if line.startswith("## "):
                if current_annotation:
                    annotations.append(current_annotation)
                current_annotation = {"lines": [line], "type": "annotation"}
            elif current_annotation is not None:
                current_annotation["lines"].append(line)
        
        if current_annotation:
            annotations.append(current_annotation)
        
        # Format results
        output = [f"# Search Results for '{query}'", ""]
        
        # Filter and highlight notes
        query_lower = query.lower()
        note_results = []
        
        for note in notes:
            data = note.get("data", {})
            note_text = data.get("note", "").lower()
            
            if query_lower in note_text:
                # Prepare full note details
                note_result = {
                    "type": "note",
                    "key": note.get("key", ""),
                    "data": data
                }
                note_results.append(note_result)
        
        # Combine and sort results
        all_results = note_results + annotations
        
        for i, result in enumerate(all_results, 1):
            if result["type"] == "note":
                # Note formatting
                data = result["data"]
                key = result["key"]
                
                # Parent item context
                parent_info = ""
                if parent_key := data.get("parentItem"):
                    try:
                        parent = get_item_with_fallback(zot, parent_key)
                        parent_title = parent["data"].get("title", "Untitled")
                        parent_info = f" (from \"{parent_title}\")"
                    except Exception:
                        parent_info = f" (parent key: {parent_key})"
                
                # Note text with query highlight
                note_text = data.get("note", "")
                note_text = note_text.replace("<p>", "").replace("</p>", "\n\n")
                note_text = note_text.replace("<br/>", "\n").replace("<br>", "\n")
                
                # Highlight query in note text
                try:
                    # Find first occurrence of query and extract context
                    text_lower = note_text.lower()
                    pos = text_lower.find(query_lower)
                    if pos >= 0:
                        # Extract context around the query
                        start = max(0, pos - 100)
                        end = min(len(note_text), pos + 200)
                        context = note_text[start:end]

                        # Highlight the query in the context - cache find() result to prevent -1 index
                        context_lower = context.lower()
                        query_pos = context_lower.find(query_lower)

                        if query_pos >= 0:
                            # Extract matched text (preserve original case)
                            matched_text = context[query_pos:query_pos+len(query)]
                            highlighted = context.replace(matched_text, f"**{matched_text}**", 1)
                            note_text = highlighted + "..."
                        else:
                            # Query not in context (shouldn't happen but be safe)
                            note_text = context + "..."
                except Exception:
                    # Fallback to first 500 characters if highlighting fails
                    note_text = note_text[:500] + "..."
                
                output.append(f"## Note {i}{parent_info}")
                output.append(f"**Key:** {key}")
                
                # Tags
                if tags := data.get("tags"):
                    tag_list = [f"`{tag['tag']}`" for tag in tags]
                    if tag_list:
                        output.append(f"**Tags:** {' '.join(tag_list)}")
                
                output.append(f"**Content:**\n{note_text}")
                output.append("")
            
            elif result["type"] == "annotation":
                # Add the entire annotation block
                output.extend(result["lines"])
                output.append("")
        
        return "\n".join(output) if output else f"No results found for '{query}'"
    
    except Exception as e:
        ctx.error(f"Error searching notes: {str(e)}")
        return f"Error searching notes: {str(e)}"


@mcp.tool(
    name="zot_create_note",
    description="📊 MEDIUM PRIORITY - 🔸 SECONDARY - Create a new note for a Zotero item.\n\nUse for: Adding research notes to items or library"
,
    annotations={
        "readOnlyHint": True,
        "title": "Create Note (Zotero)"
    }
)
def create_note(
    item_key: str,
    note_title: str,
    note_text: str,
    tags: Optional[List[str]] = None,
    *,
    ctx: Context
) -> str:
    """
    Create a new note for a Zotero item.
    
    Args:
        item_key: Zotero item key/ID to attach the note to
        note_title: Title for the note
        note_text: Content of the note (can include simple HTML formatting)
        tags: List of tags to apply to the note
        ctx: MCP context
    
    Returns:
        Confirmation message with the new note key
    """
    try:
        ctx.info(f"Creating note for item {item_key}")
        zot = get_zotero_client()
        
        # First verify the parent item exists
        try:
            parent = get_item_with_fallback(zot, item_key)
            parent_title = parent["data"].get("title", "Untitled Item")
        except Exception:
            return f"Error: No item found with key: {item_key}"
        
        # Format the note content with proper HTML
        # If the note_text already has HTML, use it directly
        if "<p>" in note_text or "<div>" in note_text:
            html_content = note_text
        else:
            # Convert plain text to HTML paragraphs - avoiding f-strings with replacements
            paragraphs = note_text.split("\n\n")
            html_parts = []
            for p in paragraphs:
                # Replace newlines with <br/> tags
                p_with_br = p.replace("\n", "<br/>")
                html_parts.append("<p>" + p_with_br + "</p>")
            html_content = "".join(html_parts)
        
        # Prepare the note data
        note_data = {
            "itemType": "note",
            "parentItem": item_key,
            "note": html_content,
            "tags": [{"tag": tag} for tag in (tags or [])]
        }
        
        # Create the note
        result = zot.create_items([note_data])
        
        # Check if creation was successful
        if "success" in result and result["success"]:
            successful = result["success"]
            if len(successful) > 0:
                note_key = next(iter(successful.keys()))
                return f"Successfully created note for \"{parent_title}\"\n\nNote key: {note_key}"
            else:
                return f"Note creation response was successful but no key was returned: {result}"
        else:
            return f"Failed to create note: {result.get('failed', 'Unknown error')}"
    
    except Exception as e:
        ctx.error(f"Error creating note: {str(e)}")
        return f"Error creating note: {str(e)}"



# ============================================================================
# EXPORT TOOLS - Data Export
# ============================================================================
@mcp.tool(
    name="zot_export_markdown",
    description="📊 MEDIUM PRIORITY - 🔸 SECONDARY - Export Zotero items to Markdown files with YAML frontmatter (Obsidian-compatible). Exports items matching a query or from a collection to a specified directory.\n\nUse for: Converting bibliographic data to markdown format for documentation",
    annotations={
        "readOnlyHint": True,
        "title": "Export to Markdown (Export)"
    }
)
def export_markdown(
    output_dir: str,
    query: str = None,
    collection_key: str = None,
    limit: int = 100,
    include_fulltext: bool = False,
    *,
    ctx: Context
) -> str:
    """
    Export Zotero items to Markdown files with YAML frontmatter.

    Args:
        output_dir: Directory to export markdown files to
        query: Search query to filter items (optional, uses zot_search_items)
        collection_key: Collection key to export from (optional)
        limit: Maximum number of items to export (default: 100)
        include_fulltext: Include full PDF text in markdown body (default: False)
        ctx: MCP context

    Returns:
        Summary of export operation
    """
    try:
        import os
        from pathlib import Path
        import re

        ctx.info(f"Exporting items to {output_dir}")

        # Create output directory if it doesn't exist
        output_path = Path(output_dir).expanduser()
        output_path.mkdir(parents=True, exist_ok=True)

        zot = get_zotero_client()

        # Fetch items based on query or collection
        if collection_key:
            ctx.info(f"Fetching items from collection: {collection_key}")
            items = zot.collection_items(collection_key, limit=limit)
        elif query:
            ctx.info(f"Searching for items with query: '{query}'")
            zot.add_parameters(q=query, limit=limit)
            items = zot.items()
        else:
            ctx.info(f"Fetching recent items (limit: {limit})")
            items = zot.items(limit=limit)

        if not items:
            return "No items found to export."

        # Export each item
        exported_count = 0
        skipped_count = 0
        errors = []

        for item in items:
            try:
                # Skip attachments and notes
                item_type = item["data"].get("itemType", "")
                if item_type in ["attachment", "note"]:
                    skipped_count += 1
                    continue

                item_key = item.get("key", "")
                data = item.get("data", {})

                # Build YAML frontmatter
                title = data.get("title", "Untitled")
                creators = data.get("creators", [])
                authors = [f"{c.get('firstName', '')} {c.get('lastName', '')}".strip()
                          for c in creators if c.get("creatorType") == "author"]

                tags = [t.get("tag", "") for t in data.get("tags", [])]

                yaml_frontmatter = ["---"]
                yaml_frontmatter.append(f"title: \"{title.replace('\"', '\\"')}\"")
                yaml_frontmatter.append(f"zotero_key: {item_key}")
                yaml_frontmatter.append(f"item_type: {item_type}")

                if authors:
                    yaml_frontmatter.append(f"authors:")
                    for author in authors:
                        yaml_frontmatter.append(f"  - {author}")

                if data.get("date"):
                    yaml_frontmatter.append(f"date: \"{data.get('date')}\"")

                if data.get("publicationTitle"):
                    yaml_frontmatter.append(f"publication: \"{data.get('publicationTitle').replace('\"', '\\"')}\"")

                if data.get("DOI"):
                    yaml_frontmatter.append(f"doi: {data.get('DOI')}")

                if data.get("url"):
                    yaml_frontmatter.append(f"url: {data.get('url')}")

                if tags:
                    yaml_frontmatter.append("tags:")
                    for tag in tags:
                        yaml_frontmatter.append(f"  - {tag}")

                yaml_frontmatter.append("---\n")

                # Build markdown body
                md_body = [f"# {title}\n"]

                if authors:
                    md_body.append(f"**Authors**: {', '.join(authors)}\n")

                if data.get("abstractNote"):
                    md_body.append("## Abstract\n")
                    md_body.append(f"{data.get('abstractNote')}\n")

                # Include full text if requested
                if include_fulltext:
                    try:
                        fulltext = get_item_fulltext(item_key=item_key, ctx=ctx)
                        if fulltext and "Full Text" in fulltext:
                            md_body.append("\n## Full Text\n")
                            # Extract just the full text section
                            text_start = fulltext.find("## Full Text")
                            if text_start >= 0:
                                md_body.append(fulltext[text_start + len("## Full Text"):].strip())
                    except Exception as e:
                        ctx.error(f"Failed to get fulltext for {item_key}: {e}")

                # Add notes if available
                if data.get("extra"):
                    md_body.append("\n## Notes\n")
                    md_body.append(f"{data.get('extra')}\n")

                # Generate safe filename from title
                safe_title = re.sub(r'[<>:"/\\|?*]', '', title)
                safe_title = safe_title[:100]  # Limit filename length
                filename = f"{item_key}_{safe_title}.md"

                # Write file
                output_file = output_path / filename
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write("\n".join(yaml_frontmatter))
                    f.write("\n")
                    f.write("\n".join(md_body))

                exported_count += 1
                ctx.info(f"Exported: {filename}")

            except Exception as e:
                errors.append(f"{item.get('key', 'unknown')}: {str(e)}")
                ctx.error(f"Error exporting item {item.get('key', 'unknown')}: {e}")

        # Format summary
        output = ["# Markdown Export Results\n"]
        output.append(f"**Output Directory**: `{output_path}`")
        output.append(f"**Items Exported**: {exported_count}")
        output.append(f"**Items Skipped**: {skipped_count}")

        if errors:
            output.append(f"\n## Errors ({len(errors)})\n")
            for error in errors[:10]:  # Show first 10 errors
                output.append(f"- {error}")
            if len(errors) > 10:
                output.append(f"- ... and {len(errors) - 10} more errors")

        return "\n".join(output)

    except Exception as e:
        ctx.error(f"Error during markdown export: {str(e)}")
        return f"Error during markdown export: {str(e)}"


@mcp.tool(
    name="zot_export_bibtex",
    description="📊 MEDIUM PRIORITY - 🔸 SECONDARY - Export Zotero items to BibTeX format. Can export items matching a query or from a collection to a .bib file.\n\nUse for: Generating BibTeX citations for LaTeX documents"
,
    annotations={
        "readOnlyHint": True,
        "title": "Export BibTeX (Export)"
    }
)
def export_bibtex(
    output_file: str,
    query: str = None,
    collection_key: str = None,
    limit: int = 1000,
    *,
    ctx: Context
) -> str:
    """
    Export Zotero items to BibTeX file.

    Args:
        output_file: Path to output .bib file
        query: Search query to filter items (optional)
        collection_key: Collection key to export from (optional)
        limit: Maximum number of items to export (default: 1000)
        ctx: MCP context

    Returns:
        Summary of export operation
    """
    try:
        from pathlib import Path

        ctx.info(f"Exporting items to BibTeX file: {output_file}")

        # Create output directory if needed
        output_path = Path(output_file).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        zot = get_zotero_client()

        # Fetch items based on query or collection
        if collection_key:
            ctx.info(f"Fetching items from collection: {collection_key}")
            items = zot.collection_items(collection_key, limit=limit)
        elif query:
            ctx.info(f"Searching for items with query: '{query}'")
            zot.add_parameters(q=query, limit=limit)
            items = zot.items()
        else:
            ctx.info(f"Fetching all items (limit: {limit})")
            items = zot.items(limit=limit)

        if not items:
            return "No items found to export."

        # Generate BibTeX for each item
        bibtex_entries = []
        exported_count = 0
        skipped_count = 0
        errors = []

        for item in items:
            try:
                # Skip attachments and notes
                item_type = item["data"].get("itemType", "")
                if item_type in ["attachment", "note"]:
                    skipped_count += 1
                    continue

                # Generate BibTeX using existing function
                bibtex_entry = generate_bibtex(item)
                if bibtex_entry and bibtex_entry.strip():
                    bibtex_entries.append(bibtex_entry)
                    exported_count += 1
                else:
                    skipped_count += 1
                    ctx.warning(f"Empty BibTeX for item {item.get('key', 'unknown')}")

            except Exception as e:
                errors.append(f"{item.get('key', 'unknown')}: {str(e)}")
                ctx.error(f"Error exporting item {item.get('key', 'unknown')}: {e}")
                skipped_count += 1

        # Write BibTeX file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n\n".join(bibtex_entries))

        # Format summary
        output = ["# BibTeX Export Results\n"]
        output.append(f"**Output File**: `{output_path}`")
        output.append(f"**Items Exported**: {exported_count}")
        output.append(f"**Items Skipped**: {skipped_count}")
        output.append(f"**File Size**: {output_path.stat().st_size:,} bytes")

        if errors:
            output.append(f"\n## Errors ({len(errors)})\n")
            for error in errors[:10]:
                output.append(f"- {error}")
            if len(errors) > 10:
                output.append(f"- ... and {len(errors) - 10} more errors")

        return "\n".join(output)

    except Exception as e:
        ctx.error(f"Error during BibTeX export: {str(e)}")
        return f"Error during BibTeX export: {str(e)}"


@mcp.tool(
    name="zot_export_graph",
    description="🔧 LOW PRIORITY - ⚪ FALLBACK - Export Neo4j knowledge graph to GraphML format for visualization in Gephi or Cytoscape. Requires Neo4j GraphRAG to be enabled.\n\nUse for: Exporting Neo4j graph data for external analysis"
,
    annotations={
        "readOnlyHint": True,
        "title": "Export Graph (Export)"
    }
)
def export_graph(
    output_file: str,
    node_types: List[str] = None,
    max_nodes: int = None,
    *,
    ctx: Context
) -> str:
    """
    Export knowledge graph to GraphML format.

    Args:
        output_file: Path to output .graphml file
        node_types: List of node types to include (e.g. ['Paper', 'Person', 'Concept']). Default: all types
        max_nodes: Maximum number of nodes to export (default: all nodes)
        ctx: MCP context

    Returns:
        Summary of export operation
    """
    try:
        from pathlib import Path
        from agent_zot.clients.neo4j_graphrag import create_neo4j_graphrag_client

        config_path = Path.home() / ".config" / "agent-zot" / "config.json"
        graph_client = create_neo4j_graphrag_client(str(config_path))

        if not graph_client:
            return "Neo4j GraphRAG is not enabled. Please configure it in config.json to use graph export."

        ctx.info(f"Exporting knowledge graph to {output_file}")

        # Export graph
        stats = graph_client.export_graph_to_graphml(
            output_file=output_file,
            node_types=node_types,
            max_nodes=max_nodes
        )

        # Format summary
        output = ["# Graph Export Results\n"]
        output.append(f"**Output File**: `{stats['output_file']}`")
        output.append(f"**Nodes Exported**: {stats['nodes_exported']}")
        output.append(f"**Edges Exported**: {stats['edges_exported']}")

        if node_types:
            output.append(f"\n**Node Types Included**: {', '.join(node_types)}")

        output.append(f"\n**Import Instructions**:")
        output.append("- **Gephi**: File → Open → Select the .graphml file")
        output.append("- **Cytoscape**: File → Import → Network from File")

        return "\n".join(output)

    except Exception as e:
        ctx.error(f"Error exporting graph: {str(e)}")
        return f"Error exporting graph: {str(e)}"



# ============================================================================
# CHATGPT COMPATIBILITY TOOLS
# ============================================================================
# @mcp.tool(
#     name="search",
#     description="🔧 LOW PRIORITY - ⚪ FALLBACK - ChatGPT-compatible search wrapper. Performs semantic search and returns JSON results.\n\nFor Claude users: Use zot_semantic_search, zot_enhanced_semantic_search, or zot_ask_paper directly for better results.\n\nUse for: ChatGPT integrations only"
# ,
#     annotations={
#         "readOnlyHint": True,
#         "title": "Search (ChatGPT)"
#     }
# )
def chatgpt_connector_search(
    query: str,
    *,
    ctx: Context
) -> str:
    """
    Returns a JSON-encoded string with shape {"results": [{"id","title","url"}, ...]}.
    The MCP runtime wraps this string as a single text content item.
    """
    try:
        default_limit = 10

        from agent_zot.search.semantic import create_semantic_search

        config_path = Path.home() / ".config" / "agent-zot" / "config.json"
        search = create_semantic_search(str(config_path))

        result_list: List[Dict[str, str]] = []
        results = search.search(query=query, limit=default_limit, filters=None) or {}
        for r in results.get("results", []):
            item_key = r.get("item_key") or ""
            title = ""
            if r.get("zotero_item"):
                data = (r.get("zotero_item") or {}).get("data", {})
                title = data.get("title", "")
            if not title:
                title = f"Zotero Item {item_key}" if item_key else "Zotero Item"
            url = f"zotero://select/items/{item_key}" if item_key else ""
            result_list.append({
                "id": item_key or uuid.uuid4().hex[:8],
                "title": title,
                "url": url,
            })

        return json.dumps({"results": result_list}, separators=(",", ":"))
    except Exception as e:
        ctx.error(f"Error in search wrapper: {str(e)}")
        return json.dumps({"results": []}, separators=(",", ":"))


# @mcp.tool(
#     name="fetch",
#     description="🔧 LOW PRIORITY - ⚪ FALLBACK - ChatGPT-compatible fetch wrapper. Retrieves fulltext/metadata for a Zotero item by ID.\n\nFor Claude users: Use zot_get_item, zot_ask_paper, or zot_semantic_search directly for better results.\n\nUse for: ChatGPT integrations only"
# ,
#     annotations={
#         "readOnlyHint": True,
#         "title": "Fetch (ChatGPT)"
#     }
# )
def connector_fetch(
    id: str,
    *,
    ctx: Context
) -> str:
    """
    Returns a JSON-encoded string with shape {"id","title","text","url","metadata":{...}}.
    The MCP runtime wraps this string as a single text content item.
    """
    try:
        item_key = (id or "").strip()
        if not item_key:
            return json.dumps({
                "id": id,
                "title": "",
                "text": "",
                "url": "",
                "metadata": {"error": "missing item key"}
            }, separators=(",", ":"))

        # Fetch item metadata for title and context
        zot = get_zotero_client()
        try:
            item = get_item_with_fallback(zot, item_key)
            data = item.get("data", {}) if item else {}
        except Exception:
            item = None
            data = {}

        title = data.get("title", f"Zotero Item {item_key}")
        zotero_url = f"zotero://select/items/{item_key}"
        # Prefer web URL for connectors; fall back to zotero:// if unknown
        lib_type = (os.getenv("ZOTERO_LIBRARY_TYPE", "user") or "user").lower()
        lib_id = os.getenv("ZOTERO_LIBRARY_ID", "")
        if lib_type not in ["user", "group"]:
            lib_type = "user"
        web_url = f"https://www.zotero.org/{'users' if lib_type=='user' else 'groups'}/{lib_id}/items/{item_key}" if lib_id else ""
        url = web_url or zotero_url

        # Use existing tool to get best-effort fulltext/markdown
        text_md = get_item_fulltext(item_key=item_key, ctx=ctx)
        # Extract the actual full text section if present, else keep as-is
        text_clean = text_md
        try:
            marker = "## Full Text"
            pos = text_md.find(marker)
            if pos >= 0:
                text_clean = text_md[pos + len(marker):].lstrip("\n #")
        except Exception:
            pass
        if (not text_clean or len(text_clean.strip()) < 40) and data:
            abstract = data.get("abstractNote", "")
            creators = data.get("creators", [])
            byline = format_creators(creators)
            text_clean = (f"{title}\n\n" + (f"Authors: {byline}\n" if byline else "") +
                          (f"Abstract:\n{abstract}" if abstract else "")) or text_md

        metadata = {
            "itemType": data.get("itemType", ""),
            "date": data.get("date", ""),
            "key": item_key,
            "doi": data.get("DOI", ""),
            "authors": format_creators(data.get("creators", [])),
            "tags": [t.get("tag", "") for t in (data.get("tags", []) or [])],
            "zotero_url": zotero_url,
            "web_url": web_url,
            "source": "agent-zot"
        }

        return json.dumps({
            "id": item_key,
            "title": title,
            "text": text_clean,
            "url": url,
            "metadata": metadata
        }, separators=(",", ":"))
    except Exception as e:
        ctx.error(f"Error in fetch wrapper: {str(e)}")
        return json.dumps({
            "id": id,
            "title": "",
            "text": "",
            "url": "",
            "metadata": {"error": str(e)}
        }, separators=(",", ":"))
