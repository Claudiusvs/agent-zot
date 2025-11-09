"""
Graphiti ingestion module for autonomous entity extraction.

Handles batch ingestion of paper chunks to Graphiti MCP server with
cost optimization, error handling, and selective filtering by tags.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from agent_zot.clients.graphiti_client import (
    GraphitiClient,
    GraphitiUnavailableError,
    GraphitiClientError,
)
from agent_zot.ingestion.graphiti_cache import get_episode_cache

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """Result of Graphiti ingestion operation."""

    success: bool
    paper_key: str
    chunks_processed: int
    episodes_created: int
    elapsed_seconds: float
    error: Optional[str] = None
    cost_estimate_usd: Optional[float] = None


@dataclass
class IngestionBatch:
    """Batch of chunks for single episode."""

    episode_name: str
    combined_text: str
    chunk_count: int
    metadata: Dict[str, Any]


class GraphitiIngestionError(Exception):
    """Base exception for Graphiti ingestion errors."""
    pass


async def ingest_to_graphiti(
    paper_key: str,
    chunks: List[str],
    metadata: Dict[str, Any],
    config: Dict[str, Any],
    client: Optional[GraphitiClient] = None,
    force_reingest: bool = False,
) -> IngestionResult:
    """
    Ingest paper chunks to Graphiti for autonomous entity extraction.

    This function:
    1. Checks if Graphiti is enabled and available
    2. Checks episode cache for deduplication (skip if already processed)
    3. Batches chunks to optimize LLM API costs
    4. Sends batches to Graphiti asynchronously
    5. Tracks metrics (time, cost, entity count)
    6. Updates episode cache on success
    7. Gracefully degrades if Graphiti unavailable

    Deduplication Logic (analogous to agent-zot's parse cache):
    - Episode cache tracks which papers have been ingested
    - Papers already in cache are skipped (unless force_reingest=True)
    - After bulk ingestion, only NEW papers are processed
    - This prevents duplicate entity extraction and wasted API costs

    Args:
        paper_key: Zotero item key
        chunks: List of text chunks from PDF
        metadata: Paper metadata (title, authors, etc.)
        config: Agent-zot configuration dict
        client: Optional GraphitiClient instance (for testing)
        force_reingest: If True, ignore cache and reprocess (default: False)

    Returns:
        IngestionResult with statistics

    Raises:
        GraphitiIngestionError: If ingestion fails critically
    """
    start_time = time.time()

    # Check if Graphiti is enabled
    graphiti_config = config.get("graphiti", {})
    if not graphiti_config.get("enabled", False):
        logger.debug(f"Graphiti disabled, skipping ingestion for {paper_key}")
        return IngestionResult(
            success=True,  # Not an error, just disabled
            paper_key=paper_key,
            chunks_processed=0,
            episodes_created=0,
            elapsed_seconds=0.0,
            error="Graphiti disabled in config",
        )

    # DEDUPLICATION: Check episode cache (unless force_reingest)
    if not force_reingest:
        episode_cache = get_episode_cache()
        if episode_cache.has_paper(paper_key):
            cached_info = episode_cache.get_paper_info(paper_key)
            logger.debug(
                f"Paper {paper_key} already in Graphiti episode cache "
                f"(episodes={cached_info['episode_count']}, "
                f"chunks={cached_info['chunks_processed']}), skipping"
            )
            return IngestionResult(
                success=True,  # Not an error, just cached
                paper_key=paper_key,
                chunks_processed=0,
                episodes_created=0,
                elapsed_seconds=0.0,
                error="Already processed (cached)",
            )

    # Check if paper has required tag for Phase 1
    filter_tag = graphiti_config.get("filter_tag")
    if filter_tag:
        paper_tags = metadata.get("tags", [])
        if filter_tag not in paper_tags:
            logger.debug(
                f"Paper {paper_key} missing tag '{filter_tag}', "
                f"skipping Graphiti ingestion"
            )
            return IngestionResult(
                success=True,  # Not an error, just filtered
                paper_key=paper_key,
                chunks_processed=0,
                episodes_created=0,
                elapsed_seconds=0.0,
                error=f"Missing filter tag: {filter_tag}",
            )

    # Initialize client if not provided
    if client is None:
        # Get Neo4j config from graphiti section (with fallback to neo4j_graphrag)
        neo4j_uri = graphiti_config.get("neo4j_uri")
        neo4j_user = graphiti_config.get("neo4j_user")
        neo4j_password = graphiti_config.get("neo4j_password")

        # Fallback to neo4j_graphrag section if not in graphiti
        if neo4j_uri is None:
            neo4j_config = config.get("neo4j_graphrag", {})
            neo4j_uri = neo4j_config.get("neo4j_uri", "bolt://localhost:7687")
            neo4j_user = neo4j_config.get("neo4j_user", "neo4j")
            neo4j_password = neo4j_config.get("neo4j_password", "demodemo")

        client = GraphitiClient(
            neo4j_uri=neo4j_uri,
            neo4j_user=neo4j_user,
            neo4j_password=neo4j_password,
            group_id=graphiti_config.get("group_id", "agent-zot-discovery"),
        )

    # Check availability (now async)
    if not await client.is_available():
        logger.warning(
            f"Graphiti unavailable for {paper_key}, "
            f"skipping entity extraction"
        )
        return IngestionResult(
            success=True,  # Graceful degradation, not a critical error
            paper_key=paper_key,
            chunks_processed=0,
            episodes_created=0,
            elapsed_seconds=0.0,
            error="Graphiti server unavailable",
        )

    # Batch chunks to optimize LLM costs
    # Increased from 15 → 30 for better throughput (50% fewer API calls)
    batch_size = graphiti_config.get("batch_size", 30)
    batches = _create_batches(
        paper_key=paper_key,
        chunks=chunks,
        metadata=metadata,
        batch_size=batch_size,
    )

    logger.info(
        f"Ingesting {len(chunks)} chunks to Graphiti in {len(batches)} batches "
        f"(batch_size={batch_size})"
    )

    # Ingest batches with controlled concurrency to avoid rate limits
    # Limit to 5 concurrent API calls to prevent 429 errors
    semaphore = asyncio.Semaphore(5)

    async def process_batch(i: int, batch: IngestionBatch) -> tuple[int, int, Optional[str]]:
        """Process a single batch and return (episodes, chunks, error)."""
        async with semaphore:  # Limit concurrent API calls
            try:
                result = await client.add_paper_chunk(
                    chunk_text=batch.combined_text,
                    paper_key=paper_key,
                    metadata=batch.metadata,
                    episode_name=batch.episode_name,
                )

                if result.get("success"):
                    logger.debug(
                        f"Batch {i+1}/{len(batches)} ingested: "
                        f"{batch.chunk_count} chunks"
                    )
                    return (1, batch.chunk_count, None)
                else:
                    error_msg = f"Batch {i+1} failed: {result.get('error')}"
                    return (0, 0, error_msg)

            except (GraphitiUnavailableError, GraphitiClientError) as e:
                logger.error(
                    f"Error ingesting batch {i+1} for {paper_key}: {e}"
                )
                error_msg = f"Batch {i+1}: {str(e)}"
                return (0, 0, error_msg)

    # Process all batches concurrently (with semaphore limiting max concurrent)
    batch_results = await asyncio.gather(
        *[process_batch(i, batch) for i, batch in enumerate(batches)],
        return_exceptions=True
    )

    # Aggregate results
    episodes_created = 0
    chunks_processed = 0
    errors = []

    for result in batch_results:
        if isinstance(result, Exception):
            logger.error(f"Batch processing raised exception: {result}")
            errors.append(str(result))
            continue

        ep, ch, err = result
        episodes_created += ep
        chunks_processed += ch
        if err:
            errors.append(err)

    elapsed = time.time() - start_time

    # Estimate cost (rough approximation)
    # GPT-4o-mini: ~$0.000150 per 1k input tokens, ~$0.000600 per 1k output tokens
    # Assume ~500 tokens per chunk, ~50 output tokens per chunk
    cost_estimate = _estimate_cost(chunks_processed)

    # Check cost threshold
    cost_threshold = graphiti_config.get("cost_threshold_usd") or 1.0
    if cost_estimate > cost_threshold:
        logger.warning(
            f"Cost estimate ${cost_estimate:.4f} exceeds threshold "
            f"${cost_threshold:.2f} for {paper_key}"
        )

    success = episodes_created > 0 and len(errors) == 0

    # Update episode cache on success (deduplication for future runs)
    if success:
        episode_cache = get_episode_cache()
        episode_cache.add_paper(
            paper_key=paper_key,
            episode_count=episodes_created,
            chunks_processed=chunks_processed,
            success=True,
        )
        logger.debug(f"Updated episode cache for {paper_key}")
    elif episodes_created > 0:
        # Partial success (some errors but some episodes created)
        # Mark as failed so it can be retried
        episode_cache = get_episode_cache()
        episode_cache.add_paper(
            paper_key=paper_key,
            episode_count=episodes_created,
            chunks_processed=chunks_processed,
            success=False,
        )
        logger.debug(f"Marked {paper_key} as partially failed in episode cache")

    logger.info(
        f"Graphiti ingestion complete for {paper_key}: "
        f"episodes={episodes_created}, chunks={chunks_processed}, "
        f"elapsed={elapsed:.1f}s, cost=${cost_estimate:.4f}"
    )

    return IngestionResult(
        success=success,
        paper_key=paper_key,
        chunks_processed=chunks_processed,
        episodes_created=episodes_created,
        elapsed_seconds=elapsed,
        error="; ".join(errors) if errors else None,
        cost_estimate_usd=cost_estimate,
    )


def _create_batches(
    paper_key: str,
    chunks: List[str],
    metadata: Dict[str, Any],
    batch_size: int = 15,
) -> List[IngestionBatch]:
    """
    Create batches of chunks for episode ingestion.

    Combines multiple chunks into single episodes to reduce LLM API calls
    while staying within reasonable context limits.

    Args:
        paper_key: Zotero item key
        chunks: List of text chunks
        metadata: Paper metadata
        batch_size: Number of chunks per batch (10-20 recommended)

    Returns:
        List of IngestionBatch objects

    Note:
        Episode names include paper_key for linking between Agent-Zot and Graphiti schemas.
        Format: "Paper {paper_key} - Part {batch_num}/{total_batches}"
        This enables queries like: "What entities were extracted from paper ABC123?"
    """
    batches = []

    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i : i + batch_size]

        # Combine chunks with separators
        combined_text = "\n\n---\n\n".join(batch_chunks)

        # Create descriptive episode name with embedded item_key
        # This enables linking between Graphiti entities and Agent-Zot papers
        batch_num = (i // batch_size) + 1
        total_batches = (len(chunks) + batch_size - 1) // batch_size

        episode_name = f"Paper {paper_key} - Part {batch_num}/{total_batches}"

        # Augment batch metadata with item_key for potential future use
        batch_metadata = dict(metadata)
        batch_metadata["zotero_item_key"] = paper_key

        batches.append(
            IngestionBatch(
                episode_name=episode_name,
                combined_text=combined_text,
                chunk_count=len(batch_chunks),
                metadata=batch_metadata,
            )
        )

    return batches


def _estimate_cost(chunks_processed: int) -> float:
    """
    Estimate LLM API cost for chunk processing.

    Based on GPT-4o-mini pricing:
    - Input: $0.150 per 1M tokens
    - Output: $0.600 per 1M tokens

    Assumptions:
    - ~500 tokens per chunk (conservative)
    - ~50 output tokens per chunk (entity extraction)

    Args:
        chunks_processed: Number of chunks processed

    Returns:
        Estimated cost in USD
    """
    # Token estimates
    input_tokens_per_chunk = 500
    output_tokens_per_chunk = 50

    # Pricing (per million tokens)
    input_price_per_1m = 0.150
    output_price_per_1m = 0.600

    # Calculate costs
    total_input_tokens = chunks_processed * input_tokens_per_chunk
    total_output_tokens = chunks_processed * output_tokens_per_chunk

    input_cost = (total_input_tokens / 1_000_000) * input_price_per_1m
    output_cost = (total_output_tokens / 1_000_000) * output_price_per_1m

    return input_cost + output_cost


def should_ingest_to_graphiti(
    paper_key: str,
    metadata: Dict[str, Any],
    config: Dict[str, Any],
    force_reingest: bool = False,
) -> bool:
    """
    Determine if a paper should be ingested to Graphiti.

    Deduplication Checks (analogous to agent-zot's main pipeline):
    1. Graphiti enabled in config
    2. Paper has required filter tag (for Phase 1 selective ingestion)
    3. Not already processed in episode cache (unless force_reingest=True)

    This prevents duplicate entity extraction and ensures:
    - After bulk ingestion, only NEW papers are processed
    - Same paper never reprocessed (unless explicitly forced)
    - Saves API costs and processing time

    Args:
        paper_key: Zotero item key
        metadata: Paper metadata
        config: Agent-zot configuration
        force_reingest: If True, ignore cache (default: False)

    Returns:
        True if should ingest, False otherwise
    """
    graphiti_config = config.get("graphiti", {})

    # Check enabled
    if not graphiti_config.get("enabled", False):
        return False

    # Check filter tag (Phase 1 selective ingestion)
    filter_tag = graphiti_config.get("filter_tag")
    if filter_tag:
        paper_tags = metadata.get("tags", [])
        if filter_tag not in paper_tags:
            logger.debug(
                f"Paper {paper_key} missing tag '{filter_tag}', "
                f"skipping Graphiti check"
            )
            return False

    # DEDUPLICATION: Check episode cache (unless force_reingest)
    if not force_reingest:
        episode_cache = get_episode_cache()
        if episode_cache.has_paper(paper_key):
            logger.debug(
                f"Paper {paper_key} already in Graphiti episode cache, "
                f"skipping to prevent duplicate ingestion"
            )
            return False

    return True
