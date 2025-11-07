# Implementation Tasks

**Status**: ✅ Phase 1-3 Complete (SDK Migration) | ⏳ Testing In Progress | ❌ Blocked by Connection Error

**Current Blocker**: `httpx.ConnectError: [Errno 61] Connection refused` during Graphiti SDK initialization/operation. All code is complete and merged, but cannot validate end-to-end functionality until this connection issue is resolved.

**Completed Work**:
- ✅ Infrastructure setup (config files, dependencies)
- ✅ GraphitiClient SDK migration (147 lines, async implementation)
- ✅ Metadata linking strategy (triple-redundancy item_key embedding)
- ✅ Ingestion pipeline integration (orchestrator + graphiti_ingestion.py)
- ✅ Documentation (ADR-017, GRAPHITI_METADATA_LINKING.md, CLAUDE.md updates)
- ✅ Unit tests (9 passing tests for metadata linking)
- ✅ Git integration (3 parallel worktrees merged successfully)

**Next Steps**: Debug connection refused error, then proceed with end-to-end testing and evaluation.

## 1. Infrastructure Setup
- [x] 1.1 Add Graphiti configuration section to `~/.config/agent-zot/config.json`
  - Feature flag: `graphiti.enabled: true` ✅ (changed from openai to anthropic)
  - Group ID: `graphiti.group_id: "agent-zot-discovery"` ✅
  - LLM provider: `graphiti.llm_provider: "anthropic"` ✅ (upgraded to claude-haiku-4-5)
  - Neo4j backend: `graphiti.use_neo4j: true` ✅
- [x] 1.2 Verify Graphiti MCP server connection via test query ✅
  - MCP tools available for read operations (interactive queries)
  - SDK used for write operations (daemon ingestion)
  - Validated `agent-zot-discovery` group_id isolation
- [x] 1.3 Document Graphiti setup ✅
  - Created `docs/GRAPHITI_METADATA_LINKING.md` (316 lines)
  - Created ADR-017: Dual-Schema Neo4j Architecture (188 lines)

## 2. Graphiti Client Integration (SDK Migration)
- [x] 2.1 Create `src/agent_zot/clients/graphiti_client.py` ✅
  - **Architecture Change**: Migrated from MCP wrappers to `graphiti_core` SDK
  - Class: `GraphitiClient` with SDK-based methods:
    - `add_paper_chunk()` → uses `graphiti.add_episode()` SDK call
    - `search_entities()` → uses `graphiti.search()` SDK call
    - `search_relationships()` → uses `graphiti.search()` SDK call (edges)
    - `get_paper_entities()` → retrieves entities by embedded item_key
  - Lazy initialization with `_ensure_initialized()` async method
  - AnthropicClient configuration for Claude Haiku 4.5
  - Error handling: Graceful degradation if Graphiti unavailable
  - Logging: Structured logs for extraction time, entity counts
- [x] 2.2 Add metadata linking strategy ✅
  - Triple-redundancy embedding of item_key (episode name, source_description, batch metadata)
  - Created comprehensive unit tests (9 passing tests)
  - See: `tests/test_graphiti_metadata_linking.py`
  - Test entity extraction success/failure
  - Test error handling when Graphiti offline

## 3. Graphiti Ingestion Pipeline
- [x] 3.1 Create `src/agent_zot/ingestion/graphiti_ingestion.py` ✅
  - Function: `ingest_to_graphiti(paper_key, chunks, metadata, config)`
  - Process:
    1. Check if feature flag enabled (`config.graphiti.enabled`) ✅
    2. Batch chunks (configurable, default 5 per episode) ✅
    3. Call `GraphitiClient.add_paper_chunk()` via SDK for each batch ✅
    4. Track metrics (time, cost estimate, entity count) ✅
  - Async implementation: Non-blocking Graphiti ingestion ✅
- [x] 3.2 Integrate into daemon orchestrator ✅
  - Modified `src/agent_zot/daemon/orchestrator.py`:
    - After Qdrant + Neo4j ingestion, triggers Graphiti asynchronously ✅
    - Try/except prevents Graphiti failures from blocking main pipeline ✅
    - Graceful degradation if Graphiti unavailable ✅
- [x] 3.3 Selective ingestion configurable ✅
  - Tag-based filtering available (`filter_tag` config option)
  - Currently set to `null` (all papers eligible)
  - Can enable selective ingestion for prototyping

## 4. Discovery Query Tool
- [ ] 4.1 MCP tools already available for queries ✅ (Deferred)
  - Graphiti MCP server provides: `search_memory_nodes`, `search_memory_facts`
  - Can be called directly from Claude Code
  - Custom wrapper tool (`zot_discover`) deferred to Phase 2
- [ ] 4.2 Query examples documented ✅
  - See ADR-017 for cross-schema query patterns
  - See `docs/GRAPHITI_METADATA_LINKING.md` for item_key-based queries

## 5. Cross-Validation Tooling (Deferred to Phase 2)
- [ ] 5.1 Cross-validation utilities (Phase 2)
  - Will create after successful end-to-end test
  - Compare Neo4j structured extraction vs Graphiti autonomous extraction
- [ ] 5.2 Analysis CLI command (Phase 2)
- [ ] 5.3 Visualization helper (Phase 2)

## 6. Testing & Validation
- [x] 6.1 Create test dataset ✅
  - Selected 2 test papers (C93XCB7U, H96QG37U)
  - Diversity: Prefrontal-hippocampal pathways, Fear and the brain
- [ ] 6.2 Run ingestion on test dataset ⏳ IN PROGRESS
  - Created `test_graphiti_ingestion.py` script ✅
  - Main pipeline complete (Qdrant + Neo4j) ✅
  - **Blocking Issue**: Connection refused error during Graphiti SDK initialization
  - Need to debug: Anthropic API connectivity or model configuration
- [ ] 6.3 Execute test queries (Blocked by 6.2)
  - Will use `mcp__graphiti__search_memory_nodes` to verify entities
  - Will query by item_key to validate cross-schema linking
- [ ] 6.4 Run cross-validation analysis (Phase 2)
- [ ] 6.5 Cost analysis ⏳ IN PROGRESS
  - Using Claude Haiku 4.5 (~$0.25 per 1M input tokens)
  - Target: <$0.05 per paper for entity extraction
  - Will measure actual costs after successful test

## 7. Documentation
- [x] 7.1 Create ADR-017: Graphiti Hybrid Discovery Architecture ✅
  - Created 188-line ADR in `decisions.md`
  - Documents dual-schema Neo4j architecture
  - Explains Agent-Zot (structured) vs Graphiti (autonomous) coexistence
  - Cross-schema linking via item_key metadata
  - Alternatives considered and trade-offs documented
- [x] 7.2 Update `CLAUDE.md` ✅
  - Graphiti integration status documented
  - SDK vs MCP pattern explained
  - Triple-redundancy metadata linking documented
  - Operational notes included (feature flag, configuration)
- [ ] 7.3 Update `README.md` (Deferred to Phase 2)
  - Will add after successful testing validates approach
  - README is user-facing, should wait for production-ready status
- [x] 7.4 Create comprehensive setup guide ✅
  - Created `docs/GRAPHITI_METADATA_LINKING.md` (316 lines)
  - Setup instructions and configuration options
  - Item_key embedding strategy (triple-redundancy)
  - Query patterns and examples
  - Integration with existing pipeline

## 8. Evaluation & Decision (Blocked - Pending Successful Test)
- [ ] 8.1 Compile Phase 1 results (Blocked by 6.2)
  - Cannot measure precision/recall until test completes
  - Cannot measure performance until entities extracted
  - Cannot measure cost until LLM calls succeed
  - **Blocking Issue**: Connection refused error during Graphiti SDK operations
- [ ] 8.2 Create evaluation report (Blocked by 8.1)
  - `docs/GRAPHITI_PHASE1_EVALUATION.md`
  - Success criteria assessment
  - Learnings and surprises
  - Recommendation: Proceed/Refine/Abandon
- [ ] 8.3 Present findings (Blocked by 8.2)
  - Update `progress.md` with Phase 1 milestone
  - Document in `decisions.md` if proceeding to Phase 2
- [ ] 8.4 Decision point (Blocked by 8.3)
  - [ ] Proceed to Phase 2: Selective full library ingestion
  - [ ] Refine and re-test: Improve extraction prompts
  - [ ] Abandon: Document learnings, disable feature

## 9. Cleanup (Phase 2 - Deferred Until Evaluation Complete)
- [ ] 9.1 Remove tag restriction (N/A - no restriction was added)
  - Configuration uses `filter_tag: null` (all papers eligible)
  - Can add selective filtering later if needed
- [ ] 9.2 Add user-facing controls (Phase 2)
  - `agent-zot graphiti enable` / `disable` commands
  - `agent-zot graphiti status` (entity count, cost to date)
  - Will add after successful Phase 1 evaluation
- [ ] 9.3 Add monitoring (Phase 2)
  - Track Graphiti query frequency
  - Alert on cost thresholds
  - Integration with existing daemon metrics
- [ ] 9.4 Production readiness checklist (Phase 2)
  - Error recovery tested (graceful degradation implemented)
  - Backup/restore procedures (Neo4j backups include Graphiti schema)
  - Performance under load (will test with 100+ papers in Phase 2)

## Estimated Effort

- **Phase 1 Implementation**: 8-12 hours
  - Infrastructure: 1-2 hours
  - Client integration: 2-3 hours
  - Ingestion pipeline: 2-3 hours
  - Discovery tool: 1-2 hours
  - Cross-validation: 1-2 hours
  - Testing: 1-2 hours
  - Documentation: 1-2 hours

- **Evaluation**: 2-3 hours
  - Run experiments
  - Analyze results
  - Write evaluation report

- **Total**: 10-15 hours (1-2 weeks part-time)
