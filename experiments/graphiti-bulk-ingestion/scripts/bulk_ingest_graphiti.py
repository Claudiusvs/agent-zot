#!/usr/bin/env python3
"""
Graphiti-only bulk ingestion script.

BYPASSES Qdrant and Agent-Zot Neo4j pipelines.
ONLY ingests to Graphiti by reading existing chunks from Qdrant.

Use for: Catching up Graphiti on existing 2,500+ papers
After:   Auto-sync will process new papers through full pipeline

Safety features (hardcoded):
- force_rebuild=False (never rebuilds existing data)
- extract_fulltext=True (always processes fulltext if needed)
- Episode cache deduplication (never reprocesses same paper)
"""

import asyncio
import os
import sys
import time
import json
from pathlib import Path
from typing import List, Dict, Any

# Set env for local Zotero
os.environ["ZOTERO_LOCAL"] = "true"

# Ollama is used for Graphiti SDK (Qwen2.5:7b-instruct + BGE-M3)
# No API key needed - Ollama runs locally at http://localhost:11434

# Disable Graphiti telemetry (PostHog analytics)
os.environ["GRAPHITI_TELEMETRY_ENABLED"] = "false"

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent_zot.clients.qdrant import create_qdrant_client
from agent_zot.ingestion.graphiti_ingestion import ingest_to_graphiti, should_ingest_to_graphiti
from agent_zot.ingestion.graphiti_cache import get_episode_cache
from agent_zot.database.local_zotero import get_local_zotero_reader


async def get_all_paper_keys_from_qdrant() -> List[str]:
    """
    Get all unique paper keys from Qdrant that have chunks.

    Strategy: Scan chunks to find unique parent_item_keys.
    These are papers that have been chunked and embedded.

    Note: parent_item_keys are attachment keys, but metadata is available
    in chunk payloads, so we don't need Zotero lookups.
    """
    print("🔍 Scanning Qdrant for papers with chunks...")

    # Initialize Qdrant client
    config_path = str(Path.home() / ".config" / "agent-zot" / "config.json")
    qdrant_client = create_qdrant_client(config_path)

    # Scroll through chunks to find unique parent papers
    paper_keys = set()

    # Query for chunks only (is_chunk=True)
    scroll_result = qdrant_client.client.scroll(
        collection_name=qdrant_client.collection_name,
        scroll_filter={
            "must": [
                {
                    "key": "is_chunk",
                    "match": {"value": True}
                }
            ]
        },
        limit=10000,  # Large batch
        with_payload=True,
        with_vectors=False,
    )

    # Extract unique parent_item_keys from chunks
    points, next_offset = scroll_result
    for point in points:
        parent_key = point.payload.get("parent_item_key")
        if parent_key:
            paper_keys.add(parent_key)

    # Handle pagination if needed
    while next_offset:
        scroll_result = qdrant_client.client.scroll(
            collection_name=qdrant_client.collection_name,
            scroll_filter={
                "must": [
                    {
                        "key": "is_chunk",
                        "match": {"value": True}
                    }
                ]
            },
            limit=10000,
            offset=next_offset,
            with_payload=True,
            with_vectors=False,
        )
        points, next_offset = scroll_result
        for point in points:
            parent_key = point.payload.get("parent_item_key")
            if parent_key:
                paper_keys.add(parent_key)

    paper_keys = sorted(list(paper_keys))
    print(f"✅ Found {len(paper_keys)} papers with chunks in Qdrant")

    return paper_keys


async def get_chunks_and_metadata_for_item(item_key: str, qdrant_client) -> tuple[List[str], Dict[str, Any]]:
    """
    Get text chunks AND rich metadata for an item from Qdrant.

    Args:
        item_key: Zotero item key (parent_item_key from chunks)
        qdrant_client: Qdrant client instance

    Returns:
        Tuple of (chunks, metadata_dict)
        - chunks: List of text chunks
        - metadata: Rich metadata extracted from first chunk
    """
    try:
        # Search for chunks matching this item key
        results = qdrant_client.client.scroll(
            collection_name=qdrant_client.collection_name,
            scroll_filter={
                "must": [
                    {
                        "key": "parent_item_key",
                        "match": {"value": item_key}
                    },
                    {
                        "key": "is_chunk",
                        "match": {"value": True}
                    }
                ]
            },
            limit=1000,  # Max chunks per paper
            with_payload=True,
            with_vectors=False,
        )

        # Extract text and metadata from points
        chunks = []
        first_payload = None

        for point in results[0]:  # results is tuple (points, next_page_offset)
            payload = point.payload

            # Save first payload for metadata extraction
            if first_payload is None:
                first_payload = payload

            # Chunks store text in 'document' field
            text = payload.get("document", "")
            if text:
                chunks.append(text)

        # Extract rich metadata from first chunk
        metadata = {}
        if first_payload:
            metadata = {
                # Core bibliographic
                "title": first_payload.get("title", ""),
                "authors": first_payload.get("creators", ""),
                "doi": first_payload.get("doi", ""),
                "journal": first_payload.get("journal", ""),
                "publication": first_payload.get("publication", ""),
                "date": first_payload.get("date", ""),
                "url": first_payload.get("url", ""),
                "abstract": first_payload.get("abstract", ""),

                # Publication details
                "volume": first_payload.get("volume", ""),
                "issue": first_payload.get("issue", ""),
                "pages": first_payload.get("pages", ""),
                "citation_key": first_payload.get("citation_key", ""),

                # Categorization
                "tags": first_payload.get("tags", "").split() if first_payload.get("tags") else [],

                # Temporal
                "date_added": first_payload.get("date_added", ""),
                "date_modified": first_payload.get("date_modified", ""),

                # Source linking (for traceability)
                "zotero_item_key": item_key,
                "fulltext_source": first_payload.get("fulltext_source", ""),

                # Chunk context (helpful for entity extraction)
                "first_chunk_headings": first_payload.get("chunk_headings", []),
            }

        return chunks, metadata

    except Exception as e:
        print(f"❌ Error retrieving chunks for {item_key}: {e}")
        return [], {}


async def bulk_ingest_graphiti(
    paper_keys: List[str],
    config: Dict[str, Any],
    max_workers: int = 2,  # Now used for limited parallelism
    batch_size: int = 30,  # Not used - config value used instead
    resume: bool = True,
):
    """
    Bulk ingest papers to Graphiti using LIMITED PARALLEL processing.

    BYPASSES Qdrant and Neo4j pipelines - only reads existing chunks.

    Processing Strategy:
    - Papers processed with LIMITED PARALLELISM (2-3 concurrent papers) - Option A
    - Semaphore controls max concurrent papers to respect API rate limits
    - Within each paper, batches processed CONCURRENTLY via asyncio.gather()
    - Batch-level semaphore (5) controls concurrent API calls per paper
    - Batch size from config.json (default: 15 chunks/episode)

    Args:
        paper_keys: List of paper keys to ingest
        config: Agent-zot configuration
        max_workers: Max concurrent papers (default: 2 for rate limit safety)
        batch_size: DEPRECATED - uses config value instead
        resume: Skip papers already in episode cache (default: True)
    """
    print("=" * 70)
    print("🚀 GRAPHITI BULK INGESTION")
    print("=" * 70)
    print(f"📊 Total papers to process: {len(paper_keys)}")
    print(f"⚙️  Parallelism: {max_workers} papers concurrently (Option A)")
    print(f"🔄 Resume mode: {'ON' if resume else 'OFF'} (skip cached papers)")
    print()

    # Initialize Qdrant client
    config_path = str(Path.home() / ".config" / "agent-zot" / "config.json")
    qdrant_client = create_qdrant_client(config_path)

    # Get cache stats before
    episode_cache = get_episode_cache()
    stats_before = episode_cache.get_stats()
    print(f"📋 Episode cache before: {stats_before['successful']} papers cached")
    print(f"📋 Episode cache stats: {stats_before}")
    print()

    # Debug: Show Graphiti config
    graphiti_config = config.get("graphiti", {})
    actual_batch_size = graphiti_config.get('batch_size', 5)  # Use config value
    print(f"🔧 Graphiti config:")
    print(f"   - enabled: {graphiti_config.get('enabled', False)}")
    print(f"   - filter_tag: {graphiti_config.get('filter_tag')}")
    print(f"   - batch_size: {actual_batch_size} chunks/episode")
    print(f"   - group_id: {graphiti_config.get('group_id', 'agent-zot-discovery')}")
    print()

    # Process papers
    start_time = time.time()

    items_processed = 0
    chunks_processed = 0
    episodes_created = 0
    errors = 0
    skipped = 0

    # Semaphore for paper-level concurrency control (Option A)
    paper_semaphore = asyncio.Semaphore(max_workers)

    # Progress tracking
    progress_lock = asyncio.Lock()

    async def process_single_paper(i: int, item_key: str) -> tuple[int, int, int, int, int]:
        """
        Process a single paper with rate limiting.

        Returns: (items_processed, chunks_processed, episodes_created, errors, skipped)
        """
        async with paper_semaphore:  # Limit concurrent papers
            try:
                async with progress_lock:
                    print(f"⏳ Processing paper {i+1}/{len(paper_keys)}: {item_key}...")

                # Get chunks AND rich metadata from Qdrant
                async with progress_lock:
                    print(f"    📦 Retrieving chunks from Qdrant...")
                chunks, metadata = await get_chunks_and_metadata_for_item(item_key, qdrant_client)

                if not chunks:
                    async with progress_lock:
                        print(f"    ⊙ No chunks found in Qdrant")
                    return (0, 0, 0, 0, 1)

                async with progress_lock:
                    print(f"    ✅ Found {len(chunks)} chunks with rich metadata")
                    print(f"    📝 Title: {metadata.get('title', 'N/A')[:60]}...")

                # Check if should ingest
                should_ingest = should_ingest_to_graphiti(item_key, metadata, config, force_reingest=not resume)
                if not should_ingest:
                    async with progress_lock:
                        print(f"    ⊙ Skipping (cached or filtered)")
                    return (0, 0, 0, 0, 1)

                # Ingest to Graphiti (this will process batches concurrently internally)
                result = await ingest_to_graphiti(
                    paper_key=item_key,
                    chunks=chunks,
                    metadata=metadata,
                    config=config,
                    force_reingest=not resume,
                )

                # Evaluate result
                if isinstance(result, Exception):
                    async with progress_lock:
                        print(f"❌ Error processing {item_key}: {result}")
                    return (0, 0, 0, 1, 0)

                if result.success and result.episodes_created > 0:
                    async with progress_lock:
                        print(f"    ✅ Success: {result.episodes_created} episodes, {result.chunks_processed} chunks")
                    return (1, result.chunks_processed, result.episodes_created, 0, 0)
                elif result.error == "Already processed (cached)":
                    return (0, 0, 0, 0, 1)
                else:
                    async with progress_lock:
                        print(f"    ❌ Failed: {result.error}")
                    return (0, 0, 0, 1, 0)

            except Exception as e:
                async with progress_lock:
                    print(f"❌ Exception processing {item_key}: {e}")
                return (0, 0, 0, 1, 0)

    # Process papers with LIMITED PARALLELISM (Option A)
    print(f"🚀 Starting parallel processing with max {max_workers} concurrent papers...")
    print()

    # Create tasks for all papers
    tasks = [process_single_paper(i, item_key) for i, item_key in enumerate(paper_keys)]

    # Execute with limited concurrency
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Aggregate results
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"❌ Task {i+1} raised exception: {result}")
            errors += 1
            continue

        items, chunks, episodes, errs, skip = result
        items_processed += items
        chunks_processed += chunks
        episodes_created += episodes
        errors += errs
        skipped += skip

        # Progress update every 10 papers
        if (i + 1) % 10 == 0:
            elapsed = time.time() - start_time
            rate = items_processed / elapsed if elapsed > 0 else 0
            eta_seconds = (len(paper_keys) - (i + 1)) / rate if rate > 0 else 0
            eta_hours = eta_seconds / 3600

            print()
            print(f"  ✅ Processed: {items_processed}")
            print(f"  📊 Episodes: {episodes_created}")
            print(f"  ⊙  Skipped: {skipped}")
            print(f"  ❌ Errors: {errors}")
            print(f"  ⏱️  Rate: {rate:.2f} papers/sec")
            print(f"  🕐 ETA: {eta_hours:.1f} hours")
            print()

    # Final stats
    elapsed = time.time() - start_time
    stats_after = episode_cache.get_stats()

    print("=" * 70)
    print("✅ BULK INGESTION COMPLETE")
    print("=" * 70)
    print(f"⏱️  Total time: {elapsed/3600:.1f} hours")
    print(f"✅ Papers processed: {items_processed}")
    print(f"📊 Episodes created: {episodes_created}")
    print(f"📄 Chunks processed: {chunks_processed}")
    print(f"⊙  Skipped (cached): {skipped}")
    print(f"❌ Errors: {errors}")
    print()
    print(f"📋 Episode cache after: {stats_after['successful']} papers cached (+{stats_after['successful'] - stats_before['successful']})")
    print(f"💰 Estimated cost: ${items_processed * 0.007:.2f}")
    print()


async def main():
    """Main entry point."""
    import sys

    # Check for test mode
    test_mode = "--test" in sys.argv or "-t" in sys.argv
    test_limit = 5 if test_mode else None

    if test_mode:
        print("🧪 TEST MODE - Processing 5 papers only")
    else:
        print("🔧 Graphiti Bulk Ingestion - Using Qdrant chunks directly")
    print()

    # Get all papers from Qdrant (papers that have chunks)
    paper_keys = await get_all_paper_keys_from_qdrant()

    # Limit for test mode
    if test_limit:
        paper_keys = paper_keys[:test_limit]
        print(f"🧪 Test mode: Limited to {len(paper_keys)} papers")
        print()

    # Load config
    config_path = str(Path.home() / ".config" / "agent-zot" / "config.json")
    with open(config_path, 'r') as f:
        config = json.load(f)

    # Run bulk ingestion
    await bulk_ingest_graphiti(
        paper_keys=paper_keys,
        config=config,
        max_workers=1,  # Sequential processing to avoid Neo4j auth rate limit during testing
        batch_size=30,  # Deprecated - config value (15) used instead
        resume=True,    # Skip cached papers
    )


if __name__ == "__main__":
    asyncio.run(main())
