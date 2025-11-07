# Unified Tools (MODIFIED Capability)

## ADDED Requirements

### Requirement: Discovery Query Tool (`zot_discover`)
The system SHALL provide a unified `zot_discover` tool for exploratory queries using Graphiti's autonomous extraction.

#### Scenario: Discover emergent entities
- **WHEN** user queries "What unexpected concepts appear in papers about transformers?"
- **THEN** `zot_discover` SHALL query Graphiti for autonomous entity extractions
- **AND** SHALL return entities not in predefined Neo4j schema
- **AND** SHALL include provenance (which papers mentioned each entity)

#### Scenario: Find cross-disciplinary connections
- **WHEN** user queries "Find connections between neuroscience and NLP papers"
- **THEN** `zot_discover` SHALL identify entities appearing in both domains
- **AND** SHALL return relationship facts linking the domains
- **AND** SHALL highlight novel connections (not in Neo4j)

#### Scenario: Temporal discovery queries (Future)
- **WHEN** user queries "How has my understanding of attention evolved from 2023 to 2025?"
- **THEN** `zot_discover` SHALL use Graphiti's temporal model
- **AND** SHALL return entities discovered at different time points
- **AND** SHALL show how relationships changed over time

#### Scenario: Natural language query support
- **WHEN** user provides vague query like "interesting patterns in machine learning papers"
- **THEN** `zot_discover` SHALL leverage Graphiti's semantic search
- **AND** SHALL return relevant entities and relationships
- **AND** SHALL NOT require precise query syntax

#### Scenario: Result provenance
- **WHEN** `zot_discover` returns results
- **THEN** each result SHALL include:
  - Entity or relationship description
  - Source paper keys (Zotero)
  - Confidence score (if available from Graphiti)
  - `source: "graphiti"` metadata tag

---

### Requirement: Tool Availability Based on Feature Flag
The `zot_discover` tool SHALL only be registered when Graphiti is enabled.

#### Scenario: Graphiti enabled
- **WHEN** `config.graphiti.enabled: true`
- **THEN** `zot_discover` SHALL appear in MCP tool list
- **AND** SHALL be callable by Claude or other MCP clients

#### Scenario: Graphiti disabled
- **WHEN** `config.graphiti.enabled: false`
- **THEN** `zot_discover` SHALL NOT appear in MCP tool list
- **AND** attempts to call it SHALL return clear error message

---

### Requirement: Query Performance Constraints
Discovery queries SHALL complete within acceptable latency bounds.

#### Scenario: Simple entity query
- **WHEN** user queries for entities about a single concept
- **THEN** query SHALL complete in <3 seconds
- **AND** SHALL return up to 10 results by default

#### Scenario: Complex relationship query
- **WHEN** user queries for multi-hop relationships
- **THEN** query SHALL complete in <5 seconds
- **AND** SHALL use Graphiti's graph traversal capabilities

#### Scenario: Timeout handling
- **WHEN** Graphiti query exceeds 10 seconds
- **THEN** system SHALL timeout and return partial results
- **AND** SHALL log timeout warning

---

### Requirement: Integration with Existing Tools
The `zot_discover` tool SHALL complement (not replace) existing unified tools.

#### Scenario: Complementary to `zot_explore_graph`
- **WHEN** user needs structured citation network queries
- **THEN** they SHALL use `zot_explore_graph` (Neo4j backend)
- **WHEN** user needs exploratory discovery
- **THEN** they SHALL use `zot_discover` (Graphiti backend)

#### Scenario: Complementary to `zot_search`
- **WHEN** user searches for papers by content
- **THEN** they SHALL use `zot_search` (Qdrant semantic search)
- **WHEN** user searches for entities across papers
- **THEN** they SHALL use `zot_discover` (Graphiti entity search)

#### Scenario: Tool recommendation in responses
- **WHEN** agent detects exploratory intent in user query
- **THEN** it SHOULD suggest trying `zot_discover`
- **EXAMPLE**: "To find unexpected connections, try using `zot_discover` for autonomous entity discovery"

---

### Requirement: Cross-Validation Query Support (Future)
The system SHALL support queries that combine Neo4j and Graphiti results for cross-validation.

#### Scenario: Compare extractions for a paper
- **WHEN** user queries "Compare entity extractions for paper ABC123"
- **THEN** system SHALL query both Neo4j and Graphiti
- **AND** SHALL return:
  - Entities found by both (cross-validated)
  - Entities found only by Neo4j (structured)
  - Entities found only by Graphiti (discovered)

#### Scenario: Validate novel discoveries
- **WHEN** Graphiti finds a new entity type
- **THEN** user SHALL be able to check if Neo4j missed it
- **AND** system SHALL suggest adding to Neo4j schema if valuable

---

## MODIFIED Requirements

None. All changes are additions (`ADDED Requirements` above).

---

## REMOVED Requirements

None.
