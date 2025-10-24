"""
Unified intelligent graph exploration tool for Agent-Zot.

Consolidates all graph analysis tools into a single intelligent interface that
automatically detects exploration intent and selects the optimal exploration
strategy (graph-based OR content-based).

Nine Execution Modes:
1. Citation Chain Mode - Multi-hop citation analysis (Neo4j)
2. Seminal Papers Mode - Influential papers by PageRank (Neo4j)
3. Related Papers Mode - Papers connected via shared entities (Neo4j)
4. Collaborator Network Mode - Co-authorship networks (Neo4j)
5. Concept Network Mode - Concept propagation through papers (Neo4j)
6. Topic Evolution Mode - Temporal trajectory analysis (Neo4j)
7. Venue Analysis Mode - Publication outlet patterns (Neo4j)
8. Content Similarity Mode - Vector-based 'More Like This' discovery (Qdrant)
9. Comprehensive Mode - Multi-strategy exploration with result merging
"""

import re
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================================
# Intent Detection Patterns (Domain-Agnostic)
# ============================================================================

# Citation Chain Mode patterns
CITATION_PATTERNS = [
    r'\bcit(ing|ation|ed?)\s+(papers?|chain|network)\b',
    r'\bpapers?\s+(citing|that\s+cite)\b',
    r'\bcitation\s+(chain|network|path)\b',
    r'\bpapers?\s+citing\s+papers?\s+(citing|that\s+cite)\b',
    r'\b(multi-hop|multihop)\s+cit',
]

# Seminal Papers Mode patterns
INFLUENCE_PATTERNS = [
    r'\b(seminal|influential|foundational|key|important|highly-cited)\s+papers?\b',
    r'\bmost\s+(influential|cited|important)\b',
    r'\b(top|best|leading)\s+papers?\b',
    r'\bPageRank\b',
    r'\binfluence\s+(score|metric|analysis)\b',
]

# Content Similarity Mode patterns (check BEFORE Related Papers - more specific)
CONTENT_SIMILARITY_PATTERNS = [
    r'\b(similar|like|resembling)\s+(to|this)\b',
    r'\bmore\s+(like|similar)\b',
    r'\bpapers?\s+(like|similar\s+to)\s+(this|[A-Z0-9]{8})\b',
    r'\bcontent-based\s+similarit',
    r'\bsemantically\s+similar\b',
    r'\b(methodology|approach)\s+similar\b',
]

# Related Papers Mode patterns (graph-based relationships)
RELATED_PATTERNS = [
    r'\b(related|connected)\s+(papers?|to)\b',  # Removed "similar" - now in Content Similarity
    r'\bpapers?\s+(related|connected)\s+to\b',
    r'\bshared\s+(entities|authors?|concepts?)\b',
    r'\bwhat\s+(else|other\s+papers?)\s+(is|are)\s+(related|connected)\b',
]

# Collaborator Network Mode patterns
COLLABORATION_PATTERNS = [
    r'\bcollaborat\w*\b',
    r'\bco-author',
    r'\bco author\b',
    r'\b(worked|works|working)\s+with\b',
    r'\bauthorship\s+network\b',
    r'\bwho\s+(did|does)\s+\w+\s+(work|collaborate)\s+with\b',
]

# Concept Network Mode patterns
CONCEPT_PATTERNS = [
    r'\bconcepts?\s+(related|connected)\s+to\b',
    r'\b(related|connected)\s+concepts?\b',
    r'\bconcept\s+(network|propagation|relationships?)\b',
    r'\b(intermediate|bridging)\s+concepts?\b',
]

# Topic Evolution Mode patterns
TEMPORAL_PATTERNS = [
    r'\b(evolv(e|ed|ing|ution)|develop(ed|ment)|progress(ed|ion))\b.*\b(from|since|over|between)\b.*\d{4}',
    r'\btrack\w*\b.*\b(over\s+time|temporal|chronological|historical)\b',
    r'\bhow\s+(did|has)\b.*\b(chang(e|ed)|evolv(e|ed)|develop(ed))\b',
    r'\b(trend|trajectory|timeline)\b.*\d{4}',
    r'\bfrom\s+\d{4}\s+to\s+\d{4}\b',
]

# Venue Analysis Mode patterns
VENUE_PATTERNS = [
    r'\b(journal|conference|venue|publication\s+outlet)s?\b',
    r'\bwhere\s+(was|were|are|is)\b.*\bpublished\b',
    r'\b(top|best|leading)\s+(journals?|conferences?|venues?)\b',
    r'\bpublication\s+(venue|outlet|pattern)s?\b',
]


def detect_graph_intent(query: str) -> Tuple[str, float, Dict[str, Any]]:
    """
    Detect graph exploration intent from query text.

    Args:
        query: User's query string

    Returns:
        Tuple of (intent, confidence, extracted_params) where intent is one of:
        - "citation" - Citation chain analysis
        - "influence" - Seminal/influential papers
        - "content_similarity" - Vector-based content similarity
        - "related" - Papers connected via entities
        - "collaboration" - Co-authorship networks
        - "concept" - Concept propagation
        - "temporal" - Topic evolution over time
        - "venue" - Publication venue analysis
        - "exploratory" - General exploration (Comprehensive Mode)
    """
    query_lower = query.lower()
    extracted_params = {}

    # Check Citation Chain patterns
    for pattern in CITATION_PATTERNS:
        if re.search(pattern, query_lower):
            logger.info(f"Detected CITATION intent: pattern '{pattern}' matched")
            return ("citation", 0.90, extracted_params)

    # Check Influence patterns
    for pattern in INFLUENCE_PATTERNS:
        if re.search(pattern, query_lower):
            logger.info(f"Detected INFLUENCE intent: pattern '{pattern}' matched")
            return ("influence", 0.90, extracted_params)

    # Check Content Similarity patterns (before Related Papers - more specific)
    for pattern in CONTENT_SIMILARITY_PATTERNS:
        if re.search(pattern, query_lower):
            logger.info(f"Detected CONTENT_SIMILARITY intent: pattern '{pattern}' matched")
            return ("content_similarity", 0.85, extracted_params)

    # Check Collaboration patterns
    for pattern in COLLABORATION_PATTERNS:
        if re.search(pattern, query_lower):
            logger.info(f"Detected COLLABORATION intent: pattern '{pattern}' matched")
            # Try to extract author name
            author_match = re.search(r'(?:with|of|by|for)\s+([A-Z][a-zA-Z\'\-]+(?:\s+[A-Z][a-zA-Z\'\-]+)*)', query)
            if author_match:
                extracted_params["author"] = author_match.group(1)
            return ("collaboration", 0.90, extracted_params)

    # Check Temporal patterns
    for pattern in TEMPORAL_PATTERNS:
        if re.search(pattern, query_lower):
            logger.info(f"Detected TEMPORAL intent: pattern '{pattern}' matched")
            # Try to extract years - use (?:19|20) to make it non-capturing
            years = re.findall(r'\b(?:19|20)\d{2}\b', query)
            if len(years) >= 2:
                extracted_params["start_year"] = int(years[0])
                extracted_params["end_year"] = int(years[-1])
            # Try to extract concept - stop before evolution verbs
            concept_match = re.search(r'(?:of|on|about|for)\s+([a-zA-Z\s]{3,30}?)\s+(?:evolv|chang|develop|progress|emerg|from|since|over|between)', query)
            if concept_match:
                extracted_params["concept"] = concept_match.group(1).strip()
            return ("temporal", 0.85, extracted_params)

    # Check Concept patterns
    for pattern in CONCEPT_PATTERNS:
        if re.search(pattern, query_lower):
            logger.info(f"Detected CONCEPT intent: pattern '{pattern}' matched")
            # Try to extract concept name
            concept_match = re.search(r'(?:to|of|around|for)\s+([a-zA-Z\s]{3,30})', query)
            if concept_match:
                extracted_params["concept"] = concept_match.group(1).strip()
            return ("concept", 0.85, extracted_params)

    # Check Venue patterns
    for pattern in VENUE_PATTERNS:
        if re.search(pattern, query_lower):
            logger.info(f"Detected VENUE intent: pattern '{pattern}' matched")
            return ("venue", 0.80, extracted_params)

    # Check Related Papers patterns
    for pattern in RELATED_PATTERNS:
        if re.search(pattern, query_lower):
            logger.info(f"Detected RELATED intent: pattern '{pattern}' matched")
            return ("related", 0.75, extracted_params)

    # Default: exploratory/comprehensive
    logger.info("Detected EXPLORATORY intent: no specific pattern matched (default)")
    return ("exploratory", 0.60, extracted_params)


# ============================================================================
# Mode Implementation Functions
# ============================================================================

def run_citation_chain_mode(
    neo4j_client,
    paper_key: str,
    max_hops: int = 2,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Citation Chain Mode: Find papers citing papers that cite the given paper.

    Multi-hop citation network analysis.
    """
    logger.info(f"Running CITATION CHAIN Mode: paper_key={paper_key}, max_hops={max_hops}")

    try:
        # Neo4j client returns a list directly
        results = neo4j_client.find_citation_chain(paper_key, max_hops=max_hops, limit=limit)

        if not results:
            return {
                "success": False,
                "error": f"No citation chain found for paper: {paper_key}",
                "mode": "citation"
            }

        # Format results as markdown
        output = [f"# Citation Chain for {paper_key}\n"]
        output.append(f"Found {len(results)} papers in citation network (max {max_hops} hops):\n")

        for paper in results:
            hops = paper.get("citation_hops", 0)
            title = paper.get("title", "Unknown")
            year = paper.get("year", "N/A")
            key = paper.get("item_key", "")
            path = paper.get("citation_path", [])

            output.append(f"## {title} ({year})")
            output.append(f"- **Key**: {key}")
            output.append(f"- **Citation Distance**: {hops} hop{'s' if hops != 1 else ''}")
            if path:
                output.append(f"- **Citation Path**: {' → '.join(path[:3])}{'...' if len(path) > 3 else ''}")
            output.append("")

        return {
            "success": True,
            "mode": "citation",
            "content": "\n".join(output),
            "papers_found": len(results),
            "max_hops": max_hops,
            "strategy": f"Multi-hop citation chain analysis ({max_hops} hops)"
        }

    except Exception as e:
        logger.error(f"Citation Chain Mode failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "mode": "citation"
        }


def run_seminal_papers_mode(
    neo4j_client,
    field: Optional[str] = None,
    top_n: int = 10
) -> Dict[str, Any]:
    """
    Seminal Papers Mode: Find influential papers using PageRank.

    Citation-based influence ranking.
    """
    logger.info(f"Running SEMINAL PAPERS Mode: field={field}, top_n={top_n}")

    try:
        # Neo4j client returns a list directly
        results = neo4j_client.find_seminal_papers(field=field, top_n=top_n)

        if not results:
            return {
                "success": False,
                "error": f"No seminal papers found{' in field: ' + field if field else ''}",
                "mode": "influence"
            }

        # Format results as markdown
        field_info = f" in field: {field}" if field else " across all fields"
        output = [f"# Seminal Papers{field_info.title()}\n"]
        output.append(f"Top {len(results)} most influential papers by citation analysis:\n")

        for i, paper in enumerate(results, 1):
            title = paper.get("title", "Unknown")
            year = paper.get("year", "N/A")
            key = paper.get("item_key", "")
            influence = paper.get("influence_score", 0)

            output.append(f"## {i}. {title} ({year})")
            output.append(f"- **Key**: {key}")
            output.append(f"- **Influence Score**: {influence:.2f} citations")
            output.append("")

        output.append("\n*Note: Influence score based on citation count (proxy for PageRank)*")

        return {
            "success": True,
            "mode": "influence",
            "content": "\n".join(output),
            "papers_found": len(results),
            "field_filter": field or "all fields",
            "strategy": "PageRank influence ranking"
        }

    except Exception as e:
        logger.error(f"Seminal Papers Mode failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "mode": "influence"
        }


def run_related_papers_mode(
    neo4j_client,
    item_key: str,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Related Papers Mode: Find papers connected via shared entities.

    Entity-based relationship discovery.
    """
    logger.info(f"Running RELATED PAPERS Mode: item_key={item_key}")

    try:
        # Neo4j client returns a list directly
        results = neo4j_client.find_related_papers(item_key, limit=limit)

        if not results:
            return {
                "success": False,
                "error": f"No related papers found for item: {item_key}",
                "mode": "related"
            }

        # Format results as markdown
        output = [f"# Papers Related to {item_key}", ""]
        output.append(f"Found {len(results)} related papers via knowledge graph:")
        output.append("")

        for i, paper in enumerate(results, 1):
            title = paper.get("title", "Untitled")
            year = paper.get("year", "N/A")
            authors = paper.get("authors", [])
            shared_count = paper.get("shared_entities", 0)
            sample_entities = paper.get("sample_entities", [])

            output.append(f"## {i}. {title}")
            output.append(f"**Year:** {year}")
            if authors:
                output.append(f"**Authors:** {', '.join(authors[:3])}")
            output.append(f"**Shared Entities:** {shared_count}")
            if sample_entities:
                output.append(f"**Sample Connections:** {', '.join(sample_entities)}")
            output.append(f"**Item Key:** {paper.get('item_key', 'N/A')}")
            output.append("")

        return {
            "success": True,
            "mode": "related",
            "content": "\n".join(output),
            "papers_found": len(results),
            "strategy": "Shared entity connections"
        }

    except Exception as e:
        logger.error(f"Related Papers Mode failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "mode": "related"
        }

def run_collaborator_network_mode(
    neo4j_client,
    author: str,
    max_hops: int = 2,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Collaborator Network Mode: Find co-authorship networks.

    Multi-hop collaboration discovery.
    """
    logger.info(f"Running COLLABORATOR NETWORK Mode: author={author}, max_hops={max_hops}")

    try:
        # Neo4j client returns a list directly
        results = neo4j_client.find_collaborator_network(author, max_hops=max_hops, limit=limit)

        if not results:
            return {
                "success": False,
                "error": f"No collaborators found for: {author}",
                "mode": "collaboration"
            }

        # Format results as markdown
        output = [f"# Collaborator Network for '{author}'\n"]
        output.append(f"Found {len(results)} collaborators (max {max_hops} hops):\n")

        for item in results:
            collab_name = item.get("author", "Unknown")
            hops = item.get("collaboration_hops", 0)
            collab_count = item.get("collaboration_count", 0)
            sample_papers = item.get("sample_papers", [])

            output.append(f"## {collab_name}")
            output.append(f"- **Collaboration Distance**: {hops} hop{'s' if hops != 1 else ''}")
            output.append(f"- **Shared Papers**: {collab_count}")
            if sample_papers:
                output.append(f"- **Sample Collaborations**:")
                for paper in sample_papers[:3]:
                    output.append(f"  - {paper}")
            output.append("")

        return {
            "success": True,
            "mode": "collaboration",
            "content": "\n".join(output),
            "collaborators_found": len(results),
            "max_hops": max_hops,
            "strategy": f"Co-authorship network ({max_hops} hops)"
        }

    except Exception as e:
        logger.error(f"Collaborator Network Mode failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "mode": "collaboration"
        }


def run_concept_network_mode(
    neo4j_client,
    concept: str,
    max_hops: int = 2,
    limit: int = 15
) -> Dict[str, Any]:
    """
    Concept Network Mode: Explore concept propagation through papers.

    Multi-hop concept relationship discovery.
    """
    logger.info(f"Running CONCEPT NETWORK Mode: concept={concept}, max_hops={max_hops}")

    try:
        # Neo4j client returns a list directly (find_related_concepts)
        results = neo4j_client.find_related_concepts(concept, max_hops=max_hops, limit=limit)

        if not results:
            return {
                "success": False,
                "error": f"No related concepts found for: {concept}",
                "mode": "concept"
            }

        # Format results as markdown
        output = [f"# Related Concepts for '{concept}'\n"]
        output.append(f"Found {len(results)} related concepts (max {max_hops} hops):\n")

        for item in results:
            concept_name = item.get("concept", "Unknown")
            hops = item.get("concept_hops", 0)
            shared_papers = item.get("shared_papers", 0)
            sample_papers = item.get("sample_papers", [])

            output.append(f"## {concept_name}")
            output.append(f"- **Relationship Distance**: {hops} hop{'s' if hops != 1 else ''}")
            output.append(f"- **Shared Papers**: {shared_papers}")
            if sample_papers:
                output.append(f"- **Sample Papers**: {', '.join(sample_papers[:3])}")
            output.append("")

        return {
            "success": True,
            "mode": "concept",
            "content": "\n".join(output),
            "concepts_found": len(results),
            "max_hops": max_hops,
            "strategy": f"Concept propagation ({max_hops} hops)"
        }

    except Exception as e:
        logger.error(f"Concept Network Mode failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "mode": "concept"
        }

def run_topic_evolution_mode(
    neo4j_client,
    concept: str,
    start_year: int,
    end_year: int
) -> Dict[str, Any]:
    """
    Topic Evolution Mode: Track temporal trajectory of research topic.

    Temporal analysis with yearly breakdown.
    """
    logger.info(f"Running TOPIC EVOLUTION Mode: concept={concept}, {start_year}-{end_year}")

    try:
        # This method returns a dict with possible "error" key
        result = neo4j_client.track_topic_evolution(concept, start_year, end_year)

        if isinstance(result, dict) and result.get("error"):
            return {
                "success": False,
                "error": result["error"],
                "mode": "temporal"
            }

        if isinstance(result, dict) and result.get("total_papers", 0) == 0:
            return {
                "success": False,
                "error": f"No papers found for concept '{concept}' in {start_year}-{end_year}",
                "mode": "temporal"
            }

        # Format results (result should have formatted_output from the client)
        return {
            "success": True,
            "mode": "temporal",
            "content": result.get("formatted_output", str(result)),
            "years_analyzed": len(result.get("yearly_data", [])),
            "time_span": f"{start_year}-{end_year}",
            "strategy": "Temporal trajectory analysis"
        }

    except Exception as e:
        logger.error(f"Topic Evolution Mode failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "mode": "temporal"
        }

def run_venue_analysis_mode(
    neo4j_client,
    field: Optional[str] = None,
    top_n: int = 10
) -> Dict[str, Any]:
    """
    Venue Analysis Mode: Analyze publication outlet patterns.

    Venue ranking by paper count.
    """
    logger.info(f"Running VENUE ANALYSIS Mode: field={field}, top_n={top_n}")

    try:
        # Neo4j client returns a list directly
        results = neo4j_client.analyze_publication_venues(field=field, top_n=top_n)

        if not results:
            field_info = f" in field: {field}" if field else ""
            return {
                "success": False,
                "error": f"No publication venues found{field_info}",
                "mode": "venue"
            }

        # Format results as markdown
        field_info = f" in field: {field}" if field else " across all fields"
        output = [f"# Top Publication Venues{field_info.title()}\n"]
        output.append(f"Found {len(results)} top venues by publication count:\n")

        for i, venue in enumerate(results, 1):
            venue_name = venue.get("venue", "Unknown")
            paper_count = venue.get("paper_count", 0)
            sample_papers = venue.get("sample_papers", [])

            output.append(f"## {i}. {venue_name}")
            output.append(f"- **Papers**: {paper_count}")
            if sample_papers:
                output.append(f"- **Sample Titles**:")
                for paper in sample_papers[:3]:
                    output.append(f"  - {paper}")
            output.append("")

        return {
            "success": True,
            "mode": "venue",
            "content": "\n".join(output),
            "venues_found": len(results),
            "field_filter": field or "all fields",
            "strategy": "Publication outlet ranking"
        }

    except Exception as e:
        logger.error(f"Venue Analysis Mode failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "mode": "venue"
        }

def run_content_similarity_mode(
    semantic_search_instance,
    zotero_client,
    paper_key: str,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Content Similarity Mode: Find papers with similar content using vector similarity.

    Uses Qdrant 'More Like This' on the paper's abstract to find semantically similar papers.
    This is content-based (what the paper discusses), not graph-based (citations/authors).
    """
    logger.info(f"Running CONTENT SIMILARITY Mode: paper_key={paper_key}")

    try:
        # Get the reference paper's abstract
        from agent_zot.tools.zotero import get_item_with_fallback

        item = get_item_with_fallback(zotero_client, paper_key)

        if not item:
            return {
                "success": False,
                "error": f"No item found with key: {paper_key}",
                "mode": "content_similarity"
            }

        # Get abstract for similarity search
        abstract = item.get("data", {}).get("abstractNote", "")
        if not abstract:
            return {
                "success": False,
                "error": f"Item {paper_key} has no abstract for similarity search.",
                "suggestion": "Use zot_explore_graph Related Papers Mode for graph-based relationships instead.",
                "mode": "content_similarity"
            }

        # Use semantic search with the abstract
        results = semantic_search_instance.search(query=abstract, limit=limit + 1)  # +1 to exclude source paper

        if not results or "results" not in results or not results["results"]:
            return {
                "success": False,
                "error": "No similar papers found",
                "mode": "content_similarity"
            }

        # Filter out the source paper if it appears in results
        filtered_results = [p for p in results["results"] if p.get("item_key") != paper_key][:limit]

        if not filtered_results:
            return {
                "success": False,
                "error": "No similar papers found (only source paper matched)",
                "mode": "content_similarity"
            }

        # Get title of reference paper
        ref_title = item.get("data", {}).get("title", paper_key)

        # Format results as markdown
        output = [f"# Papers Similar to: {ref_title}\n"]
        output.append(f"**Reference Key**: {paper_key}\n")
        output.append(f"Found {len(filtered_results)} semantically similar papers using vector similarity:\n")

        for i, paper in enumerate(filtered_results, 1):
            title = paper.get("title", "Untitled")
            authors = paper.get("creators_str", "Unknown authors")
            year = paper.get("year", "N/A")
            key = paper.get("item_key", "")
            score = paper.get("similarity_score", 0.0)

            output.append(f"## {i}. {title}")
            output.append(f"- **Authors**: {authors}")
            output.append(f"- **Year**: {year}")
            output.append(f"- **Item Key**: `{key}`")
            output.append(f"- **Similarity Score**: {score:.3f}")

            # Include abstract preview if available
            abs_text = paper.get("abstract", "")
            if abs_text:
                preview = abs_text[:200] + "..." if len(abs_text) > 200 else abs_text
                output.append(f"- **Abstract**: {preview}")

            output.append("")

        return {
            "success": True,
            "mode": "content_similarity",
            "content": "\n".join(output),
            "papers_found": len(filtered_results),
            "strategy": "Vector-based content similarity (Qdrant More Like This)",
            "reference_paper": paper_key
        }

    except Exception as e:
        logger.error(f"Content Similarity Mode failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "mode": "content_similarity"
        }


def run_comprehensive_mode(
    neo4j_client,
    query: str,
    paper_key: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Comprehensive Mode: Run multiple graph strategies and merge results.

    Exploratory analysis combining multiple perspectives.
    """
    logger.info(f"Running COMPREHENSIVE Mode: exploratory analysis")

    strategies_run = []
    all_results = []
    errors = []

    # Strategy 1: If paper_key provided, find related papers
    if paper_key:
        logger.info("Strategy 1: Finding related papers...")
        try:
            result = run_related_papers_mode(neo4j_client, paper_key, limit=limit)
            if result.get("success"):
                strategies_run.append("Related papers")
                all_results.append(result.get("content", ""))
            else:
                errors.append(f"Related papers: {result.get('error')}")
        except Exception as e:
            errors.append(f"Related papers: {str(e)}")

        # Strategy 2: Find citation chain
        logger.info("Strategy 2: Finding citation chain...")
        try:
            result = run_citation_chain_mode(neo4j_client, paper_key, max_hops=2, limit=limit)
            if result.get("success"):
                strategies_run.append("Citation chain")
                all_results.append(result.get("content", ""))
            else:
                errors.append(f"Citation chain: {result.get('error')}")
        except Exception as e:
            errors.append(f"Citation chain: {str(e)}")

    # Strategy 3: Find seminal papers (always useful)
    logger.info("Strategy 3: Finding seminal papers...")
    try:
        result = run_seminal_papers_mode(neo4j_client, field=None, top_n=limit)
        if result.get("success"):
            strategies_run.append("Seminal papers")
            all_results.append(result.get("content", ""))
        else:
            errors.append(f"Seminal papers: {result.get('error')}")
    except Exception as e:
        errors.append(f"Seminal papers: {str(e)}")

    # Combine results
    if not all_results:
        return {
            "success": False,
            "error": f"All strategies failed: {'; '.join(errors)}",
            "mode": "comprehensive"
        }

    combined_content = f"# Comprehensive Graph Exploration\n\n"
    combined_content += f"**Strategies executed**: {', '.join(strategies_run)}\n\n"
    combined_content += "---\n\n".join(all_results)

    if errors:
        combined_content += f"\n\n## Warnings\n\n"
        for error in errors:
            combined_content += f"- {error}\n"

    return {
        "success": True,
        "mode": "comprehensive",
        "content": combined_content,
        "strategies_executed": len(strategies_run),
        "strategy": f"Multi-strategy exploration ({', '.join(strategies_run)})"
    }


# ============================================================================
# Main Unified Graph Exploration Function
# ============================================================================

def smart_explore_graph(
    query: str,
    neo4j_client,
    semantic_search_instance=None,
    zotero_client=None,
    paper_key: Optional[str] = None,
    author: Optional[str] = None,
    concept: Optional[str] = None,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    field: Optional[str] = None,
    force_mode: Optional[str] = None,
    limit: int = 10,
    max_hops: int = 2
) -> Dict[str, Any]:
    """
    Intelligent unified exploration tool (graph-based AND content-based).

    Automatically detects intent and selects optimal exploration strategy:
    - Graph-based (Neo4j): citations, collaborations, concepts, temporal, venue
    - Content-based (Qdrant): vector similarity "More Like This"

    Args:
        query: User's query string
        neo4j_client: Neo4j GraphRAG client instance
        semantic_search_instance: Semantic search instance for content similarity (optional)
        zotero_client: Zotero client instance for metadata (optional)
        paper_key: Optional paper key for paper-centric analysis
        author: Optional author name for collaboration analysis
        concept: Optional concept name for concept/topic analysis
        start_year: Optional start year for temporal analysis
        end_year: Optional end year for temporal analysis
        field: Optional field filter for influence/venue analysis
        force_mode: Optional mode override
        limit: Maximum results to return (default: 10)
        max_hops: Maximum graph traversal hops (default: 2)

    Returns:
        Dict with:
        - success: bool
        - mode: str (which mode was used)
        - content: str (the exploration results)
        - error: str (if failed)
        - Additional metadata (papers_found, strategy, etc.)
    """

    logger.info(f"=== Smart Explore Graph: query={query}, force_mode={force_mode} ===")

    # Determine mode
    if force_mode:
        mode = force_mode.lower()
        confidence = 1.0
        extracted_params = {}
        logger.info(f"Mode FORCED to: {mode}")
    else:
        mode, confidence, extracted_params = detect_graph_intent(query)
        logger.info(f"Mode DETECTED: {mode} (confidence: {confidence:.2f})")

        # Use extracted parameters if not explicitly provided
        if not author and "author" in extracted_params:
            author = extracted_params["author"]
        if not concept and "concept" in extracted_params:
            concept = extracted_params["concept"]
        if not start_year and "start_year" in extracted_params:
            start_year = extracted_params["start_year"]
        if not end_year and "end_year" in extracted_params:
            end_year = extracted_params["end_year"]

    # Execute appropriate mode
    result = None

    if mode == "citation":
        if not paper_key:
            return {
                "success": False,
                "error": "Citation Chain Mode requires a paper_key parameter"
            }
        result = run_citation_chain_mode(neo4j_client, paper_key, max_hops, limit)

    elif mode == "influence":
        result = run_seminal_papers_mode(neo4j_client, field, limit)

    elif mode == "content_similarity":
        if not paper_key:
            return {
                "success": False,
                "error": "Content Similarity Mode requires a paper_key parameter",
                "suggestion": "Provide paper key or use query like 'find papers similar to ABC12345'"
            }
        if not semantic_search_instance:
            return {
                "success": False,
                "error": "Content Similarity Mode requires semantic_search_instance",
                "suggestion": "This mode requires Qdrant - ensure semantic search is initialized"
            }
        if not zotero_client:
            return {
                "success": False,
                "error": "Content Similarity Mode requires zotero_client",
                "suggestion": "This mode requires Zotero API access"
            }
        result = run_content_similarity_mode(semantic_search_instance, zotero_client, paper_key, limit)

    elif mode == "related":
        if not paper_key:
            return {
                "success": False,
                "error": "Related Papers Mode requires a paper_key parameter"
            }
        result = run_related_papers_mode(neo4j_client, paper_key, limit)

    elif mode == "collaboration":
        if not author:
            return {
                "success": False,
                "error": "Collaborator Network Mode requires an author parameter",
                "suggestion": "Provide author name or use query like 'who collaborated with [author name]'"
            }
        result = run_collaborator_network_mode(neo4j_client, author, max_hops, limit)

    elif mode == "concept":
        if not concept:
            return {
                "success": False,
                "error": "Concept Network Mode requires a concept parameter",
                "suggestion": "Provide concept name or use query like 'concepts related to [concept]'"
            }
        result = run_concept_network_mode(neo4j_client, concept, max_hops, limit)

    elif mode == "temporal":
        if not concept:
            return {
                "success": False,
                "error": "Topic Evolution Mode requires a concept parameter"
            }
        if not start_year or not end_year:
            return {
                "success": False,
                "error": "Topic Evolution Mode requires start_year and end_year parameters",
                "suggestion": "Use query like 'how did [topic] evolve from 2010 to 2024'"
            }
        result = run_topic_evolution_mode(neo4j_client, concept, start_year, end_year)

    elif mode == "venue":
        result = run_venue_analysis_mode(neo4j_client, field, limit)

    elif mode == "exploratory":
        result = run_comprehensive_mode(neo4j_client, query, paper_key, limit)

    else:
        return {
            "success": False,
            "error": f"Unknown mode: {mode}. Must be one of: citation, influence, content_similarity, related, collaboration, concept, temporal, venue, exploratory"
        }

    # Add intent detection metadata to result
    if result:
        result["intent_confidence"] = confidence
        result["query"] = query

    return result
