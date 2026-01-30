# Bug Reports & Known Issues

**Last Updated**: January 30, 2026

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

### Bug #015: Content Similarity Import Error (November 11, 2025)

**Issue**: `zot_explore_graph` Content Similarity mode failing with "No module named 'agent_zot.tools'"

**Error**: `ModuleNotFoundError: No module named 'agent_zot.tools'`

**Root Cause**: Incorrect import path in `src/agent_zot/search/unified_graph.py:623`:
```python
# ❌ WRONG - module doesn't exist
from agent_zot.tools.zotero import get_item_with_fallback
```

**Fix**: Changed to correct import path (line 623):
```python
# ✅ CORRECT - function exists in server module
from agent_zot.core.server import get_item_with_fallback
```

**Status**: ✅ Fixed - Content Similarity mode now works correctly

**Verification**: Successfully returned 5 similar papers using vector similarity

---

### Bug #016: Tags List String Attribute Error (November 11, 2025)

**Issue**: `zot_manage_tags` List mode failing with "'str' object has no attribute 'get'"

**Error**: `AttributeError: 'str' object has no attribute 'get'`

**Root Cause**: Code assumed Zotero API always returns list of dicts, but it can return list of strings in `src/agent_zot/search/unified_tags.py:147-150`:
```python
# ❌ WRONG - assumes dict format
sorted_tags = sorted(tags, key=lambda x: x.get("tag", "").lower())
for tag_data in sorted_tags:
    tag = tag_data.get("tag", "")  # Crashes if tag_data is string
```

**Fix**: Added robust type checking to handle both dict and string formats (lines 146-168):
```python
# ✅ CORRECT - handles both formats
def get_tag_name(t):
    """Extract tag name from either dict or string."""
    if isinstance(t, dict):
        return t.get("tag", "").lower()
    return str(t).lower()

sorted_tags = sorted(tags, key=get_tag_name)

for tag_data in sorted_tags:
    if isinstance(tag_data, dict):
        tag = tag_data.get("tag", "")
        # Handle metadata if present
    else:
        # Handle string format
        tag = str(tag_data)
```

**Status**: ✅ Fixed - Tags List mode now handles both data formats

**Verification**: Successfully returned 2,791 tags from library

---

### Bug #017: Infinite Recursion in Query Decomposition (November 11, 2025)

**Issue**: MCP tool calls causing complete system hang with 747% CPU usage (7-8 cores maxed)

**Symptoms**:
- `agent-zot serve` process consuming 747% CPU
- System completely unresponsive
- Queries never complete
- System lag affects entire computer

**Root Cause**: Uncontrolled infinite recursion in `src/agent_zot/search/unified_smart.py`:
1. `smart_search()` calls `decompose_query()` at line 493
2. Decomposition creates sub-queries (e.g., "papers about working memory" → ["papers about working memory", "papers", "working memory"])
3. Each sub-query triggers recursive `smart_search()` call at line 506
4. **No recursion depth limit exists**
5. Sub-queries decompose further → exponential recursion → CPU spike → infinite loop

**Fix**: Added recursion depth limiting with MAX_RECURSION_DEPTH = 2 (lines 440-522):

**Change 1** - Added depth parameter to function signature:
```python
def smart_search(
    semantic_search_instance,
    query: str,
    limit: int = 10,
    force_mode: Optional[str] = None,
    _recursion_depth: int = 0  # NEW PARAMETER
) -> Dict[str, Any]:
```

**Change 2** - Added depth check before decomposition:
```python
logger.info(f"Starting smart search for: '{query}' (recursion depth: {_recursion_depth})")

# Recursion depth check to prevent infinite recursion
MAX_RECURSION_DEPTH = 2
if _recursion_depth >= MAX_RECURSION_DEPTH:
    logger.warning(f"Max recursion depth ({MAX_RECURSION_DEPTH}) reached, skipping decomposition")
    sub_queries = [{
        "query": query,
        "type": "primary",
        "importance": 1.0
    }]
else:
    # Phase 0: Query Decomposition (if multi-concept)
    logger.info("Phase 0: Checking if query should be decomposed")
    sub_queries = decompose_query(query)
```

**Change 3** - Pass incremented depth to recursive calls:
```python
future = executor.submit(
    smart_search,  # Recursive call
    semantic_search_instance,
    subquery_text,
    limit * 2,
    force_mode,
    _recursion_depth + 1  # INCREMENT DEPTH
)
```

**Status**: ✅ Fixed - Permanent recursion limiting prevents infinite loops

**Verification**:
- All test queries completed in 2-3 seconds
- CPU usage returned to normal (0-0.81%)
- No system lag
- No infinite loops

**Performance Before/After**:
- Before: 747% CPU, system hang, never completes
- After: 0% CPU idle, 2-3 second completion, no issues

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

## ✅ Recently Fixed Bugs

### Bug #018: force_mode Escalation Override (January 30, 2026)

**Issue**: When using `force_mode="fast"` or `force_mode="semantic"`, the search would still escalate to Comprehensive Mode if quality was deemed inadequate, ignoring the user's explicit mode request.

**Example**:
```python
# Requested: force semantic only
zot_search(query="dissociation trauma", force_mode="semantic")

# Actual: Escalated to Comprehensive Mode with all backends
# Mode: Comprehensive Mode (escalated)
```

**Root Cause**: Escalation logic at line 684 only checked for `force_mode != "comprehensive"`:
```python
# ❌ WRONG - escalates even when user explicitly set force_mode
if quality["needs_escalation"] and force_mode != "comprehensive" and len(backends) < 3:
```

**Fix**: Changed to only escalate when `force_mode` is None (automatic mode selection) in `src/agent_zot/search/unified_smart.py:684`:
```python
# ✅ CORRECT - respect user's explicit mode choice
if quality["needs_escalation"] and force_mode is None and len(backends) < 3:
```

**Status**: ✅ Fixed - User's explicit mode choice is now respected

---

### Bug #020: Qdrant Collection Name Not Loading from Config (January 30, 2026)

**Issue**: Search returning 0 results because `create_qdrant_client()` was using wrong collection name.

**Evidence**:
```
# Config file has:
collection_name: "zotero_library_qdrant"  (236,490 points)

# But code was using:
collection_name: "zotero_library"  (0 points - empty!)
```

**Root Cause**: `create_qdrant_client(config_path=None)` didn't load default config file, so it used hardcoded default `"zotero_library"` instead of configured `"zotero_library_qdrant"`.

**Fix**: Added automatic default config path loading in `src/agent_zot/clients/qdrant.py:917-919`:
```python
# Use default config path if none provided
if config_path is None:
    config_path = os.path.expanduser("~/.config/agent-zot/config.json")
```

**Status**: ✅ Fixed - Search now correctly uses configured collection with 236,490 indexed chunks

**Impact**: This was a **CRITICAL** bug that made ALL semantic searches return 0 results when initialized without explicit config path.

---

### Bug #021: Attachment→Parent Linkage Broken (January 30, 2026)

**Issue**: Semantic search returns PDF attachment metadata instead of parent paper metadata, resulting in missing authors, abstracts, and DOIs.

**Evidence**:
```python
# Search returns attachment (PDF file):
Item Key: NVLYYB7P
Type: attachment
Authors: No authors listed  ← Missing!

# But parent journalArticle has full metadata:
Item Key: UESRZPID
Type: journalArticle
Authors: Anderson, Michael C.; Green, Collin
Journal: Nature, Volume 410...
Abstract: [full abstract]
```

**Root Cause**: Qdrant stores chunks with the attachment key (PDF), but the metadata enrichment wasn't resolving to the parent paper key via `parentItem` field in Zotero.

**Fix**: Modified `src/agent_zot/search/semantic.py:1710-1731` to always resolve parent key at query time:
```python
# CRITICAL FIX: Always resolve to actual parent paper key using database lookup
# Don't trust stored parent_item_key as it may be stale/wrong (pre-fix data)
resolved_parent = self._resolve_to_parent_key(attachment_key)
if resolved_parent and resolved_parent != attachment_key:
    zotero_key = resolved_parent
```

**Status**: ✅ Fixed - Search results now return parent paper metadata (journalArticle) with full author/title/abstract info

---

### Bug #022: RRF Ranking Weights Not Applied (January 30, 2026)

**Issue**: The `get_backend_weights()` function defined intent-based weights, but `reciprocal_rank_fusion()` ignored them completely.

**Evidence**:
```python
# Query: "Dalenberg 2012"
# Intent: metadata (confidence: 0.80)

# BEFORE FIX - Semantic result ranked higher:
#1: Gravetter (statistics textbook) - 0.0304 ← WRONG
#2: Dalenberg (correct paper) - 0.0164

# AFTER FIX - Metadata match ranked higher:
#1: Dalenberg - 0.0246 ✅ CORRECT
#2: Dalenberg - 0.0242 ✅ CORRECT
```

**Root Cause**: `reciprocal_rank_fusion()` in `src/agent_zot/search/unified.py` didn't accept or apply weight parameters.

**Fix**:
1. Modified `reciprocal_rank_fusion()` to accept `backend_weights` and `backend_names` parameters (lines 15-48)
2. Modified callers in `unified_smart.py` to pass weights from `get_backend_weights(intent)` (lines 653-665, 737-745)
3. Strengthened metadata-intent weights to 1.5 for metadata, 0.3 for semantic (line 170-177)

**Status**: ✅ Fixed - Author-year queries now correctly rank exact metadata matches above semantic near-matches

---

### Bug #023: Mixed-Case Author Names Not Matching (January 30, 2026)

**Issue**: Citation-style patterns like `^[A-Z][a-z]+\s+\d{4}$` failed to match names with internal capitals (McLaren, McDonald, DePrince).

**Evidence**:
```python
# Query: "McLaren 2012"
# Pattern: ^[A-Z][a-z]+\s+\d{4}$
# NOT MATCHED (the 'L' in McLaren is uppercase)

# Result: Detected as "semantic" intent, not "metadata"
```

**Root Cause**: Regex used `[a-z]+` which only matches lowercase letters after the initial capital.

**Fix**: Changed all citation patterns in `src/agent_zot/search/unified_smart.py:80-88` from `[a-z]+` to `[a-zA-Z]+`:
```python
# OLD:
r'^[A-Z][a-z]+\s+\d{4}$'  # Only matches "Anderson 2001"

# NEW:
r'^[A-Z][a-zA-Z]+\s+\d{4}$'  # Matches "Anderson 2001", "McLaren 2012", "McDonald 2018"
```

**Status**: ✅ Fixed - All author name styles now correctly detected as metadata intent

---

### Bug #019: Author+Year Intent Detection Missing (January 30, 2026)

**Issue**: Citation-style queries like "Anderson 2001" or "Anderson et al. 2021" were detected as semantic intent instead of metadata intent.

**Example**:
```python
# Query: "Anderson 2001"
# Detected: semantic (confidence: 0.70)  ← WRONG
# Should be: metadata (confidence: 0.80)
```

**Root Cause**: Missing regex patterns for common citation formats in `src/agent_zot/search/unified_smart.py:78-86`

**Fix**: Added 8 new citation-style patterns:
```python
metadata_patterns = [
    # NEW: Citation-style patterns (Author Year format)
    r'^[A-Z][a-z]+\s+\d{4}$',                          # "Anderson 2001"
    r'^[A-Z][a-z]+\s+(et\s+al\.?)\s*\d{4}$',           # "Anderson et al. 2001"
    r'^[A-Z][a-z]+\s+(et\s+al\.?)\s*,?\s*\d{4}$',      # "Anderson et al, 2001"
    r'^[A-Z][a-z]+\s+&\s+[A-Z][a-z]+\s+\d{4}$',        # "Anderson & Green 2001"
    r'^[A-Z][a-z]+\s+and\s+[A-Z][a-z]+\s+\d{4}$',      # "Anderson and Green 2001"
    r'^[A-Z][a-z]+,?\s+[A-Z][a-z]+,?\s+(&|and)\s+[A-Z][a-z]+\s+\d{4}$',  # "Anderson, Green, & Smith 2001"
    r'^[A-Z][a-z]+\s+\(\d{4}\)$',                      # "Anderson (2001)"
    r'^[A-Z][a-z]+\s+(et\s+al\.?)\s*\(\d{4}\)$',       # "Anderson et al. (2001)"
    # ... existing patterns ...
    r'\byear:\s*\d{4}\b',                              # "year: 2021" (also new)
]
```

**Status**: ✅ Fixed - Citation-style queries now correctly trigger metadata-first search

---

## 🔧 Open Issues

### Issue #001: Neo4j Citation Graph Not Linked to Papers (January 30, 2026)

**Status**: ⚠️ **Architectural Limitation**

**Observation**: Neo4j has 6,062 CITES relationships, but they're between Person/Journal/Entity nodes, NOT Paper nodes:
```
MATCH (p:Paper)-[r:CITES]->() RETURN count(r)  → 0
MATCH ()-[r:CITES]->(p:Paper) RETURN count(r)  → 0
```

**Impact**:
- `zot_explore_graph` "influence" mode returns 0.00 influence scores
- Citation chain analysis doesn't work
- Seminal paper detection fails

**Root Cause**: The LLM entity extraction creates CITES relationships between extracted entities (authors, journals) when they're mentioned together in text, but doesn't create Paper→Paper citation links.

**Technical Details**:
- The extraction prompt at line 194 says "CITES: Connect papers that cite each other (when mentioned)"
- But in practice, LLM extracts author mentions as CITES relationships
- No PDF reference parsing to build true citation graph

**Options to Fix** (Future Work):
1. **Parse reference sections** from PDFs to extract cited works, then match to Zotero library
2. **Use Semantic Scholar/OpenAlex API** to fetch citation data and create Paper→Paper links
3. **Use Zotero's "Related" field** if user has populated it
4. **Post-process extraction** to convert Person CITES to Paper CITES using AUTHORED_BY links

**Workaround**: Use `zot_search` with semantic mode instead of graph mode for discovery

---

### Issue #002: Metadata Search Slow (Zotero API Bottleneck) (January 30, 2026)

**Status**: ⚠️ **External Dependency**

**Observation**: Metadata search via Zotero API takes ~9 seconds vs 0.03 seconds for local SQLite:
```
Zotero API: 9.07s for 5 results
Local SQLite: 0.0321s for 10 results (280x faster)
```

**Impact**: Metadata-enriched and Comprehensive modes are slow due to Zotero API calls

**Root Cause**: Network latency + Zotero API server-side processing

**Options to Fix** (Future Work):
1. **Add local SQLite fallback** for metadata search (already used for item lookup)
2. **Cache metadata search results** with TTL
3. **Make metadata backend optional** with timeout-based fallback

**Current Workaround**: Use `force_mode="fast"` for time-sensitive searches

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
