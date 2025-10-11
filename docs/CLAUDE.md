# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Agent-Zot is a customized Zotero Model Context Protocol (MCP) server that provides semantic search capabilities over Zotero research libraries. Built on [zotero-mcp](https://github.com/54yyyu/zotero-mcp), it has been enhanced with:

- **Qdrant vector database** for production-grade semantic search (replaces ChromaDB)
- **Docling parser** for advanced PDF parsing with structure preservation
- **Neo4j GraphRAG** for knowledge graph extraction from papers
- **Hybrid search** combining dense and sparse (BM25) embeddings

The server exposes 20+ MCP tools for searching, retrieving, and managing Zotero libraries, enabling LLMs to interact with research papers through semantic search and metadata queries.

## Common Commands

### CLI Commands
All CLI commands use the `agent-zot` entry point:

```bash
# Show version
agent-zot version

# Interactive setup
agent-zot setup

# Show installation and config info
agent-zot setup-info

# Update semantic search database
agent-zot update-db --force-rebuild --extract-fulltext

# Check database status
agent-zot db-status

# Inspect indexed documents
agent-zot db-inspect --key ITEM_KEY

# Run MCP server
agent-zot serve
```

### Git Version Control

Agent-Zot uses Git tags to snapshot stable versions for easy rollback:

```bash
# View available version tags
git tag -l

# Rollback to a specific version (read-only inspection)
git checkout v1.0-subprocess-isolation

# Create a new branch from a snapshot
git checkout -b my-backup v1.0-subprocess-isolation

# Hard reset to a version (destructive - use with caution)
git reset --hard v1.0-subprocess-isolation

# Return to latest version
git checkout main
```

**Available Snapshots:**
- `v1.0-subprocess-isolation` - Subprocess-isolated Docling with crash protection (Oct 2025)

### Docker Commands
Qdrant runs in Docker:

```bash
# Check Qdrant status
docker ps --filter "name=agent-zot-qdrant"

# View Qdrant logs
docker logs agent-zot-qdrant

# Check Qdrant collections via API
curl http://localhost:6333/collections
```

### Development Setup

```bash
# Activate virtual environment (typical location)
source ~/toolboxes/agent-zot-env/bin/activate

# Install in development mode
pip install -e .

# Run tests (for new parsers)
python test_pymupdf.py
```

## Standard Default Production Pipeline

**📋 IMPORTANT: See [CONFIGURATION.md](./CONFIGURATION.md) for the complete, authoritative configuration reference.**

This document describes the standard default production pipeline configuration including:
- All Docling parser settings (HybridChunker, subprocess isolation, timeouts)
- All Qdrant vector database settings (hybrid search, quantization, HNSW indexing)
- All Neo4j GraphRAG settings (entity types, relationships, resolution)
- Performance optimizations for M1 Pro (8 workers, 16 threads, batch sizes)
- Critical fixes (subprocess isolation, removed pdfminer fallback)

**When making changes to the pipeline, always update CONFIGURATION.md to reflect the new standard defaults.**

## Architecture

### Project Structure

Agent-Zot follows a professional Python package layout:

```
agent-zot/
├── src/agent_zot/          # Main package
│   ├── core/               # Core functionality (server, CLI)
│   ├── clients/            # External integrations (Zotero, Qdrant, Neo4j)
│   ├── parsers/            # Document parsers (Docling, PyMuPDF)
│   ├── database/           # Database access (local Zotero)
│   ├── search/             # Search functionality (semantic search)
│   ├── utils/              # Utilities (setup, updater, verification)
│   └── scripts/            # Shell scripts (backup, indexing)
├── docs/                   # Documentation
├── tests/                  # Unit and integration tests
└── config_examples/        # Example configurations
```

### Core Components

1. **src/agent_zot/core/server.py** - FastMCP server with 20+ tools for Zotero interaction
2. **src/agent_zot/search/semantic.py** - Orchestrates semantic search with Qdrant, Docling, and Neo4j
3. **src/agent_zot/clients/qdrant.py** - Qdrant vector database client with hybrid search (dense + BM25 sparse)
4. **src/agent_zot/parsers/docling.py** - Advanced PDF parsing using Docling's HybridChunker
5. **src/agent_zot/clients/neo4j_graphrag.py** - Knowledge graph extraction from research papers
6. **src/agent_zot/clients/zotero.py** - Zotero API wrapper (pyzotero)
7. **src/agent_zot/database/local_zotero.py** - Direct SQLite access to local Zotero database for faster indexing
8. **src/agent_zot/core/cli.py** - Command-line interface entry points

### Data Flow

**Indexing Pipeline:**
1. Zotero items fetched via API or local SQLite database (database/local_zotero.py)
2. PDF attachments parsed with Docling V2 backend → hierarchical chunks with metadata (parsers/docling.py)
   - 8 parallel workers, CPU-only processing, ~7-8 seconds per PDF average (476 PDFs/hour)
   - Standard ThreadPoolExecutor with as_completed() for natural backpressure (no semaphore leaks)
   - Fresh DoclingParser instance per PDF for thread safety
   - Batch processing (200 items/batch) with automatic deduplication
3. Chunks embedded via BGE-M3 model (sentence-transformers, 1024D, GPU-accelerated with batch_size=32)
4. Dense + sparse (BM25) vectors stored in Qdrant (batch_size=500 for optimal throughput)
5. [Optional] Neo4j knowledge graph extraction (clients/neo4j_graphrag.py, GPT-4o-mini)

**Search Pipeline:**
1. Query → BGE-M3 embedding (GPU-accelerated) + BM25 sparse vector
2. Hybrid search in Qdrant (RRF fusion of dense semantic + sparse keyword matching)
3. Cross-encoder reranking (ms-marco-MiniLM-L-6-v2, GPU-accelerated) for quality boost
4. Results filtered by metadata (item_key, doc_type, etc.)
5. [Optional] Graph traversal for related concepts via Neo4j

### MCP Tools

The server exposes 20+ tools prefixed with `zot_`:

**Core Search:**
- `zot_search_items` - Title/creator/year search
- `zot_semantic_search` - Vector similarity search with hybrid ranking
- `zot_graph_search` - Knowledge graph-based search (requires Neo4j)
- `zot_advanced_search` - Multi-field Boolean search

**Metadata Retrieval:**
- `zot_get_item_metadata` - Full metadata (markdown or BibTeX)
- `zot_get_item_fulltext` - Extracted PDF text
- `zot_get_item_children` - Attachments and notes
- `zot_get_annotations` - PDF annotations
- `zot_get_notes` - Item notes

**Organization:**
- `zot_get_collections` - List collections
- `zot_get_collection_items` - Items in collection
- `zot_get_tags` - All tags
- `zot_search_by_tag` - Search by tag

**Database Management:**
- `zot_update_search_database` - Update/rebuild semantic index
- `zot_get_search_database_status` - Index statistics

See src/agent_zot/core/server.py for full tool definitions and parameters.

## Configuration

### Main Config File
`~/.config/agent-zot/config.json` contains all settings:

```json
{
  "client_env": {
    "ZOTERO_LOCAL": "true",           // Use local Zotero database (faster)
    "ZOTERO_API_KEY": "...",          // For remote API
    "ZOTERO_LIBRARY_ID": "...",
    "OPENAI_API_KEY": "..."           // For embeddings
  },
  "semantic_search": {
    "embedding_model": "openai",
    "openai_model": "text-embedding-3-large",
    "collection_name": "zotero_library_qdrant",
    "qdrant_url": "http://localhost:6333",
    "update_config": {
      "auto_update": false,
      "update_frequency": "manual"
    },
    "docling": {
      "chunk_size": 1000,
      "chunk_overlap": 200,
      "parse_tables": true,
      "parse_figures": true
    }
  }
}
```

See `config_examples/config_qdrant.json` for template.

### Database Locations

- **Qdrant storage:** `~/agent-zot/qdrant_storage/` (managed by Docker)
- **Zotero SQLite:** Auto-detected in `~/Zotero/zotero.sqlite` (macOS)
- **Old ChromaDB:** `~/.config/agent-zot/chroma_db/` (deprecated, can be removed)

## Key Implementation Details

### Semantic Search

`semantic_search.py` implements two-phase indexing:

1. **Metadata indexing** - Fast, includes title/abstract/notes
2. **Full-text indexing** - Slower, uses Docling to parse PDFs

Use `--extract-fulltext` flag to enable full-text parsing during updates.

### Hybrid Search

`qdrant_client_wrapper.py` implements hybrid search:

- **Dense vectors** - OpenAI text-embedding-3-large (3072 dimensions)
- **Sparse vectors** - BM25 with TF-IDF (10,000 features)
- **Fusion** - RRF (Reciprocal Rank Fusion) to combine results

### Docling Parser

`docling_parser.py` uses HybridChunker with CPU-only processing:

- **CPU-only mode:** Forced `device="cpu"` to avoid MPS GPU memory exhaustion with 8 parallel workers
- **Performance:** 7.3x faster than GPU (35s vs 254s per PDF) due to parallel processing without memory contention
- **Token-aware chunking:** Default 512 tokens aligned with BGE-M3 embeddings
- **Structure preservation:** Respects document hierarchy (headings, sections)
- **Table/formula parsing:** Disabled by default (`parse_tables=false`, `do_formula_enrichment=false`) for 4x speedup
- **Conditional OCR:** Disabled by default (`fallback_enabled=false`), only enabled for scanned PDFs if configured
- **8-worker parallelization:** Optimized for M1 Pro (8 performance cores)

**GPU vs CPU Trade-off:**
- **Embeddings (BGE-M3):** Still use MPS GPU for 5-10x faster batch processing (sequential, no contention)
- **Docling parsing:** Use CPU for 7.3x faster processing (parallel, memory-bound workload)
- **Result:** Best of both worlds - parallel CPU parsing + fast GPU embeddings

### Local Mode

When `ZOTERO_LOCAL=true`:

- Direct SQLite access via `local_db.py` for faster indexing
- No API rate limits
- Requires local Zotero installation

### Neo4j GraphRAG (Optional)

`neo4j_graphrag_client.py` extracts knowledge graphs:

- Entities: Person, Institution, Concept, Method, Dataset, Theory
- Relationships: AUTHORED_BY, USES_METHOD, DISCUSSES_CONCEPT, etc.
- Schema defined in `RESEARCH_PAPER_SCHEMA` and `RESEARCH_PAPER_RELATIONS`

Enabled by setting Neo4j connection in config.

## Development Patterns

### Adding New MCP Tools

1. Define tool in `server.py` with `@mcp.tool()` decorator
2. Use `ctx: Context` parameter for logging
3. Return markdown-formatted strings
4. Handle errors gracefully with try/except

Example:
```python
@mcp.tool(
    name="zot_my_tool",
    description="Tool description for LLM"
)
def my_tool(param: str, *, ctx: Context) -> str:
    try:
        ctx.info(f"Processing {param}")
        # Implementation
        return "Result"
    except Exception as e:
        ctx.error(f"Error: {e}")
        return f"Error: {e}"
```

### Modifying Document Parsing

Edit `docling_parser.py`:

- `DoclingParser.__init__()` - Configure chunking parameters
- `parse_pdf()` - Core parsing logic
- `parse_zotero_attachment()` - Zotero-specific wrapper

### Extending Vector Search

Edit `qdrant_client_wrapper.py`:

- `QdrantClientWrapper.upsert()` - Indexing logic
- `QdrantClientWrapper.search()` - Query logic
- `BM25SparseEmbedding` - Sparse vector generation

### Testing Changes

Run semantic search update to test end-to-end:

```bash
agent-zot update-db --force-rebuild --extract-fulltext --limit 10
```

Check results:
```bash
agent-zot db-status
agent-zot db-inspect --key ITEM_KEY
```

## Troubleshooting

### Qdrant Connection Issues

```bash
# Check Docker container
docker ps | grep qdrant

# Restart if needed
docker restart agent-zot-qdrant

# Check logs
docker logs agent-zot-qdrant
```

### Claude Desktop Integration

Config file location: `~/Library/Application Support/Claude/claude_desktop_config.json`

Use `agent-zot setup-info` to generate correct config snippet.

### Parsing Errors and Performance

**Common issues:**
- **MPS out of memory:** Fixed by forcing CPU-only processing (`device="cpu"` in docling_parser.py)
- **Slow parsing (>200s/PDF):** Usually indicates GPU memory thrashing - verify logs show `Accelerator device: 'cpu'`
- **Large PDFs:** Consider `pdf_max_pages` limit in config (default: 1000)

### Semaphore Leak Crashes (FIXED October 2024)

**Symptom:** Indexing crashes after ~150-200 PDFs with:
```
resource_tracker: There appear to be 1 leaked semaphore objects to clean up at shutdown
```

**Root Causes:**
1. BoundedSemaphore callback-based approach unreliable with C++ exceptions from pypdfium2
2. Docling's DocumentConverter/HybridChunker are NOT thread-safe (GitHub issue #2285)
3. Shared parser instances across threads caused race conditions

**Solution (Commit 0469a62):**
- Replaced BoundedThreadPoolExecutor with standard ThreadPoolExecutor + as_completed()
- Create fresh DoclingParser instance for EACH PDF (thread isolation)
- Wrap parsing in try/finally for guaranteed resource cleanup
- **Result:** Zero semaphore leaks, 100% crash elimination, 8% faster (476 PDFs/hour)
- **Semaphore leaks:** Fixed by BoundedThreadPoolExecutor with batch processing

**Performance benchmarks (M1 Pro, 8 workers):**
- **CPU-only:** ~35 seconds per PDF average (optimal for parallel processing)
- **GPU (MPS):** ~254 seconds per PDF (memory contention with 8 workers)
- **Expected rate:** ~100 PDFs/hour, ~33 hours for 3,425 papers

### Environment Variables

CLI loads env vars from:
1. Shell environment
2. `~/.config/agent-zot/config.json` → `client_env`
3. Claude Desktop config (if present)

Use `ZOTERO_NO_CLAUDE=true` to disable Claude Desktop detection.

## Future Enhancements

### Granite VLM Fallback (TODO)

**Current Status**: V2-only parsing (fast, born-digital PDFs)

**Future Enhancement**: Add Granite VLM as intelligent fallback for scanned/complex PDFs

**Benefits:**
- IBM Granite 3.0 Vision multimodal LLM
- Complete document understanding (text, layout, tables, equations, code)
- MLX acceleration for Apple Silicon (M1/M2/M3)
- Better than EasyOCR for complex layouts

**Implementation:**
1. Enable `granite_fallback_enabled: true` in config
2. Install Granite dependencies: `pip install docling[vlm]`
3. Configure fallback threshold (default: 100 chars)
4. Strategy: V2 backend → Granite VLM (if <100 chars) → Skip (no OCR)

**Trade-offs:**
- Adds 2-5x slower processing for difficult PDFs (~10% of library)
- Requires ~3-8GB model download
- More RAM usage during inference
- Net impact: ~12-15 hours total vs 10-12 hours V2-only

**When to enable:**
- After initial bulk indexing completes
- If you find PDFs with poor text extraction
- For scanned journal articles (pre-2000s)
- For complex multi-column layouts with figures

See `src/agent_zot/parsers/docling.py` for implementation details.

## Active Pipeline Reference

**This section documents the complete execution path for Agent-Zot's production indexing pipeline.**

When you run `agent-zot update-db --force-rebuild --fulltext`, here's exactly which files, directories, and code paths are active:

### Entry Point

**File**: `src/agent_zot/core/cli.py`
- **Function**: `update_db()` (lines ~150-180)
- **Purpose**: CLI command handler
- **Action**: Parses flags (`--force-rebuild`, `--fulltext`) and calls semantic search

### Configuration Loading

**Files**:
1. `~/.config/agent-zot/config.json` - User overrides (ACTIVE, required)
2. `src/agent_zot/search/semantic.py` - Code with fallback defaults (ACTIVE)
3. `docs/guides/configuration.md` - Documentation only (NOT executed)

**Critical settings in config.json** (these override code defaults):
```json
{
  "client_env": {
    "ZOTERO_LOCAL": "true"
  },
  "semantic_search": {
    "embedding_model": "sentence-transformers",
    "sentence_transformer_model": "BAAI/bge-m3",
    "collection_name": "zotero_library_qdrant",
    "qdrant_url": "http://localhost:6333"
  }
}
```

All other settings use smart defaults from code (see below).

### Orchestration Layer

**File**: `src/agent_zot/search/semantic.py`
- **Class**: `SemanticSearch` (lines 1-600+)
- **Method**: `update_database()` (lines ~120-200)
- **Purpose**: Routes to local or API mode based on `ZOTERO_LOCAL` setting

**Routing logic** (lines 320-321):
```python
if extract_fulltext and is_local_mode():
    return self._get_items_from_local_db(limit, extract_fulltext=extract_fulltext)
```

For fulltext indexing with local mode (our standard production pipeline), execution routes to `local_zotero.py`.

### Local Database Access (ACTIVE PATH)

**File**: `src/agent_zot/database/local_zotero.py`
- **Function**: `_get_items_from_local_db()` (lines 100-400)
- **Purpose**: Direct SQLite access + parallel PDF parsing
- **Why this path**: 10x faster than API, no rate limits, has correct defaults

**Critical defaults** (lines 265-272, subprocess code generation):
```python
parser = DoclingParser(
    tokenizer="{parser_config.get("tokenizer", "BAAI/bge-m3")}",  # ✅ Correct
    max_tokens={parser_config.get("max_tokens", 512)},            # ✅ Correct
    merge_peers={parser_config.get("merge_peers", True)},         # ✅ Correct
    num_threads={parser_config.get("num_threads", 2)},            # ✅ Correct
    do_formula_enrichment={parser_config.get("do_formula_enrichment", False)},  # ✅ Correct
    do_table_structure={parser_config.get("parse_tables", False)},              # ✅ Correct
    enable_ocr_fallback={ocr_config.get("fallback_enabled", False)},           # ✅ Correct
    ocr_min_text_threshold={ocr_config.get("min_text_threshold", 100)}         # ✅ Correct
)
```

**Performance settings** (lines 200-250):
- Workers: `8` (parallel PDF processing)
- Batch size: `200` items
- Subprocess timeout: `3600` seconds (1 hour)

### PDF Parsing (ACTIVE, subprocess-isolated)

**File**: `src/agent_zot/parsers/docling.py`
- **Class**: `DoclingParser` (lines 1-300+)
- **Backend**: `DoclingParseV2DocumentBackend` (pypdfium2-based)
- **Method**: `parse_pdf()` (lines ~150-250)
- **Execution context**: Runs in isolated subprocess (spawned by `local_zotero.py`)

**HybridChunker settings** (lines 50-80):
- Tokenizer: `BAAI/bge-m3` (aligned with embedding model)
- Max tokens: `512` per chunk
- Merge peers: `True`
- Device: `cpu` (avoids MPS memory exhaustion)

**Why subprocess isolation**: pypdfium2 C++ crashes bypass Python exception handling. Subprocess isolation prevents these crashes from killing the main indexing process.

### Embedding Generation (ACTIVE)

**File**: `src/agent_zot/clients/qdrant.py`
- **Class**: `QdrantClientWrapper` (lines 1-1200+)
- **Method**: `_get_embedding_function()` (lines ~900-1000)
- **Purpose**: Generate BGE-M3 embeddings for chunks

**Critical settings** (lines 945-960):
```python
sentence_transformer_model = config.get("sentence_transformer_model", "all-MiniLM-L6-v2")  # Overridden by config.json
embedding_batch_size = config.get("embedding_batch_size", 32)  # GPU batch size
device = "mps"  # GPU-accelerated (sequential, no contention)
```

**Embedding dimensions**:
- BGE-M3: 1024D dense + BM25 sparse (10,000 features)
- Stored with INT8 quantization (75% RAM savings)

### Vector Storage (ACTIVE)

**File**: `src/agent_zot/clients/qdrant.py`
- **Method**: `upsert()` (lines ~400-600)
- **Purpose**: Batch insert vectors into Qdrant
- **Batch size**: `500` points (5x faster than default)

**Physical storage**: `~/toolboxes/agent-zot/qdrant_storage/`
- Managed by Docker container `agent-zot-qdrant`
- Collection: `zotero_library_qdrant`
- Structure: HNSW index with INT8 quantization

### Data Structures

**Active Qdrant collection schema**:
```json
{
  "vectors": {
    "dense": {
      "size": 1024,
      "distance": "Cosine",
      "quantization": "int8"
    },
    "sparse": {
      "size": 10000,
      "distance": "BM25"
    }
  },
  "hnsw_config": {
    "m": 32,
    "ef_construct": 200
  }
}
```

**Payload fields** (stored with each vector):
- `document`: Full text of chunk
- `item_key`: Zotero item ID
- `title`: Paper title
- `creators`: Authors
- `year`: Publication year
- `item_type`: Document type
- `doc_type`: "chunk" (for full-text) or "metadata" (for title/abstract)
- `is_chunk`: Boolean flag
- `chunk_metadata`: Headings, page numbers, hierarchy

### Files NOT in Active Path

These files exist in the codebase but are NOT used for fulltext indexing with local mode:

❌ `src/agent_zot/parsers/pymupdf_parser.py` - Deprecated, slower, less accurate
❌ `src/agent_zot/clients/chroma_client.py` - Deprecated, replaced by Qdrant
❌ `src/agent_zot/clients/better_bibtex.py` - Optional, not required for indexing
❌ `config_examples/config_chroma.json` - Old ChromaDB config template

**Why semantic.py defaults don't matter for fulltext**: The `semantic.py` initialization (lines 77-87) creates a DoclingParser instance, but this instance is NOT used when `ZOTERO_LOCAL=true` and `extract_fulltext=true`. Instead, execution routes to `local_zotero.py` which spawns fresh DoclingParser instances in subprocesses with correct defaults.

### Complete Execution Flow

**From command to indexed vectors:**

1. `agent-zot update-db --force-rebuild --fulltext` (CLI)
   ↓
2. `cli.py:update_db()` parses flags
   ↓
3. `semantic.py:update_database()` checks mode
   ↓
4. Routes to `local_zotero.py:_get_items_from_local_db()` (ACTIVE PATH)
   ↓
5. Reads Zotero SQLite: `~/Zotero/zotero.sqlite`
   ↓
6. Spawns 8 parallel workers with ThreadPoolExecutor
   ↓
7. Each worker spawns subprocess with `docling.py:parse_pdf()`
   ↓
8. HybridChunker creates 512-token chunks (BAAI/bge-m3 tokenizer)
   ↓
9. Returns chunks to main process
   ↓
10. `qdrant.py` generates BGE-M3 embeddings (GPU batch_size=32)
    ↓
11. `qdrant.py:upsert()` stores vectors in Qdrant (batch_size=500)
    ↓
12. Physical storage: `~/toolboxes/agent-zot/qdrant_storage/collections/zotero_library_qdrant/`

### Verification Points

**How to verify each stage is working correctly:**

1. **Config loaded correctly**:
   ```bash
   grep -E "(embedding_model|sentence_transformer)" ~/.config/agent-zot/config.json
   ```

2. **BGE-M3 model loading**:
   ```bash
   tail -f /tmp/agent-zot-bge-m3-reindex.log | grep "Load pretrained"
   # Should show: "Load pretrained SentenceTransformer: BAAI/bge-m3"
   ```

3. **1024D vectors confirmed**:
   ```bash
   tail -f /tmp/agent-zot-bge-m3-reindex.log | grep "dimension"
   # Should show: "dimension: 1024"
   ```

4. **Correct tokenizer in chunks**:
   ```bash
   tail -f /tmp/agent-zot-bge-m3-reindex.log | grep "HybridChunker config"
   # Should show: "tokenizer=BAAI/bge-m3" (NOT "all-MiniLM-L6-v2")
   ```

5. **Subprocess isolation active**:
   ```bash
   tail -f /tmp/agent-zot-bge-m3-reindex.log | grep "Docling parsing"
   # Should show: "Docling parsing paper.pdf (timeout: 60min)"
   ```

6. **Collection exists in Qdrant**:
   ```bash
   curl -s http://localhost:6333/collections/zotero_library_qdrant | jq '.result.vectors_count'
   ```

7. **Physical storage**:
   ```bash
   du -sh ~/toolboxes/agent-zot/qdrant_storage/collections/zotero_library_qdrant/
   ```

### Quick Reference: What Needs Configuration

**Minimal config.json for production pipeline:**
```json
{
  "client_env": {
    "ZOTERO_LOCAL": "true"
  },
  "semantic_search": {
    "embedding_model": "sentence-transformers",
    "sentence_transformer_model": "BAAI/bge-m3",
    "collection_name": "zotero_library_qdrant",
    "qdrant_url": "http://localhost:6333"
  }
}
```

**Everything else uses hardcoded defaults from `local_zotero.py` (lines 240-272).**

### Directory Structure (Active Only)

**What's actually used during indexing:**

```
~/toolboxes/agent-zot/
├── src/agent_zot/
│   ├── core/
│   │   └── cli.py                    # ✅ CLI entry point
│   ├── search/
│   │   └── semantic.py               # ✅ Orchestration (routing only)
│   ├── database/
│   │   └── local_zotero.py           # ✅ MAIN ACTIVE PATH for fulltext
│   ├── parsers/
│   │   └── docling.py                # ✅ PDF parsing in subprocess
│   ├── clients/
│   │   ├── qdrant.py                 # ✅ Vector storage
│   │   └── zotero.py                 # ✅ Zotero API wrapper
│   └── parsers/
│       └── pymupdf_parser.py         # ❌ NOT USED

~/.config/agent-zot/
└── config.json                       # ✅ User overrides (required!)

~/toolboxes/agent-zot/
└── qdrant_storage/                   # ✅ Vector data storage
    └── collections/
        └── zotero_library_qdrant/    # ✅ Active collection
            └── 0/segments/           # ✅ HNSW segments

~/Zotero/
└── zotero.sqlite                     # ✅ Source data

/tmp/
└── agent-zot-bge-m3-reindex.log      # ✅ Live indexing log
```

### Common Confusion Points

**Q: Why are there two paths (`semantic.py` and `local_zotero.py`)?**
A: `semantic.py` handles both API mode and local mode. For fulltext + local mode, it delegates to `local_zotero.py` which has optimized parallel processing and correct defaults.

**Q: Why does `semantic.py` have wrong defaults if it's not used?**
A: Those defaults only matter for API mode or metadata-only indexing. Fulltext + local mode bypasses that code path entirely.

**Q: How do I know which defaults are active?**
A: Check the log file. It shows exactly which tokenizer, dimension, and settings are used at runtime.

**Q: Can I remove unused files like `pymupdf_parser.py`?**
A: Yes, but keep them for now in case you need to test alternative parsers. They don't interfere with the active pipeline.

**Q: What if I want to change chunking parameters?**
A: Edit `config.json` → `semantic_search.docling` section. The values from config.json override the hardcoded defaults in `local_zotero.py:265-272`.

---

**For complete configuration details, see [CONFIGURATION.md](./CONFIGURATION.md).**