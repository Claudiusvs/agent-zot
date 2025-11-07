# Design: Graphiti Hybrid Discovery Architecture

## Context

Agent-zot currently uses a dual-backend architecture for research paper discovery:
- **Qdrant**: Vector database with 234,153 chunks, BGE-M3 embeddings for semantic search
- **Neo4j**: Graph database with 25,184 nodes, 134,068 relationships for citation/collaboration networks

Both backends use **explicit, schema-driven extraction**:
- Qdrant: Chunks created by RecursiveCharacterTextSplitter (deterministic)
- Neo4j: Entities extracted via Neo4j GraphRAG with predefined schema (Paper, Author, Institution, Concept, Method, etc.)

**Problem**: Explicit schemas miss emergent patterns. Cross-disciplinary connections, unexpected entity types, and evolving research narratives aren't captured.

**Opportunity**: Graphiti's autonomous extraction can discover entities and relationships without predefined schemas, complementing Neo4j's precision with exploratory discovery.

**Stakeholders**:
- **Researchers**: Primary users who benefit from serendipitous discovery
- **System Maintainer** (user): Must balance complexity with value-add
- **Agent-zot codebase**: Needs clean integration without destabilizing existing functionality

## Goals / Non-Goals

### Goals
1. **Autonomous Entity Discovery**: Extract entities from academic papers without schema constraints
2. **Cross-Disciplinary Insights**: Surface connections between disparate research fields
3. **Temporal Context Tracking**: Leverage Graphiti's bi-temporal model to track evolving understanding
4. **Minimal Disruption**: Add Graphiti as optional layer, preserve existing Neo4j/Qdrant workflows
5. **Measurable Value**: Demonstrate ≥3 novel discoveries in Phase 1 prototype (10-20 papers)

### Non-Goals (Phase 1)
1. **NOT Replacing Neo4j**: Graphiti augments, doesn't replace structured graph queries
2. **NOT Full Library Ingestion**: Prototype scope limited to 10-20 papers for validation
3. **NOT Personal Annotations**: Separate from PAI research journal integration (future Phase 2)
4. **NOT Real-Time Sync**: Ingestion triggered manually, not on every Zotero update
5. **NOT Production Feature**: Experimental, behind feature flag, opt-in only

## Decisions

### Decision 1: Hybrid Architecture (Neo4j + Graphiti)

**What**: Run both Neo4j and Graphiti in parallel, linked via Zotero item keys.

**Why**:
- **Neo4j Strengths**: Precise Cypher queries, academic schema, GDS algorithms (PageRank)
- **Graphiti Strengths**: Autonomous extraction, temporal tracking, NL queries
- **Complementary**: Different query types → different backends

**Alternatives Considered**:
1. **Replace Neo4j with Graphiti**:
   - ❌ Loses Cypher precision, GDS algorithms
   - ❌ No performance benchmarks yet
   - ❌ Risk too high for full migration

2. **Neo4j Only (Status Quo)**:
   - ❌ Misses emergent insights
   - ❌ Schema maintenance burden
   - ❌ No temporal context

3. **Graphiti Only**:
   - ❌ Academic queries need precise schema (authors, years, journals)
   - ❌ Uncertain quality of autonomous NER on academic papers

**Chosen**: Hybrid (Neo4j + Graphiti) minimizes risk, maximizes discovery potential.

---

### Decision 2: Same Neo4j Instance vs Separate FalkorDB

**What**: Use same Neo4j instance for both systems with different node labels.

**Why**:
- **Simplicity**: One database container vs two
- **Resource Efficiency**: Shared infrastructure
- **Query Integration**: Can join across systems if needed (future)

**Implementation**:
- Neo4j nodes: `:Paper`, `:Person`, `:Concept`, etc. (existing labels)
- Graphiti nodes: `:GraphitiEntity`, `:GraphitiEpisode` (new labels)
- No label collision, clean separation

**Alternatives Considered**:
1. **Separate FalkorDB**:
   - ✅ Cleaner isolation
   - ❌ Additional Docker container overhead
   - ❌ Can't easily cross-query
   - ❌ More complex backup/restore

2. **Graphiti on Different Neo4j Database**:
   - ✅ Some isolation
   - ❌ Still requires Neo4j (not simpler than same instance)

**Chosen**: Same Neo4j instance, different labels. Simplest path for Phase 1.

---

### Decision 3: Async Parallel Ingestion

**What**: Graphiti ingestion runs in parallel with Neo4j, doesn't block main pipeline.

**Why**:
- **Performance**: Don't slow down existing ingestion (already ~18s/PDF)
- **Fault Isolation**: Graphiti errors don't break Neo4j ingestion
- **Optional**: Feature flag can disable Graphiti entirely

**Implementation**:
```python
# In orchestrator.py
async def process_paper(paper_key):
    # Existing pipeline (synchronous)
    await ingest_to_qdrant(paper_key)
    await ingest_to_neo4j(paper_key)

    # New: Graphiti (async, optional)
    if config.graphiti.enabled:
        asyncio.create_task(ingest_to_graphiti(paper_key))  # Fire-and-forget
```

**Trade-offs**:
- ✅ No performance impact on existing pipeline
- ⚠️ Graphiti ingestion may lag behind Neo4j (eventual consistency)
- ✅ Acceptable for Phase 1 (not real-time critical)

---

### Decision 4: Separate Tools (`zot_discover` vs `zot_explore_graph`)

**What**: Create new `zot_discover` tool for Graphiti queries, keep `zot_explore_graph` for Neo4j.

**Why**:
- **Clear Mental Model**: Users understand which backend they're querying
- **Provenance**: Explicitly know if results come from explicit schema (Neo4j) or autonomous extraction (Graphiti)
- **Debugging**: Easier to isolate issues to specific backend

**Alternatives Considered**:
1. **Merge into single tool**:
   - ❌ Complex routing logic
   - ❌ Harder to explain to users
   - ❌ Provenance unclear in results

2. **Automatic routing based on query**:
   - ❌ Fragile pattern matching
   - ❌ Users don't know which backend was used
   - ❌ Harder to test/debug

**Chosen**: Separate tools. Clearer, simpler, more debuggable.

**Future**: If Graphiti proves valuable, could merge with smart routing in Phase 2+.

---

### Decision 5: Selective Ingestion (Tag-Based)

**What**: Only ingest papers tagged `_graphiti_experiment` in Phase 1.

**Why**:
- **Cost Control**: LLM extraction costs ~$0.01-0.02 per paper → $73-146 for full library
- **Quality Validation**: Test on curated sample before bulk ingestion
- **Focused Experiment**: 10-20 papers easier to analyze than 7,390

**Implementation**:
```python
# Only ingest if paper has experiment tag
if config.graphiti.enabled and "_graphiti_experiment" in paper_tags:
    ingest_to_graphiti(paper_key)
```

**Trade-offs**:
- ✅ Low cost for Phase 1 (<$1)
- ✅ Controlled experiment
- ⚠️ Not testing scalability (defer to Phase 2)

---

### Decision 6: LLM Provider - GPT-4o-mini

**What**: Use OpenAI GPT-4o-mini for Graphiti entity extraction (not Claude, not Ollama).

**Why**:
- **Cost**: $0.15/1M input, $0.60/1M output (~$0.01 per paper)
- **Quality**: Strong NER performance on structured text
- **Speed**: Fast enough for async ingestion
- **Availability**: Always available (vs Ollama local reliability)

**Alternatives Considered**:
1. **Claude Haiku**:
   - ❌ 2x cost ($0.02 per paper)
   - ✅ Potentially better reasoning
   - **Decision**: Try GPT-4o-mini first, switch if quality issues

2. **Ollama (Mistral 7B)**:
   - ✅ Free (local)
   - ❌ Unreliable (crashes, slow)
   - ❌ Lower quality NER than GPT-4
   - **Decision**: Not for Phase 1 (prioritize quality)

**Chosen**: GPT-4o-mini. Best cost/quality balance.

**Monitoring**: Track extraction quality. If <80% precision, consider Claude Haiku upgrade.

---

## Data Flow Architecture

### Ingestion Flow
```
┌─────────────┐
│ Zotero PDF  │
└──────┬──────┘
       │
       ├─────────────────────────────────────────┐
       │                                         │
       ▼                                         ▼
┌──────────────┐                        ┌────────────────┐
│ PyMuPDF      │                        │ PyMuPDF        │
│ (18s/PDF)    │                        │ (reuse chunks) │
└──────┬───────┘                        └────────┬───────┘
       │                                         │
       ▼                                         ▼
┌──────────────┐                        ┌────────────────┐
│ Chunking     │                        │ Batch Chunks   │
│ (2048 tokens)│                        │ (10-20 chunks) │
└──────┬───────┘                        └────────┬───────┘
       │                                         │
       ├──────────┬──────────┐                  │
       ▼          ▼          ▼                  ▼
  ┌────────┐ ┌────────┐ ┌────────┐   ┌──────────────────┐
  │Qdrant  │ │Neo4j   │ │Zotero  │   │Graphiti MCP      │
  │Embedding│ │GraphRAG│ │API     │   │(Autonomous       │
  │        │ │        │ │        │   │ Extraction)      │
  └────────┘ └────────┘ └────────┘   └──────────────────┘
      │          │          │                  │
      └──────────┴──────────┴──────────────────┘
                  │
                  ▼
         ┌────────────────┐
         │ Linked via     │
         │ Zotero Keys    │
         │ (ABC123, ...)  │
         └────────────────┘
```

### Query Flow
```
User Query: "Find papers about attention mechanisms"
            │
            ▼
    ┌───────────────┐
    │ Intent        │
    │ Detection     │
    └───────┬───────┘
            │
    ┌───────┴───────────────┐
    │                       │
    ▼                       ▼
┌─────────────┐      ┌──────────────┐
│ Structured  │      │ Exploratory  │
│ Query       │      │ Query        │
└─────┬───────┘      └──────┬───────┘
      │                     │
      ▼                     ▼
┌─────────────┐      ┌──────────────┐
│zot_explore_ │      │zot_discover  │
│graph        │      │              │
│(Neo4j)      │      │(Graphiti)    │
└─────┬───────┘      └──────┬───────┘
      │                     │
      └──────────┬──────────┘
                 │
                 ▼
         ┌───────────────┐
         │ Results with  │
         │ Provenance    │
         │ (source: neo4j│
         │  or graphiti) │
         └───────────────┘
```

## Risks / Trade-offs

### Risk 1: Graphiti Entity Quality on Academic Papers
- **Concern**: General-purpose NER may struggle with academic jargon
- **Example**: "Smith et al. (2023)" might extract "et al" as organization
- **Mitigation**:
  - Phase 1 validation on diverse sample
  - Cross-validation tool highlights precision issues
  - Custom extraction prompts if needed (Graphiti supports this)
- **Threshold**: <80% precision → abandon or refine

### Risk 2: Cost Escalation
- **Concern**: Full library ingestion could cost $73-146 (7,390 papers × $0.01-0.02)
- **Mitigation**:
  - Phase 1 limited to 10-20 papers (<$1)
  - Selective ingestion (only "interesting" papers) in Phase 2
  - Monitor costs, alert if exceeds budget
- **Threshold**: If costs >$100 for full library → selective ingestion only

### Risk 3: Schema Drift
- **Concern**: Graphiti's autonomous schema diverges from Neo4j over time
- **Example**: Graphiti calls it "Transformer Architecture" while Neo4j uses "Transformer (Method)"
- **Mitigation**:
  - Cross-validation tool detects drift
  - Neo4j remains source of truth for canonical entities
  - Graphiti used for discovery, not production queries
- **Acceptable**: Some drift expected (it's the point of autonomous extraction)

### Risk 4: Performance Overhead
- **Concern**: LLM extraction adds latency
- **Current**: Neo4j GraphRAG takes ~30-60s per paper for extraction
- **Graphiti**: Likely similar (LLM-based extraction)
- **Mitigation**: Async ingestion (doesn't block main pipeline)
- **Monitoring**: Track ingestion time, alert if >2x baseline

### Risk 5: Maintenance Complexity
- **Concern**: Two graph systems = 2x operational overhead
- **Mitigation**:
  - Feature flag allows easy disable
  - Comprehensive docs (setup, troubleshooting)
  - Cross-validation tool helps justify value
  - If not valuable in Phase 1 → abandon cleanly
- **Decision Point**: After Phase 1, explicit cost/benefit analysis

## Migration Plan

### Phase 1 (This Proposal): Prototype & Validation
1. **Tag 10-20 papers** with `_graphiti_experiment`
2. **Ingest to Graphiti** (async, parallel to Neo4j)
3. **Test queries** via `zot_discover` tool
4. **Cross-validate** extractions (Neo4j vs Graphiti)
5. **Evaluate** success criteria (precision, discoveries, cost, performance)

### Phase 2 (If Phase 1 Succeeds): Selective Ingestion
1. **Remove tag restriction** (but keep selective logic)
2. **User tagging** for Graphiti ingestion (e.g., "Highly-Cited Papers" collection)
3. **Personal annotations** integration (PAI research journal)
4. **Cost monitoring** and budget controls

### Phase 3 (If Phase 2 Succeeds): Production Feature
1. **Remove experimental flag**
2. **Unified query tool** with smart routing
3. **Cross-system queries** (JOIN Neo4j + Graphiti results)
4. **Performance optimization** (caching, batching)

### Rollback Plan
- **Disable feature flag** → Graphiti pipeline stops
- **No data loss** → Neo4j and Qdrant unchanged
- **Remove Graphiti nodes** (optional cleanup):
  ```cypher
  MATCH (n:GraphitiEntity) DETACH DELETE n
  MATCH (n:GraphitiEpisode) DETACH DELETE n
  ```
- **Document learnings** in `decisions.md` (ADR-017)

## Open Questions

### Q1: How to present dual results to users?
**Current**: Separate tools (`zot_explore_graph` vs `zot_discover`)
**Future**: Merged tool with provenance?
**Answer**: Start separate (Phase 1), reconsider based on usage patterns

### Q2: Should we pre-filter chunks before Graphiti?
**Option A**: Send all chunks to Graphiti (autonomous decides what's important)
**Option B**: Send only "high-information" chunks (e.g., introduction, methodology sections)
**Decision**: Option A for Phase 1 (test full autonomous capability)

### Q3: Cross-validation frequency?
**Option A**: On-demand via CLI (`agent-zot analyze-extraction`)
**Option B**: Automatic after every ingestion
**Decision**: Option A (manual for Phase 1, avoids overhead)

### Q4: Entity deduplication strategy?
**Problem**: Graphiti might extract "John Smith" while Neo4j has "Smith, J."
**Solution**:
- Link via Zotero key (both systems tag entities with source paper)
- Fuzzy matching in cross-validation tool
- Accept some duplication (it's expected in hybrid system)

## Success Metrics (Phase 1)

1. **Precision**: ≥80% entity extraction accuracy
   - Manual review of 20 randomly sampled entities
   - Compare against ground truth (paper content)

2. **Discovery**: ≥3 novel insights
   - Entities found by Graphiti but missed by Neo4j
   - Cross-disciplinary connections not in explicit schema
   - Documented in evaluation report

3. **Performance**: <5 seconds average query latency
   - 10 test queries via `zot_discover`
   - Measured end-to-end (MCP call → result)

4. **Cost**: <$1 for Phase 1 ingestion
   - 10-20 papers × $0.01-0.02 per paper
   - Track actual OpenAI API costs

5. **Adoption**: 5+ successful queries
   - User (or Claude) finds value in discovery queries
   - Documented in evaluation report

**Go/No-Go Decision**: 4 of 5 metrics must pass to proceed to Phase 2.
