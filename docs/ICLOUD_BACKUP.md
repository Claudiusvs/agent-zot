# iCloud Drive Off-Site Backup Guide

Comprehensive guide for syncing agent-zot backups to iCloud Drive for off-site disaster recovery.

---

## 🎯 Overview

The `scripts/sync-to-icloud.sh` script syncs local backups from `backups/` directory to **iCloud Drive** for off-site storage. This provides:

- ✅ **Disaster recovery** - Protects against local disk failure
- ✅ **Automatic cloud sync** - iCloud handles upload/sync automatically
- ✅ **Cross-device access** - Access backups from any Mac/iOS device
- ✅ **30-day retention** - Automatic cleanup of old backups

**Location**: `iCloud Drive/agent-zot-backups/`

---

## 🚀 Quick Start

### One-Command Backup (Recommended)

**Option 1: CLI Command (Best - works from anywhere):**
```bash
agent-zot backup-all
```

**Option 2: Shell Script (alternative):**
```bash
cd /Users/claudiusv.schroder/toolboxes/agent-zot
./scripts/backup-all.sh
```

Both create local backups AND sync to iCloud automatically.

### Manual Steps (Alternative)

```bash
# Step 1: Create local backups
python scripts/backup.py backup-all

# Step 2: Sync to iCloud
./scripts/sync-to-icloud.sh

# Or preview what would be synced (dry run)
./scripts/sync-to-icloud.sh --dry-run
```

**Output:**
```
======================================
Agent-Zot iCloud Backup Sync
======================================

[Qdrant Snapshots]
Found 5 file(s) to sync
  ✓ zotero_library_qdrant-backup-20251024-011907.snapshot (1.6G) [new]
  ...

[Neo4j Dumps]
Found 2 file(s) to sync
  ✓ neo4j-neo4j-20251024-010541.dump ( 88M) [new]
  ...

[Cleanup]
No old backups to clean up (keeping last 30 days)

======================================
SYNC COMPLETE

iCloud Backup Statistics:
  Qdrant snapshots: 5
  Neo4j dumps: 2
  Total size: 8.4G

Location: iCloud Drive/agent-zot-backups
======================================
```

---

## 📋 Recommended Workflow

### Option 1: One-Command Backup (Recommended)

**CLI Command (works from anywhere):**
```bash
# Complete backup: Local + iCloud
agent-zot backup-all

# With custom retention
agent-zot backup-all --keep-last 10

# Local only (skip iCloud)
agent-zot backup-all --local-only

# Keep all backups (no cleanup)
agent-zot backup-all --no-cleanup
```

**When to use:**
- After manual `update-db` operations
- After bulk imports of papers
- Before risky experiments
- Weekly maintenance

### Option 2: Scheduled Daily Sync

**Add to crontab for automatic nightly sync:**

```bash
crontab -e

# Add: Daily at 3 AM (1 hour after backup-all)
0 3 * * * /Users/claudiusv.schroder/toolboxes/agent-zot/scripts/sync-to-icloud.sh >> /tmp/agent-zot-icloud-sync.log 2>&1
```

**Recommended schedule:**
- If using daily cron backups at 2 AM → sync at 3 AM
- Otherwise, weekly manual sync is sufficient

---

## ⚙️ How It Works

### Smart Sync Algorithm

1. **Finds local backups** in `backups/qdrant/` and `backups/neo4j/`
2. **Compares with iCloud** - checks if files already exist
3. **Copies new/changed files** - only uploads what's needed
4. **Syncs metadata** - includes `BACKUP_INFO.md` files
5. **Cleans old backups** - removes files older than 30 days

### Intelligent File Detection

```bash
# Already synced (same size)
✓ file.snapshot (1.6G) [already synced]

# New file (doesn't exist in iCloud)
✓ file.snapshot (1.6G) [new]

# Updated file (size changed)
✓ file.snapshot (1.6G) [updated]
```

### Retention Policy

**iCloud retention: 30 days** (vs. local retention: 5 backups)

**Why?** iCloud provides long-term off-site storage, while local backups prioritize disk space.

---

## 📁 Directory Structure

### Local Backups
```
/Users/claudiusv.schroder/toolboxes/agent-zot/backups/
├── qdrant/
│   ├── BACKUP_INFO.md
│   ├── zotero_library_qdrant-backup-20251019.snapshot (1.6G)
│   ├── zotero_library_qdrant-backup-20251024-005436.snapshot (1.6G)
│   └── ...
└── neo4j/
    ├── BACKUP_INFO_20251024-010541.md
    ├── neo4j-neo4j-20251024-010427.dump (88M)
    └── ...
```

### iCloud Backups
```
~/Library/Mobile Documents/com~apple~CloudDocs/agent-zot-backups/
├── qdrant/
│   ├── BACKUP_INFO.md
│   ├── zotero_library_qdrant-backup-20251019.snapshot (1.6G)
│   └── ...
└── neo4j/
    ├── BACKUP_INFO_20251024-010541.md
    ├── neo4j-neo4j-20251024-010541.dump (88M)
    └── ...
```

---

## 💾 Storage Requirements

### Current Usage

**Per backup:**
- Qdrant snapshot: ~1.6GB
- Neo4j dump: ~88MB
- Total per backup: ~1.7GB

**With 30-day retention:**
- Weekly backups: ~7GB (4 backups)
- Daily backups: ~51GB (30 backups)

### iCloud Storage Plan

**Check your available space:**
```bash
# macOS Ventura+
diskutil info / | grep "Free Space"

# Or check System Settings > [Your Name] > iCloud
```

**Recommendations:**
- **50GB plan**: Sufficient for weekly backups (7GB)
- **200GB plan**: Comfortable for daily backups (51GB)
- **2TB plan**: Plenty of room + other data

---

## 🔄 Restore from iCloud

### Method 1: Copy Back to Local (Simple)

```bash
# 1. Copy from iCloud to local backups
cp ~/Library/Mobile\ Documents/com~apple~CloudDocs/agent-zot-backups/qdrant/*.snapshot \
   /Users/claudiusv.schroder/toolboxes/agent-zot/backups/qdrant/

cp ~/Library/Mobile\ Documents/com~apple~CloudDocs/agent-zot-backups/neo4j/*.dump \
   /Users/claudiusv.schroder/toolboxes/agent-zot/backups/neo4j/

# 2. Follow standard restore procedures (see BACKUP_AUTOMATION.md)
```

### Method 2: Direct Restore (Advanced)

**Restore Qdrant directly from iCloud:**
```bash
# 1. Get Qdrant container ID
QDRANT_CONTAINER=$(docker ps --filter "name=agent-zot-qdrant" --format "{{.ID}}")

# 2. Copy from iCloud to container
docker cp ~/Library/Mobile\ Documents/com~apple~CloudDocs/agent-zot-backups/qdrant/zotero_library_qdrant-backup-20251024-011907.snapshot \
  $QDRANT_CONTAINER:/qdrant/snapshots/zotero_library_qdrant/

# 3. Restore via API
curl -X PUT 'http://localhost:6333/collections/zotero_library_qdrant/snapshots/recover' \
  -H 'Content-Type: application/json' \
  -d '{"location":"file:///qdrant/snapshots/zotero_library_qdrant/zotero_library_qdrant-backup-20251024-011907.snapshot"}'
```

**Restore Neo4j directly from iCloud:**
```bash
# 1. Copy from iCloud to container
docker cp ~/Library/Mobile\ Documents/com~apple~CloudDocs/agent-zot-backups/neo4j/neo4j-neo4j-20251024-010541.dump \
  agent-zot-neo4j:/tmp/

# 2. Stop, load, start
docker exec agent-zot-neo4j neo4j stop
docker exec agent-zot-neo4j neo4j-admin database load \
  --from-path=/tmp --database=neo4j --overwrite-destination=true
docker exec agent-zot-neo4j neo4j start
```

---

## 🔍 Monitoring & Verification

### Check iCloud Sync Status

```bash
# List iCloud backups
ls -lht ~/Library/Mobile\ Documents/com~apple~CloudDocs/agent-zot-backups/qdrant/
ls -lht ~/Library/Mobile\ Documents/com~apple~CloudDocs/agent-zot-backups/neo4j/

# Check total size
du -sh ~/Library/Mobile\ Documents/com~apple~CloudDocs/agent-zot-backups/

# Count backups
find ~/Library/Mobile\ Documents/com~apple~CloudDocs/agent-zot-backups/ -name "*.snapshot" | wc -l
find ~/Library/Mobile\ Documents/com~apple~CloudDocs/agent-zot-backups/ -name "*.dump" | wc -l
```

### View Sync Logs (if using cron)

```bash
tail -f /tmp/agent-zot-icloud-sync.log
```

### Verify iCloud Upload Status

**System Settings > [Your Name] > iCloud > Manage Storage > agent-zot-backups**

Files show upload status:
- ☁️ = Uploaded to iCloud
- ⬇️ = Available to download
- ⏸ = Upload paused

---

## 🔧 Troubleshooting

### iCloud Drive Not Accessible

**Error:** `iCloud Drive not accessible`

**Solution:**
1. Check System Settings > [Your Name] > iCloud
2. Enable "iCloud Drive"
3. Ensure "Desktop & Documents Folders" is enabled (optional)
4. Restart Finder or Mac if needed

### Upload Taking Too Long

**Issue:** Large files (~8GB) take time to upload

**Timeline:**
- Initial sync: 1-4 hours (depends on internet speed)
- Subsequent syncs: Minutes (only new/changed files)

**Tip:** Run sync overnight or during off-hours

### Files Not Appearing on Other Devices

**Cause:** iCloud sync lag (normal)

**Solution:**
- Wait 5-15 minutes for sync to propagate
- Check other device's iCloud storage settings
- Force refresh: Close/reopen Finder or Files app

### Disk Space Full

**Error:** Not enough disk space for sync

**Solution:**
```bash
# Check available space
df -h ~

# Remove old local backups (keep fewer than 5)
python scripts/backup.py backup-all --keep-last 3

# Or manually clean old backups
rm backups/qdrant/zotero_library_qdrant-backup-20251019.snapshot
```

---

## 📊 Script Configuration

### Customizing Retention

**Edit `scripts/sync-to-icloud.sh` line 79:**
```bash
# Keep last 30 days (default)
find "$ICLOUD_BACKUP_DIR" -name "*-20*.tar.gz" -mtime +30 -delete

# Keep last 60 days
find "$ICLOUD_BACKUP_DIR" -name "*-20*.tar.gz" -mtime +60 -delete

# Keep last 7 days (aggressive cleanup)
find "$ICLOUD_BACKUP_DIR" -name "*-20*.tar.gz" -mtime +7 -delete
```

### Customizing iCloud Location

**Edit `scripts/sync-to-icloud.sh` line 6:**
```bash
# Default
ICLOUD_BACKUP_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/agent-zot-backups"

# Custom folder
ICLOUD_BACKUP_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/Research/Backups/agent-zot"
```

---

## 🎯 Best Practices

### 1. Sync After Every Backup

```bash
# Combined workflow
python scripts/backup.py backup-all && ./scripts/sync-to-icloud.sh
```

### 2. Verify Sync Success

```bash
# Quick verification
./scripts/sync-to-icloud.sh | grep "SYNC COMPLETE"

# Check files actually exist
ls -lh ~/Library/Mobile\ Documents/com~apple~CloudDocs/agent-zot-backups/qdrant/ | wc -l
```

### 3. Test Restore Quarterly

**Best practice:** Test restoring from iCloud backups every 3 months to ensure:
- Files are not corrupted
- You remember the restore procedure
- iCloud sync is working correctly

### 4. Monitor iCloud Storage

**Monthly check:**
```bash
# Check current usage
du -sh ~/Library/Mobile\ Documents/com~apple~CloudDocs/agent-zot-backups/

# Compare to available space
# System Settings > [Your Name] > iCloud > Manage Storage
```

---

## 📚 Related Documentation

- **BACKUP_AUTOMATION.md** - Complete backup system guide
- **QUICK_REFERENCE.md** - Command reference
- **CLAUDE.md** - Operational context and current status

---

## ✅ Summary

**What you have now:**
- ✅ Script ready to use: `./scripts/sync-to-icloud.sh`
- ✅ 8.4GB already synced to iCloud Drive
- ✅ 5 Qdrant snapshots + 2 Neo4j dumps in cloud
- ✅ 30-day retention policy active
- ✅ Smart sync (only uploads new/changed files)

**Recommended workflow:**
```bash
# After manual updates or weekly maintenance
python scripts/backup.py backup-all    # Create backups
./scripts/sync-to-icloud.sh           # Sync to iCloud
```

**iCloud benefits over local-only:**
- 🔥 Fire/theft protection
- 💾 Hardware failure protection
- 🌐 Access from any device
- ☁️ Automatic cloud sync

---

**Questions?** Check the project documentation or create an issue on GitHub.
