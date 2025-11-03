# Architectural Decisions

**Last Updated**: November 3, 2025

This document logs all major architectural decisions made in the Agent-Zot project, including rationale and trade-offs.

---

## ADR-001: Tool Consolidation (October 2025)

**Decision**: Consolidate 35 specialized tools into 7 unified intelligent tools (80% reduction)

**Context**:
- Users faced decision paralysis with 35+ tools
- Many tools had overlapping functionality
- Manual mode selection required deep system knowledge
- Tool orchestration was complex

**Rationale**:
- Natural language intent detection replaces manual mode selection
- Single entry point per workflow (search → summarize → explore)
- Automatic backend selection based on query patterns
- Reduced cognitive load while maintaining full functionality

**Result**:
- Research tools: 19 → 3 (84% reduction)
- Management tools: 16 → 4 (75% reduction)
- Total: 35 → 7 (80% reduction)

**Trade-offs**:
- ✅ Simplified user experience
- ✅ Automatic optimization
- ⚠️ More complex implementation (pattern matching, orchestration)
- ⚠️ Legacy tools kept for manual control (marked DEPRECATED)

---

## ADR-002: Sequential Backend Execution for Comprehensive Mode (October 2025)

**Decision**: Run 3 backends sequentially (not parallel) in Comprehensive Mode

**Context**:
- Comprehensive Mode combines Qdrant + Neo4j + Zotero API
- Each backend is resource-intensive:
  - Qdrant: BGE-M3 model (~1-2GB)
  - Neo4j: Ollama LLM + BGE-M3 embeddings
  - Zotero API: Network I/O
- Parallel execution caused memory exhaustion → laptop freeze

**Rationale**:
- 1-2 backends → Parallel (fast, safe)
- 3 backends → Sequential (slower but prevents system freeze)
- Sequential execution adds ~2-4 seconds but ensures stability

**Implementation**: `run_sequential_backends()` in `unified_smart.py`

**Trade-offs**:
- ✅ System stability (no freeze)
- ✅ Safe concurrent sessions
- ⚠️ Slower comprehensive searches (~6-8s vs ~4s)
- ✅ Acceptable trade-off for reliability

---

## ADR-003: Disable Auto-Update on Server Startup (October 2025)

**Decision**: Disable automatic database update check on MCP server startup

**Context**:
- Server had 3-5 second startup delay
- Made agent-zot appear slower than other MCP servers
- Auto-update initialization was synchronous and blocking
- Imported ML models, initialized connections before every session

**Rationale**:
- Instant startup (~100ms) improves UX
- Consistent with other MCP servers
- Users control when to update (explicit command)
- No background processes during normal operation

**Trade-offs**:
- ✅ Instant server startup
- ✅ Consistent UX with other tools
- ⚠️ Manual database updates required after adding papers
- ✅ More explicit control is actually clearer

**User Action Required**:
```bash
agent-zot update-db --force-rebuild --fulltext
```

---

## ADR-004: Phase 0 Query Decomposition (October 2025)

**Decision**: Integrate query decomposition as automatic Phase 0 pre-processing in `zot_search`

**Context**:
- Multi-concept queries (AND/OR logic) previously required separate tool
- Users had to manually identify complex queries
- `zot_decompose_query` was extra step in workflow

**Rationale**:
- Automatic detection using 5 decomposition patterns
- Each sub-query gets full smart_search treatment (intent detection, backend selection, escalation)
- Parallel sub-query execution (ThreadPoolExecutor, max 5 workers)
- Weighted result merging (importance scoring: 1.0 required, 0.7 optional, 0.4-0.6 supporting)

**Implementation**: Phase 0 in `smart_search()` before Phase 1 (Intent Detection)

**Trade-offs**:
- ✅ Automatic multi-concept handling
- ✅ Recursive smart_search benefits
- ✅ Transparent to users
- ⚠️ Slight overhead for complex queries (~1-2s for decomposition)

---

## ADR-005: Dual-Backend Architecture for Graph Exploration (October 2025)

**Decision**: Integrate both Neo4j (graph) AND Qdrant (content) into single `zot_explore_graph` tool

**Context**:
- `zot_find_similar_papers` (Qdrant) and `zot_find_related_papers` (Neo4j) were separate tools
- Users confused about "similar" vs "related"
- Exploration should handle both relationship AND content-based queries

**Rationale**:
- Pattern-based disambiguation:
  - "Similar" (content) → Qdrant vector search
  - "Related" (graph) → Neo4j traversal
- Single unified exploration interface
- 9 total modes (8 Neo4j + 1 Qdrant)

**Trade-offs**:
- ✅ Clear distinction via intent detection
- ✅ Unified exploration experience
- ✅ Preserves both backend capabilities
- ⚠️ Tool must handle 2 backend types (added complexity)

---

## ADR-006: Cost Optimization via Depth Detection (October 2025)

**Decision**: Implement 4-tier depth detection in `zot_summarize` (Quick → Targeted → Comprehensive → Full)

**Context**:
- Users over-fetching (requesting full text when abstract suffices)
- Token costs vary 15-125x (Quick: 500 tokens vs Full: 100k tokens)
- Most questions answerable with targeted retrieval

**Rationale**:
- Automatic depth detection from query intent
- Quick Mode (~500-800 tokens) for overview questions
- Targeted Mode (~2-5k tokens) for specific questions
- Comprehensive Mode (~8-15k tokens) for full understanding
- Full Mode (10-100k tokens) only when explicit or non-semantic tasks

**Implementation**: Pattern-based intent detection with confidence thresholds

**Trade-offs**:
- ✅ 15-125x cost reduction for common queries
- ✅ Quality over quantity (targeted chunks > full text)
- ✅ Automatic optimization
- ⚠️ Occasional need for manual depth override

---

## ADR-007: Multi-Aspect Orchestration for Comprehensive Summaries (October 2025)

**Decision**: Comprehensive Mode automatically asks 4 key questions and combines results

**Context**:
- Users manually asking multiple questions to understand papers
- Repetitive workflow: "What's the question?" → "What's the method?" → "What are findings?"
- Inconsistent coverage (forgetting to ask about conclusions)

**Rationale**:
- Automated 4-aspect workflow:
  1. Research Question
  2. Methodology
  3. Findings
  4. Conclusions
- Each aspect: semantic search with specific question
- Retrieve top 3 chunks per aspect (limit to prevent token explosion)
- Combine all aspects with metadata into comprehensive summary

**Implementation**: `run_comprehensive_mode()` in `unified_summarize.py`

**Trade-offs**:
- ✅ Consistent coverage of key aspects
- ✅ No manual orchestration needed
- ⚠️ Fixed question set (not customizable per paper type)
- ✅ ~8-15k tokens (moderate cost for full understanding)

---

## ADR-008: Intent-Based Backend Selection (October 2025)

**Decision**: Use regex pattern matching for intent detection across all unified tools

**Context**:
- Query language indicates optimal backend
- "by Author" → metadata intent → Zotero API
- "who collaborated" → relationship intent → Neo4j
- "papers about" → semantic intent → Qdrant

**Rationale**:
- Pattern-based detection is:
  - Fast (~1ms overhead)
  - Transparent (patterns documented)
  - Maintainable (add new patterns easily)
  - Deterministic (same query → same mode)
- Confidence scoring (0.0-1.0) for pattern strength

**Alternative Considered**: LLM-based intent classification
- ❌ Slower (100-500ms)
- ❌ Token cost
- ❌ Non-deterministic
- ❌ Overkill for simple pattern matching

**Trade-offs**:
- ✅ Fast and deterministic
- ✅ No API costs
- ⚠️ Requires pattern maintenance
- ⚠️ May miss edge cases (fallback to semantic intent)

---

## ADR-009: Quality-Based Escalation (October 2025)

**Decision**: `zot_search` automatically escalates from Fast Mode → Comprehensive Mode when quality inadequate

**Context**:
- Fast Mode (Qdrant only) sometimes insufficient
- Users don't know when to use Comprehensive Mode
- Quality assessment metrics needed

**Rationale**:
- Real-time quality metrics:
  - Confidence scoring (high: min score >0.75, medium: >0.60, low: ≤0.60)
  - Coverage metrics (% results above 0.75 threshold)
- Automatic escalation when:
  - Confidence = low
  - Coverage < 50%
  - User query suggests comprehensive search

**Implementation**: Phase 5 (Quality Assessment) and Phase 6 (Escalation) in `smart_search()`

**Trade-offs**:
- ✅ Automatic quality optimization
- ✅ Users get best results without knowing modes
- ⚠️ Escalation adds ~2-4 seconds
- ✅ Only escalates when truly needed (quality-based)

---

## ADR-010: Fuzzy Collection Name Matching (October 2025)

**Decision**: Use fuzzy matching for collection names in `zot_manage_collections`

**Context**:
- Users forget exact collection names
- Case sensitivity issues
- Substring matching too strict

**Rationale**:
- Fuzzy matching with Levenshtein distance
- Case-insensitive comparison
- Supports partial matches
- Clear feedback when multiple matches found

**Trade-offs**:
- ✅ Improved UX (forgiving input)
- ✅ Reduces "collection not found" errors
- ⚠️ Potential ambiguity (resolved by showing matches)

---

## ADR-011: ZOTERO_LOCAL=true for Direct SQLite Access (Pre-October 2025)

**Decision**: Use direct SQLite access to Zotero database instead of web API

**Rationale**:
- 10x faster than Zotero Web API
- No rate limits
- Full access to metadata
- Batch processing support

**Requirements**:
- Zotero must be running locally
- Database path: `~/zotero_database/zotero.sqlite`
- WAL mode + 10-second timeout for concurrent access

**Trade-offs**:
- ✅ 10x performance improvement
- ✅ No API rate limits
- ⚠️ Requires Zotero running locally
- ⚠️ Occasional database locking (rare, handled with timeout)

---

## ADR-012: BGE-M3 Embeddings with INT8 Quantization (Pre-October 2025)

**Decision**: Use BAAI/bge-m3 embeddings with INT8 quantization

**Rationale**:
- SOTA multilingual performance (1024D dense + BM25 sparse)
- Hybrid search (dense + sparse vectors)
- INT8 quantization: 75% RAM savings, minimal accuracy loss (<1%)
- Free local embeddings (no API costs)

**Trade-offs**:
- ✅ Best-in-class accuracy
- ✅ 75% memory reduction
- ✅ No API costs
- ⚠️ ~1-2GB model size in memory

---

## ADR-013: Docling V2 for PDF Parsing (Pre-October 2025)

**Decision**: Use Docling V2 with pypdfium2 backend for PDF parsing

**Rationale**:
- Structure-preserving (maintains document hierarchy)
- CPU-only (no GPU required)
- Subprocess isolation (crash-proof)
- Fast (8 parallel workers, ~476 PDFs/hour)

**Trade-offs**:
- ✅ Robust (corrupted PDFs don't break indexing)
- ✅ Fast parallel processing
- ✅ CPU-only (no GPU dependency)
- ⚠️ ~18 seconds per PDF average

---

## Future Decisions to Document Here

When making new architectural decisions, add them using this template:

```markdown
## ADR-XXX: [Decision Title] (Date)

**Decision**: [Brief statement of decision]

**Context**: [Why was this decision needed?]

**Rationale**: [Why this approach? What alternatives considered?]

**Implementation**: [Where/how implemented]

**Trade-offs**:
- ✅ Benefits
- ⚠️ Drawbacks/limitations
- ✅ Overall assessment
```

## ADR-014: Smart Notes Methodology with Obsidian MCP (October 26, 2025)

**Decision**: Adopt Sönke Ahrens' Smart Notes methodology using Obsidian MCP instead of generic zettelkasten MCP

**Context**:
- Previous knowledge curation used zettelkasten MCP with 5 generic note types
- Lacked clear daily workflow
- No proven methodology for academic research
- Needed better integration with existing Obsidian vault

**Rationale**:
- **Proven system**: Luhmann's Zettelkasten (via Ahrens) has 30+ years validation
- **Clear workflow**: Fleeting → Literature → Permanent with daily processing cycle
- **Academic focus**: Specifically designed for research and academic writing
- **Three note types** (vs 5):
  - Fleeting: Temporary captures (1-2 days lifespan)
  - Literature: Source documentation in `Literature Notes/`
  - Permanent: Self-contained atoms in `Permanent Notes/`
- **Bottom-up organization**: Topics emerge from links, not folders
- **Atomic principle**: One note = one idea (can be combined in different contexts)
- **Written for print**: Forces synthesis in own words, not copy-paste

**Obsidian MCP Advantages**:
- Native wiki-links `[[Note Title]]` embedded in prose
- Backlinks navigation (`get_backlinks()`, `get_outgoing_links()`)
- Semantic search if vault has embeddings
- Tag-based retrieval
- Integration with user's existing vault

**Smart Notes Implementation**:
- research-knowledge-curator implements daily workflow
- research-orchestrator coordinates curation after literature discovery
- Both enforce atomic notes principle
- Both validate "write in own words" requirement

**Result**:
- Clearer methodology with established best practices
- Better integration with Obsidian ecosystem
- Natural wiki-link approach vs explicit link objects
- Daily processing cycle prevents fleeting notes from becoming stale

**Trade-offs**:
- ✅ Proven academic methodology (vs generic approach)
- ✅ Native Obsidian integration
- ✅ Simpler note types (3 vs 5)
- ✅ Bottom-up emergent topics
- ⚠️ Requires Obsidian vault setup
- ⚠️ Manual fleeting note processing (daily discipline)

**References**:
- Ahrens, S. (2017). How to Take Smart Notes
- Luhmann, N. (1981). "Kommunikation mit Zettelkästen"
- Singh et al. (2025). Agentic RAG survey - knowledge management patterns

**Update (October 26, 2025)**: Added bidirectional linking
- **Enhancement**: Added `zotero_key` field to Permanent Note frontmatter template
- **Problem solved**: Previously could go Zotero → Obsidian, but NOT Obsidian → Zotero
- **Implementation**: 3-line surgical fix across curator template and orchestrator workflow
- **Result**: Seamless navigation in both directions (item_key preserved throughout workflow)
- **Impact**: 6 months later, can click from Obsidian note directly back to original Zotero paper

---

## ADR-004: Unified Database Management Tool (November 2025)

**Decision**: Consolidate database update, backup, restore, and monitoring into one unified `zot_manage_database()` tool

**Context**:
- Users needed to manage databases across multiple interfaces:
  - CLI commands (`agent-zot update-db`, `agent-zot backup-all`)
  - Legacy MCP tools (`zot_update_search_database`, `zot_get_search_database_status`)
  - Shell scripts (`scripts/backup.py`)
  - Docker commands for Neo4j inspection
- No integrated backup/restore workflow via MCP
- Database rebuild had no safety backup mechanism
- Users requested "full control over the pipeline via the mcp server from within claude using natural language"

**Rationale**:
Following the successful pattern of 7 existing unified tools:
1. **Natural language interface**: Pattern-based intent detection (no LLM overhead)
2. **Safety-first design**: 3-tier safety model (confirmation, auto-backup, dry-run preview)
3. **Complete functionality**: All database operations in one tool (12 modes)
4. **User experience**: Consistent with other unified tools (search, summarize, explore)

**Implementation**:
- **12 operational modes**: update, test, rebuild, backup, restore, list_backups, status, inspect, statistics, retry, modified_since, cancel
- **Safety features**:
  - Rebuild/restore require `confirm=True`
  - Auto-backup before force rebuild
  - Dry-run preview before restore (shows backup details)
- **Pattern-based intent detection**: Fast, transparent, no LLM needed
- **Helper functions**: 6 functions (~500 lines) for backup, restore, inspect, statistics
- **BackupManager enhancements**: 3 new restore methods (~285 lines)

**Result**:
- 8th unified tool added to agent-zot (7 → 8)
- Tool consolidation: 37 → 8 (78% reduction)
- All database operations accessible via natural language
- Zero data loss risk (auto-backup, confirmation gates)
- ~1,100 lines of new code (including comprehensive safety checks)

**Trade-offs**:
- ✅ Single entry point for all database operations
- ✅ Safety backup before destructive operations
- ✅ Natural language interface (no command syntax to remember)
- ✅ Consistent with existing unified tool pattern
- ⚠️ Phase 4 features deferred (retry_failed, modified_since, cancel) - structured placeholders provided
- ⚠️ More complex implementation (12 modes, safety orchestration)

**User Impact**:
```python
# Before: Multiple interfaces
agent-zot update-db --force-rebuild --fulltext  # CLI
zot_update_search_database(force_rebuild=True)  # MCP (deprecated)
python scripts/backup.py backup-all              # Shell script

# After: Unified natural language
zot_manage_database("force rebuild", confirm=True)  # Auto-backup + rebuild
zot_manage_database("backup databases")              # Local + iCloud
zot_manage_database("restore from latest backup", confirm=True)  # Full restore
```

**References**:
- User request: "full control over the pipeline via the mcp server from within claude using natural language"
- ADR-001: Tool Consolidation pattern (natural language intent detection)
- ADR-003: Manual database updates (rationale for explicit control)
- `UNIFIED_DATABASE_TOOL_IMPLEMENTATION_PLAN.md`: Complete implementation spec

---

