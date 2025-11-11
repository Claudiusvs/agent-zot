# Agent-Zot Manual Test Checklist

Quick checklist for verifying all tools and modes work correctly.

## Backend Tests

- [ ] **Qdrant**: `docker ps` shows agent-zot-qdrant running
- [ ] **Neo4j**: `docker ps` shows agent-zot-neo4j running
- [ ] **Zotero**: Database accessible at ~/zotero_database/zotero.sqlite

## Tool Tests

### 1. zot_search (5 modes)

Test queries that trigger each mode:

- [ ] **Fast Mode**: `zot_search("papers about working memory")`
  - Should use: Qdrant only
  - Expected: ~2 seconds, 10 results

- [ ] **Entity-enriched Mode**: `zot_search("which methods appear in papers about attention?")`
  - Should use: Qdrant chunks + Neo4j entities
  - Expected: ~4 seconds, entities extracted

- [ ] **Graph-enriched Mode**: `zot_search("who collaborated with Anderson?")`
  - Should use: Qdrant + Neo4j relationships
  - Expected: ~4 seconds, collaboration data

- [ ] **Metadata-enriched Mode**: `zot_search("papers by Anderson published in 2015")`
  - Should use: Qdrant + Zotero API
  - Expected: ~4 seconds, filtered by metadata

- [ ] **Comprehensive Mode**: `zot_search("neural mechanisms", force_mode="comprehensive")`
  - Should use: All backends (sequential)
  - Expected: ~6-8 seconds, merged results

### 2. zot_summarize (4 modes)

Get a test paper key first: Use any item_key from search results.

- [ ] **Quick Mode**: `zot_summarize(item_key, "What is this paper about?")`
  - Should return: Metadata + abstract
  - Expected: ~1 second, 500-800 tokens

- [ ] **Targeted Mode**: `zot_summarize(item_key, "What methodology did they use?")`
  - Should use: Semantic Q&A on chunks
  - Expected: ~2-3 seconds, relevant chunks

- [ ] **Comprehensive Mode**: `zot_summarize(item_key, "Summarize comprehensively")`
  - Should ask: 4 key questions (research question, methods, findings, conclusions)
  - Expected: ~8-10 seconds, 8-15k tokens

- [ ] **Full Mode**: `zot_summarize(item_key, force_mode="full")`
  - Should extract: Complete PDF text
  - Expected: ~10-30 seconds, 10-100k tokens (expensive!)

### 3. zot_explore_graph (9 modes)

- [ ] **Citation Chain**: `zot_explore_graph("Find papers citing papers that cite X", paper_key="KEY")`
  - Should use: Neo4j 2-hop citation traversal

- [ ] **Influence Mode**: `zot_explore_graph("Find influential papers on working memory")`
  - Should use: Neo4j PageRank analysis

- [ ] **Content Similarity**: `zot_explore_graph("Find papers similar to X", paper_key="KEY")`
  - Should use: Qdrant vector similarity

- [ ] **Related Papers**: `zot_explore_graph("Papers related to X", paper_key="KEY")`
  - Should use: Neo4j shared entities

- [ ] **Collaboration**: `zot_explore_graph("Who collaborated with Anderson?", author="Anderson")`
  - Should use: Neo4j co-authorship network

- [ ] **Concept Network**: `zot_explore_graph("Concepts related to memory encoding")`
  - Should use: Neo4j concept relationships

- [ ] **Temporal**: `zot_explore_graph("How has attention research evolved from 2010-2020?")`
  - Should use: Neo4j with yearly trends
  - Should extract: start_year=2010, end_year=2020

- [ ] **Venue Analysis**: `zot_explore_graph("Top journals in cognitive neuroscience")`
  - Should use: Neo4j publication statistics

- [ ] **Comprehensive**: `zot_explore_graph("Explore everything about X", force_mode="comprehensive")`
  - Should use: Multiple strategies merged

### 4. zot_manage_collections (6 modes)

- [ ] **List**: `zot_manage_collections("list all collections")`
- [ ] **Create**: `zot_manage_collections("create collection Test Collection")`
- [ ] **Show Items**: `zot_manage_collections("show items in Test Collection")`
- [ ] **Add**: `zot_manage_collections("add ITEMKEY to Test Collection")`
- [ ] **Remove**: `zot_manage_collections("remove ITEMKEY from Test Collection")`
- [ ] **Recent**: `zot_manage_collections("show recently added items", limit=10)`

### 5. zot_manage_tags (4 modes)

- [ ] **List**: `zot_manage_tags("list all tags")`
- [ ] **Search**: `zot_manage_tags("find papers tagged important")`
- [ ] **Add**: `zot_manage_tags("add tag reviewed to ITEMKEY")`
- [ ] **Remove**: `zot_manage_tags("remove tag draft from ITEMKEY")`

### 6. zot_manage_notes (4 modes)

- [ ] **List Annotations**: `zot_manage_notes("list annotations for ITEMKEY")`
- [ ] **List Notes**: `zot_manage_notes("show my notes")`
- [ ] **Search**: `zot_manage_notes("search for notes about methodology")`
- [ ] **Create**: `zot_manage_notes("create note for ITEMKEY titled 'Review'")`

### 7. zot_export (3 modes)

- [ ] **Markdown**: `zot_export("papers.md", format="markdown", limit=5)`
- [ ] **BibTeX**: `zot_export("refs.bib", format="bibtex", limit=5)`
- [ ] **GraphML**: `zot_export("network.graphml", format="graphml")`

### 8. zot_manage_database (12 modes)

- [ ] **Update**: `zot_manage_database("update database")`
- [ ] **Test**: `zot_manage_database("test on 10 papers")`
- [ ] **Status**: `zot_manage_database("show status")`
- [ ] **Statistics**: `zot_manage_database("show statistics")`
- [ ] **Backup**: `zot_manage_database("backup databases")`
- [ ] **List Backups**: `zot_manage_database("show available backups")`

### 9. zot_daemon_status

- [ ] **Status**: `zot_daemon_status()`
  - Should show: Running state, queue stats, last update

## Intent Detection Tests

These queries should automatically select the correct mode:

- [ ] "papers about X" → Fast Mode
- [ ] "which methods/concepts appear in papers about X" → Entity-enriched
- [ ] "who collaborated with X" → Graph-enriched
- [ ] "papers by X published in YEAR" → Metadata-enriched
- [ ] "What is this paper about?" → Quick Mode (summarize)
- [ ] "What methodology did they use?" → Targeted Mode (summarize)
- [ ] "Summarize this comprehensively" → Comprehensive Mode (summarize)
- [ ] "Find influential papers" → Influence Mode (explore)
- [ ] "Papers similar to X" → Content Similarity (explore)
- [ ] "How has X evolved from YEAR to YEAR" → Temporal Mode (explore)

## Error Handling Tests

- [ ] Invalid item_key → Graceful error message
- [ ] Empty query → Validation error
- [ ] Backend unavailable → Fallback or clear error
- [ ] No results found → Helpful suggestions

## Performance Benchmarks

- [ ] Fast Mode: < 3 seconds
- [ ] Enriched Modes: < 5 seconds
- [ ] Comprehensive Mode: < 10 seconds
- [ ] Quick Summary: < 2 seconds
- [ ] Targeted Summary: < 5 seconds
- [ ] Comprehensive Summary: < 12 seconds

## Results Quality

- [ ] Search results are relevant to query
- [ ] Summaries capture key information
- [ ] Graph exploration returns connected papers
- [ ] Intent detection accuracy > 90%
- [ ] No duplicate results in merged modes
