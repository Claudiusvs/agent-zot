# Claude Desktop MCP Configuration

## Configuration Location
`~/Library/Application Support/Claude/claude_desktop_config.json`

## Agent-Zot MCP Server Entry

```json
"agent-zot": {
  "command": "/Users/claudiusv.schroder/toolboxes/agent-zot-env/bin/agent-zot",
  "args": ["serve"],
  "env": {
    "ZOTERO_LOCAL": "true"
  }
}
```

## Current Setup Details

- **Virtual Environment:** `~/toolboxes/agent-zot-env/`
- **Python Version:** 3.12
- **Executable:** `~/toolboxes/agent-zot-env/bin/agent-zot`
- **Config File:** `~/.config/agent-zot/config.json`
- **Vector Database:** Qdrant (http://localhost:6333)
- **Vector Storage:** `~/toolboxes/agent-zot/qdrant_storage/`

## Configuration Details

Agent-Zot loads configuration from `~/.config/agent-zot/config.json`:

```json
{
  "client_env": {
    "ZOTERO_LOCAL": "true"
  },
  "semantic_search": {
    "embedding_model": "sentence-transformers",
    "sentence_transformer_model": "BAAI/bge-m3",
    "collection_name": "zotero_library_qdrant",
    "qdrant_url": "http://localhost:6333",
    "qdrant_api_key": null,
    "enable_hybrid_search": true,
    "enable_reranking": true
  }
}
```

## Embedding Configuration

- **Provider:** sentence-transformers (local)
- **Model:** BAAI/bge-m3
- **Dimension:** 1024D
- **Collection Name:** zotero_library_qdrant
- **Hybrid Search:** Enabled (dense + BM25 sparse)
- **Reranking:** Enabled (cross-encoder)
- **Update Mode:** Manual (auto_update: false)

## Installation Path

Source code installed at:
```
~/toolboxes/agent-zot/src/agent_zot/
```

## Key Files

- `core/server.py` - MCP server implementation
- `core/cli.py` - CLI entry point
- `search/semantic.py` - Semantic search orchestration
- `database/local_zotero.py` - Local database handling (MAIN ACTIVE PATH for fulltext)
- `clients/qdrant.py` - Qdrant vector database client
- `clients/zotero.py` - Zotero API client
- `parsers/docling.py` - Docling PDF parser with subprocess isolation

## Quick Start

1. **Start Qdrant**:
   ```bash
   docker run -d -p 6333:6333 -p 6334:6334 \
     -v ~/toolboxes/agent-zot/qdrant_storage:/qdrant/storage:z \
     --name agent-zot-qdrant \
     qdrant/qdrant
   ```

2. **Index your library**:
   ```bash
   source ~/toolboxes/agent-zot-env/bin/activate
   agent-zot update-db --fulltext
   ```

3. **Restart Claude Desktop** to load the MCP server

## Testing

Test the MCP server from command line:
```bash
source ~/toolboxes/agent-zot-env/bin/activate
agent-zot serve
```

Ask Claude in Claude Desktop:
- "Search my Zotero library for papers about transformers"
- "What papers discuss memory and PTSD?"
- "Show me recent work on climate change"

## Troubleshooting

**Server not showing up in Claude Desktop:**
- Check config file syntax: `cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | python3 -m json.tool`
- Check executable path exists: `ls -la ~/toolboxes/agent-zot-env/bin/agent-zot`
- Restart Claude Desktop completely

**Qdrant connection errors:**
- Check Qdrant is running: `docker ps | grep qdrant`
- Check logs: `docker logs agent-zot-qdrant`
- Restart Qdrant: `docker restart agent-zot-qdrant`

**No search results:**
- Check database is indexed: `agent-zot db-status`
- Check collection exists: `curl http://localhost:6333/collections/zotero_library_qdrant`

## For More Information

See the main documentation:
- **[README.md](../../README.md)** - Quick start guide
- **[CONFIGURATION.md](./configuration.md)** - Full configuration reference
- **[CLAUDE.md](../CLAUDE.md)** - Technical documentation and active pipeline details
