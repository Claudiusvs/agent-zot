"""
Unified Export Tool

Consolidates 3 legacy export tools into a single intelligent tool:
- zot_export_markdown → smart_export (Markdown Mode)
- zot_export_bibtex → smart_export (BibTeX Mode)
- zot_export_graph → smart_export (GraphML Mode)

Created: 2025-10-25
Architecture: Automatic format detection from file extension + explicit format parameter
"""

import re
import os
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


def detect_export_format(
    output_file: str,
    explicit_format: Optional[str] = None
) -> tuple[str, float]:
    """
    Detect export format from file extension or explicit parameter.

    Args:
        output_file: Output file path
        explicit_format: Explicit format specification

    Returns:
        Tuple of (format, confidence)
        - format: "markdown", "bibtex", "graphml"
        - confidence: 0.0-1.0
    """
    # Explicit format takes precedence
    if explicit_format:
        format_lower = explicit_format.lower()
        if format_lower in ["markdown", "md"]:
            return ("markdown", 1.0)
        elif format_lower in ["bibtex", "bib"]:
            return ("bibtex", 1.0)
        elif format_lower in ["graphml", "xml"]:
            return ("graphml", 1.0)

    # Detect from file extension
    _, ext = os.path.splitext(output_file.lower())

    if ext in [".md", ".markdown"]:
        return ("markdown", 0.95)
    elif ext in [".bib", ".bibtex"]:
        return ("bibtex", 0.95)
    elif ext in [".graphml", ".xml"]:
        return ("graphml", 0.95)

    # Default fallback
    return ("markdown", 0.50)


# ========== Mode Implementations ==========

def run_markdown_mode(
    zotero_client,
    output_dir: str,
    query: Optional[str] = None,
    collection_key: Optional[str] = None,
    include_fulltext: bool = False,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Markdown Mode: Export items to Markdown files with YAML frontmatter.

    Args:
        zotero_client: Zotero API client
        output_dir: Directory to export markdown files to
        query: Optional search query to filter items
        collection_key: Optional collection to export from
        include_fulltext: Whether to include full PDF text
        limit: Maximum number of items to export

    Returns:
        Dict with success, mode, content, files_created
    """
    try:
        logger.info(f"Markdown Mode: Exporting to {output_dir}")

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Get items
        if collection_key:
            items = zotero_client.collection_items(collection_key, limit=limit)
        elif query:
            zotero_client.add_parameters(q=query, limit=limit)
            items = zotero_client.items()
        else:
            items = zotero_client.items(limit=limit)

        if not items:
            return {
                "success": True,
                "mode": "markdown",
                "content": "No items found to export.",
                "files_created": 0
            }

        files_created = 0
        for item in items:
            data = item.get("data", {})
            if data.get("itemType") == "attachment":
                continue  # Skip attachments

            title = data.get("title", "Untitled")
            key = item.get("key", "unknown")

            # Generate filename from title
            safe_title = re.sub(r'[^\w\s-]', '', title)[:50]
            filename = f"{safe_title}_{key}.md"
            filepath = os.path.join(output_dir, filename)

            # Build YAML frontmatter
            yaml_lines = ["---"]
            yaml_lines.append(f"title: \"{title}\"")
            yaml_lines.append(f"zotero_key: {key}")

            if creators := data.get("creators"):
                authors = [
                    f"{c.get('lastName', '')}, {c.get('firstName', '')}".strip(", ")
                    for c in creators
                ]
                yaml_lines.append(f"authors: {authors}")

            if date := data.get("date"):
                yaml_lines.append(f"date: {date}")

            if pub_title := data.get("publicationTitle"):
                yaml_lines.append(f"publication: \"{pub_title}\"")

            if tags := data.get("tags"):
                tag_list = [t.get("tag", "") for t in tags]
                yaml_lines.append(f"tags: {tag_list}")

            yaml_lines.append("---")
            yaml_lines.append("")

            # Add abstract
            if abstract := data.get("abstractNote"):
                yaml_lines.append("## Abstract")
                yaml_lines.append("")
                yaml_lines.append(abstract)
                yaml_lines.append("")

            # Add full text if requested
            if include_fulltext:
                # TODO: Implement full text extraction
                yaml_lines.append("## Full Text")
                yaml_lines.append("")
                yaml_lines.append("(Full text extraction not yet implemented)")
                yaml_lines.append("")

            # Write file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(yaml_lines))

            files_created += 1

        return {
            "success": True,
            "mode": "markdown",
            "content": f"✓ Exported {files_created} items to Markdown\n**Output Directory:** {output_dir}",
            "files_created": files_created
        }

    except Exception as e:
        logger.error(f"Markdown Mode error: {e}")
        return {
            "success": False,
            "mode": "markdown",
            "error": f"Failed to export markdown: {str(e)}"
        }


def run_bibtex_mode(
    zotero_client,
    output_file: str,
    query: Optional[str] = None,
    collection_key: Optional[str] = None,
    limit: int = 1000
) -> Dict[str, Any]:
    """
    BibTeX Mode: Export items to BibTeX format.

    Args:
        zotero_client: Zotero API client
        output_file: Output .bib file path
        query: Optional search query to filter items
        collection_key: Optional collection to export from
        limit: Maximum number of items to export

    Returns:
        Dict with success, mode, content, items_exported
    """
    try:
        logger.info(f"BibTeX Mode: Exporting to {output_file}")

        # Get items
        if collection_key:
            items = zotero_client.collection_items(collection_key, limit=limit)
        elif query:
            zotero_client.add_parameters(q=query, limit=limit)
            items = zotero_client.items()
        else:
            items = zotero_client.items(limit=limit)

        if not items:
            return {
                "success": True,
                "mode": "bibtex",
                "content": "No items found to export.",
                "items_exported": 0
            }

        # Use Zotero's built-in BibTeX export
        # Get bibliographic data in BibTeX format
        bibtex_entries = []
        for item in items:
            data = item.get("data", {})
            if data.get("itemType") == "attachment":
                continue

            # Request BibTeX format from Zotero
            key = item.get("key")
            bibtex = zotero_client.item(key, format='bibtex')
            if bibtex:
                bibtex_entries.append(bibtex)

        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(bibtex_entries))

        return {
            "success": True,
            "mode": "bibtex",
            "content": f"✓ Exported {len(bibtex_entries)} items to BibTeX\n**Output File:** {output_file}",
            "items_exported": len(bibtex_entries)
        }

    except Exception as e:
        logger.error(f"BibTeX Mode error: {e}")
        return {
            "success": False,
            "mode": "bibtex",
            "error": f"Failed to export BibTeX: {str(e)}"
        }


def run_graphml_mode(
    neo4j_client,
    output_file: str,
    node_types: Optional[List[str]] = None,
    max_nodes: Optional[int] = None
) -> Dict[str, Any]:
    """
    GraphML Mode: Export Neo4j knowledge graph to GraphML format.

    Args:
        neo4j_client: Neo4j client instance
        output_file: Output .graphml file path
        node_types: Optional list of node types to export
        max_nodes: Optional maximum number of nodes to export

    Returns:
        Dict with success, mode, content, nodes_exported, edges_exported
    """
    try:
        logger.info(f"GraphML Mode: Exporting graph to {output_file}")

        if not neo4j_client:
            return {
                "success": False,
                "mode": "graphml",
                "error": "Neo4j not available. Graph export requires Neo4j GraphRAG to be enabled."
            }

        # Build Cypher query
        if node_types:
            node_filter = " OR ".join([f"n:{nt}" for nt in node_types])
            query = f"MATCH (n) WHERE {node_filter} RETURN n"
        else:
            query = "MATCH (n) RETURN n"

        if max_nodes:
            query += f" LIMIT {max_nodes}"

        # Get nodes
        result = neo4j_client.execute_query(query)
        nodes = [record["n"] for record in result]

        # Get relationships
        rel_query = "MATCH (n)-[r]->(m) RETURN n, r, m"
        if max_nodes:
            rel_query += f" LIMIT {max_nodes * 2}"

        rel_result = neo4j_client.execute_query(rel_query)

        # Build GraphML
        graphml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        graphml_lines.append('<graphml xmlns="http://graphml.graphdrawing.org/xmlns">')
        graphml_lines.append('  <graph id="ZoteroKnowledgeGraph" edgedefault="directed">')

        # Add nodes
        for node in nodes:
            node_id = node.element_id
            node_label = list(node.labels)[0] if node.labels else "Node"
            node_name = node.get("name", node.get("title", ""))

            graphml_lines.append(f'    <node id="{node_id}">')
            graphml_lines.append(f'      <data key="label">{node_label}</data>')
            graphml_lines.append(f'      <data key="name">{node_name}</data>')
            graphml_lines.append('    </node>')

        # Add edges
        edges_count = 0
        for record in rel_result:
            source = record["n"].element_id
            target = record["m"].element_id
            rel = record["r"]
            rel_type = rel.type

            graphml_lines.append(f'    <edge source="{source}" target="{target}">')
            graphml_lines.append(f'      <data key="type">{rel_type}</data>')
            graphml_lines.append('    </edge>')
            edges_count += 1

        graphml_lines.append('  </graph>')
        graphml_lines.append('</graphml>')

        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(graphml_lines))

        return {
            "success": True,
            "mode": "graphml",
            "content": f"✓ Exported Neo4j graph to GraphML\n**Output File:** {output_file}\n**Nodes:** {len(nodes)}\n**Edges:** {edges_count}",
            "nodes_exported": len(nodes),
            "edges_exported": edges_count
        }

    except Exception as e:
        logger.error(f"GraphML Mode error: {e}")
        return {
            "success": False,
            "mode": "graphml",
            "error": f"Failed to export GraphML: {str(e)}"
        }


# ========== Main Unified Function ==========

def smart_export(
    output_file: str,
    zotero_client=None,
    neo4j_client=None,
    format: Optional[str] = None,
    query: Optional[str] = None,
    collection_key: Optional[str] = None,
    include_fulltext: bool = False,
    node_types: Optional[List[str]] = None,
    max_nodes: Optional[int] = None,
    limit: int = 1000
) -> Dict[str, Any]:
    """
    Intelligent unified export tool.

    Automatically detects format and routes to appropriate mode:
    - Markdown Mode: Export to markdown files with YAML frontmatter
    - BibTeX Mode: Export to .bib file
    - GraphML Mode: Export Neo4j graph

    Args:
        output_file: Output file path (or directory for markdown)
        zotero_client: Zotero API client (for markdown/bibtex)
        neo4j_client: Neo4j client (for graphml)
        format: Optional explicit format ("markdown", "bibtex", "graphml")
        query: Search query to filter items (markdown/bibtex)
        collection_key: Collection to export from (markdown/bibtex)
        include_fulltext: Include full PDF text (markdown only)
        node_types: Node types to export (graphml only)
        max_nodes: Max nodes to export (graphml only)
        limit: Max items to export (markdown/bibtex)

    Returns:
        Dict with success, mode, content, and mode-specific fields

    Examples:
        >>> smart_export("papers.md", zot, format="markdown")
        # Exports to markdown directory

        >>> smart_export("refs.bib", zot, query="machine learning")
        # Exports filtered items to BibTeX

        >>> smart_export("graph.graphml", neo4j_client=neo4j)
        # Exports Neo4j graph to GraphML
    """
    try:
        # Detect format
        detected_format, confidence = detect_export_format(output_file, format)
        logger.info(f"Detected format: {detected_format} (confidence: {confidence:.2f})")

        # Route to appropriate mode
        if detected_format == "markdown":
            if not zotero_client:
                return {
                    "success": False,
                    "error": "Zotero client required for markdown export"
                }

            return run_markdown_mode(
                zotero_client=zotero_client,
                output_dir=output_file,
                query=query,
                collection_key=collection_key,
                include_fulltext=include_fulltext,
                limit=limit
            )

        elif detected_format == "bibtex":
            if not zotero_client:
                return {
                    "success": False,
                    "error": "Zotero client required for BibTeX export"
                }

            return run_bibtex_mode(
                zotero_client=zotero_client,
                output_file=output_file,
                query=query,
                collection_key=collection_key,
                limit=limit
            )

        elif detected_format == "graphml":
            if not neo4j_client:
                return {
                    "success": False,
                    "error": "Neo4j client required for GraphML export. Enable Neo4j GraphRAG first."
                }

            return run_graphml_mode(
                neo4j_client=neo4j_client,
                output_file=output_file,
                node_types=node_types,
                max_nodes=max_nodes
            )

        else:
            return {
                "success": False,
                "error": f"Unknown export format: {detected_format}"
            }

    except Exception as e:
        logger.error(f"smart_export error: {e}")
        return {
            "success": False,
            "error": f"Unified export failed: {str(e)}"
        }
