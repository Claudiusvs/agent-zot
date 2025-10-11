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

### 📄 **Intelligent Document Processing**
- **Advanced PDF Parsing**: Docling V2 backend with structure preservation
- **Blazing Fast**: CPU-only processing, 8 parallel workers (~18 seconds/PDF)
- **Smart Chunking**: Token-aware HybridChunker respects document hierarchy
- **Crash-Proof**: Subprocess isolation prevents corrupted PDFs from breaking indexing
- **Skip Logic**: Gracefully handles problematic documents

### 🕸️ **Knowledge Graph (Optional)**
- **Auto-Extraction**: Identify entities, concepts, and relationships
- **Entity Types**: Person, Institution, Concept, Method, Dataset, Theory, Journal, Field
- **Smart Merging**: Entity resolution consolidates similar concepts
- **Fast Queries**: Database indexes for 10-100x speedup
- **Powered by**: GPT-4o-mini or Ollama (local)

### 🎛️ **Production-Grade Infrastructure**
- **Vector Database**: Qdrant with HNSW indexing (sub-100ms searches)
- **Graph Database**: Neo4j for relationship exploration
- **Config-Driven**: Sensible defaults, fully customizable
- **Incremental Updates**: Smart deduplication for restart-safe indexing
- **Comprehensive Logging**: Track progress, debug issues easily

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
docker run -d -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage:z \
  --name agent-zot-qdrant \
  qdrant/qdrant

# Neo4j (knowledge graph) - Optional
docker run -d -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/demodemo \
  --name agent-zot-neo4j \
  neo4j:5.15.0
```

#### 2️⃣ Install & Configure

```bash
# Create virtual environment
python3.12 -m venv ~/agent-zot-env
source ~/agent-zot-env/bin/activate

# Install Agent-Zot
pip install -e .

# Copy config template
mkdir -p ~/.config/agent-zot
cp config_examples/config_qdrant.json ~/.config/agent-zot/config.json

# Edit with your settings (API keys, paths)
nano ~/.config/agent-zot/config.json
```

#### 3️⃣ Index Your Library

```bash
# Full-text indexing (recommended)
agent-zot update-db --fulltext

# Quick metadata-only indexing
agent-zot update-db

# Force complete rebuild (use sparingly)
agent-zot update-db --force-rebuild --fulltext
```

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
    "ZOTERO_LOCAL": "true",              // Use local DB (faster)
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

### 📚 Advanced Configuration

**For complete details**, see:
- **[CONFIGURATION.md](docs/guides/configuration.md)** - Full reference guide
- **[CLAUDE.md](docs/CLAUDE.md)** - Developer documentation

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

## 📖 Documentation

### For Users

- **[Quick Start Guide](docs/guides/quick-start.md)** - Get up and running fast
- **[Configuration Reference](docs/guides/configuration.md)** - All settings explained
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
