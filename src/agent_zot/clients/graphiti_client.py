"""
Graphiti client wrapper using graphiti_core SDK.

Provides a Python interface to the Graphiti SDK for autonomous
entity extraction and knowledge graph discovery.

This client is used internally by the agent-zot ingestion pipeline
and search tools. It uses the graphiti_core SDK directly instead of
MCP tool calls, allowing it to work in daemon contexts.
"""

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Import graphiti_core SDK
try:
    from graphiti_core import Graphiti
    from graphiti_core.nodes import EpisodeType
    GRAPHITI_AVAILABLE = True
except ImportError:
    GRAPHITI_AVAILABLE = False
    logger.warning(
        "graphiti-core not installed. Install with: pip install graphiti-core"
    )


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
    Client for interacting with Graphiti using graphiti_core SDK.

    Wraps SDK calls with error handling, logging, and graceful degradation.

    This client connects directly to Neo4j using the graphiti_core SDK,
    allowing it to work in daemon contexts without MCP dependencies.
    """

    def __init__(
        self,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "demodemo",
        group_id: str = "agent-zot-discovery",
    ):
        """
        Initialize Graphiti client with direct SDK connection.

        Args:
            neo4j_uri: Neo4j connection URI (bolt://host:port)
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            group_id: Graphiti group ID for namespace isolation
        """
        if not GRAPHITI_AVAILABLE:
            raise GraphitiUnavailableError(
                "graphiti-core not installed. Install with: pip install graphiti-core"
            )

        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.group_id = group_id
        self._available: Optional[bool] = None
        self.graphiti: Optional[Graphiti] = None

    async def _ensure_initialized(self):
        """
        Lazy initialization of Graphiti SDK client.

        Creates the Graphiti instance and builds indices/constraints on first use.
        This allows the client to be created in sync context but used in async.
        """
        if self.graphiti is not None:
            return

        try:
            # Import Anthropic client for LLM operations
            from graphiti_core.llm_client.anthropic_client import AnthropicClient, LLMConfig

            # Create Anthropic LLM client
            # API key should be in environment (ANTHROPIC_API_KEY)
            llm_client = AnthropicClient(
                config=LLMConfig(
                    model="claude-haiku-4-5-20241007",  # Full model ID
                    cache=False  # Disable prompt caching for simplicity
                )
            )

            self.graphiti = Graphiti(
                uri=self.neo4j_uri,
                user=self.neo4j_user,
                password=self.neo4j_password,
                llm_client=llm_client,
            )

            # Build indices and constraints (idempotent operation)
            await self.graphiti.build_indices_and_constraints()

            logger.info(
                f"Graphiti SDK initialized successfully",
                extra={
                    "neo4j_uri": self.neo4j_uri,
                    "group_id": self.group_id,
                },
            )
        except Exception as e:
            logger.error(f"Failed to initialize Graphiti SDK: {e}", exc_info=True)
            self.graphiti = None
            raise GraphitiUnavailableError(f"Failed to initialize Graphiti: {e}") from e

    async def close(self):
        """
        Close the Graphiti SDK connection.

        Should be called when the client is no longer needed to clean up resources.
        """
        if self.graphiti is not None:
            try:
                await self.graphiti.close()
                logger.info("Graphiti SDK connection closed")
            except Exception as e:
                logger.warning(f"Error closing Graphiti SDK: {e}")
            finally:
                self.graphiti = None

    async def is_available(self) -> bool:
        """
        Check if Graphiti SDK is available and Neo4j is accessible.

        Returns:
            True if SDK is initialized and connected, False otherwise.
        """
        if not GRAPHITI_AVAILABLE:
            return False

        if self._available is not None:
            return self._available

        try:
            # Attempt to initialize the SDK
            await self._ensure_initialized()
            self._available = True
            logger.info("Graphiti SDK is available and connected")
            return True

        except Exception as e:
            self._available = False
            logger.warning(f"Graphiti SDK unavailable: {e}")
            return False

    async def add_paper_chunk(
        self,
        chunk_text: str,
        paper_key: str,
        metadata: Optional[Dict[str, Any]] = None,
        episode_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Add a paper chunk to Graphiti for entity extraction using SDK.

        The Zotero item_key is stored in two ways for cross-schema linking:
        1. Embedded in episode name: "Paper {paper_key} - Part X/Y"
        2. Included in source_description for searchability

        This enables queries like:
        - "What entities were extracted from paper ABC123?"
        - "Show me all episodes for Zotero key ABC123"

        Args:
            chunk_text: Text content of the chunk
            paper_key: Zotero item key (stored in episode name for linking)
            metadata: Optional metadata (authors, title, etc.)
            episode_name: Optional custom episode name (should include paper_key)

        Returns:
            Result dictionary with status

        Raises:
            GraphitiUnavailableError: If Graphiti is not available
            GraphitiClientError: If ingestion fails
        """
        if not await self.is_available():
            raise GraphitiUnavailableError("Graphiti SDK is not available")

        start_time = time.time()

        try:
            # Ensure SDK is initialized
            await self._ensure_initialized()

            # Generate episode name if not provided (must include paper_key)
            if not episode_name:
                episode_name = f"Paper {paper_key}"

            # Format metadata as source description (include item_key for searchability)
            source_description = f"Zotero paper chunk [item_key={paper_key}]"
            if metadata:
                title = metadata.get("title", "")
                authors = metadata.get("authors", "")
                if title:
                    source_description += f": {title}"
                if authors:
                    source_description += f" by {authors}"

            # Import datetime for reference_time
            from datetime import datetime, timezone

            # Call SDK to add episode
            # Note: We embed item_key in episode name and source_description for cross-schema linking
            result = await self.graphiti.add_episode(
                name=episode_name,
                episode_body=chunk_text,
                group_id=self.group_id,
                source=EpisodeType.text,
                source_description=source_description,
                reference_time=datetime.now(timezone.utc),
            )

            elapsed = time.time() - start_time

            logger.info(
                f"Added paper chunk to Graphiti with item_key in metadata",
                extra={
                    "paper_key": paper_key,
                    "episode_name": episode_name,
                    "chunk_length": len(chunk_text),
                    "elapsed_seconds": elapsed,
                    "group_id": self.group_id,
                    "episode_uuid": result.episode.uuid if result and result.episode else None,
                    "entities_extracted": len(result.nodes) if result and result.nodes else 0,
                    "relationships_extracted": len(result.edges) if result and result.edges else 0,
                },
            )

            return {
                "success": True,
                "paper_key": paper_key,
                "episode_name": episode_name,
                "elapsed_seconds": elapsed,
                "episode_uuid": result.episode.uuid if result and result.episode else None,
                "entities_count": len(result.nodes) if result and result.nodes else 0,
                "relationships_count": len(result.edges) if result and result.edges else 0,
            }

        except Exception as e:
            logger.error(
                f"Failed to add paper chunk to Graphiti: {e}",
                extra={"paper_key": paper_key},
            )
            raise GraphitiClientError(f"Failed to add paper chunk: {e}") from e

    async def search_entities(
        self,
        query: str,
        max_nodes: int = 10,
        center_node_uuid: Optional[str] = None,
        entity_type: Optional[str] = None,
    ) -> List[EntityNode]:
        """
        Search for entities in Graphiti using SDK.

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
        if not await self.is_available():
            raise GraphitiUnavailableError("Graphiti SDK is not available")

        try:
            await self._ensure_initialized()

            # Use SDK search method
            result = await self.graphiti.search(
                query=query,
                group_ids=[self.group_id],
                num_results=max_nodes,
                center_node_uuid=center_node_uuid,
            )

            # Parse result into EntityNode objects
            nodes = []
            if result and hasattr(result, 'nodes'):
                for node in result.nodes:
                    nodes.append(
                        EntityNode(
                            name=node.name if hasattr(node, 'name') else "",
                            uuid=node.uuid if hasattr(node, 'uuid') else "",
                            summary=node.summary if hasattr(node, 'summary') else None,
                            entity_type=None,  # SDK doesn't provide entity_type in search
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

    async def search_relationships(
        self,
        query: str,
        max_facts: int = 10,
        center_node_uuid: Optional[str] = None,
    ) -> List[RelationshipFact]:
        """
        Search for relationship facts in Graphiti using SDK.

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
        if not await self.is_available():
            raise GraphitiUnavailableError("Graphiti SDK is not available")

        try:
            await self._ensure_initialized()

            # Use SDK search method - returns edges in result
            result = await self.graphiti.search(
                query=query,
                group_ids=[self.group_id],
                num_results=max_facts,
                center_node_uuid=center_node_uuid,
            )

            # Parse edges into RelationshipFact objects
            facts = []
            if result and hasattr(result, 'edges'):
                for edge in result.edges:
                    facts.append(
                        RelationshipFact(
                            uuid=edge.uuid if hasattr(edge, 'uuid') else "",
                            fact=edge.fact if hasattr(edge, 'fact') else "",
                            valid_at=str(edge.valid_at) if hasattr(edge, 'valid_at') and edge.valid_at else None,
                            invalid_at=str(edge.invalid_at) if hasattr(edge, 'invalid_at') and edge.invalid_at else None,
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

    async def get_paper_entities(self, paper_key: str) -> List[EntityNode]:
        """
        Retrieve all entities associated with a specific paper using SDK.

        Uses the embedded item_key in episode names to find entities extracted
        from a specific Zotero paper. Episode names follow the pattern:
        "Paper {paper_key} - Part X/Y"

        Args:
            paper_key: Zotero item key

        Returns:
            List of EntityNode objects

        Raises:
            GraphitiUnavailableError: If Graphiti is not available
            GraphitiClientError: If retrieval fails

        Example:
            >>> client = GraphitiClient()
            >>> entities = client.get_paper_entities("ABC123")
            >>> # Returns entities from episodes named "Paper ABC123 - Part 1/3", etc.
        """
        if not await self.is_available():
            raise GraphitiUnavailableError("Graphiti SDK is not available")

        try:
            # Search for entities using the embedded item_key pattern
            # Episode names contain "Paper {paper_key}" for cross-schema linking
            query = f"Paper {paper_key}"

            logger.info(
                f"Searching for entities from paper using embedded item_key",
                extra={"paper_key": paper_key, "query": query},
            )

            return await self.search_entities(query=query, max_nodes=50)

        except Exception as e:
            logger.error(
                f"Failed to get entities for paper: {e}",
                extra={"paper_key": paper_key},
            )
            raise GraphitiClientError(
                f"Failed to get entities for paper {paper_key}: {e}"
            ) from e

    async def get_status(self) -> Dict[str, Any]:
        """
        Get Graphiti client status.

        Returns:
            Status dictionary with availability and configuration
        """
        return {
            "available": await self.is_available(),
            "group_id": self.group_id,
            "neo4j_uri": self.neo4j_uri,
            "sdk_initialized": self.graphiti is not None,
        }
