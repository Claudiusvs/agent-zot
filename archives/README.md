# Agent-Zot Archives

This directory contains historical backups and archived files from previous versions of agent-zot.

## Directory Structure

### `2025-10-14/`
**Archived:** October 14, 2025
**Contents:**
- Old configuration backups
- Deprecated Qdrant storage structure
- Pre-migration files

**What it contains:**
- `config_backup/` - Old config.json versions
- `qdrant_storage/` - Deprecated Qdrant storage format (before Docker volume migration)

**Retention:** Can be safely deleted after verifying current system is stable.

### `backups/`
**Contents:** Database and configuration backups from various dates

**Subdirectories:**
- `pre-neo4j-20251012-163835/` - Backup before Neo4j GraphRAG integration
  - Includes: Qdrant snapshot, config backup, manifest, restore script
- `qdrant/` - Qdrant collection snapshots
  - `zotero_library_qdrant-backup-20251019.snapshot` - Full collection backup from Oct 19, 2025

**Retention Policy:**
- Keep last 3 major version backups (pre-feature changes)
- Keep monthly snapshots for 3 months
- Delete older backups after 6 months

## Restoration

### To restore a Qdrant snapshot:
```bash
curl -X POST http://localhost:6333/collections/zotero_library_qdrant/snapshots/upload \
  -H 'Content-Type: application/json' \
  -d '{"path": "/path/to/snapshot"}'
```

### To restore from pre-neo4j backup:
```bash
cd archives/backups/pre-neo4j-20251012-163835/
./RESTORE.sh
```

## Cleanup Recommendations

After 6 months of stable operation, you can safely delete:
- `2025-10-14/` directory entirely
- Older backup snapshots (keeping only the most recent 3)

**Last reviewed:** October 2025
