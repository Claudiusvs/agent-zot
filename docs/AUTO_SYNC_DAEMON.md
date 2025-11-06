# Auto-Sync Daemon Documentation

**Last Updated**: November 6, 2025
**Status**: ✅ Production-Ready (v2.2)

---

## Overview

The auto-sync daemon automatically ingests new papers added to Zotero without requiring manual `agent-zot update-db` commands. Uses hybrid file watcher + API polling for reliability.

### Key Features

✅ **Automatic Ingestion**: New papers processed within 30-90 seconds
✅ **Defense in Depth**: File watcher (immediate) + API polling (reliable)
✅ **Same Pipeline**: Identical quality as manual updates
✅ **4-Layer Deduplication**: No duplicate papers
✅ **Production-Ready**: Graceful shutdown, auto-restart, metrics

---

## Quick Start

### 1. Enable Auto-Sync

Edit `~/.config/agent-zot/config.json`:

```json
{
  "auto_sync": {
    "enabled": true,
    "mode": "hybrid",
    "polling": {
      "interval_seconds": 300,
      "use_since_param": true
    },
    "watcher": {
      "enabled": true,
      "debounce_seconds": 30,
      "watch_path": "/Users/USERNAME/zotero_database/zotero.sqlite"
    },
    "queue": {
      "dedup_window_seconds": 60,
      "max_batch_size": 50
    }
  }
}
```

**⚠️ Update `watch_path`** to your actual `zotero.sqlite` location.

### 2. Start Daemon

```bash
# Run now (foreground)
agent-zot daemon start

# Setup auto-start on login
agent-zot daemon install       # macOS (launchd)
agent-zot daemon install --systemd  # Linux (systemd)
```

### 3. Monitor Status

```bash
# CLI
agent-zot daemon status

# Within Claude Desktop (MCP)
zot_daemon_status
```

---

## Architecture

```
┌─────────────────────────────┐
│  Zotero Library (Source)    │
└──────────┬──────────────────┘
           │
    ┌──────┼──────┐
    │             │
┌───▼────┐   ┌───▼────┐
│ File   │   │  API   │
│Watcher │   │ Poller │
│(30s)   │   │ (5min) │
└───┬────┘   └───┬────┘
    │             │
    └──────┬──────┘
      ┌────▼────┐
      │  Queue  │  60s Dedup
      └────┬────┘
      ┌────▼────────┐
      │Orchestrator │
      │(Existing    │
      │ Pipeline)   │
      └─────────────┘
```

### Components

1. **File Watcher** - Monitors `zotero.sqlite` for modifications (watchdog)
2. **API Poller** - Queries Zotero API every 5 minutes (`since` parameter)
3. **Update Queue** - Deduplicates items from both triggers
4. **Orchestrator** - Runs existing `update_database()` pipeline

---

## Configuration

### Modes

- **`hybrid`** (recommended): File watcher + API polling
- **`watcher`**: File watcher only (immediate, single point of failure)
- **`polling`**: API polling only (reliable, 5-minute delay)

### Tuning Parameters

```json
{
  "auto_sync": {
    "polling": {
      "interval_seconds": 300   // API poll frequency (default: 5 min)
    },
    "watcher": {
      "debounce_seconds": 30    // Batch rapid changes (default: 30s)
    },
    "queue": {
      "dedup_window_seconds": 60,  // Prevent double-processing
      "max_batch_size": 50          // Items per batch
    }
  }
}
```

---

## Deduplication Layers

The system has **4 independent** mechanisms preventing duplicate papers:

1. **Queue Deduplication** (60s window)
   - Prevents double-enqueue when both triggers fire
   - Tracks source (file_watcher vs api_polling)

2. **Parse Cache** (~/.cache/agent-zot/parsed_docs.db)
   - Skips PDF extraction if already cached
   - Saves ~18 seconds per already-processed paper

3. **Qdrant Upsert**
   - Uses `item_key` as deterministic point ID
   - Updates existing points instead of creating duplicates

4. **Neo4j MERGE**
   - Uses MERGE instead of CREATE for nodes/relationships
   - Updates properties if exists, creates if new

**Result**: Safe to run multiple updates - no duplicates created.

---

## Process Management

### macOS (launchd)

```bash
# Create plist
agent-zot daemon install

# Enable auto-start
launchctl load ~/Library/LaunchAgents/com.agent-zot.autosync.plist

# Start now
launchctl start com.agent-zot.autosync

# Stop
launchctl stop com.agent-zot.autosync

# Disable auto-start
launchctl unload ~/Library/LaunchAgents/com.agent-zot.autosync.plist
```

**Log Files**:
- stdout: `/tmp/agent-zot-daemon.log`
- stderr: `/tmp/agent-zot-daemon.error.log`

### Linux (systemd)

```bash
# Create service
agent-zot daemon install --systemd

# Enable auto-start
systemctl --user enable agent-zot-autosync

# Start now
systemctl --user start agent-zot-autosync

# Check status
systemctl --user status agent-zot-autosync

# Stop
systemctl --user stop agent-zot-autosync

# View logs
journalctl --user -u agent-zot-autosync -f
```

---

## Monitoring

### CLI Status

```bash
$ agent-zot daemon status

✓ Daemon running (PID: 12345)

Config: /Users/you/.config/agent-zot/config.json
  Enabled: True
  Mode: hybrid
```

### MCP Tool (Claude Desktop)

```
zot_daemon_status
```

Returns:
- Daemon status (🟢 Running / 🔴 Stopped)
- PID
- Configuration (mode, intervals)
- File watcher status
- API poller status
- Queue statistics

---

## Troubleshooting

### Daemon Won't Start

**Error**: `Auto-sync is not enabled in config`

**Solution**: Set `auto_sync.enabled = true` in config.json

---

### Orphaned MCP Server Processes

**Issue**: Multiple `agent-zot serve` processes accumulate over time

**Solution**: ✅ **Automatic cleanup enabled** (Nov 6, 2025)
- Daemon automatically cleans up orphaned processes on startup
- Check logs: `tail -f /tmp/agent-zot-daemon.error.log | grep orphaned`
- Cleanup actions are logged for transparency

**Manual cleanup** (if needed before daemon restart):
```bash
# View orphaned processes
ps aux | grep "agent-zot serve" | grep -v grep

# Kill manually
kill PID1 PID2 PID3
```

**Technical Details**: Addresses bugs.md Limitation #001 - Prevents memory buildup from accumulated MCP server processes

---

### File Watcher Path Error

**Error**: `Zotero database not found: /path/to/zotero.sqlite`

**Solution**: Update `auto_sync.watcher.watch_path` to correct location.

**Find your sqlite path**:
```bash
# macOS
mdfind "kMDItemFSName == 'zotero.sqlite'"

# Linux
find ~ -name "zotero.sqlite" 2>/dev/null
```

---

### Multiple Daemon Processes

**Symptom**: `ps aux | grep agent-zot` shows multiple processes

**Solution**: Kill old processes:
```bash
ps aux | grep "agent-zot daemon start"
kill PID1 PID2 PID3
```

Then restart:
```bash
agent-zot daemon start
```

---

### Papers Not Auto-Ingesting

**Check**:
1. Daemon running? `agent-zot daemon status`
2. Config enabled? `auto_sync.enabled = true`
3. Watch path correct? Check `zotero.sqlite` location
4. Check logs: `/tmp/agent-zot-daemon.error.log`

---

## Performance

### Resource Usage

- **RAM**: ~100-200MB (daemon process)
- **CPU**: <1% idle, ~5-10% during ingestion
- **Disk**: Parse cache (~623 MB for 2,519 papers)

### Ingestion Speed

- **File Watcher**: Triggers within ~30 seconds of DB change
- **API Poller**: Triggers within ~5 minutes
- **Processing**: ~18 seconds per paper (PDF extraction + embedding)

**Example**: Add 3 papers → File watcher triggers in 30s → All 3 processed in ~54s

---

## Advanced

### Custom Poll Interval

Increase polling frequency (not recommended - API rate limits):

```json
{
  "auto_sync": {
    "polling": {
      "interval_seconds": 60  // Poll every minute (be careful of rate limits!)
    }
  }
}
```

**⚠️ Warning**: Zotero API free tier allows 100 requests/hour.

### Disable File Watcher

Use polling only:

```json
{
  "auto_sync": {
    "mode": "polling",
    "watcher": {
      "enabled": false
    }
  }
}
```

### Batch Size

Process more items per batch:

```json
{
  "auto_sync": {
    "queue": {
      "max_batch_size": 100  // Default: 50
    }
  }
}
```

---

## References

- **ADR-014**: Hybrid Auto-Sync Daemon (decisions.md)
- **ADR-003**: Manual Database Updates (rationale for separate daemon)
- **Config Example**: `docs/config_example_auto_sync.json`
- **Implementation**: `src/agent_zot/daemon/` (6 files, ~1,238 lines)

---

**For Claude Code**: After editing `config.json`, restart daemon for changes to take effect:
```bash
agent-zot daemon stop
agent-zot daemon start
```
