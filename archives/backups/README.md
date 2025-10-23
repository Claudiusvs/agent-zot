# Agent-Zot Backup Policy

This directory contains database backups and configuration snapshots for disaster recovery.

## Backup Types

### 1. Pre-Feature Backups
**Naming:** `pre-<feature>-<YYYYMMDD-HHMMSS>/`
**Purpose:** Snapshot before major feature changes
**Contains:** Full Qdrant backup, config, manifest
**Example:** `pre-neo4j-20251012-163835/`

### 2. Qdrant Collection Snapshots
**Location:** `qdrant/`
**Naming:** `<collection>-backup-<YYYYMMDD>.snapshot`
**Purpose:** Regular vector database backups
**Restore:** Upload via Qdrant API

## Retention Policy

**Keep:**
- Last 3 pre-feature backups
- Monthly Qdrant snapshots for 3 months
- Any backup tagged as "stable release"

**Delete after:**
- Pre-feature backups: 6 months (if system stable)
- Monthly snapshots: 3 months
- Ad-hoc snapshots: 1 month

## Creating Backups

### Qdrant Snapshot
```bash
# Create snapshot
curl -X POST http://localhost:6333/collections/zotero_library_qdrant/snapshots

# Download snapshot
docker cp agent-zot-qdrant:/qdrant/snapshots/<snapshot-name> \
  archives/backups/qdrant/
```

### Full System Backup
```bash
# Create pre-feature backup
./scripts/maintenance/backup.sh --label "pre-<feature-name>"
```

## Restoration

### Restore Qdrant Snapshot
```bash
curl -X POST http://localhost:6333/collections/zotero_library_qdrant/snapshots/recover \
  -H 'Content-Type: application/json' \
  -d '{"location": "file:///path/to/snapshot"}'
```

### Restore Full System
```bash
cd archives/backups/<backup-directory>
./RESTORE.sh
```

## Current Backups

### Pre-Neo4j Backup (Oct 12, 2025)
- **Size:** ~1.5GB
- **Status:** ✅ Verified working
- **Purpose:** Rollback point before Neo4j GraphRAG integration
- **Delete after:** April 2026 (if Neo4j integration stable)

### Qdrant Snapshot (Oct 19, 2025)
- **Size:** ~800MB
- **Status:** ✅ Verified working
- **Collection:** zotero_library_qdrant
- **Points:** ~234,153 chunks
- **Delete after:** January 2026

## Backup Schedule Recommendations

1. **Before major changes:** Always create pre-feature backup
2. **Monthly:** Create Qdrant snapshot (1st of month)
3. **After successful migrations:** Create tagged "stable" backup
4. **Quarterly:** Test restoration process

**Last updated:** October 2025
