# Agent-Zot Tool Hierarchy & Decision Trees

Visual overview of all tools, their modes, and decision logic.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  AGENT-ZOT MCP SERVER                        │
│                     (9 Active Tools)                         │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   ┌────▼────┐         ┌────▼────┐        ┌────▼────┐
   │ Qdrant  │         │ Neo4j   │        │ Zotero  │
   │ Vector  │         │ Graph   │        │ Library │
   │  DB     │         │   DB    │        │   API   │
   └─────────┘         └─────────┘        └─────────┘
   234k chunks         25k nodes          7.4k items
                       134k rels
```

## Tool Hierarchy

### TIER 1: Research Tools (Core Intelligence)

#### 1. zot_search - Intent-Driven Paper Discovery
```
zot_search(query, limit, force_mode)
    │
    ├──► Intent Detection Layer
    │    └──► Pattern matching on query text
    │
    ├──► Mode Selection (5 modes)
    │    │
    │    ├─► Fast Mode
    │    │   └─► Trigger: Semantic concepts ("papers about X")
    │    │   └─► Backend: Qdrant only
    │    │   └─► Time: ~2s
    │    │
    │    ├─► Entity-enriched Mode
    │    │   └─► Trigger: Entity discovery ("which X appear in Y")
    │    │   └─► Backend: Qdrant chunks + Neo4j entities
    │    │   └─► Time: ~4s
    │    │
    │    ├─► Graph-enriched Mode
    │    │   └─► Trigger: Relationships ("who collaborated with X")
    │    │   └─► Backend: Qdrant + Neo4j graph
    │    │   └─► Time: ~4s
    │    │
    │    ├─► Metadata-enriched Mode
    │    │   └─► Trigger: Author/year filters ("by X in YEAR")
    │    │   └─► Backend: Qdrant + Zotero API
    │    │   └─► Time: ~4s
    │    │
    │    └─► Comprehensive Mode
    │        └─► Trigger: force_mode OR quality escalation
    │        └─► Backend: All (sequential to prevent freeze)
    │        └─► Time: ~6-8s
    │
    └──► Output
         └─► Papers + provenance (which backend found each)
```

**Decision Tree:**
```
Query → Intent Detection → Mode Selection → Backend Execution → Merge Results
  │            │                  │                │                   │
  └─► NLP ────►│◄─ Patterns       │                │                   │
               │                  │                │                   │
               ▼                  ▼                ▼                   ▼
         Fast/Entity/      Execute 1-3      Qdrant/Neo4j/      Deduplicate
         Graph/Meta/       backends in      Zotero APIs        & rank
         Comprehensive     parallel/seq
```

---

#### 2. zot_summarize - Depth-Aware Paper Understanding
```
zot_summarize(item_key, query, force_mode, top_k)
    │
    ├──► Depth Detection Layer
    │    └──► Analyze query complexity & intent
    │
    ├──► Mode Selection (4 modes)
    │    │
    │    ├─► Quick Mode
    │    │   └─► Trigger: Overview questions ("what is this about")
    │    │   └─► Source: Zotero metadata + abstract
    │    │   └─► Tokens: 500-800
    │    │   └─► Time: ~1s
    │    │
    │    ├─► Targeted Mode
    │    │   └─► Trigger: Specific questions ("what methodology")
    │    │   └─► Source: Semantic Q&A on Qdrant chunks
    │    │   └─► Tokens: 2k-5k
    │    │   └─► Time: ~2-3s
    │    │
    │    ├─► Comprehensive Mode
    │    │   └─► Trigger: "comprehensively" OR broad request
    │    │   └─► Source: Multi-aspect (4 questions asked)
    │    │   └─► Tokens: 8k-15k
    │    │   └─► Time: ~8-10s
    │    │   └─► Aspects: Research Q, Methods, Findings, Conclusions
    │    │
    │    └─► Full Mode
    │        └─► Trigger: force_mode OR non-semantic task
    │        └─► Source: Complete PDF text extraction
    │        └─► Tokens: 10k-100k (EXPENSIVE!)
    │        └─► Time: ~10-30s
    │
    └──► Output
         └─► Summary at appropriate depth + token count
```

**Decision Tree:**
```
Query + Item → Depth Detection → Mode Selection → Data Retrieval → Format Output
      │              │                  │                │               │
      └─► Intent ────►│◄─ Complexity    │                │               │
                      │                 │                │               │
                      ▼                 ▼                ▼               ▼
                Quick/Targeted/    Retrieve from    Metadata/         Structured
                Comprehensive/     1-3 sources      Chunks/           summary
                Full                                 Full text
```

---

#### 3. zot_explore_graph - Multi-Strategy Network Analysis
```
zot_explore_graph(query, paper_key, author, concept,
                  start_year, end_year, limit, max_hops, force_mode)
    │
    ├──► Intent Detection Layer
    │    └──► Pattern matching + parameter extraction
    │
    ├──► Mode Selection (9 modes)
    │    │
    │    ├─► Citation Chain Mode
    │    │   └─► Trigger: "citing papers" keywords
    │    │   └─► Backend: Neo4j multi-hop (2-3 hops)
    │    │   └─► Output: Extended citation network
    │    │
    │    ├─► Influence Mode (PageRank)
    │    │   └─► Trigger: "influential"/"seminal"/"important"
    │    │   └─► Backend: Neo4j citation graph + PageRank
    │    │   └─► Output: Papers ranked by impact
    │    │
    │    ├─► Content Similarity Mode
    │    │   └─► Trigger: "similar to"/"like"
    │    │   └─► Backend: Qdrant vector similarity
    │    │   └─► Output: Papers with similar content
    │    │
    │    ├─► Related Papers Mode
    │    │   └─► Trigger: "related to" (graph-based)
    │    │   └─► Backend: Neo4j shared entities
    │    │   └─► Output: Papers with shared authors/concepts/methods
    │    │
    │    ├─► Collaboration Mode
    │    │   └─► Trigger: "collaborated"/"co-author"
    │    │   └─► Backend: Neo4j co-authorship network
    │    │   └─► Output: Extended collaboration network
    │    │
    │    ├─► Concept Network Mode
    │    │   └─► Trigger: "concepts"/"themes"
    │    │   └─► Backend: Neo4j concept relationships
    │    │   └─► Output: Related concepts through papers
    │    │
    │    ├─► Temporal Mode
    │    │   └─► Trigger: "evolved"/"YEAR to YEAR"
    │    │   └─► Backend: Neo4j temporal analysis
    │    │   └─► Output: Evolution timeline with trends
    │    │
    │    ├─► Venue Analysis Mode
    │    │   └─► Trigger: "top journals"/"venues"
    │    │   └─► Backend: Neo4j publication statistics
    │    │   └─► Output: Ranked publication outlets
    │    │
    │    └─► Comprehensive Mode
    │        └─► Trigger: "explore everything" OR force_mode
    │        └─► Backend: Multiple strategies merged
    │        └─► Output: Combined multi-perspective analysis
    │
    └──► Output
         └─► Network data + relationships + metadata
```

**Decision Tree:**
```
Query → Intent + Params → Strategy Selection → Graph Query → Format Results
  │           │                   │                │              │
  └─► NLP ────►│◄─ Extract         │                │              │
               │   author/year/    │                │              │
               │   concept          │                │              │
               ▼                    ▼                ▼              ▼
         Citation/Influence/   Execute Neo4j    Papers +      Network
         Similarity/Collab/    or Qdrant       relationships  visualization
         Concept/Temporal/     traversal                      data
         Venue/Comprehensive
```

---

### TIER 2: Management Tools (CRUD Operations)

#### 4. zot_manage_collections (6 modes)
```
List → Show all collections
Create → New collection with name + parent
Show Items → Items in specific collection
Add → Add items to collection
Remove → Remove items from collection
Recent → Recently added/modified items (library maintenance)
```

#### 5. zot_manage_tags (4 modes)
```
List → All tags with counts
Search → Find items by tag(s) with operators (||, -)
Add → Add tag(s) to items (batch)
Remove → Remove tag(s) from items (batch)
```

#### 6. zot_manage_notes (4 modes)
```
List Annotations → PDF highlights + comments
List Notes → Standalone notes
Search → Search notes by text
Create → New note for item
```

#### 7. zot_export (3 modes)
```
Markdown → .md files with YAML frontmatter (Obsidian)
BibTeX → .bib file (LaTeX)
GraphML → .graphml network (Gephi/Cytoscape)
```

---

### TIER 3: System Tools (Operations & Monitoring)

#### 8. zot_manage_database (12 modes)
```
Update Operations:
├─► update database → Incremental with fulltext
├─► test on N papers → Limited test run
├─► update without fulltext → Metadata only
└─► force rebuild → Full rebuild (auto-backup)

Backup/Restore:
├─► backup databases → Local + iCloud
├─► backup locally only → Skip iCloud
├─► show available backups → List all
├─► restore from latest → Most recent
└─► restore from icloud → Cloud backup

Monitoring:
├─► show status → Health check
├─► show statistics → Aggregate stats
└─► find papers about X → Search test
```

#### 9. zot_daemon_status (1 mode)
```
Status → Running state, queue stats, last update, config mode
```

---

## Complete Decision Flow

```
User Query
    │
    ▼
┌───────────────────────┐
│ MCP Tool Routing      │
│ (Which tool to use?)  │
└───────────────────────┘
    │
    ├─► Paper Discovery? → zot_search
    │   └─► Intent Detection → Mode Selection → Backend(s) → Results
    │
    ├─► Paper Understanding? → zot_summarize
    │   └─► Depth Detection → Mode Selection → Source(s) → Summary
    │
    ├─► Network Exploration? → zot_explore_graph
    │   └─► Intent + Params → Strategy → Graph Query → Network
    │
    ├─► Collection Ops? → zot_manage_collections
    │   └─► Mode Selection → Zotero API → Confirmation
    │
    ├─► Tag Ops? → zot_manage_tags
    │   └─► Mode Selection → Zotero API → Results
    │
    ├─► Notes Ops? → zot_manage_notes
    │   └─► Mode Selection → Zotero API → Notes
    │
    ├─► Export Data? → zot_export
    │   └─► Format Detection → Source → File
    │
    ├─► Database Ops? → zot_manage_database
    │   └─► Operation Type → Execute → Status
    │
    └─► Daemon Status? → zot_daemon_status
        └─► Query Daemon → Stats
```

---

## Intent Detection Patterns

### zot_search Triggers

| Mode | Trigger Patterns | Example Queries |
|------|-----------------|-----------------|
| Fast | "papers about", "research on", "studies on" | "papers about working memory" |
| Entity-enriched | "which X", "what X appear", "extract X" | "which methods appear in papers about attention" |
| Graph-enriched | "who collaborated", "citations", "network" | "who collaborated with Anderson?" |
| Metadata-enriched | "by AUTHOR", "in YEAR", "published" | "papers by Anderson in 2015" |
| Comprehensive | force_mode OR escalation | force_mode="comprehensive" |

### zot_summarize Triggers

| Mode | Trigger Patterns | Example Queries |
|------|-----------------|-----------------|
| Quick | "what is", "overview", "about" | "What is this paper about?" |
| Targeted | "what X", "how X", specific question | "What methodology did they use?" |
| Comprehensive | "comprehensively", "detailed", "full summary" | "Summarize this comprehensively" |
| Full | force_mode OR "extract all", "complete text" | force_mode="full" |

### zot_explore_graph Triggers

| Mode | Trigger Patterns | Example Queries |
|------|-----------------|-----------------|
| Citation Chain | "citing papers", "citation" | "papers citing papers that cite X" |
| Influence | "influential", "seminal", "important" | "Find influential papers on X" |
| Content Similarity | "similar to", "like" | "Papers similar to X" |
| Related Papers | "related to" (graph) | "Papers related to X" |
| Collaboration | "collaborated", "co-author" | "Who collaborated with Anderson?" |
| Concept Network | "concepts", "themes" | "Concepts related to memory" |
| Temporal | "evolved", "YEAR to YEAR" | "Evolution from 2010 to 2020" |
| Venue Analysis | "top journals", "venues" | "Top journals in neuroscience" |
| Comprehensive | "explore everything" OR force_mode | force_mode="comprehensive" |

---

## Testing Checklist by Category

### Intent Detection (15 tests)
- [ ] 5 zot_search modes triggered correctly
- [ ] 4 zot_summarize modes triggered correctly
- [ ] 6 zot_explore_graph modes triggered correctly

### Parameter Extraction (5 tests)
- [ ] Author names extracted
- [ ] Years extracted (start/end)
- [ ] Concepts extracted
- [ ] Paper keys extracted
- [ ] Field/venue extracted

### Backend Integration (3 tests)
- [ ] Qdrant connectivity
- [ ] Neo4j connectivity
- [ ] Zotero API connectivity

### Quality Validation (10 tests)
- [ ] Results relevant to query
- [ ] No duplicates in merged results
- [ ] Execution time within bounds
- [ ] Token counts appropriate
- [ ] Summaries capture key info
- [ ] Graph queries return connections
- [ ] Intent accuracy > 90%
- [ ] Parameter extraction accurate
- [ ] Error handling graceful
- [ ] Escalation triggers properly

---

## Performance Targets

| Operation | Target Time | Backend(s) | Token Range |
|-----------|-------------|------------|-------------|
| Fast search | < 3s | Qdrant | N/A |
| Enriched search | < 5s | Qdrant + 1 | N/A |
| Comprehensive search | < 10s | All (seq) | N/A |
| Quick summary | < 2s | Metadata | 500-800 |
| Targeted summary | < 5s | Qdrant | 2k-5k |
| Comprehensive summary | < 12s | Qdrant | 8k-15k |
| Full summary | < 30s | PDF | 10k-100k |
| Graph exploration | 1-5s | Neo4j/Qdrant | N/A |

---

This hierarchy ensures:
1. ✅ Automatic intent detection (no manual mode selection)
2. ✅ Cost optimization (cheapest approach first)
3. ✅ Quality escalation (upgrade when needed)
4. ✅ Clear decision trees (transparent logic)
5. ✅ Comprehensive coverage (48 modes across 9 tools)
