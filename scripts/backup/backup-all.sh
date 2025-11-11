#!/bin/bash
#
# Complete Backup Script - Local + iCloud
#
# Creates local backups (Qdrant + Neo4j) and syncs to iCloud Drive in one command.
#
# Usage:
#   ./scripts/backup-all.sh              # Full backup + sync
#   ./scripts/backup-all.sh --local-only # Skip iCloud sync
#   ./scripts/backup-all.sh --keep-last 10 # Custom retention

set -e

# Navigate to project directory
cd "$(dirname "$0")/.."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
SKIP_ICLOUD=false
KEEP_LAST=5

while [[ $# -gt 0 ]]; do
    case $1 in
        --local-only)
            SKIP_ICLOUD=true
            shift
            ;;
        --keep-last)
            KEEP_LAST="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--local-only] [--keep-last N]"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}======================================"
echo "Agent-Zot Complete Backup"
echo "======================================${NC}"
echo ""

# Activate virtualenv
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo -e "${YELLOW}⚠ Virtual environment not found${NC}"
    exit 1
fi

# Step 1: Create local backups
echo -e "${BLUE}[1/2] Creating local backups...${NC}"
echo ""

python scripts/backup.py backup-all --keep-last "$KEEP_LAST"
BACKUP_STATUS=$?

if [ $BACKUP_STATUS -ne 0 ]; then
    echo ""
    echo -e "${YELLOW}⚠ Local backup failed${NC}"
    exit 1
fi

echo ""

# Step 2: Sync to iCloud
if [ "$SKIP_ICLOUD" = false ]; then
    echo -e "${BLUE}[2/2] Syncing to iCloud Drive...${NC}"
    echo ""

    ./scripts/sync-to-icloud.sh
    SYNC_STATUS=$?

    if [ $SYNC_STATUS -ne 0 ]; then
        echo ""
        echo -e "${YELLOW}⚠ iCloud sync failed (local backups still created)${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}[2/2] Skipping iCloud sync (--local-only)${NC}"
fi

echo ""
echo -e "${GREEN}======================================"
echo "✓ Complete Backup Finished"
echo "======================================${NC}"
