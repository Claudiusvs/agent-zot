# Claude Desktop MCP Configuration

## Configuration Location
`~/Library/Application Support/Claude/claude_desktop_config.json`

## Zotero MCP Server Entry

```json
"zotero": {
  "command": "/Users/claudiusv.schroder/toolboxes/zotero-mcp-env/bin/zotero-mcp",
  "env": {
    "ZOTERO_LOCAL": "true",
    "ZOTERO_API_KEY": "<YOUR_API_KEY>",
    "ZOTERO_LIBRARY_ID": "<YOUR_LIBRARY_ID>",
    "ZOTERO_LIBRARY_TYPE": "user",
    "OPENAI_API_KEY": "<YOUR_OPENAI_API_KEY>"
  }
}
```

## Current Setup Details

- **Virtual Environment:** `~/toolboxes/zotero-mcp-env/`
- **Python Version:** 3.12
- **Executable:** `~/toolboxes/zotero-mcp-env/bin/zotero-mcp`
- **Config Directory:** `~/.config/zotero-mcp/`
- **ChromaDB Path:** `~/.config/zotero-mcp/chroma_db/`

## Embedding Configuration

- **Provider:** OpenAI
- **Model:** text-embedding-3-large
- **Collection Name:** zotero_library_openai
- **Update Mode:** Manual (auto_update: false)

## Installation Path

Source code installed at:
```
~/toolboxes/zotero-mcp-env/lib/python3.12/site-packages/zotero_mcp/
```

## Key Files

- `chroma_client.py` - ChromaDB integration (to be replaced with Qdrant)
- `semantic_search.py` - Semantic search implementation
- `server.py` - MCP server implementation
- `local_db.py` - Local database handling
- `client.py` - Zotero API client

## Next Steps for Migration

When migrating to Qdrant + Docling:
1. Update virtual environment path in Claude Desktop config
2. Keep same environment variables structure
3. Update config.json to point to Qdrant instance
4. Re-index documents using Docling
