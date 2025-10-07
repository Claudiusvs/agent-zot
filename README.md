# Agent-Zot: Custom Zotero MCP Server

This is a customized version of the [Zotero MCP Server](https://github.com/54yyyu/zotero-mcp) modified to use:
- **Qdrant** instead of ChromaDB for vector storage
- **Docling** for enhanced document parsing and chunking

## Original Project

Based on [zotero-mcp](https://github.com/54yyyu/zotero-mcp) by @54yyyu

## Key Improvements

### ✅ Qdrant Vector Database
- Production-ready vector database
- Better performance and scalability
- More efficient storage
- Advanced filtering capabilities
- Runs in Docker for easy management

### ✅ Docling Document Parsing
- Advanced PDF parsing with structure preservation
- Table and figure extraction
- Hierarchical chunking with overlap
- Better handling of equations and special characters
- Smart semantic boundary detection

### Completed Changes
- [x] Replace ChromaDB client with Qdrant client
- [x] Integrate Docling for document parsing
- [x] Update embedding pipeline
- [x] Create migration guide

## Quick Start

### Prerequisites
- Docker installed and running
- Python 3.12 virtual environment
- Zotero with local API enabled

### Installation

1. **Qdrant is already running** via Docker at `localhost:6333`
2. **Dependencies installed** in `~/toolboxes/zotero-mcp-env/`
3. **Update your config:**

```bash
cp config_examples/config_qdrant.json ~/.config/zotero-mcp/config.json
# Edit with your API keys
```

4. **Re-index your library** (recommended for best results):

```bash
source ~/toolboxes/zotero-mcp-env/bin/activate
zotero-mcp update-database --force-rebuild --extract-fulltext
```

See [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) for detailed instructions.

## Architecture

### Components
- **qdrant_client_wrapper.py** - Qdrant database integration
- **docling_parser.py** - Advanced document parsing with Docling
- **semantic_search.py** - Updated search implementation
- **server.py** - MCP server (unchanged, compatible interface)

### Data Flow
1. Zotero items fetched via API or local database
2. PDFs parsed with Docling → structured chunks
3. Chunks embedded via OpenAI API
4. Stored in Qdrant with metadata
5. Semantic search via vector similarity

## Configuration

### Old ChromaDB Setup
**Size:** 1.7GB
**Location:** `~/.config/zotero-mcp/chroma_db/`
**Status:** Can be removed after successful migration

### New Qdrant Setup
**Location:** `~/agent-zot/qdrant_storage/`
**Container:** `agent-zot-qdrant`
**Managed by:** Docker

## Development

### Testing Locally

```bash
# Check Qdrant status
curl http://localhost:6333/collections

# View Docker logs
docker logs agent-zot-qdrant

# Test search
# Ask Claude via MCP: "Search my library for papers about X"
```

### Committing Changes

```bash
cd ~/agent-zot
git add .
git commit -m "feat: migrate to Qdrant + Docling"
git push origin main
```

## License

Same as original project (check upstream repo)
