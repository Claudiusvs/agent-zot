"""
Neo4j GraphRAG integration for Zotero MCP.

This module integrates Neo4j GraphRAG for building and querying
knowledge graphs from research papers.
"""

import json
import os
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from neo4j import GraphDatabase
from neo4j_graphrag.llm import LLMInterface, OpenAILLM
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline

logger = logging.getLogger(__name__)


class Neo4jGraphRAGClient:
    """Client for Neo4j GraphRAG knowledge graph operations."""

    def __init__(self,
                 neo4j_uri: str,
                 neo4j_user: str,
                 neo4j_password: str,
                 neo4j_database: str = "neo4j",
                 llm_model: str = "gpt-4o-mini",
                 openai_api_key: Optional[str] = None):
        """
        Initialize Neo4j GraphRAG client.

        Args:
            neo4j_uri: Neo4j connection URI (e.g., neo4j://localhost:7687)
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            neo4j_database: Neo4j database name
            llm_model: OpenAI model for entity extraction
            openai_api_key: OpenAI API key
        """
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.neo4j_database = neo4j_database

        # Initialize Neo4j driver
        self.driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )

        # Initialize LLM for entity extraction
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key required for entity extraction")

        self.llm = OpenAILLM(
            model_name=llm_model,
            api_key=api_key
        )

        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-large",
            api_key=api_key
        )

        logger.info(f"Neo4j GraphRAG client initialized for database: {neo4j_database}")

    def close(self):
        """Close Neo4j driver connection."""
        if self.driver:
            self.driver.close()

    def add_paper_to_graph(self,
                          paper_key: str,
                          title: str,
                          abstract: str,
                          authors: List[str],
                          year: Optional[int] = None,
                          chunks: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Add a research paper to the knowledge graph.

        Args:
            paper_key: Zotero item key
            title: Paper title
            abstract: Paper abstract
            authors: List of author names
            year: Publication year
            chunks: Optional document chunks from Docling

        Returns:
            Result of the operation
        """
        try:
            # Build content for entity extraction
            content_parts = [f"Title: {title}"]

            if authors:
                content_parts.append(f"Authors: {', '.join(authors)}")

            if year:
                content_parts.append(f"Year: {year}")

            if abstract:
                content_parts.append(f"\nAbstract: {abstract}")

            if chunks:
                # Add first few chunks for more context
                content_parts.append("\nKey Content:")
                content_parts.extend(chunks[:3])

            full_content = "\n\n".join(content_parts)

            # Create knowledge graph pipeline
            kg_builder = SimpleKGPipeline(
                llm=self.llm,
                driver=self.driver,
                database=self.neo4j_database,
                embedder=self.embeddings,
                entities=["Person", "Institution", "Concept", "Method", "Dataset", "Theory"],
                relations=["AUTHORED_BY", "AFFILIATED_WITH", "USES", "CITES", "BUILDS_ON", "PART_OF"],
                from_pdf=False
            )

            # Add paper metadata as a node first
            with self.driver.session(database=self.neo4j_database) as session:
                session.run(
                    """
                    MERGE (p:Paper {item_key: $item_key})
                    SET p.title = $title,
                        p.abstract = $abstract,
                        p.year = $year,
                        p.authors = $authors
                    """,
                    item_key=paper_key,
                    title=title,
                    abstract=abstract,
                    year=year,
                    authors=authors
                )

            # Extract entities and relationships from content
            result = kg_builder.run_async(text=full_content)

            # Link extracted entities to the paper
            with self.driver.session(database=self.neo4j_database) as session:
                session.run(
                    """
                    MATCH (p:Paper {item_key: $item_key})
                    MATCH (e)
                    WHERE e.id IS NOT NULL
                    MERGE (p)-[:MENTIONS]->(e)
                    """,
                    item_key=paper_key
                )

            logger.info(f"Added paper to graph: {title}")
            return {
                "status": "success",
                "paper_key": paper_key,
                "title": title
            }

        except Exception as e:
            logger.error(f"Error adding paper to graph: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def search_entities(self,
                       query: str,
                       entity_types: Optional[List[str]] = None,
                       limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for entities in the knowledge graph.

        Args:
            query: Search query
            entity_types: Filter by entity types (e.g., ["Concept", "Method"])
            limit: Maximum number of results

        Returns:
            List of matching entities with their properties
        """
        try:
            with self.driver.session(database=self.neo4j_database) as session:
                # Build entity type filter
                type_filter = ""
                if entity_types:
                    labels = " OR ".join([f"e:{t}" for t in entity_types])
                    type_filter = f"WHERE {labels}"

                # Search using text match
                cypher_query = f"""
                MATCH (e)
                {type_filter}
                WHERE toLower(e.name) CONTAINS toLower($query)
                   OR toLower(e.description) CONTAINS toLower($query)
                RETURN e, labels(e) as types
                LIMIT $limit
                """

                result = session.run(cypher_query, query=query, limit=limit)

                entities = []
                for record in result:
                    entity = dict(record["e"])
                    entity["types"] = record["types"]
                    entities.append(entity)

                logger.info(f"Found {len(entities)} entities matching: {query}")
                return entities

        except Exception as e:
            logger.error(f"Error searching entities: {e}")
            return []

    def find_related_papers(self,
                           paper_key: str,
                           max_depth: int = 2,
                           limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find papers related to a given paper via shared entities.

        Args:
            paper_key: Zotero item key of the source paper
            max_depth: Maximum graph traversal depth
            limit: Maximum number of results

        Returns:
            List of related papers with relationship information
        """
        try:
            with self.driver.session(database=self.neo4j_database) as session:
                cypher_query = """
                MATCH (source:Paper {item_key: $paper_key})
                MATCH path = (source)-[:MENTIONS*1..2]-(entity)-[:MENTIONS*1..2]-(related:Paper)
                WHERE source <> related
                WITH related,
                     count(DISTINCT entity) as shared_entities,
                     collect(DISTINCT entity.name)[0..5] as sample_entities
                RETURN related.item_key as item_key,
                       related.title as title,
                       related.year as year,
                       related.authors as authors,
                       shared_entities,
                       sample_entities
                ORDER BY shared_entities DESC
                LIMIT $limit
                """

                result = session.run(
                    cypher_query,
                    paper_key=paper_key,
                    limit=limit
                )

                related_papers = []
                for record in result:
                    related_papers.append({
                        "item_key": record["item_key"],
                        "title": record["title"],
                        "year": record["year"],
                        "authors": record["authors"],
                        "shared_entities": record["shared_entities"],
                        "sample_entities": record["sample_entities"]
                    })

                logger.info(f"Found {len(related_papers)} related papers for: {paper_key}")
                return related_papers

        except Exception as e:
            logger.error(f"Error finding related papers: {e}")
            return []

    def get_graph_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the knowledge graph.

        Returns:
            Dictionary with node counts, relationship counts, etc.
        """
        try:
            with self.driver.session(database=self.neo4j_database) as session:
                # Count papers
                paper_count = session.run("MATCH (p:Paper) RETURN count(p) as count").single()["count"]

                # Count entities by type
                entity_counts = {}
                result = session.run("""
                    MATCH (n)
                    WHERE NOT n:Paper
                    RETURN labels(n)[0] as type, count(n) as count
                """)
                for record in result:
                    entity_counts[record["type"]] = record["count"]

                # Count relationships
                rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]

                return {
                    "papers": paper_count,
                    "entities": entity_counts,
                    "total_entities": sum(entity_counts.values()),
                    "relationships": rel_count
                }

        except Exception as e:
            logger.error(f"Error getting graph statistics: {e}")
            return {"error": str(e)}


def create_neo4j_graphrag_client(config_path: Optional[str] = None) -> Optional[Neo4jGraphRAGClient]:
    """
    Create a Neo4j GraphRAG client from configuration.

    Args:
        config_path: Path to configuration file

    Returns:
        Configured Neo4jGraphRAGClient instance or None if disabled
    """
    # Default configuration
    config = {
        "enabled": False,
        "neo4j_uri": "neo4j://localhost:7687",
        "neo4j_user": "neo4j",
        "neo4j_password": "",
        "neo4j_database": "neo4j",
        "llm_model": "gpt-4o-mini"
    }

    # Load from config file
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)
                neo4j_config = file_config.get("neo4j_graphrag", {})
                config.update(neo4j_config)
        except Exception as e:
            logger.warning(f"Error loading Neo4j config: {e}")

    # Check if enabled
    if not config.get("enabled", False):
        logger.info("Neo4j GraphRAG is disabled in configuration")
        return None

    # Load OpenAI API key from environment
    openai_api_key = os.getenv("OPENAI_API_KEY")

    try:
        return Neo4jGraphRAGClient(
            neo4j_uri=config["neo4j_uri"],
            neo4j_user=config["neo4j_user"],
            neo4j_password=config["neo4j_password"],
            neo4j_database=config["neo4j_database"],
            llm_model=config["llm_model"],
            openai_api_key=openai_api_key
        )
    except Exception as e:
        logger.error(f"Failed to create Neo4j GraphRAG client: {e}")
        return None
