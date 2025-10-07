"""
Graphiti knowledge graph integration for Zotero MCP.

This module integrates with the Graphiti MCP server for knowledge graph
and GraphRAG capabilities, enabling entity extraction, relationship mapping,
and graph-based reasoning over research documents.
"""

import json
import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class GraphitiClient:
    """Client for Graphiti knowledge graph integration."""

    def __init__(self, graphiti_mcp_url: Optional[str] = None):
        """
        Initialize Graphiti client.

        Args:
            graphiti_mcp_url: URL for Graphiti MCP server (if using HTTP transport)

        Note: By default, Graphiti runs as an MCP server via stdio transport,
              so direct integration happens through the MCP protocol in Claude Desktop.
        """
        self.graphiti_mcp_url = graphiti_mcp_url
        logger.info("Graphiti client initialized (MCP server integration)")

    def add_episode(self,
                    content: str,
                    metadata: Dict[str, Any],
                    source_description: str = "Zotero document") -> Dict[str, Any]:
        """
        Add an episode to the Graphiti knowledge graph.

        Episodes are atomic units of information that Graphiti uses to build
        the knowledge graph. Each episode can contain entities, relationships,
        and facts extracted from the content.

        Args:
            content: The text content to add as an episode
            metadata: Metadata about the source (e.g., Zotero item info)
            source_description: Description of the content source

        Returns:
            Result of the episode addition
        """
        # This is a placeholder for MCP tool invocation
        # In practice, this would call the Graphiti MCP server's add_episode tool
        # through the MCP protocol

        episode_data = {
            "content": content,
            "source": source_description,
            "metadata": metadata,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"Episode prepared for Graphiti: {source_description}")
        return {
            "status": "prepared",
            "episode": episode_data,
            "note": "Episodes are added through MCP tool calls in Claude Desktop"
        }

    def add_zotero_item(self,
                        item_key: str,
                        title: str,
                        abstract: str,
                        authors: List[str],
                        year: Optional[int] = None,
                        doc_chunks: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Add a Zotero item to the knowledge graph.

        Args:
            item_key: Zotero item key
            title: Document title
            abstract: Document abstract
            authors: List of author names
            year: Publication year
            doc_chunks: Optional document chunks from Docling parsing

        Returns:
            Result of adding the item to knowledge graph
        """
        # Build comprehensive content for entity extraction
        content_parts = [f"Title: {title}"]

        if authors:
            content_parts.append(f"Authors: {', '.join(authors)}")

        if year:
            content_parts.append(f"Year: {year}")

        if abstract:
            content_parts.append(f"\nAbstract: {abstract}")

        if doc_chunks:
            # Add selected chunks (limit to avoid overwhelming the graph)
            content_parts.append("\nKey Content:")
            content_parts.extend(doc_chunks[:5])  # First 5 chunks

        full_content = "\n\n".join(content_parts)

        metadata = {
            "item_key": item_key,
            "title": title,
            "authors": authors,
            "year": year,
            "source_type": "zotero",
            "content_type": "research_paper"
        }

        return self.add_episode(
            content=full_content,
            metadata=metadata,
            source_description=f"Zotero item: {title}"
        )

    def search_graph(self,
                     query: str,
                     entity_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Search the Graphiti knowledge graph.

        Args:
            query: Search query
            entity_types: Optional filter for entity types

        Returns:
            Search results from the knowledge graph
        """
        # Placeholder for MCP tool invocation
        # Would call Graphiti's search_nodes MCP tool

        search_params = {
            "query": query,
            "entity_types": entity_types or []
        }

        logger.info(f"Graph search prepared: {query}")
        return {
            "status": "prepared",
            "search_params": search_params,
            "note": "Graph search is performed through MCP tool calls in Claude Desktop"
        }

    def get_related_entities(self, entity_name: str) -> Dict[str, Any]:
        """
        Get entities related to a given entity.

        Args:
            entity_name: Name of the entity

        Returns:
            Related entities and relationships
        """
        # Placeholder for MCP tool invocation
        logger.info(f"Fetching entities related to: {entity_name}")
        return {
            "status": "prepared",
            "entity": entity_name,
            "note": "Related entities fetched through MCP tool calls in Claude Desktop"
        }

    def hybrid_search(self,
                      query: str,
                      vector_results: List[Dict[str, Any]],
                      use_graph_context: bool = True) -> Dict[str, Any]:
        """
        Perform hybrid search combining vector similarity with graph context.

        Args:
            query: Search query
            vector_results: Results from vector semantic search
            use_graph_context: Whether to enrich with graph context

        Returns:
            Hybrid search results with graph enrichment
        """
        if not use_graph_context:
            return {"results": vector_results, "graph_enriched": False}

        # Extract entity mentions from vector results
        result_entities = []
        for result in vector_results[:5]:  # Top 5 results
            # Would extract entities from result content
            if "title" in result:
                result_entities.append(result["title"])

        # Prepare graph context query
        graph_context = {
            "query": query,
            "related_entities": result_entities,
            "vector_results": vector_results,
            "note": "Graph enrichment happens through MCP tool calls"
        }

        logger.info(f"Prepared hybrid search with {len(vector_results)} vector results")
        return {
            "status": "prepared",
            "hybrid_search": graph_context,
            "graph_enriched": True
        }


def create_graphiti_client(config_path: Optional[str] = None) -> GraphitiClient:
    """
    Create a Graphiti client from configuration.

    Args:
        config_path: Path to configuration file

    Returns:
        Configured GraphitiClient instance
    """
    graphiti_url = None

    # Load from config if available
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                graphiti_config = config.get("graphiti", {})
                graphiti_url = graphiti_config.get("mcp_url")
        except Exception as e:
            logger.warning(f"Error loading Graphiti config: {e}")

    # Check environment variable
    if not graphiti_url:
        graphiti_url = os.getenv("GRAPHITI_MCP_URL")

    return GraphitiClient(graphiti_mcp_url=graphiti_url)


# Helper functions for MCP integration

def prepare_zotero_episode(item: Dict[str, Any],
                           chunks: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Prepare a Zotero item as an episode for Graphiti.

    Args:
        item: Zotero item dictionary
        chunks: Optional document chunks

    Returns:
        Episode data ready for Graphiti ingestion
    """
    title = item.get("data", {}).get("title", "Untitled")
    abstract = item.get("data", {}).get("abstractNote", "")

    creators = item.get("data", {}).get("creators", [])
    authors = [f"{c.get('firstName', '')} {c.get('lastName', '')}" for c in creators]

    year = item.get("data", {}).get("date", "")
    try:
        year = int(year[:4]) if year else None
    except:
        year = None

    content_parts = [f"Title: {title}"]

    if authors:
        content_parts.append(f"Authors: {', '.join(authors)}")

    if year:
        content_parts.append(f"Year: {year}")

    if abstract:
        content_parts.append(f"\nAbstract: {abstract}")

    if chunks:
        content_parts.append("\nKey Content:")
        content_parts.extend(chunks[:5])

    return {
        "content": "\n\n".join(content_parts),
        "metadata": {
            "item_key": item.get("key"),
            "item_type": item.get("data", {}).get("itemType"),
            "title": title,
            "authors": authors,
            "year": year,
            "source": "zotero"
        },
        "source_description": f"Zotero: {title}"
    }
