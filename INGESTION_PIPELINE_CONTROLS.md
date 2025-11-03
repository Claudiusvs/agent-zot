# Agent-Zot Ingestion Pipeline Controls Assessment

**Generated**: November 3, 2025
**System Version**: v2.0 (Post-Consolidation)
**Status**: ✅ Production-Ready with Manual Controls

---

## Executive Summary

Agent-Zot's ingestion pipeline is **intentionally manual** by design (ADR-003). The system provides comprehensive controls through CLI commands and MCP tools, but **auto-update is disabled** for instant server startup and user control.

**Current Configuration**:
- ✅ Auto-update: **DISABLED** (manual control required)
- ✅ Update frequency: **manual** (no scheduled updates)
- ✅ Last update: October 26, 2025 at 13:12:09
- ✅ Full-text extraction: **ENABLED** by default (hardcoded)

---

## 1. Available Pipeline Control Tools

### 1.1 CLI Commands (Primary Interface)

| Command | Purpose | Key Flags | Use Case |
|---------|---------|-----------|----------|
| `agent-zot update-db` | Index/re-index library | `--force-rebuild`, `--fulltext`, `--limit` | Manual updates after adding papers |
| `agent-zot db-status` | Check database status | `--config-path` | Verify system health |
| `agent-zot db-inspect` | Inspect indexed docs | `--limit`, `--filter`, `--stats` | Debug indexing issues |

#### 1.1.1 `update-db` Command Details

**Location**: `src/agent_zot/core/cli.py:156-164`

**Available Options**:
```bash
agent-zot update-db [OPTIONS]

Options:
  --force-rebuild        Force complete rebuild (deletes collection first)
  --limit LIMIT          Process only N items (for testing)
  --fulltext             Extract PDF text (overrides config)
  --config-path PATH     Use alternate config file
```

**Execution Flow**:
1. Loads config from `~/.config/agent-zot/config.json`
2. Creates `ZoteroSemanticSearch` instance
3. Calls `search.update_database()` with provided flags
4. Returns detailed statistics (total, processed, added, updated, skipped, errors, duration)

**Example Usage**:
```bash
# Full rebuild with PDF extraction (recommended)
agent-zot update-db --force-rebuild --fulltext

# Quick test on 10 items
agent-zot update-db --limit 10

# Metadata-only update (no PDF processing)
agent-zot update-db
```

#### 1.1.2 `db-status` Command Details

**Location**: `src/agent_zot/core/cli.py:167-169`

**Output Information**:
- Collection name and document count
- Embedding model in use
- Database path (Qdrant storage location)
- Auto-update configuration
- Update frequency setting
- Last update timestamp
- Whether update is recommended

**Example Usage**:
```bash
agent-zot db-status
```

#### 1.1.3 `db-inspect` Command Details

**Location**: `src/agent_zot/core/cli.py:172-177`

**Available Options**:
```bash
agent-zot db-inspect [OPTIONS]

Options:
  --limit N              Show N records (default: 20)
  --filter TEXT          Filter by title/creators substring
  --show-documents       Display document text snippets
  --stats                Show aggregate statistics
```

**Statistics Provided** (with `--stats` flag):
- Item type distribution
- Fulltext coverage by type (PDF vs HTML)
- Common titles (duplicate detection)
- Total document count

**Example Usage**:
```bash
# Show first 20 documents
agent-zot db-inspect

# Show aggregate stats
agent-zot db-inspect --stats

# Filter for specific papers
agent-zot db-inspect --filter "cognitive" --limit 50
```

---

### 1.2 MCP Server Tools (Secondary Interface)

| Tool | Priority | Purpose | Parameters |
|------|----------|---------|------------|
| `zot_update_search_database` | 🔧 LOW - FALLBACK | Index/re-index library | `force_rebuild`, `extract_fulltext`, `limit` |
| `zot_get_search_database_status` | 🔧 LOW - FALLBACK | Get database status | None |

**Location**: `src/agent_zot/core/server.py:1224-1369`

#### 1.2.1 `zot_update_search_database` Tool

**Description**: "Index or re-index the Zotero library for semantic search. Extracts full PDF text using AI-powered parsing (Docling with OCR)."

**Parameters**:
```python
def update_search_database(
    force_rebuild: bool = False,          # Delete collection and rebuild
    extract_fulltext: bool = True,        # Extract PDF text
    limit: Optional[int] = None,          # Process only N items
    *,
    ctx: Context
) -> str
```

**Use Cases**:
- User asks to "index my library"
- User asks to "update the search database"
- User asks to "enable semantic search"

**Returns**: Markdown-formatted statistics (total, processed, added, updated, skipped, errors, duration)

#### 1.2.2 `zot_get_search_database_status` Tool

**Description**: "Get status information about the semantic search database."

**Parameters**: None (read-only)

**Returns**: Markdown-formatted status including:
- Collection information (name, count, model, path)
- Update configuration (auto_update, frequency, last_update, should_update)

---

## 2. Configuration System

### 2.1 Configuration File

**Location**: `~/.config/agent-zot/config.json`

**Relevant Sections**:

```json
{
  "semantic_search": {
    "update_config": {
      "auto_update": false,              // ⚠️ DISABLED by design
      "update_frequency": "manual",      // Options: "manual", "startup", "daily", "every_N"
      "last_update": "2025-10-26T13:12:09.489293",
      "update_days": 7                   // Interval for scheduled updates (if enabled)
    },
    "docling": {
      "tokenizer": "BAAI/bge-m3",
      "max_tokens": 512,
      "merge_peers": true,
      "num_threads": 2,
      "do_formula_enrichment": false,
      "do_table_structure": true,
      "subprocess_timeout": 3600,
      "ocr": {
        "fallback_enabled": false,
        "min_text_threshold": 100
      }
    }
  }
}
```

### 2.2 Configuration Options Explained

#### 2.2.1 Update Configuration

| Setting | Current Value | Options | Purpose |
|---------|---------------|---------|---------|
| `auto_update` | `false` | `true`, `false` | Enable/disable automatic updates |
| `update_frequency` | `"manual"` | `"manual"`, `"startup"`, `"daily"`, `"every_N"` | When to trigger updates |
| `last_update` | `"2025-10-26T13:12:09.489293"` | ISO 8601 timestamp | Track last update time |
| `update_days` | `7` | Integer | Days between scheduled updates |

**⚠️ Important**: Even if `auto_update` is enabled, the update logic is **commented out** in the server startup code (see Section 3.1).

#### 2.2.2 Docling Parser Configuration

| Setting | Current Value | Purpose |
|---------|---------------|---------|
| `tokenizer` | `"BAAI/bge-m3"` | Tokenizer for chunking (matches embedding model) |
| `max_tokens` | `512` | Chunk size for embeddings |
| `merge_peers` | `true` | Merge adjacent similar chunks |
| `num_threads` | `2` | Parallel PDF processing threads |
| `do_formula_enrichment` | `false` | Convert LaTeX formulas to text |
| `do_table_structure` | `true` | Parse table structures |
| `subprocess_timeout` | `3600` | Timeout for PDF parsing (seconds) |

#### 2.2.3 OCR Configuration

| Setting | Current Value | Purpose |
|---------|---------------|---------|
| `fallback_enabled` | `false` | Use OCR if PDF text extraction fails |
| `min_text_threshold` | `100` | Minimum chars before triggering OCR |

---

## 3. Update Pipeline Implementation

### 3.1 Automatic Update Logic (Currently Disabled)

**Location**: `src/agent_zot/core/server.py:164-183`

**Current State**: **COMMENTED OUT**

```python
# COMMENTED OUT - Auto-update at startup disabled
# Rationale: Instant startup (~100ms) vs 3-5 second delay
# Users must manually run: agent-zot update-db --force-rebuild --fulltext
#
# Code that was disabled:
#     async def background_update():
#         try:
#             if search.should_update_database():
#                 logger.info("Auto-update triggered at startup")
#                 try:
#                     stats = search.update_database(extract_fulltext=True)
#                     logger.info(f"Auto-update completed: {stats}")
#                 except Exception as e:
#                     logger.error(f"Auto-update failed: {e}")
#         except Exception as e:
#             logger.error(f"Error checking update status: {e}")
#
#     asyncio.create_task(background_update())
```

**Architectural Decision**: ADR-003 in `decisions.md`

**Rationale**:
1. **User Control**: Explicit updates prevent unexpected delays
2. **Performance**: Instant server startup (~100ms vs 3-5 seconds)
3. **Resource Management**: PDF extraction is resource-intensive
4. **Debugging**: Easier to diagnose issues with manual control

### 3.2 Manual Update Flow

**Entry Point**: `ZoteroSemanticSearch.update_database()`
**Location**: `src/agent_zot/search/semantic.py:830-1000+`

**Execution Sequence**:

```
1. Load configuration
   ├─ Read force_rebuild from config (default: False)
   └─ Read extract_fulltext from config (default: True, hardcoded)

2. Initialize statistics tracking
   ├─ total_items, processed_items, added_items
   ├─ updated_items, skipped_items, errors
   └─ start_time, duration

3. Reset collection (if force_rebuild=True)
   └─ Delete and recreate Qdrant collection

4. Get items from source
   ├─ Local mode: Query Zotero SQLite database
   └─ API mode: Fetch from Zotero Web API

5. STREAMING BATCH PROCESSING (local mode only)
   ├─ Get metadata-only list (fast, no fulltext yet)
   ├─ Process in batches of 50 items:
   │   ├─ Extract fulltext for batch
   │   ├─ Embed documents
   │   ├─ Upload to Qdrant
   │   └─ Extract entities to Neo4j
   └─ Progress reporting every 10 items

6. Save update configuration
   └─ Write last_update timestamp to config

7. Return statistics
```

**Key Implementation Details**:

```python
def update_database(self,
                   force_full_rebuild: Optional[bool] = None,
                   limit: Optional[int] = None,
                   extract_fulltext: Optional[bool] = None) -> Dict[str, Any]:
    """Update semantic search database with Zotero items."""

    # Read force_rebuild from config if not provided
    if force_full_rebuild is None:
        force_full_rebuild = self.update_config.get("force_rebuild", False)

    # HARDCODED: Always extract fulltext for local mode
    if extract_fulltext is None:
        extract_fulltext = True  # Primary use case

    # Reset collection if requested
    if force_full_rebuild:
        self.qdrant_client.reset_collection()

    # STREAMING BATCH PROCESSING
    if extract_fulltext and is_local_mode():
        metadata_items = self._get_item_metadata_list(limit=limit)

        batch_size = 50
        for i in range(0, len(metadata_items), batch_size):
            batch = metadata_items[i:i + batch_size]

            # Extract fulltext for THIS batch only
            batch_with_fulltext = self._extract_batch_fulltext(batch)

            # Process batch: embed → Qdrant → Neo4j
            batch_stats = self._process_item_batch(batch_with_fulltext, force_full_rebuild)

            # Update statistics
            stats["processed_items"] += batch_stats["processed"]
            stats["added_items"] += batch_stats["added"]
            # ...

    # Save timestamp
    self.update_config["last_update"] = datetime.now().isoformat()
    self._save_update_config()

    return stats
```

### 3.3 Should Update Logic

**Location**: `src/agent_zot/search/semantic.py:274-304`

**Implementation**:

```python
def should_update_database(self) -> bool:
    """Check if database should be updated based on configuration."""

    # Check if auto-update is enabled
    if not self.update_config.get("auto_update", False):
        return False  # ⚠️ Currently always False

    frequency = self.update_config.get("update_frequency", "manual")

    if frequency == "manual":
        return False

    elif frequency == "startup":
        return True  # Update every time server starts

    elif frequency == "daily":
        last_update = self.update_config.get("last_update")
        if not last_update:
            return True

        last_update_date = datetime.fromisoformat(last_update)
        return datetime.now() - last_update_date >= timedelta(days=1)

    elif frequency.startswith("every_"):
        # Extract days from "every_7", "every_30", etc.
        try:
            days = int(frequency.split("_")[1])
            last_update = self.update_config.get("last_update")
            if not last_update:
                return True

            last_update_date = datetime.fromisoformat(last_update)
            return datetime.now() - last_update_date >= timedelta(days=days)
        except (ValueError, IndexError):
            return False

    return False
```

**Supported Frequencies**:
- `"manual"`: Never auto-update (current setting)
- `"startup"`: Update every time MCP server starts
- `"daily"`: Update if last update was >24 hours ago
- `"every_N"`: Update if last update was >N days ago (e.g., `"every_7"`, `"every_30"`)

---

## 4. Current System Status

### 4.1 Database State

**Qdrant**:
- Collection: `zotero_library_qdrant`
- Document count: **234,153 chunks**
- Embedding model: `BAAI/bge-m3`
- Database path: Docker volume `agent-zot-qdrant-data`
- Last update: October 26, 2025 at 13:12:09

**Neo4j**:
- Database: `neo4j`
- Node count: **25,184**
- Relationship count: **134,068**
- Population: **91% functional** (by design, some specific relationships may not exist)
- Last update: Same as Qdrant (synchronized)

**Zotero**:
- Total items: **7,390**
- Source database: `/Users/claudiusv.schroder/zotero_database/zotero.sqlite`

**Parse Cache**:
- Location: `~/.cache/agent-zot/parsed_docs.db`
- Size: **623 MB**
- Cached documents: **2,519**

### 4.2 Update Configuration Status

```json
{
  "auto_update": false,              // ⚠️ DISABLED
  "update_frequency": "manual",      // ⚠️ MANUAL ONLY
  "last_update": "2025-10-26T13:12:09.489293",
  "update_days": 7                   // Not used (auto_update is false)
}
```

**Interpretation**:
- ✅ Auto-update is **intentionally disabled**
- ✅ Updates must be **manually triggered**
- ✅ Last update was **8 days ago** (within acceptable range)
- ⚠️ No scheduled updates configured

---

## 5. Pipeline Control Capabilities

### 5.1 START Controls

**There is NO automatic start/restart pipeline control.**

The pipeline is triggered **on-demand** via:

1. **CLI command**: `agent-zot update-db`
2. **MCP tool call**: `zot_update_search_database()`

**Both methods start the same `update_database()` function.**

### 5.2 STOP Controls

**There is NO explicit stop control.**

**Current Limitation**: Once an update starts, it runs to completion. There is no pause, cancel, or interrupt mechanism.

**Workarounds**:
1. **Kill process**: `Ctrl+C` during CLI execution (data may be incomplete)
2. **Limit scope**: Use `--limit N` flag to process fewer items
3. **Batch monitoring**: Watch batch progress logs to estimate completion time

### 5.3 PAUSE/RESUME Controls

**❌ NOT IMPLEMENTED**

**Current State**: No pause/resume capability exists.

**Architectural Note**: The streaming batch processing design (introduced in v2.0) processes 50-item batches sequentially. Each batch goes through the full pipeline (extract → embed → Qdrant → Neo4j). While this improves memory efficiency, it doesn't provide pause points.

### 5.4 INCREMENTAL UPDATE Controls

**✅ SUPPORTED** (default behavior when `force_rebuild=False`)

**How it works**:
1. System queries Qdrant for existing documents
2. Compares item keys with Zotero library
3. Only processes **new or modified items**
4. Skips items that already exist in Qdrant

**Example**:
```bash
# Incremental update (default)
agent-zot update-db

# Force full rebuild (delete and re-index everything)
agent-zot update-db --force-rebuild
```

### 5.5 SELECTIVE UPDATE Controls

**✅ SUPPORTED** via `--limit` flag

**Use Cases**:
- Testing: `agent-zot update-db --limit 10`
- Gradual updates: `agent-zot update-db --limit 100`
- Resource management: Process in smaller batches

**Limitation**: Cannot select **specific items** or **item types**. Limit applies to first N items from Zotero library.

### 5.6 MONITORING Controls

**✅ Available via multiple interfaces**:

1. **CLI Status Check**:
   ```bash
   agent-zot db-status
   ```

2. **CLI Inspection**:
   ```bash
   agent-zot db-inspect --stats
   ```

3. **MCP Tool**:
   ```python
   zot_get_search_database_status()
   ```

4. **Log Output** (during update):
   - Total items to index
   - Current batch number
   - Items processed count
   - Progress milestones (every 10 items)
   - Error counts

**Example Output**:
```
Total items to index: 2,519
Using STREAMING BATCH mode: extract → embed → Qdrant → Neo4j per batch
Processing streaming batch 1: items 1-50
Processing streaming batch 2: items 51-100
...
Progress: 10 items processed (milestone reached)
Progress: 20 items processed (milestone reached)
```

### 5.7 ROLLBACK Controls

**❌ NOT IMPLEMENTED**

**Current State**: No rollback or version control for database state.

**Workarounds**:
1. **Manual backup before update**:
   ```bash
   agent-zot backup-all
   ```

2. **Restore from backup** (see `docs/ICLOUD_BACKUP.md`):
   ```bash
   # Stop containers
   docker stop agent-zot-qdrant agent-zot-neo4j

   # Restore Qdrant
   docker run --rm -v agent-zot-qdrant-data:/qdrant/storage \
     -v /path/to/backup:/backup alpine sh -c "cd /qdrant && tar xzf /backup/snapshot.tar.gz"

   # Restore Neo4j
   docker cp /path/to/backup/neo4j.dump agent-zot-neo4j:/tmp/
   docker exec agent-zot-neo4j neo4j-admin database load --from-path=/tmp/neo4j.dump neo4j --overwrite-destination=true

   # Restart containers
   docker start agent-zot-qdrant agent-zot-neo4j
   ```

---

## 6. Missing Pipeline Controls

### 6.1 What's NOT Available

| Control | Status | Reason |
|---------|--------|--------|
| **Pause/Resume** | ❌ Not implemented | Architectural limitation (batch processing) |
| **Cancel/Abort** | ❌ Not implemented | Must kill process (incomplete data) |
| **Rollback** | ❌ Not implemented | No version control (use backups) |
| **Selective Item Update** | ❌ Not implemented | Cannot filter by item type or key |
| **Priority Queue** | ❌ Not implemented | Items processed in library order |
| **Parallel Pipeline** | ❌ Not implemented | Sequential batch processing only |
| **Auto-Retry Failed Items** | ⚠️ Partial | Errors logged but not automatically retried |
| **Real-Time Progress UI** | ❌ Not implemented | CLI progress logs only |

### 6.2 Potential Improvements

**High-Value Additions**:

1. **Pause/Resume Capability**:
   - Save batch checkpoint to disk
   - Allow interruption between batches
   - Resume from last completed batch

2. **Selective Item Filtering**:
   ```bash
   agent-zot update-db --item-type journalArticle
   agent-zot update-db --item-keys ABC123,XYZ789
   agent-zot update-db --modified-since "2025-10-01"
   ```

3. **Automatic Retry Failed Items**:
   - Track failed items in database
   - Provide `--retry-failed` flag
   - Exponential backoff for transient errors

4. **Progress Tracking Database**:
   - Persistent state for long-running updates
   - Resume after crashes
   - Historical update logs

**Low-Priority Additions**:

1. **Real-Time Web UI**:
   - Live progress visualization
   - Batch completion percentages
   - Error reporting dashboard

2. **Scheduled Updates** (if auto-update is re-enabled):
   - Cron-like scheduling
   - Off-peak update windows
   - Configurable resource limits

---

## 7. Common Workflows

### 7.1 Initial Library Indexing

**Scenario**: Setting up agent-zot for first time

**Steps**:
```bash
# 1. Check current status
agent-zot db-status

# 2. Run full rebuild with PDF extraction
agent-zot update-db --force-rebuild --fulltext

# 3. Verify results
agent-zot db-status
agent-zot db-inspect --stats
```

**Expected Time**: ~18 seconds per PDF × number of papers
**Example**: 2,500 papers ≈ 12.5 hours (can run overnight)

### 7.2 Adding New Papers

**Scenario**: Added 20 new papers to Zotero

**Steps**:
```bash
# 1. Run incremental update (only processes new items)
agent-zot update-db --fulltext

# 2. Verify new papers are indexed
agent-zot db-inspect --filter "new paper title"
```

**Expected Time**: ~6 minutes (20 papers × 18 seconds)

### 7.3 Testing Configuration Changes

**Scenario**: Modified Docling settings, want to test

**Steps**:
```bash
# 1. Test on small sample
agent-zot update-db --limit 10 --force-rebuild

# 2. Inspect results
agent-zot db-inspect --limit 10 --show-documents

# 3. If satisfied, run full update
agent-zot update-db --force-rebuild --fulltext
```

### 7.4 Troubleshooting Incomplete Indexing

**Scenario**: Some papers missing from search results

**Steps**:
```bash
# 1. Check database status
agent-zot db-status

# 2. Inspect indexed documents
agent-zot db-inspect --stats

# 3. Look for missing papers
agent-zot db-inspect --filter "expected paper title"

# 4. Force rebuild if data is corrupt
agent-zot update-db --force-rebuild --fulltext
```

### 7.5 Emergency Rollback

**Scenario**: Update corrupted database, need to restore

**Steps**:
```bash
# 1. Stop agent-zot MCP server (restart Claude Desktop)

# 2. Create backup of current state (just in case)
agent-zot backup-all --local-only

# 3. Follow rollback procedure from Section 5.7
# (Restore from iCloud or local backup)

# 4. Verify restoration
agent-zot db-status
agent-zot db-inspect --stats

# 5. Restart Claude Desktop
```

---

## 8. Architectural Decisions

### 8.1 ADR-003: Manual Updates Only

**Decision**: Disable auto-update at server startup

**Rationale**:
1. **Performance**: Instant startup (~100ms) vs 3-5 second delay
2. **User Control**: Explicit updates prevent unexpected delays
3. **Resource Management**: PDF extraction is CPU/memory intensive
4. **Debugging**: Easier to diagnose issues with manual triggers

**Trade-offs**:
- ✅ Pro: Fast server startup, predictable behavior
- ❌ Con: Users must remember to update after adding papers

**Implementation**: See Section 3.1 (commented-out auto-update code)

### 8.2 ADR-XXX: Streaming Batch Processing

**Decision**: Process items in 50-item batches through full pipeline

**Rationale**:
1. **Memory Efficiency**: Don't load all PDFs into memory at once
2. **Progress Visibility**: Log progress every batch
3. **Partial Success**: Some batches succeed even if others fail
4. **Resource Limits**: Prevent memory exhaustion on large libraries

**Trade-offs**:
- ✅ Pro: Handles large libraries (7,000+ items)
- ✅ Pro: Visible progress reporting
- ❌ Con: Cannot pause between batches (yet)
- ❌ Con: Sequential processing (not parallelized)

**Implementation**: See Section 3.2 (update_database flow)

### 8.3 ADR-XXX: Hardcoded Full-Text Extraction

**Decision**: Default `extract_fulltext=True` for local mode

**Rationale**:
1. **Primary Use Case**: Agent-zot is designed for local Zotero libraries
2. **Best Results**: Full-text extraction provides highest quality semantic search
3. **User Expectation**: Users expect comprehensive indexing

**Trade-offs**:
- ✅ Pro: Best semantic search quality
- ✅ Pro: Matches user expectations
- ❌ Con: Slower updates (can be overridden with CLI flag)

**Implementation**: `src/agent_zot/search/semantic.py:850-854`

---

## 9. Configuration Recommendations

### 9.1 For Fast Startup (Current Configuration)

**Use Case**: Development, frequent server restarts

**Settings**:
```json
{
  "update_config": {
    "auto_update": false,
    "update_frequency": "manual"
  }
}
```

**Workflow**: Manually run `agent-zot update-db` after adding papers

### 9.2 For Auto-Update (Not Recommended)

**Use Case**: Production with stable library

**Settings**:
```json
{
  "update_config": {
    "auto_update": true,
    "update_frequency": "daily",
    "update_days": 1
  }
}
```

**⚠️ Warning**: Would need to uncomment auto-update code in `server.py:164-183`

### 9.3 For Scheduled Updates (Not Recommended)

**Use Case**: Weekly library updates

**Settings**:
```json
{
  "update_config": {
    "auto_update": true,
    "update_frequency": "every_7",
    "update_days": 7
  }
}
```

**⚠️ Warning**: Would need to uncomment auto-update code in `server.py:164-183`

### 9.4 For Testing/Development

**Use Case**: Frequent configuration changes

**Settings**: Keep auto-update disabled, use:
```bash
# Quick test
agent-zot update-db --limit 10

# Full rebuild
agent-zot update-db --force-rebuild
```

---

## 10. Summary & Recommendations

### 10.1 What's Working Well

✅ **Manual control system** provides predictable, fast server startup
✅ **CLI commands** offer comprehensive pipeline management
✅ **Streaming batch processing** handles large libraries efficiently
✅ **Status monitoring** provides visibility into system state
✅ **Incremental updates** minimize processing time for new papers

### 10.2 What's Missing

❌ **Pause/Resume**: Cannot interrupt long-running updates
❌ **Selective Updates**: Cannot filter by item type or key
❌ **Rollback**: No version control (must use backups)
❌ **Auto-Retry**: Failed items require manual reprocessing

### 10.3 Recommended Actions

**Immediate (Keep Current Approach)**:
1. ✅ Continue using manual updates via CLI
2. ✅ Run `agent-zot update-db --force-rebuild --fulltext` weekly
3. ✅ Use `agent-zot backup-all` before major updates
4. ✅ Monitor status with `agent-zot db-status`

**Short-Term Improvements**:
1. Implement **pause/resume** using batch checkpoints
2. Add **selective item filtering** flags to CLI
3. Add **automatic retry** for failed items
4. Create **progress tracking database** for crash recovery

**Long-Term Improvements**:
1. Build **real-time progress UI** (web dashboard)
2. Implement **parallel batch processing** (multiple workers)
3. Add **incremental Neo4j updates** (currently full rebuild only)
4. Design **rollback system** with database versioning

### 10.4 User Guidance

**For New Users**:
```bash
# Initial setup (one-time, long-running)
agent-zot update-db --force-rebuild --fulltext

# Check status
agent-zot db-status
```

**For Regular Maintenance**:
```bash
# Weekly incremental update (processes only new papers)
agent-zot update-db --fulltext

# Monthly backup
agent-zot backup-all
```

**For Troubleshooting**:
```bash
# Check what's indexed
agent-zot db-inspect --stats

# Find specific paper
agent-zot db-inspect --filter "paper title"

# Force full rebuild if issues persist
agent-zot update-db --force-rebuild --fulltext
```

---

## 11. Related Documentation

- **CLAUDE.md** - Quick reference for current system state
- **decisions.md** - Architectural decisions (ADR-003 for manual updates)
- **docs/QUICK_REFERENCE.md** - Commands and configuration
- **docs/ICLOUD_BACKUP.md** - Backup and restoration procedures
- **src/agent_zot/core/cli.py** - CLI implementation
- **src/agent_zot/core/server.py** - MCP server tools
- **src/agent_zot/search/semantic.py** - Update pipeline implementation

---

**Last Updated**: November 3, 2025
**Reviewed By**: Claude (Sonnet 4.5)
**Status**: ✅ Production Assessment Complete
