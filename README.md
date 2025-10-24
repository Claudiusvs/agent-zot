<div align="center">

<img src="docs/assets/agent-zot-mascot.png" alt="Agent-Zot Mascot" width="300"/>

# 🤖 Agent-Zot

### *Your AI-Powered Research Librarian*

**Supercharge your Zotero library with semantic search, knowledge graphs, and intelligent document understanding**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Qdrant](https://img.shields.io/badge/vector_db-Qdrant-DC244C.svg)](https://qdrant.tech/)
[![Neo4j](https://img.shields.io/badge/graph_db-Neo4j-008CC1.svg)](https://neo4j.com/)

[Features](#-features) • [Quick Start](#-quick-start) • [Installation](#-installation) • [Configuration](#-configuration) • [Documentation](#-documentation)

</div>

---

## 🎯 What is Agent-Zot?

Agent-Zot transforms your Zotero research library into an intelligent, searchable knowledge base. Ask questions in natural language, discover connections between papers, and find exactly what you're looking for—even if you don't remember the exact title.

**Built on the excellent [zotero-mcp](https://github.com/54yyyu/zotero-mcp) by @54yyyu**, Agent-Zot adds production-ready enhancements for speed, accuracy, and scale.

### Why Agent-Zot?

- 🔍 **Semantic Search**: Find papers by meaning, not just keywords
- 🧠 **Knowledge Graphs**: Discover hidden connections between research
- ⚡ **Lightning Fast**: 7x faster PDF parsing with intelligent parallelization
- 🎯 **Highly Accurate**: State-of-the-art multilingual embeddings (BGE-M3)
- 🛡️ **Production-Ready**: Built for stability with thousands of papers
- 🎨 **Works with Claude**: Seamless integration via MCP protocol

---

## ✨ Features

### 🔎 **Hybrid Search Engine**
- **Semantic Understanding**: BGE-M3 embeddings (1024D, multilingual, SOTA performance)
- **Keyword Matching**: BM25 sparse vectors for precise term matching
- **Smart Fusion**: RRF (Reciprocal Rank Fusion) combines both approaches
- **Re-ranking**: Cross-encoder boosts result quality by 10-20%
- **Memory Efficient**: INT8 quantization saves 75% RAM

### 🎯 **Advanced Search Capabilities**
- **🆕 Smart Unified Search (`zot_search`)**: Single tool that automatically:
  - Detects query intent (entity/relationship/metadata/semantic)
  - Selects optimal backend combination (Fast/Entity-enriched/Graph-enriched/Metadata-enriched/Comprehensive modes)
  - Expands vague queries with domain-specific terms
  - Escalates to comprehensive search when quality is inadequate
  - Provides result provenance (shows which backends found each paper)
- **Intelligent Backend Selection (5 Modes)**:
  - Fast Mode (Qdrant only) for simple semantic queries (~2 seconds)
  - Entity-enriched Mode (Qdrant chunks + Neo4j entities) for entity discovery (~4 seconds)
  - Graph-enriched Mode (Qdrant + Neo4j) for relationship queries (~4 seconds)
  - Metadata-enriched Mode (Qdrant + Zotero API) for author/year queries (~4 seconds)
  - Comprehensive Mode (all backends) automatic fallback (~6-8 seconds, sequential execution)
- **Quality Assessment**: Real-time confidence scoring, coverage metrics, and adaptive recommendations
- **Query Decomposition**: Handles complex multi-concept queries (AND/OR logic, comma-separated)

### 📄 **Intelligent Document Processing**
- **Advanced PDF Parsing**: Docling V2 backend with structure preservation
- **Blazing Fast**: CPU-only processing, 8 parallel workers (~18 seconds/PDF)
- **Smart Chunking**: Token-aware HybridChunker respects document hierarchy
- **Crash-Proof**: Subprocess isolation prevents corrupted PDFs from breaking indexing
- **Skip Logic**: Gracefully handles problematic documents

### 🕸️ **Knowledge Graph (Optional)**
- **Auto-Extraction**: Identify entities, concepts, and relationships
- **Config-Driven Schema**: 8 entity types, 12 relationship types (fully customizable)
- **Smart Merging**: Entity resolution consolidates similar concepts
- **Free Local LLM**: Ollama with Mistral 7B Instruct or GPT-4o-mini
- **Free Local Embeddings**: BGE-M3 via SentenceTransformer (no API costs)
- **Concurrent Population**: 6-9x faster graph building (73h → 10-12h for 2,411 papers)

### 🎛️ **Production-Grade Infrastructure**
- **Vector Database**: Qdrant with HNSW indexing (sub-100ms searches)
- **Graph Database**: Neo4j for relationship exploration
- **Resource Management**:
  - Sequential backend execution prevents memory exhaustion (Comprehensive Mode)
  - Automatic orphaned process cleanup on startup
  - Safe concurrent sessions (multiple Claude Code instances)
- **Config-Driven**: Sensible defaults, fully customizable
- **Incremental Updates**: Smart deduplication for restart-safe indexing
- **Comprehensive Logging**: Track progress, debug issues easily

---

## 🎉 Recent Updates (October 2025)

### Smart Unified Search Tool
- **🆕 `zot_search`**: New intelligent search tool that consolidates `zot_semantic_search`, `zot_unified_search`, `zot_refine_search`, `zot_enhanced_semantic_search`, `zot_decompose_query`, and `zot_search_items`
- **Intent Detection**: Automatically recognizes entity discovery, relationship, metadata, and semantic queries
- **Automatic Decomposition**: Phase 0 pre-processing detects and decomposes multi-concept queries (AND/OR/complex patterns)
- **Smart Mode Selection**: Chooses optimal backend combination from 5 execution modes
- **Five Execution Modes**:
  - Fast Mode (Qdrant only, ~2s)
  - Entity-enriched Mode (Qdrant chunks + Neo4j entities, ~4s) - 🆕 Entity discovery
  - Graph-enriched Mode (Qdrant + Neo4j, ~4s)
  - Metadata-enriched Mode (Qdrant + Zotero API, ~4s)
  - Comprehensive Mode (all backends, ~6-8s)
- **Query Expansion**: Refines vague queries with domain-specific terms
- **Automatic Escalation**: Upgrades to comprehensive search when results are inadequate
- **Provenance Tracking**: Shows which backends found each paper

### Smart Unified Summarization Tool
- **🆕 `zot_summarize`**: New intelligent summarization tool that consolidates `zot_ask_paper`, `zot_get_item`, and `zot_get_item_fulltext` (all content/metadata retrieval operations)
- **Intent Detection**: Automatically recognizes desired depth (quick/targeted/comprehensive/full)
- **Cost Optimization**: Selects most efficient strategy (prevents unnecessary full-text extraction)
- **Multi-Aspect Orchestration**: Comprehensive mode automatically asks 4 key questions (research question, methodology, findings, conclusions)
- **Four Execution Modes**: Quick (~500-800 tokens), Targeted (~2k-5k tokens), Comprehensive (~8k-15k tokens), Full (10k-100k tokens)
- **Smart Escalation**: Recommends mode upgrade when needed

### Smart Unified Graph Exploration Tool
- **🆕 `zot_explore_graph`**: New intelligent graph exploration tool that consolidates 7 legacy graph tools into one intelligent interface
- **Intent Detection**: Automatically recognizes query type (citation/collaboration/concept/temporal/influence/venue)
- **Parameter Extraction**: Extracts author names, years, concepts from natural language queries
- **Smart Mode Selection**: Chooses optimal Neo4j traversal strategy automatically
- **Seven Execution Modes**: Citation Chain, Influence (PageRank), Related Papers, Collaboration, Concept Network, Temporal, Venue Analysis, plus Comprehensive
- **Multi-Strategy Exploration**: Comprehensive mode runs multiple strategies and merges results

### Resource Management & Stability
- **Sequential Execution**: Comprehensive Mode (3 backends) runs sequentially instead of parallel to prevent memory exhaustion and system freezes
- **Parallel Optimization**: Fast/Graph-enriched/Metadata-enriched modes (1-2 backends) still run in parallel for speed
- **Orphaned Process Cleanup**: Automatic cleanup of abandoned processes on server startup
- **Concurrent Sessions**: Safe to run multiple Claude Code sessions simultaneously

### Bug Fixes
- **Neo4j Availability**: Fixed detection using correct `get_graph_statistics()` method
- **Collaboration Patterns**: Fixed regex to match "collaborated", "collaboration", "collaborating" (not just "collaborat")
- **Complex Author Names**: Support for names with apostrophes (O'Brien), hyphens (Smith-Jones), internal capitals (DePrince, McDonald)
- **Provenance Deduplication**: Fixed duplicate backend names in search results

---

## 🚀 Quick Start

### Prerequisites

- 🐳 **Docker** (for Qdrant + Neo4j)
- 🐍 **Python 3.12+** with virtual environment
- 📚 **Zotero** with local database

### ⚡ 3-Step Installation

#### 1️⃣ Start Required Services

```bash
# Qdrant (vector database) - Required
docker volume create agent-zot-qdrant-data
docker run -d -p 6333:6333 -p 6334:6334 \
  -v agent-zot-qdrant-data:/qdrant/storage \
  --name agent-zot-qdrant \
  --restart unless-stopped \
  qdrant/qdrant

# Neo4j (knowledge graph) - Optional
# Requires Neo4j 5.23.0+ with APOC plugin for relationship vector support
docker volume create agent-zot-neo4j-data
docker run -d -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/demodemo \
  -e NEO4J_PLUGINS='["apoc"]' \
  -v agent-zot-neo4j-data:/data \
  --name agent-zot-neo4j \
  --restart unless-stopped \
  neo4j:5.23.0
```

#### 2️⃣ Install & Configure

```bash
# Create virtual environment
python3.12 -m venv ~/toolboxes/agent-zot/.venv
source ~/toolboxes/agent-zot/.venv/bin/activate

# Install Agent-Zot
pip install -e .

# Copy config template
mkdir -p ~/.config/agent-zot
cp config_examples/config_qdrant.json ~/.config/agent-zot/config.json

# Edit with your settings (API keys, paths)
nano ~/.config/agent-zot/config.json
```

#### 3️⃣ Index Your Library

**For large libraries (1,000+ papers)**, use the background helper to survive laptop closure:

```bash
# Full rebuild in persistent tmux session (10-40 hours)
./scripts/index-background.sh --full

# Test with first 10 items
./scripts/index-background.sh --limit 10

# Session survives: terminal closure, laptop sleep, shell exit
# Monitor: tail -f /tmp/agent-zot-index-*.log
# Detach: Ctrl+B then D
```

**For quick updates or small libraries:**

```bash
# Full-text indexing (recommended)
agent-zot update-db --fulltext

# Quick metadata-only indexing
agent-zot update-db

# Force complete rebuild (use sparingly)
agent-zot update-db --force-rebuild --fulltext
```

**💡 See [Long-Running Indexing Jobs](docs/guides/configuration.md#long-running-indexing-jobs) for details.**

**🎉 That's it!** Your library is now searchable. Ask Claude questions like:

- *"Find papers about transformer attention mechanisms"*
- *"Show me recent work on climate change mitigation"*
- *"What papers discuss both memory and PTSD?"*

---

## ⚙️ Configuration

Agent-Zot uses a single JSON config at `~/.config/agent-zot/config.json`. Here are the key settings:

### 🔧 Essential Settings

```json
{
  "client_env": {
    "ZOTERO_LOCAL": "true",              // Connect to local Zotero API (requires Zotero running)
    "ZOTERO_API_KEY": "your-key-here",
    "ZOTERO_LIBRARY_ID": "your-id",
    "OPENAI_API_KEY": "sk-..."           // For embeddings
  },
  "semantic_search": {
    "embedding_model": "sentence-transformers",
    "sentence_transformer_model": "BAAI/bge-m3",
    "enable_hybrid_search": true,        // Semantic + keyword
    "enable_reranking": true,            // Quality boost
    "batch_size": 500,                   // Qdrant batch size
    "update_config": {
      "force_rebuild": false,            // Safe incremental default
      "extract_fulltext": true           // Full PDF parsing
    }
  }
}
```

**⚠️ Important: ZOTERO_LOCAL Configuration**

When using `ZOTERO_LOCAL="true"`:
- ✅ **Zotero application must be running** - Agent-Zot connects to Zotero's local HTTP API server
- ✅ **Faster performance** - Direct access to local database via Zotero's API
- ❌ **Connection errors if Zotero closed** - You'll see "Connection refused" errors

When using `ZOTERO_LOCAL="false"`:
- ✅ **Works without Zotero running** - Uses Zotero's web API
- ✅ **Access from anywhere** - No local Zotero installation needed
- ❌ **Slower performance** - Network requests to Zotero servers
- ❌ **Requires API key** - Must have valid ZOTERO_API_KEY

### 📚 Advanced Configuration

**For complete details**, see:
- **[configuration.md](docs/guides/configuration.md)** - Comprehensive guide with explanations and rationale
- **[SETTINGS_REFERENCE.md](docs/guides/SETTINGS_REFERENCE.md)** - Quick reference inventory (100+ settings)
- **[CLAUDE.md](docs/CLAUDE.md)** - Complete technical documentation with detailed execution flow

**💡 New to Agent-Zot?**
- **Understanding settings?** → Start with [configuration.md](docs/guides/configuration.md) for WHY each setting exists
- **Quick lookup?** → Use [SETTINGS_REFERENCE.md](docs/guides/SETTINGS_REFERENCE.md) to verify WHAT values are active
- **Deep dive?** → Check [Active Pipeline Reference](docs/CLAUDE.md#active-pipeline-reference) for exact execution flow

### 🎨 Performance Tuning

```json
{
  "docling": {
    "tokenizer": "BAAI/bge-m3",        // Match your embedding model
    "max_tokens": 512,                 // Chunk size
    "num_threads": 2,                  // Per-worker (8 workers × 2 = 16)
    "subprocess_timeout": 3600,        // 1 hour for large PDFs
    "ocr": {
      "fallback_enabled": false        // Disabled for speed/stability
    }
  },
  "qdrant_optimizations": {
    "enable_quantization": true,       // 75% RAM savings
    "hnsw_m": 32,                      // Index quality
    "hnsw_ef_construct": 200           // Build quality
  }
}
```

---

## 💾 Backup & Data Protection

### Why Backups Matter

Your Qdrant and Neo4j data is stored in **Docker volumes** which persist across container restarts. However, volumes can be accidentally deleted or corrupted. Regular backups protect against:

- 🗑️ Accidental deletion
- 💥 Database corruption
- 🚀 Migration to new machines
- 🔬 Safe experimentation (rollback points)

### Quick Backup Commands

**Backup everything now:**
```bash
cd /Users/claudiusv.schroder/toolboxes/agent-zot
.venv/bin/python scripts/backup.py backup-all
```

**List available backups:**
```bash
.venv/bin/python scripts/backup.py list
```

**Backup only Qdrant or Neo4j:**
```bash
.venv/bin/python scripts/backup.py backup-qdrant  # Vector database
.venv/bin/python scripts/backup.py backup-neo4j   # Knowledge graph
```

### What Gets Backed Up

| Component | Size | Downtime | Contains |
|-----------|------|----------|----------|
| **Qdrant Snapshot** | ~1.7 GB | Zero | 234K text chunks, embeddings, metadata |
| **Neo4j Dump** | ~88 MB | ~30 sec | 25K nodes, 134K relationships |

**Backup locations:**
- Qdrant: `backups/qdrant/*.snapshot`
- Neo4j: `backups/neo4j/*.dump`

### Automated Backups (Optional)

Enable daily backups at 2 AM:
```bash
crontab -e
# Add this line:
0 2 * * * /Users/claudiusv.schroder/toolboxes/agent-zot/scripts/cron-backup.sh >> /tmp/agent-zot-backup.log 2>&1
```

### How Backups Work

**Qdrant (Vector Database):**
- Uses Qdrant's native snapshot API
- Creates compressed snapshot of entire collection
- Downloads to local `backups/qdrant/` directory
- Zero downtime during backup

**Neo4j (Knowledge Graph):**
- Stops Neo4j container temporarily (~30 seconds)
- Creates dump using `neo4j-admin database dump`
- Automatically restarts container
- Brief unavailability during backup

**Automatic Cleanup:**
- Keeps last 5 backups by default (configurable)
- Old backups automatically deleted
- Change retention: `--keep-last N`

### Restore from Backup

**Qdrant:**
```bash
# Copy snapshot to container
docker cp backups/qdrant/zotero_library_qdrant-backup-YYYYMMDD.snapshot \
  agent-zot-qdrant:/qdrant/snapshots/zotero_library_qdrant/

# Restore via API
curl -X PUT 'http://localhost:6333/collections/zotero_library_qdrant/snapshots/recover' \
  -H 'Content-Type: application/json' \
  -d '{"location":"file:///qdrant/snapshots/zotero_library_qdrant/zotero_library_qdrant-backup-YYYYMMDD.snapshot"}'
```

**Neo4j:**
```bash
# Stop container, copy dump, restore, restart
docker stop agent-zot-neo4j
docker cp backups/neo4j/neo4j-neo4j-YYYYMMDD.dump agent-zot-neo4j:/tmp/
docker exec agent-zot-neo4j neo4j-admin database load \
  --from-path=/tmp --database=neo4j --overwrite-destination=true
docker start agent-zot-neo4j
```

**📖 Full Documentation:** See [BACKUP_AUTOMATION.md](docs/BACKUP_AUTOMATION.md) for:
- Complete restore procedures
- Scheduled backup setup
- Troubleshooting guide
- Best practices

---

## 📖 Documentation

### For Users

- **[Quick Start Guide](docs/guides/quick-start.md)** - Get up and running fast
- **[Configuration Reference](docs/guides/configuration.md)** - All settings explained
- **[Backup & Recovery Guide](docs/BACKUP_AUTOMATION.md)** - Protect your data
- **[FAQ](docs/guides/faq.md)** - Common questions answered

### For Developers

- **[CLAUDE.md](docs/CLAUDE.md)** - Complete technical documentation
- **[Architecture Overview](docs/architecture.md)** - System design
- **[API Reference](docs/api.md)** - MCP tools and endpoints

---

## 🏗️ Architecture

<details>
<summary><b>📊 Click to expand system architecture</b></summary>

### Indexing Pipeline

```
Zotero Library (SQLite/API)
    ↓
[8 Parallel Workers] → Docling V2 Parser (CPU-only, ~18s/PDF)
    ↓
HybridChunker (512 tokens, structure-aware)
    ↓
BGE-M3 Embeddings (1024D dense + BM25 sparse, GPU-accelerated)
    ↓
Qdrant Storage (INT8 quantized, HNSW indexed)
    ↓
[Optional] Neo4j GraphRAG (GPT-4o-mini entity extraction)
```

### Search Pipeline

```
Natural Language Query
    ↓
BGE-M3 Embedding + BM25 Vector (GPU-accelerated)
    ↓
Hybrid Search in Qdrant (RRF fusion)
    ↓
Cross-Encoder Reranking (quality boost)
    ↓
[Optional] Graph Traversal (Neo4j)
    ↓
Ranked Results to Claude
```

### Core Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Vector DB** | Qdrant | Hybrid semantic + keyword search |
| **Graph DB** | Neo4j | Knowledge graph & relationships |
| **Embeddings** | BGE-M3 | SOTA multilingual semantic vectors |
| **Parser** | Docling V2 | Structure-aware PDF processing |
| **MCP Server** | FastMCP | Claude integration |
| **Local DB** | SQLite | Direct Zotero database access |

</details>

---

## 📊 Performance

Agent-Zot is optimized for real-world research libraries (1,000-10,000+ papers):

| Metric | Performance |
|--------|-------------|
| **Indexing Speed** | ~18 seconds/PDF average |
| **Throughput** | ~194 PDFs/hour (8 workers) |
| **Search Latency** | <100ms (hybrid + reranking) |
| **Memory Usage** | 75% reduced (INT8 quantization) |
| **Success Rate** | 95%+ (robust error handling) |

**Tested on**: M1 Pro (10-core, 16GB RAM) with 3,400+ papers

---

## 🤝 Contributing

Contributions welcome! Whether it's:

- 🐛 Bug reports
- ✨ Feature requests
- 📖 Documentation improvements
- 🔧 Code contributions

Please open an issue or PR on GitHub.

---

## 🙏 Acknowledgments

**Agent-Zot builds on incredible open-source work:**

- **[zotero-mcp](https://github.com/54yyyu/zotero-mcp)** by @54yyyu - Foundation of this project
- **[Qdrant](https://qdrant.tech/)** - Production vector database
- **[Docling](https://github.com/DS4SD/docling)** - IBM's advanced document parser
- **[BGE-M3](https://github.com/FlagOpen/FlagEmbedding)** - BAAI's multilingual embeddings
- **[Neo4j](https://neo4j.com/)** - Graph database for knowledge graphs
- **[FastMCP](https://github.com/jlowin/fastmcp)** - MCP server framework

---

## 📄 License

Same as original project - see [upstream repository](https://github.com/54yyyu/zotero-mcp)

---

<div align="center">

**Made with ❤️ for researchers everywhere**

*Have questions? [Open an issue](https://github.com/yourusername/agent-zot/issues) • Want to chat? [Start a discussion](https://github.com/yourusername/agent-zot/discussions)*

</div>
