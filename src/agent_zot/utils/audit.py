#!/usr/bin/env python3
"""
Comprehensive Agent Zot System Audit Script
Performs deep inspection of all components with raw data verification
"""

import sys
import sqlite3
import json
from pathlib import Path
from qdrant_client import QdrantClient
from neo4j import GraphDatabase
import os

print("="*80)
print("AGENT ZOT COMPREHENSIVE SYSTEM AUDIT")
print("="*80)
print()

# ============================================================================
# 1. ZOTERO DATABASE AUDIT
# ============================================================================
print("1️⃣  ZOTERO DATABASE AUDIT")
print("-" * 80)

db_path = Path.home() / 'zotero_database' / 'zotero.sqlite'
print(f"Database: {db_path}")
print(f"Exists: {db_path.exists()}")
print(f"Size: {db_path.stat().st_size / (1024**3):.2f} GB")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Item counts
cursor.execute('''
    SELECT itemTypes.typeName, COUNT(*) as count
    FROM items
    JOIN itemTypes ON items.itemTypeID = itemTypes.itemTypeID
    WHERE items.itemID NOT IN (SELECT itemID FROM deletedItems)
    GROUP BY itemTypes.typeName
    ORDER BY count DESC
    LIMIT 10
''')
print("\nTop item types:")
for name, count in cursor.fetchall():
    print(f"  {name}: {count:,}")

# PDF attachments
cursor.execute('''
    SELECT COUNT(*) FROM itemAttachments
    WHERE contentType = "application/pdf"
    AND itemID NOT IN (SELECT itemID FROM deletedItems)
''')
pdf_count = cursor.fetchone()[0]
print(f"\nPDF attachments: {pdf_count:,}")

# Fulltext status
cursor.execute('SELECT COUNT(*) FROM fulltextItems')
fulltext_count = cursor.fetchone()[0]
print(f"Items with Zotero fulltext: {fulltext_count:,}")

conn.close()
print("✅ Zotero database accessible\n")

# ============================================================================
# 2. QDRANT VECTOR DATABASE AUDIT
# ============================================================================
print("2️⃣  QDRANT VECTOR DATABASE AUDIT")
print("-" * 80)

try:
    client = QdrantClient(url='http://localhost:6333')
    collections = client.get_collections()
    print(f"Qdrant server: ONLINE (http://localhost:6333)")
    print(f"Collections: {len(collections.collections)}")

    # Get collection details
    coll = client.get_collection('zotero_library_qdrant')
    print(f"\nCollection: zotero_library_qdrant")
    print(f"  Points: {coll.points_count:,}")
    print(f"  Status: {coll.status}")
    print(f"  Optimizer: {coll.optimizer_status}")

    # Vector config
    vectors = coll.config.params.vectors
    if isinstance(vectors, dict):
        if 'dense' in vectors:
            dense = vectors['dense']
            print(f"\n  Dense Vectors:")
            print(f"    Dimension: {dense.size}D")
            print(f"    Distance: {dense.distance}")
            if hasattr(dense, 'hnsw_config') and dense.hnsw_config:
                print(f"    HNSW m: {dense.hnsw_config.m}")
                print(f"    HNSW ef_construct: {dense.hnsw_config.ef_construct}")
        if 'sparse' in vectors:
            print(f"  Sparse Vectors: ENABLED (BM25)")

    # Quantization
    quant = coll.config.quantization_config
    if quant:
        print(f"\n  Quantization: {type(quant).__name__}")
    else:
        print(f"\n  Quantization: DISABLED")

    # Sample points
    scroll_result = client.scroll(
        collection_name='zotero_library_qdrant',
        limit=2,
        with_payload=True,
        with_vectors=False
    )

    print(f"\n  Sample points:")
    for i, point in enumerate(scroll_result[0], 1):
        p = point.payload
        doc_len = len(p.get('document', ''))
        print(f"    Point {i}: item={p.get('item_key')}, doc_len={doc_len:,} chars")

    print("✅ Qdrant fully configured and populated\n")

except Exception as e:
    print(f"❌ Qdrant error: {e}\n")

# ============================================================================
# 3. NEO4J GRAPHRAG AUDIT
# ============================================================================
print("3️⃣  NEO4J GRAPHRAG AUDIT")
print("-" * 80)

try:
    driver = GraphDatabase.driver(
        "neo4j://127.0.0.1:7687",
        auth=("neo4j", "demodemo")
    )

    with driver.session(database="neo4j") as session:
        # Check if server is online
        result = session.run("RETURN 1")
        result.single()
        print("Neo4j server: ONLINE (neo4j://127.0.0.1:7687)")

        # Count nodes
        result = session.run("MATCH (n) RETURN count(n) as count")
        node_count = result.single()['count']
        print(f"Total nodes: {node_count:,}")

        # Count relationships
        result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
        rel_count = result.single()['count']
        print(f"Total relationships: {rel_count:,}")

        # Node types
        result = session.run("MATCH (n) RETURN labels(n)[0] as label, count(*) as count ORDER BY count DESC LIMIT 5")
        print("\nTop node types:")
        for record in result:
            print(f"  {record['label']}: {record['count']:,}")

        # Relationship types
        result = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(*) as count ORDER BY count DESC LIMIT 5")
        print("\nTop relationship types:")
        for record in result:
            print(f"  {record['type']}: {record['count']:,}")

    driver.close()
    print("✅ Neo4j knowledge graph active\n")

except Exception as e:
    print(f"❌ Neo4j error: {e}\n")

# ============================================================================
# 4. CONFIGURATION FILES AUDIT
# ============================================================================
print("4️⃣  CONFIGURATION FILES AUDIT")
print("-" * 80)

config_path = Path.home() / '.config' / 'agent-zot' / 'config.json'
print(f"Config: {config_path}")
print(f"Exists: {config_path.exists()}")

with open(config_path) as f:
    config = json.load(f)

print("\nSemantic Search Config:")
print(f"  Embedding model: {config['semantic_search']['embedding_model']}")
print(f"  OpenAI model: {config['semantic_search']['openai_model']}")
print(f"  Collection: {config['semantic_search']['collection_name']}")
print(f"  Hybrid search: {config['semantic_search']['enable_hybrid_search']}")
print(f"  Quantization: {config['semantic_search']['enable_quantization']}")
print(f"  Reranking: {config['semantic_search']['enable_reranking']}")
print(f"  Batch size: {config['semantic_search']['batch_size']}")

print("\nDocling Config:")
print(f"  Threads: {config['semantic_search']['docling']['num_threads']}")
print(f"  Max tokens: {config['semantic_search']['docling']['max_tokens']}")
print(f"  OCR enabled: {config['semantic_search']['docling']['ocr']['enabled']}")

print("\nNeo4j GraphRAG Config:")
print(f"  Enabled: {config['neo4j_graphrag']['enabled']}")
print(f"  URI: {config['neo4j_graphrag']['neo4j_uri']}")
print(f"  LLM: {config['neo4j_graphrag']['llm_model']}")
print(f"  Entity resolution: {config['neo4j_graphrag']['perform_entity_resolution']}")

print("✅ Configuration valid\n")

# ============================================================================
# 5. BACKGROUND PROCESSES AUDIT
# ============================================================================
print("5️⃣  BACKGROUND PROCESSES AUDIT")
print("-" * 80)

import subprocess

# Check for indexing processes
result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
lines = result.stdout.split('\n')

python_procs = [l for l in lines if 'python' in l.lower() and 'semantic_search' in l]
print(f"Active indexing processes: {len(python_procs)}")
for proc in python_procs[:3]:  # Show first 3
    parts = proc.split()
    if len(parts) > 10:
        pid = parts[1]
        cpu = parts[2]
        mem = parts[3]
        print(f"  PID {pid}: CPU={cpu}%, MEM={mem}%")

# Check Qdrant
qdrant_procs = [l for l in lines if 'qdrant' in l.lower()]
print(f"\nQdrant processes: {len(qdrant_procs)}")

# Check Neo4j
neo4j_procs = [l for l in lines if 'neo4j' in l.lower() or 'java' in l.lower()]
print(f"Neo4j/Java processes: {len(neo4j_procs)}")

print("✅ Process audit complete\n")

print("="*80)
print("AUDIT COMPLETE")
print("="*80)
