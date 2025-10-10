# Agent-Zot: Production-Ready Zotero MCP Server

A production-grade semantic search system for Zotero research libraries, built on [zotero-mcp](https://github.com/54yyyu/zotero-mcp) with significant enhancements:

- **Qdrant** vector database with hybrid search (dense + BM25 sparse)
- **Docling V2** advanced PDF parsing with CPU-only processing (7x faster than GPU)
- **Neo4j GraphRAG** knowledge graph extraction from research papers
- **BGE-M3** multilingual embeddings (SOTA performance, 1024D, GPU-accelerated)
- **8-worker parallelization** optimized for M1 Pro with CPU-only Docling
- **Config-driven** defaults for safe incremental indexing

## Original Project

Based on [zotero-mcp](https://github.com/54yyyu/zotero-mcp) by @54yyyu

## Key Features

### ✅ Qdrant Vector Database
- Production-ready vector database with hybrid search
- **Dense vectors:** BGE-M3 embeddings (1024D, multilingual)
- **Sparse vectors:** BM25 for keyword matching
- **Hybrid search:** RRF fusion combining semantic + keyword
- INT8 quantization (75% RAM savings)
- HNSW indexing (m=32, ef=200) for fast retrieval
- Cross-encoder reranking for improved quality
- Runs in Docker for easy management

### ✅ Docling Document Parsing
- Advanced PDF parsing with DoclingParseV2 backend
- **CPU-only processing:** 7.3x faster than GPU (35s vs 254s per PDF)
- **8-worker parallelization:** Optimized for M1 Pro without memory contention
- HybridChunker: token-aware + structure-preserving (512 tokens)
- Table and figure extraction disabled by default (4x speedup)
- Conditional OCR fallback disabled by default (prevents crashes)
- BoundedThreadPoolExecutor prevents semaphore leaks

### ✅ Neo4j GraphRAG Integration
- Automatic knowledge graph extraction from papers
- Entity types: Person, Institution, Concept, Method, Dataset, Theory
- Relationship extraction with custom schema
- Entity resolution (merges similar entities)
- Lexical graph (keyword connections)
- Database indexes for 10-100x faster queries
- Powered by GPT-4o-mini

### Completed Enhancements
- [x] Qdrant vector database with hybrid search (dense + BM25 sparse)
- [x] Docling V2 backend with CPU-only processing (7.3x faster than GPU)
- [x] 8-worker parallelization with BoundedThreadPoolExecutor (prevents semaphore leaks)
- [x] Neo4j GraphRAG knowledge graph extraction (GPT-4o-mini)
- [x] BGE-M3 multilingual embeddings (1024D, GPU-accelerated)
- [x] Config-driven defaults (force_rebuild, extract_fulltext)
- [x] Always-on deduplication for restart-safe indexing
- [x] OCR and table/formula parsing disabled by default (4x speedup)

## Quick Start

### Prerequisites
- Docker (for Qdrant and Neo4j)
- Python 3.12 virtual environment
- Zotero with local database access

### Installation

1. **Start required services:**

```bash
# Qdrant (vector database)
docker run -d -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage:z \
  --name agent-zot-qdrant \
  qdrant/qdrant

# Neo4j (knowledge graph) - optional
docker run -d -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/demodemo \
  --name agent-zot-neo4j \
  neo4j:5.15.0
```

2. **Configure the system:**

```bash
cp config_examples/config_qdrant.json ~/.config/zotero-mcp/config.json
# Edit with your API keys and settings
```

3. **Index your library:**

```bash
source ~/toolboxes/zotero-mcp-env/bin/activate
zotero-mcp update-db --fulltext
```

The `--fulltext` flag is optional (defaults from config). Use `--force-rebuild` only when you need to completely rebuild the index.

See [CLAUDE.md](./CLAUDE.md) for comprehensive documentation.

## Architecture

### Core Components
- **server.py** - FastMCP server with 20+ MCP tools
- **semantic_search.py** - Orchestrates Qdrant, Docling, and Neo4j
- **qdrant_client_wrapper.py** - Hybrid search (dense + BM25 sparse)
- **docling_parser.py** - HybridChunker with V2 backend (no OCR)
- **neo4j_graphrag_client.py** - Knowledge graph extraction
- **local_db.py** - Direct SQLite access for faster indexing
- **client.py** - Zotero API wrapper

### Data Flow
**Indexing Pipeline:**
1. Fetch Zotero items (API or local SQLite)
2. Parse PDFs with Docling V2 → hierarchical chunks (8 parallel workers, CPU-only, ~35s/PDF)
3. Embed chunks with BGE-M3 (dense + BM25 sparse, GPU-accelerated)
4. Store in Qdrant with metadata (INT8 quantization)
5. Extract entities/relationships to Neo4j (GPT-4o-mini, optional)

**Search Pipeline:**
1. Query → BGE-M3 embedding + BM25 sparse vector (GPU-accelerated)
2. Hybrid search in Qdrant (RRF fusion combining semantic + keyword)
3. Cross-encoder reranking (ms-marco-MiniLM-L-6-v2, GPU-accelerated)
4. Optional: Graph traversal for related concepts via Neo4j

## Configuration

**📋 For complete configuration reference, see [CONFIGURATION.md](./CONFIGURATION.md) - the authoritative documentation of the standard default production pipeline.**

All settings in `~/.config/zotero-mcp/config.json`. Key sections:

### Semantic Search
- **embedding_model:** `sentence-transformers` (BGE-M3)
- **enable_hybrid_search:** `true` (dense + BM25 sparse)
- **enable_quantization:** `true` (INT8, 75% RAM savings)
- **enable_reranking:** `true` (cross-encoder quality boost)
- **force_rebuild:** `false` (safe incremental default)
- **extract_fulltext:** `true` (full PDF parsing default)

### Docling
- **tokenizer:** `BAAI/bge-m3` (aligned with embeddings)
- **max_tokens:** `512` (chunk size)
- **num_threads:** `2` (per worker, 8 workers × 2 = 16 threads)
- **subprocess_timeout:** `3600` (1 hour, handles large PDFs)
- **ocr.fallback_enabled:** `false` (disabled for consistency)

### Neo4j GraphRAG
- **enabled:** `true`
- **llm_model:** `gpt-4o-mini`
- **entity_types:** Person, Institution, Concept, Method, Dataset, Theory
- **perform_entity_resolution:** `true`

See `config_examples/config_qdrant.json` for full template.

## Performance

- **Indexing speed:** ~35 seconds/PDF average (3,425 papers in ~33 hours)
- **Parallelization:** 8 workers, CPU-only Docling (7.3x faster than GPU)
- **Vector database:** Qdrant with INT8 quantization (75% RAM savings)
- **Embedding model:** BGE-M3 (1024D, multilingual, SOTA, GPU-accelerated)
- **Search latency:** <100ms for hybrid search with reranking

**Performance Notes:**
- CPU-only Docling avoids MPS GPU memory exhaustion (18GB limit)
- GPU still used for embeddings (sequential batch processing, no contention)
- BoundedThreadPoolExecutor prevents semaphore leaks with batch processing

## Development

### Monitoring

```bash
# Check Qdrant status
curl http://localhost:6333/collections/zotero_library_qdrant

# Check Neo4j status
curl http://neo4j:demodemo@localhost:7474

# Monitor indexing progress
tail -f /tmp/zotero-final-clean.log

# View Docker logs
docker logs agent-zot-qdrant
docker logs agent-zot-neo4j
```

### Testing

```bash
# Quick database status
zotero-mcp db-status

# Inspect specific item
zotero-mcp db-inspect --key ITEM_KEY

# Test search via Claude
# Ask: "Search my library for papers about reinforcement learning"
```

## License

Same as original project (check upstream repo)
