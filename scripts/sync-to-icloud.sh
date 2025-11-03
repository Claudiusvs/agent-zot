#!/bin/bash
#
# Sync agent-zot backups to iCloud Drive
#
# This script syncs existing backups from the local backups/ directory
# to iCloud Drive for off-site storage. Works with the Python-based
# backup system (scripts/backup.py).
#
# Usage:
#   ./scripts/sync-to-icloud.sh              # Sync all backups
#   ./scripts/sync-to-icloud.sh --dry-run    # Preview what would be synced

set -e

# Configuration
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOCAL_BACKUP_DIR="$PROJECT_DIR/backups"
ICLOUD_BACKUP_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/agent-zot-backups"
DRY_RUN=false

# Parse arguments
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
fi

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "======================================"
echo "Agent-Zot iCloud Backup Sync"
echo "======================================"
echo ""
echo "Local:  $LOCAL_BACKUP_DIR"
echo "iCloud: $ICLOUD_BACKUP_DIR"
echo ""

# Check if iCloud Drive is accessible
if [ ! -d "$HOME/Library/Mobile Documents/com~apple~CloudDocs" ]; then
    echo -e "${RED}✗ iCloud Drive not accessible${NC}"
    echo "  Make sure iCloud Drive is enabled in System Settings"
    exit 1
fi

# Create iCloud backup directory
if [ "$DRY_RUN" = false ]; then
    mkdir -p "$ICLOUD_BACKUP_DIR/qdrant"
    mkdir -p "$ICLOUD_BACKUP_DIR/neo4j"
fi

# Function to sync directory
sync_directory() {
    local source_dir="$1"
    local dest_dir="$2"
    local file_pattern="$3"
    local label="$4"

    echo "[$label]"

    if [ ! -d "$source_dir" ]; then
        echo -e "${YELLOW}⚠ Source directory not found: $source_dir${NC}"
        echo ""
        return
    fi

    # Count files
    local file_count=$(find "$source_dir" -name "$file_pattern" -type f | wc -l | tr -d ' ')

    if [ "$file_count" -eq 0 ]; then
        echo -e "${YELLOW}⚠ No files found matching: $file_pattern${NC}"
        echo ""
        return
    fi

    echo "Found $file_count file(s) to sync"

    # Sync files
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN]${NC} Would sync:"
        find "$source_dir" -name "$file_pattern" -type f | while read file; do
            local size=$(du -h "$file" | cut -f1)
            echo "  - $(basename "$file") ($size)"
        done
    else
        local synced=0
        find "$source_dir" -name "$file_pattern" -type f | while read file; do
            local filename=$(basename "$file")
            local size=$(du -h "$file" | cut -f1)

            # Check if file already exists in iCloud
            if [ -f "$dest_dir/$filename" ]; then
                # Compare sizes to see if update needed
                local local_size=$(stat -f%z "$file")
                local icloud_size=$(stat -f%z "$dest_dir/$filename")

                if [ "$local_size" -eq "$icloud_size" ]; then
                    echo -e "  ${GREEN}✓${NC} $filename ($size) [already synced]"
                else
                    cp "$file" "$dest_dir/"
                    echo -e "  ${GREEN}✓${NC} $filename ($size) [updated]"
                fi
            else
                cp "$file" "$dest_dir/"
                echo -e "  ${GREEN}✓${NC} $filename ($size) [new]"
            fi
        done
    fi

    echo ""
}

# Sync Qdrant snapshots
sync_directory \
    "$LOCAL_BACKUP_DIR/qdrant" \
    "$ICLOUD_BACKUP_DIR/qdrant" \
    "*.snapshot" \
    "Qdrant Snapshots"

# Sync Neo4j dumps
sync_directory \
    "$LOCAL_BACKUP_DIR/neo4j" \
    "$ICLOUD_BACKUP_DIR/neo4j" \
    "*.dump" \
    "Neo4j Dumps"

# Sync backup info files
if [ "$DRY_RUN" = false ]; then
    if [ -f "$LOCAL_BACKUP_DIR/qdrant/BACKUP_INFO.md" ]; then
        cp "$LOCAL_BACKUP_DIR/qdrant/BACKUP_INFO.md" "$ICLOUD_BACKUP_DIR/qdrant/"
        echo -e "${GREEN}✓${NC} Synced Qdrant backup info"
    fi

    find "$LOCAL_BACKUP_DIR/neo4j" -name "BACKUP_INFO_*.md" -type f | while read file; do
        cp "$file" "$ICLOUD_BACKUP_DIR/neo4j/"
    done

    if [ -n "$(find "$LOCAL_BACKUP_DIR/neo4j" -name "BACKUP_INFO_*.md" -type f)" ]; then
        echo -e "${GREEN}✓${NC} Synced Neo4j backup info"
    fi
    echo ""
fi

# Cleanup old backups in iCloud (keep last 30 days)
if [ "$DRY_RUN" = false ]; then
    echo "[Cleanup]"

    # Qdrant
    deleted_qdrant=$(find "$ICLOUD_BACKUP_DIR/qdrant" -name "*.snapshot" -mtime +30 -delete -print | wc -l | tr -d ' ')

    # Neo4j
    deleted_neo4j=$(find "$ICLOUD_BACKUP_DIR/neo4j" -name "*.dump" -mtime +30 -delete -print | wc -l | tr -d ' ')

    if [ "$deleted_qdrant" -gt 0 ] || [ "$deleted_neo4j" -gt 0 ]; then
        echo "Removed $deleted_qdrant old Qdrant snapshot(s)"
        echo "Removed $deleted_neo4j old Neo4j dump(s)"
    else
        echo "No old backups to clean up (keeping last 30 days)"
    fi
    echo ""
fi

# Summary
echo "======================================"
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}DRY RUN COMPLETE${NC}"
    echo "Run without --dry-run to perform sync"
else
    echo -e "${GREEN}SYNC COMPLETE${NC}"

    # Show iCloud backup statistics
    qdrant_count=$(find "$ICLOUD_BACKUP_DIR/qdrant" -name "*.snapshot" -type f | wc -l | tr -d ' ')
    neo4j_count=$(find "$ICLOUD_BACKUP_DIR/neo4j" -name "*.dump" -type f | wc -l | tr -d ' ')
    total_size=$(du -sh "$ICLOUD_BACKUP_DIR" | cut -f1)

    echo ""
    echo "iCloud Backup Statistics:"
    echo "  Qdrant snapshots: $qdrant_count"
    echo "  Neo4j dumps: $neo4j_count"
    echo "  Total size: $total_size"
    echo ""
    echo "Location: iCloud Drive/agent-zot-backups"
fi
echo "======================================"
