"""
Query decomposition for complex multi-concept queries.

This module provides functionality to break down complex queries into simpler
sub-queries, execute them in parallel, and intelligently merge the results.
"""

import logging
from typing import Dict, List, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

logger = logging.getLogger(__name__)


def identify_conjunctions(query: str) -> List[str]:
    """
    Identify conjunction patterns in a query (AND, OR, with, about, etc.).

    Args:
        query: Search query string

    Returns:
        List of identified conjunction words
    """
    # Common conjunction patterns
    conjunctions = []

    # Explicit boolean operators
    if re.search(r'\bAND\b', query, re.IGNORECASE):
        conjunctions.append('AND')
    if re.search(r'\bOR\b', query, re.IGNORECASE):
        conjunctions.append('OR')

    # Natural language conjunctions
    if re.search(r'\b(and|with|plus)\b', query, re.IGNORECASE):
        conjunctions.append('and')
    if re.search(r'\b(or|versus|vs)\b', query, re.IGNORECASE):
        conjunctions.append('or')

    # Prepositions indicating relationships
    if re.search(r'\b(in|about|regarding|concerning)\b', query, re.IGNORECASE):
        conjunctions.append('about')

    return conjunctions


def decompose_query(query: str) -> List[Dict[str, Any]]:
    """
    Decompose a complex query into simpler sub-queries.

    Handles various query patterns:
    - Boolean operators (AND, OR)
    - Natural language conjunctions (and, or, with)
    - Multi-concept queries with prepositions
    - Nested concepts

    Args:
        query: Complex search query

    Returns:
        List of sub-query dictionaries with 'query', 'type', and 'importance' fields
    """
    sub_queries = []

    # Pattern 1: Explicit AND/OR operators
    if re.search(r'\bAND\b', query, re.IGNORECASE):
        # Split on AND
        parts = re.split(r'\bAND\b', query, flags=re.IGNORECASE)
        for part in parts:
            part = part.strip()
            if part:
                sub_queries.append({
                    "query": part,
                    "type": "required",  # All parts are required for AND
                    "importance": 1.0
                })
        logger.info(f"Decomposed query with AND operator: {len(sub_queries)} sub-queries")
        return sub_queries

    if re.search(r'\bOR\b', query, re.IGNORECASE):
        # Split on OR
        parts = re.split(r'\bOR\b', query, flags=re.IGNORECASE)
        for part in parts:
            part = part.strip()
            if part:
                sub_queries.append({
                    "query": part,
                    "type": "optional",  # Any part is acceptable for OR
                    "importance": 0.7
                })
        logger.info(f"Decomposed query with OR operator: {len(sub_queries)} sub-queries")
        return sub_queries

    # Pattern 2: Natural language conjunctions
    if re.search(r'\b(and|with|plus)\b', query, re.IGNORECASE):
        # Split on and/with/plus
        parts = re.split(r'\b(and|with|plus)\b', query, flags=re.IGNORECASE)
        for i, part in enumerate(parts):
            part = part.strip()
            if part and part.lower() not in ['and', 'with', 'plus']:
                sub_queries.append({
                    "query": part,
                    "type": "required",
                    "importance": 1.0
                })
        logger.info(f"Decomposed query with natural conjunctions: {len(sub_queries)} sub-queries")
        return sub_queries

    # Pattern 3: Preposition patterns (e.g., "X in Y", "X about Y")
    preposition_pattern = r'^(.+?)\b(in|about|regarding|concerning|for|during|with respect to)\b(.+)$'
    if match := re.match(preposition_pattern, query, re.IGNORECASE):
        concept1 = match.group(1).strip()
        preposition = match.group(2).strip()
        concept2 = match.group(3).strip()

        # Main query is the full query
        sub_queries.append({
            "query": query,
            "type": "primary",
            "importance": 1.0
        })

        # Add individual concepts as supporting queries
        sub_queries.append({
            "query": concept1,
            "type": "supporting",
            "importance": 0.6
        })

        sub_queries.append({
            "query": concept2,
            "type": "supporting",
            "importance": 0.6
        })

        logger.info(f"Decomposed query with preposition '{preposition}': 3 sub-queries")
        return sub_queries

    # Pattern 4: Comma-separated concepts
    if ',' in query:
        parts = [p.strip() for p in query.split(',') if p.strip()]
        if len(parts) >= 2:
            # Original query is primary
            sub_queries.append({
                "query": query,
                "type": "primary",
                "importance": 1.0
            })

            # Individual parts are supporting
            for part in parts:
                sub_queries.append({
                    "query": part,
                    "type": "supporting",
                    "importance": 0.5
                })

            logger.info(f"Decomposed comma-separated query: {len(sub_queries)} sub-queries")
            return sub_queries

    # Pattern 5: Multiple noun phrases (complex heuristic)
    # Look for capitalized phrases that might be separate concepts
    capitalized_phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query)
    if len(capitalized_phrases) >= 2:
        # Keep original query as primary
        sub_queries.append({
            "query": query,
            "type": "primary",
            "importance": 1.0
        })

        # Add individual capitalized phrases as supporting
        for phrase in capitalized_phrases[:3]:  # Limit to 3
            if len(phrase.split()) >= 2:  # Only multi-word phrases
                sub_queries.append({
                    "query": phrase,
                    "type": "supporting",
                    "importance": 0.4
                })

        if len(sub_queries) > 1:
            logger.info(f"Decomposed query by noun phrases: {len(sub_queries)} sub-queries")
            return sub_queries

    # No decomposition patterns found - return original query
    logger.info("No decomposition pattern found, returning original query")
    return [{
        "query": query,
        "type": "primary",
        "importance": 1.0
    }]


def merge_decomposed_results(
    results_by_subquery: Dict[str, List[Dict[str, Any]]],
    sub_queries: List[Dict[str, Any]],
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Merge results from multiple sub-queries using weighted scoring.

    Sub-queries with higher importance contribute more to the final score.
    Results appearing in multiple sub-queries get higher combined scores.

    Args:
        results_by_subquery: Dict mapping sub-query strings to their results
        sub_queries: List of sub-query metadata dicts with importance scores
        limit: Number of final results to return

    Returns:
        List of merged and ranked result dictionaries
    """
    # Create importance lookup
    importance_by_query = {sq["query"]: sq["importance"] for sq in sub_queries}

    # Track cumulative scores for each paper
    paper_scores = {}  # item_key -> (score, result_dict)

    for subquery_text, results in results_by_subquery.items():
        importance = importance_by_query.get(subquery_text, 1.0)

        for rank, result in enumerate(results, start=1):
            item_key = result.get("item_key")
            if not item_key:
                continue

            # Calculate weighted score: (similarity * importance) / rank
            similarity = result.get("similarity_score", 0.0)
            rank_discount = 1.0 / rank
            weighted_score = similarity * importance * rank_discount

            if item_key in paper_scores:
                # Add to existing score (papers appearing in multiple queries get higher scores)
                existing_score, existing_result = paper_scores[item_key]
                paper_scores[item_key] = (existing_score + weighted_score, result)
            else:
                paper_scores[item_key] = (weighted_score, result)

    # Sort by combined score
    sorted_papers = sorted(
        paper_scores.items(),
        key=lambda x: x[1][0],  # Sort by score
        reverse=True
    )

    # Return top results with their combined scores
    final_results = []
    for item_key, (score, result) in sorted_papers[:limit]:
        # Add combined score to result
        result_with_score = result.copy()
        result_with_score["combined_score"] = round(score, 4)
        final_results.append(result_with_score)

    return final_results


def decomposed_search(
    semantic_search_instance,
    query: str,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Perform decomposed search on a complex query.

    Process:
    1. Analyze query to identify multiple concepts
    2. Decompose into simpler sub-queries
    3. Execute sub-queries in parallel
    4. Merge results using weighted scoring
    5. Return ranked results with decomposition metadata

    Args:
        semantic_search_instance: ZoteroSemanticSearch instance
        query: Complex search query
        limit: Number of final results to return

    Returns:
        Dict with decomposed search results and metadata
    """
    logger.info(f"Starting decomposed search for: '{query}'")

    # Decompose query
    sub_queries = decompose_query(query)

    logger.info(f"Decomposed into {len(sub_queries)} sub-queries")

    # If no decomposition (only 1 sub-query), just do regular search
    if len(sub_queries) == 1:
        logger.info("No decomposition needed, performing regular search")
        results = semantic_search_instance.search(query, limit=limit)
        return {
            "query": query,
            "limit": limit,
            "results": results.get("results", []),
            "total_found": len(results.get("results", [])),
            "decomposition": {
                "decomposed": False,
                "sub_queries": sub_queries,
                "reason": "Query is already simple"
            }
        }

    # Execute sub-queries in parallel
    results_by_subquery = {}
    errors_by_subquery = {}

    with ThreadPoolExecutor(max_workers=min(len(sub_queries), 5)) as executor:
        # Submit all sub-query searches
        futures = {}

        for sq in sub_queries:
            subquery_text = sq["query"]
            # Get more results for sub-queries to increase coverage
            future = executor.submit(
                semantic_search_instance.search,
                subquery_text,
                limit * 2
            )
            futures[future] = subquery_text

        # Collect results as they complete
        for future in as_completed(futures):
            subquery_text = futures[future]
            try:
                result = future.result()
                results_by_subquery[subquery_text] = result.get("results", [])
                logger.info(f"Sub-query '{subquery_text}' returned {len(result.get('results', []))} results")
            except Exception as e:
                logger.error(f"Error in sub-query '{subquery_text}': {e}")
                errors_by_subquery[subquery_text] = str(e)

    if not results_by_subquery:
        return {
            "query": query,
            "limit": limit,
            "results": [],
            "total_found": 0,
            "decomposition": {
                "decomposed": True,
                "sub_queries": sub_queries,
                "errors": errors_by_subquery
            },
            "error": "All sub-queries failed"
        }

    # Merge results
    logger.info("Merging results from sub-queries...")
    merged_results = merge_decomposed_results(
        results_by_subquery,
        sub_queries,
        limit
    )

    # Calculate statistics
    total_results_found = sum(len(r) for r in results_by_subquery.values())
    unique_papers = len(set(r.get("item_key") for results in results_by_subquery.values() for r in results if r.get("item_key")))

    return {
        "query": query,
        "limit": limit,
        "results": merged_results,
        "total_found": len(merged_results),
        "decomposition": {
            "decomposed": True,
            "sub_queries": sub_queries,
            "total_sub_results": total_results_found,
            "unique_papers_found": unique_papers,
            "errors": errors_by_subquery if errors_by_subquery else None
        }
    }
