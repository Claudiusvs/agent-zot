"""
Unified smart summarization tool for agent-zot.

This module provides intelligent paper summarization with automatic intent detection
and mode selection. It replaces several legacy tools:
- zot_ask_paper (Targeted Mode)
- zot_get_item (Quick Mode)
- zot_get_item_fulltext (Full Mode)

The smart_summarize_paper function automatically detects summarization depth needed
and selects the optimal retrieval strategy.

Usage Examples:
    ```python
    # Quick overview (metadata + abstract)
    result = smart_summarize_paper(item_key="ABC123", ctx=ctx)

    # Targeted question answering
    result = smart_summarize_paper(
        item_key="ABC123",
        query="What methodology did they use?",
        ctx=ctx
    )

    # Comprehensive summary
    result = smart_summarize_paper(
        item_key="ABC123",
        query="Summarize this paper comprehensively",
        ctx=ctx
    )

    # Force specific mode
    result = smart_summarize_paper(
        item_key="ABC123",
        query="Get complete text",
        force_mode="full",
        ctx=ctx
    )
    ```

Modes:
    - Quick Mode: Metadata + abstract (~500-800 tokens)
    - Targeted Mode: Semantic Q&A (~2k-5k tokens)
    - Comprehensive Mode: Multi-aspect orchestration (~8k-15k tokens)
    - Full Mode: Complete text extraction (10k-100k tokens, expensive)
"""

from typing import Optional
from pathlib import Path
from fastmcp import Context
import tempfile
import os


def smart_summarize_paper(
    item_key: str,
    query: Optional[str] = None,
    force_mode: Optional[str] = None,
    top_k: int = 5,
    *,
    ctx: Context
) -> str:
    """
    Intelligent unified summarization tool.

    Automatically detects intent and selects optimal summarization strategy.

    Args:
        item_key: Zotero item key to summarize
        query: Optional query/question (if None, defaults to Quick Mode)
        force_mode: Optional mode override ("quick", "targeted", "comprehensive", "full")
        top_k: Number of chunks to retrieve in targeted/comprehensive modes (default: 5)
        ctx: MCP context

    Returns:
        Markdown-formatted summary with mode and strategy info

    Examples:
        >>> # Quick overview
        >>> smart_summarize_paper("ABC123", ctx=ctx)

        >>> # Specific question
        >>> smart_summarize_paper("ABC123", "What are the main findings?", ctx=ctx)

        >>> # Comprehensive summary
        >>> smart_summarize_paper("ABC123", "Summarize comprehensively", ctx=ctx)

        >>> # Force full text extraction
        >>> smart_summarize_paper("ABC123", force_mode="full", ctx=ctx)
    """
    try:
        from agent_zot.search.semantic import create_semantic_search
        from agent_zot.search.unified_summarize import smart_summarize
        from agent_zot.clients.zotero import (
            get_zotero_client,
            format_item_metadata,
            get_attachment_details,
            convert_to_markdown
        )

        ctx.info(f"Smart summarizing item {item_key} (query: {query}, force_mode: {force_mode})")

        # Initialize dependencies
        config_path = Path.home() / ".config" / "agent-zot" / "config.json"
        semantic_search = create_semantic_search(str(config_path))
        zot = get_zotero_client()

        # Helper function for full mode PDF extraction
        def extract_fulltext_wrapper(zot_client, attachment):
            """Extract full text from PDF attachment."""
            with tempfile.TemporaryDirectory() as tmpdir:
                file_path = os.path.join(tmpdir, attachment.filename or f"{attachment.key}.pdf")
                zot_client.dump(attachment.key, filename=os.path.basename(file_path), path=tmpdir)

                if os.path.exists(file_path):
                    converted_text = convert_to_markdown(file_path)
                    if converted_text:
                        return converted_text
                    else:
                        raise Exception("Could not extract text from PDF")
                else:
                    raise Exception("PDF download failed")

        # Call the smart summarization function
        result = smart_summarize(
            item_key=item_key,
            query=query,
            force_mode=force_mode,
            semantic_search_instance=semantic_search,
            zot_client=zot,
            format_metadata_func=format_item_metadata,
            get_attachment_func=get_attachment_details,
            extract_fulltext_func=extract_fulltext_wrapper,
            top_k=top_k
        )

        # Format response
        if not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            suggestion = result.get("suggestion", "")
            return f"❌ Error: {error_msg}\n\n{suggestion}"

        # Build output
        output_parts = []

        # Add metadata header
        mode = result.get("mode", "unknown")
        strategy = result.get("strategy", "unknown")
        tokens_est = result.get("tokens_estimated", 0)

        output_parts.append(f"# Summary (Mode: {mode.upper()})\n")
        output_parts.append(f"**Strategy:** {strategy}")
        output_parts.append(f"**Estimated tokens:** ~{int(tokens_est)}")

        if result.get("chunks_retrieved"):
            output_parts.append(f"**Chunks retrieved:** {result['chunks_retrieved']}")

        if result.get("aspects_covered"):
            output_parts.append(f"**Aspects covered:** {result['aspects_covered']}")

        if result.get("warning"):
            output_parts.append(f"\n⚠️ {result['warning']}")

        output_parts.append("\n---\n")

        # Add content
        output_parts.append(result.get("content", ""))

        # Add confidence info if available
        if "intent_confidence" in result:
            conf = result["intent_confidence"]
            output_parts.append(f"\n---\n\n*Intent detected with {conf:.0%} confidence*")

        return "\n".join(output_parts)

    except Exception as e:
        import traceback
        ctx.error(f"Smart summarize failed: {str(e)}")
        ctx.error(f"Traceback: {traceback.format_exc()}")
        return f"❌ Error: {str(e)}\n\n💡 Suggestion: Try using zot_get_item for metadata or zot_ask_paper for targeted content retrieval."


# Alias for code execution pattern (function name matches module name)
zot_summarize = smart_summarize_paper
