# Implementation Plan: `zot_manage_database()` Unified Tool

**Created**: November 3, 2025
**Status**: 📋 Ready for Implementation
**Estimated Effort**: 6-8 hours
**Priority**: High-Value Enhancement

---

## Executive Summary

Create **one elegant unified MCP tool** for all database management operations, following the established pattern of agent-zot's 7 unified research tools. This tool will provide **natural language control** over pipeline management, backup/restore operations, and database monitoring.

**Philosophy**: "One tool to manage them all" - consistent with `zot_search`, `zot_summarize`, `zot_explore_graph`, etc.

---

## Table of Contents

1. [Tool Specification](#tool-specification)
2. [Architecture](#architecture)
3. [Implementation Phases](#implementation-phases)
4. [Safety Features](#safety-features)
5. [File Changes](#file-changes)
6. [Testing Plan](#testing-plan)
7. [Documentation Updates](#documentation-updates)
8. [Rollback Plan](#rollback-plan)

---

## Tool Specification

### Tool Name
`zot_manage_database()`

### Tool Description
```
🔧 Unified database management - update, backup, restore, inspect, and monitor
the Qdrant and Neo4j databases using natural language
```

### Parameters
```python
def manage_database(
    query: str,                          # Natural language command
    force_mode: Optional[str] = None,    # Override auto-detection
    confirm: bool = False,               # Required for destructive operations (rebuild, restore)
    *,
    ctx: Context
) -> str
```

### Replaces These Existing Tools
1. `zot_update_search_database()` - Update/rebuild database
2. `zot_get_search_database_status()` - Database status

### Adds These New Capabilities
3. **Backup operations** (new)
4. **Restore operations** (new)
5. **Database inspection** (new - wraps CLI `db-inspect`)
6. **Graceful cancellation** (new)
7. **Auto-retry failed items** (new)
8. **Modified-since filtering** (new)
9. **Auto-backup before force-rebuild** (new safety feature)

---

## Architecture

### Supported Modes (12 Total)

| Category | Mode | Query Examples | Safety | Confirm? |
|----------|------|----------------|--------|----------|
| **Update** | `update` | "update database", "index new papers" | ✅ Safe | No |
| **Update** | `rebuild` | "force rebuild", "start from scratch" | 🔴 Destructive | **YES** |
| **Update** | `test` | "test on 10 papers", "quick test" | ✅ Safe | No |
| **Update** | `modified_since` | "papers from last week", "since Nov 1" | ✅ Safe | No |
| **Update** | `retry` | "retry failed", "reprocess errors" | ✅ Safe | No |
| **Update** | `metadata_only` | "update without fulltext" | ✅ Safe | No |
| **Backup/Restore** | `backup` | "backup databases", "create backup" | ✅ Safe | No |
| **Backup/Restore** | `restore` | "restore from backup", "undo rebuild" | 🔴 Destructive | **YES** |
| **Backup/Restore** | `list_backups` | "show backups", "available backups" | ✅ Safe | No |
| **Monitor** | `status` | "show status", "database info" | ✅ Safe | No |
| **Monitor** | `inspect` | "inspect database", "find paper X" | ✅ Safe | No |
| **Monitor** | `statistics` | "show stats", "aggregate info" | ✅ Safe | No |
| **Control** | `cancel` | "stop update", "cancel indexing" | ✅ Safe | No |

### Intent Detection Strategy

**Pattern-based matching** (fast, transparent, no LLM needed):

```python
query_lower = query.lower()

# Priority order (most specific first):
if "restore" in query_lower or "undo" in query_lower:
    mode = "restore"
elif "backup" in query_lower or "save" in query_lower:
    mode = "backup"
elif "rebuild" in query_lower or "force" in query_lower:
    mode = "rebuild"
elif "test" in query_lower and number_found:
    mode = "test"
# ... etc
else:
    mode = "update"  # Safe default
```

### Parameter Extraction

**Regex-based extraction** from natural language:

```python
def _extract_number(query: str) -> Optional[int]:
    """Extract number for limit: 'test on 10 papers' → 10"""
    match = re.search(r'\b(\d+)\b', query)
    return int(match.group(1)) if match else None

def _extract_date(query: str) -> Optional[str]:
    """Extract date: 'since November 1' → '2025-11-01'"""
    # Parse relative dates: "last week", "yesterday", "3 days ago"
    # Parse absolute dates: "November 1", "2025-11-01", "Nov 1"
    # Return ISO format string or None

def _extract_filter(query: str) -> Optional[str]:
    """Extract filter text: 'find papers about attention' → 'attention'"""
    # Extract text after "about", "for", "containing", etc.

def _extract_backup_source(query: str) -> str:
    """Extract backup source: 'restore from icloud' → 'icloud'"""
    if "icloud" in query.lower():
        return "icloud"
    elif timestamp_pattern_found:
        return timestamp
    else:
        return "latest"
```

---

## Implementation Phases

### Phase 1: Core Tool Structure (1-2 hours)

**Files to Create/Modify**:
- `src/agent_zot/core/server.py` - Add new tool definition

**Tasks**:
1. Define `manage_database()` function signature
2. Implement intent detection logic (pattern matching)
3. Implement parameter extraction helpers
4. Add safety checks for destructive operations
5. Wire up to existing functionality (update, status)

**Deliverable**: Tool responds to basic modes (update, status)

---

### Phase 2: Backup Operations (1 hour)

**Files to Modify**:
- `src/agent_zot/core/server.py` - Add backup mode handlers

**Tasks**:
1. Implement `_execute_backup()` helper (wrapper around `BackupManager`)
2. Implement `_list_available_backups()` helper
3. Add iCloud sync integration (wrapper around script)
4. Format backup results for MCP response

**Deliverable**: Tool can create backups and list them

**Dependencies**: Existing `src/agent_zot/utils/backup.py` (already exists)

---

### Phase 3: Restore Operations (3-4 hours)

**Files to Create/Modify**:
- `src/agent_zot/utils/backup.py` - Add restore methods
- `src/agent_zot/core/server.py` - Add restore mode handler

**Tasks**:
1. Create `BackupManager.restore_qdrant_snapshot()` method
2. Create `BackupManager.restore_neo4j_dump()` method
3. Create `BackupManager.restore_all()` method
4. Implement `_execute_restore()` helper in server
5. Add dry-run preview functionality
6. Add safety confirmations
7. Test restore workflow end-to-end

**Deliverable**: Tool can restore from backups with safety checks

**New Code**: ~150 lines in `backup.py`, ~80 lines in `server.py`

---

### Phase 4: Enhanced Update Features (1-2 hours)

**Files to Modify**:
- `src/agent_zot/search/semantic.py` - Add new parameters to `update_database()`
- `src/agent_zot/core/server.py` - Add enhanced mode handlers

**Tasks**:
1. Add `modified_since` parameter to `update_database()`
2. Add `retry_failed_only` parameter to `update_database()`
3. Add `cancel_flag` parameter to `update_database()`
4. Implement failed items tracking (SQLite cache)
5. Implement date filtering logic
6. Add cancel checks between batches
7. Update `_execute_update()` helper to use new parameters

**Deliverable**: Tool supports retry, modified-since filter, cancellation

**New Code**: ~100 lines in `semantic.py`, ~50 lines in `server.py`

---

### Phase 5: Auto-Backup Before Rebuild (30 minutes)

**Files to Modify**:
- `src/agent_zot/core/server.py` - Enhance rebuild mode handler

**Tasks**:
1. Add automatic backup call before rebuild
2. Add backup success verification
3. Add abort logic if backup fails
4. Format backup confirmation in output

**Deliverable**: Force rebuild always backs up first

**New Code**: ~20 lines in `server.py`

---

### Phase 6: Database Inspection (1 hour)

**Files to Modify**:
- `src/agent_zot/core/server.py` - Add inspect/statistics modes

**Tasks**:
1. Implement `_inspect_database()` helper (wrapper around Qdrant queries)
2. Implement `_get_database_statistics()` helper (aggregate stats)
3. Add filter parameter support
4. Format inspection results for MCP response

**Deliverable**: Tool can inspect indexed documents and show statistics

**New Code**: ~80 lines in `server.py`

---

### Phase 7: Deprecation & Documentation (1 hour)

**Files to Modify**:
- `src/agent_zot/core/server.py` - Mark old tools as deprecated
- `CLAUDE.md` - Update tool reference
- `docs/development/TOOL_HIERARCHY.md` - Update architecture docs
- `decisions.md` - Add ADR for unified tool

**Tasks**:
1. Add deprecation notices to old tools
2. Update tool descriptions to point to new unified tool
3. Update CLAUDE.md quick reference
4. Document architectural decision
5. Update tool count (38 → 37 tools, 7 → 8 unified tools)

**Deliverable**: All documentation reflects new tool

---

## Safety Features

### 1. Mandatory Confirmation for Destructive Operations

**Operations Requiring `confirm=True`**:
- ✅ `rebuild` - Deletes all vectors and entities
- ✅ `restore` - Replaces current databases with backup

**Flow**:
```
User: "force rebuild"
→ Tool returns warning with detailed info
→ User must run with confirm=True
→ Tool executes operation

If user forgets confirm=True:
→ Tool shows error and instructions
```

**Implementation**:
```python
if mode == "rebuild" and not confirm:
    return """🔴 CONFIRMATION REQUIRED

This will delete all data. To proceed:
zot_manage_database("force rebuild", confirm=True)
"""
```

### 2. Auto-Backup Before Force Rebuild

**Flow**:
```
User: "force rebuild" (with confirm=True)
→ Tool automatically triggers backup
→ Waits for backup success
→ If backup fails, aborts rebuild
→ If backup succeeds, proceeds with rebuild
```

**Implementation**:
```python
if mode == "rebuild" and confirm:
    backup_result = _execute_backup(include_icloud=True, ctx=ctx)
    if "❌" in backup_result:
        return "Backup failed - aborting for safety"

    # Safe to rebuild now
    return _execute_update(force_rebuild=True, ...)
```

### 3. Dry-Run Preview for Restore

**Flow**:
```
User: "restore from backup"
→ Tool shows what will be restored (dry-run)
→ Shows timestamp, size, node counts
→ Warns about data loss
→ User must confirm with confirm=True
```

### 4. Cancel Flag for Long Operations

**Flow**:
```
User: "update database" (starts long operation)
→ Processing batch 1 of 50...
→ User: "cancel update"
→ Tool sets cancel flag
→ Between batches, operation checks flag
→ Stops gracefully after current batch
```

**Implementation**:
```python
# In update_database():
for batch in batches:
    if cancel_flag and cancel_flag.get("requested"):
        logger.info("Cancellation requested, stopping")
        break
    # ... process batch
```

---

## File Changes

### Files to Modify

**1. `src/agent_zot/core/server.py`**
- Add `manage_database()` tool (~300 lines)
- Add helper functions (~200 lines)
- Deprecate old tools (~20 lines)
- **Total**: ~520 new lines

**2. `src/agent_zot/search/semantic.py`**
- Add `modified_since` parameter (~10 lines)
- Add `retry_failed_only` parameter (~30 lines)
- Add `cancel_flag` parameter (~10 lines)
- Implement failed items tracking (~50 lines)
- **Total**: ~100 new lines

**3. `src/agent_zot/utils/backup.py`**
- Add `restore_qdrant_snapshot()` method (~50 lines)
- Add `restore_neo4j_dump()` method (~70 lines)
- Add `restore_all()` method (~30 lines)
- **Total**: ~150 new lines

### Files to Update (Documentation)

**4. `CLAUDE.md`**
- Update tool count (38 → 37)
- Update unified tool count (7 → 8)
- Add `zot_manage_database()` to tool list
- Deprecate old tool references

**5. `docs/development/TOOL_HIERARCHY.md`**
- Update architecture diagram
- Document new unified tool

**6. `decisions.md`**
- Add ADR-004: Unified Database Management Tool
- Document rationale for consolidation

**7. `progress.md`**
- Log completion of unified tool implementation
- Document phase timeline

---

## Testing Plan

### Unit Tests (Optional - if time permits)

**Test Coverage**:
- Intent detection for all 12 modes
- Parameter extraction (numbers, dates, filters)
- Safety checks (confirmation required)
- Backup/restore operations

**Files to Create**:
- `tests/test_database_management.py`

### Manual Testing Checklist

**Update Operations**:
- [ ] "update database" → Incremental update works
- [ ] "force rebuild" without confirm → Shows warning
- [ ] "force rebuild" with confirm → Auto-backup → Rebuild works
- [ ] "test on 10 papers" → Limits to 10 items
- [ ] "papers from last week" → Filters by date
- [ ] "retry failed items" → Reprocesses failures
- [ ] "update without fulltext" → Metadata-only mode

**Backup/Restore Operations**:
- [ ] "backup databases" → Creates local + iCloud backups
- [ ] "backup locally only" → Skips iCloud sync
- [ ] "show available backups" → Lists backups
- [ ] "restore from backup" without confirm → Shows preview
- [ ] "restore from backup" with confirm → Restores successfully

**Monitoring Operations**:
- [ ] "show status" → Database health info
- [ ] "inspect database" → Shows indexed papers
- [ ] "find papers about attention" → Filters by keyword
- [ ] "show statistics" → Aggregate stats

**Control Operations**:
- [ ] Start long update → "cancel update" → Stops gracefully

**Error Handling**:
- [ ] Invalid query → Defaults to safe mode
- [ ] Backup failure during rebuild → Aborts safely
- [ ] Restore from non-existent backup → Error message
- [ ] Cancel when no operation running → Graceful message

---

## Documentation Updates

### CLAUDE.md Updates

**Section to Update**: "🔥 The 7 Unified Tools" → "🔥 The 8 Unified Tools"

**Add**:
```markdown
### Management Tool (1)

**8. `zot_manage_database` - Managing Databases**
- 12 execution modes: update, rebuild, test, modified_since, retry, metadata_only, backup, restore, list_backups, status, inspect, statistics, cancel
- Natural language interface for all database operations
- Auto-backup before destructive operations
- Replaces 2 legacy tools
```

**Update Tool Count**:
- Total tools: 38 → 37 (consolidation of 2 into 1)
- Primary unified tools: 7 → 8

### Tool Hierarchy Documentation

**File**: `docs/development/TOOL_HIERARCHY.md`

**Add Section**:
```markdown
## Database Management Tools (1 Unified)

### zot_manage_database (Unified Smart Tool)

**Modes**: 12 (update, rebuild, test, modified_since, retry, metadata_only, backup, restore, list_backups, status, inspect, statistics, cancel)

**Intent Detection**: Pattern-based keyword matching
**Parameter Extraction**: Regex-based from natural language
**Safety**: Confirmation required for rebuild/restore

**Backends Used**:
- Qdrant (vector database)
- Neo4j (knowledge graph)
- Local file system (backups)
- iCloud Drive (off-site backups)
```

### Architectural Decision Record

**File**: `decisions.md`

**Add ADR-004**:
```markdown
## ADR-004: Unified Database Management Tool

**Date**: November 3, 2025
**Status**: Approved

### Context
Agent-zot has 2 separate MCP tools for database management (update_search_database, get_search_database_status), but lacks natural language control, backup/restore functionality, and advanced pipeline features.

### Decision
Create `zot_manage_database()` unified tool following the established pattern of 7 unified research tools.

### Rationale
1. **Consistency**: Matches architecture of zot_search, zot_summarize, zot_explore_graph
2. **Natural Language**: Users can say "force rebuild" instead of remembering tool names
3. **Safety**: Auto-backup before destructive operations prevents data loss
4. **Completeness**: Adds missing backup/restore functionality
5. **Simplicity**: 1 tool instead of multiple scattered tools

### Consequences
- Consolidates 2 existing tools into 1 unified tool
- Adds 10 new operational modes
- Requires confirmation for destructive operations (rebuild, restore)
- Automatically backs up before force rebuild
- Total unified tools: 7 → 8

### Implementation
- Pattern-based intent detection (no LLM needed)
- Regex-based parameter extraction
- Wrappers around existing CLI functionality
- ~770 new lines of code
```

---

## Rollback Plan

### If Implementation Fails

**Immediate Rollback**:
1. Remove new tool definition from `server.py`
2. Keep old tools (`zot_update_search_database`, `zot_get_search_database_status`) active
3. Revert any changes to `semantic.py` and `backup.py`

**Recovery**:
- No data loss (tool only manages existing data)
- Old tools still functional
- Can retry implementation after debugging

### If Tool Has Bugs in Production

**Temporary Fix**:
1. Mark new tool as "EXPERIMENTAL - USE WITH CAUTION"
2. Keep old tools available as fallback
3. Fix bugs in development branch
4. Test thoroughly before re-deploying

**Graceful Degradation**:
- If backup fails, tool aborts operation (safe)
- If restore fails, original data intact (safe)
- If update fails, partial indexing (acceptable)

---

## Success Criteria

### Functional Requirements
- ✅ All 12 modes work correctly
- ✅ Natural language intent detection accurate >95%
- ✅ Confirmation required for rebuild/restore
- ✅ Auto-backup before force rebuild works
- ✅ Restore successfully restores databases
- ✅ Graceful cancellation works between batches
- ✅ Failed item retry works correctly

### Non-Functional Requirements
- ✅ Response time <500ms for mode detection
- ✅ Backup completes in <3 minutes
- ✅ Restore completes in <5 minutes
- ✅ No data loss in any scenario
- ✅ Clear error messages for all failure modes

### Documentation Requirements
- ✅ CLAUDE.md updated with new tool
- ✅ Tool hierarchy docs updated
- ✅ ADR-004 added to decisions.md
- ✅ Implementation logged in progress.md

---

## Timeline

**Total Estimated Time**: 6-8 hours

| Phase | Task | Estimated Time | Dependencies |
|-------|------|----------------|--------------|
| 1 | Core tool structure | 1-2 hours | None |
| 2 | Backup operations | 1 hour | Phase 1, existing backup.py |
| 3 | Restore operations | 3-4 hours | Phase 2, existing backup.py |
| 4 | Enhanced update features | 1-2 hours | Phase 1, existing semantic.py |
| 5 | Auto-backup before rebuild | 30 minutes | Phase 2, Phase 4 |
| 6 | Database inspection | 1 hour | Phase 1 |
| 7 | Documentation | 1 hour | All phases complete |

**Recommended Order**:
1. Phase 1 (foundation)
2. Phase 2 (backup - needed for Phase 5)
3. Phase 4 (update enhancements)
4. Phase 5 (auto-backup - depends on 2 & 4)
5. Phase 3 (restore - can be done independently)
6. Phase 6 (inspection - can be done independently)
7. Phase 7 (documentation - after all features complete)

---

## Post-Implementation Tasks

1. **Update README.md** with new tool examples
2. **Create demo video** showing natural language control
3. **Announce in changelog** for next release
4. **Monitor usage** via MCP server logs
5. **Collect user feedback** for refinements

---

## Notes

- All new code follows existing patterns (unified tools, intent detection, natural language)
- Leverages existing infrastructure (BackupManager, SemanticSearch, Qdrant, Neo4j)
- Minimal risk (wrappers around existing functionality)
- High value (natural language control, safety features, backup/restore)
- Maintains backward compatibility (old tools deprecated but functional)

---

**Status**: 📋 Ready for Implementation
**Approval Required**: User confirmation to proceed with implementation
**Next Step**: Review plan → User approves → Begin Phase 1
