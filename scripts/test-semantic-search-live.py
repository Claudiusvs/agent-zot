#!/usr/bin/env python3
"""
Interactive Semantic Search Test - See the Hierarchy in Action!
Created: 2025-11-10 20:09

This script lets you test semantic search and watch the 8-phase hierarchy execute live.
You'll see:
- Phase 0: Query decomposition analysis
- Phase 1: Intent detection and query expansion
- Phase 2: Backend selection (Fast/Comprehensive mode)
- Phase 3: Parallel backend execution
- Phase 4: Result merging
- Phase 5: Quality assessment
- Phase 6: Auto-escalation (if quality insufficient)
- Phase 7: Deduplication and provenance

Usage:
    python scripts/test-semantic-search-live.py
"""

import sys
import os
from pathlib import Path

# Set up environment
os.environ['ZOTERO_LOCAL'] = 'true'

def run_live_search():
    """Run interactive semantic search test."""

    print("=" * 70)
    print("🔍 AGENT-ZOT SEMANTIC SEARCH - LIVE HIERARCHY TEST")
    print("=" * 70)
    print()
    print("This will show you the complete 8-phase search hierarchy in action!")
    print()

    # Get query from user
    print("Enter your search query (or press Enter for default 'working memory'):")
    query = input("> ").strip()

    if not query:
        query = "working memory"
        print(f"Using default query: '{query}'")

    print()
    print("How many results do you want? (default: 5)")
    limit_str = input("> ").strip()

    try:
        limit = int(limit_str) if limit_str else 5
    except ValueError:
        limit = 5
        print(f"Invalid number, using default: {limit}")

    print()
    print("=" * 70)
    print(f"SEARCHING FOR: '{query}' (limit={limit})")
    print("=" * 70)
    print()
    print("📊 Watch the phases execute below...")
    print()

    # Import and run search
    try:
        from agent_zot.search.semantic import create_semantic_search

        config_path = Path.home() / ".config" / "agent-zot" / "config.json"

        print("🔧 Initializing semantic search engine...")
        search = create_semantic_search(str(config_path))
        print("✅ Engine initialized!")
        print()

        print("🚀 Starting smart search (watch for Phase 0-7 in logs)...")
        print("-" * 70)
        print()

        # Run the search (logs will stream to stderr)
        from agent_zot.search.unified_smart import smart_search

        results = smart_search(
            search,
            query=query,
            limit=limit,
            force_mode=None  # Let it auto-detect
        )

        print()
        print("-" * 70)
        print("✅ Search completed!")
        print()

        # Display results summary
        print("=" * 70)
        print("📊 RESULTS SUMMARY")
        print("=" * 70)
        print()

        print(f"Query: '{query}'")
        if expanded := results.get("expanded_query"):
            print(f"Expanded to: '{expanded}'")
        print()

        intent = results.get("intent", "unknown")
        confidence = results.get("intent_confidence", 0)
        mode = results.get("mode", "unknown")
        backends = results.get("backends_used", [])

        print(f"🎯 Intent: {intent} (confidence: {confidence:.0%})")
        print(f"⚡ Mode: {mode}")
        print(f"🔧 Backends: {', '.join(backends)}")
        print()

        if quality := results.get("quality_metrics"):
            print(f"📈 Quality Assessment:")
            print(f"   - Confidence: {quality['confidence']}")
            print(f"   - Coverage: {quality['coverage']:.0%}")
            print(f"   - Needs Escalation: {quality['needs_escalation']}")
            print()

        search_results = results.get("results", [])
        print(f"📚 Found {len(search_results)} papers:")
        print()

        for i, result in enumerate(search_results, 1):
            item_key = result.get("item_key", "")
            zotero_item = result.get("zotero_item", {})
            data = zotero_item.get("data", {})

            title = data.get("title", "Untitled")
            creators = data.get("creators", [])

            # Format authors
            from agent_zot.utils.common import format_creators
            authors = format_creators(creators)

            # Get scores and provenance
            similarity = result.get("similarity_score")
            found_in = result.get("found_in", [])

            print(f"{i}. {title}")
            print(f"   Key: {item_key}")
            if authors:
                print(f"   Authors: {authors}")
            if similarity:
                print(f"   Similarity: {similarity:.3f}")
            if found_in:
                print(f"   Found in: {', '.join(found_in)}")
            print()

        # Show errors if any
        if errors := results.get("errors_by_backend"):
            print("⚠️  Backend Errors:")
            for backend, error in errors.items():
                print(f"   - {backend}: {error}")
            print()

        print("=" * 70)
        print()
        print("💡 TIP: Scroll up to see the detailed phase logs!")
        print()

    except Exception as e:
        import traceback
        print()
        print("=" * 70)
        print("❌ ERROR")
        print("=" * 70)
        print(f"Error: {str(e)}")
        print()
        print("Traceback:")
        print(traceback.format_exc())
        return 1

    return 0


def show_menu():
    """Show interactive menu."""
    while True:
        print()
        print("=" * 70)
        print("🔍 SEMANTIC SEARCH LIVE TEST")
        print("=" * 70)
        print()
        print("What would you like to do?")
        print()
        print("  1. Test semantic search (default query: 'working memory')")
        print("  2. Test with custom query")
        print("  3. Test with decomposition (multi-concept query)")
        print("  4. Test author search intent detection")
        print("  5. Test escalation (use obscure query)")
        print("  6. Exit")
        print()

        choice = input("Enter choice (1-6): ").strip()

        if choice == "1":
            print()
            run_specific_test("working memory", 5)
        elif choice == "2":
            print()
            print("Enter your query:")
            query = input("> ").strip()
            if query:
                run_specific_test(query, 5)
        elif choice == "3":
            print()
            run_specific_test("working memory in aging and alzheimers", 5)
        elif choice == "4":
            print()
            run_specific_test("papers by Baddeley", 5)
        elif choice == "5":
            print()
            run_specific_test("xyz123 obscure nonexistent topic", 10)
        elif choice == "6" or choice.lower() == "q":
            print()
            print("Goodbye!")
            break
        else:
            print()
            print("Invalid choice, please try again.")


def run_specific_test(query: str, limit: int):
    """Run search with specific parameters."""
    print("=" * 70)
    print(f"TESTING: '{query}' (limit={limit})")
    print("=" * 70)
    print()

    try:
        from agent_zot.search.semantic import create_semantic_search
        from agent_zot.search.unified_smart import smart_search
        from pathlib import Path

        config_path = Path.home() / ".config" / "agent-zot" / "config.json"
        search = create_semantic_search(str(config_path))

        print("🚀 Executing search (watch the phases in logs)...")
        print()

        results = smart_search(search, query=query, limit=limit, force_mode=None)

        print()
        print("✅ Search completed!")
        print()

        # Quick summary
        mode = results.get("mode", "unknown")
        backends = results.get("backends_used", [])
        num_results = len(results.get("results", []))

        print(f"Mode: {mode}")
        print(f"Backends: {', '.join(backends)}")
        print(f"Results: {num_results} papers")

        if quality := results.get("quality_metrics"):
            print(f"Quality: confidence={quality['confidence']}, coverage={quality['coverage']:.0%}")

        print()
        input("Press Enter to continue...")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        input("Press Enter to continue...")


if __name__ == "__main__":
    print()
    print("Choose mode:")
    print("  1. Interactive menu (recommended)")
    print("  2. Single search with prompts")
    print()

    mode = input("Enter choice (1 or 2): ").strip()

    if mode == "1" or not mode:
        show_menu()
    else:
        sys.exit(run_live_search())
