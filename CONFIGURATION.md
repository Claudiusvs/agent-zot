# Agent-Zot Configuration Reference

**This document describes the standard default production pipeline configuration for Agent-Zot.**

Last updated: October 2025 (Subprocess isolation release)

---

## Table of Contents

- [System Requirements](#system-requirements)
- [Docling PDF Parser](#docling-pdf-parser)
- [Qdrant Vector Database](#qdrant-vector-database)
- [Neo4j GraphRAG](#neo4j-graphrag)
- [Zotero Data Source](#zotero-data-source)
- [Performance Optimizations](#performance-optimizations)
- [Critical Fixes](#critical-fixes)
- [Indexing Pipeline](#indexing-pipeline)

---

## System Requirements

### Hardware (Optimized for M1 Pro)
- **CPU**: 8+ performance cores
- **RAM**: 16GB minimum
- **GPU**: Apple M1 Pro MPS (optional, for embeddings)
- **Storage**: SSD recommended (for Qdrant persistence)

### Software
- **Docker**: Qdrant and Neo4j containers
- **Python**: 3.12+ with virtual environment
- **Zotero**: Local installation with SQLite database access

### Services
- ✅ **Qdrant**: Running on `http://localhost:6333`
- ✅ **Neo4j** (optional): Running on `neo4j://127.0.0.1:7687`
- ✅ **Zotero**: Local database at `~/Zotero/zotero.sqlite`

---

## Docling PDF Parser

**Purpose**: Advanced PDF parsing with structure preservation and hierarchical chunking.

### Backend Configuration

| Setting | Value | Description |
|---------|-------|-------------|
| **Backend** | `DoclingParseV2DocumentBackend` | 10x faster than V1, uses pypdfium2 |
| **Subprocess Isolation** | ✅ Enabled | Prevents C++ crashes from affecting main process |
| **Subprocess Timeout** | `3600` seconds (1 hour) | Handles large documents (textbooks, dissertations) |
| **Infinite Timeout** | Supported (`null`) | For extremely large documents |
| **CPU Threads** | `2` per worker | Balances performance vs memory |
| **Device** | `cpu` | Avoids MPS GPU memory exhaustion |
| **pdfminer Fallback** | ❌ Removed | Ensures consistent output quality |

**Config location**: `~/.config/zotero-mcp/config.json` → `semantic_search.docling`

```json
{
  "docling": {
    "tokenizer": "BAAI/bge-m3",
    "max_tokens": 512,
    "merge_peers": true,
    "num_threads": 2,
    "do_formula_enrichment": false,
    "parse_tables": false,
    "parse_figures": false,
    "subprocess_timeout": 3600,
    "ocr": {
      "fallback_enabled": false,
      "min_text_threshold": 100
    }
  }
}
```

### HybridChunker Configuration

| Setting | Value | Description |
|---------|-------|-------------|
| **Tokenizer** | `BAAI/bge-m3` | Aligned with embedding model |
| **Max Tokens** | `512` | Balances context vs granularity |
| **Merge Peers** | `true` | Combines undersized chunks with same metadata |
| **Delimiter** | `\n` | Preserves paragraph structure |
| **Token-Aware** | ✅ Yes | Accurate multilingual token counting |
| **Structure-Preserving** | ✅ Yes | Maintains document hierarchy |

**Chunking strategy**: Token-aware boundary detection that respects document structure (headings, paragraphs, sections).

### Parsing Features

| Feature | Status | Reason |
|---------|--------|--------|
| **Formula Enrichment** | ❌ Disabled | LaTeX→text conversion not needed for most papers |
| **Table Parsing** | ❌ Disabled | Structure extraction adds overhead, limited benefit |
| **Figure Parsing** | ❌ Disabled | Image extraction not needed for text search |
| **OCR Fallback** | ❌ Disabled | Prevents crashes, maintains consistent quality |

### Metadata Extraction

**Preserved per chunk:**
- ✅ **Headings**: Full heading hierarchy
- ✅ **Page Numbers**: Source page tracking
- ✅ **Document Structure**: Reading order maintained
- ✅ **Bounding Boxes**: Spatial coordinates (for future use)
- ✅ **Doc Items**: Self-references for content linking

### Error Handling

**Strategy**: Fail loudly with clear error codes

| Error Code | Meaning | Action |
|------------|---------|--------|
| `"failed"` | Docling parsing failed | Check PDF integrity |
| `"timeout"` | Exceeded subprocess timeout | Increase timeout or check PDF size |
| `"error"` | Subprocess setup failed | Check system resources |

**No silent degradation**: All errors are logged and reported clearly.

---

## Qdrant Vector Database

**Purpose**: Production-grade vector storage with hybrid search (dense + sparse).

### Connection Settings

| Setting | Value | Description |
|---------|-------|-------------|
| **URL** | `http://localhost:6333` | Local Docker container |
| **Collection Name** | `zotero_library_qdrant` | Main collection for Zotero items |
| **API Key** | `null` | Not needed for local Docker |

### Embedding Configuration

| Setting | Value | Description |
|---------|-------|-------------|
| **Model Type** | `sentence-transformers` | Local embedding generation |
| **Model** | `BAAI/bge-m3` | Multilingual, SOTA performance |
| **Dimension** | `1024` | BGE-M3 native dimension |
| **GPU Batch Size** | `32` chunks | Optimized for M1 Pro MPS (~2-3GB GPU memory) |
| **Device** | MPS (GPU) | GPU-accelerated embedding generation |

**Config location**: `~/.config/zotero-mcp/config.json` → `semantic_search`

```json
{
  "semantic_search": {
    "embedding_model": "sentence-transformers",
    "sentence_transformer_model": "BAAI/bge-m3",
    "collection_name": "zotero_library_qdrant",
    "qdrant_url": "http://localhost:6333",
    "qdrant_api_key": null
  }
}
```

### Dense Vector Configuration

| Setting | Value | Description |
|---------|-------|-------------|
| **Distance Metric** | Cosine similarity | Standard for semantic search |
| **Vector Size** | `1024` dimensions | BGE-M3 embeddings |
| **Quantization** | ✅ Enabled | Scalar quantization (int8) |
| **Memory Savings** | 75% | From float32 → int8 |

### Sparse Vector Configuration (BM25)

| Setting | Value | Description |
|---------|-------|-------------|
| **Hybrid Search** | ✅ Enabled | Combines dense + sparse for better recall |
| **Sparse Model** | BM25 with TF-IDF | Keyword-based retrieval |
| **Max Features** | `10,000` terms | Vocabulary size |
| **Lowercase** | ✅ Yes | Case-insensitive matching |
| **Stop Words** | English | Filters common words |
| **IDF** | ✅ Enabled | Inverse document frequency weighting |
| **Normalization** | None | BM25-style scoring |

**Config location**: `~/.config/zotero-mcp/config.json` → `semantic_search`

```json
{
  "enable_hybrid_search": true,
  "enable_quantization": true
}
```

### HNSW Index Configuration

| Setting | Value | Description |
|---------|-------|-------------|
| **M** (connections per node) | `32` | Higher = better recall (default: 16) |
| **EF Construct** | `200` | Build-time accuracy (default: 100) |
| **Indexing Threshold** | `20,000` vectors | When to start indexing |
| **Payload Threshold** | `10,000` vectors | When to optimize |

**HNSW tuning**: Optimized for high recall at the cost of slightly slower indexing. Search performance remains fast (<100ms).

```json
{
  "hnsw_m": 32,
  "hnsw_ef_construct": 200
}
```

### Search & Reranking

| Setting | Value | Description |
|---------|-------|-------------|
| **Reranking** | ✅ Enabled | Cross-encoder reranking |
| **Reranker Model** | `ms-marco-MiniLM-L-6-v2` | Fast and accurate |
| **Quality Improvement** | +10-20% | Better result ordering |
| **Fusion Method** | RRF (Reciprocal Rank Fusion) | Combines dense + sparse rankings |

```json
{
  "enable_reranking": true
}
```

### Performance Tuning

| Setting | Value | Description |
|---------|-------|-------------|
| **Batch Size** | `500` points | 5x increase reduces API overhead |
| **Write Speed** | 3-5x faster | Compared to default batch size |
| **Optimization** | Automatic | Runs after indexing completes |

```json
{
  "batch_size": 500
}
```

### Quantization Search Parameters

| Setting | Value | Description |
|---------|-------|-------------|
| **Ignore** | `false` | Uses quantized vectors for initial search |
| **Rescore** | `true` | Rescores top results with original vectors |
| **Quality** | Near-perfect | Minimal quality loss vs full precision |

---

## Neo4j GraphRAG

**Purpose**: Knowledge graph extraction for relationship-aware search.

### Connection Settings

| Setting | Value | Description |
|---------|-------|-------------|
| **Enabled** | ✅ `true` | Active by default |
| **URI** | `neo4j://127.0.0.1:7687` | Local Docker container |
| **Database** | `neo4j` | Default database |
| **User** | `neo4j` | Default username |
| **Password** | `demodemo` | Configure in Docker |
| **LLM Model** | `gpt-4o-mini` | For entity/relationship extraction |

**Config location**: `~/.config/zotero-mcp/config.json` → `neo4j_graphrag`

```json
{
  "neo4j_graphrag": {
    "enabled": true,
    "neo4j_uri": "neo4j://127.0.0.1:7687",
    "neo4j_user": "neo4j",
    "neo4j_password": "demodemo",
    "neo4j_database": "neo4j",
    "llm_model": "gpt-4o-mini"
  }
}
```

### Entity Types

**6 primary entity types** extracted from research papers:

1. **Person** - Authors, researchers, historical figures
2. **Institution** - Universities, research labs, companies
3. **Concept** - Abstract ideas, frameworks, paradigms
4. **Method** - Techniques, algorithms, approaches
5. **Dataset** - Benchmark datasets, corpora, collections
6. **Theory** - Theoretical frameworks, models, hypotheses

### Relationship Types

**10 relationship types** connecting entities:

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

```json
{
  "entity_types": [
    "Person", "Institution", "Concept",
    "Method", "Dataset", "Theory"
  ],
  "relation_types": [
    "AUTHORED_BY", "AFFILIATED_WITH", "USES_METHOD",
    "USES_DATASET", "APPLIES_THEORY", "DISCUSSES_CONCEPT",
    "BUILDS_ON", "EXTENDS", "RELATED_TO", "CITES"
  ]
}
```

### Advanced Features

| Feature | Status | Description |
|---------|--------|-------------|
| **Entity Resolution** | ✅ Enabled | Merges similar entities (e.g., "Stanford" = "Stanford University") |
| **Lexical Graph** | ✅ Enabled | Keyword connections for full-text search |
| **Custom Extraction Prompt** | ✅ Active | Optimized for research papers |
| **Database Indexes** | ✅ Created | 10-100x faster queries |

```json
{
  "perform_entity_resolution": true,
  "enable_lexical_graph": true
}
```

### Graph Schema

**Optimized for research paper queries:**
- Author collaboration networks
- Methodological lineages
- Conceptual relationships
- Citation graphs
- Institution affiliations

---

## Zotero Data Source

**Purpose**: Direct access to Zotero's SQLite database for faster indexing.

### Connection Mode

| Setting | Value | Description |
|---------|-------|-------------|
| **Local Mode** | ✅ `true` | Direct SQLite access (faster than API) |
| **Local DB Path** | Auto-detected | Usually `~/Zotero/zotero.sqlite` |
| **API Key** | Available | For remote fallback if needed |
| **Library ID** | User-specific | From Zotero settings |
| **Library Type** | `user` | Personal library |

**Config location**: `~/.config/zotero-mcp/config.json` → `client_env`

```json
{
  "client_env": {
    "ZOTERO_LOCAL": "true",
    "ZOTERO_API_KEY": "your_api_key_here",
    "ZOTERO_LIBRARY_ID": "your_library_id",
    "ZOTERO_LIBRARY_TYPE": "user"
  }
}
```

### Indexing Strategy

| Setting | Value | Description |
|---------|-------|-------------|
| **Auto Update** | ❌ `false` | Manual control (prevents unexpected rebuilds) |
| **Update Frequency** | `manual` | User-triggered only |
| **Force Rebuild** | ❌ `false` (default) | Safe incremental indexing |
| **Extract Fulltext** | ✅ `true` (default) | Uses Docling for PDF parsing |

**Config location**: `~/.config/zotero-mcp/config.json` → `semantic_search.update_config`

```json
{
  "update_config": {
    "auto_update": false,
    "update_frequency": "manual",
    "force_rebuild": false,
    "extract_fulltext": true
  }
}
```

### Deduplication

**Always-on duplicate detection** (independent of `force_rebuild` flag):

| Feature | Behavior |
|---------|----------|
| **Document Exists Check** | Always runs before indexing |
| **Preprint Filtering** | `journalArticle` preferred over `preprint` |
| **DOI Matching** | Normalized DOI comparison |
| **Title Matching** | Normalized title comparison |
| **Restart-Safe** | Can safely restart interrupted indexing |

**Implementation**: Hardcoded in `semantic_search.py` to prevent duplicate processing.

### PDF Limits

| Setting | Value | Description |
|---------|-------|-------------|
| **Max Pages** | `1000` pages | Prevents extremely long PDFs from hanging |

```json
{
  "extraction": {
    "pdf_max_pages": 1000
  }
}
```

---

## Performance Optimizations

**Optimized for M1 Pro (8 perf cores + 16GB RAM)**

### Parallel Processing

| Component | Setting | Description |
|-----------|---------|-------------|
| **PDF Workers** | `8` workers | One per performance core |
| **Threads per Worker** | `2` threads | Total 16 threads = full CPU utilization |
| **Item Batch Size** | `50` items | Balances memory vs throughput |
| **Qdrant Batch Size** | `500` points | 5x faster writes |
| **GPU Embedding Batch** | `32` chunks | Optimizes MPS GPU usage |

**Total thread count**: 8 workers × 2 threads = 16 threads (matches M1 Pro's 8 perf + 2 efficiency cores)

### Memory Management

| Strategy | Benefit |
|----------|---------|
| **Quantization** | 75% RAM savings on vectors |
| **Subprocess Isolation** | Prevents memory leaks from C++ crashes |
| **CPU-only Parsing** | Avoids MPS GPU memory exhaustion (18GB limit) |
| **Automatic Cleanup** | Removes temp files after processing |

### Expected Performance

| Metric | Value | Notes |
|--------|-------|-------|
| **Metadata-Only** | ~5-10 items/sec | Title, abstract, notes only |
| **Full-Text** | ~2-5 items/sec | Includes PDF parsing with Docling |
| **3425 Items** | ~35-47 hours | Full-text indexing with current config |
| **Search Latency** | <100ms | Hybrid search with reranking |

**Performance notes**:
- CPU-only Docling is 7.3x faster than GPU mode (35s vs 254s per PDF)
- GPU still used for embeddings (sequential, no contention)
- Deduplication adds negligible overhead (~1ms per item)

---

## Critical Fixes

**Production-ready improvements (October 2025)**

### 1. Subprocess Isolation

**Problem**: pypdfium2 C++ backend crashes bypassed Python exception handling, causing semaphore leaks and process crashes after 150-200 PDFs.

**Solution**: Run Docling in isolated subprocess with configurable timeout.

**Benefits**:
- ✅ Main process immune to C++ crashes
- ✅ Handles large documents (1-hour timeout)
- ✅ Supports infinite timeout (`null`)
- ✅ Clear error codes: `"failed"`, `"timeout"`, `"error"`

**Implementation**: `local_db.py:_extract_text_from_pdf()`

### 2. Removed pdfminer Fallback

**Problem**: PDFs timing out fell back to pdfminer, resulting in inconsistent output quality:
- Docling: 49 chunks × 512 tokens + rich metadata (⭐⭐⭐⭐⭐)
- pdfminer: 1 blob × 8000 tokens, no metadata (⭐⭐)

**Solution**: Removed pdfminer fallback entirely.

**Benefits**:
- ✅ 100% consistent high-quality chunking
- ✅ All indexed papers have identical structure
- ✅ Fail loudly instead of silent degradation

### 3. Configurable Timeout

**Problem**: 30s timeout insufficient for large documents (textbooks, dissertations).

**Solution**: Configurable timeout with sensible defaults.

**Options**:
- `3600` (1 hour) - Default, handles most documents
- `null` - Infinite timeout for extremely large PDFs
- Custom integer - Set per your needs

**Configuration**: `config.json` → `semantic_search.docling.subprocess_timeout`

---

## Indexing Pipeline

**Standard default production pipeline command:**

```bash
zotero-mcp update-db --force-rebuild --fulltext
```

### What This Does

**Step-by-step execution:**

1. ✅ **Delete Qdrant collection** (`--force-rebuild` flag)
   - Ensures clean slate
   - Removes any contaminated data

2. ✅ **Read all items from local Zotero database**
   - Direct SQLite access (fast)
   - No API rate limits

3. ✅ **Parse PDFs with Docling**
   - Subprocess-isolated (crash-proof)
   - 1-hour timeout per PDF
   - CPU-only processing (7.3x faster)
   - HybridChunker: 512 tokens per chunk
   - Preserves structure + metadata

4. ✅ **Generate embeddings**
   - BGE-M3 dense vectors (1024D)
   - BM25 sparse vectors (10,000 features)
   - GPU-accelerated (batch size 32)

5. ✅ **Store in Qdrant**
   - Hybrid vectors (dense + sparse)
   - Scalar quantization (int8)
   - HNSW indexing (m=32, ef=200)
   - Batch size 500 for fast writes

6. ✅ **Extract Neo4j knowledge graph** (optional)
   - GPT-4o-mini entity extraction
   - 6 entity types, 10 relationship types
   - Entity resolution enabled

7. ✅ **Optimize Qdrant collection**
   - Automatic after indexing
   - Builds final HNSW index

### Command Flags

| Flag | Effect | Default |
|------|--------|---------|
| `--force-rebuild` | Delete collection before indexing | `false` (incremental) |
| `--fulltext` | Parse PDFs with Docling | `true` (from config) |
| `--limit N` | Process only N items | None (all items) |

**Note**: Flags override config defaults. Without flags, uses values from `update_config`.

### Monitoring Progress

**Real-time monitoring:**

```bash
# View progress (every 10 items)
tail -f /tmp/zotero-indexing.log

# Check Qdrant collection size
curl http://localhost:6333/collections/zotero_library_qdrant

# Database status
zotero-mcp db-status
```

### Expected Output

**Console output format:**

```
Total items to index: 3425
Processed: 10/3425 added:8 skipped:2 errors:0
Processed: 20/3425 added:17 skipped:3 errors:0
...
✓ Docling parsed paper.pdf (49 chunks)
✓ Docling parsed thesis.pdf (127 chunks)
✗ Docling timeout (60min) for huge_book.pdf
```

### Post-Indexing Verification

**Verify successful indexing:**

```bash
# Check document count
zotero-mcp db-status

# Inspect specific item
zotero-mcp db-inspect --key ITEM_KEY

# Test search
# Via Claude Desktop: "Search my library for papers about transformers"
```

---

## Configuration Files

### Main Configuration

**Location**: `~/.config/zotero-mcp/config.json`

**Full example**: See `config_examples/config_qdrant.json` in repository

### Docker Compose (Optional)

**Location**: `docker-compose.yml` (create in project root)

```yaml
version: '3.8'
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./qdrant_storage:/qdrant/storage
    container_name: agent-zot-qdrant

  neo4j:
    image: neo4j:5.15.0
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/demodemo
    container_name: agent-zot-neo4j
```

---

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

### Docling Parsing Errors

**Low text extraction** → OCR would trigger (but disabled)
- Solution: Verify PDF is not scanned/image-only
- Consider re-OCRing PDF externally first

**Large PDFs timeout** → Increase subprocess timeout
- Edit: `config.json` → `docling.subprocess_timeout`
- Set to `null` for infinite timeout

**Formula parsing issues** → Toggle formula enrichment
- Edit: `config.json` → `docling.do_formula_enrichment`

### Neo4j Issues

```bash
# Check Neo4j status
docker logs agent-zot-neo4j

# Access Neo4j browser
open http://localhost:7474
# Login: neo4j / demodemo
```

---

## Version History

- **October 2025**: Subprocess isolation, removed pdfminer fallback, configurable timeout
- **September 2025**: BGE-M3 embeddings, hybrid search, 8-worker parallelization
- **August 2025**: Initial Qdrant migration, Neo4j GraphRAG integration

---

## See Also

- **CLAUDE.md** - Development guide for AI assistants
- **README.md** - Quick start and architecture overview
- **config_examples/config_qdrant.json** - Full configuration template
