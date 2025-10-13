# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚠️ CRITICAL: Monitoring Long-Running Indexing Jobs

**NEVER trust log files alone. ALWAYS verify with multiple sources.**

When checking indexing status, you MUST follow this protocol:

### 1. Find the Active Log (NEVER assume)
```bash
# Get most recently modified log file
ls -lt /tmp/*.log | head -1

# Multiple log files may exist from old runs - they can mislead you!
```

### 2. Verify with Qdrant (Ground Truth)
```bash
# Check actual point count in Qdrant
curl -s http://localhost:6333/collections/zotero_library_qdrant | \
  python3 -c "import sys, json; data = json.load(sys.stdin); print(f\"Points: {data['result']['points_count']:,}\")"
```

### 3. Check Process Status
```bash
# Verify process is actually running and not stuck
ps aux | grep "agent-zot update-db" | grep -v grep
# Look for: CPU usage (should be 10-15%), process state (should not be 'S' for sleeping)
```

### 4. Cross-Reference All Three
- **Log shows progress** + **Qdrant count increasing** + **Process active** = ✅ Running correctly
- **Log stopped** + **Qdrant count static** + **Process sleeping** = ❌ Stuck/frozen
- **Log active** but **Qdrant count not matching** = ⚠️ Wrong log file

### Quick Status Script
```bash
/tmp/check-indexing-status.sh
# This script checks all sources automatically
```

### Reference File
```bash
cat /tmp/ACTIVE_INDEXING_LOG.txt
# Always check this file first to know which log is active
```

### 5. Understanding Pipeline Stages (CRITICAL)

**The log does NOT show clear "Stage 1 Complete, Stage 2 Started" messages. You MUST search backwards through the log to understand what stage the pipeline is in.**

**Pipeline has 2 sequential stages:**
1. **Stage 1: PDF Parsing** (8-10 hours) - Extract text and chunks from ALL PDFs
2. **Stage 2: Embedding & Upload** (1-2 hours) - Generate vectors and upload to Qdrant

**To determine current stage, search the log backwards:**

```bash
# Find parsing completion
grep -E "(Extracted content for|Batch.*complete)" /tmp/agent-zot-production-index.log | tail -20

# Look for these markers:
# - "Extracted content for 3425/3426 items" = parsing progress
# - "Batch 3400-3426 complete, garbage collected" = parsing FINISHED
# - "add_documents called with XXXX documents" = embedding STARTED
# - "Processing batch X/Y (500 docs)" = embedding in progress
# - "Uploaded batch X" = uploading to Qdrant
```

**Example analysis:**
```
2025-10-11 22:28:25 - INFO - Batch 3400-3426 complete, garbage collected  ← PARSING FINISHED
...
2025-10-12 03:14:14 - INFO - add_documents called with 3238 documents     ← EMBEDDING STARTED
2025-10-12 03:20:32 - INFO - Processing batch 5/7 (500 docs)              ← EMBEDDING IN PROGRESS
```

**This means:**
- ✅ Stage 1 (Parsing): 100% complete (finished at 22:28 on Oct 11)
- 🔄 Stage 2 (Embedding): 71% complete (batch 5 of 7)
- ⏱️ Expected completion: ~30 minutes (2 batches remaining × ~2 min/batch)

**Why this matters:** The log only shows "Processing batch 5/7" without context. Without searching backwards, you cannot tell if this is batch 5 of parsing or batch 5 of embedding. You MUST search to find the "Batch complete, garbage collected" message that marks the transition between stages.

**Why this matters:** Multiple indexing runs create multiple log files. If you check the wrong log (e.g., one from a stuck/old run), you'll report incorrect progress. The user will catch your mistake and lose trust. ALWAYS verify with Qdrant's live data.

### 6. Generating Complete Status Reports

**When the user asks for a "status report" or "progress update", generate a comprehensive report using this exact template and data collection process:**

#### Data Collection Commands (run in sequence):

```bash
# 1. Check reference file for active log location
cat /tmp/ACTIVE_INDEXING_LOG.txt

# 2. Find parsing completion
grep -E "(Extracted content for|Batch.*complete)" /tmp/agent-zot-production-index.log | tail -5

# 3. Find current embedding stage
tail -100 /tmp/agent-zot-production-index.log | grep -E "(add_documents|Processing batch|Uploaded batch)" | tail -10

# 4. Check Qdrant point count (ground truth)
curl -s http://localhost:6333/collections/zotero_library_qdrant | python3 -c "import sys, json; data = json.load(sys.stdin); print(f\"Points: {data['result']['points_count']:,}\")"

# 5. Verify process is running
ps aux | grep "agent-zot update-db" | grep -v grep
```

#### Report Template Structure:

**ALWAYS use this exact structure:**

```markdown
# 📊 COMPLETE INDEXING PIPELINE STATUS REPORT
**Generated:** [current date/time]
**Runtime:** [hours since start from ACTIVE_INDEXING_LOG.txt]

---

## ✅ STAGE 1: PDF PARSING & TEXT EXTRACTION
**Status:** [100% COMPLETE or X% IN PROGRESS]

### Papers Processed
- **Total papers:** X papers
- **Parsed:** X / X (XX.XX%)
- **Completion time:** [timestamp from log]

### Technical Details
- **Parser:** Docling V2 (pypdfium2 backend) with HybridChunker
- **Tokenizer:** BAAI/bge-m3 (aligned with embedding model)
- **Chunk size:** 512 tokens per chunk
- **Workers:** 8 parallel workers (M1 Pro optimization)
- **Subprocess isolation:** Enabled (prevents crashes)
- **OCR:** Disabled (born-digital PDFs only)

### Output
- **Chunks generated:** ~X document chunks extracted
- **Storage:** In-memory (passed to embedding stage)

---

## 🔄 STAGE 2: EMBEDDING & VECTOR UPLOAD
**Status:** [X% COMPLETE] (X of Y batches done)

### Current Progress
- **Embedding batch:** X / Y (processing batch X now)
- **Chunks embedded:** X / Y (XX%)
- **Uploaded to Qdrant:** X points (includes metadata entries)
- **Batch size:** 500 docs per batch

### Technical Details
- **Model:** BAAI/bge-m3 (1024 dimensions)
- **Device:** MPS GPU (Apple Silicon acceleration)
- **Vector types:** Dense (1024D) + Sparse (BM25, 10K features)
- **Quantization:** INT8 (75% memory savings)
- **Upload batch size:** 500 points

### Timeline
- **Started:** [timestamp from log]
- **Current:** Processing batch X/Y
- **Expected completion:** [calculate based on remaining batches × 2 min/batch]

---

## ⏸️ STAGE 3: NEO4J KNOWLEDGE GRAPH
**Status:** [NOT STARTED or COMPLETE]

[Include configuration status and details]

---

## 📈 OVERALL COMPLETION

### Pipeline Progress
```
Stage 1 (Parsing):    [ASCII progress bar] XX% ✅/🔄
Stage 2 (Embedding):  [ASCII progress bar] XX% 🔄/⏸️
Stage 3 (Neo4j):      [ASCII progress bar] XX% ⏸️
─────────────────────────────────────────────
TOTAL:                [ASCII progress bar] XX% complete
```

### Time Analysis
- **Total runtime:** X hours
  - Parsing: Xh Xm (XX%)
  - Wait time: Xh (gap between stages)
  - Embedding: Xm (X% of runtime so far)
- **Estimated completion:** [calculation]

---

## 🔍 VERIFICATION DATA

### Log File
- **Active log:** [path] (X MB)
- **Last update:** [X minutes ago]
- **Old logs:** [archived count]

### Process Status
- **PID:** [from ps output]
- **CPU usage:** [from ps output]
- **Memory:** [from ps output]
- **State:** [from ps output + interpretation]

### Qdrant Database
- **Collection:** zotero_library_qdrant
- **Points stored:** [from Qdrant API]
- **URL:** http://localhost:6333
- **Storage:** ~/toolboxes/agent-zot/qdrant_storage/

---

## 📝 CONFIGURATION SUMMARY
[Include embedding model, parser config, vector DB settings]

---

## 🎯 WHAT'S LEFT
[Enumerate remaining tasks with checkboxes]

---

## 🔬 FINAL STATS (Projected)
[Project final numbers after completion]
```

#### Calculation Rules:

1. **Parsing percentage:** (Extracted count / Total papers) × 100
2. **Embedding percentage:** (Current batch / Total batches) × 100
3. **Overall percentage:**
   - If parsing incomplete: (Parsing % × 0.9)
   - If embedding incomplete: 90 + (Embedding % × 0.1)
   - If both complete: 100%

4. **Time remaining:** (Batches remaining) × 2 minutes per batch

5. **ASCII progress bars:** Use 20 characters, filled = ████, empty = ░░░░

#### Critical Requirements:

- ✅ **ALWAYS verify data with all 5 commands** - never assume or use cached data
- ✅ **Include timestamps** from actual log entries, not estimates
- ✅ **Show both chunk counts AND point counts** - they may differ (metadata entries)
- ✅ **Calculate percentages** - don't just show raw numbers
- ✅ **Estimate completion time** - based on observed batch timing
- ✅ **Use emojis consistently** - ✅ (complete), 🔄 (in progress), ⏸️ (not started)

#### Common Pitfalls to Avoid:

❌ **DON'T** report progress based on Qdrant count alone (includes metadata)
❌ **DON'T** assume parsing finished without checking log for "Batch complete"
❌ **DON'T** forget to search backwards for stage transitions
❌ **DON'T** use old/cached data - always fetch fresh data
❌ **DON'T** skip the verification section - process status is critical

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
source ~/toolboxes/agent-zot/.venv/bin/activate

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

**Purpose**: Extract knowledge graphs from research papers for relationship-aware search and discovery.

#### Core Components

1. **Client**: `src/agent_zot/clients/neo4j_graphrag.py`
   - Config-driven schema (8 entity types, 12 relationship types)
   - Free local LLM support via Ollama (Mistral 7B Instruct)
   - Free local embeddings via SentenceTransformer (BGE-M3)
   - OpenAI support (GPT-4o-mini + text-embedding-3-large)

2. **Population Script**: `populate_neo4j_from_qdrant.py`
   - Read-only Qdrant access (never modifies vector DB)
   - Concurrent processing with asyncio (default: 4 parallel tasks)
   - 6-9x performance improvement (73 hours → 10-12 hours for 2,411 papers)
   - CLI flags: `--dry-run`, `--limit`, `--concurrency`

#### Config-Driven Schema

**Entity types** (configurable via `config.json`):
1. **Person** - Authors, researchers, historical figures
2. **Institution** - Universities, research labs, companies
3. **Concept** - Abstract ideas, frameworks, paradigms
4. **Method** - Techniques, algorithms, approaches
5. **Dataset** - Benchmark datasets, corpora, collections
6. **Theory** - Theoretical frameworks, models, hypotheses
7. **Journal** - Publication venues, academic journals
8. **Field** - Academic disciplines, research areas

**Relationship types** (configurable via `config.json`):
1. **AUTHORED_BY** - Paper → Person
2. **AFFILIATED_WITH** - Person → Institution
3. **USES_METHOD** - Paper/Study → Method
4. **USES_DATASET** - Paper/Study → Dataset
5. **APPLIES_THEORY** - Paper/Study → Theory
6. **DISCUSSES_CONCEPT** - Paper → Concept
7. **BUILDS_ON** - Paper → Paper
8. **EXTENDS** - Work → Prior Work
9. **RELATED_TO** - Generic relationship
10. **CITES** - Paper → Paper
11. **PUBLISHED_IN** - Paper → Journal
12. **BELONGS_TO_FIELD** - Paper/Concept → Field

#### Requirements

- **Neo4j Version**: 5.23.0+ with APOC plugin (for relationship vector support)
- **Docker Command**:
  ```bash
  docker run -d -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/demodemo \
    -e NEO4J_PLUGINS='["apoc"]' \
    --name agent-zot-neo4j \
    neo4j:5.23.0
  ```

#### Configuration

**Config location**: `~/.config/agent-zot/config.json` → `neo4j_graphrag`

```json
{
  "neo4j_graphrag": {
    "enabled": true,
    "neo4j_uri": "neo4j://127.0.0.1:7687",
    "neo4j_user": "neo4j",
    "neo4j_password": "demodemo",
    "neo4j_database": "neo4j",
    "llm_model": "ollama/mistral:7b-instruct",
    "entity_types": [
      "Person", "Institution", "Concept", "Method",
      "Dataset", "Theory", "Journal", "Field"
    ],
    "relation_types": [
      "AUTHORED_BY", "AFFILIATED_WITH", "USES_METHOD",
      "USES_DATASET", "APPLIES_THEORY", "DISCUSSES_CONCEPT",
      "BUILDS_ON", "EXTENDS", "RELATED_TO", "CITES",
      "PUBLISHED_IN", "BELONGS_TO_FIELD"
    ]
  }
}
```

#### Free Local LLM Option

Use Ollama with Mistral 7B Instruct for zero-cost entity extraction:

```bash
# Install Ollama (macOS)
brew install ollama

# Pull Mistral 7B Instruct
ollama pull mistral:7b-instruct

# Verify it's running
ollama list

# Configure in config.json
"llm_model": "ollama/mistral:7b-instruct"
```

**Benefits**:
- Zero API costs (fully local)
- No rate limits
- Privacy-preserving (data never leaves your machine)
- Good quality (Mistral 7B competitive with GPT-3.5)

**When to use OpenAI instead**:
- Need higher accuracy (GPT-4o-mini)
- Already have OpenAI credits
- Don't want to run local LLM (8GB RAM required)

#### Free Local Embeddings

When using Ollama LLM without OpenAI API key, Neo4j automatically uses free local embeddings:

```python
# Automatically configured when llm_model starts with "ollama/" and no OpenAI key
self.embeddings = SentenceTransformerEmbeddings(model="BAAI/bge-m3")
```

**Benefits**:
- Same embeddings as Qdrant (BGE-M3) for consistency
- Zero API costs
- 1024 dimensions (vs OpenAI's 3072)
- Multilingual support

#### Population Script Usage

After initial Qdrant indexing, populate Neo4j graph:

```bash
# Dry run (test without writing to Neo4j)
python populate_neo4j_from_qdrant.py --dry-run

# Process first 5 items (testing)
python populate_neo4j_from_qdrant.py --limit 5

# Full population with default concurrency (4 parallel tasks)
python populate_neo4j_from_qdrant.py

# High concurrency (8 parallel tasks)
python populate_neo4j_from_qdrant.py --concurrency 8

# Low concurrency (2 parallel tasks, for memory-constrained systems)
python populate_neo4j_from_qdrant.py --concurrency 2
```

#### Performance

**Concurrent processing** (new):
- Default: 4 parallel tasks
- Performance: 6-9x faster than sequential
- Example: 2,411 papers in 10-12 hours (vs 73 hours sequential)

**Read-only Qdrant access**:
- Script NEVER modifies vector database
- Safe to run alongside semantic search
- Reconstructs fulltext from Qdrant chunks

#### Advanced Features

| Feature | Status | Description |
|---------|--------|-------------|
| **Entity Resolution** | ✅ Enabled | Merges similar entities (e.g., "Stanford" = "Stanford University") |
| **Lexical Graph** | ✅ Enabled | Keyword connections for full-text search |
| **Custom Extraction Prompt** | ✅ Active | Optimized for research papers |
| **Database Indexes** | ✅ Created | 10-100x faster queries |
| **Vector Embeddings** | ✅ Supported | Requires Neo4j 5.23.0+ with APOC |

#### Graph Schema

**Optimized for research paper queries**:
- Author collaboration networks
- Methodological lineages
- Conceptual relationships
- Citation graphs
- Institution affiliations

#### Verification

```bash
# Check Neo4j status
docker logs agent-zot-neo4j

# Access Neo4j browser
open http://localhost:7474
# Login: neo4j / demodemo

# Check graph statistics
curl -X POST http://localhost:7474/db/neo4j/tx/commit \
  -H "Authorization: Basic bmVvNGo6ZGVtb2RlbW8=" \
  -H "Content-Type: application/json" \
  -d '{"statements":[{"statement":"MATCH (n) RETURN labels(n) as type, count(n) as count"}]}'
```

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

### zot_advanced_search - Complex Boolean Search (NOT RECOMMENDED)

**Current Status**: Disabled due to architectural concerns

**Location**: `src/agent_zot/core/server.py:1211` (commented out)

**Known Issues:**
- Uses Zotero's saved search API as a workaround (creates temp search, executes, deletes)
- Has unsafe dict access bug: `saved_search.get("success", {}).values()` fails if `success` is `None`
- Fragile dependency on pyzotero's saved search implementation

**Why NOT Recommended:**
- Unclear value proposition - when would boolean search beat semantic search?
- Better alternatives already exist:
  - `zot_semantic_search` - Far more powerful for research queries
  - `zot_search_by_tag` - Advanced tag operators (||, -, AND logic)
  - `zot_search_items` - Simple exact matching
  - `zot_graph_search` - Relationship-based queries
- Maintenance burden: Complex code for marginal benefit
- Architectural smell: Temp object creation/deletion pattern

**If You Really Want It:**

The bug fix is simple:
```python
# Old (broken):
search_key = next(iter(saved_search.get("success", {}).values()), None)

# Fixed:
success_dict = saved_search.get("success") or {}
search_key = next(iter(success_dict.values()), None) if success_dict else None
```

But fixing the bug doesn't address the fundamental issues above.

**Decision**: Left disabled. If you need complex queries, use semantic search or the Zotero UI.

---

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

## Future Code Quality Improvements

**Status: Non-Critical** - Production-ready as-is. These are quality-of-life improvements for future consideration.

### Audit Warnings (Medium Priority)

Comprehensive audit completed 2025-10-13. See `AUDIT_REPORT.md` for details.

**✅ Critical Issues: RESOLVED**
- Commit 84e406a: Fixed 3 critical IndexError/KeyError bugs in MCP tools
- Commit 2dedd9c: Disabled broken `zot_advanced_search`, corrected `zot_find_seminal_papers` description
- 2 false positives confirmed safe

**⚠️ Warnings: DEFERRED** (13 total)

Consider addressing if planning multi-user deployment or untrusted input:

1. **Edge Case Handling** (Low risk in production)
   - `zot_get_tags` (line 683): Empty string check `tag[0]` when `tag=""`
   - Already guarded by `if tag`, only fails on empty string (rare)

2. **Input Validation** (UX improvements)
   - `zot_get_recent` (line 723): Add user feedback when limit capped
   - `zot_update_search_database` (line 1861): Range validation after type coercion
   - Currently silent capping/coercion works but less helpful

3. **Security Hardening** (For production/multi-user)
   - `zot_get_item_fulltext` (line 358): Path traversal protection for `file_path`
   - `zot_create_note` (line 1658): HTML sanitization (use `bleach` library)
   - `zot_export_markdown` (line 2792): Enhanced filename sanitization
   - Currently low risk with trusted local Zotero data

4. **Code Refactoring** (Medium risk, medium priority)
   - `zot_search_notes` (lines 1519-1535): Fragile markdown parsing
   - Parses markdown strings from `get_annotations()` output
   - Risk: Will break if output format changes
   - Mitigation: Both tools in same codebase, format controlled internally
   - **When to fix**: During broader refactoring with test coverage, or if format changes

**Recommendation**: Address security hardening (#3) before exposing to untrusted users or remote access. Address refactoring (#4) when doing broader code quality improvements.

---

**For complete configuration details, see [CONFIGURATION.md](./CONFIGURATION.md).**