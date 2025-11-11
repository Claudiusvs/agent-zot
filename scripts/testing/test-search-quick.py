#!/usr/bin/env python3
"""
Quick Semantic Search Test - One Command to See Everything!

Usage:
    python scripts/test-search-quick.py "working memory"
    python scripts/test-search-quick.py "papers by Baddeley"
    python scripts/test-search-quick.py "attention in alzheimers and aging"
"""

import sys
import os
from pathlib import Path

# Set up environment
os.environ['ZOTERO_LOCAL'] = 'true'

def main():
    # Get query from command line or use default
    query = sys.argv[1] if len(sys.argv) > 1 else "working memory"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    print("=" * 70)
    print(f"🔍 TESTING: '{query}' (limit={limit})")
    print("=" * 70)
    print()
    print("📊 Watch for these phases in the logs:")
    print("   Phase 0: Query decomposition check")
    print("   Phase 1: Intent detection & query expansion")
    print("   Phase 2: Backend selection")
    print("   Phase 3: Parallel backend execution")
    print("   Phase 4: Result merging")
    print("   Phase 5: Quality assessment")
    print("   Phase 6: Auto-escalation (if needed)")
    print("   Phase 7: Deduplication & provenance")
    print()
    print("-" * 70)
    print()

    try:
        from agent_zot.search.semantic import create_semantic_search
        from agent_zot.search.unified_smart import smart_search

        config_path = Path.home() / ".config" / "agent-zot" / "config.json"
        search = create_semantic_search(str(config_path))

        # Run search (all phase logs will appear here)
        results = smart_search(search, query=query, limit=limit)

        print()
        print("-" * 70)
        print()
        print("=" * 70)
        print("📊 RESULTS")
        print("=" * 70)
        print()

        # Show intent and mode
        intent = results.get("intent", "unknown")
        confidence = results.get("intent_confidence", 0)
        mode = results.get("mode", "unknown")
        backends = results.get("backends_used", [])

        print(f"🎯 Intent: {intent} (confidence: {confidence:.0%})")
        print(f"⚡ Mode: {mode}")
        print(f"🔧 Backends: {', '.join(backends)}")
        print()

        # Show quality
        if quality := results.get("quality_metrics"):
            escalated = " → ESCALATED!" if quality['needs_escalation'] else ""
            print(f"📈 Quality: {quality['confidence']} ({quality['coverage']:.0%} coverage){escalated}")
            print()

        # Show results
        papers = results.get("results", [])
        print(f"📚 Found {len(papers)} papers:")
        print()

        for i, paper in enumerate(papers, 1):
            data = paper.get("zotero_item", {}).get("data", {})
            title = data.get("title", "Untitled")

            from agent_zot.utils.common import format_creators
            authors = format_creators(data.get("creators", []))

            sim = paper.get("similarity_score")
            found_in = ', '.join(paper.get("found_in", []))

            print(f"{i}. {title}")
            if authors:
                print(f"   {authors}")
            if sim:
                print(f"   Score: {sim:.3f} | Found in: {found_in}")
            print()

        print("=" * 70)
        print()
        print("💡 Scroll up to see the detailed phase-by-phase execution!")
        print()

    except Exception as e:
        import traceback
        print()
        print("❌ ERROR:")
        print(str(e))
        print()
        print(traceback.format_exc())
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
