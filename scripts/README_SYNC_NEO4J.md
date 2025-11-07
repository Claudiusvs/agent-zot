# Sync Missing Papers to Neo4j

**RECOMMENDED**: Use `sync_missing_papers_to_neo4j_v2.py` - it's simpler and faster!

This script adds papers that exist in Qdrant but are missing from Neo4j, **using data already in Qdrant** (no need to touch Zotero or the parse cache).

## Problem

Based on the audit, 151 papers have processed chunks in Qdrant but are missing from Neo4j:
- **Qdrant**: 2,519 papers with chunks
- **Neo4j**: 2,370 papers
- **Missing**: 151 papers (6% gap)

This happened because Neo4j entity extraction is slow (~5-10 min per batch) and the initial population was likely interrupted.

## Solution

**V2 Script (RECOMMENDED)**: Reads data directly from Qdrant
- ✅ No Zotero access needed
- ✅ No parse cache needed
- ✅ Simpler and faster
- ✅ Uses the SAME data that's already indexed

**V1 Script**: Reads from Zotero + parse cache
- ⚠️ More complex
- ⚠️ Slower
- ❌ Unnecessary file I/O

## Usage (V2 - Recommended)

### 1. Dry Run (recommended first)

See what would be done without making changes:

```bash
.venv/bin/python scripts/sync_missing_papers_to_neo4j_v2.py --dry-run
```

**Output:**
```
STEP 1: Identifying missing papers
Found 2519 papers with chunks in Qdrant
Found 2370 papers in Neo4j

Summary:
  Papers in Qdrant: 2519
  Papers in Neo4j: 2370
  Missing from Neo4j: 151

🔍 DRY RUN MODE - No changes will be made

Would add 151 papers to Neo4j:
  1. 227R96PW
  2. 24EDLTK3
  ...
```

### 2. Run Actual Sync

Add the missing papers:

```bash
.venv/bin/python scripts/sync_missing_papers_to_neo4j_v2.py
```

**With custom batch size:**
```bash
.venv/bin/python scripts/sync_missing_papers_to_neo4j_v2.py --batch-size 3
```

**With custom config:**
```bash
.venv/bin/python scripts/sync_missing_papers_to_neo4j_v2.py --config ~/.config/agent-zot/config.json
```

## How It Works

### Data Flow (V2):

```
Qdrant (Already has everything)
  ├─ Paper metadata (title, authors, abstract, date)
  ├─ All chunks with text content
  └─ Chunk metadata (headings, IDs)
        ↓
  Reconstruct item format
        ↓
  Neo4j Entity Extraction
```

**Why this works:**
- Qdrant stores complete paper metadata in EVERY chunk
- We can reconstruct the full paper from its chunks
- This is THE SAME data the original pipeline used
- No information loss vs reading from Zotero

### Data Flow (V1 - Not Recommended):

```
Zotero SQLite DB
        ↓
  Parse Cache (~/.cache/agent-zot/parsed_docs.db)
        ↓
  Reconstruct item format
        ↓
  Neo4j Entity Extraction
```

## Performance

**Estimated Duration:**
- 151 papers ÷ 5 papers per batch = 31 batches
- ~5-10 min per batch = **2.5-5 hours total**

**V2 is slightly faster** because:
- No SQLite queries to Zotero
- No parse cache lookups
- Qdrant already optimized for bulk retrieval

**Progress Tracking:**
```
Fetched 10/151 papers...
Fetched 20/151 papers...
...
```

## Output Files

### `/tmp/missing_papers_neo4j.json`
List of paper keys missing from Neo4j:
```json
[
  "227R96PW",
  "24EDLTK3",
  "24G22K4T",
  ...
]
```

### `/tmp/neo4j_sync_results.json`
Detailed results:
```json
{
  "start_time": "2025-11-03T...",
  "duration": "3:24:15",
  "missing_papers_count": 151,
  "prepared_papers_count": 149,
  "result": {
    "successful": 148,
    "failed": 1,
    "total_chunks": 13764,
    "errors": [...]
  }
}
```

## What Gets Created in Neo4j

For each paper, the script creates:

1. **Paper Node**
   - Properties: item_key, title, abstract, year, authors
   - Label: `Paper`

2. **Chunk Nodes** (first 20 chunks per paper)
   - Properties: chunk_id, text, qdrant_point_id, headings
   - Label: `Chunk`
   - Relationship: `(Paper)-[:HAS_CHUNK]->(Chunk)`

3. **Entity Nodes** (extracted from chunks)
   - Labels: `Person`, `Concept`, `Method`, `Institution`, etc.
   - Relationships: `(Chunk)-[:CONTAINS_ENTITY]->(Entity)`

4. **Author Nodes**
   - Label: `Person`
   - Relationship: `(Paper)-[:AUTHORED_BY]->(Person)`

## Safety Features

✅ **Idempotent**: Uses `MERGE` - won't duplicate if paper already exists
✅ **Read-only on Qdrant**: Only reads from Qdrant, never writes
✅ **Dry-run mode**: Preview changes before executing
✅ **Error handling**: Continues processing if individual papers fail
✅ **Detailed logging**: Progress tracking and error reporting

## Troubleshooting

### Issue: "Paper X has no chunks in Qdrant"

**Cause**: Paper key exists but has no chunk data (shouldn't happen in practice)
**Solution**: This is expected for metadata-only entries. Script will skip these.

### Issue: "Error extracting entities for chunk Y"

**Cause**: LLM extraction failed (timeout, API error, malformed text)
**Solution**: Script continues with other chunks. Check errors in output JSON.

### Issue: Script hangs or takes >8 hours

**Cause**: Default batch_size=5 is conservative
**Solution**: Increase batch size if you have good internet/API limits:
```bash
.venv/bin/python scripts/sync_missing_papers_to_neo4j_v2.py --batch-size 10
```

### Issue: "Error fetching paper X from Qdrant"

**Cause**: Qdrant query failed or paper has malformed data
**Solution**: Script continues with other papers. Check error logs.

## Expected Results

After running successfully:

**Before:**
- Neo4j: 2,370 papers (94.1% coverage)
- Missing: 151 papers

**After:**
- Neo4j: 2,519 papers (100% coverage) ✅
- Missing: 0 papers

**Verification:**
```bash
# Check Neo4j paper count
docker exec agent-zot-neo4j cypher-shell -u neo4j -p demodemo \
  "MATCH (p:Paper) RETURN count(p) as total"
# Should show: 2519
```

## Why Use V2 Instead of V1?

| Feature | V2 (Qdrant) | V1 (Zotero+Cache) |
|---------|-------------|-------------------|
| **Data Source** | Qdrant only | Zotero + parse cache |
| **Speed** | Fast | Slower (SQLite I/O) |
| **Simplicity** | Single data source | Multiple lookups |
| **Dependencies** | Qdrant (already running) | Zotero DB + cache DB |
| **Data Freshness** | Same as Qdrant | Same (from cache) |
| **Reliability** | High | High |

**Recommendation**: Use V2 unless you have a specific reason to use V1.

## Alternative: Full Rebuild

If you prefer to rebuild everything from scratch:

```bash
agent-zot update-db --force-rebuild --fulltext
```

**Pros:**
- Ensures perfect consistency
- Rebuilds both Qdrant and Neo4j from source

**Cons:**
- Takes 72-84 hours (full Qdrant rebuild)
- Loses any manual Neo4j edits
- Higher risk of interruption

**Recommendation**: Use the sync script instead - it's faster, safer, and surgical.

## Questions?

See the main audit reports:
- `NEO4J_AUDIT_REPORT_FINAL.md` - Complete Neo4j analysis
- `MISSING_PDFS_VALIDATION.md` - Qdrant coverage analysis
- `QDRANT_AUDIT_REPORT.md` - Full Qdrant audit
