#!/bin/bash
echo "🔄 Restoring Qdrant collection from backup..."
docker stop agent-zot-qdrant
rm -rf ~/toolboxes/agent-zot/qdrant_storage/*
cp -r qdrant_storage_backup/* ~/toolboxes/agent-zot/qdrant_storage/
docker start agent-zot-qdrant
sleep 3
echo "✅ Qdrant restored! Verify with: curl http://localhost:6333/collections/zotero_library_qdrant"
