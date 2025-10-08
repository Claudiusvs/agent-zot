#!/bin/bash
# Agent-Zot Backup Script
# Backs up Qdrant and Neo4j data

BACKUP_DIR="$HOME/toolboxes/agent-zot-backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "Starting agent-zot backup: $TIMESTAMP"

# Backup Qdrant (Docker volume)
echo "Backing up Qdrant..."
docker run --rm \
  -v agent-zot-qdrant-data:/data \
  -v "$BACKUP_DIR:/backup" \
  alpine tar czf "/backup/qdrant-$TIMESTAMP.tar.gz" /data

# Backup Neo4j (if using Neo4j Desktop, backup the data directory)
echo "Backing up Neo4j..."
NEO4J_DATA="$HOME/Library/Application Support/neo4j-desktop/Application/Data"
if [ -d "$NEO4J_DATA" ]; then
  tar czf "$BACKUP_DIR/neo4j-$TIMESTAMP.tar.gz" -C "$NEO4J_DATA" .
fi

# Keep only last 7 days of backups
echo "Cleaning old backups (keeping last 7 days)..."
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete

echo "Backup complete: $BACKUP_DIR"
ls -lh "$BACKUP_DIR" | tail -5
