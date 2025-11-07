#!/usr/bin/env python3
"""
Sync missing papers from Qdrant to Neo4j.

This script adds papers that exist in Qdrant but are missing from Neo4j,
without touching or rebuilding the Qdrant database.

Usage:
    python scripts/sync_missing_papers_to_neo4j.py [--dry-run] [--batch-size N]
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
from neo4j import GraphDatabase
from agent_zot.database.local_zotero import LocalZoteroReader
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


def get_paper_data_from_zotero(zotero_reader: LocalZoteroReader, paper_keys: List[str]) -> List[Dict[str, Any]]:
    """Get full paper data from Zotero for missing papers."""
    logger.info(f"Fetching data for {len(paper_keys)} papers from Zotero...")

    papers_data = []

    for i, key in enumerate(paper_keys):
        try:
            # Get item from Zotero
            item = zotero_reader.get_item(key)
            if not item:
                logger.warning(f"Paper {key} not found in Zotero")
                continue

            # Get fulltext data (Docling chunks from cache)
            fulltext_data = zotero_reader.get_item_fulltext(key)
            if fulltext_data and isinstance(fulltext_data, dict):
                # Inject fulltext into item data
                if 'data' not in item:
                    item['data'] = {}
                item['data']['fulltext'] = fulltext_data
                papers_data.append(item)
            else:
                logger.warning(f"Paper {key} has no fulltext data in Zotero")

            if (i + 1) % 10 == 0:
                logger.info(f"  Fetched {i + 1}/{len(paper_keys)} papers...")

        except Exception as e:
            logger.error(f"Error fetching paper {key}: {e}")
            continue

    logger.info(f"Successfully fetched {len(papers_data)} papers with fulltext")
    return papers_data


def prepare_papers_for_neo4j(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Prepare paper data in format expected by Neo4j client."""
    logger.info(f"Preparing {len(items)} papers for Neo4j...")

    papers_with_chunks = []

    for item in items:
        try:
            item_data = item.get("data", {})
            paper_key = item.get("key", "")
            title = item_data.get("title", "Untitled")
            abstract = item_data.get("abstractNote", "")

            # Extract Docling chunks
            fulltext_data = item_data.get("fulltext", "")
            if not isinstance(fulltext_data, dict):
                logger.warning(f"Paper {paper_key}: No Docling chunks available")
                continue

            docling_chunks = fulltext_data.get("chunks", [])
            if not docling_chunks:
                logger.warning(f"Paper {paper_key}: Empty chunks array")
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
                    "title": title,
                    "abstract": abstract,
                    "authors": authors,
                    "year": year,
                    "chunks": chunk_data
                })

        except Exception as e:
            logger.error(f"Error preparing paper {item.get('key', 'unknown')}: {e}")
            continue

    logger.info(f"Prepared {len(papers_with_chunks)} papers for Neo4j")
    return papers_with_chunks


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
    qdrant_url = config.get("qdrant", {}).get("url", "http://localhost:6333")
    collection_name = config.get("qdrant", {}).get("collection_name", "zotero_library_qdrant")

    neo4j_config = config.get("neo4j", {})
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

    # Step 2: Fetch paper data from Zotero
    logger.info("\n" + "=" * 80)
    logger.info("STEP 2: Fetching paper data from Zotero")
    logger.info("=" * 80)

    zotero_reader = LocalZoteroReader()
    papers_data = get_paper_data_from_zotero(zotero_reader, missing_papers)

    if not papers_data:
        logger.error("\n❌ No paper data could be fetched from Zotero")
        return 1

    # Step 3: Prepare papers for Neo4j
    logger.info("\n" + "=" * 80)
    logger.info("STEP 3: Preparing papers for Neo4j")
    logger.info("=" * 80)

    prepared_papers = prepare_papers_for_neo4j(papers_data)

    if not prepared_papers:
        logger.error("\n❌ No papers could be prepared for Neo4j")
        return 1

    # Step 4: Add papers to Neo4j
    logger.info("\n" + "=" * 80)
    logger.info("STEP 4: Adding papers to Neo4j")
    logger.info("=" * 80)

    neo4j_client = Neo4jGraphRAGClient(
        neo4j_uri=neo4j_uri,
        neo4j_user=neo4j_user,
        neo4j_password=neo4j_password,
        llm_model=neo4j_config.get("llm_model", "gpt-4o-mini"),
        openai_api_key=config.get("openai_api_key") or config.get("openai", {}).get("api_key")
    )

    logger.info(f"Adding {len(prepared_papers)} papers in batches of {args.batch_size}...")

    try:
        result = neo4j_client.add_papers_with_chunks(
            prepared_papers,
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
                "prepared_papers_count": len(prepared_papers),
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
