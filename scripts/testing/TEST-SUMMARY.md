# Agent-Zot Testing Summary

## Testing Resources Created

### 1. Automated Backend Test
**File:** `scripts/quick-mcp-tool-test.py`

**What it tests:**
- ✅ Docker containers running (Neo4j, Qdrant)
- ✅ Qdrant connectivity and point count
- ✅ Neo4j connectivity and node count

**How to run:**
```bash
.venv/bin/python scripts/quick-mcp-tool-test.py
```

**Current status:** ✅ All 3 tests passing

---

### 2. Manual Test Checklist
**File:** `scripts/MANUAL-TEST-CHECKLIST.md`

**What it covers:**
- All 9 MCP tools
- All modes for each tool (36+ mode tests)
- Intent detection validation
- Error handling tests
- Performance benchmarks

**How to use:**
Open the file and check off each test as you run it in Claude Desktop.

---

### 3. Comprehensive Testing Guide
**File:** `docs/TESTING-GUIDE.md`

**What it includes:**
- Complete testing strategy (3-tier approach)
- Tool-by-tool test specifications
- Decision tree validation procedures
- Parameter extraction tests
- Quality escalation verification
- Performance benchmarks
- Error handling validation
- Troubleshooting guide

**How to use:**
Reference guide for understanding what to test and why.

---

## Quick Start Testing

### Step 1: Automated Backend Tests (30 seconds)

```bash
cd /Users/claudiusv.schroder/toolboxes/agent-zot
.venv/bin/python scripts/quick-mcp-tool-test.py
```

**Expected output:**
```
✅ Docker containers running
✅ Qdrant status
✅ Neo4j status
All automated tests passed!
```

---

### Step 2: Essential MCP Tool Tests (5 minutes)

Test the 3 core tools with their key modes:

**zot_search (5 modes):**
```
1. zot_search("papers about working memory", limit=3)
   → Fast Mode (Qdrant only)

2. zot_search("which methods appear in papers about attention?", limit=3)
   → Entity-enriched (Qdrant + Neo4j entities)

3. zot_search("who collaborated with Anderson?", limit=3)
   → Graph-enriched (Qdrant + Neo4j graph)

4. zot_search("papers by Anderson in 2015", limit=3)
   → Metadata-enriched (Qdrant + Zotero API)

5. zot_search("neural mechanisms", force_mode="comprehensive", limit=3)
   → Comprehensive (all backends)
```

**zot_summarize (4 modes):**
```
# First get an item_key from search results
item_key = "..." # From search results

1. zot_summarize(item_key, "What is this about?")
   → Quick Mode (metadata + abstract)

2. zot_summarize(item_key, "What methodology?")
   → Targeted Mode (semantic Q&A)

3. zot_summarize(item_key, "Summarize comprehensively")
   → Comprehensive Mode (4 aspects)

4. zot_summarize(item_key, force_mode="full")
   → Full Mode (complete text)
```

**zot_explore_graph (5 key modes):**
```
1. zot_explore_graph("Find influential papers on working memory")
   → Influence Mode (PageRank)

2. zot_explore_graph("Papers similar to X", paper_key=item_key)
   → Content Similarity (Qdrant)

3. zot_explore_graph("Who collaborated with Anderson?")
   → Collaboration Mode (Neo4j)

4. zot_explore_graph("How has attention evolved from 2010 to 2020?")
   → Temporal Mode (time analysis)

5. zot_explore_graph("Papers related to X", paper_key=item_key)
   → Related Papers (shared entities)
```

---

### Step 3: Management Tools (5 minutes)

Quick smoke test of management tools:

```
1. zot_manage_collections("list all collections")
2. zot_manage_tags("list all tags")
3. zot_manage_database("show status")
4. zot_daemon_status()
5. zot_manage_notes("show my notes", limit=5)
```

---

## Test Coverage Summary

### Backend Tests (Automated)
- ✅ 3 connectivity tests
- ✅ All passing

### MCP Tool Tests (Manual)
- 🔧 zot_search: 5 modes
- 🔧 zot_summarize: 4 modes
- 🔧 zot_explore_graph: 9 modes
- 🔧 zot_manage_collections: 6 modes
- 🔧 zot_manage_tags: 4 modes
- 🔧 zot_manage_notes: 4 modes
- 🔧 zot_export: 3 modes
- 🔧 zot_manage_database: 12 modes
- 🔧 zot_daemon_status: 1 mode

**Total: 48 mode tests across 9 tools**

### Decision Tree Tests
- ✅ Intent detection (15+ patterns)
- ✅ Parameter extraction (5+ cases)
- ✅ Quality escalation (3+ scenarios)

### Error Handling Tests
- ✅ Invalid inputs (5+ cases)
- ✅ Backend failures (3+ cases)
- ✅ Edge cases (5+ cases)

### Performance Tests
- ✅ Execution time benchmarks (10+ checks)
- ✅ Token usage validation (4 modes)

---

## Validation Criteria

### ✅ Tool Working Correctly If:

1. **Correct mode selected** based on query intent
2. **Results relevant** to the query
3. **Execution time** within expected range
4. **Error handling** graceful (no crashes)
5. **Backend integration** functioning (Qdrant, Neo4j, Zotero)
6. **Parameter extraction** accurate from natural language
7. **Quality escalation** triggers when appropriate

### ❌ Tool Needs Debugging If:

1. Wrong mode selected for query type
2. Results irrelevant or duplicate
3. Execution times exceed 2x expected
4. Crashes or unhandled exceptions
5. Backend connectivity fails
6. Parameters not extracted correctly
7. Escalation doesn't trigger when it should

---

## Current Test Status

**As of November 11, 2025:**

✅ **Backend Tests:** All passing (3/3)
- Docker containers running
- Qdrant accessible (234,153 chunks)
- Neo4j accessible (25,184 nodes)

🔧 **MCP Tool Tests:** Ready to run manually
- All 9 tools available via MCP
- Deprecated tools removed from menu
- Python caches cleared
- Package freshly installed

📋 **Test Artifacts:**
- `quick-mcp-tool-test.py` - Automated backend tests
- `MANUAL-TEST-CHECKLIST.md` - Comprehensive checklist
- `TESTING-GUIDE.md` - Complete testing guide
- `TEST-SUMMARY.md` - This file

---

## Next Steps

1. **Run automated backend test** (30 sec)
   ```bash
   .venv/bin/python scripts/quick-mcp-tool-test.py
   ```

2. **Test essential tools** in Claude Desktop (5 min)
   - zot_search (5 queries)
   - zot_summarize (4 queries)
   - zot_explore_graph (5 queries)

3. **Validate decision trees** (5 min)
   - Check mode selection is correct
   - Verify parameter extraction
   - Confirm results quality

4. **Quick smoke test management tools** (5 min)
   - Collections, tags, database, daemon status

**Total estimated time: 15-20 minutes for comprehensive validation**

---

## Troubleshooting

**If backend tests fail:**
```bash
docker ps  # Check containers running
docker restart agent-zot-neo4j agent-zot-qdrant
```

**If MCP tools not showing:**
```bash
# Restart Claude Desktop
# Or reconnect: /mcp
```

**If caching issues:**
```bash
find . -name __pycache__ -exec rm -rf {} +
pkill -f "agent-zot serve"
# Restart Claude Desktop
```

---

## Resources

- **Testing Guide:** `docs/TESTING-GUIDE.md`
- **Manual Checklist:** `scripts/MANUAL-TEST-CHECKLIST.md`
- **Quick Test:** `scripts/quick-mcp-tool-test.py`
- **Project Docs:** `CLAUDE.md`, `decisions.md`, `progress.md`
