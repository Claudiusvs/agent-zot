# Agent-Zot Technical Documentation for Claude Code

**Last Updated**: October 25, 2025
**Version**: Post-Management Consolidation
**Architecture**: 7 Unified Intelligent Tools (79% reduction from 34 legacy tools)

---

## 🎯 Overview

Agent-Zot provides Claude with intelligent access to research libraries through **7 unified tools** that automatically detect intent, select optimal backends, and handle complex workflows. This represents a complete consolidation from 34 specialized tools to 7 intelligent orchestrators.

### Complete Tool Consolidation

**Before**: 34 Legacy Tools
- Research Tools: 19 specialized tools
- Management Tools: 15 specialized tools

**After**: 7 Unified Intelligent Tools (79% reduction)
- **Research Tools**: 3 tools (84% reduction)
  - `zot_search` - Finding papers (5 execution modes)
  - `zot_summarize` - Understanding papers (4 depth modes)
  - `zot_explore_graph` - Exploring connections (9 modes: 8 graph + 1 content)
- **Management Tools**: 4 tools (73% reduction)
  - `zot_manage_collections` - Collections management (5 modes)
  - `zot_manage_tags` - Tags management (4 modes)
  - `zot_manage_notes` - Notes/annotations management (4 modes)
  - `zot_export` - Export operations (3 modes)

---

## 🔥 The 7 Unified Tools

### 1. `zot_search` - Finding Papers

**Purpose**: Smart unified search with automatic intent detection and backend selection.

**Five Execution Modes**:
1. **Fast Mode** (Qdrant only) - Simple semantic queries (~2 seconds)
2. **Entity-enriched Mode** (Qdrant chunks + Neo4j entities) - Entity discovery (~4 seconds)
3. **Graph-enriched Mode** (Qdrant + Neo4j) - Relationship queries (~4 seconds)
4. **Metadata-enriched Mode** (Qdrant + Zotero API) - Author/year queries (~4 seconds)
5. **Comprehensive Mode** (All backends) - Automatic fallback (~6-8 seconds, sequential)

**Key Features**:
- Intent detection from natural language queries
- Automatic query decomposition (Phase 0 for multi-concept queries)
- Smart backend selection based on query type
- Quality assessment with automatic escalation
- Result provenance tracking

**Replaces**: `zot_semantic_search`, `zot_unified_search`, `zot_refine_search`, `zot_enhanced_semantic_search`, `zot_hybrid_vector_graph_search`, `zot_decompose_query`, `zot_search_items`

**Example Queries**:
- "papers about transformer attention mechanisms" → Fast Mode
- "which methods appear in papers about attention?" → Entity-enriched Mode
- "papers by Smith published in 2023" → Metadata-enriched Mode
- "who collaborated with Einstein on quantum mechanics?" → Graph-enriched Mode

---

### 2. `zot_summarize` - Understanding Papers

**Purpose**: Smart depth-aware summarization with cost optimization.

**Four Execution Modes**:
1. **Quick Mode** (~500-800 tokens) - Overview questions, metadata + abstract
2. **Targeted Mode** (~2k-5k tokens) - Specific questions, semantic retrieval
3. **Comprehensive Mode** (~8k-15k tokens) - Full understanding, 4-aspect orchestration
4. **Full Mode** (10k-100k tokens) - Complete text extraction (expensive, rare use)

**Key Features**:
- Automatic depth detection from query intent
- Cost optimization (uses most efficient approach)
- Multi-aspect orchestration (4 key questions for comprehensive mode)
- Smart escalation recommendations

**Replaces**: `zot_ask_paper`, `zot_get_item`, `zot_get_item_fulltext`

**Example Queries**:
- "What is this paper about?" → Quick Mode
- "What methodology did they use?" → Targeted Mode
- "Summarize this paper comprehensively" → Comprehensive Mode (auto-asks 4 questions)

---

### 3. `zot_explore_graph` - Exploring Connections

**Purpose**: Smart graph exploration with dual backend (Neo4j + Qdrant).

**Nine Execution Modes**:
1. **Citation Chain Mode** (Neo4j) - 2-3 hop citation networks
2. **Influence Mode** (Neo4j PageRank) - Seminal/influential papers
3. **Content Similarity Mode** (Qdrant) - Vector-based "More Like This"
4. **Related Papers Mode** (Neo4j) - Graph-based shared entities
5. **Collaboration Mode** (Neo4j) - Co-authorship networks
6. **Concept Network Mode** (Neo4j) - Multi-hop concept relationships
7. **Temporal Mode** (Neo4j) - Topic evolution over time
8. **Venue Analysis Mode** (Neo4j) - Publication outlet ranking
9. **Comprehensive Mode** (Multi-strategy) - Combined exploration

**Key Features**:
- Dual backend: Neo4j (graph) + Qdrant (content)
- Automatic intent detection
- Parameter extraction (authors, years, concepts)
- Clear distinction: "Similar" (content) vs "Related" (graph)

**Replaces**: `zot_graph_search`, `zot_find_citation_chain`, `zot_find_seminal_papers`, `zot_find_similar_papers`, `zot_find_related_papers`, `zot_find_collaborator_network`, `zot_explore_concept_network`, `zot_track_topic_evolution`, `zot_analyze_venues`

**Example Queries**:
- "Find papers citing papers that cite X" → Citation Chain Mode
- "Find seminal papers in cognitive neuroscience" → Influence Mode
- "Papers similar to X" → Content Similarity Mode (Qdrant)
- "Papers related to X" → Related Papers Mode (Neo4j)
- "Track how deep learning evolved from 2015-2025" → Temporal Mode

---

### 4. `zot_manage_collections` - Collections Management

**Purpose**: Unified collections management with fuzzy matching.

**Five Execution Modes**:
1. **List Mode** - List all collections
2. **Create Mode** - Create new collection
3. **Show Items Mode** - Show items in collection
4. **Add Mode** - Add items to collection
5. **Remove Mode** - Remove items from collection

**Key Features**:
- Fuzzy collection name matching
- Automatic intent detection
- Natural language interface

**Replaces**: `zot_get_collections`, `zot_create_collection`, `zot_get_collection_items`, `zot_add_to_collection`, `zot_remove_from_collection`

**Example Queries**:
- "list my collections" → List Mode
- "create collection Machine Learning 2024" → Create Mode
- "show items in collection ML" → Show Items Mode (fuzzy match)

---

### 5. `zot_manage_tags` - Tags Management

**Purpose**: Unified tags management with advanced operators.

**Four Execution Modes**:
1. **List Mode** - List all tags
2. **Search Mode** - Find items by tag(s)
3. **Add Mode** - Add tag(s) to items
4. **Remove Mode** - Remove tag(s) from items

**Key Features**:
- Advanced operators (|| for OR, - for NOT)
- Automatic intent detection
- Batch operations

**Replaces**: `zot_get_tags`, `zot_search_by_tag`, `zot_batch_update_tags`

**Example Queries**:
- "list all tags" → List Mode
- "find papers tagged important OR urgent" → Search Mode (|| operator)
- "add tag reviewed to items [keys]" → Add Mode

---

### 6. `zot_manage_notes` - Notes Management

**Purpose**: Unified notes and annotations management.

**Four Execution Modes**:
1. **List Annotations Mode** - Get PDF annotations/highlights
2. **List Notes Mode** - Get standalone notes
3. **Search Mode** - Search notes by text
4. **Create Mode** - Create new note

**Key Features**:
- Handles both notes and PDF annotations
- Automatic intent detection
- HTML formatting for rich notes

**Replaces**: `zot_get_annotations`, `zot_get_notes`, `zot_search_notes`, `zot_create_note`

**Example Queries**:
- "show my annotations" → List Annotations Mode
- "list notes for paper X" → List Notes Mode
- "search notes for methodology" → Search Mode
- "create note for paper X about findings" → Create Mode

---

### 7. `zot_export` - Export Operations

**Purpose**: Unified export with automatic format detection.

**Three Execution Modes**:
1. **Markdown Mode** - Export to markdown files with YAML frontmatter
2. **BibTeX Mode** - Export to .bib file
3. **GraphML Mode** - Export Neo4j graph

**Key Features**:
- Automatic format detection from file extension
- Filtered exports (by query or collection)
- Dual backend: Zotero (markdown/bibtex) + Neo4j (graphml)

**Replaces**: `zot_export_markdown`, `zot_export_bibtex`, `zot_export_graph`

**Example Queries**:
- Export to "papers.md" → Markdown Mode (detected from .md extension)
- Export to "refs.bib" → BibTeX Mode (detected from .bib extension)
- Export to "graph.graphml" → GraphML Mode (detected from .graphml extension)

---

## 🎯 Query-Driven Tool Selection

**Principle**: Choose tools based on what the query asks for, not hierarchical ordering.

### Decision Tree

```
User Query
    ↓
┌──────────────────────────────────────────┐
│ Finding papers?                          │ → zot_search (auto-detects mode)
│ Understanding a paper?                   │ → zot_summarize (auto-detects depth)
│ Exploring connections?                   │ → zot_explore_graph (auto-detects intent)
│ Managing collections?                    │ → zot_manage_collections (auto-detects mode)
│ Managing tags?                           │ → zot_manage_tags (auto-detects mode)
│ Managing notes/annotations?              │ → zot_manage_notes (auto-detects mode)
│ Exporting data?                          │ → zot_export (auto-detects format)
└──────────────────────────────────────────┘
```

---

## 📊 Backend Architecture

### Three Backends

1. **Qdrant** (Vector Database)
   - **Purpose**: Semantic search over full-text chunks
   - **Technology**: HNSW indexing, INT8 quantization
   - **Data**: 234K+ text chunks from 2,411+ papers
   - **Speed**: Sub-100ms searches

2. **Neo4j** (Knowledge Graph)
   - **Purpose**: Relationship exploration, entity discovery
   - **Technology**: Graph traversal, PageRank, entity resolution
   - **Data**: 25K+ nodes, 138K+ relationships
   - **Population**: 98% complete

3. **Zotero API** (Metadata Source)
   - **Purpose**: Bibliographic metadata, collections, tags, notes
   - **Technology**: Local HTTP API (when ZOTERO_LOCAL=true) or web API
   - **Data**: Complete Zotero library metadata

### Backend Combination Strategies

| Mode | Backends Used | Speed | Cost | Best For |
|------|---------------|-------|------|----------|
| **Fast** | Qdrant only | ~2s | Low | Simple semantic queries |
| **Entity-enriched** | Qdrant chunks + Neo4j entities | ~4s | Medium | Entity discovery |
| **Graph-enriched** | Qdrant + Neo4j | ~4s | Medium | Relationship queries |
| **Metadata-enriched** | Qdrant + Zotero | ~4s | Medium | Author/year queries |
| **Comprehensive** | All 3 backends (sequential) | ~6-8s | Higher | Complex queries, automatic fallback |

---

## 🚀 Workflow Examples

### Example 1: Complete Literature Review

```
1. zot_search("neural mechanisms of cognitive control")
   → Finds relevant papers (automatic mode selection)

2. zot_summarize(item_key, "Summarize comprehensively")
   → Understands each paper (4-aspect summary)

3. zot_explore_graph("Find the most influential papers on cognitive control")
   → Identifies foundational work (Influence Mode)

4. zot_explore_graph("How has cognitive control research evolved from 2015-2025?")
   → Development trajectory (Temporal Mode)

5. zot_manage_collections("create collection Cognitive Control Review")
   → Organizes findings (Create Mode)

6. zot_export("review.bib")
   → Exports citations (BibTeX Mode, auto-detected)
```

### Example 2: Finding Collaboration Opportunities

```
1. zot_search("graph neural networks")
   → Finds papers in area

2. zot_explore_graph("Who collaborated with [top author]?")
   → Extended network (Collaboration Mode)

3. zot_summarize(item_key, "What methodology did they use?")
   → Understands approach (Targeted Mode)
```

---

## ⚙️ Configuration

### Key Settings in `~/.config/agent-zot/config.json`

```json
{
  "client_env": {
    "ZOTERO_LOCAL": "true",
    "ZOTERO_API_KEY": "your-key",
    "ZOTERO_LIBRARY_ID": "your-id"
  },
  "semantic_search": {
    "embedding_model": "sentence-transformers",
    "sentence_transformer_model": "BAAI/bge-m3",
    "enable_hybrid_search": true,
    "enable_reranking": true
  },
  "neo4j": {
    "enabled": true,
    "uri": "bolt://localhost:7687",
    "username": "neo4j",
    "password": "demodemo"
  }
}
```

---

## 📈 Benefits of Consolidation

### Quantitative Impact

- **79% total reduction**: 34 → 7 tools
- **Research: 84% reduction**: 19 → 3 tools
- **Management: 73% reduction**: 15 → 4 tools

### Qualitative Benefits

- ✅ **Natural language interface** replaces function signatures
- ✅ **Automatic intent detection** (no manual mode selection)
- ✅ **Automatic decomposition** (Phase 0 multi-concept queries)
- ✅ **Smart mode selection** (optimal strategy per query)
- ✅ **Built-in quality optimization** (escalates when needed)
- ✅ **Dual-backend architecture** (Neo4j + Qdrant)
- ✅ **Consistent interface** (same query → consistent routing)
- ✅ **Compound operations** (multi-step workflows in single request)
- ✅ **Reduced cognitive load** (7 vs 34+ options)
- ✅ **Cost optimization** (uses cheapest/fastest mode that works)

---

## 🔧 Maintenance & Utilities

### Database Status

```bash
# Check Qdrant collection
agent-zot get-search-database-status

# Check Neo4j graph
docker exec agent-zot-neo4j cypher-shell -u neo4j -p demodemo \
  "MATCH (n) RETURN count(n) as total"
```

### Indexing

```bash
# Update search database (Qdrant)
agent-zot update-search-database

# Full rebuild with full-text extraction
agent-zot update-search-database --force-rebuild --extract-fulltext
```

### Backup & Recovery

```bash
# Backup everything
python scripts/backup.py backup-all

# List backups
python scripts/backup.py list

# Restore (see docs/BACKUP_AUTOMATION.md for procedures)
```

---

## 📚 Additional Resources

- **[TOOL_HIERARCHY.md](development/TOOL_HIERARCHY.md)** - Complete architecture documentation
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Current configuration and commands
- **[README.md](../README.md)** - User-facing documentation
- **[BACKUP_AUTOMATION.md](BACKUP_AUTOMATION.md)** - Backup procedures
- **[Configuration Guide](guides/configuration.md)** - Comprehensive settings guide

---

**For Claude Code**: This document provides the technical foundation for understanding Agent-Zot's unified tool architecture. All 7 tools automatically handle intent detection, backend selection, and execution strategy. Trust their automatic mode selection - they're optimized for quality, speed, and cost.
