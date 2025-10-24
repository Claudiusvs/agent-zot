"""
Automatic query expansion for vague semantic searches.

Expands short, vague queries with domain-specific related terms to improve search quality.
"""

from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


# Domain-specific expansion terms for cognitive neuroscience and psychology
EXPANSION_TERMS: Dict[str, List[str]] = {
    # Cognitive processes
    "attention": ["attentional control", "selective attention", "sustained attention", "divided attention"],
    "memory": ["working memory", "episodic memory", "semantic memory", "memory consolidation"],
    "executive function": ["cognitive control", "inhibitory control", "set shifting", "working memory"],
    "cognitive control": ["executive function", "inhibitory control", "attention regulation", "top-down control"],

    # Clinical/psychological constructs
    "dissociation": ["depersonalization", "derealization", "dissociative experiences", "altered states"],
    "trauma": ["PTSD", "post-traumatic stress", "traumatic stress", "trauma exposure"],
    "anxiety": ["anxious arousal", "worry", "fear response", "threat detection"],
    "depression": ["depressive symptoms", "mood disorder", "anhedonia", "dysphoria"],

    # Neural mechanisms
    "prefrontal": ["prefrontal cortex", "PFC", "dorsolateral prefrontal", "ventromedial prefrontal"],
    "amygdala": ["amygdalar", "threat processing", "fear conditioning", "emotional learning"],
    "hippocampus": ["hippocampal", "memory formation", "spatial memory", "pattern separation"],

    # Methods
    "fMRI": ["functional MRI", "neuroimaging", "brain imaging", "BOLD signal"],
    "EEG": ["electroencephalography", "event-related potentials", "ERP", "neural oscillations"],
    "behavioral": ["task performance", "reaction time", "accuracy", "experimental paradigm"],
}


def should_expand_query(query: str, threshold_words: int = 4) -> bool:
    """
    Determine if a query should be automatically expanded.

    Args:
        query: The search query
        threshold_words: Minimum word count before expansion is considered (default: 4)

    Returns:
        True if query should be expanded, False otherwise
    """
    words = query.split()

    # Don't expand if query is already long enough
    if len(words) > threshold_words:
        return False

    # Don't expand if query contains specific operators or quotes
    if any(op in query for op in ['"', 'AND', 'OR', 'NOT', '(', ')']):
        return False

    # Expand if query contains expandable terms
    query_lower = query.lower()
    for term in EXPANSION_TERMS.keys():
        if term in query_lower:
            return True

    return False


def expand_query(query: str, max_expansions: int = 2) -> Tuple[str, List[str]]:
    """
    Automatically expand a query with domain-specific related terms.

    Args:
        query: Original search query
        max_expansions: Maximum number of expansion terms to add per matched concept

    Returns:
        Tuple of (expanded_query, list of added terms)
    """
    if not should_expand_query(query):
        return query, []

    query_lower = query.lower()
    added_terms = []

    # Find matching expansion terms
    for term, expansions in EXPANSION_TERMS.items():
        if term in query_lower:
            # Add up to max_expansions terms
            selected_expansions = expansions[:max_expansions]
            added_terms.extend(selected_expansions)

    if not added_terms:
        return query, []

    # Build expanded query
    expanded_query = f"{query} {' '.join(added_terms)}"

    logger.info(f"Query expansion: '{query}' → '{expanded_query}'")
    logger.info(f"Added terms: {added_terms}")

    return expanded_query, added_terms


def expand_query_smart(query: str,
                       quality_metrics: Dict = None,
                       min_coverage: float = 0.40) -> Tuple[str, List[str], bool]:
    """
    Smart query expansion that considers initial search quality.

    Automatically expands query only if:
    1. Query appears vague (short, high-level)
    2. Initial search quality is low (if quality_metrics provided)

    Args:
        query: Original search query
        quality_metrics: Optional quality metrics from initial search
        min_coverage: Minimum coverage threshold for expansion (default: 0.40)

    Returns:
        Tuple of (expanded_query, added_terms, was_expanded)
    """
    # Check if expansion is needed based on quality metrics
    needs_expansion = False

    if quality_metrics:
        confidence = quality_metrics.get("confidence", "medium")
        coverage = quality_metrics.get("coverage", 0.5)

        # Expand if quality is low
        if confidence == "low" or coverage < min_coverage:
            needs_expansion = True
            logger.info(f"Query expansion triggered by low quality: confidence={confidence}, coverage={coverage:.2f}")
    else:
        # No quality metrics - decide based on query structure
        needs_expansion = should_expand_query(query)

    if not needs_expansion:
        return query, [], False

    # Perform expansion
    expanded_query, added_terms = expand_query(query)

    return expanded_query, added_terms, len(added_terms) > 0
