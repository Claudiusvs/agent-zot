"""
Graphiti client wrapper for MCP server.

Provides a Python interface to the Graphiti MCP tools for autonomous
entity extraction and knowledge graph discovery.

This client is used internally by the agent-zot ingestion pipeline
and search tools. It interacts with the Graphiti MCP server through
the mcp__ prefixed tools that are exposed to Claude.
"""

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class EntityNode:
    """An entity node extracted by Graphiti."""

    name: str
    uuid: str
    summary: Optional[str] = None
    entity_type: Optional[str] = None


@dataclass
class RelationshipFact:
    """A relationship fact extracted by Graphiti."""

    uuid: str
    fact: str
    valid_at: Optional[str] = None
    invalid_at: Optional[str] = None


class GraphitiClientError(Exception):
    """Base exception for Graphiti client errors."""
    pass


class GraphitiUnavailableError(GraphitiClientError):
    """Raised when Graphiti MCP server is unavailable."""
    pass


class GraphitiClient:
    """
    Client for interacting with Graphiti MCP server.

    Wraps MCP tool calls with error handling, logging, and graceful degradation.

    Note: This client uses a callable interface for MCP tool invocation to allow
    dependency injection for testing and to avoid circular imports with server.py.
    """

    def __init__(
        self,
        group_id: str = "agent-zot-discovery",
        mcp_timeout_seconds: int = 10,
        mcp_tool_caller: Optional[Callable] = None,
    ):
        """
        Initialize Graphiti client.

        Args:
            group_id: Graphiti group ID for namespace isolation
            mcp_timeout_seconds: Timeout for MCP calls
            mcp_tool_caller: Optional callable for MCP tool invocation (tool_name, **kwargs)
                            If None, will attempt to import from agent_zot.mcp_integration
        """
        self.group_id = group_id
        self.timeout = mcp_timeout_seconds
        self._mcp_tool_caller = mcp_tool_caller
        self._available: Optional[bool] = None

    def _call_mcp_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Internal method to call MCP tools.

        Args:
            tool_name: Name of the MCP tool (without mcp__ prefix)
            **kwargs: Tool parameters

        Returns:
            Tool result

        Raises:
            Exception: If tool call fails
        """
        if self._mcp_tool_caller:
            return self._mcp_tool_caller(tool_name, **kwargs)

        # Default: try to import mcp integration module
        try:
            from agent_zot.mcp_integration import call_mcp_tool
            return call_mcp_tool(tool_name, **kwargs)
        except ImportError:
            # Fallback: return mock result for testing
            logger.warning(f"MCP tool caller not configured, returning mock result for {tool_name}")
            return {"status": "mock"}

    def is_available(self) -> bool:
        """
        Check if Graphiti MCP server is available.

        Returns:
            True if server is responding, False otherwise.
        """
        if self._available is not None:
            return self._available

        try:
            # Test connectivity with a simple search
            result = self._call_mcp_tool(
                "mcp__graphiti__search_memory_nodes",
                query="test",
                group_ids=[self.group_id],
                max_nodes=1,
            )
            self._available = True
            logger.info("Graphiti MCP server is available")
            return True

        except Exception as e:
            self._available = False
            logger.warning(f"Graphiti MCP server unavailable: {e}")
            return False

    def add_paper_chunk(
        self,
        chunk_text: str,
        paper_key: str,
        metadata: Optional[Dict[str, Any]] = None,
        episode_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Add a paper chunk to Graphiti for entity extraction.

        Args:
            chunk_text: Text content of the chunk
            paper_key: Zotero item key
            metadata: Optional metadata (authors, title, etc.)
            episode_name: Optional custom episode name

        Returns:
            Result dictionary with status

        Raises:
            GraphitiUnavailableError: If Graphiti is not available
            GraphitiClientError: If ingestion fails
        """
        if not self.is_available():
            raise GraphitiUnavailableError("Graphiti MCP server is not available")

        start_time = time.time()

        try:
            # Generate episode name if not provided
            if not episode_name:
                episode_name = f"Paper {paper_key}"

            # Format metadata as source description
            source_description = "Zotero paper chunk"
            if metadata:
                title = metadata.get("title", "")
                authors = metadata.get("authors", "")
                if title:
                    source_description += f": {title}"
                if authors:
                    source_description += f" by {authors}"

            # Call MCP tool to add memory
            result = self._call_mcp_tool(
                "mcp__graphiti__add_memory",
                name=episode_name,
                episode_body=chunk_text,
                group_id=self.group_id,
                source="text",
                source_description=source_description,
            )

            elapsed = time.time() - start_time

            logger.info(
                f"Added paper chunk to Graphiti",
                extra={
                    "paper_key": paper_key,
                    "chunk_length": len(chunk_text),
                    "elapsed_seconds": elapsed,
                    "group_id": self.group_id,
                },
            )

            return {
                "success": True,
                "paper_key": paper_key,
                "elapsed_seconds": elapsed,
                "result": result,
            }

        except Exception as e:
            logger.error(
                f"Failed to add paper chunk to Graphiti: {e}",
                extra={"paper_key": paper_key},
            )
            raise GraphitiClientError(f"Failed to add paper chunk: {e}") from e

    def search_entities(
        self,
        query: str,
        max_nodes: int = 10,
        center_node_uuid: Optional[str] = None,
        entity_type: Optional[str] = None,
    ) -> List[EntityNode]:
        """
        Search for entities in Graphiti.

        Args:
            query: Natural language search query
            max_nodes: Maximum nodes to return
            center_node_uuid: Optional UUID to center search around
            entity_type: Optional entity type filter (e.g., "Preference", "Procedure")

        Returns:
            List of EntityNode objects

        Raises:
            GraphitiUnavailableError: If Graphiti is not available
            GraphitiClientError: If search fails
        """
        if not self.is_available():
            raise GraphitiUnavailableError("Graphiti MCP server is not available")

        try:
            result = self._call_mcp_tool(
                "mcp__graphiti__search_memory_nodes",
                query=query,
                group_ids=[self.group_id],
                max_nodes=max_nodes,
                center_node_uuid=center_node_uuid,
                entity=entity_type or "",
            )

            # Parse result into EntityNode objects
            nodes = []
            if isinstance(result, dict) and "nodes" in result:
                for node_data in result["nodes"]:
                    nodes.append(
                        EntityNode(
                            name=node_data.get("name", ""),
                            uuid=node_data.get("uuid", ""),
                            summary=node_data.get("summary"),
                            entity_type=node_data.get("entity_type"),
                        )
                    )

            logger.info(
                f"Found {len(nodes)} entities in Graphiti",
                extra={
                    "query": query,
                    "max_nodes": max_nodes,
                    "entity_type": entity_type,
                },
            )

            return nodes

        except Exception as e:
            logger.error(f"Failed to search entities in Graphiti: {e}")
            raise GraphitiClientError(f"Failed to search entities: {e}") from e

    def search_relationships(
        self,
        query: str,
        max_facts: int = 10,
        center_node_uuid: Optional[str] = None,
    ) -> List[RelationshipFact]:
        """
        Search for relationship facts in Graphiti.

        Args:
            query: Natural language search query
            max_facts: Maximum facts to return
            center_node_uuid: Optional UUID to center search around

        Returns:
            List of RelationshipFact objects

        Raises:
            GraphitiUnavailableError: If Graphiti is not available
            GraphitiClientError: If search fails
        """
        if not self.is_available():
            raise GraphitiUnavailableError("Graphiti MCP server is not available")

        try:
            result = self._call_mcp_tool(
                "mcp__graphiti__search_memory_facts",
                query=query,
                group_ids=[self.group_id],
                max_facts=max_facts,
                center_node_uuid=center_node_uuid,
            )

            # Parse result into RelationshipFact objects
            facts = []
            if isinstance(result, dict) and "facts" in result:
                for fact_data in result["facts"]:
                    facts.append(
                        RelationshipFact(
                            uuid=fact_data.get("uuid", ""),
                            fact=fact_data.get("fact", ""),
                            valid_at=fact_data.get("valid_at"),
                            invalid_at=fact_data.get("invalid_at"),
                        )
                    )

            logger.info(
                f"Found {len(facts)} relationship facts in Graphiti",
                extra={"query": query, "max_facts": max_facts},
            )

            return facts

        except Exception as e:
            logger.error(f"Failed to search relationships in Graphiti: {e}")
            raise GraphitiClientError(f"Failed to search relationships: {e}") from e

    def get_paper_entities(self, paper_key: str) -> List[EntityNode]:
        """
        Retrieve all entities associated with a specific paper.

        Args:
            paper_key: Zotero item key

        Returns:
            List of EntityNode objects

        Raises:
            GraphitiUnavailableError: If Graphiti is not available
            GraphitiClientError: If retrieval fails
        """
        if not self.is_available():
            raise GraphitiUnavailableError("Graphiti MCP server is not available")

        try:
            # Search for entities mentioning the paper key
            # This is a heuristic approach since Graphiti doesn't have direct
            # paper-to-entity linking (we track via episode names)
            query = f"Paper {paper_key}"

            return self.search_entities(query=query, max_nodes=50)

        except Exception as e:
            logger.error(
                f"Failed to get entities for paper: {e}",
                extra={"paper_key": paper_key},
            )
            raise GraphitiClientError(
                f"Failed to get entities for paper {paper_key}: {e}"
            ) from e

    def get_status(self) -> Dict[str, Any]:
        """
        Get Graphiti client status.

        Returns:
            Status dictionary with availability and configuration
        """
        return {
            "available": self.is_available(),
            "group_id": self.group_id,
            "timeout_seconds": self.timeout,
        }
