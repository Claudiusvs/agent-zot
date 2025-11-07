#!/usr/bin/env python3
"""
Extract entities for papers that have chunks but no entity extraction.

This script finds papers in Neo4j that have HAS_CHUNK relationships but no
CONTAINS_ENTITY relationships, then runs entity extraction for those papers.

Usage:
    python scripts/extract_missing_entities.py [--dry-run] [--batch-size N]
"""

import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import argparse
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import GraphDatabase
from neo4j_graphrag.experimental.components.types import LexicalGraphConfig
from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline
from neo4j_graphrag.generation.prompts import ERExtractionTemplate
from neo4j_graphrag.llm import LLMInterface
from agent_zot.clients.neo4j_graphrag import RESEARCH_EXTRACTION_PROMPT


# Ollama LLM implementation for local entity extraction
class OllamaLLM(LLMInterface):
    """
    Ollama LLM implementation compatible with neo4j-graphrag.

    Provides free local entity/relationship extraction.
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

    async def ainvoke(self, input: str) -> Any:
        """
        Async invoke the LLM with a prompt (required by neo4j-graphrag).

        Args:
            input: The prompt text

        Returns:
            LLM response with content attribute
        """
        # Ollama Python client doesn't have native async support yet,
        # so we'll use the sync method (wrapped in async for compatibility)
        return self.invoke(input)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_papers_without_entities(neo4j_uri: str, neo4j_user: str, neo4j_password: str) -> List[Dict[str, Any]]:
    """
    Find papers that have chunks but no entity extraction.

    Returns list of dicts with:
    - item_key: Paper key
    - title: Paper title
    - chunk_count: Number of chunks
    """
    logger.info("Scanning Neo4j for papers without entity extraction...")

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    with driver.session() as session:
        # Find papers with chunks but no FROM_CHUNK relationships (correct pattern)
        result = session.run(
            """
            MATCH (p:Paper)-[:HAS_CHUNK]->(c:Chunk)
            WHERE NOT (c)<-[:FROM_CHUNK]-()
            WITH p, count(c) as chunk_count
            RETURN DISTINCT p.item_key as key,
                   p.title as title,
                   p.abstract as abstract,
                   p.year as year,
                   p.authors as authors,
                   chunk_count
            ORDER BY p.item_key
            """
        )

        papers = []
        for record in result:
            papers.append({
                "item_key": record["key"],
                "title": record["title"],
                "abstract": record["abstract"] or "",
                "year": record["year"],
                "authors": record["authors"] or [],
                "chunk_count": record["chunk_count"]
            })

    driver.close()
    logger.info(f"Found {len(papers)} papers without entity extraction")

    return papers


def get_chunks_for_paper(driver, paper_key: str) -> List[Dict[str, Any]]:
    """
    Get all chunks for a paper from Neo4j.

    Returns list of chunk dicts with:
    - chunk_id: Chunk ID
    - text: Chunk text
    - headings: Chunk headings
    """
    with driver.session() as session:
        result = session.run(
            """
            MATCH (p:Paper {item_key: $paper_key})-[:HAS_CHUNK]->(c:Chunk)
            RETURN c.chunk_id as chunk_id,
                   c.qdrant_point_id as qdrant_point_id,
                   c.headings as headings
            ORDER BY c.chunk_id
            """,
            paper_key=paper_key
        )

        chunks = []
        for record in result:
            chunks.append({
                "chunk_id": record["chunk_id"],
                "qdrant_point_id": record["qdrant_point_id"],
                "headings": record["headings"] or []
            })

        return chunks


def get_chunk_text_from_qdrant(qdrant_client, collection_name: str, qdrant_point_id: str) -> str:
    """Get chunk text from Qdrant point."""
    try:
        from qdrant_client import QdrantClient

        point = qdrant_client.retrieve(
            collection_name=collection_name,
            ids=[qdrant_point_id],
            with_payload=True,
            with_vectors=False
        )

        if point and len(point) > 0:
            return point[0].payload.get('document', '')
        return ''
    except Exception as e:
        logger.warning(f"Could not retrieve text for {qdrant_point_id}: {e}")
        return ''


def extract_entities_for_papers(
    driver,
    qdrant_client,
    qdrant_collection: str,
    llm,
    embeddings,
    entity_types: List[str],
    relation_types: List[str],
    papers: List[Dict[str, Any]],
    batch_size: int
) -> Dict[str, Any]:
    """
    Run entity extraction for papers without entities.

    This implements the same entity extraction logic as add_papers_with_chunks.
    """
    results = {
        "total": len(papers),
        "successful": 0,
        "failed": 0,
        "total_entities": 0,
        "errors": []
    }

    logger.info(f"Extracting entities for {len(papers)} papers in batches of {batch_size}...")

    for i in range(0, len(papers), batch_size):
        batch = papers[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(papers) + batch_size - 1) // batch_size

        logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} papers)")

        for paper in batch:
            paper_key = paper['item_key']

            try:
                # Get chunks from Neo4j
                chunks = get_chunks_for_paper(driver, paper_key)

                if not chunks:
                    logger.warning(f"Paper {paper_key}: No chunks found")
                    results["failed"] += 1
                    results["errors"].append({
                        "paper_key": paper_key,
                        "error": "No chunks found"
                    })
                    continue

                logger.info(f"  Processing {paper_key}: {paper['title'][:60]}... ({len(chunks)} chunks)")

                # Extract entities per chunk (same as add_papers_with_chunks Step 3)
                entities_extracted = 0

                for chunk in chunks:
                    # Get chunk text from Qdrant
                    chunk_text = get_chunk_text_from_qdrant(
                        qdrant_client,
                        qdrant_collection,
                        chunk['qdrant_point_id']
                    )

                    if not chunk_text.strip():
                        logger.warning(f"  Chunk {chunk['chunk_id']} has no text - skipping")
                        continue

                    # Create extraction template
                    extraction_template = ERExtractionTemplate(template=RESEARCH_EXTRACTION_PROMPT)
                    # Use default LexicalGraphConfig (Pydantic v2 compatible - FIXED!)
                    lexical_config = LexicalGraphConfig()

                    # Create pipeline for this chunk
                    chunk_pipeline_kwargs = {
                        "llm": llm,
                        "driver": driver,
                        "entities": entity_types,
                        "relations": relation_types,
                        "from_pdf": False,
                        "prompt_template": extraction_template,
                        "perform_entity_resolution": True,
                        "lexical_graph_config": lexical_config
                    }

                    # Only add embedder if available
                    if embeddings is not None:
                        chunk_pipeline_kwargs["embedder"] = embeddings

                    kg_builder = SimpleKGPipeline(**chunk_pipeline_kwargs)

                    # Extract entities from this chunk
                    # SimpleKGPipeline automatically creates entity nodes and FROM_CHUNK relationships
                    try:
                        kg_builder.run_async(text=chunk_text)
                        entities_extracted += 1

                    except Exception as e:
                        logger.error(f"  Error extracting entities for chunk {chunk['chunk_id']}: {e}")
                        continue

                results["successful"] += 1
                results["total_entities"] += entities_extracted
                logger.info(f"  ✓ Extracted entities from {entities_extracted}/{len(chunks)} chunks for {paper_key}")

            except Exception as e:
                logger.error(f"Error processing paper {paper_key}: {e}")
                results["failed"] += 1
                results["errors"].append({
                    "paper_key": paper_key,
                    "error": str(e)
                })
                import traceback
                traceback.print_exc()
                continue

    return results


def main():
    parser = argparse.ArgumentParser(description="Extract entities for papers without entity extraction")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--batch-size", type=int, default=5, help="Batch size for entity extraction (default: 5)")
    parser.add_argument("--config", type=str, help="Path to config file")
    parser.add_argument("--limit", type=int, help="Limit number of papers to process (for testing)")
    args = parser.parse_args()

    start_time = datetime.now()

    # Load config
    if args.config:
        config_path = Path(args.config)
    else:
        config_path = Path.home() / ".config" / "agent-zot" / "config.json"

    logger.info(f"Loading config from {config_path}")
    with open(config_path, 'r') as f:
        config = json.load(f)

    neo4j_config = config.get("neo4j_graphrag", {})
    neo4j_uri = neo4j_config.get("neo4j_uri", "neo4j://127.0.0.1:7687")
    neo4j_user = neo4j_config.get("neo4j_user", "neo4j")
    neo4j_password = neo4j_config.get("neo4j_password", "demodemo")

    qdrant_config = config.get("semantic_search", {})
    qdrant_url = qdrant_config.get("qdrant_url", "http://localhost:6333")
    qdrant_collection = qdrant_config.get("collection_name", "zotero_library_qdrant")

    # Find papers without entities
    logger.info("=" * 80)
    logger.info("STEP 1: Finding papers without entity extraction")
    logger.info("=" * 80)

    papers = find_papers_without_entities(neo4j_uri, neo4j_user, neo4j_password)

    if not papers:
        logger.info("\n✅ All papers with chunks have entity extraction. Nothing to do!")
        return 0

    # Apply limit if specified
    if args.limit:
        papers = papers[:args.limit]
        logger.info(f"Limited to first {len(papers)} papers for testing")

    logger.info(f"\nFound {len(papers)} papers needing entity extraction:")
    logger.info(f"  Average chunks per paper: {sum(p['chunk_count'] for p in papers) / len(papers):.1f}")

    # Save list
    output_file = Path("/tmp/papers_without_entities.json")
    with open(output_file, 'w') as f:
        json.dump([p["item_key"] for p in papers], f, indent=2)
    logger.info(f"Saved paper keys to {output_file}")

    if args.dry_run:
        logger.info("\n🔍 DRY RUN MODE - No changes will be made")
        logger.info(f"\nWould extract entities for {len(papers)} papers:")
        for i, paper in enumerate(papers[:20]):
            logger.info(f"  {i+1}. {paper['item_key']}: {paper['title'][:60]}... ({paper['chunk_count']} chunks)")
        if len(papers) > 20:
            logger.info(f"  ... and {len(papers) - 20} more")
        return 0

    # Extract entities
    logger.info("\n" + "=" * 80)
    logger.info("STEP 2: Extracting entities")
    logger.info("=" * 80)

    # Initialize clients
    from qdrant_client import QdrantClient
    qdrant_client = QdrantClient(url=qdrant_url)

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    # Initialize LLM
    llm_model = neo4j_config.get("llm_model", "gpt-4o-mini")
    openai_api_key = config.get("openai_api_key") or config.get("openai", {}).get("api_key")

    if llm_model.startswith("gpt-"):
        if not openai_api_key:
            logger.error("OpenAI API key required for OpenAI models")
            return 1
        from neo4j_graphrag.llm import OpenAILLM
        llm = OpenAILLM(model_name=llm_model, api_key=openai_api_key)
        embeddings = None  # Optional
    elif llm_model.startswith("ollama/"):
        model_name = llm_model.replace("ollama/", "")
        ollama_base_url = neo4j_config.get("ollama_base_url", "http://localhost:11434")
        llm = OllamaLLM(model_name=model_name, base_url=ollama_base_url)
        embeddings = None  # Optional
    else:
        logger.error(f"Unsupported LLM model: {llm_model}")
        return 1

    # Entity and relation types
    entity_types = ["Person", "Organization", "Concept", "Method", "Dataset", "Metric"]
    relation_types = ["USES", "PROPOSES", "IMPROVES", "EVALUATES", "CITES"]

    try:
        results = extract_entities_for_papers(
            driver,
            qdrant_client,
            qdrant_collection,
            llm,
            embeddings,
            entity_types,
            relation_types,
            papers,
            args.batch_size
        )

        logger.info("\n" + "=" * 80)
        logger.info("RESULTS")
        logger.info("=" * 80)
        logger.info(f"✅ Successfully processed: {results['successful']} papers")
        logger.info(f"   Total chunk extractions: {results['total_entities']}")
        logger.info(f"❌ Failed: {results['failed']} papers")

        if results['errors']:
            logger.warning(f"\nErrors encountered:")
            for error in results['errors'][:10]:
                logger.warning(f"  - {error['paper_key']}: {error['error']}")
            if len(results['errors']) > 10:
                logger.warning(f"  ... and {len(results['errors']) - 10} more errors")

        duration = datetime.now() - start_time
        logger.info(f"\n⏱️  Total duration: {duration}")

        # Save results
        results_file = Path("/tmp/entity_extraction_results.json")
        with open(results_file, 'w') as f:
            json.dump({
                "start_time": start_time.isoformat(),
                "duration": str(duration),
                "papers_processed": len(papers),
                "result": results
            }, f, indent=2)
        logger.info(f"Saved results to {results_file}")

        return 0 if results['failed'] == 0 else 1

    except Exception as e:
        logger.error(f"\n❌ Error during entity extraction: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        driver.close()


if __name__ == "__main__":
    sys.exit(main())
