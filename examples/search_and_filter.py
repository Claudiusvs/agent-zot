#!/usr/bin/env python3
"""
Search and Filter Example - agent-zot v3.0+

Demonstrates powerful filtering BEFORE results enter Claude's context window.

Token Efficiency:
- v2.1 (MCP tool): 100 papers × 800 tokens = 80,000 tokens (all papers in context)
- v3.0 (code execution): Filter → 5 papers × 400 tokens = 2,000 tokens
- **Reduction: 97.5%**

This is the CORE advantage of the code execution pattern!

Prerequisites:
- agent-zot installed: pip install -e .
- Zotero database indexed: agent-zot update-db --fulltext
"""

from agent_zot.mcp_tools.zot_search import zot_search


def main():
    """
    Search for papers and apply multi-criteria filtering.
    """
    print("🔍 Agent-Zot v3.0 - Search & Filter Example\n")

    # Step 1: Execute search (returns ALL matching papers)
    query = "machine learning"
    results = zot_search(query=query, limit=100)
    print(f"📊 Retrieved {len(results)} papers")

    # Step 2: Filter by year (code execution - NO tokens consumed yet!)
    recent = [p for p in results if p.get('year', 0) >= 2022]
    print(f"   → {len(recent)} papers from 2022+")

    # Step 3: Filter by author count (multi-author papers)
    collaborative = [p for p in recent if len(p.get('creators', [])) > 3]
    print(f"   → {len(collaborative)} papers with 4+ authors")

    # Step 4: Sort by citation count (if available)
    sorted_papers = sorted(
        collaborative,
        key=lambda x: x.get('citationCount', 0),
        reverse=True
    )

    # Step 5: Take top 5 (ONLY these 5 enter Claude's context!)
    top_5 = sorted_papers[:5]
    print(f"   → Top 5 by citation count\n")

    # Display results
    for i, paper in enumerate(top_5, 1):
        title = paper.get('title', 'Untitled')
        year = paper.get('year', 'N/A')
        authors = paper.get('creators', [])
        author_str = ', '.join([a.get('lastName', '') for a in authors[:3]])
        if len(authors) > 3:
            author_str += f" et al. ({len(authors)} authors)"
        citations = paper.get('citationCount', 'N/A')

        print(f"{i}. {title}")
        print(f"   {author_str} ({year})")
        print(f"   Citations: {citations}")
        print()

    print(f"✅ Filtered 100 → 5 papers (97.5% token reduction!)")
    print(f"💡 Original {len(results)} results available for different filters")


if __name__ == "__main__":
    main()
