# Backup and Automation Guide

Comprehensive guide to backing up and automating backups for Qdrant and Neo4j databases in agent-zot.

## Table of Contents

- [Quick Start](#quick-start)
- [How Data Persistence Works](#how-data-persistence-works)
- [Backup Types](#backup-types)
- [Manual Backups](#manual-backups)
- [Automated Backups](#automated-backups)
  - [Option 1: Scheduled (Cron)](#option-1-scheduled-cron)
  - [Option 2: Event-Driven (After Updates)](#option-2-event-driven-after-updates)
  - [Option 3: Hybrid Approach](#option-3-hybrid-approach)
- [Restoring from Backups](#restoring-from-backups)
- [Best Practices](#best-practices)

---

## Quick Start

**Backup everything now:**
```bash
cd /Users/claudiusv.schroder/toolboxes/agent-zot
source agent-zot-env/bin/activate
python scripts/backup.py backup-all
```

**List available backups:**
```bash
python scripts/backup.py list
```

---

## How Data Persistence Works

### Docker Volumes (Persistent)

Both Qdrant and Neo4j use **Docker volumes** for data storage, which persists even when containers stop/restart:

```bash
# List volumes
docker volume ls | grep agent-zot

# Outputs:
#   agent-zot-qdrant-data   - Qdrant vector database
#   agent-zot-neo4j-data    - Neo4j knowledge graph
```

**✅ Safe operations:**
- Restart Docker Desktop
- Stop/start containers
- Restart your computer

**❌ Data loss scenarios:**
- Delete the Docker volume
- `docker volume prune` (removes unused volumes)
- Recreate container without mounting volume

### Why Backups Matter

Even with volumes, backups protect against:
1. **Accidental deletion** - Volumes can be removed
2. **Corruption** - Database corruption from crashes
3. **Migration** - Moving to different machine/setup
4. **Version control** - Snapshots at specific points in time
5. **Experimentation** - Safe rollback point before risky operations

---

## Backup Types

### Qdrant Snapshots

- **Format:** `.snapshot` files (compressed)
- **Location (in-container):** `/qdrant/snapshots/<collection>/`
- **Location (downloaded):** `backups/qdrant/`
- **Size:** ~132MB - 1.7GB (depends on library size)
- **Speed:** Fast (API-based, 10-30 seconds)
- **Advantage:** Can be created while Qdrant is running

**What's included:**
- All vector embeddings (dense + sparse)
- Document chunks
- Metadata (item keys, titles, etc.)
- Index configuration

### Neo4j Dumps

- **Format:** `.dump` files (compressed)
- **Location:** `backups/neo4j/`
- **Size:** Varies (typically 10-100MB for 25k nodes)
- **Speed:** Moderate (1-2 minutes for large databases)
- **Advantage:** Complete database export

**What's included:**
- All nodes (Papers, People, Concepts, etc.)
- All relationships (CITES, AUTHORED_BY, etc.)
- Properties and metadata
- Indexes and constraints

---

## Manual Backups

### Backup Everything

```bash
cd /Users/claudiusv.schroder/toolboxes/agent-zot
source agent-zot-env/bin/activate
python scripts/backup.py backup-all
```

**Output:**
```
=== Backup Results ===

✅ Qdrant (zotero_library_qdrant)
   Snapshot: zotero_library_qdrant-4127038390122124-2025-10-24-10-30-00.snapshot
   Local: backups/qdrant/zotero_library_qdrant-backup-20251024-103000.snapshot
   Size: 1650.3 MB

✅ Neo4j (neo4j)
   Dump: neo4j-neo4j-20251024-103015.dump
   Size: 45.2 MB
   Nodes: 25,184
   Relationships: 134,068
```

### Backup Qdrant Only

```bash
python scripts/backup.py backup-qdrant
```

### Backup Neo4j Only

```bash
python scripts/backup.py backup-neo4j
```

### List Backups

```bash
python scripts/backup.py list
```

**Output:**
```
=== Available Backups ===

Qdrant Snapshots:
  • zotero_library_qdrant-backup-20251024-103000.snapshot
    1650.3 MB - 2025-10-24 10:30:00
  • zotero_library_qdrant-backup-20251019-161720.snapshot
    1700.5 MB - 2025-10-19 16:17:20

Neo4j Dumps:
  • neo4j-neo4j-20251024-103015.dump
    45.2 MB - 2025-10-24 10:30:15
  • neo4j-neo4j-20251019-140000.dump
    43.8 MB - 2025-10-19 14:00:00
```

---

## Automated Backups

### Option 1: Scheduled (Cron)

**Best for:** Regular, predictable backups (daily, weekly, etc.)

#### Setup Daily Backups (2 AM)

1. **Edit crontab:**
   ```bash
   crontab -e
   ```

2. **Add this line:**
   ```cron
   0 2 * * * /Users/claudiusv.schroder/toolboxes/agent-zot/scripts/cron-backup.sh >> /tmp/agent-zot-backup.log 2>&1
   ```

3. **Save and exit**

#### Other Schedules

```cron
# Every 6 hours
0 */6 * * * /path/to/cron-backup.sh

# Weekly (Sunday at 3 AM)
0 3 * * 0 /path/to/cron-backup.sh

# Every hour
0 * * * * /path/to/cron-backup.sh

# Daily at 2 AM and 2 PM
0 2,14 * * * /path/to/cron-backup.sh
```

#### Verify Cron Setup

```bash
# List active cron jobs
crontab -l

# Check backup log
tail -f /tmp/agent-zot-backup.log
```

**Pros:**
- ✅ Automatic - runs without intervention
- ✅ Predictable - always happens at set times
- ✅ Simple - standard Unix tool

**Cons:**
- ❌ Fixed schedule - might backup when nothing changed
- ❌ Wastes resources if no updates happened
- ❌ Might miss important updates between backups

---

### Option 2: Event-Driven (After Updates)

**Best for:** Backup only when library changes

#### Approach A: Hook into Index Updates

**Modify `semantic.py` to trigger backups after successful index update:**

```python
# In src/agent_zot/search/semantic.py, after successful index update:

def update_index(self, limit: Optional[int] = None, **kwargs):
    # ... existing index update code ...

    if success:
        # Trigger automatic backup
        try:
            from agent_zot.utils.backup import create_backup_manager
            import logging
            logger = logging.getLogger(__name__)

            logger.info("Index update successful, creating automatic backup...")
            manager = create_backup_manager()
            manager.backup_all(cleanup_old=True, keep_last=5)
            logger.info("Automatic backup completed")
        except Exception as e:
            logger.warning(f"Automatic backup failed (non-critical): {e}")
```

**Pros:**
- ✅ Only backs up when needed
- ✅ Captures state immediately after changes
- ✅ No wasted backups

**Cons:**
- ❌ Requires code modification
- ❌ Adds time to index updates
- ❌ Might fail silently if backup has issues

#### Approach B: File System Watcher

**Watch Zotero's `zotero.sqlite` for changes:**

```python
# Example: scripts/watch-and-backup.py

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
from agent_zot.utils.backup import create_backup_manager

class ZoteroChangeHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_backup = 0
        self.cooldown = 3600  # 1 hour between backups

    def on_modified(self, event):
        if event.src_path.endswith("zotero.sqlite"):
            current_time = time.time()
            if current_time - self.last_backup > self.cooldown:
                print("Zotero database changed, triggering backup...")
                manager = create_backup_manager()
                manager.backup_all()
                self.last_backup = current_time

observer = Observer()
observer.schedule(ZoteroChangeHandler(), path="/Users/claudiusv.schroder/Zotero", recursive=False)
observer.start()
```

**Pros:**
- ✅ Responds to actual changes
- ✅ No code modification needed
- ✅ Can set cooldown to avoid excessive backups

**Cons:**
- ❌ Requires running background process
- ❌ Zotero database changes frequently (might over-backup)
- ❌ More complex to set up

---

### Option 3: Hybrid Approach (Recommended)

**Combine scheduled backups with event-driven triggers:**

1. **Daily baseline backup** (cron at 2 AM)
2. **After major updates** (manual trigger when adding many papers)
3. **Before risky operations** (manual before experiments)

**Implementation:**

```bash
# Add to crontab: Daily baseline
0 2 * * * /path/to/cron-backup.sh

# Manual trigger after bulk import
cd /Users/claudiusv.schroder/toolboxes/agent-zot
source agent-zot-env/bin/activate
python scripts/backup.py backup-all
```

**Pros:**
- ✅ Best of both worlds
- ✅ Safety net (daily) + responsiveness (manual)
- ✅ Flexible

**Cons:**
- ❌ Requires discipline for manual triggers

---

## Restoring from Backups

### Restore Qdrant Snapshot

#### Method 1: Via API (Recommended)

```bash
# 1. Find latest snapshot
cd /Users/claudiusv.schroder/toolboxes/agent-zot
ls -lht backups/qdrant/*.snapshot | head -1

# 2. Copy to Qdrant container
docker cp backups/qdrant/zotero_library_qdrant-backup-20251024.snapshot \
  <qdrant-container-id>:/qdrant/snapshots/zotero_library_qdrant/

# 3. Restore via API
curl -X PUT 'http://localhost:6333/collections/zotero_library_qdrant/snapshots/recover' \
  -H 'Content-Type: application/json' \
  -d '{"location":"file:///qdrant/snapshots/zotero_library_qdrant/zotero_library_qdrant-backup-20251024.snapshot"}'

# 4. Verify
curl -s http://localhost:6333/collections/zotero_library_qdrant | python3 -m json.tool | grep points_count
```

#### Method 2: Via Internal Snapshots

```bash
# If snapshot is already in container (/qdrant/snapshots/):
curl -X PUT 'http://localhost:6333/collections/zotero_library_qdrant/snapshots/recover' \
  -H 'Content-Type: application/json' \
  -d '{"location":"file:///qdrant/snapshots/zotero_library_qdrant/<snapshot-name>.snapshot"}'
```

### Restore Neo4j Dump

```bash
# 1. Stop Neo4j (optional but recommended)
docker exec agent-zot-neo4j neo4j stop

# 2. Copy dump to container
docker cp backups/neo4j/neo4j-neo4j-20251024-103015.dump \
  agent-zot-neo4j:/tmp/

# 3. Load dump
docker exec agent-zot-neo4j neo4j-admin database load \
  --from-path=/tmp \
  --database=neo4j \
  --overwrite-destination=true

# 4. Start Neo4j
docker exec agent-zot-neo4j neo4j start

# 5. Verify
docker exec agent-zot-neo4j cypher-shell -u neo4j -p demodemo \
  "MATCH (n) RETURN count(n) as total_nodes"
```

---

## Best Practices

### 1. Regular Backups

**Minimum:** Weekly backups
**Recommended:** Daily backups (automated via cron)
**Ideal:** Daily + after major changes

### 2. Retention Policy

**Keep:**
- Last 5 daily backups (default)
- Last 4 weekly backups
- Last 3 monthly backups (manual archival)

**Configure retention:**
```bash
python scripts/backup.py backup-all --keep-last 10  # Keep last 10 backups
```

### 3. Backup Storage

**Local backups location:** `backups/` (in project root)

**Additional recommendations:**
- ✅ Copy to external drive weekly
- ✅ Upload to cloud storage (S3, Dropbox, etc.)
- ✅ Keep off-site backup for disaster recovery

### 4. Test Restores

**Monthly:** Practice restoring from backup
**Why:** Ensure backups are valid and you know the procedure

### 5. Monitor Backup Success

```bash
# Check recent backup logs
tail -100 /tmp/agent-zot-backup.log

# Verify backups exist
ls -lht backups/qdrant/*.snapshot | head -5
ls -lht backups/neo4j/*.dump | head -5

# Check sizes (should be consistent)
du -sh backups/*/
```

### 6. Before Risky Operations

**Always backup before:**
- Rebuilding index (`zot_update_search_database --force`)
- Major code changes
- Experimental features
- Database migrations

```bash
# Quick pre-experiment backup
python scripts/backup.py backup-all
```

---

## Troubleshooting

### Backup Fails with "Container not found"

**Check containers are running:**
```bash
docker ps | grep -E "qdrant|neo4j"
```

**Start containers if needed:**
```bash
cd /Users/claudiusv.schroder/toolboxes/agent-zot
docker-compose up -d
```

### Neo4j Dump Fails

**Ensure database is not busy:**
```bash
# Stop Neo4j temporarily
docker exec agent-zot-neo4j neo4j stop

# Create dump
python scripts/backup.py backup-neo4j

# Restart Neo4j
docker exec agent-zot-neo4j neo4j start
```

### Qdrant Snapshot Download Slow

**Large collections take time:**
- 1.7GB snapshot ≈ 2-5 minutes download
- Be patient, don't interrupt

### Restore Doesn't Work

**Check snapshot location:**
```bash
# List snapshots in Qdrant container
docker exec <qdrant-container> ls -lh /qdrant/snapshots/zotero_library_qdrant/
```

**Verify file integrity:**
```bash
# Check checksum file
docker exec <qdrant-container> cat /qdrant/snapshots/zotero_library_qdrant/<snapshot>.checksum
```

---

## Summary

**🎯 Recommended Setup:**

1. **Enable daily automated backups:**
   ```bash
   crontab -e
   # Add: 0 2 * * * /path/to/cron-backup.sh >> /tmp/agent-zot-backup.log 2>&1
   ```

2. **Manual backup after bulk imports:**
   ```bash
   python scripts/backup.py backup-all
   ```

3. **Weekly verification:**
   ```bash
   python scripts/backup.py list
   ```

4. **Monthly off-site copy:**
   ```bash
   rsync -av backups/ /external-drive/agent-zot-backups/
   ```

**This gives you:**
- ✅ Automatic protection
- ✅ Point-in-time snapshots
- ✅ Disaster recovery capability
- ✅ Peace of mind

---

**Questions?** Check the project documentation or create an issue on GitHub.
