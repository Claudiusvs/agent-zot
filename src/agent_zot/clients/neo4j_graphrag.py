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


# Ollama LLM implementation for local entity extraction
class OllamaLLM(LLMInterface):
    """
    Ollama LLM implementation compatible with neo4j-graphrag.

    Provides free local entity/relationship extraction using Mistral 7B Instruct.
    """

    def __init__(self, model_name: str = "mistral:7b-instruct", base_url: str = "http://localhost:11434"):
        """
        Initialize Ollama LLM client.

        Args:
            model_name: Ollama model name (default: mistral:7b-instruct)
            base_url: Ollama API base URL (default: http://localhost:11434)
        """
        try:
            import ollama
            self.client = ollama.Client(host=base_url)
            self.model_name = model_name
            logger.info(f"Ollama LLM initialized with model: {model_name}")
        except ImportError:
            raise ImportError("ollama package is required for local LLM. Install with: pip install ollama")

    def invoke(self, input: str) -> Any:
        """
        Invoke the LLM with a prompt.

        Args:
            input: The prompt text

        Returns:
            LLM response with content attribute
        """
        response = self.client.generate(model=self.model_name, prompt=input)

        # Create response object with content attribute (neo4j-graphrag expects this structure)
        class OllamaResponse:
            def __init__(self, text):
                self.content = text

        return OllamaResponse(response['response'])


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
    },
    {
        "label": "Journal",
        "properties": [
            {"name": "name", "type": "STRING"},
            {"name": "publisher", "type": "STRING"}
        ]
    },
    {
        "label": "Field",
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
    {"type": "CITES", "source": "Paper", "target": "Paper"},
    {"type": "PUBLISHED_IN", "source": "Paper", "target": "Journal"},
    {"type": "BELONGS_TO_FIELD", "source": "Paper", "target": "Field"}
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
7. **Journals**: Publication venues (journals, conferences, proceedings)
8. **Fields**: Research domains or disciplines (e.g., "Machine Learning", "Neuroscience")

Extract entities and their relationships following these rules:

**Entity Extraction Guidelines**:
- Extract full names for people (not initials when full name is available)
- Use canonical names for institutions (e.g., "MIT" not "Massachusetts Institute of Technology")
- For concepts/methods, use the specific technical term from the paper
- For journals, extract the full official name (e.g., "Nature", "Proceedings of ACL")
- For fields, identify the primary research domain (e.g., "Computer Vision", "Quantum Physics")
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
- PUBLISHED_IN: Connect paper to the journal/venue where it was published
- BELONGS_TO_FIELD: Connect paper to its primary research field(s)

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
                 openai_api_key: Optional[str] = None,
                 ollama_base_url: str = "http://localhost:11434"):
        """
        Initialize Neo4j GraphRAG client with OpenAI or Ollama support.

        Args:
            neo4j_uri: Neo4j connection URI (e.g., neo4j://localhost:7687)
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            neo4j_database: Neo4j database name
            llm_model: Model for entity extraction. Use "ollama/" prefix for Ollama models (e.g., "ollama/mistral:7b-instruct")
            openai_api_key: OpenAI API key (required for OpenAI models)
            ollama_base_url: Ollama API base URL (default: http://localhost:11434)
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

        # Initialize LLM for entity extraction (OpenAI or Ollama)
        if llm_model.startswith("ollama/"):
            # Use Ollama for free local extraction
            ollama_model = llm_model.replace("ollama/", "")
            self.llm = OllamaLLM(model_name=ollama_model, base_url=ollama_base_url)
            logger.info(f"Using Ollama LLM: {ollama_model} (free, local)")

            # For Ollama, we still need OpenAI for embeddings (or could switch to sentence-transformers)
            api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
            if api_key:
                self.embeddings = OpenAIEmbeddings(
                    model="text-embedding-3-large",
                    api_key=api_key
                )
            else:
                logger.warning("No OpenAI API key provided - embeddings disabled for Ollama mode")
                self.embeddings = None

        else:
            # Use OpenAI
            api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API key required for OpenAI models")

            self.llm = OpenAILLM(
                model_name=llm_model,
                api_key=api_key
            )

            self.embeddings = OpenAIEmbeddings(
                model="text-embedding-3-large",
                api_key=api_key
            )
            logger.info(f"Using OpenAI LLM: {llm_model}")

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

    def find_citation_chain(self, paper_key: str, max_hops: int = 2, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find papers citing papers that cite the given paper (multi-hop citation analysis).

        Args:
            paper_key: Zotero item key of the starting paper
            max_hops: Maximum number of citation hops (default: 2)
            limit: Maximum number of papers to return per hop (default: 10)

        Returns:
            List of papers with citation hop distance and paths
        """
        try:
            with self.driver.session(database=self.neo4j_database) as session:
                # Cypher query for multi-hop citation traversal
                query = """
                MATCH path = (start:Paper {item_key: $paper_key})-[:CITES*1..%d]-(cited:Paper)
                WHERE start <> cited
                RETURN DISTINCT cited.item_key as item_key,
                       cited.title as title,
                       cited.year as year,
                       length(path) as hops,
                       [node in nodes(path) | node.title] as path_titles
                ORDER BY hops ASC, cited.year DESC
                LIMIT $limit
                """ % max_hops

                result = session.run(query, paper_key=paper_key, limit=limit)

                citation_chain = []
                for record in result:
                    citation_chain.append({
                        "item_key": record["item_key"],
                        "title": record["title"],
                        "year": record["year"],
                        "citation_hops": record["hops"],
                        "citation_path": record["path_titles"]
                    })

                logger.info(f"Found {len(citation_chain)} papers in citation chain for: {paper_key}")
                return citation_chain

        except Exception as e:
            logger.error(f"Error finding citation chain: {e}")
            return []

    def find_related_concepts(self, concept: str, max_hops: int = 2, limit: int = 15) -> List[Dict[str, Any]]:
        """
        Find concepts related through intermediate concepts (concept propagation).

        Args:
            concept: Starting concept name
            max_hops: Maximum number of concept relationship hops (default: 2)
            limit: Maximum number of related concepts to return (default: 15)

        Returns:
            List of related concepts with relationship paths
        """
        try:
            with self.driver.session(database=self.neo4j_database) as session:
                # Find concepts related through DISCUSSES_CONCEPT relationships
                query = """
                MATCH path = (start:Concept {name: $concept})<-[:DISCUSSES_CONCEPT*1..%d]-(p:Paper)-[:DISCUSSES_CONCEPT]->(related:Concept)
                WHERE start <> related
                WITH related, collect(DISTINCT p.title) as papers, length(path) as hops
                RETURN DISTINCT related.name as concept_name,
                       hops,
                       papers[0..3] as sample_papers,
                       size(papers) as paper_count
                ORDER BY paper_count DESC, hops ASC
                LIMIT $limit
                """ % max_hops

                result = session.run(query, concept=concept, limit=limit)

                related_concepts = []
                for record in result:
                    related_concepts.append({
                        "concept": record["concept_name"],
                        "relationship_hops": record["hops"],
                        "paper_count": record["paper_count"],
                        "sample_papers": record["sample_papers"]
                    })

                logger.info(f"Found {len(related_concepts)} related concepts for: {concept}")
                return related_concepts

        except Exception as e:
            logger.error(f"Error finding related concepts: {e}")
            return []

    def find_collaborator_network(self, author: str, max_hops: int = 2, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Find collaborators of collaborators (co-authorship network).

        Args:
            author: Author name to start from
            max_hops: Maximum number of collaboration hops (default: 2)
            limit: Maximum number of collaborators to return (default: 20)

        Returns:
            List of authors with collaboration distance and shared papers
        """
        try:
            with self.driver.session(database=self.neo4j_database) as session:
                # Find collaborators through co-authorship
                query = """
                MATCH path = (start:Person {name: $author})<-[:AUTHORED_BY*1..%d]-(p:Paper)-[:AUTHORED_BY]->(collab:Person)
                WHERE start <> collab
                WITH collab, collect(DISTINCT p.title) as papers, length(path) as hops
                RETURN DISTINCT collab.name as author_name,
                       hops,
                       papers[0..3] as sample_papers,
                       size(papers) as collaboration_count
                ORDER BY collaboration_count DESC, hops ASC
                LIMIT $limit
                """ % max_hops

                result = session.run(query, author=author, limit=limit)

                collaborators = []
                for record in result:
                    collaborators.append({
                        "author": record["author_name"],
                        "collaboration_hops": record["hops"],
                        "collaboration_count": record["collaboration_count"],
                        "sample_papers": record["sample_papers"]
                    })

                logger.info(f"Found {len(collaborators)} collaborators for: {author}")
                return collaborators

        except Exception as e:
            logger.error(f"Error finding collaborator network: {e}")
            return []

    def find_seminal_papers(self, field: str = None, top_n: int = 10) -> List[Dict[str, Any]]:
        """
        Find most influential papers using PageRank algorithm on citation graph.

        Args:
            field: Optional field name to filter papers (default: None, all fields)
            top_n: Number of top papers to return (default: 10)

        Returns:
            List of papers ranked by influence (PageRank score)
        """
        try:
            with self.driver.session(database=self.neo4j_database) as session:
                # Build query with optional field filter
                if field:
                    # Filter by field if specified
                    query = """
                    CALL gds.graph.project(
                        'citationGraph',
                        'Paper',
                        {
                            CITES: {
                                orientation: 'REVERSE'
                            }
                        }
                    )
                    YIELD graphName

                    CALL gds.pageRank.stream('citationGraph')
                    YIELD nodeId, score
                    WITH gds.util.asNode(nodeId) AS paper, score
                    WHERE EXISTS {
                        MATCH (paper)-[:BELONGS_TO_FIELD]->(f:Field {name: $field})
                    }
                    RETURN paper.item_key as item_key,
                           paper.title as title,
                           paper.year as year,
                           score
                    ORDER BY score DESC
                    LIMIT $top_n
                    """
                    # Note: This is a simplified version. In production, you'd want to:
                    # 1. Check if graph exists before projecting
                    # 2. Drop graph after use
                    # 3. Use gds.graph.exists() to avoid re-creating
                else:
                    # All papers PageRank
                    query = """
                    MATCH (p:Paper)
                    WITH p, size([(p)<-[:CITES]-() | 1]) as citation_count
                    RETURN p.item_key as item_key,
                           p.title as title,
                           p.year as year,
                           citation_count as score
                    ORDER BY score DESC
                    LIMIT $top_n
                    """
                    # Simplified version using citation count as proxy for PageRank
                    # Full GDS PageRank requires Neo4j Graph Data Science library

                params = {"top_n": top_n}
                if field:
                    params["field"] = field

                result = session.run(query, **params)

                seminal_papers = []
                for record in result:
                    seminal_papers.append({
                        "item_key": record["item_key"],
                        "title": record["title"],
                        "year": record["year"],
                        "influence_score": float(record["score"])
                    })

                logger.info(f"Found {len(seminal_papers)} seminal papers" + (f" in field: {field}" if field else ""))
                return seminal_papers

        except Exception as e:
            logger.error(f"Error finding seminal papers: {e}")
            # Fallback to simple citation count if GDS not available
            logger.info("Falling back to citation count ranking")
            try:
                with self.driver.session(database=self.neo4j_database) as session:
                    fallback_query = """
                    MATCH (p:Paper)
                    WITH p, size([(p)<-[:CITES]-() | 1]) as citation_count
                    WHERE citation_count > 0
                    RETURN p.item_key as item_key,
                           p.title as title,
                           p.year as year,
                           citation_count as score
                    ORDER BY score DESC
                    LIMIT $top_n
                    """
                    result = session.run(fallback_query, top_n=top_n)

                    seminal_papers = []
                    for record in result:
                        seminal_papers.append({
                            "item_key": record["item_key"],
                            "title": record["title"],
                            "year": record["year"],
                            "influence_score": float(record["score"])
                        })
                    return seminal_papers
            except Exception as fallback_error:
                logger.error(f"Fallback query also failed: {fallback_error}")
                return []

    def track_topic_evolution(self, concept: str, start_year: int, end_year: int) -> Dict[str, Any]:
        """
        Track how a topic/concept has evolved over time with paper counts and key entities.

        Args:
            concept: Concept name to track
            start_year: Start year for analysis
            end_year: End year for analysis

        Returns:
            Dictionary with temporal evolution data (yearly counts, related entities, trend)
        """
        try:
            with self.driver.session(database=self.neo4j_database) as session:
                # Get yearly paper counts for the concept
                temporal_query = """
                MATCH (c:Concept {name: $concept})<-[:DISCUSSES_CONCEPT]-(p:Paper)
                WHERE p.year >= $start_year AND p.year <= $end_year
                WITH p.year as year, count(p) as paper_count, collect(p.title)[0..3] as sample_papers
                RETURN year, paper_count, sample_papers
                ORDER BY year ASC
                """

                result = session.run(temporal_query, concept=concept, start_year=start_year, end_year=end_year)

                yearly_data = []
                total_papers = 0
                for record in result:
                    yearly_data.append({
                        "year": record["year"],
                        "paper_count": record["paper_count"],
                        "sample_papers": record["sample_papers"]
                    })
                    total_papers += record["paper_count"]

                # Get related concepts that emerged over time
                related_concepts_query = """
                MATCH (c:Concept {name: $concept})<-[:DISCUSSES_CONCEPT]-(p:Paper)-[:DISCUSSES_CONCEPT]->(related:Concept)
                WHERE p.year >= $start_year AND p.year <= $end_year AND c <> related
                WITH related.name as concept_name, count(DISTINCT p) as co_occurrence_count, min(p.year) as first_year
                RETURN concept_name, co_occurrence_count, first_year
                ORDER BY co_occurrence_count DESC
                LIMIT 10
                """

                related_result = session.run(related_concepts_query, concept=concept, start_year=start_year, end_year=end_year)

                related_concepts = []
                for record in related_result:
                    related_concepts.append({
                        "concept": record["concept_name"],
                        "co_occurrence_count": record["co_occurrence_count"],
                        "first_appeared": record["first_year"]
                    })

                # Calculate trend (simple linear: increasing, stable, decreasing)
                trend = "stable"
                if len(yearly_data) >= 3:
                    first_half = sum(d["paper_count"] for d in yearly_data[:len(yearly_data)//2])
                    second_half = sum(d["paper_count"] for d in yearly_data[len(yearly_data)//2:])
                    if second_half > first_half * 1.5:
                        trend = "increasing"
                    elif second_half < first_half * 0.67:
                        trend = "decreasing"

                logger.info(f"Tracked topic evolution for '{concept}': {total_papers} papers from {start_year}-{end_year}")

                return {
                    "concept": concept,
                    "time_range": f"{start_year}-{end_year}",
                    "total_papers": total_papers,
                    "yearly_breakdown": yearly_data,
                    "related_concepts": related_concepts,
                    "trend": trend
                }

        except Exception as e:
            logger.error(f"Error tracking topic evolution: {e}")
            return {"error": str(e)}

    def analyze_publication_venues(self, field: str = None, top_n: int = 10) -> List[Dict[str, Any]]:
        """
        Find most common publication venues (journals/conferences) for a field or across all papers.

        Args:
            field: Optional field name to filter by (default: None, all fields)
            top_n: Number of top venues to return (default: 10)

        Returns:
            List of venues with paper counts and sample titles
        """
        try:
            with self.driver.session(database=self.neo4j_database) as session:
                if field:
                    # Filter by field
                    query = """
                    MATCH (p:Paper)-[:PUBLISHED_IN]->(j:Journal)
                    WHERE EXISTS {
                        MATCH (p)-[:BELONGS_TO_FIELD]->(f:Field {name: $field})
                    }
                    WITH j.name as venue, count(p) as paper_count, collect(p.title)[0..3] as sample_papers
                    RETURN venue, paper_count, sample_papers
                    ORDER BY paper_count DESC
                    LIMIT $top_n
                    """
                else:
                    # All venues
                    query = """
                    MATCH (p:Paper)-[:PUBLISHED_IN]->(j:Journal)
                    WITH j.name as venue, count(p) as paper_count, collect(p.title)[0..3] as sample_papers
                    RETURN venue, paper_count, sample_papers
                    ORDER BY paper_count DESC
                    LIMIT $top_n
                    """

                params = {"top_n": top_n}
                if field:
                    params["field"] = field

                result = session.run(query, **params)

                venues = []
                for record in result:
                    venues.append({
                        "venue": record["venue"],
                        "paper_count": record["paper_count"],
                        "sample_papers": record["sample_papers"]
                    })

                logger.info(f"Found {len(venues)} top publication venues" + (f" in field: {field}" if field else ""))
                return venues

        except Exception as e:
            logger.error(f"Error analyzing publication venues: {e}")
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

    def export_graph_to_graphml(self, output_file: str, node_types: List[str] = None, max_nodes: int = None) -> Dict[str, Any]:
        """
        Export Neo4j graph to GraphML format for visualization in Gephi/Cytoscape.

        Args:
            output_file: Path to output .graphml file
            node_types: List of node types to include (default: all types)
            max_nodes: Maximum number of nodes to export (default: all)

        Returns:
            Dictionary with export statistics
        """
        try:
            # Build node filter query
            node_filter = ""
            if node_types:
                labels_str = " OR ".join([f"n:{label}" for label in node_types])
                node_filter = f"WHERE {labels_str}"

            # Build limit clause
            limit_clause = f"LIMIT {max_nodes}" if max_nodes else ""

            # Export query
            export_query = f"""
            MATCH (n){node_filter}
            WITH n {limit_clause}
            MATCH (n)-[r]->(m)
            RETURN n, r, m
            """

            with self.driver.session(database=self.neo4j_database) as session:
                result = session.run(export_query)

                # Build GraphML manually
                nodes = {}
                edges = []

                for record in result:
                    n = record["n"]
                    m = record["m"]
                    r = record["r"]

                    # Add nodes
                    n_id = n.element_id
                    if n_id not in nodes:
                        nodes[n_id] = {
                            "id": n_id,
                            "labels": list(n.labels),
                            "properties": dict(n.items())
                        }

                    m_id = m.element_id
                    if m_id not in nodes:
                        nodes[m_id] = {
                            "id": m_id,
                            "labels": list(m.labels),
                            "properties": dict(m.items())
                        }

                    # Add edge
                    edges.append({
                        "source": n_id,
                        "target": m_id,
                        "type": r.type,
                        "properties": dict(r.items())
                    })

                # Write GraphML file
                import xml.etree.ElementTree as ET
                from xml.dom import minidom

                graphml = ET.Element("graphml", {
                    "xmlns": "http://graphml.graphdrawing.org/xmlns",
                    "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance"
                })

                # Define property keys
                key_id = 0
                property_keys = {}

                # Node property keys
                for node in nodes.values():
                    for prop_name in node["properties"].keys():
                        if prop_name not in property_keys:
                            key_elem = ET.SubElement(graphml, "key", {
                                "id": f"d{key_id}",
                                "for": "node",
                                "attr.name": prop_name,
                                "attr.type": "string"
                            })
                            property_keys[prop_name] = f"d{key_id}"
                            key_id += 1

                # Add labels key
                if "labels" not in property_keys:
                    ET.SubElement(graphml, "key", {
                        "id": f"d{key_id}",
                        "for": "node",
                        "attr.name": "labels",
                        "attr.type": "string"
                    })
                    property_keys["labels"] = f"d{key_id}"
                    key_id += 1

                # Edge type key
                ET.SubElement(graphml, "key", {
                    "id": "edge_type",
                    "for": "edge",
                    "attr.name": "type",
                    "attr.type": "string"
                })

                # Create graph element
                graph_elem = ET.SubElement(graphml, "graph", {
                    "id": "ZoteroKnowledgeGraph",
                    "edgedefault": "directed"
                })

                # Add nodes
                for node_id, node_data in nodes.items():
                    node_elem = ET.SubElement(graph_elem, "node", {"id": node_id})

                    # Add labels
                    labels_elem = ET.SubElement(node_elem, "data", {"key": property_keys["labels"]})
                    labels_elem.text = ",".join(node_data["labels"])

                    # Add properties
                    for prop_name, prop_value in node_data["properties"].items():
                        if prop_name in property_keys:
                            data_elem = ET.SubElement(node_elem, "data", {"key": property_keys[prop_name]})
                            data_elem.text = str(prop_value)

                # Add edges
                for i, edge_data in enumerate(edges):
                    edge_elem = ET.SubElement(graph_elem, "edge", {
                        "id": f"e{i}",
                        "source": edge_data["source"],
                        "target": edge_data["target"]
                    })

                    type_elem = ET.SubElement(edge_elem, "data", {"key": "edge_type"})
                    type_elem.text = edge_data["type"]

                # Pretty print and write
                xml_str = ET.tostring(graphml, encoding='unicode')
                dom = minidom.parseString(xml_str)
                pretty_xml = dom.toprettyxml(indent="  ")

                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(pretty_xml)

                stats = {
                    "nodes_exported": len(nodes),
                    "edges_exported": len(edges),
                    "output_file": output_file
                }

                logger.info(f"Exported {len(nodes)} nodes and {len(edges)} edges to {output_file}")
                return stats

        except Exception as e:
            logger.error(f"Error exporting graph to GraphML: {e}")
            raise


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
