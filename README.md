# Agent-Zot: Production-Ready Zotero MCP Server

A production-grade semantic search system for Zotero research libraries, built on [zotero-mcp](https://github.com/54yyyu/zotero-mcp) with significant enhancements:

- **Qdrant** vector database with hybrid search (dense + BM25 sparse)
- **Docling** advanced PDF parsing with structure-preserving chunking
- **Neo4j GraphRAG** knowledge graph extraction from research papers
- **BGE-M3** multilingual embeddings (SOTA performance, 1024D)
- **7-worker parallelization** optimized for M1 Pro architecture
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
- Advanced PDF parsing with DoclingParseV2 backend (10x faster)
- HybridChunker: token-aware + structure-preserving (512 tokens)
- Table and figure extraction with metadata
- Conditional OCR fallback for scanned documents
- Formula enrichment (LaTeX → text)
- Smart semantic boundary detection
- 7-worker parallel extraction

### ✅ Neo4j GraphRAG Integration
- Automatic knowledge graph extraction from papers
- Entity types: Person, Institution, Concept, Method, Dataset, Theory
- Relationship extraction with custom schema
- Entity resolution (merges similar entities)
- Lexical graph (keyword connections)
- Database indexes for 10-100x faster queries
- Powered by GPT-4o-mini

### Completed Enhancements
- [x] Qdrant vector database with hybrid search
- [x] Docling V2 backend with 7-worker parallelization
- [x] Neo4j GraphRAG knowledge graph extraction
- [x] BGE-M3 multilingual embeddings
- [x] Config-driven defaults (force_rebuild, extract_fulltext)
- [x] Always-on deduplication for restart-safe indexing
- [x] OCR fallback disabled for 4x faster parsing

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
2. Parse PDFs with Docling → hierarchical chunks (7 parallel workers)
3. Embed chunks with BGE-M3 (dense + BM25 sparse)
4. Store in Qdrant with metadata
5. Extract entities/relationships to Neo4j (GPT-4o-mini)

**Search Pipeline:**
1. Query → BGE-M3 embedding + BM25 sparse vector
2. Hybrid search in Qdrant (RRF fusion)
3. Optional: Graph traversal for related concepts
4. Cross-encoder reranking

## Configuration

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
- **num_threads:** `8` (M1 Pro 8 performance cores)
- **ocr.fallback_enabled:** `false` (disabled for 4x speedup)

### Neo4j GraphRAG
- **enabled:** `true`
- **llm_model:** `gpt-4o-mini`
- **entity_types:** Person, Institution, Concept, Method, Dataset, Theory
- **perform_entity_resolution:** `true`

See `config_examples/config_qdrant.json` for full template.

## Performance

- **Indexing speed:** ~40 seconds/paper (3,425 papers in ~35 hours)
- **Vector database:** Qdrant with INT8 quantization
- **Embedding model:** BGE-M3 (1024D, multilingual, SOTA)
- **Parallelization:** 7 workers optimized for M1 Pro
- **Search latency:** <100ms for hybrid search with reranking

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
