# Qdrant Backup Information

**Collection:** zotero_library_qdrant
**Timestamp:** 20251024-011907
**Snapshot:** zotero_library_qdrant-4127038390122124-2025-10-23-23-19-07.snapshot
**Local File:** zotero_library_qdrant-backup-20251024-011907.snapshot
**Size:** 1676.4 MB

## Restore Command

```bash
# First, upload snapshot to Qdrant container
docker cp /Users/claudiusv.schroder/toolboxes/agent-zot/backups/qdrant/zotero_library_qdrant-backup-20251024-011907.snapshot <container>:/qdrant/snapshots/zotero_library_qdrant/

# Then restore via API
curl -X PUT 'http://localhost:6333/collections/zotero_library_qdrant/snapshots/recover' \
  -H 'Content-Type: application/json' \
  -d '{"location":"file:///qdrant/snapshots/zotero_library_qdrant/zotero_library_qdrant-backup-20251024-011907.snapshot"}'
```
