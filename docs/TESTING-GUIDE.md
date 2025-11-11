# Agent-Zot Testing Guide

Complete guide for testing all agent-zot tools and validating their internal decision trees.

## Quick Start

### 1. Automated Backend Tests
```bash
.venv/bin/python scripts/testing/quick-mcp-tool-test.py
```

This validates:
- ✅ Docker containers running
- ✅ Qdrant connectivity and indexed points
- ✅ Neo4j connectivity and node count
- ✅ Backend health

### 2. Manual MCP Tool Tests

Use the checklist at `scripts/testing/MANUAL-TEST-CHECKLIST.md` to test each tool through Claude Desktop.

## Testing Strategy

### Three-Tier Approach

**Tier 1: Backend Connectivity** (Automated)
- Docker containers running
- Qdrant accessible with indexed data
- Neo4j accessible with graph data
- Zotero database readable

**Tier 2: Tool Execution** (Manual via Claude)
- Each tool callable via MCP
- Basic functionality works
- Error handling graceful

**Tier 3: Decision Tree Logic** (Manual validation)
- Intent detection selects correct mode
- Parameter extraction from natural language
- Quality escalation triggers properly
- Results are relevant and accurate

## Tool-by-Tool Testing

### 1. zot_search - Intent-Driven Search

**5 Execution Modes to Test:**

| Mode | Query Example | Expected Backend | Expected Time |
|------|--------------|------------------|---------------|
| Fast | "papers about X" | Qdrant only | ~2s |
| Entity-enriched | "which methods appear in papers about X" | Qdrant + Neo4j entities | ~4s |
| Graph-enriched | "who collaborated with X" | Qdrant + Neo4j graph | ~4s |
| Metadata-enriched | "papers by X in 2015" | Qdrant + Zotero API | ~4s |
| Comprehensive | force_mode="comprehensive" | All backends (sequential) | ~6-8s |

**Intent Detection Tests:**

```python
# Test 1: Semantic concept → Fast Mode
zot_search("papers about working memory", limit=5)
# Expected: mode_executed = "fast"

# Test 2: Entity discovery → Entity-enriched
zot_search("which methods are used in attention research?", limit=5)
# Expected: mode_executed = "entity-enriched"

# Test 3: Relationship query → Graph-enriched
zot_search("who collaborated with Michael Anderson?", limit=5)
# Expected: mode_executed = "graph-enriched"

# Test 4: Author/year filter → Metadata-enriched
zot_search("papers by Anderson published after 2010", limit=5)
# Expected: mode_executed = "metadata-enriched"

# Test 5: Force comprehensive mode
zot_search("neural mechanisms", force_mode="comprehensive", limit=5)
# Expected: mode_executed = "comprehensive"
```

**Validation Criteria:**
- ✅ Correct mode selected based on query intent
- ✅ Results relevant to query
- ✅ No duplicates in merged results (Comprehensive Mode)
- ✅ Execution time within expected range
- ✅ Provenance tracking (which backend found each result)

### 2. zot_summarize - Depth-Aware Summarization

**4 Depth Modes to Test:**

| Mode | Query Example | Token Range | Expected Time |
|------|--------------|-------------|---------------|
| Quick | "What is this about?" | 500-800 | ~1s |
| Targeted | "What methodology?" | 2k-5k | ~2-3s |
| Comprehensive | "Summarize comprehensively" | 8k-15k | ~8-10s |
| Full | force_mode="full" | 10k-100k | ~10-30s |

**Depth Detection Tests:**

```python
# First get a test item
results = zot_search("working memory", limit=1)
item_key = results["papers"][0]["key"]

# Test 1: Overview question → Quick Mode
zot_summarize(item_key, query="What is this paper about?")
# Expected: mode_executed = "quick", returns metadata + abstract

# Test 2: Specific question → Targeted Mode
zot_summarize(item_key, query="What methodology did they use?")
# Expected: mode_executed = "targeted", semantic Q&A on chunks

# Test 3: Comprehensive request → Comprehensive Mode
zot_summarize(item_key, query="Summarize this paper comprehensively")
# Expected: mode_executed = "comprehensive", 4 aspects covered

# Test 4: Force full text → Full Mode
zot_summarize(item_key, force_mode="full")
# Expected: mode_executed = "full", complete PDF text
```

**Validation Criteria:**
- ✅ Correct depth mode selected
- ✅ Token count within expected range
- ✅ Quick Mode: Metadata + abstract present
- ✅ Targeted Mode: Answers specific question
- ✅ Comprehensive Mode: All 4 aspects (question, methods, findings, conclusions)
- ✅ Full Mode: Complete text extracted

### 3. zot_explore_graph - Graph Exploration

**9 Exploration Modes to Test:**

| Mode | Query Example | Backend | Output |
|------|--------------|---------|--------|
| Citation Chain | "papers citing papers that cite X" | Neo4j multi-hop | Citation network |
| Influence | "influential papers on X" | Neo4j PageRank | Ranked by citations |
| Content Similarity | "papers similar to X" | Qdrant vectors | Similar content |
| Related Papers | "papers related to X" | Neo4j entities | Shared entities |
| Collaboration | "who collaborated with X" | Neo4j co-authorship | Author network |
| Concept Network | "concepts related to X" | Neo4j concepts | Concept graph |
| Temporal | "evolution from YEAR to YEAR" | Neo4j temporal | Timeline |
| Venue Analysis | "top journals in X" | Neo4j publications | Ranked venues |
| Comprehensive | force_mode="comprehensive" | Multiple modes | Merged analysis |

**Intent Detection Tests:**

```python
# Get test paper
results = zot_search("Anderson working memory", limit=1)
paper_key = results["papers"][0]["key"]

# Test 1: Citation chain
zot_explore_graph(
    f"Find papers citing papers that cite {paper_key}",
    paper_key=paper_key
)
# Expected: mode_executed = "citation_chain"

# Test 2: Influence analysis
zot_explore_graph("Find the most influential papers on working memory", limit=10)
# Expected: mode_executed = "influence", PageRank ranking

# Test 3: Content similarity
zot_explore_graph(f"Find papers similar to {paper_key}", paper_key=paper_key)
# Expected: mode_executed = "content_similarity", Qdrant vectors

# Test 4: Collaboration network
zot_explore_graph("Who collaborated with Anderson?", author="Anderson")
# Expected: mode_executed = "collaboration", co-author network

# Test 5: Temporal analysis
zot_explore_graph(
    "How has working memory research evolved from 2010 to 2020?",
    start_year=2010,
    end_year=2020
)
# Expected: mode_executed = "temporal", yearly trends
```

**Validation Criteria:**
- ✅ Correct exploration mode selected
- ✅ Parameter extraction (author, years, concepts)
- ✅ Results show connections/relationships
- ✅ Neo4j queries execute successfully
- ✅ Qdrant similarity works for content mode

### 4-9. Management Tools

**zot_manage_collections** (6 modes):
- List, Create, Show Items, Add, Remove, Recent

**zot_manage_tags** (4 modes):
- List, Search, Add, Remove

**zot_manage_notes** (4 modes):
- List Annotations, List Notes, Search, Create

**zot_export** (3 modes):
- Markdown, BibTeX, GraphML

**zot_manage_database** (12 modes):
- Update, Test, Rebuild, Backup, Restore, Status, etc.

**zot_daemon_status** (1 mode):
- Show daemon running state and statistics

See `scripts/testing/MANUAL-TEST-CHECKLIST.md` for detailed test cases for each.

## Decision Tree Validation

### Intent Detection Accuracy

Test that queries correctly trigger expected modes:

**zot_search Intent Patterns:**
- "papers about X" → Fast Mode
- "which X appear in papers about Y" → Entity-enriched
- "who X with Y" → Graph-enriched
- "papers by X in YEAR" → Metadata-enriched

**zot_summarize Depth Patterns:**
- "what is X" / "overview" → Quick Mode
- "what X did they use" → Targeted Mode
- "summarize comprehensively" → Comprehensive Mode
- Non-semantic tasks → Full Mode

**zot_explore_graph Strategy Patterns:**
- "citing papers" / "citation" → Citation Chain
- "influential" / "seminal" / "important" → Influence
- "similar to" / "like" → Content Similarity
- "related to" → Related Papers
- "collaborated" / "co-author" → Collaboration
- "concepts" / "themes" → Concept Network
- "evolved" / "YEAR to YEAR" → Temporal
- "top journals" / "venues" → Venue Analysis

### Parameter Extraction

Verify natural language parameter extraction:

```python
# Test author extraction
query = "papers by Anderson and Green from 2015 to 2020"
# Should extract: authors=["Anderson", "Green"], year_start=2015, year_end=2020

# Test concept extraction
query = "concepts related to memory encoding and consolidation"
# Should extract: concepts=["memory encoding", "consolidation"]

# Test year extraction
query = "how has attention research evolved from 2010 to 2020?"
# Should extract: start_year=2010, end_year=2020
```

### Quality Escalation

Test automatic mode escalation when results insufficient:

```python
# zot_search should escalate from Fast to Comprehensive if:
# - Fast Mode returns < 3 results
# - Result quality score low
# - Query complexity high

# This should trigger escalation:
zot_search("highly specific obscure query that returns few results")
# Expected: Starts Fast, escalates to Comprehensive
```

## Performance Benchmarks

Expected execution times (approximate):

**zot_search:**
- Fast Mode: < 3 seconds
- Enriched Modes: < 5 seconds
- Comprehensive Mode: < 10 seconds

**zot_summarize:**
- Quick Mode: < 2 seconds
- Targeted Mode: < 5 seconds
- Comprehensive Mode: < 12 seconds
- Full Mode: < 30 seconds

**zot_explore_graph:**
- Most modes: 1-5 seconds
- Comprehensive Mode: < 10 seconds

## Error Handling Tests

Test graceful error handling:

```python
# Invalid item_key
zot_summarize("INVALID_KEY", "test")
# Expected: Clear error message

# Backend unavailable
# Stop Neo4j container, then:
zot_search("who collaborated with Anderson?")
# Expected: Fallback to Qdrant or clear error message

# Empty query
zot_search("")
# Expected: Validation error

# No results
zot_search("xyzabc123nonexistent")
# Expected: "No results found" with helpful suggestions
```

## Continuous Integration

### Pre-Deployment Checklist

Before deploying changes:

1. ✅ Run `quick-mcp-tool-test.py` (backends)
2. ✅ Test each mode of top 3 tools (search, summarize, explore)
3. ✅ Verify intent detection with 5+ sample queries
4. ✅ Check error handling for invalid inputs
5. ✅ Validate performance benchmarks

### Regression Testing

After making changes:

1. ✅ All previous tests still pass
2. ✅ Intent detection accuracy maintained
3. ✅ No performance degradation
4. ✅ Backward compatibility preserved

## Troubleshooting

**Backend tests fail:**
- Check Docker containers: `docker ps`
- Restart containers if needed: `docker restart agent-zot-neo4j agent-zot-qdrant`

**Intent detection wrong:**
- Check unified_smart.py intent patterns
- Verify query matches expected pattern regex

**Results quality poor:**
- Check Qdrant index status: `zot_manage_database("show status")`
- Verify Neo4j data populated: ~25k nodes expected

**Performance slow:**
- Check for multiple agent-zot processes: `ps aux | grep agent-zot`
- Clear Python caches: `find . -name __pycache__ -exec rm -rf {} +`

## Summary

**Automated tests:** Backend connectivity (3 tests)
**Manual tests:** 9 tools × average 4 modes = ~36 mode tests
**Intent detection:** ~15 query patterns
**Error handling:** ~5 error cases
**Performance:** ~10 benchmark checks

**Total test coverage:** ~70 test cases across all tools and modes
