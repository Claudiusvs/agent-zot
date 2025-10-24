#!/usr/bin/env python3
"""Test script to check Neo4j initialization."""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from agent_zot.search.semantic import create_semantic_search

# Create semantic search instance with config
config_path = Path.home() / ".config" / "agent-zot" / "config.json"
print(f"Using config: {config_path}")
print(f"Config exists: {config_path.exists()}")

search_instance = create_semantic_search(str(config_path))

print(f"\nNeo4j client: {search_instance.neo4j_client}")
print(f"Neo4j client is None: {search_instance.neo4j_client is None}")

if search_instance.neo4j_client:
    print("\n✅ Neo4j client initialized successfully")

    # Try the availability check (using correct method)
    try:
        stats = search_instance.neo4j_client.get_graph_statistics()
        if "error" in stats:
            print(f"❌ Neo4j statistics error: {stats['error']}")
        else:
            total_nodes = stats.get("papers", 0) + stats.get("total_entities", 0)
            print(f"✅ Neo4j statistics successful:")
            print(f"   - Papers: {stats.get('papers', 0)}")
            print(f"   - Entities: {stats.get('total_entities', 0)}")
            print(f"   - Total nodes: {total_nodes}")
            print(f"   - Relationships: {stats.get('relationships', 0)}")
    except Exception as e:
        print(f"❌ Neo4j statistics failed: {e}")
else:
    print("\n❌ Neo4j client is None - not initialized")
