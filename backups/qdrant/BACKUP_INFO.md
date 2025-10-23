# Qdrant Backup - Full Library

**Backup Date:** 2025-10-19 18:18 CEST
**Collection:** zotero_library_qdrant
**Snapshot Name:** zotero_library_qdrant-4127038390122124-2025-10-19-16-17-20.snapshot

## Backup Details

- **Total Papers:** 3,426
- **Total Chunks:** 234,152
- **Backup Size:** 1.6 GB
- **SHA-256 Checksum:** 370494d0111a2ba3db206cbfa3c3a58f7c1026cf5e31f7df9d6dff64310e4fad

## What's Included

This backup contains the complete Qdrant vector database after full library indexing:
- All 3,426 papers from Zotero library
- 234,152 chunks with BGE-M3 embeddings
- Full text content extracted via Docling V2
- All metadata (titles, authors, item keys, chunk IDs, etc.)

## When to Restore

Use this backup if:
- Qdrant collection becomes corrupted
- Need to revert after failed migration
- Want to restore to pre-migration state

## How to Restore

```bash
# Stop Qdrant (if running in Docker)
docker stop agent-zot-qdrant

# Remove existing collection
docker exec agent-zot-qdrant rm -rf /qdrant/storage/collections/zotero_library_qdrant

# Copy backup to container
docker cp backups/qdrant/zotero_library_qdrant-backup-20251019.snapshot agent-zot-qdrant:/tmp/

# Restore using Qdrant API
curl -X PUT "http://localhost:6333/collections/zotero_library_qdrant/snapshots/upload?priority=snapshot" \
     --data-binary @/tmp/zotero_library_qdrant-backup-20251019.snapshot

# Or use Python:
from qdrant_client import QdrantClient
client = QdrantClient(url='http://localhost:6333')
client.recover_snapshot(
    collection_name='zotero_library_qdrant',
    location='/tmp/zotero_library_qdrant-backup-20251019.snapshot'
)
```

## Notes

- Created immediately after full library indexing completed
- Taken before Neo4j migration
- Safe to use even if Neo4j migration fails (Neo4j and Qdrant are independent)
- The Neo4j migration only reads from Qdrant, never writes to it
