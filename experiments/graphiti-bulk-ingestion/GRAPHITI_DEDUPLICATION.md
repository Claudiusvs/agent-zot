# Graphiti Deduplication System

## Overview

Graphiti ingestion uses the same multi-layer deduplication architecture as agent-zot's main pipeline to ensure papers are never reprocessed and API costs are minimized.

## Deduplication Architecture

### Agent-Zot Main Pipeline (3 Layers)

1. **Parse Cache** (`~/.cache/agent-zot/parsed_docs.db`)
   - Prevents re-extracting same PDF
   - Stores extraction results per item_key + PDF hash

2. **Qdrant Checks**
   - Prevents re-embedding same chunks
   - Checks for existing points before upserting

3. **Neo4j GraphRAG Checks**
   - Prevents duplicate entities
   - MERGE operations ensure uniqueness

### Graphiti Pipeline (Episode Cache)

**Episode Cache** (`~/.cache/agent-zot/graphiti_episodes.db`)
- Tracks which papers have been ingested to Graphiti
- Prevents duplicate entity extraction
- Ensures same paper never reprocessed (unless `force_reingest=True`)

## Schema

```sql
CREATE TABLE episodes (
    paper_key TEXT PRIMARY KEY,
    episode_count INTEGER NOT NULL,
    chunks_processed INTEGER NOT NULL,
    timestamp REAL NOT NULL,
    success INTEGER NOT NULL
);
```

## Workflow

### First Time Ingestion

```python
# Paper C93XCB7U (not in cache)
should_ingest_to_graphiti("C93XCB7U", ...)  # Returns: True
ingest_to_graphiti("C93XCB7U", ...)         # Processes paper
# → Creates 4 episodes, 94 chunks processed
# → Adds to cache: {paper_key: "C93XCB7U", episode_count: 4, success: True}
```

### Subsequent Attempts (Deduplication)

```python
# Paper C93XCB7U (already in cache)
should_ingest_to_graphiti("C93XCB7U", ...)  # Returns: False (cached)
# No processing happens - saves API costs
```

### Force Re-ingestion

```python
# Explicitly force reprocessing
should_ingest_to_graphiti("C93XCB7U", ..., force_reingest=True)  # Returns: True
ingest_to_graphiti("C93XCB7U", ..., force_reingest=True)          # Reprocesses
```

## API

### `GraphitiEpisodeCache`

```python
from agent_zot.ingestion.graphiti_cache import get_episode_cache

cache = get_episode_cache()

# Check if paper processed
if cache.has_paper("ABC123"):
    print("Already processed")

# Get ingestion info
info = cache.get_paper_info("ABC123")
# → {'episode_count': 4, 'chunks_processed': 94, 'timestamp': 1699..., 'success': True}

# Add paper after successful ingestion
cache.add_paper(
    paper_key="ABC123",
    episode_count=4,
    chunks_processed=94,
    success=True
)

# Remove paper (force re-ingestion)
cache.remove_paper("ABC123")

# Get statistics
stats = cache.get_stats()
# → {'total_papers': 2500, 'successful': 2480, 'failed': 20, 'total_chunks': 150000}

# Clear failed records (to retry)
cache.clear_failed()

# Clear entire cache (danger!)
cache.clear_all()
```

### Integration with Ingestion

```python
from agent_zot.ingestion.graphiti_ingestion import (
    ingest_to_graphiti,
    should_ingest_to_graphiti
)

# Check before processing
if should_ingest_to_graphiti(paper_key, metadata, config):
    result = await ingest_to_graphiti(
        paper_key=paper_key,
        chunks=chunks,
        metadata=metadata,
        config=config,
        force_reingest=False  # Respect cache (default)
    )
else:
    print(f"Paper {paper_key} already processed, skipping")
```

## Benefits

1. **Cost Savings**
   - Prevents duplicate API calls to GPT-5-mini
   - ~$0.007 per paper × 2,500 papers = $17.50 saved on re-runs

2. **Time Savings**
   - Skip already-processed papers
   - Bulk catch-up processes only missing papers

3. **Consistency**
   - Same deduplication pattern as agent-zot
   - Familiar cache management API

4. **Safety**
   - Never accidentally reprocess same paper
   - Explicit force flag required for re-ingestion

## Maintenance

### Check Cache Status

```bash
# Via Python
python -c "from agent_zot.ingestion.graphiti_cache import get_episode_cache; print(get_episode_cache().get_stats())"
```

### Clear Failed Papers (Retry)

```python
from agent_zot.ingestion.graphiti_cache import get_episode_cache

cache = get_episode_cache()
cache.clear_failed()  # Remove failed records to retry
```

### Force Full Re-ingestion

```python
from agent_zot.ingestion.graphiti_cache import get_episode_cache

cache = get_episode_cache()
cache.clear_all()  # WARNING: Clears entire cache, all papers will be reprocessed
```

## Auto-Sync Integration

The auto-sync daemon automatically uses the episode cache:

1. New paper detected in Zotero
2. Processed through Qdrant + Neo4j GraphRAG
3. Checked against episode cache
4. If not cached → ingested to Graphiti
5. If cached → skipped (deduplication)

This ensures:
- New papers go through full pipeline (Qdrant + Neo4j + Graphiti)
- Existing papers never reprocessed
- Cache automatically maintained
