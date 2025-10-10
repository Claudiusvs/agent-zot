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
All CLI commands use the `zotero-mcp` entry point:

```bash
# Show version
zotero-mcp version

# Interactive setup
zotero-mcp setup

# Show installation and config info
zotero-mcp setup-info

# Update semantic search database
zotero-mcp update-db --force-rebuild --extract-fulltext

# Check database status
zotero-mcp db-status

# Inspect indexed documents
zotero-mcp db-inspect --key ITEM_KEY

# Run MCP server
zotero-mcp serve
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
source ~/toolboxes/zotero-mcp-env/bin/activate

# Install in development mode
pip install -e .

# Run tests (for new parsers)
python test_pymupdf.py
```

## Architecture

### Core Components

1. **server.py** - FastMCP server with 20+ tools for Zotero interaction
2. **semantic_search.py** - Orchestrates semantic search with Qdrant, Docling, and Neo4j
3. **qdrant_client_wrapper.py** - Qdrant vector database client with hybrid search (dense + BM25 sparse)
4. **docling_parser.py** - Advanced PDF parsing using Docling's HybridChunker
5. **neo4j_graphrag_client.py** - Knowledge graph extraction from research papers
6. **client.py** - Zotero API wrapper (pyzotero)
7. **local_db.py** - Direct SQLite access to local Zotero database for faster indexing
8. **cli.py** - Command-line interface entry points

### Data Flow

**Indexing Pipeline:**
1. Zotero items fetched via API or local SQLite database (local_db.py)
2. PDF attachments parsed with Docling V2 backend → hierarchical chunks with metadata (docling_parser.py)
   - 8 parallel workers, CPU-only processing, ~7-8 seconds per PDF average (476 PDFs/hour)
   - Standard ThreadPoolExecutor with as_completed() for natural backpressure (no semaphore leaks)
   - Fresh DoclingParser instance per PDF for thread safety
   - Batch processing (200 items/batch) with automatic deduplication
3. Chunks embedded via BGE-M3 model (sentence-transformers, 1024D, GPU-accelerated with batch_size=32)
4. Dense + sparse (BM25) vectors stored in Qdrant (batch_size=500 for optimal throughput)
5. [Optional] Neo4j knowledge graph extraction (neo4j_graphrag_client.py, GPT-4o-mini)

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

See server.py for full tool definitions and parameters.

## Configuration

### Main Config File
`~/.config/zotero-mcp/config.json` contains all settings:

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
- **Old ChromaDB:** `~/.config/zotero-mcp/chroma_db/` (deprecated, can be removed)

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
zotero-mcp update-db --force-rebuild --extract-fulltext --limit 10
```

Check results:
```bash
zotero-mcp db-status
zotero-mcp db-inspect --key ITEM_KEY
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

Use `zotero-mcp setup-info` to generate correct config snippet.

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
2. `~/.config/zotero-mcp/config.json` → `client_env`
3. Claude Desktop config (if present)

Use `ZOTERO_NO_CLAUDE=true` to disable Claude Desktop detection.

## Future Improvements

### TODO: Migrate to Proper Virtual Environment Setup

**Context**: Currently using external virtual environments (`~/toolboxes/zotero-mcp-env/` or `~/toolboxes/agent-zot-env/`) instead of following Python best practices with an in-project virtual environment.

**Action Items** (after current indexing completes):

1. **Create proper virtual environment inside project:**
   ```bash
   cd ~/toolboxes/agent-zot
   python3.12 -m venv .venv
   ```

2. **Install package in editable mode:**
   ```bash
   source .venv/bin/activate
   pip install -e .
   ```

3. **Update documentation:**
   - Change all `source ~/toolboxes/zotero-mcp-env/bin/activate` → `source .venv/bin/activate`
   - Update README.md installation instructions
   - Update this CLAUDE.md file (Development Setup section)

4. **Verify .gitignore:**
   - Already configured to ignore `venv/`, `env/`, `*.venv` (lines 12-14)
   - The `.venv/` directory will be automatically ignored

5. **Clean up old virtual environments:**
   ```bash
   rm -rf ~/toolboxes/zotero-mcp-env
   rm -rf ~/toolboxes/agent-zot-env
   ```

**Why This Matters:**
- **Convention**: Standard Python practice is virtual environment inside project directory
- **Portability**: Anyone cloning the repo expects `source .venv/bin/activate`
- **Simplicity**: Shorter activation command, no absolute paths needed
- **Clarity**: Clear separation between project code and dependencies

**Note**: Wait until current indexing pipeline completes to avoid disrupting running processes.

---

### TODO: Rename Package from "zotero-mcp" to "agent-zot"

**Context**: The project is forked from zotero-mcp but has diverged significantly. The directory is already named `agent-zot`, but the Python package and CLI still use `zotero-mcp` internally.

**Safe Migration Steps** (after any long-running processes complete):

1. **Update setup.py**:
   - Change `name="zotero-mcp"` → `name="agent-zot"`
   - Change entry point: `'zotero-mcp=cli:main'` → `'agent-zot=cli:main'`

2. **Reinstall package**:
   ```bash
   pip uninstall zotero-mcp
   pip install -e .
   ```

3. **Update documentation**:
   - Replace all `zotero-mcp` command references with `agent-zot`
   - Update this CLAUDE.md file

4. **Update Claude Desktop config**:
   - Change `"command": "zotero-mcp"` → `"command": "agent-zot"`
   - Location: `~/Library/Application Support/Claude/claude_desktop_config.json`

5. **Update config directory** (optional):
   - Consider migrating `~/.config/zotero-mcp/` → `~/.config/agent-zot/`
   - Update config path references in code

**Impact**: CLI command changes from `zotero-mcp` to `agent-zot`. No impact on Qdrant database, config file, or running processes.

**Note**: Wait until any long-running indexing processes complete before renaming to avoid confusion.
