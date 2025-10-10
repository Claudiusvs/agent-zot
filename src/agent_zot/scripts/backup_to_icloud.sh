#!/bin/bash
# Agent-Zot Automated Backup to iCloud Drive
# Backs up Qdrant and Neo4j data, automatically syncs to iCloud

# Configuration
ICLOUD_BACKUP_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/agent-zot-backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TEMP_BACKUP_DIR="/tmp/agent-zot-backup-$TIMESTAMP"

# Create temp backup directory
mkdir -p "$TEMP_BACKUP_DIR"

echo "======================================"
echo "Agent-Zot Backup: $TIMESTAMP"
echo "======================================"

# Backup Qdrant (Docker volume)
echo ""
echo "[1/3] Backing up Qdrant vector database..."
docker run --rm \
  -v agent-zot-qdrant-data:/data \
  -v "$TEMP_BACKUP_DIR:/backup" \
  alpine tar czf "/backup/qdrant.tar.gz" /data 2>/dev/null

if [ -f "$TEMP_BACKUP_DIR/qdrant.tar.gz" ]; then
  SIZE=$(du -h "$TEMP_BACKUP_DIR/qdrant.tar.gz" | cut -f1)
  echo "✓ Qdrant backup created: $SIZE"
else
  echo "✗ Qdrant backup failed"
fi

# Backup Neo4j (Neo4j Desktop data directory)
echo ""
echo "[2/3] Backing up Neo4j knowledge graph..."
NEO4J_DATA="$HOME/Library/Application Support/neo4j-desktop/Application/Data"
if [ -d "$NEO4J_DATA" ]; then
  tar czf "$TEMP_BACKUP_DIR/neo4j.tar.gz" -C "$NEO4J_DATA" . 2>/dev/null
  if [ -f "$TEMP_BACKUP_DIR/neo4j.tar.gz" ]; then
    SIZE=$(du -h "$TEMP_BACKUP_DIR/neo4j.tar.gz" | cut -f1)
    echo "✓ Neo4j backup created: $SIZE"
  else
    echo "✗ Neo4j backup failed"
  fi
else
  echo "✗ Neo4j data directory not found"
fi

# Copy to iCloud Drive
echo ""
echo "[3/3] Syncing to iCloud Drive..."
mkdir -p "$ICLOUD_BACKUP_DIR"

# Copy with timestamp
if [ -f "$TEMP_BACKUP_DIR/qdrant.tar.gz" ]; then
  cp "$TEMP_BACKUP_DIR/qdrant.tar.gz" "$ICLOUD_BACKUP_DIR/qdrant-$TIMESTAMP.tar.gz"
  echo "✓ Qdrant synced to iCloud"
fi

if [ -f "$TEMP_BACKUP_DIR/neo4j.tar.gz" ]; then
  cp "$TEMP_BACKUP_DIR/neo4j.tar.gz" "$ICLOUD_BACKUP_DIR/neo4j-$TIMESTAMP.tar.gz"
  echo "✓ Neo4j synced to iCloud"
fi

# Also keep "latest" versions (for easy access)
if [ -f "$TEMP_BACKUP_DIR/qdrant.tar.gz" ]; then
  cp "$TEMP_BACKUP_DIR/qdrant.tar.gz" "$ICLOUD_BACKUP_DIR/qdrant-latest.tar.gz"
fi

if [ -f "$TEMP_BACKUP_DIR/neo4j.tar.gz" ]; then
  cp "$TEMP_BACKUP_DIR/neo4j.tar.gz" "$ICLOUD_BACKUP_DIR/neo4j-latest.tar.gz"
fi

# Clean up temp directory
rm -rf "$TEMP_BACKUP_DIR"

# Clean old backups (keep last 30 days in iCloud)
echo ""
echo "Cleaning old backups (keeping last 30 days)..."
find "$ICLOUD_BACKUP_DIR" -name "*-20*.tar.gz" -mtime +30 -delete 2>/dev/null
BACKUP_COUNT=$(find "$ICLOUD_BACKUP_DIR" -name "*.tar.gz" -type f | wc -l | tr -d ' ')
echo "✓ Total backups in iCloud: $BACKUP_COUNT files"

echo ""
echo "======================================"
echo "Backup complete!"
echo "Location: iCloud Drive/agent-zot-backups"
echo "======================================"
echo ""
echo "Recent backups:"
ls -lht "$ICLOUD_BACKUP_DIR" | grep -E "qdrant|neo4j" | head -6
