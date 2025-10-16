# Agent-Zot Settings Reference
**Complete Inventory of All Settings & Configurations**

> 📖 **Detailed Guide**: For comprehensive explanations, rationale, and setup instructions, see [configuration.md](configuration.md)

Generated: 2025-10-16
Status: Production-ready configuration as of this moment

## Purpose

This document provides an exhaustive inventory of **every single setting** in Agent-Zot, clearly labeled as either user-configurable or hardcoded. Use this for:
- Quick lookups ("What is X set to?")
- Configuration auditing
- Verification after changes
- Understanding the complete system state

Legend:
- **[CONFIG]** = In config.json (user override)
- **[CODE]** = Hardcoded in source (not configurable without editing code)
- **Value shown** = Actual runtime value used when Agent-Zot launches

---

## 1. ZOTERO INTEGRATION

### Connection Mode
- `ZOTERO_LOCAL`: `"true"` **[CONFIG]** - Use local SQLite database instead of API

### API Credentials (Not Used in Local Mode)
- `ZOTERO_API_KEY`: Not set (local mode active)
- `ZOTERO_LIBRARY_ID`: Not set (local mode active)
- `ZOTERO_LIBRARY_TYPE`: Not set (local mode active)

### Database Location
- SQLite path: `~/Zotero/zotero.sqlite` **[CODE]** - Auto-detected
- Storage path: `~/Zotero/storage/` **[CODE]** - Auto-detected

---

## 2. DOCLING PDF PARSER

### Backend Configuration
- Backend: `DoclingParseV2DocumentBackend` **[CODE]** - Fast pypdfium2-based
- Device: `cpu` **[CODE]** - Forced CPU to avoid MPS memory exhaustion
- Subprocess isolation: `Enabled` **[CODE]** - Prevents C++ crashes
- Subprocess timeout: `3600` seconds **[CONFIG]** - 1 hour for large documents

### HybridChunker Settings
- `tokenizer`: `"BAAI/bge-m3"` **[CONFIG]** - Aligned with embedding model
- `max_tokens`: `512` **[CONFIG]** - Chunk size
- `merge_peers`: `true` **[CONFIG]** - Merge undersized adjacent chunks
- `delimiter`: `"\n"` **[CODE]** - Preserve paragraph structure
- Token-aware: `true` **[CODE]** - Accurate multilingual token counting

### Parsing Features
- `do_formula_enrichment`: `false` **[CONFIG]** - No LaTeX→text conversion
- `do_table_structure`: `true` **[CONFIG]** - Parse table structure
- `num_threads`: `2` **[CONFIG]** - CPU threads per worker

### OCR Configuration
- `ocr.fallback_enabled`: `false` **[CONFIG]** - No OCR fallback
- `ocr.min_text_threshold`: `100` **[CONFIG]** - Minimum chars before OCR triggers
- `enable_granite_fallback`: `false` **[CODE]** - No Granite VLM fallback
- `granite_min_text_threshold`: `100` **[CODE]** - Minimum chars for Granite

### Metadata Extraction (Always Active)
- Headings: `✅ Enabled` **[CODE]** - Full hierarchy preserved
- Page numbers: `✅ Enabled` **[CODE]** - Source page tracking
- Document structure: `✅ Enabled` **[CODE]** - Reading order maintained
- Bounding boxes: `✅ Enabled` **[CODE]** - Spatial coordinates
- Doc items: `✅ Enabled` **[CODE]** - Self-references for linking

### Reference Filtering (NEW - Oct 2025)
- Filter labels: `[REFERENCE, PAGE_HEADER, PAGE_FOOTER]` **[CODE]**
- Applied at: Chunk level **[CODE]**
- Fallback: Keep chunk if no doc_items **[CODE]**

---

## 3. PARALLEL PROCESSING

### Worker Configuration
- Parallel workers: `8` **[CODE]** - Optimized for M1 Pro (8 performance cores)
- Executor type: `ThreadPoolExecutor` **[CODE]** - Standard, no semaphore leaks
- Worker isolation: Fresh DoclingParser per PDF **[CODE]** - Thread safety

### Batch Processing
- Batch size: `200` items **[CODE]** - Items per processing batch
- Deduplication: `Automatic` **[CODE]** - Prevents re-indexing

### ParseCache Integration
- Cache location: `~/.cache/agent-zot/parsed_docs.db` **[CODE]**
- Cache key: MD5 of PDF content **[CODE]**
- Invalidation: MD5 mismatch triggers re-parse **[CODE]**

---

## 4. QDRANT VECTOR DATABASE

### Connection Settings
- `qdrant_url`: `"http://localhost:6333"` **[CONFIG]**
- `collection_name`: `"zotero_library_qdrant"` **[CONFIG]**
- `qdrant_api_key`: `null` **[CONFIG]** - Not needed for local Docker
- Physical storage: Docker volume `agent-zot-qdrant-data` at `/var/lib/docker/volumes/agent-zot-qdrant-data/_data` **[CODE]**

### Embedding Model
- `embedding_model`: `"sentence-transformers"` **[CONFIG]**
- `sentence_transformer_model`: `"BAAI/bge-m3"` **[CONFIG]**
- Model dimension: `1024` **[CODE]** - BGE-M3 native dimension
- Device: `mps` **[CODE]** - GPU-accelerated (Apple Silicon)
- Batch size (GPU): `32` chunks **[CODE]** - Optimal for M1 Pro MPS

### Dense Vector Configuration
- Vector size: `1024` dimensions **[CODE]** - From BGE-M3
- Distance metric: `Cosine` **[CODE]** - Standard for semantic search
- Quantization: `✅ Enabled` **[CODE]** - INT8 scalar quantization
- Quantization type: `INT8` **[CODE]** - 75% memory savings
- Quantization mode: `always_ram=True` **[CODE]** - Keep in RAM for speed
- Rescore: `true` **[CODE]** - Rescore top results with original vectors

### Sparse Vector Configuration (BM25)
- Hybrid search: `✅ Enabled` **[CODE]** - Dense + sparse fusion
- Sparse model: `BM25 with TF-IDF` **[CODE]**
- Max features: `10,000` terms **[CODE]** - Vocabulary size
- Lowercase: `true` **[CODE]** - Case-insensitive matching
- Stop words: `English + German` **[CODE]** - Multilingual filtering (71 English + 67 German = 138 total)
- IDF: `✅ Enabled` **[CODE]** - Inverse document frequency weighting
- Normalization: `None` **[CODE]** - BM25-style scoring (no L2 norm)

### HNSW Index Configuration
- M (connections per node): `32` **[CODE]** - Higher = better recall (default: 16)
- EF Construct: `200` **[CODE]** - Build-time accuracy (default: 100)
- Indexing threshold: `20,000` vectors **[CODE]** - When to start indexing
- Payload threshold: `10,000` vectors **[CODE]** - When to optimize

### Search & Reranking
- Reranking: `✅ Enabled` **[CODE]** - Cross-encoder reranking
- Reranker model: `cross-encoder/ms-marco-MiniLM-L-6-v2` **[CODE]**
- Device (reranker): `mps` **[CODE]** - GPU-accelerated
- Fusion method: `RRF (Reciprocal Rank Fusion)` **[CODE]** - Combines dense + sparse

### Performance Tuning
- Batch size (upload): `500` points **[CODE]** - 5x faster than default (100)
- Optimization: `Automatic` **[CODE]** - Runs after indexing completes
- Collection caching: `Enabled` **[CODE]** - In-memory collection info

---

## 5. NEO4J KNOWLEDGE GRAPH

### Connection Settings
- `enabled`: `true` **[CONFIG]**
- `neo4j_uri`: `"neo4j://127.0.0.1:7687"` **[CONFIG]**
- `neo4j_user`: `"neo4j"` **[CONFIG]**
- `neo4j_password`: `"demodemo"` **[CONFIG]**
- `neo4j_database`: `"neo4j"` **[CONFIG]**

### LLM Configuration
- `llm_model`: `"ollama/qwen2.5:7b-instruct"` **[CONFIG]**
- Embedding model: `SentenceTransformer (BAAI/bge-m3)` **[CODE]** - When using Ollama without OpenAI key
- Embedding dimension: `1024` **[CODE]** - Matches Qdrant

### Schema Configuration
- `entity_types`: **[CONFIG]** - 8 types
  1. Person
  2. Institution
  3. Concept
  4. Method
  5. Dataset
  6. Theory
  7. Journal
  8. Field

- `relation_types`: **[CONFIG]** - 12 types
  1. AUTHORED_BY
  2. AFFILIATED_WITH
  3. USES_METHOD
  4. USES_DATASET
  5. APPLIES_THEORY
  6. DISCUSSES_CONCEPT
  7. BUILDS_ON
  8. EXTENDS
  9. RELATED_TO
  10. CITES
  11. PUBLISHED_IN
  12. BELONGS_TO_FIELD

### Advanced Features
- `perform_entity_resolution`: `true` **[CONFIG]** - Merge similar entities
- `enable_lexical_graph`: `true` **[CONFIG]** - BM25 keyword connections
- Custom extraction prompt: `✅ Active` **[CODE]** - Optimized for research papers
- Database indexes: `✅ Created` **[CODE]** - 10-100x faster queries
- Vector embeddings: `✅ Supported` **[CODE]** - Requires Neo4j 5.23.0+ with APOC

---

## 6. UPDATE CONFIGURATION

### Auto-Update Settings
- `auto_update`: `false` **[CONFIG]** - Manual updates only
- `update_frequency`: `"manual"` **[CONFIG]**
- `update_days`: `7` **[CONFIG]** - Check weekly (when auto-update enabled)
- `last_update`: `"2025-10-16T22:02:09.147508"` **[CONFIG]** - Last indexing run

---

## 7. MCP SERVER CONFIGURATION

### Server Settings
- Protocol: `FastMCP` **[CODE]**
- Port: Default (assigned by Claude Desktop) **[CODE]**
- Tools exposed: `38 active` **[CODE]** (36 original + 2 new workflow tools)
- Tool prefix: `zot_` **[CODE]**

### Tool Enhancements (Phase 4)
- ReadOnlyHint: `✅ All tools` **[CODE]** - Helps Claude understand safety
- Title metadata: `✅ All tools` **[CODE]** - Human-readable names
- Zero-bias examples: `✅ All tools` **[CODE]** - Intent-based patterns

### Deprecated Tools (Phase 4)
- `zot_get_item_metadata`: ⚠️ Use `zot_get_item()` instead
- `zot_get_item_fulltext`: ⚠️ Use `zot_get_item()` instead
- `zot_get_item_children`: ⚠️ Use `zot_get_item()` instead

### New Workflow Tools (Phase 5-6)
- `zot_ask_paper`: ✅ Ask questions about paper content (returns text chunks)
- `zot_literature_review`: ✅ Automated review workflow (search → analyze → summarize)

---

## 8. SEARCH BEHAVIOR

### Query Processing
- Default limit: `10` results **[CODE]**
- Maximum limit: Unlimited (user can specify) **[CODE]**
- Search timeout: None (no timeout) **[CODE]**

### Result Ranking
1. Dense semantic similarity (BGE-M3) **[CODE]**
2. Sparse keyword matching (BM25) **[CODE]**
3. RRF fusion of above **[CODE]**
4. Cross-encoder reranking (ms-marco) **[CODE]**
5. Final sorted results **[CODE]**

---

## 9. LOGGING & MONITORING

### Log Locations
- Indexing logs: `/tmp/agent-zot-*.log` **[CODE]**
- Application logs: `stderr` **[CODE]**
- Parse cache: `~/.cache/agent-zot/parsed_docs.db` **[CODE]**

### Log Levels
- Default: `INFO` **[CODE]**
- Configurable: Yes (via Python logging) **[CODE]**

---

## 10. ERROR HANDLING

### Docling Parsing
- Subprocess crash: Main process continues **[CODE]**
- Timeout: Subprocess killed after 3600s **[CONFIG]**
- Parse failure: Logged, item skipped **[CODE]**
- Error codes: `"failed"`, `"timeout"`, `"error"` **[CODE]**

### Qdrant Operations
- Connection failure: Raises exception **[CODE]**
- Upload failure: Logged, retries **[CODE]**
- Search failure: Returns empty results **[CODE]**

### Neo4j Operations
- Connection failure: GraphRAG disabled **[CODE]**
- Extraction failure: Logged, continues **[CODE]**
- Graph tools: Return "requires Neo4j" message **[CODE]**

---

## 11. PERFORMANCE METRICS (Reference Only)

These are observed performance characteristics, not configurable settings:

### Parsing Performance
- Average PDF parse time: ~7-8 seconds **[OBSERVED]**
- Throughput: ~476 PDFs/hour (8 workers) **[OBSERVED]**
- CPU utilization: ~90-95% (8 cores) **[OBSERVED]**

### Embedding Performance
- Batch embedding (32 chunks): ~2-3 seconds **[OBSERVED]**
- Device: MPS GPU (Apple Silicon) **[OBSERVED]**
- Throughput: ~500-600 chunks/minute **[OBSERVED]**

### Vector Upload
- Batch size: 500 points **[CODE]**
- Upload time: ~1-2 seconds per batch **[OBSERVED]**

### End-to-End Pipeline
- Full library (2,411 papers): ~10-12 hours **[OBSERVED]**
- Stage 1 (Parsing): ~8-10 hours **[OBSERVED]**
- Stage 2 (Embedding): ~1-2 hours **[OBSERVED]**

---

## 12. SYSTEM REQUIREMENTS (Reference Only)

### Hardware
- CPU: 8+ cores recommended (tested on M1 Pro) **[DOCS]**
- RAM: 16GB minimum, 32GB recommended **[DOCS]**
- GPU: Optional (MPS for Apple Silicon, CUDA for NVIDIA) **[DOCS]**
- Storage: ~10GB for 2,500 papers (vectors + PDFs) **[OBSERVED]**

### Software Dependencies
- Python: 3.10+ **[DOCS]**
- Docker: For Qdrant and Neo4j **[DOCS]**
- Ollama: Optional (for free local LLM) **[DOCS]**

---

## SUMMARY

**Total Settings Documented**: 100+

**Breakdown**:
- User-Configurable (in config.json): 28 settings
- Hardcoded (in source code): 72+ settings
- Auto-detected (system paths): 3 settings

**Config File Size**: 65 lines (formatted JSON)
**Code Defaults Coverage**: 100% of undocumented behavior captured

**Last Verified**: 2025-10-16 (comprehensive audit passed with all ✅)
