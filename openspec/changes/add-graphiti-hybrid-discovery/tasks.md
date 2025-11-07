# Implementation Tasks

## 1. Infrastructure Setup
- [ ] 1.1 Add Graphiti configuration section to `~/.config/agent-zot/config.json`
  - Feature flag: `graphiti.enabled: false` (default)
  - Group ID: `graphiti.group_id: "agent-zot-discovery"`
  - LLM provider: `graphiti.llm_provider: "openai"` (gpt-4o-mini)
  - Neo4j backend: `graphiti.use_neo4j: true`
- [ ] 1.2 Verify Graphiti MCP server connection via test query
  - Use `mcp__graphiti__search_memory_nodes` to confirm connectivity
  - Validate `agent-zot-discovery` group_id isolation
- [ ] 1.3 Document Graphiti setup in `docs/GRAPHITI_INTEGRATION.md`
  - Prerequisites, configuration, cost estimates

## 2. Graphiti Client Integration
- [ ] 2.1 Create `src/agent_zot/clients/graphiti_client.py`
  - Class: `GraphitiClient` with methods:
    - `add_paper_chunk(chunk_text, paper_key, metadata)` → wrapper for `mcp__graphiti__add_memory`
    - `search_entities(query, max_nodes)` → wrapper for `mcp__graphiti__search_memory_nodes`
    - `search_relationships(query, max_facts)` → wrapper for `mcp__graphiti__search_memory_facts`
    - `get_paper_entities(paper_key)` → retrieve all entities for a paper
  - Error handling: Graceful degradation if Graphiti unavailable
  - Logging: Structured logs for extraction time, entity counts
- [ ] 2.2 Add unit tests for `GraphitiClient` (mocking MCP calls)
  - Test entity extraction success/failure
  - Test error handling when Graphiti offline

## 3. Graphiti Ingestion Pipeline
- [ ] 3.1 Create `src/agent_zot/ingestion/graphiti_ingestion.py`
  - Function: `ingest_to_graphiti(paper_key, chunks, metadata, config)`
  - Process:
    1. Check if feature flag enabled (`config.graphiti.enabled`)
    2. Batch chunks (10-20 chunks per episode to reduce LLM calls)
    3. Call `GraphitiClient.add_paper_chunk()` for each batch
    4. Track metrics (time, cost estimate, entity count)
  - Async/parallel: Run Graphiti ingestion asynchronously (don't block Neo4j)
- [ ] 3.2 Integrate into existing ingestion orchestrator
  - Modify `src/agent_zot/ingestion/orchestrator.py`:
    - After Qdrant + Neo4j ingestion, optionally trigger Graphiti
    - Add try/except to prevent Graphiti failures from blocking main pipeline
- [ ] 3.3 Add selective ingestion logic
  - Only ingest papers with specific tags (e.g., `_graphiti_experiment`) for Phase 1
  - Limit to 10-20 papers for prototype

## 4. Discovery Query Tool
- [ ] 4.1 Create `src/agent_zot/search/discovery_search.py`
  - Function: `graphiti_discovery_search(query, limit, config)`
  - Query types:
    - "What unexpected entities appear in papers about X?"
    - "Find emergent concepts across papers"
    - "Discover cross-disciplinary connections"
  - Return format: Standardized `SearchResult` with provenance tag `source: "graphiti"`
- [ ] 4.2 Create MCP tool handler `zot_discover`
  - Location: `src/agent_zot/core/server.py`
  - Parameters: `query` (str), `limit` (int, default 10)
  - Description: "Discover emergent entities and relationships using autonomous extraction (experimental)"
  - Implementation: Call `graphiti_discovery_search()`
- [ ] 4.3 Add natural language query examples to tool docstring
  - "What concepts appear across multiple papers but aren't in my schema?"
  - "Find papers with similar entities to [paper_key]"
  - "Discover relationships between [concept A] and [concept B]"

## 5. Cross-Validation Tooling
- [ ] 5.1 Create `src/agent_zot/utils/cross_validation.py`
  - Function: `compare_extractions(paper_key, neo4j_client, graphiti_client)`
  - Compare:
    - Entities: Neo4j schema entities vs Graphiti autonomous entities
    - Relationships: Explicit (Neo4j) vs Emergent (Graphiti)
  - Output: Venn diagram data (Neo4j only, Graphiti only, Both)
- [ ] 5.2 Create analysis CLI command
  - `agent-zot analyze-extraction --paper-key ABC123 --output report.json`
  - Generates comparison report with:
    - Entity precision/recall
    - Novel discoveries (Graphiti-only entities)
    - Confirmed extractions (both systems agree)
- [ ] 5.3 Create visualization helper (optional)
  - Generate markdown summary of comparison
  - Highlight interesting discoveries

## 6. Testing & Validation
- [ ] 6.1 Create test dataset
  - Tag 10-20 papers in Zotero with `_graphiti_experiment`
  - Ensure diversity: Different fields, cross-disciplinary papers
- [ ] 6.2 Run ingestion on test dataset
  - `agent-zot update-db --tag _graphiti_experiment --graphiti`
  - Verify Graphiti entities created (check via `mcp__graphiti__search_memory_nodes`)
- [ ] 6.3 Execute test queries
  - Run 5-10 discovery queries via `zot_discover`
  - Measure: Latency, relevance, novel insights
  - Compare: Same queries via `zot_explore_graph` (Neo4j)
- [ ] 6.4 Run cross-validation analysis
  - For each test paper: `agent-zot analyze-extraction --paper-key XYZ`
  - Calculate precision/recall metrics
  - Document novel discoveries
- [ ] 6.5 Cost analysis
  - Track LLM API calls during ingestion
  - Calculate cost per paper ($0.01 target for GPT-4o-mini)
  - Extrapolate to full library (7,390 papers)

## 7. Documentation
- [ ] 7.1 Create ADR-017: Graphiti Hybrid Discovery Architecture
  - Decision: Add Graphiti as complementary discovery layer
  - Rationale: Autonomous extraction for emergent insights
  - Alternatives: Full migration (rejected), Neo4j only (current)
  - Trade-offs: Complexity vs discovery capability
- [ ] 7.2 Update `CLAUDE.md`
  - Add `zot_discover` to unified tools list
  - Document Graphiti integration status (experimental)
  - Add operational notes (feature flag, cost tracking)
- [ ] 7.3 Update `README.md`
  - Add "Hybrid Knowledge Graph (Experimental)" section
  - Explain Neo4j (precision) vs Graphiti (discovery)
  - Link to setup guide
- [ ] 7.4 Create `docs/GRAPHITI_INTEGRATION.md`
  - Setup instructions
  - Configuration options
  - Example queries
  - Cost optimization tips
  - Troubleshooting guide

## 8. Evaluation & Decision
- [ ] 8.1 Compile Phase 1 results
  - Precision: Entity extraction accuracy
  - Recall: Novel discoveries count
  - Performance: Query latency metrics
  - Cost: Actual LLM expenses
- [ ] 8.2 Create evaluation report
  - `docs/GRAPHITI_PHASE1_EVALUATION.md`
  - Success criteria assessment
  - Learnings and surprises
  - Recommendation: Proceed/Refine/Abandon
- [ ] 8.3 Present findings
  - Update `progress.md` with Phase 1 milestone
  - Document in `decisions.md` if proceeding to Phase 2
- [ ] 8.4 Decision point
  - [ ] Proceed to Phase 2: Selective full library ingestion
  - [ ] Refine and re-test: Improve extraction prompts
  - [ ] Abandon: Document learnings, disable feature

## 9. Cleanup (If Proceeding)
- [ ] 9.1 Remove `_graphiti_experiment` tag restriction
- [ ] 9.2 Add user-facing controls
  - `agent-zot graphiti enable` / `disable` commands
  - `agent-zot graphiti status` (entity count, cost to date)
- [ ] 9.3 Add monitoring
  - Track Graphiti query frequency
  - Alert on cost thresholds
- [ ] 9.4 Production readiness checklist
  - Error recovery tested
  - Backup/restore procedures
  - Performance under load (100+ papers)

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
