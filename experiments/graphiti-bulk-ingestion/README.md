# Graphiti SDK Bulk Ingestion Experiment (ARCHIVED)

**Status**: ❌ **DISCONTINUED** (November 9, 2025)
**Reason**: Tool-use case mismatch
**Decision**: Focus on existing agent-zot stack (Qdrant + Neo4j + Zotero)

---

## What This Was

An attempt to integrate Graphiti SDK (temporal knowledge graph with autonomous entity extraction) for bulk ingestion of agent-zot's 2,685 research papers.

**Goal**: Extract entities and relationships from academic papers using LLM-powered autonomous extraction.

**Result**: Graphiti is designed for **real-time, incremental ingestion** (chatbots, voice apps, CRM sync), NOT batch ETL of large static datasets.

---

## Why It Was Discontinued

### Design Mismatch

From Graphiti official documentation:

> "Traditional RAG approaches rely on batch processing and static data summarization. **Graphiti provides Real-Time Incremental Updates**: immediate integration of new data episodes without batch recomputation."

**Intended Use Cases**:
- ✅ AI assistants learning from conversations over time
- ✅ Agents with evolving state
- ✅ Voice applications with real-time context
- ❌ **NOT for bulk loading 2,685 static research papers**

### Technical Issues Encountered

1. **Hardcoded OpenAI Dependency**: SDK hardcodes `OpenAIRerankerClient` even when using Ollama
2. **Rate Limiting**: Default settings prioritize avoiding rate limits, not throughput
3. **Stability**: Community-reported issues with `add_episode_bulk()` (GitHub issues #223, #879, #882, #760)
4. **API Costs**: Requires commercial API access (OpenAI or Anthropic) for entity extraction

### What Agent-Zot Already Has

| Component | Status | Capability |
|-----------|--------|------------|
| Qdrant | ✅ 234k chunks | Semantic search, BGE-M3 embeddings |
| Neo4j | ✅ 134k relationships | Graph queries, citations, collaborations |
| Zotero | ✅ 7,390 items | Metadata, collections, tags |
| 8 Unified Tools | ✅ Production | Search, summarize, explore |

**Conclusion**: Marginal benefit didn't justify complexity and cost.

---

## Archive Contents

```
experiments/graphiti-bulk-ingestion/
├── README.md                    (this file)
├── GRAPHITI_DEDUPLICATION.md    (original documentation, now outdated)
├── src/
│   ├── graphiti_client.py       (SDK wrapper)
│   ├── graphiti_ingestion.py    (ingestion pipeline)
│   └── graphiti_cache.py        (episode deduplication)
├── scripts/
│   ├── bulk_ingest_graphiti.py  (bulk ingestion script)
│   └── purge_graphiti_episodes.py (cleanup utility)
└── tests/
    └── (test scripts if any)
```

---

## Important Notes

### What This Archive Is NOT

**This is NOT PAI's Graphiti MCP Server**:
- PAI has a separate, **working** Graphiti MCP server for personal memory
- Group ID: `pai-claudius-main`
- MCP tools: `mcp__graphiti__search_memory_nodes`, etc.
- **That system is UNTOUCHED and still in production**

**This archive is ONLY**:
- Agent-zot's attempt to bulk-ingest research papers
- Separate Graphiti instance for academic literature
- Experimental, never reached production

### Key Lessons Learned

1. **Research tool design philosophy first**: Could have saved days by checking use cases upfront
2. **Don't assume tool capabilities**: "Temporal knowledge graph" ≠ "good for historical bulk loading"
3. **Check for hardcoded dependencies**: Always review source code for unexpected constraints
4. **Question incremental value**: Does new tool justify the complexity?
5. **Trust your existing stack**: Agent-zot already excellent - don't over-engineer

---

## Timeline

- **October 2025**: Initial Graphiti integration attempt
- **November 2-8, 2025**: Multiple LLM configuration attempts:
  - Ollama (failed - hardcoded OpenAI dependency)
  - GPT-4o-mini (wrong model)
  - GPT-5-mini (rate limits)
  - Claude Haiku 4.5 (insufficient API credits)
- **November 9, 2025**: Research revealed tool-use case mismatch → Archived

---

## If You Want to Resurrect This

**Consider these options**:

1. **Hybrid Approach**: Use Graphiti only for NEW papers (incremental ingestion aligns with design)
2. **Custom Integration**: Skip SDK, build custom Neo4j temporal graph with direct Cypher queries
3. **Different Tool**: Explore alternatives better suited for bulk static dataset loading
4. **Keep Current Stack**: Agent-zot already excellent - enhance what exists

**Recommendation**: Option 4 (keep current stack)

---

## For More Details

See project documentation:
- `decisions.md` - ADR documenting why this was archived
- `progress.md` - Timeline entry for experiment conclusion

---

**Archived**: November 9, 2025
**By**: Claude Code (Sonnet 4.5)
**Approved By**: User decision
