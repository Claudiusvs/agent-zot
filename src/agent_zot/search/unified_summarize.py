"""
Unified intelligent summarization tool for Agent-Zot.

Consolidates zot_ask_paper, zot_get_item, and zot_get_item_fulltext into a single
intelligent tool that automatically selects the optimal summarization strategy based
on query intent.

Four Execution Modes:
1. Quick Mode - Abstract + metadata (fast, ~500-800 tokens)
2. Targeted Mode - Specific Q&A via semantic chunk search (~2k-5k tokens)
3. Comprehensive Mode - Multi-aspect orchestrated Q&A (~8k-15k tokens)
4. Full Mode - Complete raw text extraction (expensive, 10k-100k tokens)
"""

import re
import logging
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


# ============================================================================
# Intent Detection Patterns (Domain-Agnostic)
# ============================================================================

# Quick Mode patterns - overview, basic info
QUICK_PATTERNS = [
    r'\bwhat\s+is\s+this\s+(paper|article|study|document)\s+about\b',
    r'\b(give|show)\s+(me\s+)?(an?\s+)?overview\b',
    r'\b(give|show)\s+(me\s+)?(the\s+)?abstract\b',
    r'\bbasic\s+info(rmation)?\b',
    r'\bquick\s+(summary|overview)\b',
    r'\bwho\s+(are\s+)?the\s+authors?\b',
    r'\bwhen\s+was\s+this\s+published\b',
    r'\bwhat\s+(journal|conference|venue)\b',
    r'\bcitation\s+info(rmation)?\b',
]

# Targeted Mode patterns - specific questions
TARGETED_PATTERNS = [
    r'\bwhat\s+(methodology|method|approach|technique)\b',
    r'\bhow\s+did\s+(they|the\s+authors)\b',
    r'\bwhat\s+(were|are)\s+the\s+(main\s+)?(findings|results|conclusions)\b',
    r'\bwhat\s+(data|dataset|sample)\b',
    r'\bhow\s+(was|were)\s+\w+\s+(measured|assessed|evaluated|analyzed)\b',
    r'\bwhat\s+(statistical|analysis)\s+methods?\b',
    r'\bwhat\s+(limitations|weaknesses)\b',
    r'\bwhat\s+implications?\b',
    r'\bwhat\s+(theoretical|conceptual)\s+framework\b',
]

# Comprehensive Mode patterns - full summary needed
COMPREHENSIVE_PATTERNS = [
    r'\bsummarize\s+(this\s+)?(paper|article|study)\s+comprehensively\b',
    r'\bsummarize\s+(the\s+)?entire\s+(paper|article|study)\b',
    r'\b(give|provide)\s+(me\s+)?a\s+(complete|full|detailed|thorough)\s+summary\b',
    r'\bsummarize\s+(all|everything)\b',
    r'\btell\s+me\s+everything\s+about\s+this\s+(paper|article|study)\b',
    r'\b(what|describe)\s+(are\s+)?all\s+(the\s+)?(aspects|components|sections)\b',
]

# Full Mode patterns - raw text extraction needed
FULL_PATTERNS = [
    r'\bextract\s+all\s+\w+',
    r'\bget\s+(the\s+)?(complete|full|entire|raw)\s+text\b',
    r'\bfull\s+text\s+of\b',
    r'\b(find|get|show)\s+all\s+(equations|formulas|figures|tables)\b',
    r'\bword\s+count\b',
    r'\bexport\s+(the\s+)?text\b',
    r'\bget\s+everything\b',
]


def detect_summarization_intent(query: str) -> Tuple[str, float]:
    """
    Detect summarization intent from query text.

    Args:
        query: User's query string

    Returns:
        Tuple of (intent, confidence) where intent is one of:
        - "quick" - Overview/metadata (Quick Mode)
        - "targeted" - Specific question (Targeted Mode)
        - "comprehensive" - Full summary needed (Comprehensive Mode)
        - "full" - Raw text extraction (Full Mode)
    """
    query_lower = query.lower()

    # Check Full Mode patterns first (most specific)
    for pattern in FULL_PATTERNS:
        if re.search(pattern, query_lower):
            logger.info(f"Detected FULL intent: pattern '{pattern}' matched")
            return ("full", 0.95)

    # Check Comprehensive Mode patterns
    for pattern in COMPREHENSIVE_PATTERNS:
        if re.search(pattern, query_lower):
            logger.info(f"Detected COMPREHENSIVE intent: pattern '{pattern}' matched")
            return ("comprehensive", 0.90)

    # Check Quick Mode patterns
    for pattern in QUICK_PATTERNS:
        if re.search(pattern, query_lower):
            logger.info(f"Detected QUICK intent: pattern '{pattern}' matched")
            return ("quick", 0.85)

    # Check Targeted Mode patterns
    for pattern in TARGETED_PATTERNS:
        if re.search(pattern, query_lower):
            logger.info(f"Detected TARGETED intent: pattern '{pattern}' matched")
            return ("targeted", 0.80)

    # Default: if query is short and general, use Quick Mode
    # If query is a question (what/how/why), use Targeted Mode
    if len(query_lower.split()) <= 5:
        logger.info("Detected QUICK intent: short query (default)")
        return ("quick", 0.60)
    elif re.search(r'\b(what|how|why|which|where|when)\b', query_lower):
        logger.info("Detected TARGETED intent: question word detected (default)")
        return ("targeted", 0.65)
    else:
        logger.info("Detected TARGETED intent: fallback default")
        return ("targeted", 0.60)


# ============================================================================
# Mode Implementation Functions
# ============================================================================

def run_quick_mode(
    item_key: str,
    zot_client,
    format_metadata_func
) -> Dict[str, Any]:
    """
    Quick Mode: Return abstract + metadata using get_item.

    Fast and efficient for overview questions.
    Cost: ~500-800 tokens
    """
    logger.info("Running QUICK Mode: fetching metadata + abstract")

    try:
        # Get item metadata
        item = zot_client.item(item_key)
        if not item:
            return {
                "success": False,
                "error": f"No item found with key: {item_key}",
                "mode": "quick"
            }

        # Format metadata with abstract
        metadata = format_metadata_func(item, include_abstract=True)

        return {
            "success": True,
            "mode": "quick",
            "content": metadata,
            "tokens_estimated": len(metadata.split()) * 1.3,  # rough estimate
            "strategy": "Metadata + abstract retrieval"
        }

    except Exception as e:
        logger.error(f"Quick Mode failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "mode": "quick"
        }


def run_targeted_mode(
    item_key: str,
    query: str,
    semantic_search_instance,
    top_k: int = 5
) -> Dict[str, Any]:
    """
    Targeted Mode: Answer specific question using semantic chunk search.

    Retrieves relevant chunks from the paper to answer a specific question.
    Cost: ~2k-5k tokens
    """
    logger.info(f"Running TARGETED Mode: semantic search with question: {query}")

    try:
        # Search with parent_item_key filter to only get chunks from this specific paper
        results = semantic_search_instance.search(
            query=query,
            limit=top_k,
            filters={"parent_item_key": item_key}
        )

        if results.get("error"):
            return {
                "success": False,
                "error": f"Semantic search failed: {results['error']}",
                "mode": "targeted"
            }

        if not results.get("results"):
            return {
                "success": False,
                "error": "No relevant content found in this paper",
                "mode": "targeted",
                "suggestion": "Try using Comprehensive Mode for broader context"
            }

        # Format results
        output_parts = [f"# Relevant Content for: {query}\n"]

        for i, result in enumerate(results["results"], 1):
            score = result.get("score", 0)
            content = result.get("content", "")
            chunk_id = result.get("chunk_id", "unknown")

            output_parts.append(f"\n## Chunk {i} (relevance: {score:.2f})")
            output_parts.append(f"*Chunk ID: {chunk_id}*\n")
            output_parts.append(content)
            output_parts.append("\n---\n")

        content = "\n".join(output_parts)

        return {
            "success": True,
            "mode": "targeted",
            "content": content,
            "chunks_retrieved": len(results["results"]),
            "tokens_estimated": len(content.split()) * 1.3,
            "strategy": f"Semantic search over chunks (top_{top_k})"
        }

    except Exception as e:
        logger.error(f"Targeted Mode failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "mode": "targeted"
        }


def run_comprehensive_mode(
    item_key: str,
    semantic_search_instance,
    zot_client,
    format_metadata_func,
    top_k: int = 5
) -> Dict[str, Any]:
    """
    Comprehensive Mode: Multi-aspect orchestrated summarization.

    Automatically asks multiple questions covering different aspects of the paper:
    - Research question/objective
    - Methodology
    - Main findings/results
    - Conclusions/implications

    Cost: ~8k-15k tokens
    """
    logger.info("Running COMPREHENSIVE Mode: multi-aspect orchestration")

    # Predefined questions covering key aspects
    aspects = [
        ("Research Question", "What is the main research question or objective of this study?"),
        ("Methodology", "What methodology or approach did the researchers use?"),
        ("Findings", "What were the main findings or results?"),
        ("Conclusions", "What conclusions or implications did the authors draw?"),
    ]

    try:
        # First, get metadata for context
        item = zot_client.item(item_key)
        if not item:
            return {
                "success": False,
                "error": f"No item found with key: {item_key}",
                "mode": "comprehensive"
            }

        metadata = format_metadata_func(item, include_abstract=True)

        # Then, run targeted searches for each aspect
        output_parts = [
            "# Comprehensive Summary\n",
            "## Bibliographic Information\n",
            metadata,
            "\n---\n"
        ]

        total_chunks = 0

        for aspect_name, question in aspects:
            logger.info(f"Retrieving content for: {aspect_name}")

            # Run semantic search for this aspect
            results = semantic_search_instance.search(
                query=question,
                limit=top_k,
                filters={"parent_item_key": item_key}
            )

            if results.get("error") or not results.get("results"):
                output_parts.append(f"\n## {aspect_name}\n")
                output_parts.append("*No relevant content found*\n")
                continue

            output_parts.append(f"\n## {aspect_name}\n")

            # Add top chunks for this aspect
            for i, result in enumerate(results["results"][:3], 1):  # Limit to top 3 per aspect
                content = result.get("content", "")
                score = result.get("score", 0)

                if i == 1:  # Only add header for first chunk
                    output_parts.append(f"*Relevance: {score:.2f}*\n")

                output_parts.append(content)
                output_parts.append("\n")
                total_chunks += 1

            output_parts.append("---\n")

        content = "\n".join(output_parts)

        return {
            "success": True,
            "mode": "comprehensive",
            "content": content,
            "aspects_covered": len(aspects),
            "chunks_retrieved": total_chunks,
            "tokens_estimated": len(content.split()) * 1.3,
            "strategy": "Multi-aspect orchestration (4 key aspects)"
        }

    except Exception as e:
        logger.error(f"Comprehensive Mode failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "mode": "comprehensive"
        }


def run_full_mode(
    item_key: str,
    zot_client,
    format_metadata_func,
    get_attachment_func,
    extract_fulltext_func
) -> Dict[str, Any]:
    """
    Full Mode: Extract complete raw text from PDF.

    WARNING: Expensive operation (10k-100k tokens).
    Only use when absolutely necessary (e.g., extracting all equations, word count).

    Cost: 10k-100k tokens
    """
    logger.info("Running FULL Mode: complete text extraction (expensive!)")
    logger.warning("⚠️ Full Mode is expensive (10k-100k tokens) - use sparingly!")

    try:
        # Get item metadata
        item = zot_client.item(item_key)
        if not item:
            return {
                "success": False,
                "error": f"No item found with key: {item_key}",
                "mode": "full"
            }

        metadata = format_metadata_func(item, include_abstract=True)

        # Get attachment
        attachment = get_attachment_func(zot_client, item)
        if not attachment:
            return {
                "success": False,
                "error": "No suitable PDF attachment found",
                "mode": "full",
                "suggestion": "Verify attachments exist using Quick Mode first"
            }

        logger.info(f"Found attachment: {attachment.key} ({attachment.content_type})")

        # Try fetching from Zotero's full text index first
        try:
            full_text_data = zot_client.fulltext_item(attachment.key)
            if full_text_data and "content" in full_text_data and full_text_data["content"]:
                full_text = full_text_data["content"]
                source = "Zotero full text index"
            else:
                # Fall back to PDF extraction
                full_text = extract_fulltext_func(zot_client, attachment)
                source = "AI-powered PDF extraction (Docling)"

        except Exception as e:
            logger.warning(f"Full text index failed, using PDF extraction: {e}")
            full_text = extract_fulltext_func(zot_client, attachment)
            source = "AI-powered PDF extraction (Docling)"

        if not full_text or not full_text.strip():
            return {
                "success": False,
                "error": "Could not extract full text from PDF",
                "mode": "full"
            }

        # Combine metadata and full text
        content = f"{metadata}\n\n---\n\n## Full Text\n\n{full_text}"

        return {
            "success": True,
            "mode": "full",
            "content": content,
            "tokens_estimated": len(content.split()) * 1.3,
            "extraction_source": source,
            "strategy": "Complete text extraction",
            "warning": "This is an expensive operation (10k-100k tokens)"
        }

    except Exception as e:
        logger.error(f"Full Mode failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "mode": "full"
        }


# ============================================================================
# Main Unified Summarization Function
# ============================================================================

def smart_summarize(
    item_key: str,
    query: Optional[str] = None,
    force_mode: Optional[str] = None,
    semantic_search_instance = None,
    zot_client = None,
    format_metadata_func = None,
    get_attachment_func = None,
    extract_fulltext_func = None,
    top_k: int = 5
) -> Dict[str, Any]:
    """
    Intelligent unified summarization tool.

    Automatically detects intent and selects optimal summarization strategy.

    Args:
        item_key: Zotero item key to summarize
        query: Optional query/question (if None, defaults to Quick Mode)
        force_mode: Optional override ("quick", "targeted", "comprehensive", "full")
        semantic_search_instance: Instance of SemanticSearch for chunk retrieval
        zot_client: Zotero client instance
        format_metadata_func: Function to format item metadata
        get_attachment_func: Function to get PDF attachment
        extract_fulltext_func: Function to extract full text from PDF
        top_k: Number of chunks to retrieve in targeted/comprehensive modes

    Returns:
        Dict with:
        - success: bool
        - mode: str (which mode was used)
        - content: str (the summary/content)
        - error: str (if failed)
        - Additional metadata (tokens_estimated, strategy, etc.)
    """

    logger.info(f"=== Smart Summarize: item_key={item_key}, query={query}, force_mode={force_mode} ===")

    # Validate required dependencies
    if not all([zot_client, format_metadata_func]):
        return {
            "success": False,
            "error": "Missing required dependencies (zot_client, format_metadata_func)"
        }

    # Determine mode
    if force_mode:
        mode = force_mode.lower()
        confidence = 1.0
        logger.info(f"Mode FORCED to: {mode}")
    elif query:
        mode, confidence = detect_summarization_intent(query)
        logger.info(f"Mode DETECTED: {mode} (confidence: {confidence:.2f})")
    else:
        # No query provided - default to Quick Mode
        mode = "quick"
        confidence = 1.0
        logger.info("No query provided - defaulting to Quick Mode")

    # Execute appropriate mode
    result = None

    if mode == "quick":
        result = run_quick_mode(item_key, zot_client, format_metadata_func)

    elif mode == "targeted":
        if not semantic_search_instance:
            return {
                "success": False,
                "error": "Targeted Mode requires semantic_search_instance"
            }
        if not query:
            return {
                "success": False,
                "error": "Targeted Mode requires a specific question"
            }
        result = run_targeted_mode(item_key, query, semantic_search_instance, top_k)

    elif mode == "comprehensive":
        if not semantic_search_instance:
            return {
                "success": False,
                "error": "Comprehensive Mode requires semantic_search_instance"
            }
        result = run_comprehensive_mode(
            item_key, semantic_search_instance, zot_client,
            format_metadata_func, top_k
        )

    elif mode == "full":
        if not all([get_attachment_func, extract_fulltext_func]):
            return {
                "success": False,
                "error": "Full Mode requires get_attachment_func and extract_fulltext_func"
            }
        result = run_full_mode(
            item_key, zot_client, format_metadata_func,
            get_attachment_func, extract_fulltext_func
        )

    else:
        return {
            "success": False,
            "error": f"Unknown mode: {mode}. Must be one of: quick, targeted, comprehensive, full"
        }

    # Add intent detection metadata to result
    if result:
        result["intent_confidence"] = confidence
        result["query"] = query

    return result
