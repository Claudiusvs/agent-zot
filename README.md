# Agent-Zot: Custom Zotero MCP Server

This is a customized version of the [Zotero MCP Server](https://github.com/54yyyu/zotero-mcp) modified to use:
- **Qdrant** instead of ChromaDB for vector storage
- **Docling** for enhanced document parsing and chunking

## Original Project

Based on [zotero-mcp](https://github.com/54yyyu/zotero-mcp) by @54yyyu

## Modifications

### Current State (Backup)
This repository contains the original ChromaDB-based implementation as a backup before migration.

### Planned Changes
- [ ] Replace ChromaDB client with Qdrant client
- [ ] Integrate Docling for document parsing
- [ ] Update embedding pipeline
- [ ] Migrate existing vector data

## Installation

Original installation path: `~/toolboxes/zotero-mcp-env/`

### Configuration

Configuration file: `config_backup/config.json` (sanitized copy)

Claude Desktop MCP config location:
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

### ChromaDB Data

**Size:** 1.7GB
**Location:** `~/.config/zotero-mcp/chroma_db/`
**Note:** Not included in git due to size. Backed up locally.

## Backup Instructions

To back up ChromaDB data separately:
```bash
tar -czf chroma_backup_$(date +%Y%m%d).tar.gz ~/.config/zotero-mcp/chroma_db/
```

## License

Same as original project (check upstream repo)
