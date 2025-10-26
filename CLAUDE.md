# Agent-Zot Context for Claude

**Last Updated**: October 25, 2025
**Status**: ✅ Production-Ready (v2.0 - Post-Consolidation)
**Project Health**: A Grade (95/100)

---

## 🎯 Quick Overview

Agent-Zot is a production-grade MCP server providing intelligent access to Zotero research libraries through **7 unified tools** (consolidated from 35 legacy tools - 80% reduction).

**Current System State**:
- ✅ Qdrant: 234,153 chunks indexed
- ✅ Neo4j: 25,184 nodes, 134,068 relationships (91% functional)
- ✅ Zotero: 7,390 items
- ✅ MCP Server: 38 tools (7 primary unified + 28 deprecated/utility)

---

## 🔥 The 7 Unified Tools

### Research Tools (3)

**1. `zot_search` - Finding Papers**
- 5 execution modes: Fast, Entity-enriched, Graph-enriched, Metadata-enriched, Comprehensive
- Automatic intent detection, Phase 0 query decomposition, quality-based escalation
- Replaces 7 legacy tools

**2. `zot_summarize` - Understanding Papers**
- 4 depth modes: Quick (~500 tokens), Targeted (~2-5k), Comprehensive (~8-15k), Full (10-100k)
- Automatic depth detection, cost optimization
- Replaces 3 legacy tools

**3. `zot_explore_graph` - Exploring Connections**
- 9 execution modes: Citation Chain, Influence, Content Similarity, Related Papers, Collaboration, Concept Network, Temporal, Venue Analysis, Comprehensive
- Dual backend: Neo4j (graph) + Qdrant (content)
- Replaces 9 legacy tools

### Management Tools (4)

**4. `zot_manage_collections`** - 6 modes (List, Create, Show Items, Add, Remove, Recent)
**5. `zot_manage_tags`** - 4 modes (List, Search, Add, Remove)
**6. `zot_manage_notes`** - 4 modes (List Annotations, List Notes, Search, Create)
**7. `zot_export`** - 3 modes (Markdown, BibTeX, GraphML)

---

## 🎯 Tool Selection Guide

```
Finding papers?              → zot_search
Understanding a paper?       → zot_summarize
Exploring connections?       → zot_explore_graph
Managing collections?        → zot_manage_collections
Managing tags?               → zot_manage_tags
Managing notes/annotations?  → zot_manage_notes
Exporting data?              → zot_export
```

**Key Principle**: Trust the automatic mode selection. All tools use pattern-based intent detection.

---

## ⚠️ Critical Operational Info

### Manual Database Updates Required

**Auto-update DISABLED** for instant server startup (~100ms instead of 3-5 seconds).

⚠️ **You MUST manually update after adding/modifying papers:**

```bash
# Full update with full-text extraction
agent-zot update-db --force-rebuild --fulltext

# Quick update (metadata only)
agent-zot update-db

# Check status
agent-zot get-search-database-status
```

**Why**: Instant startup improves UX. Explicit updates give better control.
**See**: `decisions.md` ADR-003 for rationale

---

### Orphaned Process Cleanup

**Issue**: Multiple `agent-zot serve` processes can accumulate (each ~1-2GB RAM).

**Automatic**: `cleanup_orphaned_processes()` runs on server startup

**Manual cleanup** (if needed):
```bash
ps aux | grep "agent-zot serve" | grep -v grep
kill <old_PID>
```

**Limitation**: macOS keeps Unix sockets open, so auto-cleanup may miss some. See `bugs.md` Limitation #001

---

### Backend Execution Strategy

| Backends | Mode | Use Case |
|----------|------|----------|
| 1 backend | Parallel | Fast searches |
| 2 backends | Parallel | Entity/Graph/Metadata-enriched |
| 3 backends | **Sequential** | Comprehensive (prevents freeze) |

**Critical**: Comprehensive Mode uses sequential execution to prevent memory exhaustion.
**See**: `decisions.md` ADR-002

---

## 📁 Important File Locations

### Configuration
- **Config**: `~/.config/agent-zot/config.json`
- **Server**: `src/agent_zot/core/server.py`
- **Unified Search**: `src/agent_zot/search/unified_smart.py`
- **Unified Summarize**: `src/agent_zot/search/unified_summarize.py`
- **Unified Graph**: `src/agent_zot/search/unified_graph.py`

### Data
- **Qdrant**: Docker volume `agent-zot-qdrant-data`
- **Neo4j**: Docker volume `agent-zot-neo4j-data`
- **Zotero DB**: `/Users/claudiusv.schroder/zotero_database/zotero.sqlite`
- **Parse Cache**: `~/.cache/agent-zot/parsed_docs.db` (623 MB, 2,519 docs)

### Project Documentation
- **decisions.md** - 13 architectural decisions (WHY things are done)
- **bugs.md** - 13 fixed bugs + 5 known limitations
- **progress.md** - Implementation timeline and milestones
- **docs/development/TOOL_HIERARCHY.md** - Complete architecture
- **docs/QUICK_REFERENCE.md** - Current configuration
- **docs/BACKUP_AUTOMATION.md** - Backup/restore procedures

---

## 🚀 Common Workflows

### Complete Literature Review
```
1. zot_search("neural mechanisms of cognitive control")
2. zot_summarize(item_key, "Summarize comprehensively")
3. zot_explore_graph("Find influential papers on cognitive control")
4. zot_explore_graph("How has research evolved from 2015-2025?")
5. zot_manage_collections("create collection Cognitive Control Review")
6. zot_export("review.bib")
```

### Finding Collaboration Networks
```
1. zot_search("graph neural networks")
2. zot_explore_graph("Who collaborated with [author]?")
3. zot_summarize(item_key, "What methodology did they use?")
```

---

## 🔧 System Maintenance

### Backup System
```bash
# Backup everything
python scripts/backup.py backup-all

# List backups
python scripts/backup.py list

# Restore procedures in docs/BACKUP_AUTOMATION.md
```

**Recommendation**: Weekly manual backups, especially before major operations.

### Database Status
```bash
# Check Qdrant
agent-zot get-search-database-status

# Check Neo4j
docker exec agent-zot-neo4j cypher-shell -u neo4j -p demodemo \
  "MATCH (n) RETURN count(n) as total"
```

---

## 🎯 Key Design Principles

All architectural decisions documented in `decisions.md`. Key principles:

1. **Automatic Intent Detection** - Pattern-based, fast, transparent
2. **Cost Optimization** - Use cheapest/fastest approach that works
3. **Quality-Based Escalation** - Automatically upgrade when needed
4. **Sequential Execution** - Prevents resource exhaustion (Comprehensive Mode)
5. **Phase 0 Decomposition** - Multi-concept queries handled automatically
6. **Dual-Backend** - Neo4j (graph) + Qdrant (content) in single tool

---

## 📊 Performance Benchmarks

**Search**: Fast (~2s), Enriched (~4s), Comprehensive (~6-8s)
**Summarize**: Quick (<1s), Targeted (~2-3s), Comprehensive (~8-10s), Full (10-30s)
**Graph**: Varies by mode (1-3s for most queries)
**PDF Processing**: ~18s per PDF, ~476 PDFs/hour (8 workers)

---

## 🔍 Troubleshooting

### "No results found" from graph queries
**Cause**: Neo4j 91% populated (by design). Some specific relationships may not exist.
**Solution**: Expected behavior. Try alternative queries or use Qdrant-based search.

### Memory usage high
**Cause**: BGE-M3 model (~1-2GB) loaded in memory
**Solution**: Normal. If multiple processes exist, kill orphaned ones (see above).

### Database locked (rare)
**Cause**: Zotero writing while agent-zot reading
**Solution**: 10-second timeout + WAL mode handles this. Retry automatically.
**See**: `bugs.md` Bug #002

---

## 📚 Documentation Map

- **This file (CLAUDE.md)** - Quick reference for current system state
- **decisions.md** - WHY architectural decisions were made
- **bugs.md** - Fixed bugs and known limitations
- **progress.md** - Implementation timeline and milestones
- **README.md** - User-facing documentation
- **docs/development/TOOL_HIERARCHY.md** - Complete architecture
- **docs/QUICK_REFERENCE.md** - Commands and configuration
- **docs/BACKUP_AUTOMATION.md** - Backup/restore procedures

---

## 🔄 Memory System Integration

After every session, update these files:
- **progress.md** - What was completed, what's in progress, what's next
- **bugs.md** - New bugs discovered or fixed
- **decisions.md** - New architectural decisions made

This keeps documentation current and prevents CLAUDE.md bloat.

---

**For Claude Code**: Trust the 7 unified tools' automatic mode selection. They're optimized for quality, speed, and cost. Use natural language queries - intent detection handles the rest. When you need to understand WHY something is done a certain way, check `decisions.md`. When something breaks, check `bugs.md`. When you need historical context, check `progress.md`.
- update the progress.md file after every run, while adding bug reports to bugs.md, and use the decisions.md file to log every architectural decision you make. create these files in the projects root idrectory if they dont yet exist.
- always warn about the context remaining and before starting a new task make sure the left over context is enough for the task or not. if not, ask the user to use 'compact'.
- comit and push any untracked changes upon completion of major tasks and/or todos, etc. to a given project's github repository. prompt the user to connect the project to its github repository if it is not yet connected.