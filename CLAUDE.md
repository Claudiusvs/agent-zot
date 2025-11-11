<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# Agent-Zot Context for Claude

**Last Updated**: November 6, 2025
**Status**: ✅ Production-Ready (v2.2 - Incremental Auto-Sync)
**Project Health**: A+ Grade (99/100)

---

## 🎯 Quick Overview

Agent-Zot is a production-grade MCP server providing intelligent access to Zotero research libraries through **8 unified tools** (consolidated from 37 legacy tools - 78% reduction).

**Current System State**:
- ✅ Qdrant: 234,153 chunks indexed
- ✅ Neo4j: 25,184 nodes, 134,068 relationships (91% functional)
- ✅ Zotero: 7,390 items
- ✅ MCP Server: 40 tools (8 primary unified + 30 deprecated/utility)

---

## 🔥 The 8 Unified Tools

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

### Management Tools (5)

**4. `zot_manage_collections`** - 6 modes (List, Create, Show Items, Add, Remove, Recent)
**5. `zot_manage_tags`** - 4 modes (List, Search, Add, Remove)
**6. `zot_manage_notes`** - 4 modes (List Annotations, List Notes, Search, Create)
**7. `zot_export`** - 3 modes (Markdown, BibTeX, GraphML)
**8. `zot_manage_database`** - 12 modes (Update, Test, Rebuild, Backup, Restore, Status, Inspect, Statistics, and more) **🆕 NEW**

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
Database operations?         → zot_manage_database  🆕 NEW
```

**Key Principle**: Trust the automatic mode selection. All tools use pattern-based intent detection.

---

## ⚠️ Critical Operational Info

### Auto-Sync with True Incremental Processing

**Automatic ingestion** via polling daemon (60-second intervals) with **true incremental filtering** (ADR-016):
- ✅ **Incremental Item Filtering**: Only loads/processes newly detected items (SQL WHERE IN filtering)
- ✅ **Dynamic Scaling** (ADR-015): Adjusts workers based on job size
  - **1-5 papers**: 2 workers, batch size 10 (typical auto-sync)
  - **6-20 papers**: 4 workers, batch size 20
  - **21+ papers**: 8 workers, batch size 50
- ✅ **99.9% efficiency**: Daemon detects 3 → loads 3 → processes 3 (not all 3,890 items)

**Performance**: 15-20% faster than previous cache-based approach, scales to 10k+ libraries

**Monitoring**: Use `zot_daemon_status` MCP tool for daemon health checks

**Manual updates** also available for immediate control.

### Manual Database Updates Required

**Auto-update DISABLED** for instant server startup (~100ms instead of 3-5 seconds).

⚠️ **You MUST manually update after adding/modifying papers:**

**NEW: Natural Language Interface** (via MCP):
```
zot_manage_database("update database")           # Incremental update
zot_manage_database("test on 10 papers")         # Test with limit
zot_manage_database("force rebuild", confirm=True)  # Full rebuild (auto-backup first)
zot_manage_database("show status")               # Database health
```

**Alternative: CLI Commands**:
```bash
agent-zot update-db --force-rebuild --fulltext  # Full rebuild
agent-zot update-db                              # Incremental
agent-zot get-search-database-status            # Status
```

**Why**: Instant startup improves UX. Explicit updates give better control.
**See**: `decisions.md` ADR-003 for rationale

---

### Orphaned Process Cleanup

**Issue**: Multiple `agent-zot serve` processes can accumulate (each ~1-2GB RAM).

**Symptoms**:
- High CPU usage (hundreds of % on one process)
- "Failed to call tool zot_search" errors in Claude Desktop
- MCP server shows "Connected" but doesn't respond to requests

**Automatic**: `cleanup_orphaned_processes()` runs on server startup

**Manual cleanup** (if needed):
```bash
# Check for orphaned processes
ps aux | grep "agent-zot serve" | grep -v grep

# Kill single process
kill <old_PID>

# Kill multiple processes at once
kill PID1 PID2 PID3 PID4
```

**After cleanup**:
- Restart Claude Desktop (or wait - MCP server auto-restarts on next use)
- Fresh process will start automatically on next tool call

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
- **docs/BACKUP_AUTOMATION.md** - Local backup procedures
- **docs/ICLOUD_BACKUP.md** - iCloud off-site backup guide

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

## 🔧 Unified Database Management

**NEW**: `zot_manage_database()` provides complete database control via natural language.

### 12 Operational Modes

**Update Operations**:
- `"update database"` → Incremental update with fulltext
- `"test on 10 papers"` → Test with limited items
- `"update without fulltext"` → Metadata-only update
- `"force rebuild"` → Full rebuild (requires confirm=True, auto-backup first)

**Backup/Restore Operations**:
- `"backup databases"` → Create local + iCloud backups
- `"backup locally only"` → Skip iCloud sync
- `"show available backups"` → List all backups
- `"restore from latest backup"` → Restore from most recent (requires confirm=True)
- `"restore from icloud"` → Restore from iCloud (requires confirm=True)

**Monitoring Operations**:
- `"show status"` → Database health and stats
- `"show statistics"` → Aggregate stats (Qdrant + Neo4j)
- `"find papers about X"` → Search indexed papers

### Safety Features

**3-Tier Safety Model**:
1. **Destructive operations** (rebuild, restore): Require `confirm=True`
2. **Auto-backup before rebuild**: Protects against data loss
3. **Dry-run preview**: Shows what will happen before restore

### Usage Examples

```python
# Daily operations
zot_manage_database("update database")
zot_manage_database("show status")

# Before major operations
zot_manage_database("backup databases")

# Force rebuild with safety
zot_manage_database("force rebuild", confirm=True)
# ↑ Auto-backup runs first

# Restore from backup
zot_manage_database("restore from latest backup", confirm=True)

# Inspect database
zot_manage_database("find papers about neural networks")
zot_manage_database("show statistics")
```

**See**: `decisions.md` ADR-004 for design rationale

---

## 🔧 System Maintenance

### Backup System

**🆕 NEW: Natural Language Interface** (recommended):
```
zot_manage_database("backup databases")          # Local + iCloud
zot_manage_database("backup locally only")       # Skip iCloud
zot_manage_database("show available backups")    # List backups
zot_manage_database("restore from latest backup", confirm=True)
```

**Alternative: CLI Commands**:
```bash
agent-zot backup-all                 # Complete backup
agent-zot backup-all --local-only    # Local only
python scripts/backup/backup.py list # List backups
```

**Locations**:
- Local: `backups/` (keep last 5)
- iCloud: `~/Library/Mobile Documents/com~apple~CloudDocs/agent-zot-backups/` (keep 30 days)

**Recommendation**: Weekly manual backups, especially before major operations.
**See**: `docs/ICLOUD_BACKUP.md` for complete guide

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

### "Failed to call tool zot_search" errors
**Cause**: Orphaned `agent-zot serve` processes consuming CPU (see Orphaned Process Cleanup section)
**Solution**:
```bash
ps aux | grep "agent-zot serve" | grep -v grep
kill PID1 PID2 PID3  # Kill all old processes
```
Restart Claude Desktop or wait for MCP server to auto-restart.

### "No results found" from graph queries
**Cause**: Neo4j 91% populated (by design). Some specific relationships may not exist.
**Solution**: Expected behavior. Try alternative queries or use Qdrant-based search.

### Memory usage high
**Cause**: BGE-M3 model (~1-2GB) loaded in memory
**Solution**: Normal. If multiple processes exist, kill orphaned ones (see Orphaned Process Cleanup section).

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
- **docs/BACKUP_AUTOMATION.md** - Local backup procedures
- **docs/ICLOUD_BACKUP.md** - iCloud off-site backup guide

---

## 🚀 Auto-Sync Daemon Status

**Current Status**: 🟢 **ACTIVE AND PERSISTENT** (November 6, 2025)

- ✅ All code written (~2,600 lines across 8 files)
- ✅ Documentation complete (ADR-014, AUTO_SYNC_DAEMON.md)
- ✅ CLI commands ready (`agent-zot daemon start/stop/status/install`)
- ✅ MCP tool available (`zot_daemon_status`)
- ✅ Configuration enabled (`auto_sync.enabled: true`)
- ✅ **launchd service installed** - Auto-starts on login, survives crashes
- ✅ Daemon running (PID 57810, detached from terminal)
- ✅ File watcher active (monitoring zotero.sqlite with 30s debounce)
- ⏳ **Pending**: User testing with actual paper addition

**Persistence Guarantees:**
- ✅ Survives terminal closure
- ✅ Survives laptop sleep/wake
- ✅ Auto-starts on laptop boot (after login)
- ✅ Auto-restarts if crashes (KeepAlive enabled)

**Optional Future Enhancements**:
1. Real-time daemon statistics via MCP (queue depth, items/sec processing rate)
2. Web UI dashboard for monitoring (optional, low priority)
3. Email/webhook notifications on ingestion errors (optional)
4. Multi-library support (watch multiple Zotero databases)
5. Smart scheduling (e.g., only run during specific hours to save battery)
6. Ingestion metrics export (Prometheus/Grafana integration)

**See**: `docs/AUTO_SYNC_DAEMON.md` for complete setup guide

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