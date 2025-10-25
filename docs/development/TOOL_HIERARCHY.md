# Agent-Zot Tool Hierarchy

**Date**: 2025-10-24
**Version**: Post-Unified Tools Migration
**Context**: Documentation of the new 3-tool intelligent architecture

---

## 🎯 Architecture Overview

Agent-Zot has migrated from **15+ specialized tools** to **3 unified intelligent tools** that automatically:
- Detect query intent
- Select optimal backends
- Choose execution strategies
- Escalate when needed

This simplifies the tool landscape from complex hierarchical decision-making to query-driven automatic routing.

---

## 🆕 Three Unified Intelligent Tools (October 2025)

### **Tier 1: The Three Core Tools (🔥 HIGHEST PRIORITY)**

These are the **only tools Claude needs** for 95% of research workflows.

| Tool | Purpose | Auto-Detects | Execution Modes | Speed |
|------|---------|--------------|-----------------|-------|
| **`zot_search`** | Finding papers | Entity/Relationship/Metadata/Semantic intent | Fast/Entity-enriched/Graph-enriched/Metadata-enriched/Comprehensive (5 modes) | 2-8s |
| **`zot_summarize`** | Understanding papers | Quick/Targeted/Comprehensive/Full depth | 4 depth modes | 0.5-100k tokens |
| **`zot_explore_graph`** | Exploring connections | Citation/Collaboration/Concept/Temporal/Influence/Venue/Content Similarity intent | 9 modes total (8 graph + 1 content) | 2-10s |

**Why only 3 tools?**
- ✅ **Automatic intent detection** - No manual backend selection
- ✅ **Smart mode selection** - Chooses optimal strategy automatically
- ✅ **Built-in escalation** - Upgrades when quality inadequate
- ✅ **Quality optimization** - Uses cheapest/fastest mode that works
- ✅ **Consistent interface** - Same query → consistent routing

---

## 🔍 Tool #1: `zot_search` - Finding Papers

**Replaces 5 legacy tools:**
- ❌ `zot_semantic_search` (Fast Mode)
- ❌ `zot_unified_search` (Comprehensive Mode)
- ❌ `zot_refine_search` (built-in refinement)
- ❌ `zot_hybrid_vector_graph_search` (Graph-enriched Mode)
- ❌ `zot_enhanced_semantic_search` (Entity-enriched Mode) - 🆕

### Intent Detection Patterns

| Intent | Confidence | Query Patterns | Selected Mode |
|--------|-----------|----------------|---------------|
| **Entity** | 0.95 | "which methods/concepts appear in papers about X" | Entity-enriched Mode (Qdrant chunks + Neo4j entities) |
| **Relationship** | 0.90 | "who collaborated with X", "citation network for X" | Graph-enriched Mode (Qdrant + Neo4j) |
| **Metadata** | 0.80 | "papers by [Author] in [Year]", "published in [Journal]" | Metadata-enriched Mode (Qdrant + Zotero API) |
| **Semantic** | 0.70 | "papers about [topic]", "research on [concept]" | Fast Mode (Qdrant only) |

### Five Execution Modes

```
1. Fast Mode (Qdrant only)
   - Simple semantic queries
   - ~2 seconds, minimal cost
   - Example: "papers about neural networks"

2. Entity-enriched Mode (Qdrant chunks + Neo4j entities) 🆕
   - Entity discovery queries
   - ~4 seconds, moderate cost
   - Example: "which methods appear in papers about attention?"
   - Implements Figure 3 pattern from Qdrant GraphRAG

3. Graph-enriched Mode (Qdrant + Neo4j)
   - Relationship/network queries
   - ~4 seconds, moderate cost
   - Example: "who collaborated with [author]"

4. Metadata-enriched Mode (Qdrant + Zotero API)
   - Author/journal/year queries
   - ~4 seconds, moderate cost
   - Example: "papers by Smith published in 2023"

5. Comprehensive Mode (All backends)
   - Automatic fallback when quality inadequate
   - ~6-8 seconds, higher cost
   - Sequential execution prevents resource exhaustion
```

### Escalation Logic

```
Initial Search (Fast/Entity/Graph/Metadata Mode)
    ↓
Quality Assessment
    ├─ High confidence (≥10 results, score ≥0.7) → Done
    ├─ Medium confidence (≥5 results, score ≥0.6) → Done
    └─ Low confidence (<5 results or score <0.6) → Escalate
        ↓
    Add remaining backends → Comprehensive Mode
```

---

## 📄 Tool #2: `zot_summarize` - Understanding Papers

**Replaces 3 legacy tools:**
- ❌ `zot_ask_paper` (Targeted Mode)
- ❌ `zot_get_item` (Quick Mode)
- ❌ `zot_get_item_fulltext` (Full Mode)

### Depth Detection Patterns

| Depth | Token Cost | Query Patterns | Returns |
|-------|-----------|----------------|---------|
| **Quick** | 500-800 | "What is this paper about?", "Overview of X" | Title, authors, abstract, citation |
| **Targeted** | 2k-5k | "What methodology did they use?", specific questions | Relevant chunks answering question |
| **Comprehensive** | 8k-15k | "Summarize this paper comprehensively" | 4-aspect summary (question, methods, findings, conclusions) |
| **Full** | 10k-100k | "Extract all equations", "Get complete text" | Complete raw PDF text (expensive!) |

### Cost Optimization

```
Query Analysis
    ↓
Intent Detection
    ├─ Overview question? → Quick Mode (metadata only)
    ├─ Specific question? → Targeted Mode (semantic retrieval)
    ├─ Full understanding? → Comprehensive Mode (4-aspect orchestration)
    └─ Non-semantic task? → Full Mode (complete extraction)
```

### Multi-Aspect Orchestration (Comprehensive Mode)

```python
# Automatically asks 4 key questions:
questions = [
    "What is the research question or hypothesis?",
    "What methodology did the researchers use?",
    "What were the main findings or results?",
    "What conclusions did the authors draw?"
]
# Combines results into structured summary
```

---

## 🕸️ Tool #3: `zot_explore_graph` - Exploring Connections

**Replaces 9 legacy tools:**
- ❌ `zot_graph_search` (general graph queries)
- ❌ `zot_find_citation_chain` (Citation Chain Mode)
- ❌ `zot_find_seminal_papers` (Influence Mode)
- ❌ `zot_find_similar_papers` (Content Similarity Mode) - 🆕
- ❌ `zot_find_related_papers` (Related Papers Mode)
- ❌ `zot_find_collaborator_network` (Collaboration Mode)
- ❌ `zot_explore_concept_network` (Concept Network Mode)
- ❌ `zot_track_topic_evolution` (Temporal Mode)
- ❌ `zot_analyze_venues` (Venue Analysis Mode)

### Intent Detection & Parameter Extraction

| Intent | Extracted Parameters | Query Patterns | Selected Mode |
|--------|---------------------|----------------|---------------|
| **Citation** | paper_key | "Papers citing papers that cite X" | Citation Chain Mode (2-3 hop traversal) |
| **Influence** | field | "Find seminal/influential papers in X" | Influence Mode (PageRank analysis) |
| **Content Similarity** | paper_key | "Papers similar to X", "More like this" | Content Similarity Mode (Qdrant vector similarity) |
| **Related** | paper_key | "Papers related to X", "Connected work" | Related Papers Mode (Neo4j shared entities) |
| **Collaboration** | author | "Who collaborated with X?" | Collaboration Mode (co-authorship network) |
| **Concept** | concept | "Concepts related to X" | Concept Network Mode (multi-hop concept links) |
| **Temporal** | start_year, end_year | "Track how X evolved from 2020-2025" | Temporal Mode (evolution timeline) |
| **Venue** | field | "Top journals/conferences in X" | Venue Analysis Mode (publication ranking) |

### Nine Execution Modes

```
1. Citation Chain Mode (Neo4j)
   - 2-3 hop citation network traversal
   - Example: "Find papers citing papers that cite X"

2. Influence Mode (Neo4j PageRank)
   - Citation graph ranking analysis
   - Example: "Find seminal papers in cognitive neuroscience"

3. Content Similarity Mode (Qdrant) 🆕
   - Vector-based 'More Like This' discovery
   - Example: "Find papers similar to X", "More papers like this"
   - Note: Content-based (what the paper discusses), not graph-based

4. Related Papers Mode (Neo4j)
   - Shared entity connections
   - Example: "Papers related to X", "Connected work"
   - Note: Graph-based (citations/shared authors), not content-based

5. Collaboration Mode (Neo4j)
   - Co-authorship network
   - Example: "Who collaborated with Smith?"

6. Concept Network Mode (Neo4j)
   - Multi-hop concept relationships
   - Example: "Concepts related to attention mechanisms"

7. Temporal Mode (Neo4j)
   - Topic evolution over time
   - Example: "Track how deep learning evolved from 2015-2025"

8. Venue Analysis Mode (Neo4j)
   - Publication outlet ranking
   - Example: "Top conferences in NLP"

9. Comprehensive Mode (Multi-backend)
   - Multi-strategy execution
   - Example: "Explore everything about transformers"
```

---

## 📊 Tier 2: Unified Management Tools (🔥 HIGH PRIORITY)

**The Four Management Tools:**

| Tool | Modes | Purpose |
|------|-------|---------|
| **`zot_manage_collections`** | 6 modes | List, Create, Show Items, Add, Remove collections, Recent (library maintenance) |
| **`zot_manage_tags`** | 4 modes | List, Search, Add, Remove tags |
| **`zot_manage_notes`** | 4 modes | List Annotations, List Notes, Search, Create notes |
| **`zot_export`** | 3 modes | Markdown, BibTeX, GraphML export |

**Replaces 15 legacy tools** with natural language interface and automatic mode selection.

---

## 🔧 Tier 3: Maintenance/Utility Tools (LOW PRIORITY)

| Tool | Priority | Purpose |
|------|----------|---------|
| `zot_search_items` | 🔧 LOW | Keyword-based metadata search (fallback) |
| `zot_get_item` | 🔧 LOW | Retrieve paper metadata (fallback) |
| `zot_update_search_database` | 🔧 LOW | Rebuild semantic search index |
| `zot_get_search_database_status` | 🔧 LOW | Check index health |

---

## 🎯 Query-Driven Tool Selection Framework

### Important Principles

1. **Query-driven, not hierarchical** - Choose tools based on what the query asks for, not tier ordering
2. **No required escalation path** - Can skip directly to advanced tools if query warrants it
3. **Automatic routing** - The 3 unified tools handle most routing internally
4. **Direct requests honored** - If user explicitly requests a tool, use it

### Decision Tree

```
User Query
    ↓
┌──────────────────────────────────────────┐
│ Is it about FINDING papers?              │ → zot_search (auto-detects mode)
│ Is it about UNDERSTANDING a paper?       │ → zot_summarize (auto-detects depth)
│ Is it about EXPLORING connections?       │ → zot_explore_graph (auto-detects intent)
│ Is it about COLLECTIONS?                 │ → zot_manage_collections (auto-detects mode)
│ Is it about TAGS?                        │ → zot_manage_tags (auto-detects mode)
│ Is it about NOTES/ANNOTATIONS?           │ → zot_manage_notes (auto-detects mode)
│ Is it about EXPORTING data?              │ → zot_export (auto-detects format)
│ Is it about MAINTENANCE?                 │ → Utility tools
└──────────────────────────────────────────┘
```

---

## 📈 Complete Migration Summary

### Before: 35 Legacy Tools

**Research Tools (19):**
```
Search/Discovery (8):
- zot_semantic_search → zot_search
- zot_unified_search → zot_search
- zot_refine_search → zot_search
- zot_enhanced_semantic_search → zot_search
- zot_hybrid_vector_graph_search → zot_search
- zot_decompose_query → zot_search (Phase 0)
- zot_search_items → zot_search (Metadata Mode)
- zot_get_item → zot_summarize (Quick Mode)

Summarization (2):
- zot_ask_paper → zot_summarize
- zot_get_item_fulltext → zot_summarize

Graph/Exploration (9):
- zot_graph_search → zot_explore_graph
- zot_find_citation_chain → zot_explore_graph
- zot_find_seminal_papers → zot_explore_graph
- zot_find_similar_papers → zot_explore_graph
- zot_find_related_papers → zot_explore_graph
- zot_find_collaborator_network → zot_explore_graph
- zot_explore_concept_network → zot_explore_graph
- zot_track_topic_evolution → zot_explore_graph
- zot_analyze_venues → zot_explore_graph
```

**Management Tools (16):**
```
Collections (6):
- zot_get_collections → zot_manage_collections
- zot_create_collection → zot_manage_collections
- zot_get_collection_items → zot_manage_collections
- zot_add_to_collection → zot_manage_collections
- zot_remove_from_collection → zot_manage_collections
- zot_get_recent → zot_manage_collections

Tags (3):
- zot_get_tags → zot_manage_tags
- zot_search_by_tag → zot_manage_tags
- zot_batch_update_tags → zot_manage_tags

Notes (4):
- zot_get_annotations → zot_manage_notes
- zot_get_notes → zot_manage_notes
- zot_search_notes → zot_manage_notes
- zot_create_note → zot_manage_notes

Export (3):
- zot_export_markdown → zot_export
- zot_export_bibtex → zot_export
- zot_export_graph → zot_export
```

### After: 7 Unified Intelligent Tools

**Research Tools (3):**
```
✅ zot_search (5 execution modes)
✅ zot_summarize (4 depth modes)
✅ zot_explore_graph (9 modes: 8 graph + 1 content)
```

**Management Tools (4):**
```
✅ zot_manage_collections (6 modes)
✅ zot_manage_tags (4 modes)
✅ zot_manage_notes (4 modes)
✅ zot_export (3 modes: markdown, bibtex, graphml)
```

### Complete Benefits

- ✅ **80% total reduction in tool count** (35 → 7 unified tools)
- ✅ **Research: 84% reduction** (19 → 3 for core workflows)
- ✅ **Management: 75% reduction** (16 → 4 for organization)
- ✅ **Natural language interface** replaces function signatures
- ✅ **Automatic intent detection** (no manual mode selection)
- ✅ **Automatic decomposition** (Phase 0 multi-concept queries)
- ✅ **Smart mode selection** (optimal strategy per query)
- ✅ **Built-in quality optimization** (escalates when needed)
- ✅ **Dual-backend architecture** (Neo4j + Qdrant)
- ✅ **Consistent interface** (same query → consistent routing)
- ✅ **Compound operations** (multi-step workflows in single request)
- ✅ **Reduced cognitive load** (LLM chooses from 7 vs 35+ options)
- ✅ **Cost optimization** (uses cheapest/fastest mode that works)

---

## ✅ Validation Checklist

Current tool distribution (post-migration):

- [x] **3 tools** marked 🔥 HIGHEST PRIORITY (unified intelligent tools)
- [x] **~15 tools** marked 📊 MEDIUM PRIORITY (specialized/metadata)
- [x] **~9 tools** marked 🔧 LOW PRIORITY (maintenance/utility)
- [x] Tool Coordination Guide in server.py updated with 5 modes for zot_search
- [x] Each unified tool has automatic intent detection
- [x] Each unified tool has built-in quality assessment and escalation
- [x] Legacy tools disabled and marked DEPRECATED
- [x] Documentation updated (README.md, this file)

---

## 📝 Summary

**New Architecture**:
- **3 unified intelligent tools** handle 99% of research workflows
- **Complete consolidation** - All query-based search in zot_search (including decomposition)
- **Automatic routing** based on query intent
- **Smart mode selection** with built-in escalation
- **Quality optimization** uses cheapest/fastest mode that works

**Tool Selection**:
- **Query-driven** - Choose based on what the query asks for
- **Automatic** - The 3 unified tools handle all complexity internally
- **Direct when needed** - Can still use specialized tools for specific tasks

**Benefits**:
- **Simpler** - 84% fewer tools for core workflows (19 → 3)
- **Smarter** - Automatic intent detection, decomposition, and mode selection
- **Faster** - Uses optimal backend combination for each query
- **Better** - Quality assessment and automatic escalation
- **Unified** - Graph exploration (Neo4j) + content similarity (Qdrant) in one tool

**Impact**:
- **For Claude** - Clear 3-tool interface, reduced cognitive load
- **For Users** - More consistent, higher-quality results
- **For Developers** - Centralized logic, easier to maintain
