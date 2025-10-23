"""
Unified search using Reciprocal Rank Fusion (RRF).

This module provides functionality to merge results from multiple search backends
(semantic/vector, graph/Neo4j, and metadata) using the Reciprocal Rank Fusion algorithm.
"""

import logging
from typing import Dict, List, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    ranked_lists: List[List[Dict[str, Any]]],
    k: int = 60
) -> List[Tuple[str, float]]:
    """
    Merge multiple ranked lists using Reciprocal Rank Fusion algorithm.

    The RRF formula is: RRF_score(item) = Σ 1/(k + rank_i)
    where rank_i is the rank of the item in list i.

    Args:
        ranked_lists: List of result lists from different search methods.
                     Each list contains dicts with at least an 'item_key' field.
        k: Constant for RRF formula (default: 60, as per original paper)

    Returns:
        List of (item_key, rrf_score) tuples sorted by RRF score (descending)

    Reference:
        Cormack, G. V., Clarke, C. L., & Buettcher, S. (2009).
        Reciprocal rank fusion outperforms condorcet and individual rank learning methods.
    """
    rrf_scores = {}

    for results in ranked_lists:
        for rank, item in enumerate(results, start=1):
            item_key = item.get("item_key")
            if item_key:
                # Add this item's contribution to the RRF score
                rrf_scores[item_key] = rrf_scores.get(item_key, 0) + 1 / (k + rank)

    # Sort by RRF score descending
    sorted_items = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_items


def convert_graph_entities_to_papers(graph_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert Neo4j graph entity results to paper-like format for RRF merging.

    Args:
        graph_results: List of entity results from Neo4j graph search

    Returns:
        List of dicts with 'item_key' field extracted from related papers
    """
    papers = []
    seen_keys = set()

    for entity in graph_results:
        # Extract related paper keys from the entity
        # Neo4j results may have different structures, adapt as needed
        if related_papers := entity.get("related_papers"):
            for paper in related_papers:
                if paper_key := paper.get("item_key"):
                    if paper_key not in seen_keys:
                        papers.append({"item_key": paper_key})
                        seen_keys.add(paper_key)

        # Some graph entities might directly have paper keys
        if paper_key := entity.get("paper_key"):
            if paper_key not in seen_keys:
                papers.append({"item_key": paper_key})
                seen_keys.add(paper_key)

    return papers


def convert_metadata_search_to_papers(metadata_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert Zotero API metadata search results to consistent format for RRF.

    Args:
        metadata_results: List of items from Zotero API search

    Returns:
        List of dicts with 'item_key' field
    """
    papers = []

    for item in metadata_results:
        # Zotero API returns items with 'key' in different places
        if key := item.get("key"):
            papers.append({"item_key": key})
        elif data := item.get("data"):
            if key := data.get("key"):
                papers.append({"item_key": key})

    return papers


def unified_search(
    semantic_search_instance,
    query: str,
    limit: int = 10,
    semantic_weight: float = 1.0,
    graph_weight: float = 1.0,
    metadata_weight: float = 1.0
) -> Dict[str, Any]:
    """
    Perform unified search across multiple backends using Reciprocal Rank Fusion.

    Combines:
    - Semantic search (Qdrant vector DB)
    - Graph search (Neo4j knowledge graph) - if available
    - Metadata search (Zotero API keyword search)

    Args:
        semantic_search_instance: ZoteroSemanticSearch instance
        query: Search query string
        limit: Number of final results to return
        semantic_weight: Weight for semantic search (default: 1.0)
        graph_weight: Weight for graph search (default: 1.0)
        metadata_weight: Weight for metadata search (default: 1.0)

    Returns:
        Dict with unified search results and metadata
    """
    logger.info(f"Performing unified search for: '{query}'")

    results_by_backend = {}
    errors_by_backend = {}

    # Run searches in parallel for efficiency
    with ThreadPoolExecutor(max_workers=3) as executor:
        # Submit all search tasks
        futures = {}

        # Semantic search (always available)
        futures[executor.submit(
            semantic_search_instance.search,
            query,
            limit * 2  # Get more results to increase overlap with other methods
        )] = "semantic"

        # Graph search (if Neo4j is enabled)
        if semantic_search_instance.neo4j_client:
            futures[executor.submit(
                semantic_search_instance.graph_search,
                query,
                None,  # entity_types
                limit
            )] = "graph"

        # Metadata search via Zotero API
        futures[executor.submit(
            lambda: semantic_search_instance.zotero_client.items(
                q=query,
                qmode="titleCreatorYear",
                limit=limit
            ),
        )] = "metadata"

        # Collect results as they complete
        for future in as_completed(futures):
            backend = futures[future]
            try:
                result = future.result()
                results_by_backend[backend] = result
                logger.info(f"{backend} search completed successfully")
            except Exception as e:
                logger.error(f"{backend} search failed: {e}")
                errors_by_backend[backend] = str(e)

    # Prepare ranked lists for RRF
    ranked_lists = []
    backend_contributions = {}

    # Process semantic search results
    if semantic_result := results_by_backend.get("semantic"):
        semantic_papers = semantic_result.get("results", [])
        if semantic_papers:
            ranked_lists.append(semantic_papers)
            backend_contributions["semantic"] = len(semantic_papers)
            logger.info(f"Semantic search contributed {len(semantic_papers)} papers")

    # Process graph search results
    if graph_result := results_by_backend.get("graph"):
        graph_papers = convert_graph_entities_to_papers(graph_result.get("results", []))
        if graph_papers:
            ranked_lists.append(graph_papers)
            backend_contributions["graph"] = len(graph_papers)
            logger.info(f"Graph search contributed {len(graph_papers)} papers")

    # Process metadata search results
    if metadata_result := results_by_backend.get("metadata"):
        metadata_papers = convert_metadata_search_to_papers(metadata_result)
        if metadata_papers:
            ranked_lists.append(metadata_papers)
            backend_contributions["metadata"] = len(metadata_papers)
            logger.info(f"Metadata search contributed {len(metadata_papers)} papers")

    if not ranked_lists:
        return {
            "query": query,
            "results": [],
            "total_found": 0,
            "error": "All search backends failed",
            "errors_by_backend": errors_by_backend
        }

    # Apply Reciprocal Rank Fusion
    logger.info("Applying Reciprocal Rank Fusion...")
    merged_rankings = reciprocal_rank_fusion(ranked_lists)

    # Build cache of already-enriched items from semantic search results
    # to avoid redundant Zotero API calls
    enriched_items_cache = {}
    if semantic_result := results_by_backend.get("semantic"):
        for result in semantic_result.get("results", []):
            if result.get("zotero_item"):
                enriched_items_cache[result["item_key"]] = result["zotero_item"]

    # Fetch full details for top results
    final_results = []
    for item_key, rrf_score in merged_rankings[:limit]:
        try:
            # Check if we already have this item from semantic search
            if item_key in enriched_items_cache:
                zotero_item = enriched_items_cache[item_key]
                logger.debug(f"Reusing cached Zotero item for {item_key}")
            else:
                # Fetch only if not already enriched
                zotero_item = semantic_search_instance.zotero_client.item(item_key)
                logger.debug(f"Fetched Zotero item for {item_key}")

            final_results.append({
                "item_key": item_key,
                "rrf_score": round(rrf_score, 4),
                "zotero_item": zotero_item,
                "query": query
            })
        except Exception as e:
            logger.error(f"Error fetching item {item_key}: {e}")
            # Include item without full details
            final_results.append({
                "item_key": item_key,
                "rrf_score": round(rrf_score, 4),
                "query": query,
                "error": f"Could not fetch full item: {e}"
            })

    return {
        "query": query,
        "limit": limit,
        "results": final_results,
        "total_found": len(final_results),
        "backend_contributions": backend_contributions,
        "errors_by_backend": errors_by_backend if errors_by_backend else None
    }
