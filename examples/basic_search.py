#!/usr/bin/env python3
"""
Basic Search Example - agent-zot v3.0+

Demonstrates the MCP code execution pattern for simple semantic search.

Token Efficiency:
- v2.1 (MCP tool): 50 papers × 800 tokens = 40,000 tokens
- v3.0 (code execution): Display top 10 = ~4,000 tokens
- **Reduction: 90%**

Prerequisites:
- agent-zot installed: pip install -e .
- Zotero database indexed: agent-zot update-db --fulltext
"""

from agent_zot.mcp_tools.zot_search import zot_search


def main():
    """
    Execute a basic semantic search and display results.
    """
    print("🔍 Agent-Zot v3.0 - Basic Search Example\n")

    # Execute search (returns ALL matching papers)
    query = "neural networks deep learning"
    results = zot_search(query=query, limit=50)

    print(f"📊 Found {len(results)} papers matching '{query}'\n")

    # Display top 10 results
    for i, paper in enumerate(results[:10], 1):
        title = paper.get('title', 'Untitled')
        year = paper.get('year', 'N/A')
        authors = paper.get('creators', [])
        author_str = authors[0].get('lastName', 'Unknown') if authors else 'Unknown'

        print(f"{i:2d}. {title}")
        print(f"    {author_str} ({year})")
        print()

    print(f"✅ Displayed top 10 results")
    print(f"💡 Tip: Full {len(results)} results available in Python for further processing")


if __name__ == "__main__":
    main()
