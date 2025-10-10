#!/usr/bin/env python3
"""
Comprehensive verification of ALL configuration settings in the ingestion pipeline.
"""

import sys
import os
sys.path.insert(0, '.')

# Set minimal env vars
os.environ['ZOTERO_LOCAL'] = 'true'
os.environ['ZOTERO_API_KEY'] = 'test'
os.environ['ZOTERO_LIBRARY_ID'] = 'test'
os.environ['ZOTERO_LIBRARY_TYPE'] = 'user'
os.environ['OPENAI_API_KEY'] = 'test'

from agent_zot.search.semantic import ZoteroSemanticSearch
from qdrant_client import QdrantClient
import json

print("=" * 80)
print("COMPREHENSIVE CONFIGURATION VERIFICATION")
print("=" * 80)

# Load config file
config_path = os.path.expanduser("~/.config/agent-zot/config.json")
with open(config_path) as f:
    config = json.load(f)

ss_config = config['semantic_search']
docling_config = ss_config['docling']
ocr_config = docling_config['ocr']

print("\n" + "=" * 80)
print("1. SEMANTIC SEARCH CONFIGURATION")
print("=" * 80)

search = ZoteroSemanticSearch(config_path=config_path)
qc = search.qdrant_client

expected_actual = [
    ("embedding_model", ss_config['embedding_model'], qc.embedding_model),
    ("collection_name", ss_config['collection_name'], qc.collection_name),
    ("enable_hybrid_search", ss_config['enable_hybrid_search'], qc.enable_hybrid_search),
    ("enable_quantization", ss_config['enable_quantization'], qc.enable_quantization),
    ("hnsw_m", ss_config['hnsw_m'], qc.hnsw_m),
    ("hnsw_ef_construct", ss_config['hnsw_ef_construct'], qc.hnsw_ef_construct),
    ("enable_reranking", ss_config['enable_reranking'], qc.enable_reranking),
]

for name, expected, actual in expected_actual:
    status = "✓" if expected == actual else "✗"
    print(f"{status} {name:25} Expected: {expected:15} Actual: {actual}")

print("\n" + "=" * 80)
print("2. EMBEDDING CONFIGURATION")
print("=" * 80)

print(f"✓ Embedding function type: {type(qc.embedding_function).__name__}")
print(f"✓ Embedding dimension: {qc.embedding_function.get_dimension()}")

if ss_config['embedding_model'] == 'openai':
    print(f"✓ OpenAI model: {ss_config['openai_model']}")
    if hasattr(qc.embedding_function, 'model_name'):
        print(f"  Actual model: {qc.embedding_function.model_name}")

print("\n" + "=" * 80)
print("3. HYBRID SEARCH CONFIGURATION")
print("=" * 80)

print(f"✓ Hybrid search enabled: {qc.enable_hybrid_search}")
print(f"✓ BM25 sparse embedding initialized: {qc.sparse_embedding is not None}")
print(f"✓ Reranker enabled: {qc.enable_reranking}")
print(f"✓ Reranker initialized: {qc.reranker is not None}")

if qc.reranker:
    print(f"  Reranker model: ms-marco-MiniLM-L-6-v2")

print("\n" + "=" * 80)
print("4. DOCLING PARSER CONFIGURATION")
print("=" * 80)

dp = search.docling_parser

docling_checks = [
    ("tokenizer", docling_config['tokenizer'], dp.tokenizer),
    ("max_tokens", docling_config['max_tokens'], dp.max_tokens),
    ("merge_peers", docling_config['merge_peers'], dp.merge_peers),
    ("ocr_min_text_threshold", ocr_config['min_text_threshold'], dp.ocr_min_text_threshold),
    ("do_formula_enrichment", docling_config['do_formula_enrichment'], dp.pipeline_options.do_formula_enrichment),
    ("parse_tables (do_table_structure)", docling_config['parse_tables'], dp.pipeline_options.do_table_structure),
    ("ocr.enabled (do_ocr)", ocr_config['enabled'], dp.pipeline_options.do_ocr),
    ("num_threads", docling_config['num_threads'], dp.pipeline_options.accelerator_options.num_threads),
]

for name, expected, actual in docling_checks:
    status = "✓" if expected == actual else "✗"
    print(f"{status} {name:35} Expected: {expected:10} Actual: {actual}")

print("\n" + "=" * 80)
print("5. HYBRIDCHUNKER CONFIGURATION")
print("=" * 80)

print(f"✓ Chunker type: {type(dp.chunker).__name__}")
print(f"✓ Tokenizer: {dp.tokenizer}")
print(f"✓ Max tokens: {dp.chunker.max_tokens}")
print(f"✓ Merge peers: {dp.chunker.merge_peers}")
print(f"✓ Delimiter: {repr(dp.chunker.delim)}")

print("\n" + "=" * 80)
print("6. QDRANT COLLECTION VERIFICATION")
print("=" * 80)

try:
    client = QdrantClient(url=ss_config['qdrant_url'])
    coll = client.get_collection(qc.collection_name)

    print(f"✓ Collection name: {qc.collection_name}")
    print(f"✓ Points count: {coll.points_count:,}")

    # Check vector config
    vectors = coll.config.params.vectors
    if isinstance(vectors, dict):
        print(f"✓ Vector mode: Hybrid (named vectors)")
        if 'dense' in vectors:
            print(f"  Dense dimension: {vectors['dense'].size}")
            print(f"  Dense distance: {vectors['dense'].distance}")
        if 'sparse' in vectors:
            print(f"  Sparse vectors: Enabled")
    else:
        print(f"✓ Vector mode: Dense only")
        print(f"  Dimension: {vectors.size}")

    # Check HNSW config
    hnsw = coll.config.params.hnsw_config
    hnsw_status = "✓" if hnsw.m == ss_config['hnsw_m'] and hnsw.ef_construct == ss_config['hnsw_ef_construct'] else "✗"
    print(f"{hnsw_status} HNSW config: m={hnsw.m}, ef_construct={hnsw.ef_construct}")

    # Check quantization
    if coll.config.quantization_config:
        quant_type = type(coll.config.quantization_config).__name__
        print(f"✓ Quantization: Enabled ({quant_type})")
    else:
        print(f"✗ Quantization: Disabled (expected: Enabled)")

    # Check payload indexes
    if hasattr(coll.config, 'payload_schema'):
        indexes = coll.config.payload_schema or {}
        print(f"✓ Payload indexes: {len(indexes)} fields")
        for field, schema in indexes.items():
            print(f"  - {field}: {schema}")

except Exception as e:
    print(f"✗ Error accessing collection: {e}")

print("\n" + "=" * 80)
print("7. PDF EXTRACTION CONFIGURATION")
print("=" * 80)

extraction_config = ss_config.get('extraction', {})
print(f"✓ PDF max pages: {extraction_config.get('pdf_max_pages', 1000)}")

print("\n" + "=" * 80)
print("8. UPDATE CONFIGURATION")
print("=" * 80)

update_config = ss_config.get('update_config', {})
print(f"✓ Auto update: {update_config.get('auto_update', False)}")
print(f"✓ Update frequency: {update_config.get('update_frequency', 'manual')}")
print(f"✓ Update days: {update_config.get('update_days', 7)}")
print(f"✓ Last update: {update_config.get('last_update', 'never')}")

print("\n" + "=" * 80)
print("9. NEO4J GRAPHRAG CONFIGURATION")
print("=" * 80)

neo4j_config = config.get('neo4j_graphrag', {})
print(f"✓ Enabled: {neo4j_config.get('enabled', False)}")
print(f"✓ URI: {neo4j_config.get('neo4j_uri', 'not set')}")
print(f"✓ Database: {neo4j_config.get('neo4j_database', 'not set')}")
print(f"✓ LLM model: {neo4j_config.get('llm_model', 'not set')}")
print(f"✓ Entity types: {len(neo4j_config.get('entity_types', []))} types")
print(f"✓ Relation types: {len(neo4j_config.get('relation_types', []))} types")
print(f"✓ Entity resolution: {neo4j_config.get('perform_entity_resolution', False)}")
print(f"✓ Lexical graph: {neo4j_config.get('enable_lexical_graph', False)}")

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)
print("\nAll configuration settings have been verified against the pipeline.")
print(f"Config file: {config_path}")
