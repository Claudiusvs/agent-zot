#!/usr/bin/env python3
"""
Sync missing papers from Qdrant to Neo4j - SIMPLIFIED VERSION

This script uses data ALREADY IN QDRANT to populate Neo4j, without touching
Zotero or the parse cache. Much faster and simpler!

Usage:
    python scripts/sync_missing_papers_to_neo4j_v2.py [--dry-run] [--batch-size N]
"""

import sys
import json
import logging
from pathlib import Path
from typing import Set, List, Dict, Any
import argparse
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from neo4j import GraphDatabase
from agent_zot.clients.neo4j_graphrag import Neo4jGraphRAGClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_papers_in_qdrant(qdrant_url: str, collection_name: str) -> Set[str]:
    """Get all unique paper keys that have chunks in Qdrant."""
    logger.info("Scanning Qdrant for papers with chunks...")

    client = QdrantClient(url=qdrant_url)
    chunk_parents = set()
    offset = None
    total_scanned = 0

    while True:
        results = client.scroll(
            collection_name=collection_name,
            limit=1000,
            offset=offset,
            with_payload=["parent_item_key", "is_chunk"],
            with_vectors=False
        )

        points, next_offset = results

        for point in points:
            total_scanned += 1
            payload = point.payload
            if payload.get('is_chunk') and payload.get('parent_item_key'):
                chunk_parents.add(payload.get('parent_item_key'))

        if next_offset is None:
            break
        offset = next_offset

        if total_scanned % 10000 == 0:
            logger.info(f"  Scanned {total_scanned} points, found {len(chunk_parents)} unique papers...")

    logger.info(f"Found {len(chunk_parents)} papers with chunks in Qdrant")
    return chunk_parents


def get_papers_in_neo4j(neo4j_uri: str, neo4j_user: str, neo4j_password: str) -> Set[str]:
    """Get all paper keys in Neo4j."""
    logger.info("Scanning Neo4j for papers...")

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    with driver.session() as session:
        result = session.run("MATCH (p:Paper) RETURN p.item_key as key")
        papers = {record["key"] for record in result}

    driver.close()
    logger.info(f"Found {len(papers)} papers in Neo4j")
    return papers


def get_paper_data_from_qdrant(client: QdrantClient, collection_name: str, paper_key: str) -> Dict[str, Any]:
    """
    Get all data needed for Neo4j from Qdrant for a single paper.

    Returns item in the format expected by Neo4j's add_papers_with_chunks():
    {
        "key": "ABC123",
        "data": {
            "title": "...",
            "abstractNote": "...",
            "creators": [...],
            "date": "2024",
            "fulltext": {
                "chunks": [
                    {"chunk_id": 0, "text": "...", "meta": {"headings": [...]}},
                    ...
                ]
            }
        }
    }
    """
    # Get all chunks for this paper
    results = client.scroll(
        collection_name=collection_name,
        scroll_filter=Filter(
            must=[
                FieldCondition(key="parent_item_key", match=MatchValue(value=paper_key)),
                FieldCondition(key="is_chunk", match=MatchValue(value=True))
            ]
        ),
        limit=200,  # Max chunks per paper
        with_payload=True,
        with_vectors=False
    )

    chunks_data = results[0]
    if not chunks_data:
        return None

    # Use first chunk's metadata for paper-level info
    first_chunk = chunks_data[0].payload

    # Extract creators from string format "Author1, Author2" to list of dicts
    creators_str = first_chunk.get('creators', 'No authors listed')
    creators = []
    if creators_str and creators_str != 'No authors listed':
        for author in creators_str.split(', '):
            parts = author.strip().split()
            if len(parts) >= 2:
                creators.append({
                    "firstName": ' '.join(parts[:-1]),
                    "lastName": parts[-1]
                })
            elif len(parts) == 1:
                creators.append({"lastName": parts[0]})

    # Build chunks array in Docling format
    chunks = []
    for point in sorted(chunks_data, key=lambda p: p.payload.get('chunk_id', 0)):
        payload = point.payload
        chunk_id = payload.get('chunk_id')
        chunk_text = payload.get('document', '')
        chunk_headings = payload.get('chunk_headings', [])

        if chunk_text.strip():
            chunks.append({
                "chunk_id": chunk_id,
                "text": chunk_text,
                "meta": {"headings": chunk_headings}
            })

    # Build item structure
    item = {
        "key": paper_key,
        "data": {
            "title": first_chunk.get('title', 'Untitled'),
            "abstractNote": first_chunk.get('abstract', ''),
            "creators": creators,
            "date": first_chunk.get('date', ''),
            "fulltext": {
                "chunks": chunks
            }
        }
    }

    return item


def main():
    parser = argparse.ArgumentParser(description="Sync missing papers from Qdrant to Neo4j")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--batch-size", type=int, default=5, help="Neo4j batch size (default: 5)")
    parser.add_argument("--config", type=str, help="Path to config file")
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

    # Get connection details
    qdrant_config = config.get("semantic_search", {})
    qdrant_url = qdrant_config.get("qdrant_url", "http://localhost:6333")
    collection_name = qdrant_config.get("collection_name", "zotero_library_qdrant")

    neo4j_config = config.get("neo4j_graphrag", {})
    neo4j_uri = neo4j_config.get("neo4j_uri", "bolt://localhost:7687")
    neo4j_user = neo4j_config.get("neo4j_user", "neo4j")
    neo4j_password = neo4j_config.get("neo4j_password", "demodemo")

    # Step 1: Find missing papers
    logger.info("=" * 80)
    logger.info("STEP 1: Identifying missing papers")
    logger.info("=" * 80)

    qdrant_papers = get_papers_in_qdrant(qdrant_url, collection_name)
    neo4j_papers = get_papers_in_neo4j(neo4j_uri, neo4j_user, neo4j_password)

    missing_papers = sorted(list(qdrant_papers - neo4j_papers))

    logger.info(f"\nSummary:")
    logger.info(f"  Papers in Qdrant: {len(qdrant_papers)}")
    logger.info(f"  Papers in Neo4j: {len(neo4j_papers)}")
    logger.info(f"  Missing from Neo4j: {len(missing_papers)}")

    if not missing_papers:
        logger.info("\n✅ All papers in Qdrant are already in Neo4j. Nothing to do!")
        return 0

    # Save missing papers list
    output_file = Path("/tmp/missing_papers_neo4j.json")
    with open(output_file, 'w') as f:
        json.dump(missing_papers, f, indent=2)
    logger.info(f"\nSaved missing paper keys to {output_file}")

    if args.dry_run:
        logger.info("\n🔍 DRY RUN MODE - No changes will be made")
        logger.info(f"\nWould add {len(missing_papers)} papers to Neo4j:")
        for i, key in enumerate(missing_papers[:20]):
            logger.info(f"  {i+1}. {key}")
        if len(missing_papers) > 20:
            logger.info(f"  ... and {len(missing_papers) - 20} more")
        return 0

    # Step 2: Fetch paper data from Qdrant
    logger.info("\n" + "=" * 80)
    logger.info("STEP 2: Fetching paper data from Qdrant")
    logger.info("=" * 80)

    qdrant_client = QdrantClient(url=qdrant_url)
    papers_data = []

    for i, paper_key in enumerate(missing_papers):
        try:
            item = get_paper_data_from_qdrant(qdrant_client, collection_name, paper_key)
            if item:
                papers_data.append(item)
            else:
                logger.warning(f"Paper {paper_key} has no chunks in Qdrant")

            if (i + 1) % 10 == 0:
                logger.info(f"  Fetched {i + 1}/{len(missing_papers)} papers...")

        except Exception as e:
            logger.error(f"Error fetching paper {paper_key} from Qdrant: {e}")
            continue

    logger.info(f"\nSuccessfully fetched {len(papers_data)} papers from Qdrant")

    if not papers_data:
        logger.error("\n❌ No paper data could be fetched from Qdrant")
        return 1

    # Step 3: Add papers to Neo4j
    logger.info("\n" + "=" * 80)
    logger.info("STEP 3: Adding papers to Neo4j")
    logger.info("=" * 80)

    # Prepare papers in Neo4j format
    papers_with_chunks = []
    for item in papers_data:
        item_data = item["data"]
        paper_key = item["key"]

        # Extract chunks from fulltext
        fulltext_data = item_data.get("fulltext", {})
        docling_chunks = fulltext_data.get("chunks", [])

        if not docling_chunks:
            logger.warning(f"Paper {paper_key}: No chunks in fulltext data")
            continue

        # Extract authors
        creators = item_data.get("creators", [])
        authors = [f"{c.get('firstName', '')} {c.get('lastName', '')}".strip() for c in creators]

        # Extract year
        year = item_data.get("date", "")
        try:
            year = int(year[:4]) if year else None
        except Exception:
            year = None

        # Prepare chunk data (limit to first 20 for LLM processing)
        chunk_data = []
        for chunk in docling_chunks[:20]:
            chunk_id = chunk.get("chunk_id", 0)
            chunk_text = chunk.get("text", "")

            if not chunk_text.strip():
                continue

            chunk_meta = chunk.get("meta", {})
            headings = chunk_meta.get("headings", [])

            # Create context-aware chunk representation
            chunk_context = chunk_text
            if headings:
                chunk_context = f"[Section: {' > '.join(headings)}]\n{chunk_text}"

            chunk_data.append({
                "chunk_id": chunk_id,
                "text": chunk_context,
                "qdrant_point_id": f"{paper_key}_chunk_{chunk_id}",
                "headings": headings
            })

        if chunk_data:
            papers_with_chunks.append({
                "paper_key": paper_key,
                "title": item_data.get("title", "Untitled"),
                "abstract": item_data.get("abstractNote", ""),
                "authors": authors,
                "year": year,
                "chunks": chunk_data
            })

    logger.info(f"Prepared {len(papers_with_chunks)} papers for Neo4j")

    if not papers_with_chunks:
        logger.error("\n❌ No papers could be prepared for Neo4j")
        return 1

    # Add to Neo4j
    llm_model = neo4j_config.get("llm_model", "gpt-4o-mini")
    openai_api_key = config.get("openai_api_key") or config.get("openai", {}).get("api_key")

    # Only require OpenAI API key for OpenAI models
    if llm_model.startswith("gpt-") and not openai_api_key:
        logger.error("OpenAI API key required for OpenAI models. Please set in config or use Ollama model.")
        return 1

    neo4j_client = Neo4jGraphRAGClient(
        neo4j_uri=neo4j_uri,
        neo4j_user=neo4j_user,
        neo4j_password=neo4j_password,
        llm_model=llm_model,
        openai_api_key=openai_api_key if llm_model.startswith("gpt-") else None
    )

    logger.info(f"Adding {len(papers_with_chunks)} papers in batches of {args.batch_size}...")

    try:
        result = neo4j_client.add_papers_with_chunks(
            papers_with_chunks,
            batch_size=args.batch_size
        )

        logger.info("\n" + "=" * 80)
        logger.info("RESULTS")
        logger.info("=" * 80)
        logger.info(f"✅ Successfully added: {result.get('successful', 0)} papers")
        logger.info(f"   Total chunks: {result.get('total_chunks', 0)}")
        logger.info(f"❌ Failed: {result.get('failed', 0)} papers")

        if result.get('errors'):
            logger.warning(f"\nErrors encountered:")
            for error in result['errors'][:10]:
                logger.warning(f"  - {error}")
            if len(result['errors']) > 10:
                logger.warning(f"  ... and {len(result['errors']) - 10} more errors")

        duration = datetime.now() - start_time
        logger.info(f"\n⏱️  Total duration: {duration}")

        # Save results
        results_file = Path("/tmp/neo4j_sync_results.json")
        with open(results_file, 'w') as f:
            json.dump({
                "start_time": start_time.isoformat(),
                "duration": str(duration),
                "missing_papers_count": len(missing_papers),
                "prepared_papers_count": len(papers_with_chunks),
                "result": result
            }, f, indent=2)
        logger.info(f"Saved results to {results_file}")

        return 0 if result.get('failed', 0) == 0 else 1

    except Exception as e:
        logger.error(f"\n❌ Error adding papers to Neo4j: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        neo4j_client.close()


if __name__ == "__main__":
    sys.exit(main())
