# Project Context

## Purpose

**Agent-Zot** is a production-grade MCP (Model Context Protocol) server that transforms Zotero research libraries into intelligent, searchable knowledge bases. It provides semantic search, knowledge graph exploration, and intelligent document understanding for academic research workflows.

**Core Mission**: Supercharge research productivity by enabling natural language queries over academic papers, automatic extraction of entities and relationships, and discovery of hidden connections between research.

**Key Capabilities**:
- Semantic search using state-of-the-art multilingual embeddings (BGE-M3)
- Knowledge graph construction from academic papers (Neo4j GraphRAG)
- Intelligent query routing with automatic intent detection
- Hybrid retrieval combining vector search (Qdrant) and graph traversal (Neo4j)
- Natural language interface via unified intelligent tools

**Target Users**: Researchers, academics, PhD students, and knowledge workers managing large research libraries (hundreds to thousands of papers)

## Tech Stack

### Core Technologies
- **Language**: Python 3.12+
- **MCP Framework**: FastMCP (Model Context Protocol server)
- **Package Management**: pip + virtualenv (`.venv/`)
- **Deployment**: CLI tool + MCP server (stdio/SSE transport)

### Data Storage
- **Vector Database**: Qdrant (HNSW indexing, cosine similarity)
- **Graph Database**: Neo4j 5.26+ (Cypher queries, GDS algorithms)
- **Primary Data Source**: Zotero SQLite database (read-only access)

### ML/AI Stack
- **Embeddings**: BGE-M3 (1024D, multilingual, via SentenceTransformers)
- **Chunking**: RecursiveCharacterTextSplitter (LangChain)
- **Re-ranking**: Cross-encoder (optional, +10-20% accuracy)
- **Entity Extraction**: Neo4j GraphRAG with Ollama (Mistral 7B Instruct) or GPT-4o-mini
- **Quantization**: INT8 for memory efficiency (75% RAM savings)

### PDF Processing
- **Parser**: PyMuPDF (fast, CPU-only)
- **Advanced Backend**: Docling V2 (structure preservation, optional)
- **Parallelization**: Subprocess isolation with 8 workers
- **Performance**: ~18 seconds per PDF, ~476 PDFs/hour

### Infrastructure
- **Containerization**: Docker Compose (Qdrant + Neo4j services)
- **Logging**: Python `logging` module with structured output
- **Config**: JSON-based (`~/.config/agent-zot/config.json`)
- **Caching**: SQLite for parsed document cache (`~/.cache/agent-zot/parsed_docs.db`)

### Testing
- **Framework**: pytest
- **Structure**: `tests/unit/`, `tests/integration/`
- **Coverage**: Smoke tests + integration tests for critical paths

## Project Conventions

### Code Style

**Python Standards**:
- PEP 8 compliant (with Black/Ruff for auto-formatting when used)
- Type hints on all public functions
- Docstrings: Google-style format
- Max line length: 100 characters (flexible for readability)

**Naming Conventions**:
- Modules: `snake_case.py` (e.g., `unified_smart.py`)
- Classes: `PascalCase` (e.g., `SearchClient`, `Neo4jGraphRAG`)
- Functions/methods: `snake_case` (e.g., `zot_search()`, `run_sequential_backends()`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `RESEARCH_PAPER_SCHEMA`)
- Private methods: `_leading_underscore` (e.g., `_validate_config()`)

**Import Organization**:
```python
# Standard library
import os
import logging
from typing import Dict, List, Optional

# Third-party
from qdrant_client import QdrantClient
from neo4j import GraphDatabase

# Local
from agent_zot.clients.qdrant_search import QdrantSearchClient
from agent_zot.utils.logging import setup_logger
```

**Error Handling**:
- Explicit exception handling with logging
- Graceful degradation (e.g., skip problematic PDFs, continue indexing)
- User-friendly error messages in MCP tool responses

### Architecture Patterns

**Unified Intelligent Tools Pattern** (ADR-001):
- Single entry point per workflow (e.g., `zot_search` replaces 7 legacy tools)
- Pattern-based intent detection (regex + keyword matching)
- Automatic backend selection based on query characteristics
- Natural language interface over manual mode selection

**Sequential Backend Execution** (ADR-002):
- 1-2 backends: Parallel execution (fast, safe)
- 3 backends (Comprehensive Mode): Sequential execution (prevents memory exhaustion)
- Trade-off: +2-4 seconds latency for system stability

**Client-Server Separation**:
- `src/agent_zot/clients/`: Database clients (Qdrant, Neo4j, Zotero API)
- `src/agent_zot/core/`: MCP server implementation and tool handlers
- `src/agent_zot/search/`: Search strategies and unified tool orchestration
- `src/agent_zot/parsers/`: PDF extraction and chunking
- `src/agent_zot/utils/`: Shared utilities (logging, config, helpers)

**Subprocess Isolation**:
- PDF parsing runs in isolated subprocesses
- Prevents corrupted PDFs from crashing main process
- Timeout handling (30-60 seconds per PDF)

**Config-Driven Design**:
- All tunable parameters in `config.json`
- Sensible defaults with full customizability
- Runtime config validation

### Testing Strategy

**Test Structure**:
- `tests/unit/`: Fast, isolated unit tests (mocking external dependencies)
- `tests/integration/`: Integration tests with real Qdrant/Neo4j/Zotero
- `tests/conftest.py`: Shared fixtures

**Testing Priorities**:
1. **Critical Path Coverage**: MCP tool handlers, search orchestration, database operations
2. **Smoke Tests**: Basic functionality verification (server startup, config loading)
3. **Integration Tests**: End-to-end workflows (ingest → search → retrieve)

**Testing Philosophy**:
- Test public interfaces, not implementation details
- Integration tests for data pipeline correctness
- Unit tests for algorithmic correctness (e.g., intent detection patterns)

**Manual Testing**:
- Real-world usage with Claude Desktop (MCP integration)
- Performance benchmarking on large libraries (1,000+ papers)
- Qualitative assessment of search relevance

### Git Workflow

**Branching Strategy**:
- `main`: Production-ready code (always deployable)
- Feature branches: `feature/graphiti-integration`, `fix/neo4j-timeout`
- Hotfixes: `hotfix/critical-bug`

**Commit Conventions**:
- Format: `<type>: <description>` (Conventional Commits style)
- Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`
- Examples:
  - `feat: Add Graphiti autonomous extraction integration`
  - `fix: Handle Neo4j connection timeout gracefully`
  - `docs: Update ADR-017 with Graphiti integration decision`
  - `refactor: Simplify intent detection in zot_search`

**Commit Footer** (auto-generated):
```
🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Pull Request Workflow**:
- PRs for all significant changes (feature branches → main)
- Description includes: Summary, Test Plan, Breaking Changes (if any)
- Auto-generated via `gh pr create` with template

**Documentation Synchronization**:
- Update `CLAUDE.md` when system state changes significantly
- Add architectural decisions to `decisions.md` (ADR format)
- Log bugs/limitations in `bugs.md`
- Track milestones in `progress.md`

## Domain Context

**Academic Research Workflows**:
- Zotero is the canonical source of truth (SQLite database at `~/Zotero/` or custom path)
- Papers stored as PDFs with metadata (title, authors, year, journal, abstract, DOI)
- Collections organize papers by topic/project
- Tags provide flexible categorization
- Notes and annotations capture insights

**Knowledge Graph Schema**:
- **Entity Types** (8): Paper, Person (Author), Institution, Journal, Concept, Method, Dataset, Software
- **Relationship Types** (12): CITES, CITED_BY, WROTE, AFFILIATED_WITH, PUBLISHED_IN, DISCUSSES, USES, CONTRIBUTES_TO, VALIDATED_BY, COMPARES_TO, EXTENDS, CONTRADICTS
- **Temporal Model**: Bi-temporal tracking (event time vs ingestion time) coming via Graphiti integration

**Search Intent Categories**:
1. **Semantic**: Content-based queries ("papers about attention mechanisms")
2. **Entity Discovery**: Entity extraction queries ("which methods appear in papers about X?")
3. **Relationship**: Graph-based queries ("who collaborated with [author]?")
4. **Metadata**: Author/year/journal queries ("papers by Smith published in 2023")
5. **Multi-Concept**: Complex queries with AND/OR logic ("transformers AND neuroscience")

**Performance Expectations**:
- Search: Fast (~2s), Enriched (~4s), Comprehensive (~6-8s)
- PDF Ingestion: ~18 seconds per PDF, ~476 PDFs/hour (8 workers)
- Graph Population: ~10-12 hours for 2,411 papers (concurrent extraction)

## Important Constraints

**Technical Constraints**:
- **Read-Only Zotero Access**: Never modify Zotero database directly (read-only operations only)
- **Memory Limitations**: MacBook Pro with limited RAM → Sequential execution for 3+ backends
- **No GPU Required**: All ML operations run on CPU (BGE-M3 INT8 quantization)
- **Offline-First**: Core functionality works without internet (except Zotero API enrichment)

**Data Constraints**:
- **Zotero SQLite Locking**: 10-second timeout with WAL mode for concurrent access
- **PDF Quality**: Gracefully handle corrupted/scanned PDFs (skip problematic documents)
- **Incremental Updates**: Must support restart-safe indexing (deduplication via paper keys)

**Operational Constraints**:
- **No Auto-Update on Startup** (ADR-003): Explicit user control over database updates
- **Orphaned Process Cleanup**: Automatic cleanup of stale `agent-zot serve` processes on startup
- **Concurrent Sessions**: Support multiple Claude Code instances safely

**Performance Constraints**:
- **Startup Time**: <100ms for MCP server initialization (no auto-update)
- **Search Latency**: <10 seconds for worst-case Comprehensive Mode queries
- **Indexing Speed**: Must scale to 10,000+ papers without degradation

**Compatibility Constraints**:
- **Python 3.12+**: Modern type hints and async/await patterns
- **Neo4j 5.26+**: Requires specific GraphRAG library version
- **Qdrant**: Local Docker instance (no cloud dependency)

## External Dependencies

**Core Services**:
- **Zotero**: Primary data source (SQLite database + optional Zotero API for metadata enrichment)
- **Qdrant**: Vector database (local Docker container, port 6333)
- **Neo4j**: Graph database (local Docker container, port 7687 bolt, 7474 browser)
- **Ollama** (optional): Local LLM for entity extraction (Mistral 7B Instruct)

**Python Libraries** (key dependencies):
- `mcp` (fastmcp): MCP server framework
- `qdrant-client`: Qdrant vector database client
- `neo4j`: Neo4j graph database driver
- `neo4j-graphrag`: Neo4j GraphRAG library (entity extraction, knowledge graph construction)
- `sentence-transformers`: BGE-M3 embeddings
- `pymupdf`: PDF parsing
- `langchain-text-splitters`: Recursive chunking
- `pyzotero`: Zotero API client (metadata enrichment)

**Optional Services**:
- **OpenAI API**: Alternative to Ollama for entity extraction (GPT-4o-mini)
- **Docling V2**: Advanced PDF parsing backend (structure preservation)

**Infrastructure**:
- **Docker Desktop**: Required for Qdrant and Neo4j containers
- **macOS/Linux**: Primary development/deployment platforms (Windows untested)

**MCP Integration**:
- **Claude Desktop**: Primary consumer of MCP server
- **stdio transport**: Default communication protocol
- **SSE transport**: Alternative for web-based clients (experimental)

**Configuration Files**:
- `~/.config/agent-zot/config.json`: User configuration
- `~/.cache/agent-zot/parsed_docs.db`: Document parsing cache (SQLite)
- `docker-compose.yml`: Qdrant + Neo4j service definitions

**Environment Variables**:
- `ZOTERO_DATABASE_PATH`: Custom Zotero SQLite path (optional)
- `OPENAI_API_KEY`: OpenAI API key for GPT-based extraction (optional)
- `NEO4J_PASSWORD`: Neo4j database password (default: `demodemo`)

## Development Workflow

**Setup**:
```bash
cd /Users/claudiusv.schroder/toolboxes/agent-zot
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

**Docker Services**:
```bash
docker-compose up -d  # Start Qdrant + Neo4j
docker-compose down   # Stop services
```

**Database Operations**:
```bash
agent-zot update-db --force-rebuild --fulltext  # Full rebuild
agent-zot update-db                              # Incremental update
agent-zot get-search-database-status            # Check status
```

**Running MCP Server**:
```bash
agent-zot serve  # stdio transport (default)
```

**Common Tasks**:
```bash
# Backup databases
agent-zot backup-all

# List backups
python scripts/backup.py list

# Test with 10 papers
agent-zot update-db --limit 10

# Check daemon status
agent-zot daemon status
```

**Documentation Updates**:
- `CLAUDE.md`: System state, current capabilities, operational info
- `decisions.md`: New architectural decisions (ADR format)
- `bugs.md`: Bug reports and known limitations
- `progress.md`: Implementation milestones
- `README.md`: User-facing documentation

## Integration with PAI System

**Context Management**:
- Agent-zot is a specialized tool within the broader PAI (Personal AI Infrastructure) ecosystem
- Uses PAI conventions for Skills, hooks, and context management
- OpenSpec integration for proposal-driven development

**Graphiti Integration** (Proposed):
- Hybrid architecture: Neo4j (structured) + Graphiti (autonomous discovery)
- Graphiti ingests Qdrant chunks for emergent entity/relationship extraction
- Cross-validation between explicit Neo4j schema and Graphiti autonomous extraction
- Separate group_ids: `agent-zot-papers` (Neo4j) vs `agent-zot-discovery` (Graphiti)

**Memory Integration**:
- Research annotations stored in Graphiti PAI memory (`pai-research-annotations`)
- Personal insights linked to papers via Zotero keys
- Temporal tracking of evolving understanding

## Project Health

**Current Status** (November 7, 2025):
- Version: 2.2 (Incremental Auto-Sync)
- Health Score: A+ (99/100)
- Stability: Production-Ready
- Active Development: Graphiti integration exploration

**Key Metrics**:
- Papers Indexed: 7,390 (Zotero library)
- Vector Chunks: 234,153 (Qdrant)
- Graph Nodes: 25,184 (Neo4j)
- Graph Relationships: 134,068 (Neo4j, 91% populated)
- Tools: 8 unified intelligent tools (40 total including deprecated)

**Roadmap**:
1. **Immediate**: OpenSpec setup for Graphiti integration prototype
2. **Next**: Phase 1 Graphiti experiment (10-20 papers)
3. **Future**: Autonomous entity extraction, cross-validation, hybrid retrieval
