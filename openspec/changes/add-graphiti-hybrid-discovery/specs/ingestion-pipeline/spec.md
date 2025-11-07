# Ingestion Pipeline (NEW Capability)

## ADDED Requirements

### Requirement: Multi-Backend Ingestion Orchestration
The system SHALL coordinate ingestion across three backends (Qdrant, Neo4j, Graphiti) with proper error isolation and parallelization.

#### Scenario: Synchronous core pipeline (Qdrant + Neo4j)
- **WHEN** a paper is added to the library
- **THEN** system SHALL ingest to Qdrant (vector embeddings) synchronously
- **AND** SHALL ingest to Neo4j (graph entities) synchronously
- **AND** these SHALL complete before marking paper as "indexed"

#### Scenario: Asynchronous Graphiti ingestion
- **WHEN** Graphiti is enabled and paper meets criteria
- **THEN** system SHALL trigger Graphiti ingestion asynchronously
- **AND** Graphiti errors SHALL NOT block Qdrant/Neo4j ingestion
- **AND** Graphiti ingestion MAY complete after core pipeline

#### Scenario: Feature flag disabled
- **WHEN** `config.graphiti.enabled: false`
- **THEN** Graphiti ingestion SHALL be skipped entirely
- **AND** no Graphiti API calls SHALL be made

---

### Requirement: Graphiti Client Integration
The system SHALL provide a `GraphitiClient` wrapper for MCP tool interactions.

#### Scenario: Add paper chunks as episodes
- **WHEN** `GraphitiClient.add_paper_chunk()` is called
- **THEN** it SHALL invoke `mcp__graphiti__add_memory`
- **AND** SHALL format chunks with paper metadata (title, authors, key)
- **AND** SHALL use group_id `agent-zot-discovery`

#### Scenario: Search extracted entities
- **WHEN** `GraphitiClient.search_entities()` is called
- **THEN** it SHALL invoke `mcp__graphiti__search_memory_nodes`
- **AND** SHALL return entities with paper key associations

#### Scenario: Search relationships
- **WHEN** `GraphitiClient.search_relationships()` is called
- **THEN** it SHALL invoke `mcp__graphiti__search_memory_facts`
- **AND** SHALL return relationship facts between entities

#### Scenario: Handle Graphiti unavailability
- **WHEN** Graphiti MCP server is offline
- **THEN** `GraphitiClient` methods SHALL raise clear exceptions
- **AND** calling code SHALL catch and log errors
- **AND** SHALL NOT crash the main ingestion pipeline

---

### Requirement: Chunk Batching for Cost Efficiency
Graphiti ingestion SHALL batch multiple chunks into single episodes to reduce LLM API calls.

#### Scenario: Batch 10-20 chunks per episode
- **WHEN** a paper has 50 chunks
- **THEN** system SHALL create 3-5 Graphiti episodes (batches of 10-20)
- **AND** each episode SHALL contain contiguous text for coherent extraction

#### Scenario: Single small paper
- **WHEN** a paper has <10 chunks
- **THEN** system SHALL create single Graphiti episode with all chunks
- **AND** SHALL NOT create empty episodes

#### Scenario: Cost tracking per batch
- **WHEN** an episode is created
- **THEN** system SHALL estimate LLM token usage
- **AND** SHALL log cost estimate (based on configured LLM pricing)

---

### Requirement: Selective Ingestion via Tags
The system SHALL only ingest papers to Graphiti if they meet configured criteria.

#### Scenario: Tag-based filter (Phase 1)
- **WHEN** paper has tag `_graphiti_experiment`
- **THEN** it SHALL be ingested to Graphiti
- **WHEN** paper does NOT have this tag
- **THEN** Graphiti ingestion SHALL be skipped

#### Scenario: Tag filter configurable
- **WHEN** user sets `config.graphiti.filter_tag: "highly-cited"`
- **THEN** only papers with "highly-cited" tag SHALL be ingested
- **AND** filter SHALL be case-insensitive

#### Scenario: No tag filter (Future)
- **WHEN** `config.graphiti.filter_tag: null`
- **THEN** all papers SHALL be ingested to Graphiti (no filter)
- **AND** cost warnings SHALL be displayed

---

### Requirement: Ingestion Metrics and Logging
The system SHALL track and log detailed metrics for Graphiti ingestion operations.

#### Scenario: Log ingestion start
- **WHEN** Graphiti ingestion begins for a paper
- **THEN** system SHALL log paper key, title, chunk count
- **AND** SHALL log estimated batch count

#### Scenario: Log ingestion success
- **WHEN** Graphiti ingestion completes successfully
- **THEN** system SHALL log elapsed time, entity count (estimated), cost estimate
- **AND** SHALL mark paper as "graphiti_indexed: true" in metadata

#### Scenario: Log ingestion failure
- **WHEN** Graphiti ingestion fails
- **THEN** system SHALL log error message, paper key, failure reason
- **AND** SHALL mark paper as "graphiti_indexed: false"
- **AND** SHALL NOT retry automatically (manual retry available)

#### Scenario: Aggregate metrics
- **WHEN** multiple papers are ingested
- **THEN** system SHALL track cumulative metrics:
  - Total papers processed
  - Total LLM tokens used
  - Total estimated cost
  - Average time per paper
- **AND** metrics SHALL be queryable via CLI

---

### Requirement: Error Isolation and Fault Tolerance
Graphiti ingestion failures SHALL NOT affect the core Qdrant/Neo4j pipeline.

#### Scenario: Graphiti LLM timeout
- **WHEN** Graphiti LLM extraction times out (>60s)
- **THEN** system SHALL log timeout error
- **AND** SHALL continue with next paper
- **AND** failed paper SHALL be marked for manual retry

#### Scenario: Graphiti MCP server crash
- **WHEN** Graphiti MCP server is unresponsive
- **THEN** system SHALL detect failure after 10-second timeout
- **AND** SHALL log error and disable Graphiti for current session
- **AND** Qdrant/Neo4j ingestion SHALL proceed normally

#### Scenario: Graphiti API rate limit
- **WHEN** OpenAI API returns rate limit error (429)
- **THEN** system SHALL implement exponential backoff (1s, 2s, 4s)
- **AND** SHALL retry up to 3 times
- **AND** SHALL fail gracefully if retries exhausted

---

### Requirement: Parallel Ingestion Without Blocking
Graphiti ingestion SHALL run in parallel with Neo4j to avoid slowing the main pipeline.

#### Scenario: Async fire-and-forget
- **WHEN** core pipeline (Qdrant + Neo4j) completes
- **THEN** Graphiti ingestion SHALL be triggered asynchronously
- **AND** main process SHALL NOT wait for Graphiti completion
- **AND** paper SHALL be marked "indexed" regardless of Graphiti status

#### Scenario: Background task management
- **WHEN** multiple papers are queued for ingestion
- **THEN** Graphiti tasks SHALL run in background thread pool
- **AND** SHALL respect concurrency limit (max 3 concurrent Graphiti calls)
- **AND** SHALL not overwhelm LLM API

---

### Requirement: LLM Provider Configuration
The system SHALL support configurable LLM providers for Graphiti entity extraction.

#### Scenario: Default to GPT-4o-mini
- **WHEN** `config.graphiti.llm_provider: "openai"`
- **THEN** system SHALL use GPT-4o-mini model
- **AND** SHALL use API key from `OPENAI_API_KEY` environment variable

#### Scenario: Alternative provider (Future)
- **WHEN** `config.graphiti.llm_provider: "anthropic"`
- **THEN** system SHALL use Claude Haiku model
- **AND** SHALL use API key from `ANTHROPIC_API_KEY` environment variable

#### Scenario: Local Ollama (Future)
- **WHEN** `config.graphiti.llm_provider: "ollama"`
- **THEN** system SHALL use local Ollama instance
- **AND** SHALL use configured model (e.g., "mistral:7b")
- **AND** cost tracking SHALL be disabled (free)

---

### Requirement: Incremental Ingestion Support
The system SHALL support incremental updates without re-processing all papers.

#### Scenario: Skip already-ingested papers
- **WHEN** a paper has `graphiti_indexed: true` in metadata
- **THEN** Graphiti ingestion SHALL be skipped
- **WHEN** user forces re-ingestion (`--force-graphiti`)
- **THEN** paper SHALL be re-ingested regardless of status

#### Scenario: New papers only
- **WHEN** user runs `agent-zot update-db`
- **THEN** only papers modified since last run SHALL be ingested to Graphiti
- **AND** existing Graphiti data SHALL remain unchanged

---

### Requirement: Manual Ingestion Control
Users SHALL have CLI commands to control Graphiti ingestion explicitly.

#### Scenario: Ingest specific paper
- **WHEN** user runs `agent-zot graphiti ingest --paper-key ABC123`
- **THEN** that paper SHALL be ingested to Graphiti
- **AND** feature flag SHALL be ignored (force ingestion)

#### Scenario: Ingest by tag
- **WHEN** user runs `agent-zot graphiti ingest --tag _graphiti_experiment`
- **THEN** all papers with that tag SHALL be ingested
- **AND** cost estimate SHALL be shown before starting

#### Scenario: Ingest entire library (Future)
- **WHEN** user runs `agent-zot graphiti ingest --all`
- **THEN** system SHALL warn about cost (7,390 papers × $0.01 = $73)
- **AND** SHALL require confirmation before proceeding
