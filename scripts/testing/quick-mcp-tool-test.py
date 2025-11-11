#!/usr/bin/env python3
"""
Quick MCP Tool Test - Direct test using agent-zot MCP tools

Tests tools by calling them directly, simulating how Claude would use them.
"""

import sys
import json
from pathlib import Path

# Test configurations
TESTS = {
    "Backend Connectivity": [
        {
            "name": "Docker containers running",
            "command": "docker ps --filter 'name=agent-zot' --format '{{.Names}}: {{.Status}}'",
            "type": "bash"
        }
    ],

    "zot_search (Intent Detection)": [
        {
            "name": "Fast Mode - semantic query",
            "query": "papers about working memory",
            "expected_mode": "fast",
            "tool": "zot_search"
        },
        {
            "name": "Graph-enriched - collaboration query",
            "query": "who collaborated with Anderson?",
            "expected_mode": "graph-enriched",
            "tool": "zot_search"
        },
        {
            "name": "Metadata-enriched - author/year query",
            "query": "papers by Anderson published in 2015",
            "expected_mode": "metadata-enriched",
            "tool": "zot_search"
        }
    ],

    "Backend Status": [
        {
            "name": "Qdrant status",
            "command": "curl -s http://localhost:6333/collections/agent_zot_chunks | python3 -m json.tool | grep -E 'points_count|status'",
            "type": "bash"
        },
        {
            "name": "Neo4j status",
            "command": "docker exec agent-zot-neo4j cypher-shell -u neo4j -p demodemo 'MATCH (n) RETURN count(n) as nodes LIMIT 1' 2>&1 | grep -v 'neo4j@'",
            "type": "bash"
        }
    ]
}


def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_bash_command(test):
    """Test a bash command."""
    import subprocess

    try:
        result = subprocess.run(
            test["command"],
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0 and result.stdout.strip():
            print(f"✅ {test['name']}")
            print(f"   {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {test['name']}")
            if result.stderr:
                print(f"   Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ {test['name']}: {str(e)}")
        return False


def main():
    """Run quick MCP tool tests."""
    print("=" * 70)
    print("  AGENT-ZOT QUICK MCP TOOL TEST")
    print("=" * 70)

    passed = 0
    failed = 0

    # Backend tests
    print_header("Backend Connectivity")
    for test in TESTS["Backend Connectivity"]:
        if test_bash_command(test):
            passed += 1
        else:
            failed += 1

    print_header("Backend Status Details")
    for test in TESTS["Backend Status"]:
        if test_bash_command(test):
            passed += 1
        else:
            failed += 1

    # Print test instructions for manual MCP tool testing
    print_header("Manual MCP Tool Tests")
    print("\nTo test the MCP tools, use these queries in Claude Desktop:\n")

    print("📋 ZOT_SEARCH MODE TESTS:")
    for test in TESTS["zot_search (Intent Detection)"]:
        print(f"\n  Test: {test['name']}")
        print(f"  Query: zot_search(\"{test['query']}\", limit=3)")
        print(f"  Expected mode: {test['expected_mode']}")

    print("\n\n📋 ZOT_SUMMARIZE MODE TESTS:")
    print("  1. Get item_key: Use zot_search() first to get a paper key")
    print("  2. Quick Mode: zot_summarize(item_key, \"What is this about?\")")
    print("  3. Targeted Mode: zot_summarize(item_key, \"What methodology?\")")
    print("  4. Comprehensive: zot_summarize(item_key, \"Summarize comprehensively\")")

    print("\n\n📋 ZOT_EXPLORE_GRAPH MODE TESTS:")
    print("  1. Influence: zot_explore_graph(\"Find influential papers on X\")")
    print("  2. Similarity: zot_explore_graph(\"Papers similar to X\", paper_key=KEY)")
    print("  3. Collaboration: zot_explore_graph(\"Who collaborated with Anderson?\")")
    print("  4. Temporal: zot_explore_graph(\"How has X evolved 2010-2020?\")")

    print("\n\n📋 OTHER TOOLS:")
    print("  • zot_manage_collections(\"list all collections\")")
    print("  • zot_manage_tags(\"list all tags\")")
    print("  • zot_manage_database(\"show status\")")
    print("  • zot_daemon_status()")

    # Summary
    print_header("Test Summary")
    total = passed + failed
    print(f"Automated tests: {total}")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")

    if failed > 0:
        print("\n⚠️  Some backend tests failed. Check Docker containers and databases.")
    else:
        print("\n✅ All automated tests passed!")

    print("\n📝 See scripts/MANUAL-TEST-CHECKLIST.md for complete testing guide")
    print("📝 Manual MCP tool tests should be run in Claude Desktop")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
