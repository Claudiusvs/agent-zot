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
| **`zot_explore_graph`** | Exploring connections | Citation/Collaboration/Concept/Temporal/Influence/Venue intent | 7 strategy modes + Comprehensive | 2-10s |

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

**Replaces 7 legacy tools:**
- ❌ `zot_graph_search` (general graph queries)
- ❌ `zot_find_related_papers` (Related Papers Mode)
- ❌ `zot_find_citation_chain` (Citation Chain Mode)
- ❌ `zot_explore_concept_network` (Concept Network Mode)
- ❌ `zot_find_collaborator_network` (Collaboration Mode)
- ❌ `zot_find_seminal_papers` (Influence Mode)
- ❌ `zot_track_topic_evolution` (Temporal Mode)
- ❌ `zot_analyze_venues` (Venue Analysis Mode)

### Intent Detection & Parameter Extraction

| Intent | Extracted Parameters | Query Patterns | Selected Mode |
|--------|---------------------|----------------|---------------|
| **Citation** | paper_key | "Papers citing papers that cite X" | Citation Chain Mode (2-3 hop traversal) |
| **Influence** | field | "Find seminal/influential papers in X" | Influence Mode (PageRank analysis) |
| **Related** | paper_key | "Papers related to X", "Connected work" | Related Papers Mode (shared entities) |
| **Collaboration** | author | "Who collaborated with X?" | Collaboration Mode (co-authorship network) |
| **Concept** | concept | "Concepts related to X" | Concept Network Mode (multi-hop concept links) |
| **Temporal** | start_year, end_year | "Track how X evolved from 2020-2025" | Temporal Mode (evolution timeline) |
| **Venue** | field | "Top journals/conferences in X" | Venue Analysis Mode (publication ranking) |

### Seven Execution Modes

```
1. Citation Chain Mode
   - 2-3 hop citation network traversal
   - Example: "Find papers citing papers that cite X"

2. Influence Mode (PageRank)
   - Citation graph ranking analysis
   - Example: "Find seminal papers in cognitive neuroscience"

3. Related Papers Mode
   - Shared entity connections
   - Example: "Papers related to X"

4. Collaboration Mode
   - Co-authorship network
   - Example: "Who collaborated with Smith?"

5. Concept Network Mode
   - Multi-hop concept relationships
   - Example: "Concepts related to attention mechanisms"

6. Temporal Mode
   - Topic evolution over time
   - Example: "Track how deep learning evolved from 2015-2025"

7. Venue Analysis Mode
   - Publication outlet ranking
   - Example: "Top conferences in NLP"

8. Comprehensive Mode
   - Multi-strategy execution
   - Example: "Explore everything about transformers"
```

---

## 📊 Tier 2: Specialized/Advanced Tools (MEDIUM PRIORITY)

### Query Decomposition

| Tool | Priority | Purpose | Use When |
|------|----------|---------|----------|
| **`zot_decompose_query`** | 📊 MEDIUM | Multi-concept boolean queries | Query has AND/OR operators, multiple concepts |

**Example**: "fMRI studies of working memory AND aging"

### Metadata & Organization

| Tool | Priority | Purpose |
|------|----------|---------|
| `zot_search_items` | 📊 MEDIUM | Keyword-based metadata search |
| `zot_get_item` | 📊 MEDIUM | Retrieve paper metadata |
| `zot_find_similar_papers` | 📊 MEDIUM | Content-based "More Like This" |
| Collection tools | 📊 MEDIUM | Create/add/remove from collections |
| Tag tools | 📊 MEDIUM | Get/update tags |
| Note tools | 📊 MEDIUM | Get/create/search notes |
| Export tools | 📊 MEDIUM | Markdown/BibTeX/GraphML export |

---

## 🔧 Tier 3: Maintenance/Utility Tools (LOW PRIORITY)

| Tool | Priority | Purpose |
|------|----------|---------|
| `zot_update_search_database` | 🔧 LOW | Rebuild semantic search index |
| `zot_get_search_database_status` | 🔧 LOW | Check index health |
| `zot_get_recent` | 🔧 LOW | Recently added items |
| `zot_batch_update_tags` | 🔧 LOW | Bulk tag operations |
| `zot_get_annotations` | 🔧 LOW | Retrieve PDF highlights |
| `zot_get_collections` | 🔧 LOW | List all collections |

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
┌─────────────────────────────────────────┐
│ Is it about FINDING papers?             │ → zot_search (auto-detects mode)
│ Is it about UNDERSTANDING a paper?      │ → zot_summarize (auto-detects depth)
│ Is it about EXPLORING connections?      │ → zot_explore_graph (auto-detects intent)
│ Is it a MULTI-CONCEPT boolean query?    │ → zot_decompose_query
│ Is it about METADATA/ORGANIZATION?      │ → Specialized metadata tools
│ Is it about MAINTENANCE?                │ → Utility tools
└─────────────────────────────────────────┘
```

---

## 📈 Migration Summary

### Before (15+ tools)

```
Search Tools (6):
- zot_semantic_search
- zot_unified_search
- zot_refine_search
- zot_enhanced_semantic_search
- zot_hybrid_vector_graph_search
- zot_decompose_query

Summarization Tools (3):
- zot_ask_paper
- zot_get_item
- zot_get_item_fulltext

Graph Tools (7):
- zot_graph_search
- zot_find_related_papers
- zot_find_citation_chain
- zot_explore_concept_network
- zot_find_collaborator_network
- zot_find_seminal_papers
- zot_track_topic_evolution
- zot_analyze_venues
```

### After (3 unified tools)

```
Finding Papers (1):
✅ zot_search (5 execution modes)

Understanding Papers (1):
✅ zot_summarize (4 depth modes)

Exploring Connections (1):
✅ zot_explore_graph (7 strategy modes + comprehensive)
```

### Benefits

- ✅ **95% reduction in tool count** (15 → 3 for core workflows)
- ✅ **Automatic intent detection** (no manual backend selection)
- ✅ **Smart mode selection** (optimal strategy for each query)
- ✅ **Built-in quality optimization** (escalates when needed)
- ✅ **Consistent interface** (same query → consistent routing)
- ✅ **Reduced cognitive load** (LLM doesn't choose from 15+ options)
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
- **3 unified intelligent tools** handle 95% of research workflows
- **Automatic routing** based on query intent
- **Smart mode selection** with built-in escalation
- **Quality optimization** uses cheapest/fastest mode that works

**Tool Selection**:
- **Query-driven** - Choose based on what the query asks for
- **Automatic** - The 3 unified tools handle most complexity internally
- **Direct when needed** - Can still use specialized tools for specific tasks

**Benefits**:
- **Simpler** - 95% fewer tools for core workflows (15 → 3)
- **Smarter** - Automatic intent detection and mode selection
- **Faster** - Uses optimal backend combination for each query
- **Better** - Quality assessment and automatic escalation

**Impact**:
- **For Claude** - Clear 3-tool interface, reduced cognitive load
- **For Users** - More consistent, higher-quality results
- **For Developers** - Centralized logic, easier to maintain
