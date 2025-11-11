# Graphiti Metadata Linking Strategy

**Created**: November 7, 2025
**Status**: ✅ Implemented
**Branch**: graphiti-metadata

---

## Problem

We need to link Graphiti episodes/entities back to specific Zotero papers in Agent-Zot's structured schema (Qdrant + Neo4j). This enables queries like:

- "What entities were extracted from paper ABC123?"
- "Show me all Graphiti episodes for this Zotero item"
- "Link this Graphiti discovery back to the source paper"

---

## Solution: Embedded Metadata in Episode Names

Since Graphiti's MCP `add_memory` tool doesn't support custom metadata dictionaries, we embed the Zotero `item_key` in **three locations** for maximum linkability:

### 1. Episode Name Pattern
```python
episode_name = f"Paper {paper_key} - Part {batch_num}/{total_batches}"
# Example: "Paper ABC123 - Part 1/3"
```

**Rationale**: Episode names are:
- ✅ Searchable via `mcp__graphiti__search_memory_nodes`
- ✅ Persistent in Graphiti's Neo4j backend
- ✅ Human-readable for debugging
- ✅ Parseable for programmatic extraction

### 2. Source Description
```python
source_description = f"Zotero paper chunk [item_key={paper_key}]: {title} by {authors}"
# Example: "Zotero paper chunk [item_key=ABC123]: Attention is All You Need by Vaswani et al."
```

**Rationale**: Provides secondary searchability and context.

### 3. Batch Metadata Dict (Future-Proofing)
```python
batch_metadata = dict(metadata)
batch_metadata["zotero_item_key"] = paper_key
```

**Rationale**: If Graphiti SDK adds custom metadata support in the future, we're ready.

---

## Implementation

### Modified Files

#### 1. `src/agent_zot/ingestion/graphiti_ingestion.py`
**Function**: `_create_batches()`

**Changes**:
- Added `zotero_item_key` to batch metadata dict
- Enhanced docstring to explain linking strategy
- Added inline comments documenting the approach

#### 2. `src/agent_zot/clients/graphiti_client.py`
**Function**: `add_paper_chunk()`

**Changes**:
- Updated `source_description` to include `[item_key={paper_key}]` tag
- Enhanced docstring with cross-schema linking examples
- Added logging for episode_name tracking
- Added technical note about Graphiti SDK limitations

**Function**: `get_paper_entities()`

**Changes**:
- Enhanced docstring with episode name pattern documentation
- Added example usage
- Improved logging with structured metadata

---

## Usage Examples

### Ingestion (Automatic)
```python
from agent_zot.ingestion.graphiti_ingestion import ingest_to_graphiti

result = await ingest_to_graphiti(
    paper_key="ABC123",
    chunks=["...", "..."],
    metadata={"title": "...", "authors": "..."},
    config=config
)

# Creates episodes:
# - "Paper ABC123 - Part 1/2"
# - "Paper ABC123 - Part 2/2"
```

### Querying Entities by Paper (Programmatic)
```python
from agent_zot.clients.graphiti_client import GraphitiClient

client = GraphitiClient(group_id="agent-zot-discovery")

# Get all entities extracted from paper ABC123
entities = client.get_paper_entities("ABC123")

for entity in entities:
    print(f"Entity: {entity.name}")
    print(f"Type: {entity.entity_type}")
    print(f"Summary: {entity.summary}")
```

### Querying via MCP (Manual)
```python
# Search for episodes from specific paper
mcp__graphiti__search_memory_nodes(
    query="Paper ABC123",
    group_ids=["agent-zot-discovery"],
    max_nodes=50
)

# Or search by item_key tag
mcp__graphiti__search_memory_nodes(
    query="item_key=ABC123",
    group_ids=["agent-zot-discovery"],
    max_nodes=50
)
```

---

## Episode Structure Example

After ingestion, Graphiti episodes have this structure:

```json
{
  "name": "Paper ABC123 - Part 1/3",
  "content": "...combined chunk text...",
  "source": "text",
  "source_description": "Zotero paper chunk [item_key=ABC123]: Attention is All You Need by Vaswani et al.",
  "group_id": "agent-zot-discovery",
  "created_at": "2025-11-07T22:00:00Z"
}
```

**Entities extracted** from this episode inherit the association via Graphiti's internal episode tracking.

---

## Querying Patterns

### Pattern 1: Find All Entities from Paper
```python
entities = client.search_entities(
    query="Paper ABC123",
    max_nodes=50
)
```

### Pattern 2: Find Specific Entity Type from Paper
```python
entities = client.search_entities(
    query="Paper ABC123",
    entity_type="Preference",  # Or "Procedure"
    max_nodes=50
)
```

### Pattern 3: Parse Episode Name to Extract Item Key
```python
import re

episode_name = "Paper ABC123 - Part 2/5"
match = re.match(r"Paper ([A-Z0-9]+) - Part \d+/\d+", episode_name)
if match:
    item_key = match.group(1)  # "ABC123"
```

---

## Benefits

### ✅ Cross-Schema Linking
- Graphiti entities → Zotero papers (via episode name parsing)
- Zotero papers → Graphiti entities (via `get_paper_entities()`)

### ✅ Searchability
- Episode names are indexed in Graphiti's Neo4j backend
- Source descriptions provide secondary search path
- Works with existing MCP search tools

### ✅ Human-Readable
- Episode names like "Paper ABC123 - Part 1/3" are intuitive
- Easy debugging in Graphiti's UI or CLI
- Clear audit trail for data provenance

### ✅ Future-Proof
- Batch metadata dict ready for Graphiti SDK enhancements
- Pattern-based approach works with any Graphiti backend
- No breaking changes to existing Agent-Zot code

---

## Limitations

### ⚠️ Episode Name Parsing Required
- No direct metadata dict access (Graphiti SDK limitation)
- Requires regex or string parsing to extract item_key from episode names
- Episode name format must remain consistent

### ⚠️ Manual Queries Needed
- No built-in "get episodes by metadata" endpoint
- Must use search-based queries with episode name patterns
- Performance depends on Graphiti's search index

### ⚠️ No Reverse Index
- Graphiti doesn't maintain a "papers → episodes" index
- Must search episodes to find papers (acceptable for Phase 1)
- Could build external index if needed (future optimization)

---

## Future Enhancements

### Option 1: Graphiti SDK Custom Metadata (if added)
If Graphiti adds support for custom metadata dicts:
```python
result = await graphiti.add_episode(
    name=episode_name,
    episode_body=chunk_text,
    source=EpisodeType.text,
    metadata={"zotero_item_key": paper_key}  # ← NEW
)
```

### Option 2: External Linking Table
Create a lightweight index:
```python
# SQLite table: paper_episodes
{
    "paper_key": "ABC123",
    "episode_uuid": "e4f8a2...",
    "episode_name": "Paper ABC123 - Part 1/3",
    "created_at": "2025-11-07T22:00:00Z"
}
```

### Option 3: Graphiti Group ID per Paper
Instead of one global group (`agent-zot-discovery`), use:
```python
group_id = f"paper-{paper_key}"  # "paper-ABC123"
```

**Tradeoff**: Better isolation but 7,390 groups (one per paper) may complicate search.

---

## Testing

### Unit Tests
- ✅ `test_create_batches_includes_item_key()` - Verify metadata augmentation
- ✅ `test_add_paper_chunk_embeds_item_key()` - Verify episode name pattern
- ✅ `test_source_description_contains_item_key()` - Verify searchability

### Integration Tests
- ✅ End-to-end ingestion → query workflow
- ✅ Episode name parsing accuracy
- ✅ Cross-schema linking validation

---

## Decision Rationale

**Why episode names instead of custom metadata?**

1. **SDK Constraint**: Graphiti's `mcp__graphiti__add_memory` doesn't accept custom metadata dict (as of Nov 2025)
2. **Searchability**: Episode names are indexed and searchable via existing MCP tools
3. **Simplicity**: No need for external tables or complex indexing
4. **Debuggability**: Human-readable episode names aid troubleshooting
5. **Future-Proof**: Can add metadata dict later without breaking episode name approach

**Why not Graphiti's `uuid` field?**

- UUIDs are auto-generated by Graphiti, not user-controlled
- Can't set custom UUIDs during `add_memory` call
- Would require post-ingestion lookup and mapping (complex)

**Why not use `group_id` per paper?**

- 7,390 groups (one per paper) complicates search queries
- Global group (`agent-zot-discovery`) enables cross-paper entity discovery
- Episode name pattern provides sufficient paper-level filtering

---

## Conclusion

The **embedded metadata in episode names** approach provides robust cross-schema linking between Graphiti and Agent-Zot's structured schema without requiring Graphiti SDK modifications or external indexing tables.

**Metadata Storage**:
- ✅ Episode name: `"Paper {item_key} - Part X/Y"`
- ✅ Source description: `"...
[item_key={item_key}]..."`
- ✅ Batch metadata dict: `{"zotero_item_key": item_key}` (future-proof)

**Query Pattern**:
```python
entities = client.get_paper_entities("ABC123")
# Searches episodes with name="Paper ABC123*"
```

This solution is production-ready, maintainable, and extensible for Phase 1 deployment.
