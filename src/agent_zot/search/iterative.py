"""
Iterative retrieval with query refinement.

This module provides functionality to analyze initial search results and reformulate
queries for improved retrieval. The refinement process extracts key concepts from
high-scoring results and generates alternative queries.
"""

import logging
from typing import Dict, List, Any, Optional
from collections import Counter
import re

logger = logging.getLogger(__name__)


def extract_key_concepts(results: List[Dict[str, Any]], top_n: int = 3) -> List[str]:
    """
    Extract key concepts from top search results.

    Analyzes titles, abstracts, and tags from highly relevant papers to identify
    important concepts that can improve query refinement.

    Args:
        results: List of search results with Zotero item data
        top_n: Number of top results to analyze for concept extraction

    Returns:
        List of key concept phrases extracted from results
    """
    if not results:
        return []

    # Analyze top N results
    top_results = results[:top_n]

    # Collect text from titles, abstracts, and tags
    text_corpus = []

    for result in top_results:
        zotero_item = result.get("zotero_item", {})
        data = zotero_item.get("data", {})

        # Extract title
        if title := data.get("title"):
            text_corpus.append(title)

        # Extract abstract
        if abstract := data.get("abstractNote"):
            text_corpus.append(abstract)

        # Extract tags
        if tags := data.get("tags"):
            for tag in tags:
                if tag_text := tag.get("tag"):
                    text_corpus.append(tag_text)

    # Extract noun phrases and important terms
    # Simple implementation: extract capitalized phrases and common terms
    concepts = []

    for text in text_corpus:
        # Find capitalized phrases (likely proper nouns, concepts)
        capitalized_phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        concepts.extend(capitalized_phrases)

        # Find technical terms (words with specific patterns)
        technical_terms = re.findall(r'\b[a-z]+(?:-[a-z]+)+\b', text.lower())
        concepts.extend(technical_terms)

    # Count frequency and return most common
    concept_counts = Counter(concepts)

    # Filter out very common/generic terms
    stopwords = {'The', 'This', 'That', 'These', 'Those', 'A', 'An', 'In', 'On', 'At', 'To', 'For', 'Of', 'And', 'Or', 'But'}
    filtered_concepts = [c for c, count in concept_counts.most_common(20) if c not in stopwords and count >= 2]

    return filtered_concepts[:10]  # Return top 10 concepts


def reformulate_query(
    original_query: str,
    initial_results: List[Dict[str, Any]],
    quality_metrics: Optional[Dict[str, Any]] = None
) -> List[str]:
    """
    Reformulate query based on initial search results.

    Generates alternative queries by:
    1. Extracting key concepts from high-quality results
    2. Expanding with related terms
    3. Narrowing focus if results are too broad
    4. Broadening scope if results are too sparse

    Args:
        original_query: The original search query
        initial_results: Results from initial search
        quality_metrics: Optional quality metrics from initial search

    Returns:
        List of reformulated query strings
    """
    if not initial_results:
        # No results - broaden query by making it more general
        # Remove specific modifiers and qualifiers
        broader_query = re.sub(r'\b(specific|particular|exact|precise)\b', '', original_query, flags=re.IGNORECASE)
        broader_query = re.sub(r'\s+', ' ', broader_query).strip()
        return [broader_query] if broader_query != original_query else [original_query]

    reformulated_queries = []

    # Extract key concepts from top results
    key_concepts = extract_key_concepts(initial_results, top_n=3)

    # Strategy 1: Add key concepts to original query
    if key_concepts:
        # Add most important concept
        concept_query = f"{original_query} {key_concepts[0]}"
        reformulated_queries.append(concept_query)

        # If we have multiple concepts, create combination query
        if len(key_concepts) >= 2:
            multi_concept_query = f"{original_query} {key_concepts[0]} {key_concepts[1]}"
            reformulated_queries.append(multi_concept_query)

    # Strategy 2: Use quality metrics to adjust specificity
    if quality_metrics:
        confidence = quality_metrics.get("confidence", "medium")
        coverage = quality_metrics.get("coverage", 0.5)

        # Low confidence or coverage - try alternative formulations
        if confidence == "low" or coverage < 0.3:
            # Try more specific query using concepts
            if key_concepts:
                specific_query = " ".join(key_concepts[:3])
                reformulated_queries.append(specific_query)

            # Try synonym expansion (basic implementation)
            synonym_map = {
                "neural": "brain cognitive neurological",
                "network": "system architecture framework",
                "learning": "training education acquisition",
                "memory": "recall retention cognition",
                "attention": "focus concentration awareness",
                "emotion": "affect feeling mood",
                "decision": "choice judgment reasoning",
                "language": "linguistic verbal communication",
                "vision": "visual perception sight",
                "motor": "movement action execution"
            }

            expanded_query = original_query
            for term, synonyms in synonym_map.items():
                if term in original_query.lower():
                    expanded_query = f"{original_query} {synonyms}"
                    break

            if expanded_query != original_query:
                reformulated_queries.append(expanded_query)

    # Strategy 3: Extract methodology or domain from results
    methods = []
    domains = []

    for result in initial_results[:3]:
        zotero_item = result.get("zotero_item", {})
        data = zotero_item.get("data", {})

        # Look for methodological terms in title/abstract
        text = f"{data.get('title', '')} {data.get('abstractNote', '')}"

        # Common methods
        if any(m in text.lower() for m in ['fmri', 'mri', 'neuroimaging', 'brain imaging']):
            methods.append('neuroimaging')
        if any(m in text.lower() for m in ['eeg', 'meg', 'electrophysiology']):
            methods.append('electrophysiology')
        if any(m in text.lower() for m in ['behavioral', 'behavior', 'task']):
            methods.append('behavioral')

        # Common domains
        if any(d in text.lower() for d in ['clinical', 'patient', 'disorder', 'disease']):
            domains.append('clinical')
        if any(d in text.lower() for d in ['cognitive', 'cognition']):
            domains.append('cognitive')

    # Add method-specific query
    if methods:
        method_query = f"{original_query} {methods[0]}"
        reformulated_queries.append(method_query)

    # Add domain-specific query
    if domains:
        domain_query = f"{original_query} {domains[0]}"
        reformulated_queries.append(domain_query)

    # Remove duplicates while preserving order
    seen = set()
    unique_queries = []
    for q in reformulated_queries:
        q_normalized = q.lower().strip()
        if q_normalized not in seen and q_normalized != original_query.lower():
            seen.add(q_normalized)
            unique_queries.append(q)

    return unique_queries[:3]  # Return top 3 reformulated queries


def iterative_search(
    semantic_search_instance,
    query: str,
    limit: int = 10,
    max_iterations: int = 2
) -> Dict[str, Any]:
    """
    Perform iterative search with query refinement.

    Process:
    1. Perform initial semantic search
    2. Analyze result quality
    3. If quality is low, reformulate query and search again
    4. Merge results from multiple iterations
    5. Return best results with refinement metadata

    Args:
        semantic_search_instance: ZoteroSemanticSearch instance
        query: Initial search query
        limit: Number of final results to return
        max_iterations: Maximum number of refinement iterations

    Returns:
        Dict with refined search results and metadata
    """
    logger.info(f"Starting iterative search for: '{query}'")

    # Initial search
    initial_results = semantic_search_instance.search(query, limit=limit * 2)

    if not initial_results.get("results"):
        return {
            "query": query,
            "limit": limit,
            "results": [],
            "total_found": 0,
            "iterations": 1,
            "refinements": [],
            "error": "No results found for initial query"
        }

    quality_metrics = initial_results.get("quality_metrics", {})
    confidence = quality_metrics.get("confidence", "medium")
    coverage = quality_metrics.get("coverage", 0.5)

    logger.info(f"Initial search: confidence={confidence}, coverage={coverage:.2f}")

    # Collect all results
    all_results = {}  # item_key -> result dict
    for result in initial_results["results"]:
        item_key = result.get("item_key")
        if item_key:
            all_results[item_key] = result

    refinements = []
    current_iteration = 1

    # Decide if refinement is needed
    needs_refinement = (
        confidence == "low" or
        coverage < 0.4 or
        len(initial_results["results"]) < limit
    )

    if needs_refinement and current_iteration < max_iterations:
        logger.info("Results quality low - attempting query refinement")

        # Reformulate query
        reformulated_queries = reformulate_query(
            query,
            initial_results["results"],
            quality_metrics
        )

        logger.info(f"Generated {len(reformulated_queries)} refined queries")

        # Try refined queries
        for refined_query in reformulated_queries:
            current_iteration += 1

            if current_iteration > max_iterations:
                break

            logger.info(f"Iteration {current_iteration}: searching with refined query: '{refined_query}'")

            try:
                refined_results = semantic_search_instance.search(refined_query, limit=limit * 2)

                # Track refinement
                refinements.append({
                    "iteration": current_iteration,
                    "query": refined_query,
                    "results_found": len(refined_results.get("results", [])),
                    "quality_metrics": refined_results.get("quality_metrics")
                })

                # Merge new results
                for result in refined_results.get("results", []):
                    item_key = result.get("item_key")
                    if item_key and item_key not in all_results:
                        all_results[item_key] = result

                logger.info(f"Refined search found {len(refined_results.get('results', []))} results")

                # Check if we have enough high-quality results now
                refined_quality = refined_results.get("quality_metrics", {})
                if refined_quality.get("confidence") == "high" and refined_quality.get("coverage", 0) >= 0.6:
                    logger.info("High-quality results achieved, stopping refinement")
                    break

            except Exception as e:
                logger.error(f"Error in refined search: {e}")
                refinements.append({
                    "iteration": current_iteration,
                    "query": refined_query,
                    "error": str(e)
                })

    # Sort all results by similarity score
    final_results = sorted(
        all_results.values(),
        key=lambda x: x.get("similarity_score", 0),
        reverse=True
    )[:limit]

    return {
        "query": query,
        "limit": limit,
        "results": final_results,
        "total_found": len(final_results),
        "iterations": current_iteration,
        "refinements": refinements,
        "initial_quality": quality_metrics,
        "final_result_count": len(all_results)
    }
