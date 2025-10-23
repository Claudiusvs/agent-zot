#!/usr/bin/env python3
"""
Populate Neo4j knowledge graph from existing Qdrant fulltext data.

This script:
1. Queries Qdrant for all items with fulltext chunks (read-only)
2. Reconstructs full document text from chunks
3. Extracts entities and relationships using Neo4j GraphRAG
4. NEVER writes anything back to Qdrant

Usage:
    python populate_neo4j_from_qdrant.py --dry-run  # Test without writing to Neo4j
    python populate_neo4j_from_qdrant.py --limit 5   # Process only 5 items
    python populate_neo4j_from_qdrant.py             # Process all items
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, ScrollRequest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agent_zot.clients.neo4j_graphrag import Neo4jGraphRAGClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config() -> Dict:
    """Load configuration from ~/.config/agent-zot/config.json"""
    config_path = Path.home() / ".config" / "agent-zot" / "config.json"

    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path}\n"
            f"Run 'zotero-mcp setup' to create it."
        )

    with open(config_path) as f:
        return json.load(f)


def get_items_with_fulltext(qdrant_client: QdrantClient, collection_name: str) -> List[str]:
    """
    Query Qdrant for all unique item_key values that have fulltext chunks.

    Args:
        qdrant_client: Qdrant client instance
        collection_name: Name of the Qdrant collection

    Returns:
        List of unique item_key values
    """
    logger.info("Querying Qdrant for items with fulltext chunks...")

    item_keys = set()
    offset = None

    # Scroll through all points with has_fulltext=true
    while True:
        results = qdrant_client.scroll(
            collection_name=collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="has_fulltext",
                        match=MatchValue(value=True)
                    )
                ]
            ),
            limit=100,
            offset=offset,
            with_payload=["parent_item_key"],
            with_vectors=False
        )

        points, next_offset = results

        if not points:
            break

        for point in points:
            # Chunks have parent_item_key field pointing to the actual paper
            parent_key = point.payload.get("parent_item_key")
            if parent_key:
                item_keys.add(parent_key)

        offset = next_offset
        if offset is None:
            break

    logger.info(f"Found {len(item_keys)} items with fulltext chunks")
    return sorted(list(item_keys))


def get_item_data(
    qdrant_client: QdrantClient,
    collection_name: str,
    item_key: str
) -> Optional[Dict]:
    """
    Retrieve all data for a single item from Qdrant.

    Args:
        qdrant_client: Qdrant client instance
        collection_name: Name of the Qdrant collection
        item_key: Item key to retrieve

    Returns:
        Dictionary with:
        - item_key: Item key
        - title: Paper title
        - creators: List of authors
        - abstract: Abstract text
        - year: Publication year
        - fulltext: Complete document text (reconstructed from chunks)

        Returns None if item not found or insufficient data.
    """
    # Query all chunks for this item (they have parent_item_key pointing to this item)
    chunk_results = qdrant_client.scroll(
        collection_name=collection_name,
        scroll_filter=Filter(
            must=[
                FieldCondition(key="parent_item_key", match=MatchValue(value=item_key)),
                FieldCondition(key="has_fulltext", match=MatchValue(value=True))
            ]
        ),
        limit=1000,  # Assume max 1000 chunks per document
        with_payload=True,
        with_vectors=False
    )

    chunk_points, _ = chunk_results

    if not chunk_points:
        logger.warning(f"No chunks found for item {item_key}")
        return None

    # Reconstruct fulltext from all chunks
    # Sort by item_key suffix (e.g., "KEY_chunk_0", "KEY_chunk_1")
    def get_chunk_index(point):
        key = point.payload.get("item_key", "")
        if "_chunk_" in key:
            try:
                return int(key.split("_chunk_")[-1])
            except ValueError:
                return 0
        return 0

    chunks_sorted = sorted(chunk_points, key=get_chunk_index)

    # Extract metadata from first chunk (all chunks have the same metadata)
    first_chunk = chunks_sorted[0].payload
    title = first_chunk.get("title", "Unknown")
    creators_str = first_chunk.get("creators", "No authors listed")
    creators = [c.strip() for c in creators_str.split(",")] if creators_str != "No authors listed" else []
    abstract = first_chunk.get("abstract", "")
    date_str = first_chunk.get("date", "")
    year = date_str.split("-")[0] if date_str else None

    # Reconstruct fulltext from all chunks
    fulltext = "\n\n".join(p.payload.get("document", "") for p in chunks_sorted)

    # Require minimum text length
    if len(fulltext) < 100:
        logger.warning(f"Item {item_key} has insufficient text ({len(fulltext)} chars)")
        return None

    return {
        "item_key": item_key,
        "title": title,
        "creators": creators,
        "abstract": abstract,
        "year": year,
        "fulltext": fulltext
    }


async def process_single_item(
    idx: int,
    item_key: str,
    qdrant_client: QdrantClient,
    collection_name: str,
    neo4j_client: Optional[Neo4jGraphRAGClient],
    total_items: int,
    dry_run: bool,
    semaphore: asyncio.Semaphore
) -> bool:
    """Process a single item with concurrency control."""
    async with semaphore:
        logger.info(f"Processing item {idx}/{total_items}: {item_key}")

        try:
            # Get item data from Qdrant
            item_data = get_item_data(qdrant_client, collection_name, item_key)

            if not item_data:
                logger.warning(f"Skipping item {item_key} - insufficient data")
                return False

            logger.info(
                f"  Title: {item_data['title'][:80]}...\n"
                f"  Authors: {', '.join(item_data['creators'][:3])}...\n"
                f"  Text length: {len(item_data['fulltext'])} chars"
            )

            if dry_run:
                logger.info(f"  [DRY RUN] Would extract entities from this paper")
            else:
                # Extract entities and relationships with Neo4j
                logger.info(f"  Extracting entities with Neo4j GraphRAG...")

                # Split fulltext into chunks (Neo4j expects list of strings)
                fulltext = item_data["fulltext"]
                chunk_size = 5000  # Characters per chunk for LLM processing
                chunks = [fulltext[i:i+chunk_size] for i in range(0, len(fulltext), chunk_size)]

                await neo4j_client.add_paper_to_graph(
                    paper_key=item_data["item_key"],
                    title=item_data["title"],
                    abstract=item_data["abstract"],
                    authors=item_data["creators"],
                    year=item_data["year"],
                    chunks=chunks
                )
                logger.info(f"  ✓ Successfully extracted entities for {item_key}")

            return True

        except Exception as e:
            logger.error(f"  ✗ Error processing {item_key}: {e}", exc_info=True)
            return False


async def populate_neo4j(
    config: Dict,
    item_keys: List[str],
    limit: Optional[int] = None,
    dry_run: bool = False,
    concurrency: int = 4
):
    """
    Populate Neo4j knowledge graph from Qdrant data with concurrent processing.

    Args:
        config: Configuration dictionary
        item_keys: List of item keys to process
        limit: Maximum number of items to process (None for all)
        dry_run: If True, don't write to Neo4j
        concurrency: Number of concurrent tasks (default: 4)
    """
    # Initialize Qdrant client (read-only)
    qdrant_config = config["semantic_search"]
    qdrant_client = QdrantClient(url=qdrant_config["qdrant_url"])
    collection_name = qdrant_config["collection_name"]

    # Initialize Neo4j client (if not dry run)
    neo4j_client = None
    if not dry_run:
        neo4j_config = config.get("neo4j_graphrag", {})
        if not neo4j_config.get("enabled"):
            raise ValueError("Neo4j GraphRAG is not enabled in config")

        logger.info("Initializing Neo4j GraphRAG client...")
        neo4j_client = Neo4jGraphRAGClient(
            neo4j_uri=neo4j_config["neo4j_uri"],
            neo4j_user=neo4j_config["neo4j_user"],
            neo4j_password=neo4j_config["neo4j_password"],
            neo4j_database=neo4j_config.get("neo4j_database", "neo4j"),
            llm_model=neo4j_config.get("llm_model", "gpt-4o-mini"),
            entity_types=neo4j_config.get("entity_types"),
            relation_types=neo4j_config.get("relation_types")
        )

    # Apply limit
    if limit:
        item_keys = item_keys[:limit]
        logger.info(f"Processing only first {limit} items (limit applied)")

    logger.info(f"Using concurrency level: {concurrency}")

    # Create semaphore to limit concurrency
    semaphore = asyncio.Semaphore(concurrency)

    # Process items concurrently
    tasks = [
        process_single_item(
            idx + 1,
            item_key,
            qdrant_client,
            collection_name,
            neo4j_client,
            len(item_keys),
            dry_run,
            semaphore
        )
        for idx, item_key in enumerate(item_keys)
    ]

    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks, return_exceptions=False)

    # Count successes and failures
    success_count = sum(1 for r in results if r is True)
    error_count = len(results) - success_count

    # Summary
    logger.info("\n" + "="*80)
    logger.info("SUMMARY")
    logger.info("="*80)
    logger.info(f"Total items processed: {len(item_keys)}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Errors: {error_count}")

    if dry_run:
        logger.info("\n[DRY RUN] No changes were made to Neo4j")


def main():
    parser = argparse.ArgumentParser(
        description="Populate Neo4j knowledge graph from Qdrant fulltext data"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test without writing to Neo4j"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Process only N items (for testing)"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="Number of concurrent tasks (default: 4)"
    )

    args = parser.parse_args()

    try:
        # Load config
        logger.info("Loading configuration...")
        config = load_config()

        # Initialize Qdrant client
        qdrant_config = config["semantic_search"]
        qdrant_client = QdrantClient(url=qdrant_config["qdrant_url"])
        collection_name = qdrant_config["collection_name"]

        # Get all items with fulltext
        item_keys = get_items_with_fulltext(qdrant_client, collection_name)

        if not item_keys:
            logger.error("No items with fulltext found in Qdrant!")
            return 1

        # Populate Neo4j (async)
        asyncio.run(populate_neo4j(
            config,
            item_keys,
            limit=args.limit,
            dry_run=args.dry_run,
            concurrency=args.concurrency
        ))

        return 0

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
