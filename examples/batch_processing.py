#!/usr/bin/env python3
"""
Batch Processing Example - agent-zot v3.0+

Demonstrates processing multiple queries efficiently with the code execution pattern.

Token Efficiency:
- v2.1 (MCP tool): 50 queries × 20 papers × 800 tokens = 800,000 tokens
- v3.0 (code execution): 50 queries × top 3 × 400 tokens = 60,000 tokens
- **Reduction: 92.5%**

Real-World Use Case:
- Literature review across multiple topics
- Systematic review with predefined search terms
- Monitoring multiple research areas

Prerequisites:
- agent-zot installed: pip install -e .
- Zotero database indexed: agent-zot update-db --fulltext
"""

from agent_zot.mcp_tools.zot_search import zot_search
from typing import List, Dict, Any


def batch_search(queries: List[str], top_n: int = 3) -> Dict[str, List[Dict[str, Any]]]:
    """
    Execute multiple searches and return top N results for each.

    Args:
        queries: List of search queries
        top_n: Number of top results to keep per query

    Returns:
        Dictionary mapping query → top results
    """
    results = {}

    for query in queries:
        print(f"🔍 Searching: {query}")

        # Execute search
        papers = zot_search(query=query, limit=50)

        # Filter by recency (last 3 years)
        from datetime import datetime
        current_year = datetime.now().year
        recent = [p for p in papers if p.get('year', 0) >= current_year - 3]

        # Take top N
        top_papers = recent[:top_n]

        results[query] = top_papers
        print(f"   → Found {len(papers)} papers, keeping top {len(top_papers)}\n")

    return results


def main():
    """
    Process multiple research queries in a single batch.
    """
    print("🔍 Agent-Zot v3.0 - Batch Processing Example\n")

    # Define research queries
    queries = [
        "attention mechanisms transformers",
        "large language models scaling",
        "reinforcement learning robotics",
        "graph neural networks molecules",
        "few-shot learning meta-learning"
    ]

    print(f"📊 Batch processing {len(queries)} queries...\n")

    # Execute batch search (processes ALL queries in Python)
    results = batch_search(queries, top_n=3)

    # Summary report
    print("=" * 70)
    print("BATCH PROCESSING SUMMARY")
    print("=" * 70)
    print()

    total_papers = sum(len(papers) for papers in results.values())

    for query, papers in results.items():
        print(f"📌 {query}")
        for i, paper in enumerate(papers, 1):
            title = paper.get('title', 'Untitled')[:60]
            year = paper.get('year', 'N/A')
            print(f"   {i}. {title}... ({year})")
        print()

    print("=" * 70)
    print(f"✅ Processed {len(queries)} queries")
    print(f"✅ Retrieved {total_papers} papers total")
    print(f"💡 Token Efficiency: ~92.5% reduction vs v2.1 tool calls")
    print("=" * 70)


if __name__ == "__main__":
    main()
