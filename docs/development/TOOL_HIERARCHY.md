# Agent-Zot Tool Hierarchy Audit

**Date**: 2025-10-23
**Context**: Verifying new tools (zot_unified_search, zot_refine_search, zot_decompose_query) integrate properly with existing tool orchestration

---

## 🚨 Issues Found

### **Critical Issue #1: Tool Coordination Guide Outdated**

**Location**: `src/agent_zot/core/server.py` lines 138-220

**Problem**: The Tool Coordination Guide does NOT mention the three new advanced search tools:
- `zot_unified_search` (RRF multi-backend)
- `zot_refine_search` (iterative refinement)
- `zot_decompose_query` (query decomposition)

**Impact**:
- Claude has no guidance on when to use these new tools
- No integration with the Level 1/2/3 search pattern framework
- Unclear relationship to existing tools

---

### **Critical Issue #2: Priority Misalignment**

**Current State**:
```
HIGH PRIORITY Tools (8 total):
1. zot_semantic_search       ✅ Correct (basic content discovery)
2. zot_unified_search        ⚠️  WRONG (should be MEDIUM)
3. zot_refine_search         ⚠️  WRONG (should be MEDIUM)
4. zot_decompose_query       ⚠️  WRONG (should be MEDIUM)
5. zot_ask_paper             ✅ Correct (read paper content)
6. zot_find_similar_papers   ✅ Correct (more-like-this)
7. zot_enhanced_semantic_search ✅ Correct (most precise search)
8. zot_get_item              ✅ Correct (metadata retrieval)
```

**Why This Is Wrong**:

The three new tools are marked HIGH PRIORITY, making them compete with `zot_semantic_search` as "first choice" tools. But they should be **second-tier** tools used when:
- Basic search is insufficient (refine_search)
- Need comprehensive multi-backend coverage (unified_search)
- Query has multiple distinct concepts (decompose_query)

**Intended Tool Selection Flow**:
```
User Query
    ↓
Start with HIGH PRIORITY tools (fast, simple):
    ├─ Content query? → zot_semantic_search
    ├─ Relationship query? → zot_graph_search
    ├─ Read paper? → zot_ask_paper
    └─ Get metadata? → zot_get_item
    ↓
If results insufficient, escalate to MEDIUM PRIORITY (advanced):
    ├─ Low quality results? → zot_refine_search
    ├─ Need multi-backend? → zot_unified_search
    ├─ Complex multi-concept? → zot_decompose_query
    └─ Need entity precision? → zot_enhanced_semantic_search
```

**Current Behavior**:
All 7 search tools marked HIGH PRIORITY → Claude must choose from 7 options upfront with no clear hierarchy.

---

### **Issue #3: Missing "Often Combines With" Guidance**

**Pattern in existing tools**:
```python
zot_semantic_search:
  "💡 Often combines with:
   - zot_ask_paper() to read content of found papers
   - Neo4j tools to explore relationships"

zot_graph_search:
  "💡 Often combines with zot_semantic_search to first discover papers by content"
```

**New tools MISSING this guidance**:
- `zot_unified_search` - No guidance on when to use vs zot_semantic_search
- `zot_refine_search` - No mention that quality metrics trigger this
- `zot_decompose_query` - No examples of multi-concept queries

---

## 📊 Current Tool Distribution

| Priority | Count | Backend | Tools |
|----------|-------|---------|-------|
| 🔥 HIGH | 8 | Qdrant (5), Neo4j (0), Zotero (1), Hybrid (2) | semantic_search, **unified_search**, **refine_search**, **decompose_query**, ask_paper, find_similar, enhanced_semantic, get_item |
| 📊 MEDIUM | 22 | Mostly Neo4j graph tools | graph_search, find_related_papers, citation_chain, concept_network, collaborators, etc. |
| 🔧 LOW | 9 | Maintenance/utility | update_db, search_items, export tools |

**Observation**: 5 out of 8 HIGH PRIORITY tools are Qdrant search variants. Too many competing "first choice" options.

---

## 🎯 Recommended Hierarchy (Query-Driven Guidance, Not Rules)

### **Important: This is GUIDANCE, not enforcement**
- Priority markers suggest **typical patterns**, not strict requirements
- **Query-driven selection**: Choose tools based on what the query needs, not hierarchy
- **Direct requests honored**: If user/agent explicitly requests a tool, use it (skip hierarchy)
- **Multi-tool workflows**: Complex queries often need multiple tools in combination
- **Agent autonomy**: Claude can skip directly to advanced tools if query warrants it

---

### **Tier 1: Common Starting Points (HIGH PRIORITY - 🔥)**
**Often the simplest/fastest choice for straightforward queries**

| Tool | Priority | Category | Typical Use Case | Can Skip To Advanced? |
|------|----------|----------|------------------|----------------------|
| `zot_semantic_search` | 🔥 HIGH | 🔵 PRIMARY | Simple content discovery - "papers about X" | **YES** - Skip to unified/refine/decompose if query is complex |
| `zot_ask_paper` | 🔥 HIGH | 🔵 PRIMARY | Reading specific paper - "what does paper X say about Y" | **N/A** - Different purpose |
| `zot_get_item` | 🔥 HIGH | ⚪ FALLBACK | Metadata retrieval - "who wrote X", "when was X published" | **N/A** - Different purpose |
| `zot_graph_search` | 🔥 HIGH | 🟢 PRIMARY | Relationship discovery - "who collaborated with X" | **YES** - Can combine with semantic tools |

**Rationale**: These are fast and commonly used. **But feel free to skip directly to advanced tools if the query demands it.**

---

### **Tier 2: Advanced/Specialized (MEDIUM PRIORITY - 📊)**
**Often used for complex queries or when simpler approaches insufficient**

| Tool | Priority | Category | Typical Use Case | Can Use Directly? |
|------|----------|----------|------------------|-------------------|
| `zot_refine_search` | 📊 MEDIUM | 🔵 ADVANCED | Auto-improve low-quality results | **YES** - Use directly if you know query needs refinement |
| `zot_unified_search` | 📊 MEDIUM | 🔵 ADVANCED | Comprehensive multi-backend coverage | **YES** - Use directly for complex multi-faceted queries |
| `zot_decompose_query` | 📊 MEDIUM | 🔵 ADVANCED | Multi-concept queries with AND/OR | **YES** - Use directly when you see boolean operators |
| `zot_enhanced_semantic_search` | 📊 MEDIUM | 🔵 ADVANCED | Entity-level precision for concepts/methods | **YES** - Use directly when need "what methods appear in papers about X" |
| `zot_find_similar_papers` | 📊 MEDIUM | 🔵 ADVANCED | More-like-this after finding key paper | Usually needs item_key first |
| `zot_hybrid_vector_graph_search` | 📊 MEDIUM | 🔸 HYBRID | Content + relationship enrichment | **YES** - Use directly for complex queries |
| Neo4j graph tools (15+) | 📊 MEDIUM | 🟢 SECONDARY | Specialized graph analysis | **YES** - Use directly for explicit relationship queries |

**Rationale**: More complex or specialized. **Often used directly when query clearly needs advanced capabilities. No need to try simpler tools first if you know these are appropriate.**

---

### **Tier 3: Maintenance/Utility (LOW PRIORITY - 🔧)**

| Tool | Priority | Category | When to Use |
|------|----------|----------|-------------|
| `zot_search_items` | 🔧 LOW | ⚪ FALLBACK | Keyword search when don't have item keys yet |
| `zot_update_search_database` | 🔧 LOW | ⚪ FALLBACK | Rebuild search index after adding papers |
| Export tools | 🔧 LOW | ⚪ FALLBACK | Generate markdown/bibtex/graph exports |
| Collection/tag management | 🔧 LOW | ⚪ FALLBACK | Organize library |

**Rationale**: These are maintenance tasks, not research queries.

---

## 🔧 Required Fixes

### **Fix #1: Update Tool Priority Markers**

**File**: `src/agent_zot/core/server.py`

**Change**:
```python
# BEFORE (line ~374)
@mcp.tool(
    name="zot_unified_search",
    description="🔥 HIGH PRIORITY - 🔵 ADVANCED - Unified search..."

# AFTER
@mcp.tool(
    name="zot_unified_search",
    description="📊 MEDIUM PRIORITY - 🔵 ADVANCED - Unified search..."
```

**Apply to**:
- `zot_unified_search` (line ~374): 🔥 HIGH → 📊 MEDIUM
- `zot_refine_search` (line ~504): 🔥 HIGH → 📊 MEDIUM
- `zot_decompose_query` (line ~664): 🔥 HIGH → 📊 MEDIUM

---

### **Fix #2: Update Tool Coordination Guide**

**File**: `src/agent_zot/core/server.py` lines 138-220

**Add section**:
```markdown
### Advanced Search Strategies (Use when basic search insufficient)
**Secondary:** 🔵 Qdrant advanced tools
- zot_refine_search - automatic query refinement when quality is low
- zot_unified_search - merge results from Qdrant + Neo4j + Zotero API using RRF
- zot_decompose_query - break complex queries into sub-queries for better coverage

**When to escalate:**
- ✓ Initial semantic_search returned low-quality results (confidence=low, coverage<40%)
- ✓ Need comprehensive coverage across multiple backends
- ✓ Query has multiple distinct concepts (AND/OR operators)

**Search Strategy Progression:**
1. **Start**: zot_semantic_search (fast, simple)
2. **If insufficient**: Check quality metrics
   - Low quality? → zot_refine_search (auto-improve query)
   - Need more coverage? → zot_unified_search (multi-backend)
   - Multi-concept query? → zot_decompose_query (break apart)
3. **Then**: Use Neo4j tools to explore relationships between found papers
```

---

### **Fix #3: Add Cross-References in Tool Descriptions**

**zot_unified_search** should say:
```
💡 Use AFTER basic search:
✓ zot_semantic_search returned too few results
✓ Need comprehensive coverage across backends
✓ Simple search missed important papers

NOT for:
✗ First search attempt → use zot_semantic_search first
```

**zot_refine_search** should say:
```
💡 Triggered by quality metrics:
✓ After zot_semantic_search shows: confidence=low or coverage<40%
✓ Semantic search recommendation: "Consider refining your query"

NOT for:
✗ High-quality initial results → unnecessary overhead
```

**zot_decompose_query** should say:
```
💡 Pattern recognition:
✓ Query contains "AND", "OR", "and", "with", "or"
✓ Multiple distinct concepts in one query
✓ Example: "fMRI studies of memory AND aging"

NOT for:
✗ Simple queries like "neural networks" → use zot_semantic_search
✗ Queries that should stay together → "New York" shouldn't decompose
```

---

## 🎯 Updated Search Level Framework

**Extend the existing Level 1/2/3 framework**:

| Level | Tool | Backend | Precision | Speed | Use When |
|-------|------|---------|-----------|-------|----------|
| **Level 1** | `zot_semantic_search` | Qdrant | Good | Fast | Default - basic content discovery |
| **Level 1.5** | `zot_refine_search` | Qdrant | Better | Medium | Level 1 quality low, auto-improve |
| **Level 1.5** | `zot_unified_search` | Qdrant+Neo4j+API | Better | Slow | Level 1 insufficient, need coverage |
| **Level 1.5** | `zot_decompose_query` | Qdrant | Better | Medium | Multi-concept queries |
| **Level 2** | `zot_hybrid_vector_graph_search` | Qdrant+Neo4j | Good | Medium | Need content + relationships |
| **Level 3** | `zot_enhanced_semantic_search` | Qdrant+Neo4j | Best | Slow | Need chunk-level entities ⭐ MOST PRECISE |

**Rationale**: Insert new tools as "Level 1.5" - more advanced than basic search but simpler than full hybrid/enhanced.

---

## ✅ Validation Checklist

After fixes, verify:

- [ ] Only 4-5 tools marked 🔥 HIGH PRIORITY (first-choice tools)
- [ ] 3 new tools marked 📊 MEDIUM PRIORITY (second-choice)
- [ ] Tool Coordination Guide mentions all search strategies
- [ ] Each tool description includes "Often combines with" guidance
- [ ] Each tool has clear trigger conditions ("Use when...")
- [ ] Each tool has anti-patterns ("NOT for...")
- [ ] Search Level framework includes new tools
- [ ] Priority distribution is balanced: ~5 HIGH, ~25 MEDIUM, ~9 LOW

---

## 📝 Summary

**Current State**:
- 3 new tools incorrectly marked HIGH PRIORITY
- Competing with basic search as "first choice"
- No guidance in Tool Coordination Guide
- Missing cross-references and trigger conditions

**Desired State**:
- New tools marked MEDIUM PRIORITY (second-tier)
- Clear escalation path: basic → advanced → specialized
- Updated guide with search strategy progression
- Each tool has clear "when to use" and "when NOT to use"

**Impact of NOT fixing**:
- Claude confused by too many HIGH PRIORITY search options
- May use advanced/slow tools when simple search sufficient
- No clear mental model of when to escalate
- Suboptimal tool selection leading to slower queries

**Impact of fixing**:
- Clear hierarchy: try fast tools first, escalate if needed
- Better tool selection by Claude
- Faster average query time (use simple tools when appropriate)
- Explicit guidance reduces cognitive load on LLM
