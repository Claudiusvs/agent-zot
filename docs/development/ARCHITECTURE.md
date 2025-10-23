# Agent-Zot Architecture

**Last Updated:** October 2025

## System Overview

Agent-Zot is a production-grade MCP (Model Context Protocol) server that transforms Zotero research libraries into intelligent, searchable knowledge bases using semantic search and knowledge graphs.

```
┌──────────────────────────────────────────────────────────────┐
│                   Claude Desktop (Client)                     │
│                  or other MCP-compatible AI                   │
└────────────────────┬─────────────────────────────────────────┘
                     │ MCP Protocol (stdio)
                     ▼
┌──────────────────────────────────────────────────────────────┐
│              FastMCP Server (agent-zot)                       │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  38 MCP Tools (zot_semantic_search, etc.)              │  │
│  └────────────────────────────────────────────────────────┘  │
└──────┬──────────────┬──────────────────┬────────────────────┘
       │              │                  │
       ▼              ▼                  ▼
┌─────────────┐ ┌──────────────┐ ┌────────────────┐
│   Qdrant    │ │   Neo4j      │ │    Zotero      │
│ (Vector DB) │ │ (Graph DB)   │ │   Database     │
│             │ │              │ │                │
│  234K+      │ │  22K+        │ │  7,390         │
│  chunks     │ │  entities    │ │  items         │
└─────────────┘ └──────────────┘ └────────────────┘
```

## Core Components

### 1. MCP Server (`src/agent_zot/core/server.py`)
- **Framework:** FastMCP (async-first)
- **Tools:** 38 active tools for Zotero interaction
- **Protocol:** Stdio-based JSON-RPC communication
- **Entry point:** `agent-zot serve`

### 2. Search Engine (`src/agent_zot/search/semantic.py`)
- **Hybrid Search:** Dense (BGE-M3) + Sparse (BM25)
- **Re-ranking:** Cross-encoder boost (ms-marco-MiniLM)
- **Orchestration:** Routes between Qdrant, Neo4j, Zotero API
- **Quality Metrics:** Real-time confidence scoring

### 3. Vector Database (`src/agent_zot/clients/qdrant.py`)
- **Engine:** Qdrant (Docker container)
- **Vectors:** 1024D dense + 10K sparse per chunk
- **Index:** HNSW with INT8 quantization
- **Performance:** Sub-100ms searches, 75% RAM savings

### 4. PDF Parsing Pipeline (`src/agent_zot/parsers/docling.py`)
- **Parser:** Docling V2 (pypdfium2 backend)
- **Chunking:** HybridChunker (token-aware, 512 tokens)
- **Isolation:** Subprocess-based (crash-proof)
- **Performance:** 8 parallel workers, ~476 PDFs/hour

### 5. Knowledge Graph (`src/agent_zot/clients/neo4j_graphrag.py`)
- **Engine:** Neo4j (optional)
- **Entities:** 8 types (Person, Concept, Method, etc.)
- **Relationships:** 12 types (AUTHORED_BY, CITES, etc.)
- **Extraction:** Ollama (Mistral 7B) or GPT-4o-mini

### 6. Database Access (`src/agent_zot/database/local_zotero.py`)
- **Mode:** Direct SQLite access (ZOTERO_LOCAL=true)
- **Performance:** 10x faster than API
- **Features:** Parallel processing, batch indexing

## Data Flow

### Indexing Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Zotero Database (SQLite)                                 │
│    ~/zotero_database/zotero.sqlite                          │
│    ↓ SELECT items, attachments, metadata                    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Local Zotero Reader (local_zotero.py)                    │
│    ↓ 8 parallel workers, batch_size=200                     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. PDF Parsing (Docling V2, subprocess-isolated)            │
│    ↓ HybridChunker: 512 tokens/chunk, BGE-M3 tokenizer     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Parse Cache (parse_cache.py)                             │
│    ~/.cache/agent-zot/parsed_docs.db                        │
│    ↓ Deduplication via MD5, skip re-parsing                 │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Embedding Generation (qdrant.py)                         │
│    ↓ BGE-M3: 1024D dense + BM25 sparse, GPU batch_size=32  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. Qdrant Upload (batch_size=500)                           │
│    Docker volume: agent-zot-qdrant-data                     │
│    Collection: zotero_library_qdrant                        │
└─────────────────────────────────────────────────────────────┘
                          ↓ (Optional)
┌─────────────────────────────────────────────────────────────┐
│ 7. Neo4j Entity Extraction (async, concurrent)              │
│    ↓ Ollama Mistral 7B or GPT-4o-mini                       │
│    ↓ 8 entity types, 12 relationship types                  │
│    Docker volume: agent-zot-neo4j-data                      │
└─────────────────────────────────────────────────────────────┘
```

### Search Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User Query (via Claude Desktop)                          │
│    "Papers about dissociation and cognitive control"        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Query Processing (semantic.py)                           │
│    ↓ BGE-M3 embedding (GPU-accelerated)                     │
│    ↓ BM25 sparse vector generation                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Hybrid Search (Qdrant)                                   │
│    ↓ RRF fusion: dense semantic + sparse keyword            │
│    ↓ Sub-100ms query latency                                │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Re-ranking (ms-marco-MiniLM, GPU)                        │
│    ↓ 10-20% quality boost via cross-encoder                 │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Results Formatting                                        │
│    ↓ Markdown with metadata (title, authors, year)          │
│    ↓ Relevance scores, chunk context                        │
└─────────────────────────────────────────────────────────────┘
```

## Technology Stack

### Core Dependencies
- **Python:** 3.12+
- **MCP Framework:** FastMCP (async stdlib-based)
- **Vector DB:** Qdrant 1.7+
- **Graph DB:** Neo4j 5.23+ (optional)
- **PDF Parser:** Docling V2 (pypdfium2)
- **Embeddings:** sentence-transformers (BGE-M3)

### Infrastructure
- **Docker:** Qdrant + Neo4j containers
- **Storage:** Docker volumes for persistence
- **Database:** SQLite (Zotero), embedded (Qdrant/Neo4j)

## Configuration

### Main Config File
**Location:** `~/.config/agent-zot/config.json`

**Critical settings:**
- `client_env.ZOTERO_LOCAL`: Enable direct SQLite access
- `semantic_search.embedding_model`: Model selection
- `semantic_search.sentence_transformer_model`: BGE-M3
- `neo4j_graphrag.enabled`: Enable knowledge graph

See [`docs/guides/configuration.md`](../guides/configuration.md) for comprehensive guide.

## Performance Characteristics

### Indexing
- **Parsing:** 476 PDFs/hour (8 parallel workers, CPU-only)
- **Embedding:** 32 chunks/batch (GPU-accelerated)
- **Upload:** 500 points/batch to Qdrant
- **Total:** ~10-12 hours for 3,426 papers

### Search
- **Query latency:** <100ms (Qdrant)
- **Re-ranking:** +20ms (cross-encoder)
- **Total response:** <200ms end-to-end

### Memory
- **Qdrant:** ~2GB for 234K chunks (INT8 quantization)
- **Neo4j:** ~500MB for 22K entities
- **Parse cache:** ~650MB for 2,519 documents

## Scalability

### Current Capacity
- **Papers:** 7,390 Zotero items
- **Chunks:** 234,153 indexed
- **Entities:** 22,184 in graph

### Tested Limits
- **Qdrant:** 1M+ points (no degradation)
- **Neo4j:** 100K+ entities (acceptable performance)
- **Parse cache:** 10K+ documents (SQLite handles well)

## Key Design Decisions

### 1. Subprocess Isolation for PDF Parsing
**Rationale:** pypdfium2 C++ crashes bypass Python exception handling
**Benefit:** Zero crash propagation, 100% reliability
**Trade-off:** +5% overhead vs in-process parsing

### 2. CPU-Only Docling Processing
**Rationale:** MPS GPU memory contention with 8 parallel workers
**Benefit:** 7.3x faster (35s vs 254s per PDF)
**Trade-off:** No GPU acceleration for parsing (embeddings still use GPU)

### 3. Hybrid Search (Dense + Sparse)
**Rationale:** Dense vectors miss exact keyword matches
**Benefit:** Best of both worlds (semantic + keyword precision)
**Trade-off:** 2x storage per vector

### 4. INT8 Quantization
**Rationale:** 1024D vectors consume significant RAM
**Benefit:** 75% RAM savings, <2% accuracy loss
**Trade-off:** Slight precision reduction (acceptable)

### 5. Direct SQLite Access (ZOTERO_LOCAL=true)
**Rationale:** Zotero API rate limits + slower
**Benefit:** 10x faster indexing, no rate limits
**Trade-off:** Requires local Zotero installation

## Extension Points

### Adding New MCP Tools
1. Define in `src/agent_zot/core/server.py`
2. Use `@mcp.tool()` decorator
3. Return markdown-formatted strings
4. Handle errors gracefully

### Custom PDF Parsers
1. Extend `BasePDFParser` interface
2. Implement `parse_pdf()` method
3. Register in `semantic.py`

### Alternative Embedding Models
1. Update `config.json` with model name
2. Ensure tokenizer alignment
3. Reindex collection

### Custom Entity Types (Neo4j)
1. Edit `config.json` → `neo4j_graphrag.entity_types`
2. Add corresponding relationship types
3. Re-run population script

## Security Considerations

### Sensitive Data
- API keys stored in `~/.config/agent-zot/config.json` (chmod 600)
- Git history may contain old keys (see cleanup plan)
- Local Zotero database contains full library

### Network Exposure
- Qdrant: localhost:6333 (no authentication by default)
- Neo4j: localhost:7474/7687 (basic auth: neo4j/demodemo)
- MCP server: stdio only (no network exposure)

### Input Validation
- User queries sanitized before embedding
- File paths validated to prevent traversal
- HTML in notes requires sanitization for export

## Monitoring & Observability

### Logs
- **Indexing:** `/tmp/agent-zot-*.log`
- **MCP server:** stderr (captured by Claude Desktop)
- **Docker containers:** `docker logs <container>`

### Health Checks
- **Qdrant:** `curl http://localhost:6333/health`
- **Neo4j:** `curl http://localhost:7474`
- **Parse cache:** `agent-zot db-status`

### Metrics
- Parse cache hit rate
- Qdrant point count
- Neo4j entity/relationship counts
- Search query latency

## Future Enhancements

### Planned
- Granite VLM fallback for scanned PDFs
- Multi-modal search (figures, tables, equations)
- Automated literature review workflows
- Citation network analysis

### Experimental
- Real-time indexing (watch Zotero for changes)
- Distributed indexing (multi-machine)
- Advanced query DSL (boolean, proximity, faceted)

## References

- [FastMCP Documentation](https://fastmcp.com)
- [Qdrant Vector Search](https://qdrant.tech/documentation/)
- [Neo4j Graph Database](https://neo4j.com/docs/)
- [Docling PDF Parser](https://github.com/DS4SD/docling)
- [BGE Embeddings](https://huggingface.co/BAAI/bge-m3)

**For detailed configuration, see:**
- [Configuration Guide](../guides/configuration.md)
- [Settings Reference](../guides/SETTINGS_REFERENCE.md)
