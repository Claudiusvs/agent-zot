"""
Intent-driven unified search with smart backend selection.

This module provides intelligent search coordination that:
1. Detects query intent (relationship, metadata, semantic)
2. Selects appropriate backends based on intent
3. Applies query refinement when needed
4. Uses Reciprocal Rank Fusion for result merging
5. Provides result provenance and deduplication
6. Escalates to comprehensive search when quality is inadequate
"""

import logging
import re
from typing import Dict, List, Any, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


def detect_query_intent(query: str) -> Tuple[str, float]:
    """
    Detect the primary intent of a search query.

    Analyzes query patterns to determine whether the user is asking about:
    - Entity discovery (which/what entities appear in passages)
    - Relationships (citations, collaborations, networks)
    - Metadata (specific authors, journals, years)
    - Semantic content (concepts, topics, findings)

    Args:
        query: The search query string

    Returns:
        Tuple of (intent_type, confidence) where intent_type is one of:
        - "entity": Query asking which/what entities appear in relevant passages
        - "relationship": Query about connections, networks, citations
        - "metadata": Query about specific papers, authors, journals
        - "semantic": Query about content, concepts, topics (default)
    """
    query_lower = query.lower()

    # Entity intent patterns (highest priority - very specific)
    # Matches "which/what [entity_type] in/appears/discussed/used in [topic]"
    entity_patterns = [
        r'\b(which|what)\s+(concepts?|methods?|theories|techniques?|approaches?|models?)\s+(appear|discussed|used|employed|applied|mentioned)\s+in\b',
        r'\b(which|what)\s+(concepts?|methods?|theories|techniques?|approaches?|models?)\s+(in|about)\s+(papers?|research|literature|studies)\b',
        r'\bwhich\s+(concepts?|methods?|theories|techniques?|approaches?|models?)\b',
        r'\bwhat\s+(concepts?|methods?|theories|techniques?|approaches?|models?)\s+(are|appear)\b',
    ]

    for pattern in entity_patterns:
        if re.search(pattern, query_lower):
            logger.info(f"Detected entity intent: '{query}' (pattern: {pattern})")
            return ("entity", 0.95)

    # Relationship intent patterns (high priority)
    relationship_patterns = [
        r'\bcollaborat\w*\b',  # collaborate, collaborated, collaboration, collaborating, etc.
        r'\bco-author\b',  # co-author (hyphenated)
        r'\bco author\b',  # co author (space)
        r'\b(citation|cited|citing|cites)\b',
        r'\b(network|connection|related to)\b',
        r'\b(who worked with|influenced by|builds on)\b',
        r'\b(relationship between|links between)\b',
        r'\bwho\s+(has\s+)?(studied|researched|worked|wrote|published|examined|investigated|explored)\b',
        r'\b(which|what)\s+(authors|researchers|scientists|scholars)\b',
        r'\b(researchers|authors|scholars)\s+(working|focusing|studying)\s+on\b',
    ]

    for pattern in relationship_patterns:
        if re.search(pattern, query_lower):
            logger.info(f"Detected relationship intent: '{query}' (pattern: {pattern})")
            return ("relationship", 0.9)

    # Metadata intent patterns (medium priority)
    # Name pattern handles: Smith, McDonald, DePrince, O'Brien, van der Waals
    metadata_patterns = [
        r'\bby\s+[A-Z][a-zA-Z\'\-]+(\s+[A-Z][a-zA-Z\'\-]+)*\b',  # "by [Author Name]"
        r'\b[A-Z][a-zA-Z\'\-]+\'s\s+(work|papers|research|study|studies)\b',  # "[Author]'s work"
        r'\bpublished in\s+\d{4}\b',  # "published in 2023"
        r'\bpublished in\s+[A-Z]',  # "published in Journal"
        r'\bin\s+\d{4}\b',  # "in 2023"
        r'\bfrom\s+\d{4}\b',  # "from 2020"
        r'\bauthor:\s*[A-Za-z]',  # "author: Smith"
    ]

    for pattern in metadata_patterns:
        if re.search(pattern, query):
            logger.info(f"Detected metadata intent: '{query}' (pattern: {pattern})")
            return ("metadata", 0.8)

    # Default to semantic intent
    logger.info(f"Detected semantic intent (default): '{query}'")
    return ("semantic", 0.7)


def check_neo4j_availability(semantic_search_instance) -> bool:
    """
    Check if Neo4j knowledge graph is available and populated.

    Args:
        semantic_search_instance: ZoteroSemanticSearch instance

    Returns:
        True if Neo4j is available and has nodes, False otherwise
    """
    if not semantic_search_instance.neo4j_client:
        logger.info("Neo4j client not initialized")
        return False

    try:
        # Quick check: get graph statistics (should be fast)
        stats = semantic_search_instance.neo4j_client.get_graph_statistics()

        if "error" in stats:
            logger.warning(f"Neo4j statistics error: {stats['error']}")
            return False

        # Check total nodes (papers + entities)
        total_nodes = stats.get("papers", 0) + stats.get("total_entities", 0)

        if total_nodes > 0:
            logger.info(f"Neo4j available with {total_nodes} nodes ({stats.get('papers', 0)} papers, {stats.get('total_entities', 0)} entities)")
            return True
        else:
            logger.info("Neo4j available but empty (0 nodes)")
            return False
    except Exception as e:
        logger.warning(f"Neo4j availability check failed: {e}")
        return False


def get_backend_weights(intent: str) -> Dict[str, float]:
    """
    Get RRF weighting for backends based on query intent.

    Args:
        intent: Query intent type ("entity", "relationship", "metadata", "semantic")

    Returns:
        Dict with weights for each backend
    """
    if intent == "entity":
        # Boost entity search for entity discovery queries
        return {
            "semantic": 0.4,
            "graph": 0.3,
            "metadata": 0.2,
            "entity": 1.0
        }
    elif intent == "relationship":
        # Boost graph search for relationship queries
        return {
            "semantic": 0.6,
            "graph": 1.0,
            "metadata": 0.4
        }
    elif intent == "metadata":
        # Boost metadata search for author/journal queries
        return {
            "semantic": 0.7,
            "graph": 0.3,
            "metadata": 1.0
        }
    else:  # semantic (default)
        # Boost semantic search for content queries
        return {
            "semantic": 1.0,
            "graph": 0.5,
            "metadata": 0.3
        }


def assess_result_quality(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Assess the quality of search results.

    Analyzes result count, score distribution, and coverage to determine
    if results are adequate or if escalation is needed.

    Args:
        results: List of search results

    Returns:
        Dict with quality metrics:
        - confidence: "high", "medium", or "low"
        - coverage: float between 0 and 1
        - needs_escalation: bool
    """
    if not results:
        return {
            "confidence": "low",
            "coverage": 0.0,
            "needs_escalation": True
        }

    result_count = len(results)

    # Extract similarity/relevance scores if available
    scores = []
    for result in results:
        if score := result.get("similarity_score") or result.get("rrf_score"):
            scores.append(score)

    # Calculate metrics
    if result_count >= 10:
        coverage = min(1.0, result_count / 10)
    else:
        coverage = result_count / 10

    # Determine confidence based on count and scores
    if result_count >= 10 and (not scores or max(scores) >= 0.7):
        confidence = "high"
        needs_escalation = False
    elif result_count >= 5 and (not scores or max(scores) >= 0.6):
        confidence = "medium"
        needs_escalation = False
    else:
        confidence = "low"
        needs_escalation = True

    return {
        "confidence": confidence,
        "coverage": coverage,
        "needs_escalation": needs_escalation
    }


def deduplicate_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate search results by item_key.

    Args:
        results: List of search results

    Returns:
        Deduplicated list (first occurrence kept)
    """
    seen_keys = set()
    deduplicated = []

    for result in results:
        item_key = result.get("item_key")
        if item_key and item_key not in seen_keys:
            seen_keys.add(item_key)
            deduplicated.append(result)

    return deduplicated


def add_provenance(
    results: List[Dict[str, Any]],
    backend_results: Dict[str, List[Dict[str, Any]]]
) -> List[Dict[str, Any]]:
    """
    Add provenance information to results showing which backends found each paper.

    Args:
        results: Merged results list
        backend_results: Dict mapping backend name to its results

    Returns:
        Results list with "found_in" field added to each result
    """
    # Build mapping of item_key to backends
    key_to_backends = {}

    for backend_name, backend_result_list in backend_results.items():
        for result in backend_result_list:
            item_key = result.get("item_key")
            if item_key:
                if item_key not in key_to_backends:
                    key_to_backends[item_key] = []
                key_to_backends[item_key].append(backend_name)

    # Add provenance to final results (deduplicate backends)
    for result in results:
        item_key = result.get("item_key")
        if item_key:
            backends = key_to_backends.get(item_key, ["unknown"])
            # Deduplicate backends while preserving order
            result["found_in"] = list(dict.fromkeys(backends))

    return results


def run_parallel_backends(
    semantic_search_instance,
    query: str,
    backends: List[str],
    limit: int
) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, str]]:
    """
    Run multiple search backends in parallel.

    Args:
        semantic_search_instance: ZoteroSemanticSearch instance
        query: Search query
        backends: List of backend names to run ("semantic", "graph", "metadata", "entity")
        limit: Result limit per backend

    Returns:
        Tuple of (results_by_backend, errors_by_backend)
    """
    from agent_zot.search.unified import convert_graph_entities_to_papers, convert_metadata_search_to_papers

    results_by_backend = {}
    errors_by_backend = {}

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}

        # Submit backend tasks
        if "semantic" in backends:
            futures[executor.submit(
                semantic_search_instance.search,
                query,
                limit * 2  # Get more for better overlap
            )] = "semantic"

        if "graph" in backends:
            futures[executor.submit(
                semantic_search_instance.graph_search,
                query,
                None,  # entity_types
                limit
            )] = "graph"

        if "metadata" in backends:
            futures[executor.submit(
                lambda: semantic_search_instance.zotero_client.items(
                    q=query,
                    qmode="titleCreatorYear",
                    limit=limit
                ),
            )] = "metadata"

        if "entity" in backends:
            futures[executor.submit(
                semantic_search_instance.enhanced_semantic_search,
                query,
                limit,
                None,  # filters
                True   # include_chunk_entities
            )] = "entity"

        # Collect results
        for future in as_completed(futures):
            backend = futures[future]
            try:
                result = future.result()

                # Convert results to consistent format
                if backend == "semantic":
                    results_by_backend[backend] = result.get("results", [])
                elif backend == "graph":
                    results_by_backend[backend] = convert_graph_entities_to_papers(result.get("results", []))
                elif backend == "metadata":
                    results_by_backend[backend] = convert_metadata_search_to_papers(result)
                elif backend == "entity":
                    results_by_backend[backend] = result.get("results", [])

                logger.info(f"{backend} search completed: {len(results_by_backend[backend])} results")
            except Exception as e:
                logger.error(f"{backend} search failed: {e}")
                errors_by_backend[backend] = str(e)

    return results_by_backend, errors_by_backend


def run_sequential_backends(
    semantic_search_instance,
    query: str,
    backends: List[str],
    limit: int
) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, str]]:
    """
    Run multiple search backends sequentially (one at a time).

    Used for Comprehensive Mode to prevent resource exhaustion from
    running 3+ heavy backends (Qdrant + Neo4j + Zotero) in parallel.

    Args:
        semantic_search_instance: ZoteroSemanticSearch instance
        query: Search query
        backends: List of backend names to run ("semantic", "graph", "metadata", "entity")
        limit: Result limit per backend

    Returns:
        Tuple of (results_by_backend, errors_by_backend)
    """
    from agent_zot.search.unified import convert_graph_entities_to_papers, convert_metadata_search_to_papers

    results_by_backend = {}
    errors_by_backend = {}

    # Run each backend sequentially
    for backend in backends:
        try:
            if backend == "semantic":
                logger.info("Running semantic search...")
                result = semantic_search_instance.search(query, limit * 2)
                results_by_backend[backend] = result.get("results", [])

            elif backend == "graph":
                logger.info("Running graph search...")
                result = semantic_search_instance.graph_search(query, None, limit)
                results_by_backend[backend] = convert_graph_entities_to_papers(result.get("results", []))

            elif backend == "metadata":
                logger.info("Running metadata search...")
                result = semantic_search_instance.zotero_client.items(
                    q=query,
                    qmode="titleCreatorYear",
                    limit=limit
                )
                results_by_backend[backend] = convert_metadata_search_to_papers(result)

            elif backend == "entity":
                logger.info("Running entity-enriched search...")
                result = semantic_search_instance.enhanced_semantic_search(
                    query,
                    limit,
                    None,  # filters
                    True   # include_chunk_entities
                )
                results_by_backend[backend] = result.get("results", [])

            logger.info(f"{backend} search completed: {len(results_by_backend[backend])} results")

        except Exception as e:
            logger.error(f"{backend} search failed: {e}")
            errors_by_backend[backend] = str(e)
            results_by_backend[backend] = []  # Empty results on failure

    return results_by_backend, errors_by_backend


def smart_search(
    semantic_search_instance,
    query: str,
    limit: int = 10,
    force_mode: Optional[str] = None
) -> Dict[str, Any]:
    """
    Perform intent-driven smart search with automatic backend selection.

    This is the main unified search function that replaces:
    - zot_semantic_search (Fast Mode)
    - zot_unified_search (Comprehensive Mode)
    - zot_refine_search (with refinement + escalation)
    - zot_enhanced_semantic_search (Entity-enriched Mode)

    Execution flow:
    1. Detect query intent (entity/relationship/metadata/semantic)
    2. Apply query refinement if query is vague
    3. Select backends based on intent:
       - Fast Mode: Qdrant only (semantic queries)
       - Entity-enriched Mode: Qdrant chunks + Neo4j entities (entity discovery)
       - Graph-enriched Mode: Qdrant + Neo4j (relationship queries)
       - Metadata-enriched Mode: Qdrant + Zotero API (metadata queries)
       - Comprehensive Mode: All backends (fallback only)
    4. Execute search with appropriate backends
    5. Assess result quality
    6. Escalate to comprehensive if needed
    7. Deduplicate and add provenance

    Args:
        semantic_search_instance: ZoteroSemanticSearch instance
        query: Search query string
        limit: Maximum number of results to return
        force_mode: Optional mode override ("fast", "comprehensive")

    Returns:
        Dict with search results and metadata
    """
    from agent_zot.search.iterative import reformulate_query
    from agent_zot.search.unified import reciprocal_rank_fusion
    from agent_zot.utils.query_expansion import expand_query_smart

    logger.info(f"Starting smart search for: '{query}'")

    # Phase 1: Query Analysis & Refinement
    logger.info("Phase 1: Query analysis and refinement")

    # Detect intent
    intent, intent_confidence = detect_query_intent(query)
    logger.info(f"Query intent: {intent} (confidence: {intent_confidence})")

    # Try query expansion for vague queries
    expanded_query, added_terms, was_expanded = expand_query_smart(query)
    if was_expanded:
        logger.info(f"Query expanded: '{query}' -> '{expanded_query}' (added: {added_terms})")
        query_to_use = expanded_query
    else:
        query_to_use = query

    # Phase 2: Backend Selection
    logger.info("Phase 2: Backend selection based on intent")

    # Check Neo4j availability
    neo4j_available = check_neo4j_availability(semantic_search_instance)

    # Select backends based on intent and force_mode
    if force_mode == "fast":
        backends = ["semantic"]
        mode_description = "Fast Mode (forced)"
    elif force_mode == "comprehensive":
        backends = ["semantic", "graph", "metadata"] if neo4j_available else ["semantic", "metadata"]
        mode_description = "Comprehensive Mode (forced)"
    elif intent == "entity" and neo4j_available:
        backends = ["entity"]
        mode_description = "Entity-enriched Mode"
    elif intent == "relationship" and neo4j_available:
        backends = ["semantic", "graph"]
        mode_description = "Graph-enriched Mode"
    elif intent == "metadata":
        backends = ["semantic", "metadata"]
        mode_description = "Metadata-enriched Mode"
    else:  # semantic intent or Neo4j unavailable
        backends = ["semantic"]
        mode_description = "Fast Mode"

    logger.info(f"Selected mode: {mode_description}")
    logger.info(f"Backends to use: {backends}")

    # Get intent-based backend weights
    weights = get_backend_weights(intent)

    # Phase 3: Execute Search
    logger.info("Phase 3: Executing search across selected backends")

    # Use sequential execution for 3+ backends (Comprehensive Mode) to prevent resource exhaustion
    # Use parallel execution for 1-2 backends (Fast/Graph-enriched/Metadata-enriched) for speed
    if len(backends) >= 3:
        logger.info("Using sequential execution (3+ backends - prevents resource exhaustion)")
        results_by_backend, errors_by_backend = run_sequential_backends(
            semantic_search_instance,
            query_to_use,
            backends,
            limit
        )
    else:
        logger.info(f"Using parallel execution ({len(backends)} backend(s) - safe and fast)")
        results_by_backend, errors_by_backend = run_parallel_backends(
            semantic_search_instance,
            query_to_use,
            backends,
            limit
        )

    if not results_by_backend:
        return {
            "query": query,
            "expanded_query": query_to_use if was_expanded else None,
            "intent": intent,
            "mode": mode_description,
            "results": [],
            "total_found": 0,
            "error": "All search backends failed",
            "errors_by_backend": errors_by_backend
        }

    # Phase 4: Merge Results (if multiple backends)
    logger.info("Phase 4: Merging results")

    if len(backends) == 1:
        # Single backend - no merging needed
        final_results = results_by_backend.get(backends[0], [])[:limit]
    else:
        # Multiple backends - use RRF
        ranked_lists = [results for results in results_by_backend.values() if results]
        merged_rankings = reciprocal_rank_fusion(ranked_lists)

        # Build enriched items cache
        enriched_items_cache = {}
        if semantic_result := results_by_backend.get("semantic"):
            for result in semantic_result:
                if result.get("zotero_item"):
                    enriched_items_cache[result["item_key"]] = result

        # Build final results with RRF scores
        final_results = []
        for item_key, rrf_score in merged_rankings[:limit]:
            if item_key in enriched_items_cache:
                result = enriched_items_cache[item_key].copy()
                result["rrf_score"] = round(rrf_score, 4)
                final_results.append(result)
            else:
                # Fetch item if not in cache
                try:
                    zotero_item = semantic_search_instance.zotero_client.item(item_key)
                    final_results.append({
                        "item_key": item_key,
                        "rrf_score": round(rrf_score, 4),
                        "zotero_item": zotero_item,
                        "query": query
                    })
                except Exception as e:
                    logger.error(f"Error fetching item {item_key}: {e}")

    # Phase 5: Quality Assessment
    logger.info("Phase 5: Assessing result quality")

    quality = assess_result_quality(final_results)
    logger.info(f"Quality assessment: {quality}")

    # Phase 6: Escalation (if needed)
    if quality["needs_escalation"] and force_mode != "comprehensive" and len(backends) < 3:
        logger.info("Phase 6: Result quality inadequate - escalating to Comprehensive Mode")

        # Add remaining backends
        all_backends = ["semantic", "graph", "metadata"] if neo4j_available else ["semantic", "metadata"]
        additional_backends = [b for b in all_backends if b not in backends]

        if additional_backends:
            # Use sequential for 2+ additional backends, parallel for 1
            if len(additional_backends) >= 2:
                logger.info(f"Running {len(additional_backends)} additional backends sequentially")
                additional_results, additional_errors = run_sequential_backends(
                    semantic_search_instance,
                    query_to_use,
                    additional_backends,
                    limit
                )
            else:
                logger.info(f"Running {len(additional_backends)} additional backend in parallel")
                additional_results, additional_errors = run_parallel_backends(
                    semantic_search_instance,
                    query_to_use,
                    additional_backends,
                    limit
                )

            # Merge with existing results
            results_by_backend.update(additional_results)
            errors_by_backend.update(additional_errors)

            # Re-merge all results
            ranked_lists = [results for results in results_by_backend.values() if results]
            merged_rankings = reciprocal_rank_fusion(ranked_lists)

            # Rebuild final results
            enriched_items_cache = {}
            if semantic_result := results_by_backend.get("semantic"):
                for result in semantic_result:
                    if result.get("zotero_item"):
                        enriched_items_cache[result["item_key"]] = result

            final_results = []
            for item_key, rrf_score in merged_rankings[:limit]:
                if item_key in enriched_items_cache:
                    result = enriched_items_cache[item_key].copy()
                    result["rrf_score"] = round(rrf_score, 4)
                    final_results.append(result)
                else:
                    try:
                        zotero_item = semantic_search_instance.zotero_client.item(item_key)
                        final_results.append({
                            "item_key": item_key,
                            "rrf_score": round(rrf_score, 4),
                            "zotero_item": zotero_item,
                            "query": query
                        })
                    except Exception as e:
                        logger.error(f"Error fetching item {item_key}: {e}")

            mode_description = "Comprehensive Mode (escalated)"
            quality = assess_result_quality(final_results)

    # Phase 7: Deduplication & Provenance
    logger.info("Phase 7: Deduplicating and adding provenance")

    final_results = deduplicate_results(final_results)
    final_results = add_provenance(final_results, results_by_backend)

    # Build response
    return {
        "query": query,
        "expanded_query": query_to_use if was_expanded else None,
        "intent": intent,
        "intent_confidence": intent_confidence,
        "mode": mode_description,
        "backends_used": list(results_by_backend.keys()),
        "backend_weights": weights,
        "results": final_results,
        "total_found": len(final_results),
        "quality_metrics": quality,
        "errors_by_backend": errors_by_backend if errors_by_backend else None
    }
