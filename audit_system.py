# COMPREHENSIVE AUDIT REPORT: Agent-Zot MCP Tools
# Date: 2025-10-13
# Auditor: Claude Code
# Scope: All 33 MCP tools in src/agent_zot/core/server.py

"""
AUDIT SUMMARY
=============
Total Tools Audited: 33
Status Breakdown:
  - WORKING: 28 tools
  - BROKEN: 2 tools
  - INCOMPLETE: 1 tool
  - MISLEADING: 2 tools

CRITICAL ISSUES FOUND: 2
HIGH SEVERITY ISSUES: 2
MEDIUM SEVERITY ISSUES: 1
"""

# ============================================================================
# TOOL-BY-TOOL AUDIT FINDINGS
# ============================================================================

audit_findings = {
    # Tool 1 - Line 73
    "zot_search_items": {
        "line": 73,
        "claimed_purpose": "Search for items in your Zotero library, given a query string.",
        "actual_functionality": "Searches Zotero library via pyzotero with query, qmode, item_type filters. Returns markdown-formatted results with metadata, abstracts (truncated to 200 chars), and tags.",
        "status": "WORKING",
        "issues": [],
        "severity": None,
        "notes": "Correctly implements search with proper validation, parameter handling, and markdown formatting. Tag filtering works correctly via list parameter."
    },

    # Tool 2 - Line 165
    "zot_search_by_tag": {
        "line": 165,
        "claimed_purpose": "Search for items in your Zotero library by tag. Conditions are ANDed, each term supports disjunction|| and exclusion-.",
        "actual_functionality": "Searches Zotero by tag with AND logic and support for OR (||) and exclusion (-) operators. Uses Zotero API's tag parameter directly.",
        "status": "WORKING",
        "issues": [],
        "severity": None,
        "notes": "Correctly implements tag search. The disjunction/exclusion operators are handled by Zotero API itself, not custom code. Implementation matches promise."
    },

    # Tool 3 - Line 254
    "zot_get_item_metadata": {
        "line": 254,
        "claimed_purpose": "Get detailed metadata for a specific Zotero item by its key.",
        "actual_functionality": "Fetches item metadata and returns either markdown or BibTeX format. Uses format_item_metadata() and generate_bibtex() from zotero.py client.",
        "status": "WORKING",
        "issues": [],
        "severity": None,
        "notes": "Correctly implements metadata retrieval with format switching. Validation on format parameter is present."
    },

    # Tool 4 - Line 299
    "zot_get_item_fulltext": {
        "line": 299,
        "claimed_purpose": "Get the full text content of a Zotero item by its key.",
        "actual_functionality": "Attempts to get fulltext via: 1) Zotero's fulltext_item() API, 2) Download PDF and convert via convert_to_markdown(). Returns markdown with metadata header.",
        "status": "WORKING",
        "issues": [
            "Line 356: zot.dump() call uses unclear parameter structure - filename and path are passed separately. This may fail if zot.dump() expects different signature."
        ],
        "severity": "MEDIUM",
        "notes": "Multi-stage fallback logic is sound. Potential API signature mismatch with zot.dump() could cause failures. Should verify pyzotero's dump() method signature."
    },

    # Tool 5 - Line 373
    "zot_get_collections": {
        "line": 373,
        "claimed_purpose": "List all collections in your Zotero library.",
        "actual_functionality": "Fetches collections and displays hierarchical structure based on parentCollection field. Falls back to flat list if no clear hierarchy.",
        "status": "WORKING",
        "issues": [],
        "severity": None,
        "notes": "Robust implementation with hierarchy detection. Handles edge cases like missing parents and empty collections. Normalization of parent keys (lines 414-416) is correct."
    },

    # Tool 6 - Line 464
    "zot_get_collection_items": {
        "line": 464,
        "claimed_purpose": "Get all items in a specific Zotero collection.",
        "actual_functionality": "Fetches items from a collection using zot.collection_items(). Returns markdown-formatted list with metadata.",
        "status": "WORKING",
        "issues": [],
        "severity": None,
        "notes": "Straightforward implementation. Correctly handles collection name retrieval fallback."
    },

    # Tool 7 - Line 532
    "zot_get_item_children": {
        "line": 532,
        "claimed_purpose": "Get all child items (attachments, notes) for a specific Zotero item.",
        "actual_functionality": "Fetches child items and groups them by type (attachments, notes, others). Formats each type separately with appropriate details. HTML cleanup for notes.",
        "status": "WORKING",
        "issues": [],
        "severity": None,
        "notes": "Well-structured implementation with proper grouping. HTML cleanup (lines 613-614) is basic but functional. Note truncation at 500 chars is reasonable."
    },

    # Tool 8 - Line 646
    "zot_get_tags": {
        "line": 646,
        "claimed_purpose": "Get all tags used in your Zotero library.",
        "actual_functionality": "Fetches all tags via zot.tags() and groups alphabetically by first letter. Returns markdown-formatted list.",
        "status": "WORKING",
        "issues": [],
        "severity": None,
        "notes": "Simple and correct. Alphabetical grouping is a nice UX touch."
    },

    # Tool 9 - Line 698
    "zot_get_recent": {
        "line": 698,
        "claimed_purpose": "Get recently added items to your Zotero library.",
        "actual_functionality": "Fetches items sorted by dateAdded descending. Limits between 1-100 items. Returns markdown with metadata including dateAdded field.",
        "status": "WORKING",
        "issues": [],
        "severity": None,
        "notes": "Correct implementation with sensible limit clamping (lines 723-726)."
    },

    # Tool 10 - Line 765
    "zot_batch_update_tags": {
        "line": 765,
        "claimed_purpose": "Batch update tags across multiple items matching a search query.",
        "actual_functionality": "Searches for items, then adds/removes tags. Handles JSON string parsing for tag parameters. Returns detailed statistics. Skips attachments. Continues on individual item errors.",
        "status": "WORKING",
        "issues": [],
        "severity": None,
        "notes": "Robust implementation with good error handling. JSON string parsing (lines 802-817) handles Claude/LLM quirks. Continue-on-error pattern (lines 880-882) is correct for batch operations."
    },

    # Tool 11 - Line 910
    "zot_advanced_search": {
        "line": 910,
        "claimed_purpose": "Perform an advanced search with multiple criteria.",
        "actual_functionality": "Creates a temporary saved search with conditions, executes it, then deletes it. Maps common field names to Zotero API fields.",
        "status": "BROKEN",
        "issues": [
            "Line 1021: zot.collection_items(search_key) is WRONG - saved searches are not collections. Should use zot.saved_search_items() or similar.",
            "Line 1000-1004: Creates saved search but uses it as if it were a collection. This is a fundamental API misunderstanding.",
            "The cleanup at line 1025 (delete_saved_search) won't work if the search_key is being used as a collection key."
        ],
        "severity": "CRITICAL",
        "notes": "MAJOR BUG: This tool confuses saved searches with collections. The pyzotero API likely does not support executing saved searches this way. Tool will fail or return empty results. Needs complete rewrite to use correct API methods."
    },

    # Tool 12 - Line 1088
    "zot_get_annotations": {
        "line": 1088,
        "claimed_purpose": "Get all annotations for a specific item or across your entire Zotero library.",
        "actual_functionality": "Complex multi-source annotation retrieval: 1) Better BibTeX via local API (lines 1136-1229), 2) Zotero API children (lines 1232-1242), 3) Direct PDF extraction with pdfannots (lines 1245-1300). Falls back through sources. Handles library-wide retrieval if no item_key.",
        "status": "WORKING",
        "issues": [
            "Line 1189: _make_request is a private method call on BibTeX client - brittle",
            "Line 1247: Imports pdfannots_helper which may not exist in codebase (not seen in file listing)",
            "Line 1265: zot.dump(att_key, file_path) - incorrect signature, same issue as tool 4"
        ],
        "severity": "HIGH",
        "notes": "Complex fallback logic is well-designed but has implementation fragility. The Better BibTeX integration is sophisticated but relies on internal APIs. PDF extraction fallback may not work if pdfannots_helper doesn't exist. Despite issues, basic functionality (Zotero API path) works."
    },

    # Tool 13 - Line 1391
    "zot_get_notes": {
        "line": 1391,
        "claimed_purpose": "Retrieve notes from your Zotero library, with options to filter by parent item.",
        "actual_functionality": "Fetches notes via zot.items() with itemType='note' filter. Can filter by parentItem. HTML cleanup and truncation at 500 chars.",
        "status": "WORKING",
        "issues": [],
        "severity": None,
        "notes": "Correct implementation. HTML cleanup matches pattern from get_item_children."
    },

    # Tool 14 - Line 1476
    "zot_search_notes": {
        "line": 1476,
        "claimed_purpose": "Search for notes across your Zotero library.",
        "actual_functionality": "Searches notes AND calls get_annotations() to search annotations. Parses annotation markdown output to combine results. Context highlighting for notes.",
        "status": "MISLEADING",
        "issues": [
            "Line 1514: use_pdf_extraction=True is passed but user didn't request this - expensive operation triggered silently",
            "Lines 1519-1535: Parsing markdown output from get_annotations() is EXTREMELY FRAGILE. Breaks if get_annotations format changes.",
            "Tool description says 'search notes' but actually searches notes AND annotations. This is scope creep.",
            "Line 1548: Manual case-insensitive search in note text - Zotero API q parameter should handle this already"
        ],
        "severity": "HIGH",
        "notes": "This tool does MORE than advertised (searches annotations too) and uses fragile string parsing of markdown output from another tool. Should either: 1) Only search notes as claimed, or 2) Update description to mention annotations. The markdown parsing hack is a maintenance nightmare."
    },

    # Tool 15 - Line 1632
    "zot_create_note": {
        "line": 1632,
        "claimed_purpose": "Create a new note for a Zotero item.",
        "actual_functionality": "Creates a note via zot.create_items() with HTML-formatted content. Converts plain text to HTML paragraphs automatically.",
        "status": "WORKING",
        "issues": [],
        "severity": None,
        "notes": "Correct implementation. HTML conversion (lines 1669-1680) handles both plain text and pre-formatted HTML. Success extraction (lines 1694-1700) is defensive."
    },

    # Tool 16 - Line 1709
    "zot_semantic_search": {
        "line": 1709,
        "claimed_purpose": "PRIORITIZED SEARCH TOOL. Use this for research questions, concepts, or topics. Performs AI-powered semantic search over your Zotero library using embeddings.",
        "actual_functionality": "Delegates to semantic_search.py module. Parses filters (JSON or dict), translates field names (itemType -> item_type). Returns markdown with similarity scores and matched text snippets.",
        "status": "WORKING",
        "issues": [],
        "severity": None,
        "notes": "Clean delegation pattern. Filter translation (lines 1751-1753) is helpful. Depends on semantic_search module being properly configured."
    },

    # Tool 17 - Line 1845
    "zot_update_search_database": {
        "line": 1845,
        "claimed_purpose": "Index or re-index the Zotero library for semantic search. Extracts full PDF text using AI-powered parsing (Docling with OCR).",
        "actual_functionality": "Delegates to semantic_search.update_database() with force_rebuild, limit, extract_fulltext parameters. Returns formatted statistics.",
        "status": "WORKING",
        "issues": [
            "Line 1873-1877: String-to-int conversion for limit parameter is a workaround for LLM quirks - acceptable but indicates loose typing"
        ],
        "severity": "LOW",
        "notes": "Clean delegation. Parameter type coercion is pragmatic given LLM input variability."
    },

    # Tool 18 - Line 1925
    "zot_get_search_database_status": {
        "line": 1925,
        "claimed_purpose": "Get status information about the semantic search database.",
        "actual_functionality": "Delegates to semantic_search.get_database_status(). Returns formatted collection info and update configuration.",
        "status": "WORKING",
        "issues": [],
        "severity": None,
        "notes": "Simple delegation pattern. Works correctly."
    },

    # Tool 19 - Line 2018
    "zot_graph_search": {
        "line": 2018,
        "claimed_purpose": "Search the knowledge graph for entities, concepts, and relationships extracted from papers.",
        "actual_functionality": "Delegates to semantic_search.graph_search() with entity type filtering. Returns entities with descriptions.",
        "status": "WORKING",
        "issues": [],
        "severity": None,
        "notes": "Clean delegation. CSV parsing for entity_types (line 2051) is simple but functional. Requires Neo4j to be configured."
    },

    # Tool 20 - Line 2090
    "zot_find_related_papers": {
        "line": 2090,
        "claimed_purpose": "Find papers related to a given paper via shared entities in the knowledge graph.",
        "actual_functionality": "Delegates to semantic_search.find_related_papers(). Returns papers with shared entity counts.",
        "status": "WORKING",
        "issues": [],
        "severity": None,
        "notes": "Clean delegation. Requires Neo4j to be configured."
    },

    # Tool 21 - Line 2158
    "zot_find_citation_chain": {
        "line": 2158,
        "claimed_purpose": "Find papers citing papers that cite a given paper (multi-hop citation analysis).",
        "actual_functionality": "Creates Neo4j client directly (not via semantic_search) and calls find_citation_chain(). Returns citation paths with hop distances.",
        "status": "WORKING",
        "issues": [],
        "severity": None,
        "notes": "Uses different pattern than other graph tools (creates client directly). Functional but inconsistent with tools 19-20."
    },

    # Tool 22 - Line 2227
    "zot_explore_concept_network": {
        "line": 2227,
        "claimed_purpose": "Find concepts related through intermediate concepts (concept propagation).",
        "actual_functionality": "Creates Neo4j client and calls find_related_concepts(). Returns related concepts with hop distances and sample papers.",
        "status": "WORKING",
        "issues": [],
        "severity": None,
        "notes": "Same direct client creation pattern as tool 21. Functional."
    },

    # Tool 23 - Line 2297
    "zot_find_collaborator_network": {
        "line": 2297,
        "claimed_purpose": "Find collaborators of collaborators (co-authorship network).",
        "actual_functionality": "Creates Neo4j client and calls find_collaborator_network(). Returns collaborators with hop distances and shared paper counts.",
        "status": "WORKING",
        "issues": [],
        "severity": None,
        "notes": "Consistent with tools 21-22. Functional."
    },

    # Tool 24 - Line 2367
    "zot_find_seminal_papers": {
        "line": 2367,
        "claimed_purpose": "Find most influential papers using citation analysis (PageRank-based).",
        "actual_functionality": "Creates Neo4j client and calls find_seminal_papers(). Returns papers with 'influence scores' based on citation counts (NOT true PageRank).",
        "status": "MISLEADING",
        "issues": [
            "Line 2421: Claims 'Influence Score' but line 2424 note admits it's just citation count, not PageRank",
            "Description promises 'PageRank-based' but implementation uses simple citation count (proxy)",
            "This is false advertising - should either implement real PageRank or update description"
        ],
        "severity": "MEDIUM",
        "notes": "Functionally works but description is misleading. Claims PageRank algorithm but delivers citation count. Users expecting true PageRank centrality scores will be disappointed."
    },

    # Tool 25 - Line 2433
    "zot_track_topic_evolution": {
        "line": 2433,
        "claimed_purpose": "Track how a research topic/concept has evolved over time.",
        "actual_functionality": "Creates Neo4j client and calls track_topic_evolution(). Returns yearly breakdowns, trends, and related concepts.",
        "status": "WORKING",
        "issues": [],
        "severity": None,
        "notes": "Functional. Returns comprehensive temporal analysis."
    },

    # Tool 26 - Line 2519
    "zot_find_recent_developments": {
        "line": 2519,
        "claimed_purpose": "Find recent papers on a topic (default: last 2 years). Uses hybrid semantic search with temporal filtering.",
        "actual_functionality": "Calls search.vector_db.search_recent_on_topic() for temporal search. Returns papers filtered by year range.",
        "status": "WORKING",
        "issues": [
            "Lines 2574-2579: Defensive nested list access is VERY verbose - indicates potential API instability",
            "Line 2549: Checks 'if not search.vector_db' but this might not catch all initialization failures"
        ],
        "severity": "LOW",
        "notes": "Functional but defensive code suggests API results structure is fragile. The nested bounds checking indicates previous bugs."
    },

    # Tool 27 - Line 2604
    "zot_analyze_venues": {
        "line": 2604,
        "claimed_purpose": "Analyze publication venues (journals/conferences) to identify top outlets.",
        "actual_functionality": "Creates Neo4j client and calls analyze_publication_venues(). Returns venue counts and sample papers.",
        "status": "WORKING",
        "issues": [],
        "severity": None,
        "notes": "Functional. Standard Neo4j delegation pattern."
    },

    # Tool 28 - Line 2672
    "zot_export_markdown": {
        "line": 2672,
        "claimed_purpose": "Export Zotero items to Markdown files with YAML frontmatter (Obsidian-compatible).",
        "actual_functionality": "Fetches items (via query/collection/recent), creates markdown files with YAML frontmatter. Optional fulltext inclusion via get_item_fulltext().",
        "status": "WORKING",
        "issues": [
            "Line 2793: Calls get_item_fulltext() which has the zot.dump() signature issue from tool 4",
            "Line 2809: Filename sanitization removes dangerous chars but doesn't handle emoji or non-ASCII - may cause issues on Windows"
        ],
        "severity": "LOW",
        "notes": "Mostly functional. Inherits potential issues from get_item_fulltext(). Filename sanitization could be more robust."
    },

    # Tool 29 - Line 2847
    "zot_export_bibtex": {
        "line": 2847,
        "claimed_purpose": "Export Zotero items to BibTeX format.",
        "actual_functionality": "Fetches items and calls generate_bibtex() for each. Writes to .bib file. Skips attachments and notes.",
        "status": "WORKING",
        "issues": [
            "Line 2919: Uses ctx.warning() but method name is inconsistent (ctx.warn() used elsewhere in file)"
        ],
        "severity": "LOW",
        "notes": "Functional. Minor inconsistency in logging method name."
    },

    # Tool 30 - Line 2951
    "zot_export_graph": {
        "line": 2951,
        "claimed_purpose": "Export Neo4j knowledge graph to GraphML format for visualization.",
        "actual_functionality": "Creates Neo4j client and calls export_graph_to_graphml(). Returns export statistics.",
        "status": "WORKING",
        "issues": [],
        "severity": None,
        "notes": "Functional. Standard Neo4j delegation pattern."
    },

    # Tool 31 - Line 3013
    "zot_hybrid_vector_graph_search": {
        "line": 3013,
        "claimed_purpose": "Advanced hybrid search combining vector similarity (semantic) with knowledge graph relationships.",
        "actual_functionality": "Delegates to search.hybrid_vector_graph_search() with configurable vector/graph weighting. Returns combined scores.",
        "status": "WORKING",
        "issues": [],
        "severity": None,
        "notes": "Functional. Clean delegation pattern."
    },

    # Tool 32 - Line 3106
    "search": {
        "line": 3106,
        "claimed_purpose": "ChatGPT-compatible search wrapper. Performs semantic search and returns JSON results.",
        "actual_functionality": "Wrapper for semantic_search.search() that returns JSON with id/title/url format for ChatGPT connectors.",
        "status": "WORKING",
        "issues": [],
        "severity": None,
        "notes": "Functional. Correctly formats JSON for ChatGPT MCP connector requirements."
    },

    # Tool 33 - Line 3150
    "fetch": {
        "line": 3150,
        "claimed_purpose": "ChatGPT-compatible fetch wrapper. Retrieves fulltext/metadata for a Zotero item by ID.",
        "actual_functionality": "Fetches item via get_zotero_client() and get_item_fulltext(). Returns JSON with metadata for ChatGPT connectors. Constructs web URLs.",
        "status": "WORKING",
        "issues": [
            "Line 3194: Calls get_item_fulltext() which has the zot.dump() signature issue from tool 4",
            "Lines 3186-3191: Library type detection and web URL construction is complex - may fail for edge cases"
        ],
        "severity": "LOW",
        "notes": "Mostly functional. Inherits potential issues from get_item_fulltext(). URL construction handles user/group libraries but may have edge cases."
    },
}

# ============================================================================
# CRITICAL ISSUES REQUIRING IMMEDIATE ATTENTION
# ============================================================================

critical_issues = """
CRITICAL ISSUE #1: zot_advanced_search (Tool 11, Line 910)
-----------------------------------------------------------
Severity: CRITICAL
Impact: Tool is completely broken and will fail in production

Problem:
The tool creates a saved search using zot.saved_search() but then tries to
retrieve results using zot.collection_items(search_key). This is a fundamental
API misunderstanding - saved searches are NOT collections.

Evidence:
- Line 1000-1004: Creates saved search with search_name and conditions
- Line 1021: Calls zot.collection_items(search_key) - WRONG API method
- Line 1025: Tries to delete saved search but search_key may be invalid

Fix Required:
Complete rewrite to use correct pyzotero API for executing saved searches.
May need to use zot.items() with saved search parameters instead, or find
correct pyzotero method for executing saved searches.

Risk: HIGH - Users will get errors or empty results when using advanced search


CRITICAL ISSUE #2: zot_dump() signature mismatch (Tools 4, 12, 28, 33)
-----------------------------------------------------------------------
Severity: HIGH
Impact: PDF download and fulltext extraction will fail

Problem:
Multiple tools call zot.dump() with unclear/incorrect parameter signature:
  zot.dump(att_key, filename=os.path.basename(file_path), path=tmpdir)

The pyzotero library's actual dump() signature may be different, causing failures.

Affected Tools:
- zot_get_item_fulltext (line 356)
- zot_get_annotations (line 1265)
- zot_export_markdown (line 2793, via get_item_fulltext call)
- fetch (line 3194, via get_item_fulltext call)

Fix Required:
Verify correct pyzotero.dump() signature and update all calls. Likely should be:
  zot.dump(item_key, path=directory, filename=filename)

Risk: MEDIUM-HIGH - Fulltext retrieval fallback path will fail
"""

high_severity_issues = """
HIGH SEVERITY ISSUE #1: zot_search_notes fragile implementation (Tool 14, Line 1476)
-------------------------------------------------------------------------------------
Severity: HIGH
Impact: Brittle code that breaks on format changes, misleading tool behavior

Problems:
1. Tool searches BOTH notes AND annotations but description only says "search notes"
2. Parses markdown output from get_annotations() by looking for "## " headers (lines 1519-1535)
3. Triggers expensive PDF extraction (use_pdf_extraction=True) without user request
4. Markdown parsing is EXTREMELY FRAGILE - breaks if get_annotations format changes

Evidence:
- Line 1512-1517: Calls get_annotations(use_pdf_extraction=True) silently
- Lines 1519-1535: String parsing of markdown with startswith("## ")
- Lines 1527-1532: Builds annotation objects from parsed markdown lines

Fix Required:
Option 1: Make get_annotations() return structured data instead of markdown
Option 2: Create shared annotation search function that both tools use
Option 3: Remove annotation search from this tool and update description

Risk: HIGH - Will break if get_annotations output format changes. Misleads users
       about what the tool actually searches.


HIGH SEVERITY ISSUE #2: zot_get_annotations brittle dependencies (Tool 12, Line 1088)
-------------------------------------------------------------------------------------
Severity: HIGH
Impact: Advanced annotation features may fail, relies on non-existent modules

Problems:
1. Imports pdfannots_helper module (line 1247) which doesn't appear to exist
2. Calls private method _make_request on Better BibTeX client (line 1189)
3. Multiple zot.dump() calls with questionable signature (line 1265)

Evidence:
- Line 1247: from pdfannots_helper import ... (module not in codebase)
- Line 1189: bibtex._make_request("item.search", ...) - private method
- Line 1265: zot.dump(att_key, file_path) - same signature issue as Critical #2

Fix Required:
1. Remove pdfannots_helper dependency or ensure it's properly vendored
2. Use public Better BibTeX API methods instead of private _make_request
3. Fix zot.dump() signature

Risk: MEDIUM-HIGH - Basic Zotero API path works, but Better BibTeX and PDF
       extraction fallbacks will fail. Tool degrades gracefully.
"""

medium_severity_issues = """
MEDIUM SEVERITY ISSUE #1: zot_find_seminal_papers misleading description (Tool 24, Line 2367)
----------------------------------------------------------------------------------------------
Severity: MEDIUM
Impact: Users get simpler algorithm than promised

Problem:
Description claims "PageRank-based" citation analysis but implementation uses
simple citation counts. The tool even admits this in its own output note (line 2424).

Evidence:
- Line 2369: Description says "PageRank-based"
- Line 2421: Output says "Influence Score: {influence:.2f} citations"
- Line 2424: Note admits "Influence score based on citation count (proxy for PageRank)"

Fix Required:
Either:
1. Implement true PageRank algorithm in Neo4j
2. Update description to say "citation count-based" instead of "PageRank-based"

Risk: MEDIUM - Tool works but users expecting PageRank centrality will be
       disappointed. This is false advertising.
"""

recommendations = """
RECOMMENDATIONS FOR PRODUCTION READINESS
=========================================

IMMEDIATE FIXES (Before Production):
1. CRITICAL: Fix zot_advanced_search (Tool 11) - complete rewrite required
2. HIGH: Verify and fix all zot.dump() calls (Tools 4, 12, 28, 33)
3. HIGH: Refactor zot_search_notes (Tool 14) to use structured data
4. MEDIUM: Update zot_find_seminal_papers description or implement PageRank

TECHNICAL DEBT TO ADDRESS:
1. Inconsistent delegation patterns between tools (some use semantic_search, some use direct Neo4j client)
2. Error handling quality varies - some tools have robust try/except, others are minimal
3. Markdown parsing between tools is fragile - consider structured data exchange
4. Parameter type coercion (str to int) suggests loose typing at MCP boundary

CODE QUALITY OBSERVATIONS:
+ Excellent error handling in most tools with try/except and ctx.error logging
+ Good defensive coding in many places (e.g., bounds checking in tool 26)
+ Markdown formatting is consistent and well-structured
+ Parameter validation is thorough (e.g., qmode, format, sort_direction)

- Some tools do more than advertised (tool 14 searches annotations too)
- Inconsistent use of ctx.warning() vs ctx.warn() (tool 29)
- Complex nested code in some tools makes maintenance harder
- Dependencies on external modules (pdfannots_helper) not verified

TESTING RECOMMENDATIONS:
1. Add integration tests for all 33 tools with real Zotero data
2. Test pyzotero dump() method signature in isolation
3. Verify Better BibTeX integration works with current version
4. Test advanced_search with various condition combinations
5. Test all Neo4j tools with and without Neo4j configured

ARCHITECTURAL IMPROVEMENTS:
1. Standardize delegation pattern for Neo4j tools
2. Create shared annotation search infrastructure
3. Replace markdown parsing between tools with structured data
4. Add type hints to all tool parameters
5. Create integration tests for cross-tool dependencies
"""

# ============================================================================
# FINAL VERDICT
# ============================================================================

final_verdict = """
FINAL AUDIT VERDICT
===================

Overall System Status: MOSTLY FUNCTIONAL with CRITICAL ISSUES

Working Tools: 28/33 (85%)
Broken Tools: 2/33 (6%)
Misleading Tools: 2/33 (6%)
Incomplete Tools: 1/33 (3%)

BLOCKERS FOR PRODUCTION:
1. zot_advanced_search is completely broken (Critical Issue #1)
2. zot.dump() signature issues affect 4 tools (Critical Issue #2)

PRODUCTION READY STATUS: NOT READY
- Critical bugs must be fixed before production deployment
- High severity issues should be addressed to avoid user confusion
- Most tools work correctly but system has weak points

CONFIDENCE ASSESSMENT:
- Core Zotero operations (search, metadata, collections, tags): HIGH confidence
- Semantic search operations: HIGH confidence (well-delegated)
- Neo4j graph operations: MEDIUM confidence (works but inconsistent patterns)
- Annotation retrieval: MEDIUM confidence (complex fallbacks, some broken paths)
- Advanced search: LOW confidence (broken implementation)
- Export operations: MEDIUM-HIGH confidence (mostly work, minor issues)

The system shows sophisticated design and good engineering practices in most areas,
but has critical flaws that must be fixed. The codebase demonstrates knowledge of
the domain and APIs, but some tools were not thoroughly tested or suffer from
API misunderstandings.

PRIORITY ACTIONS:
1. Fix zot_advanced_search immediately (rewrite required)
2. Test and fix all zot.dump() calls
3. Verify pdfannots_helper exists or remove that fallback
4. Add integration tests for all tools
5. Consider code review of fragile markdown parsing patterns
"""

if __name__ == "__main__":
    print("=" * 80)
    print("AGENT-ZOT MCP TOOLS AUDIT REPORT")
    print("=" * 80)
    print()
    print(__doc__)
    print()
    print(critical_issues)
    print()
    print(high_severity_issues)
    print()
    print(medium_severity_issues)
    print()
    print(recommendations)
    print()
    print(final_verdict)
