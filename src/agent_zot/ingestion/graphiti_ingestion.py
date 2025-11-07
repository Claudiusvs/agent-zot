"""
Graphiti ingestion module for autonomous entity extraction.

Handles batch ingestion of paper chunks to Graphiti MCP server with
cost optimization, error handling, and selective filtering by tags.
"""

import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from agent_zot.clients.graphiti_client import (
    GraphitiClient,
    GraphitiUnavailableError,
    GraphitiClientError,
)

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
) -> IngestionResult:
    """
    Ingest paper chunks to Graphiti for autonomous entity extraction.

    This function:
    1. Checks if Graphiti is enabled and available
    2. Batches chunks to optimize LLM API costs
    3. Sends batches to Graphiti asynchronously
    4. Tracks metrics (time, cost, entity count)
    5. Gracefully degrades if Graphiti unavailable

    Args:
        paper_key: Zotero item key
        chunks: List of text chunks from PDF
        metadata: Paper metadata (title, authors, etc.)
        config: Agent-zot configuration dict
        client: Optional GraphitiClient instance (for testing)

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
        # Get Neo4j config (defaults from agent-zot config or fallback)
        neo4j_config = config.get("neo4j_graphrag", {})
        client = GraphitiClient(
            neo4j_uri=neo4j_config.get("neo4j_uri", "bolt://localhost:7687"),
            neo4j_user=neo4j_config.get("neo4j_user", "neo4j"),
            neo4j_password=neo4j_config.get("neo4j_password", "demodemo"),
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
    batch_size = graphiti_config.get("batch_size", 15)
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

    # Ingest batches
    episodes_created = 0
    chunks_processed = 0
    errors = []

    for i, batch in enumerate(batches):
        try:
            result = await client.add_paper_chunk(
                chunk_text=batch.combined_text,
                paper_key=paper_key,
                metadata=batch.metadata,
                episode_name=batch.episode_name,
            )

            if result.get("success"):
                episodes_created += 1
                chunks_processed += batch.chunk_count
                logger.debug(
                    f"Batch {i+1}/{len(batches)} ingested: "
                    f"{batch.chunk_count} chunks"
                )
            else:
                errors.append(f"Batch {i+1} failed: {result.get('error')}")

        except (GraphitiUnavailableError, GraphitiClientError) as e:
            logger.error(
                f"Error ingesting batch {i+1} for {paper_key}: {e}"
            )
            errors.append(f"Batch {i+1}: {str(e)}")
            # Continue with remaining batches instead of failing completely

    elapsed = time.time() - start_time

    # Estimate cost (rough approximation)
    # GPT-4o-mini: ~$0.000150 per 1k input tokens, ~$0.000600 per 1k output tokens
    # Assume ~500 tokens per chunk, ~50 output tokens per chunk
    cost_estimate = _estimate_cost(chunks_processed)

    # Check cost threshold
    cost_threshold = graphiti_config.get("cost_threshold_usd", 1.0)
    if cost_estimate > cost_threshold:
        logger.warning(
            f"Cost estimate ${cost_estimate:.4f} exceeds threshold "
            f"${cost_threshold:.2f} for {paper_key}"
        )

    success = episodes_created > 0 and len(errors) == 0

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
) -> bool:
    """
    Determine if a paper should be ingested to Graphiti.

    Checks:
    1. Graphiti enabled in config
    2. Paper has required filter tag (for Phase 1)
    3. Not already processed (future: check episode cache)

    Args:
        paper_key: Zotero item key
        metadata: Paper metadata
        config: Agent-zot configuration

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

    # Future: Check if already processed
    # This would require maintaining a cache of processed paper keys
    # For Phase 1 prototype, we always re-process

    return True
