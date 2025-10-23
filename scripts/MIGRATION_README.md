# Neo4j Paper Link Migration

## Problem

Paper nodes in Neo4j are isolated - they have no relationships to Chunk or Entity nodes, making them invisible to graph queries like `zot_graph_search`, `zot_find_related_papers`, etc.

**Current (broken) state:**
```
Paper (isolated)
Chunk → Entity  (FROM_CHUNK)
Entity → Entity  (AUTHORED_BY, etc.)
```

**Desired state:**
```
Paper → Chunk → Entity  (HAS_CHUNK + FROM_CHUNK)
Paper → Entity  (MENTIONS, AUTHORED_BY, etc.)
```

## Solution

This migration script connects isolated Paper nodes by:
1. Matching Neo4j Chunk nodes to Qdrant chunks (by text content)
2. Creating `Paper → HAS_CHUNK → Chunk` relationships
3. Propagating `Chunk → Entity` relationships to `Paper → Entity`

**No re-parsing or re-embedding required** - uses existing Qdrant and Neo4j data.

## When to Run

### ⚠️ **RECOMMENDED: Wait for full library indexing to complete**

**Why?**
- Full library indexing is currently at batch 50/69 (~72% complete)
- Running now would require re-running after indexing completes
- More efficient to migrate once after all papers are indexed

**Current status:**
- Papers in Neo4j: ~2,370 (batches 1-49)
- Papers remaining: ~1,056 (batches 50-69)
- Time to completion: ~7-10 hours

**Recommended workflow:**
1. **NOW:** Test the script on 5-10 papers
2. **WAIT:** Let indexing complete (~7-10 hours)
3. **THEN:** Run full migration (~2-4 hours)

## Usage

### Test Run (recommended first)

Test on 5 papers to verify everything works:

```bash
cd /Users/claudiusv.schroder/toolboxes/agent-zot
.venv/bin/python3 scripts/migrate_neo4j_paper_links.py --test --test-limit 5
```

### Validation Only

Check current state without making changes:

```bash
.venv/bin/python3 scripts/migrate_neo4j_paper_links.py --validate-only
```

### Full Migration

After indexing completes, run full migration:

```bash
# This will process ALL papers in Neo4j
.venv/bin/python3 scripts/migrate_neo4j_paper_links.py
```

## Expected Output

### Test Run (5 papers)
```
================================================================================
NEO4J PAPER LINK MIGRATION
================================================================================
⚠️  TEST MODE: Processing only 5 papers
Found 5 papers needing migration

[1/5] Processing ABCD1234
Migrating: Example Paper Title...
  Found 45 chunks in Qdrant
  Matched 43/45 chunks to Neo4j
  Created 43 HAS_CHUNK relationships
  Linked to 12 entities (3 persons, 6 concepts, 2 methods)

[2/5] Processing EFGH5678
...

================================================================================
MIGRATION COMPLETE
================================================================================
Total papers: 5
Successful: 5
Failed: 0
Total chunks linked: 215
Total entities linked: 58
Duration: 2.3 minutes

================================================================================
VALIDATING MIGRATION
================================================================================
Total papers: 2,370
Isolated papers: 2,365
Papers with entity links: 5
HAS_CHUNK relationships: 215
MENTIONS relationships: 58
⚠️  VALIDATION INCOMPLETE - 2,365 papers still isolated
```

### Full Run (all papers after indexing completes)
```
================================================================================
NEO4J PAPER LINK MIGRATION
================================================================================
Found 3,426 papers needing migration

[1/3426] Processing ABCD1234
...
[100/3426] Processing ...
📊 Progress: 100/3426 papers processed (98 successful, 2 failed)
...

================================================================================
MIGRATION COMPLETE
================================================================================
Total papers: 3,426
Successful: 3,395
Failed: 31
Total chunks linked: 193,520
Total entities linked: 45,678
Duration: 147.2 minutes (2.5 hours)

================================================================================
VALIDATING MIGRATION
================================================================================
Total papers: 3,426
Isolated papers: 0
Papers with entity links: 3,395
HAS_CHUNK relationships: 193,520
MENTIONS relationships: 45,678
✅ VALIDATION PASSED - No isolated papers!
```

## Performance

**Test run (5 papers):**
- Time: ~2-3 minutes
- Matches ~200-250 chunks

**Full run (3,426 papers):**
- Time: ~2-4 hours
- Matches ~195,520 chunks
- Creates ~45,000-50,000 entity relationships

**Factors affecting speed:**
- Number of chunks per paper (varies widely: 5-1,200 chunks)
- Text matching complexity
- Neo4j query performance

## What Gets Created

### Relationships

**HAS_CHUNK** (Paper → Chunk):
- Links papers to their document chunks
- ~195,520 relationships (one per Qdrant chunk)

**MENTIONS** (Paper → Entity):
- Generic relationship to all entities mentioned in paper
- ~45,000-50,000 relationships

**Typed relationships** (Paper → Entity):
- `AUTHORED_BY` → Person entities
- `DISCUSSES_CONCEPT` → Concept entities
- `USES_METHOD` → Method entities
- `USES_DATASET` → Dataset entities
- `APPLIES_THEORY` → Theory entities
- `AFFILIATED_WITH` → Institution entities
- `PUBLISHED_IN` → Journal entities
- `BELONGS_TO_FIELD` → Field entities

## Troubleshooting

### "No chunks found in Qdrant"
**Cause:** Paper exists in Neo4j but not yet in Qdrant (still being indexed)
**Solution:** Wait for indexing to complete

### "Could not match any chunks to Neo4j"
**Cause:** Text content mismatch between Qdrant and Neo4j
**Solution:** Check if Neo4j chunks have correct text content

### "Validation failed - papers still isolated"
**Cause:** Some papers couldn't be matched or linked
**Solution:** Check error log for specific paper keys, may need manual investigation

## Next Steps After Migration

1. **Verify graph queries work:**
   ```python
   from agent_zot.tools import zot_graph_search

   # Should now return results
   results = zot_graph_search("papers about neural networks")
   ```

2. **Fix ingestion code** to prevent future papers from being isolated:
   - Update `src/agent_zot/clients/neo4j_graphrag.py`
   - Add Paper→Chunk→Entity linking to `add_papers_with_chunks()` method

3. **Test Neo4j tools:**
   - `zot_find_related_papers()` - should find connections
   - `zot_find_citation_chain()` - should traverse networks
   - `zot_explore_concept_network()` - should map relationships

## Files

- **Migration script:** `scripts/migrate_neo4j_paper_links.py`
- **This README:** `scripts/MIGRATION_README.md`
- **Log location:** Console output (save with `2>&1 | tee migration.log`)

## Safety

- **Idempotent:** Safe to run multiple times (uses MERGE, not CREATE)
- **Non-destructive:** Only adds relationships, doesn't modify existing data
- **Qdrant untouched:** Only reads from Qdrant, no writes
- **Parse cache untouched:** No re-parsing of PDFs
