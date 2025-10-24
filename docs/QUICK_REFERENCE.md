# Quick Reference: Agent-Zot Current Configuration

**⚠️ This document reflects the CURRENT production system (October 2025)**

---

## Active Stack

| Component | Technology | Details |
|-----------|-----------|---------|
| **Vector DB** | Qdrant (Docker) | Collection: `zotero_library_qdrant` |
| **Embeddings** | BGE-M3 | 1024-dim, multilingual, local/free |
| **Graph DB** | Neo4j (Docker) | Database: `neo4j` |
| **Document Parser** | Docling | AI-powered PDF extraction with OCR |

---

## Docker Containers

### Start Services
```bash
docker start agent-zot-qdrant agent-zot-neo4j
```

### Stop Services
```bash
docker stop agent-zot-qdrant agent-zot-neo4j
```

### Check Status
```bash
docker ps | grep agent-zot
```

---

## Database Connections

### Qdrant
- **URL:** `http://localhost:6333`
- **Collection:** `zotero_library_qdrant`
- **Auth:** None required
- **Web UI:** http://localhost:6333/dashboard

### Neo4j
- **Bolt URL:** `bolt://localhost:7687`
- **HTTP URL:** `http://localhost:7474`
- **Username:** `neo4j`
- **Password:** `demodemo`
- **Web UI:** http://localhost:7474/browser/

---

## Common Operations

### Check Qdrant Collection Status
```bash
curl -s http://localhost:6333/collections/zotero_library_qdrant | python3 -c "
import sys, json
data = json.load(sys.stdin)['result']
print(f\"Points: {data['points_count']:,}\")
print(f\"Status: {data['status']}\")
"
```

### Check Neo4j Node Count
```bash
docker exec agent-zot-neo4j cypher-shell -u neo4j -p demodemo \
  "MATCH (n) RETURN count(n) as total"
```

### Update Search Database (Qdrant)
```bash
agent-zot update-search-database
```

### Rebuild Neo4j Graph
```bash
# Check if this command exists
agent-zot rebuild-neo4j
# OR
python populate_neo4j_from_qdrant.py
```

---

## MCP Tool Usage

### 🆕 Primary Search (Recommended)
- **`zot_search(query, limit, force_mode)`** - **Smart unified search (RECOMMENDED DEFAULT)**
  - Automatic intent detection (entity/relationship/metadata/semantic)
  - Smart backend selection (Fast/Entity-enriched/Graph-enriched/Metadata-enriched/Comprehensive - 5 modes)
  - Query expansion for vague queries
  - Automatic escalation when quality is inadequate
  - Result provenance tracking

### 🆕 Primary Summarization (Recommended)
- **`zot_summarize(item_key, query, force_mode, top_k)`** - **Smart unified summarization (RECOMMENDED DEFAULT)**
  - Automatic depth detection (quick/targeted/comprehensive/full)
  - Cost optimization (prevents unnecessary full-text extraction)
  - Multi-aspect orchestration (4 key questions for comprehensive mode)
  - Four modes: Quick (~500-800 tokens), Targeted (~2k-5k tokens), Comprehensive (~8k-15k tokens), Full (10k-100k tokens)

### 🆕 Primary Graph Exploration (Recommended)
- **`zot_explore_graph(query, paper_key, author, concept, start_year, end_year, field, force_mode, limit, max_hops)`** - **Smart unified exploration (RECOMMENDED DEFAULT)**
  - Automatic intent detection (citation/collaboration/concept/temporal/influence/venue/content_similarity)
  - Parameter extraction from natural language queries
  - Smart mode selection (chooses optimal strategy: graph-based OR content-based)
  - Nine modes: Citation Chain, Influence (PageRank), Content Similarity (vector-based), Related Papers, Collaboration, Concept Network, Temporal, Venue Analysis, plus Comprehensive
  - Dual backend: Neo4j for graph exploration + Qdrant for content similarity

### Content Analysis (Advanced)
- `zot_ask_paper(item_key, question, top_k)` - Direct chunk retrieval (manual control)
- `zot_get_item(item_key)` - Metadata only
- `zot_get_item_fulltext(item_key)` - Complete text (expensive - use zot_summarize instead)

### Advanced Search (Legacy - use `zot_search` instead)
- ~~`zot_semantic_search(query, limit)`~~ - DEPRECATED: Use `zot_search` (Fast Mode)
- ~~`zot_unified_search(query, limit)`~~ - DEPRECATED: Use `zot_search` (Comprehensive Mode)
- ~~`zot_refine_search(query, limit, max_iterations)`~~ - DEPRECATED: Use `zot_search` (has built-in refinement)
- ~~`zot_enhanced_semantic_search(query, limit, include_chunk_entities, filters)`~~ - DEPRECATED: Use `zot_search` (Entity-enriched Mode)
- ~~`zot_hybrid_vector_graph_search(query, limit, vector_weight)`~~ - DEPRECATED: Use `zot_search` (Graph-enriched Mode)
- ~~`zot_decompose_query(query, limit)`~~ - DEPRECATED: Use `zot_search` (automatic multi-concept decomposition as Phase 0)
- ~~`zot_search_items(query, limit)`~~ - DEPRECATED: Use `zot_search` (Metadata-enriched Mode)
- ~~`zot_get_item(item_key)`~~ - DEPRECATED: Use `zot_summarize` (Quick Mode)

### Advanced Graph Analysis (Legacy - use `zot_explore_graph` instead)
- ~~`zot_graph_search(query, entity_types, limit)`~~ - DEPRECATED: Use `zot_explore_graph` (automatic mode selection)
- ~~`zot_find_citation_chain(paper_key, max_hops, limit)`~~ - DEPRECATED: Use `zot_explore_graph` (Citation Chain Mode)
- ~~`zot_find_seminal_papers(field, top_n)`~~ - DEPRECATED: Use `zot_explore_graph` (Influence Mode)
- ~~`zot_find_similar_papers(item_key, limit)`~~ - DEPRECATED: Use `zot_explore_graph` (Content Similarity Mode)
- ~~`zot_find_related_papers(item_key, limit)`~~ - DEPRECATED: Use `zot_explore_graph` (Related Papers Mode)
- ~~`zot_find_collaborator_network(author, max_hops, limit)`~~ - DEPRECATED: Use `zot_explore_graph` (Collaboration Mode)
- ~~`zot_explore_concept_network(concept, max_hops, limit)`~~ - DEPRECATED: Use `zot_explore_graph` (Concept Network Mode)
- ~~`zot_track_topic_evolution(concept, start_year, end_year)`~~ - DEPRECATED: Use `zot_explore_graph` (Temporal Mode)
- ~~`zot_analyze_venues(field, top_n)`~~ - DEPRECATED: Use `zot_explore_graph` (Venue Analysis Mode)

### Fallback Tools
- None - All query/retrieval operations consolidated into 3 smart tools

---

## ⚠️ DEPRECATED (Do Not Use)

### Old Technologies
- ❌ ChromaDB - Migrated to Qdrant (Oct 2024)
- ❌ OpenAI embeddings (`text-embedding-3-large`) - Replaced with BGE-M3
- ❌ Collection `zotero_library_openai` - Renamed to `zotero_library_qdrant`

### Old Files/Directories
- ❌ `./qdrant_storage/` - Docker uses internal volume
- ❌ `~/.config/agent-zot/chroma_db/` - Old ChromaDB data
- ❌ `config_backup/config.json` - Outdated configuration

---

## Troubleshooting

### "MPS backend out of memory"
**Solution:** Add to `claude_desktop_config.json`:
```json
"env": {
  "PYTORCH_MPS_HIGH_WATERMARK_RATIO": "0.0",
  ...
}
```
Then restart Claude Desktop.

### "Collection not found"
**Check:** Are you using `zotero_library_qdrant` (correct) or `zotero_library_openai` (wrong)?

### "Neo4j authentication failed"
**Check:** Password is `demodemo` (not `password` or `graphiti123`)

### "Graph search returns no results"
**Check:** Is Neo4j populated? Run:
```bash
docker exec agent-zot-neo4j cypher-shell -u neo4j -p demodemo \
  "MATCH (n:Paper) RETURN count(n) as papers"
```
Expected: ~2,370 papers. If 0, rebuild graph.

---

## See Also

- `SYSTEM_STATUS.md` - Current system health and statistics
- `README.md` - Full documentation
- `docs/CLAUDE.md` - Claude Code guidance for monitoring indexing
