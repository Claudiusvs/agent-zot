# Change: Add Graphiti Hybrid Discovery Layer

## Why

Agent-zot currently uses an explicit, schema-driven approach for knowledge graph construction via Neo4j GraphRAG. While this provides academic precision and powerful Cypher queries, it has limitations:

1. **Manual Schema Maintenance**: Adding new entity types requires code changes and graph rebuilds
2. **Missed Cross-Disciplinary Connections**: The explicit schema may not capture emergent relationships between disparate research fields
3. **Limited Discovery**: Users can only find relationships that were explicitly modeled in the schema
4. **No Temporal Context**: Current system doesn't track how understanding evolves over time

Graphiti's autonomous extraction capabilities can address these gaps by discovering emergent entities and relationships that weren't pre-defined in our schema, while the existing Neo4j system continues to provide precise, structured queries.

This creates a **complementary hybrid architecture**: Neo4j for precision, Graphiti for discovery.

## What Changes

### Phase 1: Prototype & Validation (This Proposal)
- **Add Graphiti ingestion pipeline** that processes Qdrant vector chunks in parallel to Neo4j extraction
- **Implement autonomous entity extraction** using Graphiti's built-in NER, coreference resolution, and LLM-powered extraction
- **Create dual-backend query routing** that directs exploratory queries to Graphiti and structured queries to Neo4j
- **Build cross-validation tooling** to compare Graphiti's autonomous extraction against Neo4j's explicit schema
- **Test on sample dataset** (10-20 papers) to evaluate:
  - Precision: Does Graphiti's NER handle academic content correctly?
  - Recall: Does it discover connections Neo4j misses?
  - Cost: What's the LLM API expense for extraction?
  - Performance: Query latency vs Neo4j Cypher

### Architecture
```
Current: Qdrant (Vector) + Neo4j (Graph) → Structured queries only

Proposed:
┌─────────────────────────────────────────────────────────────┐
│                   Hybrid Architecture                        │
├──────────────────────┬──────────────────────────────────────┤
│   Neo4j (Explicit)   │   Graphiti (Autonomous Discovery)    │
│   • Structured       │   • Emergent entities                │
│   • Academic schema  │   • Unexpected relationships         │
│   • Cypher/GDS       │   • Temporal tracking                │
│   • Fast, precise    │   • Natural language queries         │
└──────────────────────┴──────────────────────────────────────┘
             Linked via Zotero Item Keys
```

### Non-Goals (Phase 1)
- **NOT replacing Neo4j**: This is an augmentation, not a migration
- **NOT full library ingestion**: Prototype with 10-20 papers only
- **NOT production deployment**: Experimental feature behind feature flag
- **NOT personal annotations**: Separate from PAI research journal integration (future work)

## Impact

### Affected Capabilities
- **knowledge-graph** (NEW): Spec for graph-based research discovery (both Neo4j and Graphiti)
- **ingestion-pipeline** (NEW): Spec for multi-backend processing (Qdrant + Neo4j + Graphiti)
- **unified-tools** (MODIFIED): Add `zot_discover` tool for Graphiti-based exploratory queries

### Affected Code
- `src/agent_zot/clients/graphiti_client.py` (NEW): Graphiti MCP integration
- `src/agent_zot/ingestion/graphiti_ingestion.py` (NEW): Autonomous extraction pipeline
- `src/agent_zot/search/discovery_search.py` (NEW): Graphiti query orchestration
- `src/agent_zot/core/server.py` (MODIFIED): Register `zot_discover` tool
- `src/agent_zot/utils/cross_validation.py` (NEW): Compare Neo4j vs Graphiti extractions
- `~/.config/agent-zot/config.json` (MODIFIED): Add Graphiti feature flag and group_id config

### Breaking Changes
- **None**: Graphiti is opt-in via feature flag (`graphiti.enabled: false` by default)
- Existing tools and workflows remain unchanged

### Migration Path
- No migration required
- Users opt-in by setting `graphiti.enabled: true` in config
- Can disable Graphiti at any time without data loss (Neo4j remains primary)

### Success Criteria
1. **Precision**: Graphiti achieves >80% entity extraction accuracy on academic papers
2. **Discovery**: Graphiti finds ≥3 cross-disciplinary connections missed by Neo4j (in 10-20 paper sample)
3. **Performance**: Graphiti queries complete in <5 seconds
4. **Cost**: LLM extraction costs <$1 per 10 papers (using efficient models)
5. **Quality**: Cross-validation reveals complementary insights (not just duplication)

### Decision Point
After Phase 1 evaluation:
- **SUCCESS**: Proceed to Phase 2 (selective full library ingestion, personal annotations)
- **PARTIAL SUCCESS**: Refine extraction prompts, re-test
- **FAILURE**: Document learnings, abandon Graphiti integration

## Dependencies

### External
- **Graphiti MCP Server**: Already installed in PAI system (`group_id` isolation via `agent-zot-discovery`)
- **FalkorDB or Neo4j Backend**: Graphiti uses Neo4j (same instance as agent-zot) or FalkorDB
- **LLM API**: OpenAI GPT-4o-mini or Anthropic Claude for entity extraction (~$0.10 per 10 papers estimated)

### Internal
- **Qdrant Vector Database**: Must be populated with chunks (already exists)
- **Zotero Item Keys**: Primary linking mechanism between systems (already exists)
- **MCP Protocol**: Communication with Graphiti server (already configured in Claude Desktop)

## Risks & Mitigations

### Risk: Graphiti Extraction Quality
- **Risk**: Autonomous NER may produce low-quality entities for academic content
- **Mitigation**: Phase 1 prototype validates quality on sample before full deployment
- **Fallback**: Abandon if precision <80%

### Risk: Performance Overhead
- **Risk**: LLM extraction adds latency to ingestion pipeline
- **Mitigation**: Async parallel ingestion (Graphiti doesn't block Neo4j)
- **Monitoring**: Track ingestion time, alert if >2x baseline

### Risk: Cost Escalation
- **Risk**: LLM API costs for 7,390 papers could be $50-100+
- **Mitigation**: Test costs on sample first, use efficient models (GPT-4o-mini)
- **Selective Ingestion**: Only feed Graphiti "interesting" papers (user-tagged or high-citation)

### Risk: Schema Drift
- **Risk**: Graphiti's autonomous schema may diverge from Neo4j over time
- **Mitigation**: Cross-validation tool detects drift, alerts for manual reconciliation
- **Constraint**: Neo4j remains source of truth for academic metadata

### Risk: Complexity Burden
- **Risk**: Maintaining two graph systems increases operational overhead
- **Mitigation**: Feature flag allows easy disable, comprehensive documentation
- **Monitoring**: Track query distribution (Neo4j vs Graphiti), justify complexity

## Open Questions

1. **Should Graphiti use the same Neo4j instance or separate FalkorDB?**
   - Same Neo4j: Simpler infrastructure, potential schema collision
   - Separate FalkorDB: Cleaner isolation, additional container overhead
   - **Recommendation**: Start with same Neo4j using different node labels (`GraphitiEntity` vs `Paper`)

2. **How to handle entity deduplication across systems?**
   - Zotero key as primary link
   - Graphiti entities tagged with source paper key
   - Cross-validation tool matches by paper + entity name

3. **What LLM model for extraction?**
   - GPT-4o-mini: $0.15/1M input, $0.60/1M output (~$0.01 per paper)
   - Claude Haiku: $0.25/1M input, $1.25/1M output (~$0.02 per paper)
   - **Recommendation**: GPT-4o-mini for Phase 1 (lower cost)

4. **How to present dual-graph results to users?**
   - Separate tools: `zot_explore_graph` (Neo4j) vs `zot_discover` (Graphiti)
   - Merged results: Single tool with provenance tags
   - **Recommendation**: Separate tools (clearer mental model for prototype)

## Approval Checklist

- [ ] Technical feasibility validated (Graphiti MCP integration confirmed working)
- [ ] Success criteria defined and measurable
- [ ] Risk mitigations acceptable
- [ ] Phase 1 scope limited and achievable (10-20 papers, 1-2 weeks)
- [ ] Rollback plan clear (disable feature flag, no data loss)
- [ ] Documentation plan defined (ADR-017, updated CLAUDE.md)
