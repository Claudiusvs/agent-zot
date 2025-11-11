# Graphiti Integration Guide

**Status**: 🧪 Experimental (Phase 1 - Prototype)
**Last Updated**: November 7, 2025

---

## Overview

Agent-zot's Graphiti integration adds **autonomous entity extraction** as a complementary discovery layer alongside the existing Neo4j structured graph. This creates a hybrid architecture where:

- **Neo4j** provides precise, schema-driven queries (citations, collaborations, structured metadata)
- **Graphiti** discovers emergent entities and relationships without predefined schemas

**Use Case**: Find cross-disciplinary connections, unexpected concepts, and relationships that weren't explicitly modeled in the Neo4j schema.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Hybrid Discovery Architecture              │
├──────────────────────┬──────────────────────────────────────┤
│   Neo4j (Explicit)   │   Graphiti (Autonomous)              │
│                      │                                      │
│ • Structured schema  │ • Schema-free extraction             │
│ • Academic precision │ • Cross-disciplinary discovery       │
│ • Cypher + GDS       │ • Natural language queries           │
│ • Fast, predictable  │ • Temporal context tracking          │
└──────────────────────┴──────────────────────────────────────┘
             Linked via Zotero Item Keys
```

---

## Prerequisites

### Required

1. **Graphiti MCP Server** installed and configured in Claude Desktop
   - Group ID isolation: `agent-zot-discovery`
   - Backend: Neo4j or FalkorDB

2. **OpenAI API Key** (for GPT-4o-mini entity extraction)
   - Set environment variable: `OPENAI_API_KEY=sk-...`
   - Alternative: Anthropic Claude (future support)

3. **Agent-zot v2.2+** with Qdrant and Neo4j already configured

### Optional

- Tags in Zotero for selective ingestion (`_graphiti_experiment`)
- Cost tracking enabled for LLM API monitoring

---

## Configuration

### config.json Settings

Located at: `~/.config/agent-zot/config.json`

```json
{
  "graphiti": {
    "enabled": false,               // Feature flag (opt-in)
    "group_id": "agent-zot-discovery",  // Isolated namespace
    "llm_provider": "openai",       // LLM for entity extraction
    "llm_model": "gpt-4o-mini",     // Cost-efficient model
    "use_neo4j": true,              // Use same Neo4j instance
    "filter_tag": "_graphiti_experiment",  // Phase 1: selective ingestion
    "batch_size": 15,               // Chunks per episode (cost optimization)
    "cost_threshold_usd": 1.0,      // Alert if costs exceed threshold
    "mcp_timeout_seconds": 10       // Timeout for MCP calls
  }
}
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `false` | Enable Graphiti integration |
| `group_id` | string | `"agent-zot-discovery"` | Graphiti namespace for isolation |
| `llm_provider` | string | `"openai"` | LLM provider (`openai`, `anthropic`) |
| `llm_model` | string | `"gpt-4o-mini"` | Model for entity extraction |
| `use_neo4j` | boolean | `true` | Use same Neo4j instance (vs FalkorDB) |
| `filter_tag` | string | `"_graphiti_experiment"` | Only ingest papers with this tag (Phase 1) |
| `batch_size` | integer | `15` | Chunks per episode (10-20 recommended) |
| `cost_threshold_usd` | float | `1.0` | Cost alert threshold |
| `mcp_timeout_seconds` | integer | `10` | MCP call timeout |

---

## Usage

### Phase 1: Prototype (10-20 Papers)

**1. Tag Papers in Zotero**

Add the tag `_graphiti_experiment` to 10-20 papers you want to test with autonomous extraction. Choose diverse papers (different fields, cross-disciplinary content).

**2. Enable Graphiti**

Edit `~/.config/agent-zot/config.json`:
```json
{
  "graphiti": {
    "enabled": true,
    ...
  }
}
```

**3. Ingest Papers**

```bash
# Trigger ingestion for tagged papers
agent-zot update-db --tag _graphiti_experiment

# Or manually ingest specific paper
agent-zot graphiti ingest --paper-key ABC123
```

**4. Query via `zot_discover` Tool**

```python
# Example queries (via Claude or MCP client)
zot_discover("What unexpected entities appear in papers about transformers?")
zot_discover("Find emergent concepts across neuroscience and NLP papers")
zot_discover("Discover cross-disciplinary connections")
```

**5. Compare Extractions**

```bash
# Cross-validation: Neo4j vs Graphiti
agent-zot analyze-extraction --paper-key ABC123 --output report.json
```

---

## Cost Estimates

### LLM API Costs (GPT-4o-mini)

- **Per Paper**: ~$0.01-0.02 (depending on length)
- **Phase 1 (10-20 papers)**: <$1
- **Full Library (7,390 papers)**: ~$73-146

### Optimization Tips

1. **Batch Chunks**: Use `batch_size: 15` to reduce API calls
2. **Selective Ingestion**: Only ingest "interesting" papers (high-citation, cross-disciplinary)
3. **Use Efficient Models**: GPT-4o-mini is 60% cheaper than GPT-4
4. **Monitor Costs**: Check `cost_threshold_usd` alerts

---

## Query Examples

### Exploratory Discovery

```python
# Find entities not in Neo4j schema
zot_discover("What concepts appear across multiple papers but aren't in my schema?")

# Cross-disciplinary connections
zot_discover("Find relationships between attention mechanisms and memory systems")

# Emergent patterns
zot_discover("Discover unexpected methodological similarities across papers")
```

### Comparison with Neo4j

```python
# Structured (Neo4j) - fast, precise
zot_explore_graph("Find papers citing Smith (2023)")

# Discovery (Graphiti) - exploratory, autonomous
zot_discover("Find papers with similar conceptual themes to Smith (2023)")
```

---

## Troubleshooting

### "Graphiti MCP server offline"

**Symptoms**: `GraphitiClient` raises connection errors

**Solution**:
1. Check Claude Desktop MCP configuration
2. Verify Graphiti MCP server is running
3. Test connection: `mcp__graphiti__search_memory_nodes("test")`

### "No entities found"

**Symptoms**: `zot_discover` returns empty results

**Possible Causes**:
1. Papers not yet ingested (check `graphiti.enabled: true`)
2. Episode processing lag (Graphiti async)
3. Query doesn't match extracted entities

**Solution**:
```bash
# Check ingestion status
agent-zot graphiti status

# Manually ingest if needed
agent-zot graphiti ingest --paper-key ABC123
```

### "Cost threshold exceeded"

**Symptoms**: Alert triggered during ingestion

**Solution**:
1. Review `cost_threshold_usd` setting
2. Check OpenAI API billing dashboard
3. Reduce scope (fewer papers, smaller batches)

### "Extraction quality poor"

**Symptoms**: <80% precision in cross-validation

**Solution**:
1. Review `docs/GRAPHITI_PHASE1_EVALUATION.md` (after testing)
2. Consider upgrading to Claude Haiku (better reasoning)
3. Adjust extraction prompts (advanced)

---

## Monitoring

### Check Graphiti Status

```bash
# View ingested episode count
mcp__graphiti__get_episodes(group_id="agent-zot-discovery", last_n=10)

# Search for entities
mcp__graphiti__search_memory_nodes(
    query="attention mechanisms",
    group_ids=["agent-zot-discovery"],
    max_nodes=10
)
```

### Cost Tracking

```bash
# View estimated costs (future feature)
agent-zot graphiti costs --since 2025-11-01
```

---

## Limitations (Phase 1)

1. **Selective Ingestion Only**: Tag-based filter (`_graphiti_experiment`)
2. **No Real-Time Sync**: Manual ingestion trigger required
3. **Limited Cross-Validation**: Basic entity comparison only
4. **Experimental Status**: May be disabled/modified based on evaluation

---

## Next Steps

After Phase 1 evaluation:

- **SUCCESS**: Remove tag filter, enable for full library (selective)
- **PARTIAL**: Refine extraction prompts, re-test
- **FAILURE**: Disable feature, document learnings

---

## References

- **OpenSpec Proposal**: `openspec/changes/add-graphiti-hybrid-discovery/proposal.md`
- **Design Decisions**: `openspec/changes/add-graphiti-hybrid-discovery/design.md`
- **Implementation Tasks**: `openspec/changes/add-graphiti-hybrid-discovery/tasks.md`
- **ADR-017**: Graphiti Hybrid Discovery Architecture (to be created)

---

## Support

For issues or questions:
1. Check `bugs.md` for known limitations
2. Review `decisions.md` for architectural context
3. Consult `progress.md` for implementation status
