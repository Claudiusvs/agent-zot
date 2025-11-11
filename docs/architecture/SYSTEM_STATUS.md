# Agent-Zot System Status

**Last Updated:** 2025-10-14

## 🟢 ACTIVE PRODUCTION SYSTEMS

### Docker Containers

| Container | Service | Ports | Status | Credentials |
|-----------|---------|-------|--------|-------------|
| `agent-zot-qdrant` | Qdrant Vector DB | 6333-6334 | ✅ ACTIVE | No auth |
| `agent-zot-neo4j` | Neo4j Graph DB | 7474, 7687 | ✅ ACTIVE | neo4j/demodemo |

### Qdrant Configuration
- **Collection:** `zotero_library_qdrant`
- **Embeddings:** BGE-M3 (1024-dim, multilingual)
- **Points:** 3,087 document chunks
- **Status:** GREEN
- **Location:** Docker volume (internal)

### Neo4j Configuration
- **Database:** Default (`neo4j`)
- **Nodes:** 25,184 total (2,370 Papers, 14,985 Persons, 2,048 Concepts)
- **Relationships:** 63,838
- **Location:** Docker volume `agent-zot-neo4j-data`

### Zotero Library
- **Library ID:** 5585614
- **Total Items:** 2,515
- **Type:** User library

---

## ⚠️ UNRELATED/EXTERNAL SYSTEMS

### Other Docker Containers
| Container | Purpose | Status | Action |
|-----------|---------|--------|--------|
| `graphiti-neo4j` | **Separate project** (not agent-zot) | Running (ports 7475, 7688) | ✅ IGNORE - Different research project |

**Note:** `graphiti-neo4j` is a completely independent project using Neo4j. It does NOT interfere with `agent-zot-neo4j`.

---

## 🗑️ ARCHIVED FILES (Cleanup Completed)

**Archived on:** 2025-10-14 14:57:51
**Archive location:** `./archived_20251014_145751/`

### Archived Items
- ✅ `qdrant_storage/` - Unused local Qdrant storage (Docker uses own volume)
- ✅ `config_backup/` - Outdated config files (referenced ChromaDB + OpenAI embeddings)
- ⚠️ `~/.config/agent-zot/chroma_db/` - Old ChromaDB data (not archived, may still exist)

### Remaining Backups
- `backups/pre-neo4j-20251012-163835/` - Pre-Neo4j migration backup (Oct 12, 2024)

**To restore archived files:**
```bash
mv ./archived_20251014_145751/* ./
```

---

## 🔍 HOW TO VERIFY SYSTEM HEALTH

### Check Qdrant Status
```bash
docker exec agent-zot-qdrant curl -s http://localhost:6333/collections/zotero_library_qdrant
```

### Check Neo4j Status
```bash
docker exec agent-zot-neo4j cypher-shell -u neo4j -p demodemo "MATCH (n) RETURN count(n) as total"
```

### Check Docker Health
```bash
docker ps | grep agent-zot
# Should show: agent-zot-qdrant (Up XX hours), agent-zot-neo4j (Up XX hours)
```

---

## 📝 IMPORTANT NOTES

1. **Collection Name:** Always use `zotero_library_qdrant` (NOT `zotero_library_openai`)
2. **Embedding Model:** BGE-M3 (1024-dim) - NOT OpenAI (3072-dim)
3. **Neo4j Password:** `demodemo` (NOT `password` or `graphiti123`)
4. **ChromaDB:** Completely deprecated - ignore all ChromaDB references in old docs

---

## 🆘 TROUBLESHOOTING

### "Collection not found" errors
- Check you're using `zotero_library_qdrant` (correct name)
- Verify Docker container is running: `docker ps | grep qdrant`

### "MPS backend out of memory" errors
- Verify `PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0` in `claude_desktop_config.json`
- Restart Claude Desktop after config changes

### Neo4j connection errors
- Use password `demodemo` (not `password`)
- Port 7687 for Bolt, 7474 for HTTP
- Check container: `docker ps | grep agent-zot-neo4j`
