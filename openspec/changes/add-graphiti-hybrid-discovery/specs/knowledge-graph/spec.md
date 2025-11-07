# Knowledge Graph (NEW Capability)

## ADDED Requirements

### Requirement: Dual-Backend Graph Architecture
The system SHALL support both explicit schema-driven (Neo4j) and autonomous discovery-based (Graphiti) knowledge graph backends operating in parallel on the same research library.

#### Scenario: Neo4j provides structured queries
- **WHEN** user queries for "papers citing Smith (2023)"
- **THEN** system uses Neo4j backend with explicit `:CITES` relationships
- **AND** returns results from structured graph traversal

#### Scenario: Graphiti provides autonomous discovery
- **WHEN** user queries for "emergent concepts across neuroscience and NLP papers"
- **THEN** system uses Graphiti backend with autonomous entity extraction
- **AND** returns entities discovered without predefined schema

#### Scenario: Both backends linked via Zotero keys
- **WHEN** an entity is extracted by either backend
- **THEN** it SHALL be tagged with source paper Zotero key (e.g., "ABC123")
- **AND** cross-references SHALL be possible via shared paper keys

---

### Requirement: Feature Flag Controlled Activation
The Graphiti autonomous discovery backend SHALL be disabled by default and require explicit opt-in via configuration.

#### Scenario: Graphiti disabled by default
- **WHEN** agent-zot is freshly installed
- **THEN** `config.graphiti.enabled` SHALL be `false`
- **AND** only Neo4j knowledge graph SHALL be active

#### Scenario: User enables Graphiti
- **WHEN** user sets `config.graphiti.enabled: true`
- **THEN** subsequent paper ingestions SHALL trigger both Neo4j and Graphiti extraction
- **AND** `zot_discover` tool SHALL become available

#### Scenario: User disables Graphiti
- **WHEN** user sets `config.graphiti.enabled: false`
- **THEN** Graphiti ingestion SHALL stop
- **AND** existing Graphiti data SHALL remain queryable but not updated

---

### Requirement: Autonomous Entity Extraction
Graphiti SHALL autonomously extract entities and relationships from academic papers without requiring predefined schemas.

#### Scenario: Extract entities without schema constraints
- **WHEN** a paper chunk is ingested into Graphiti
- **THEN** Graphiti SHALL use NER, coreference resolution, and LLM extraction
- **AND** SHALL create entity nodes for discovered concepts, methods, authors
- **AND** SHALL NOT be limited to predefined entity types

#### Scenario: Discover emergent relationships
- **WHEN** multiple papers discuss related concepts with different terminology
- **THEN** Graphiti SHALL identify semantic relationships
- **AND** SHALL create relationship edges between entities
- **AND** relationships MAY be novel (not in Neo4j schema)

#### Scenario: Handle academic jargon
- **WHEN** paper contains domain-specific terminology (e.g., "LSTM", "fMRI", "p-hacking")
- **THEN** Graphiti extraction SHALL correctly identify these as technical entities
- **AND** precision SHALL be ≥80% on academic content

---

### Requirement: Cross-Validation Between Backends
The system SHALL provide tooling to compare entity extractions between Neo4j (explicit) and Graphiti (autonomous) backends.

#### Scenario: Identify Neo4j-only entities
- **WHEN** cross-validation runs for a paper
- **THEN** system SHALL list entities found by Neo4j but not Graphiti
- **AND** SHALL categorize these as "Confirmed Structured Entities"

#### Scenario: Identify Graphiti-only entities
- **WHEN** cross-validation runs for a paper
- **THEN** system SHALL list entities found by Graphiti but not Neo4j
- **AND** SHALL categorize these as "Novel Discoveries"
- **AND** SHALL flag for potential schema extension

#### Scenario: Identify overlapping entities
- **WHEN** both backends extract similar entities (e.g., "Transformer" vs "Transformer Architecture")
- **THEN** system SHALL use fuzzy matching to identify duplicates
- **AND** SHALL report as "Cross-Validated Entities"

---

### Requirement: Selective Ingestion Control
Users SHALL control which papers are ingested into Graphiti to manage costs and scope.

#### Scenario: Tag-based selective ingestion (Phase 1)
- **WHEN** a paper has tag `_graphiti_experiment`
- **THEN** it SHALL be ingested into both Neo4j and Graphiti
- **WHEN** a paper does NOT have this tag
- **THEN** it SHALL be ingested only into Neo4j (existing behavior)

#### Scenario: Collection-based selective ingestion (Future)
- **WHEN** user marks a collection for Graphiti ingestion
- **THEN** all papers in that collection SHALL be processed by Graphiti
- **AND** cost estimates SHALL be shown before processing

#### Scenario: Cost tracking
- **WHEN** Graphiti ingestion processes papers
- **THEN** system SHALL track LLM API token usage
- **AND** SHALL estimate costs per paper
- **AND** SHALL alert if costs exceed configured threshold

---

### Requirement: Temporal Context Tracking
Graphiti SHALL leverage bi-temporal tracking to record when facts were created and when they were invalidated.

#### Scenario: Track entity creation time
- **WHEN** an entity is extracted from a paper
- **THEN** Graphiti SHALL record the extraction timestamp
- **AND** SHALL distinguish between paper publication date and entity discovery date

#### Scenario: Track evolving understanding (Future)
- **WHEN** a user re-ingests or annotates a paper
- **THEN** new entities SHALL have later timestamps
- **AND** system SHALL support queries like "what did I know about X in 2023 vs 2025"

---

### Requirement: Query Provenance Tracking
All search results SHALL indicate which backend (Neo4j, Graphiti, or both) provided the data.

#### Scenario: Neo4j results tagged
- **WHEN** `zot_explore_graph` returns results
- **THEN** each result SHALL have `source: "neo4j"` metadata

#### Scenario: Graphiti results tagged
- **WHEN** `zot_discover` returns results
- **THEN** each result SHALL have `source: "graphiti"` metadata

#### Scenario: Merged results (Future)
- **WHEN** a query uses both backends
- **THEN** results SHALL show provenance for each item
- **AND** duplicates SHALL be marked as cross-validated
