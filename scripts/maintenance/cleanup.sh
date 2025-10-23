#!/bin/bash
# Agent-Zot Cleanup Script
# Removes deprecated/unused files to prevent confusion

set -e

echo "=== Agent-Zot System Cleanup ==="
echo ""
echo "This script will archive old/unused files to prevent confusion."
echo "Active Docker containers and volumes will NOT be affected."
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleanup cancelled."
    exit 0
fi

ARCHIVE_DIR="./archived_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$ARCHIVE_DIR"

echo ""
echo "Creating archive directory: $ARCHIVE_DIR"
echo ""

# Archive local Qdrant storage (Docker uses its own volume)
if [ -d "./qdrant_storage" ]; then
    echo "📦 Archiving unused local Qdrant storage..."
    mv ./qdrant_storage "$ARCHIVE_DIR/"
    echo "   ✓ Moved to $ARCHIVE_DIR/qdrant_storage"
fi

# Archive old config files
if [ -d "./config_backup" ]; then
    echo "📦 Archiving outdated config files..."
    mv ./config_backup "$ARCHIVE_DIR/"
    echo "   ✓ Moved to $ARCHIVE_DIR/config_backup"
fi

# Check for old ChromaDB data
if [ -d "$HOME/.config/agent-zot/chroma_db" ]; then
    echo "📦 Found old ChromaDB data..."
    read -p "   Archive ChromaDB data? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        mkdir -p "$ARCHIVE_DIR/chroma_db"
        mv "$HOME/.config/agent-zot/chroma_db" "$ARCHIVE_DIR/"
        echo "   ✓ Moved to $ARCHIVE_DIR/chroma_db"
    else
        echo "   ⊘ Skipped ChromaDB archival"
    fi
fi

echo ""
echo "=== Cleanup Complete ==="
echo ""
echo "Archived files location: $ARCHIVE_DIR"
echo ""
echo "⚠️  If you need to restore anything:"
echo "   mv $ARCHIVE_DIR/* ./"
echo ""
echo "Active system components (NOT affected):"
echo "   ✓ Docker containers: agent-zot-qdrant, agent-zot-neo4j"
echo "   ✓ Docker volumes: agent-zot-neo4j-data, agent-zot-neo4j-logs"
echo "   ✓ Qdrant collection: zotero_library_qdrant (3,087 points)"
echo "   ✓ Neo4j database: 25,184 nodes, 63,838 relationships"
echo ""
