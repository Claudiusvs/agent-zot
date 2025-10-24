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
  - Automatic intent detection (relationship/metadata/semantic)
  - Smart backend selection (Fast/Graph-enriched/Metadata-enriched/Comprehensive modes)
  - Query expansion for vague queries
  - Automatic escalation when quality is inadequate
  - Result provenance tracking

### Content Analysis
- `zot_ask_paper(item_key, question, top_k)` - Read and analyze paper content

### Advanced Search (Legacy - use `zot_search` instead)
- ~~`zot_semantic_search(query, limit)`~~ - DEPRECATED: Use `zot_search` (Fast Mode)
- ~~`zot_unified_search(query, limit)`~~ - DEPRECATED: Use `zot_search` (Comprehensive Mode)
- ~~`zot_refine_search(query, limit, max_iterations)`~~ - DEPRECATED: Use `zot_search` (has built-in refinement)
- `zot_decompose_query(query, limit)` - Multi-concept query decomposition (still useful for complex AND/OR queries)

### Relationship Analysis
- `zot_graph_search(query, entity_types, limit)` - Neo4j graph search
- `zot_find_related_papers(item_key, limit)` - Citation/author connections

### Fallback Tools
- `zot_search_items(query, limit)` - Keyword search via Zotero API
- `zot_get_item(item_key)` - Metadata retrieval

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
