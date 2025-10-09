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
from neo4j_graphrag.generation.prompts import ERExtractionTemplate
from neo4j_graphrag.experimental.pipeline.kg_builder import LexicalGraphConfig

logger = logging.getLogger(__name__)


# Define explicit schema for research papers
RESEARCH_PAPER_SCHEMA = [
    # Entity type definitions
    {
        "label": "Person",
        "properties": [
            {"name": "name", "type": "STRING"},
            {"name": "affiliation", "type": "STRING"}
        ]
    },
    {
        "label": "Institution",
        "properties": [
            {"name": "name", "type": "STRING"},
            {"name": "country", "type": "STRING"}
        ]
    },
    {
        "label": "Concept",
        "properties": [
            {"name": "name", "type": "STRING"},
            {"name": "description", "type": "STRING"}
        ]
    },
    {
        "label": "Method",
        "properties": [
            {"name": "name", "type": "STRING"},
            {"name": "description", "type": "STRING"}
        ]
    },
    {
        "label": "Dataset",
        "properties": [
            {"name": "name", "type": "STRING"},
            {"name": "size", "type": "STRING"}
        ]
    },
    {
        "label": "Theory",
        "properties": [
            {"name": "name", "type": "STRING"},
            {"name": "description", "type": "STRING"}
        ]
    }
]

# Define valid relationships between entities
RESEARCH_PAPER_RELATIONS = [
    {"type": "AUTHORED_BY", "source": "Paper", "target": "Person"},
    {"type": "AFFILIATED_WITH", "source": "Person", "target": "Institution"},
    {"type": "USES_METHOD", "source": "Paper", "target": "Method"},
    {"type": "USES_DATASET", "source": "Paper", "target": "Dataset"},
    {"type": "APPLIES_THEORY", "source": "Paper", "target": "Theory"},
    {"type": "DISCUSSES_CONCEPT", "source": "Paper", "target": "Concept"},
    {"type": "BUILDS_ON", "source": "Method", "target": "Method"},
    {"type": "EXTENDS", "source": "Theory", "target": "Theory"},
    {"type": "RELATED_TO", "source": "Concept", "target": "Concept"},
    {"type": "CITES", "source": "Paper", "target": "Paper"}
]

# Custom extraction prompt for research papers
RESEARCH_EXTRACTION_PROMPT = """
You are an expert research librarian extracting structured information from academic papers.

Your task is to identify:
1. **People**: Authors, researchers mentioned in the text
2. **Institutions**: Universities, research labs, organizations
3. **Concepts**: Key ideas, theories, frameworks discussed
4. **Methods**: Techniques, algorithms, approaches used
5. **Datasets**: Data sources, corpora, benchmarks mentioned
6. **Theories**: Theoretical frameworks or models

Extract entities and their relationships following these rules:

**Entity Extraction Guidelines**:
- Extract full names for people (not initials when full name is available)
- Use canonical names for institutions (e.g., "MIT" not "Massachusetts Institute of Technology")
- For concepts/methods, use the specific technical term from the paper
- Include brief descriptions when context is important

**Relationship Extraction Guidelines**:
- AUTHORED_BY: Connect paper to its authors
- AFFILIATED_WITH: Connect authors to their institutions
- USES_METHOD: Connect paper to methods it employs
- USES_DATASET: Connect paper to datasets it uses
- APPLIES_THEORY: Connect paper to theories it applies
- DISCUSSES_CONCEPT: Connect paper to concepts it discusses
- BUILDS_ON: Connect methods that extend other methods
- EXTENDS: Connect theories that extend other theories
- RELATED_TO: Connect related concepts
- CITES: Connect papers that cite each other (when mentioned)

Return result as JSON using this exact format:
{{"nodes": [{{"id": "0", "label": "Person", "properties": {{"name": "John Smith", "affiliation": "MIT"}}}}],
"relationships": [{{"type": "AUTHORED_BY", "start_node_id": "1", "end_node_id": "0"}}]}}

Use only the node and relationship types provided in the schema: {schema}

Important JSON rules:
- Assign unique string IDs to each node
- Reuse IDs to define relationships
- Property names in double quotes
- No backticks, no markdown formatting
- Return ONLY the JSON object

Input text:

{text}
"""


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

        # Initialize database schema on first connection
        self._initialize_schema()

    def _initialize_schema(self):
        """Initialize database schema with indexes and constraints."""
        try:
            with self.driver.session(database=self.neo4j_database) as session:
                # Create uniqueness constraint on Paper.item_key
                session.run("""
                    CREATE CONSTRAINT paper_item_key_unique IF NOT EXISTS
                    FOR (p:Paper) REQUIRE p.item_key IS UNIQUE
                """)

                # Create index on Paper.title for faster text searches
                session.run("""
                    CREATE INDEX paper_title_idx IF NOT EXISTS
                    FOR (p:Paper) ON (p.title)
                """)

                # Create index on Paper.year for temporal queries
                session.run("""
                    CREATE INDEX paper_year_idx IF NOT EXISTS
                    FOR (p:Paper) ON (p.year)
                """)

                # Create indexes for common entity types
                for entity_type in ["Person", "Institution", "Concept", "Method", "Dataset", "Theory"]:
                    session.run(f"""
                        CREATE INDEX {entity_type.lower()}_name_idx IF NOT EXISTS
                        FOR (e:{entity_type}) ON (e.name)
                    """)

                # Create full-text search index on Paper titles and abstracts
                session.run("""
                    CREATE FULLTEXT INDEX paper_fulltext IF NOT EXISTS
                    FOR (p:Paper) ON EACH [p.title, p.abstract]
                """)

                # Create full-text search index on entity names
                session.run("""
                    CREATE FULLTEXT INDEX entity_fulltext IF NOT EXISTS
                    FOR (e:Person|Institution|Concept|Method|Dataset|Theory)
                    ON EACH [e.name, e.description]
                """)

                logger.info("Neo4j schema initialized with indexes and constraints")

        except Exception as e:
            logger.warning(f"Error initializing schema (may already exist): {e}")

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

            # Create custom extraction template with research-specific prompt
            extraction_template = ERExtractionTemplate(
                template=RESEARCH_EXTRACTION_PROMPT
            )

            # Configure lexical graph for keyword-based connections
            # Use keyword arguments instead of dict (Pydantic v2 compatibility)
            lexical_config = LexicalGraphConfig(
                chunk_id_property="id",
                chunk_text_property="text",
                chunk_embedding_property="embedding"
            )

            # Create knowledge graph pipeline with optimized settings
            kg_builder = SimpleKGPipeline(
                llm=self.llm,
                driver=self.driver,
                database=self.neo4j_database,
                embedder=self.embeddings,
                entities=["Person", "Institution", "Concept", "Method", "Dataset", "Theory"],
                relations=["AUTHORED_BY", "AFFILIATED_WITH", "USES_METHOD", "USES_DATASET",
                          "APPLIES_THEORY", "DISCUSSES_CONCEPT", "BUILDS_ON", "EXTENDS",
                          "RELATED_TO", "CITES"],
                potential_schema=RESEARCH_PAPER_SCHEMA + RESEARCH_PAPER_RELATIONS,
                from_pdf=False,
                prompt_template=extraction_template,
                perform_entity_resolution=True,  # Merge similar entities
                lexical_graph_config=lexical_config  # Enable keyword-based connections
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

    def add_papers_batch(self,
                        papers: List[Dict[str, Any]],
                        batch_size: int = 10) -> Dict[str, Any]:
        """
        Add multiple papers to the knowledge graph in batches.

        Args:
            papers: List of paper dictionaries with keys:
                   - paper_key, title, abstract, authors, year, chunks (optional)
            batch_size: Number of papers to process in parallel (default: 10)

        Returns:
            Dictionary with success/failure counts and details
        """
        results = {
            "total": len(papers),
            "successful": 0,
            "failed": 0,
            "errors": []
        }

        try:
            # Process papers in batches
            for i in range(0, len(papers), batch_size):
                batch = papers[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(papers) + batch_size - 1)//batch_size} ({len(batch)} papers)")

                # Build combined content for batch
                batch_content_parts = []
                for paper in batch:
                    content_parts = [f"Title: {paper['title']}"]

                    if paper.get('authors'):
                        content_parts.append(f"Authors: {', '.join(paper['authors'])}")
                    if paper.get('year'):
                        content_parts.append(f"Year: {paper['year']}")
                    if paper.get('abstract'):
                        content_parts.append(f"\nAbstract: {paper['abstract']}")
                    if paper.get('chunks'):
                        content_parts.append("\nKey Content:")
                        content_parts.extend(paper['chunks'][:2])  # Fewer chunks per paper in batch

                    batch_content_parts.append("\n\n=== PAPER ===\n\n" + "\n\n".join(content_parts))

                batch_content = "\n\n---\n\n".join(batch_content_parts)

                # Create extraction template
                extraction_template = ERExtractionTemplate(template=RESEARCH_EXTRACTION_PROMPT)
                lexical_config = LexicalGraphConfig({
                    "id": "__Entity__",
                    "label": "__Entity__",
                    "text": "text",
                    "embedding": "embedding"
                })

                # Create pipeline for batch
                kg_builder = SimpleKGPipeline(
                    llm=self.llm,
                    driver=self.driver,
                    database=self.neo4j_database,
                    embedder=self.embeddings,
                    entities=["Person", "Institution", "Concept", "Method", "Dataset", "Theory"],
                    relations=["AUTHORED_BY", "AFFILIATED_WITH", "USES_METHOD", "USES_DATASET",
                              "APPLIES_THEORY", "DISCUSSES_CONCEPT", "BUILDS_ON", "EXTENDS",
                              "RELATED_TO", "CITES"],
                    potential_schema=RESEARCH_PAPER_SCHEMA + RESEARCH_PAPER_RELATIONS,
                    from_pdf=False,
                    prompt_template=extraction_template,
                    perform_entity_resolution=True,
                    lexical_graph_config=lexical_config
                )

                # Add paper metadata nodes for batch
                with self.driver.session(database=self.neo4j_database) as session:
                    for paper in batch:
                        try:
                            session.run(
                                """
                                MERGE (p:Paper {item_key: $item_key})
                                SET p.title = $title,
                                    p.abstract = $abstract,
                                    p.year = $year,
                                    p.authors = $authors
                                """,
                                item_key=paper['paper_key'],
                                title=paper['title'],
                                abstract=paper.get('abstract', ''),
                                year=paper.get('year'),
                                authors=paper.get('authors', [])
                            )
                        except Exception as e:
                            logger.error(f"Error adding paper metadata for {paper['paper_key']}: {e}")
                            results["failed"] += 1
                            results["errors"].append({"paper_key": paper['paper_key'], "error": str(e)})
                            continue

                # Extract entities from batch content
                try:
                    kg_builder.run_async(text=batch_content)

                    # Link extracted entities to papers
                    with self.driver.session(database=self.neo4j_database) as session:
                        for paper in batch:
                            try:
                                session.run(
                                    """
                                    MATCH (p:Paper {item_key: $item_key})
                                    MATCH (e)
                                    WHERE e.id IS NOT NULL
                                    MERGE (p)-[:MENTIONS]->(e)
                                    """,
                                    item_key=paper['paper_key']
                                )
                                results["successful"] += 1
                                logger.info(f"Successfully added paper: {paper['title']}")
                            except Exception as e:
                                logger.error(f"Error linking entities for {paper['paper_key']}: {e}")
                                results["failed"] += 1
                                results["errors"].append({"paper_key": paper['paper_key'], "error": str(e)})

                except Exception as e:
                    logger.error(f"Error processing batch: {e}")
                    for paper in batch:
                        results["failed"] += 1
                        results["errors"].append({"paper_key": paper['paper_key'], "error": f"Batch error: {str(e)}"})

            logger.info(f"Batch processing complete: {results['successful']}/{results['total']} successful")
            return results

        except Exception as e:
            logger.error(f"Fatal error in batch processing: {e}")
            return {
                "status": "error",
                "error": str(e),
                **results
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

    # Load OpenAI API key from config file or environment
    openai_api_key = None
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)
                # Try to get from client_env first (where it's stored in config)
                openai_api_key = file_config.get("client_env", {}).get("OPENAI_API_KEY")
                # Also try from embedding_config as fallback
                if not openai_api_key:
                    openai_api_key = file_config.get("semantic_search", {}).get("embedding_config", {}).get("api_key")
        except Exception as e:
            logger.warning(f"Error loading OpenAI API key from config: {e}")

    # Fallback to environment variable
    if not openai_api_key:
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
