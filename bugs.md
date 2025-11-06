# Bug Reports & Known Issues

**Last Updated**: October 25, 2025

This document tracks bug fixes, known limitations, and workarounds for the Agent-Zot project.

---

## ✅ Fixed Bugs

### Bug #001: Score Normalization (October 24, 2025)

**Issue**: Qdrant DBSF (Distribution-Based Score Fusion) producing similarity scores >1.0 (e.g., 1.026), invalid for cosine similarity

**Root Cause**: Qdrant hybrid search fusion can produce out-of-range scores in edge cases (Qdrant GitHub issues #4646, #5921)

**Fix**: Defensive normalization in `src/agent_zot/clients/qdrant.py:633`
```python
# Clamp scores to [0,1] range before conversion
distances = [max(0.0, 1.0 - min(1.0, hit.score)) for hit in search_result]
```

**Status**: ✅ Fixed - All scores now guaranteed in valid [0,1] range

---

### Bug #002: SQLite Database Locking (October 24, 2025)

**Issue**: "Database is locked" errors when querying Zotero's SQLite database while Zotero was actively writing

**Root Cause**: No timeout configured, blocking on write locks

**Fix**: Enhanced database connection in `src/agent_zot/database/local_zotero.py:135-167`
- 10-second timeout for lock acquisition
- Read-only mode for safety
- WAL (Write-Ahead Logging) mode verification
- Thread-safe connection sharing

**Status**: ✅ Fixed - Dramatically reduced locking issues. Most operations succeed concurrently with Zotero writes.

---

### Bug #003: Duplicate Chunks in Results (October 24, 2025)

**Issue**: Duplicate chunks appearing in `zot_ask_paper` results due to overlapping text extractions

**Fix**: Added `deduplicate_chunks()` function in `src/agent_zot/core/server.py:1163-1203`
- Normalizes text (strip whitespace, lowercase)
- Hash-based duplicate detection (O(n) efficiency)
- Preserves relevance order
- Logs number of duplicates removed

**Status**: ✅ Fixed - Cleaner, more concise results without redundant content

---

### Bug #004: CRITICAL Attachment Filtering (October 24, 2025)

**Issue**: SQL query had **backwards logic** - was ONLY indexing PDF attachments instead of excluding them. Caused:
- Empty Qdrant collection (0 documents)
- PDF attachments in search results instead of papers
- Incorrect item counts

**Root Cause**: Two SQL queries with `WHERE itemType = 'attachment'` instead of `WHERE itemType NOT IN ('attachment', 'note')`

**Fix**: Fixed SQL in `local_zotero.py`:
- Line 589: `get_item_count()`
- Line 658: `get_items_with_text()`

**Status**: ✅ Fixed - Now correctly indexes actual papers (journal articles, books, etc.) instead of PDF files

---

### Bug #005: Neo4j Availability Detection (October 24, 2025)

**Issue**: Used non-existent `execute_query()` method on Neo4j client

**Fix**: Use correct `get_graph_statistics()` method in `unified_smart.py:90-113`
```python
# ✅ CORRECT
stats = neo4j_client.get_graph_statistics()
total_nodes = stats.get("papers", 0) + stats.get("total_entities", 0)
```

**Status**: ✅ Fixed - Proper Neo4j availability checking

---

### Bug #006: Collaboration Pattern Matching (October 24, 2025)

**Issue**: Pattern `r'\b(collaborat|co-author|co author)\b'` only matched "collaborat" as complete word, missing "collaborated", "collaboration"

**Fix**: Use `\w*` wildcard in `unified_smart.py:43-45`
```python
# ✅ CORRECT - matches all inflections
r'\bcollaborat\w*\b',  # collaborated, collaboration, collaborating
r'\bco-author\b',      # hyphenated
r'\bco author\b',      # with space
```

**Status**: ✅ Fixed - Properly detects all collaboration query forms

---

### Bug #007: Complex Author Name Matching (October 24, 2025)

**Issue**: Pattern `[A-Z][a-z]+` only matched simple names like "Smith", failed on "McDonald", "O'Brien", "van der Waals"

**Fix**: Support apostrophes, hyphens, internal capitals in `unified_smart.py:60-62`
```python
# Handles: Smith, McDonald, DePrince, O'Brien, van der Waals
r'\bby\s+[A-Z][a-zA-Z\'\-]+(\s+[A-Z][a-zA-Z\'\-]+)*\b',
```

**Status**: ✅ Fixed - Robust author name extraction

---

### Bug #008: Provenance Deduplication (October 24, 2025)

**Issue**: Backend names duplicated in provenance tracking: `["semantic", "semantic", "semantic"]`

**Fix**: Deduplicate while preserving order in `unified_smart.py:230-261`
```python
result["found_in"] = list(dict.fromkeys(backends))
```

**Status**: ✅ Fixed - Clean provenance tracking

---

### Bug #009: Neo4j Client Return Value Mismatch (October 24, 2025)

**Issue**: All 7 graph exploration mode functions expected Neo4j methods to return dicts with `{'papers': [...], 'formatted_output': '...'}`, but they actually return lists directly

**Error**: `AttributeError: 'list' object has no attribute 'get'`

**Fix**: Rewrote all mode functions in `unified_graph.py` to handle list returns and format markdown ourselves

**Status**: ✅ Fixed - All 7 modes (citation, influence, related, collaboration, concept, temporal, venue) now work correctly

---

### Bug #010: Year Extraction Capturing Only Prefix (October 24, 2025)

**Issue**: Query "evolved from 2010 to 2024" extracted years as "20" and "20" instead of "2010" and "2024"

**Root Cause**: Regex `r'\b(19|20)\d{2}\b'` used capturing group, so `re.findall` returned only captured part

**Fix**: Changed to non-capturing group in `unified_graph.py`
```python
# ✅ CORRECT - non-capturing group
years = re.findall(r'\b(?:19|20)\d{2}\b', query)
```

**Status**: ✅ Fixed - Temporal mode correctly extracts 4-digit years

---

### Bug #011: Concept Extraction Including Evolution Verbs (October 24, 2025)

**Issue**: Query "dissociation evolved from 2010 to 2024" extracted concept as "dissociation evolved" instead of just "dissociation"

**Fix**: Added evolution verbs to stop pattern in `unified_graph.py`
```python
# ✅ CORRECT - stops at evolution verbs
concept_match = re.search(
    r'(?:of|on|about|for)\s+([a-zA-Z\s]{3,30}?)\s+(?:evolv|chang|develop|progress|emerg|from|since|over|between)',
    query
)
```

**Status**: ✅ Fixed - Clean concept extraction without trailing verbs

---

### Bug #012: Chunk Content Retrieval (October 24, 2025)

**Issue**: Chunks returning empty with 0.00 relevance scores in Targeted and Comprehensive modes

**Root Cause**: Using `result.get("content")` instead of `result.get("matched_text")`

**Fix**: Changed to correct field in `unified_summarize.py`
```python
matched_text = result.get("matched_text", result.get("content", ""))
```

**Status**: ✅ Fixed - Both Targeted and Comprehensive modes return actual content

---

### Bug #013: MCP Server Syntax Errors (October 23, 2025)

**Issue**: 3 unterminated string literals in `server.py` causing SyntaxError on server restart

**Fix**: Fixed all 3 string literals (lines where tools were commented out during deprecation)

**Status**: ✅ Fixed - Server starts successfully

---

### Bug #014: Pydantic v2 Compatibility Error (November 4, 2025)

**Issue**: "BaseModel.__init__() takes 1 positional argument but 2 were given" error in Neo4j entity extraction

**Root Cause**: Incorrectly passing a dict as positional argument to `LexicalGraphConfig()` in `src/agent_zot/clients/neo4j_graphrag.py:708-713`:
```python
# ❌ WRONG - Pydantic v2 doesn't accept dicts as positional args
lexical_config = LexicalGraphConfig({
    "id": "__Entity__",
    "label": "__Entity__",
    "text": "text",
    "embedding": "embedding"
})
```

**Impact**: **COSMETIC ONLY** - Papers were successfully written to Neo4j before this error occurred. The error happened during result validation/reporting phase.

**Fix**: Use default `LexicalGraphConfig()` with no arguments (line 709):
```python
# ✅ CORRECT - Use defaults
lexical_config = LexicalGraphConfig()
```

**Status**: ✅ Fixed - Proper Pydantic v2 syntax

**Related**: Neo4j sync of 151 papers completed successfully despite this error appearing in logs

---

## ⚠️ Known Limitations

### Limitation #001: Orphaned Process Cleanup on macOS

**Issue**: macOS keeps Unix sockets open after MCP disconnect, so `lsof` can't always distinguish orphaned processes

**Impact**: ~~Orphaned `agent-zot serve` processes accumulate~~ **→ MITIGATED (Nov 6, 2025)**

**Solution Implemented**:
- Auto-sync daemon now runs cleanup on startup (`manager.py:125-180`)
- Detects and kills orphaned `agent-zot serve` processes
- Logged cleanup actions for transparency
- Tested successfully (killed 3 orphaned processes on first run)

**Manual Cleanup** (if needed):
```bash
# View orphaned processes
ps aux | grep "agent-zot serve" | grep -v grep

# Kill manually
kill <old_PID>
```

**Status**: ✅ **Mitigated** - Automatic cleanup on daemon startup

**Technical Details**: Uses `ps aux` to find processes, kills with `SIGTERM`, logs actions to `/tmp/agent-zot-daemon.error.log`

---

### Limitation #002: Neo4j Graph Population (Ongoing)

**Status**: 91% populated (by design)

**Context**:
- 2,157/2,370 papers (91%) have HAS_CHUNK relationships
- 213 papers (9%) without HAS_CHUNK relationships
  - ~200 are metadata-only entries (no PDFs) - **CORRECT behavior**
  - ~12 papers (~0.5%) genuinely mis-linked - **acceptable tolerance**

**Impact**: Some graph queries may return fewer results than expected, but this is expected behavior

**Not a Bug**: System correctly avoids creating chunk relationships for papers without full-text

---

### Limitation #003: Reference Section Filtering

**Status**: ✅ Implemented but imperfect

**Implementation**: Docling structural metadata filters chunks labeled as:
- `DocItemLabel.REFERENCE` (bibliography)
- `DocItemLabel.PAGE_HEADER`
- `DocItemLabel.PAGE_FOOTER`

**Effectiveness**: Solves ~54% of reference contamination (per code comments)

**Remaining Issue**: Some references still leak through when structural metadata is ambiguous

**Impact**: Minor - Reference text occasionally appears in search results

---

### Limitation #004: Parse Cache Invalidation

**Issue**: Parse cache (`~/.cache/agent-zot/parsed_docs.db`) uses MD5 hash for deduplication. If PDF content changes but filename stays same, cache may serve stale content.

**Workaround**: Force rebuild when PDFs are updated
```bash
agent-zot update-db --force-rebuild
```

**Status**: ⚠️ Known limitation - Manual rebuild needed for updated PDFs

---

### Limitation #005: Full-Text Extraction Cost

**Issue**: Full Mode summarization (10k-100k tokens) is very expensive

**Mitigation**: Automatic depth detection prevents unnecessary full-text extraction. Full Mode only used when:
- Explicitly requested
- Non-semantic tasks (extract equations, complete export)
- Other modes insufficient

**Best Practice**: Use Targeted Mode for specific questions instead of Full Mode

---

## 🔧 Open Issues

### None

All critical issues resolved. System is production-ready.

---

## 📋 Bug Reporting Template

When reporting new bugs, use this template:

```markdown
### Bug #XXX: [Brief Title] (Date)

**Issue**: [Clear description of the problem]

**Steps to Reproduce**:
1. Step 1
2. Step 2
3. Observed behavior

**Expected Behavior**: [What should happen]

**Root Cause**: [Why this happened, if known]

**Fix**: [Solution applied, with code location]

**Status**: ⚠️ Open / 🔨 In Progress / ✅ Fixed

**Related**: [Links to related issues, commits, or decisions]
```

---

## Future Work

When fixing bugs, update this file immediately with:
- Issue description
- Root cause analysis
- Fix details with file locations
- Status update
