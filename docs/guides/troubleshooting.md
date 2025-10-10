# Troubleshooting Guide

Common issues and solutions for Agent-Zot / Zotero MCP.

## Table of Contents

1. [Connection Issues](#connection-issues)
2. [Indexing Problems](#indexing-problems)
3. [Performance Issues](#performance-issues)
4. [Docker/Qdrant Problems](#dockerqdrant-problems)
5. [Neo4j GraphRAG Issues](#neo4j-graphrag-issues)
6. [PDF Parsing Errors](#pdf-parsing-errors)
7. [Memory Issues](#memory-issues)
8. [Claude Desktop Integration](#claude-desktop-integration)

---

## Connection Issues

### Error: "Semantic search is not initialized"

**Symptoms**: Tools return "Please run 'agent-zot update-db' first"

**Causes**:
- Database not indexed yet
- Qdrant not running
- Configuration missing

**Solutions**:

1. **Check Qdrant is running**:
```bash
docker ps | grep qdrant
```

If not running:
```bash
docker start agent-zot-qdrant
# Or if container doesn't exist:
docker run -d -p 6333:6333 -v ~/agent-zot/qdrant_storage:/qdrant/storage --name agent-zot-qdrant qdrant/qdrant
```

2. **Check database status**:
```bash
agent-zot db-status
```

3. **Index your library**:
```bash
agent-zot update-db --fulltext
```

---

### Error: "Neo4j GraphRAG is not enabled"

**Symptoms**: Graph tools return "Please configure it in config.json"

**Cause**: Neo4j not configured or not running

**Solutions**:

1. **Check Neo4j is running**:
```bash
docker ps | grep neo4j
```

2. **Verify configuration** (`~/.config/agent-zot/config.json`):
```json
{
  "neo4j_graphrag": {
    "enabled": true,
    "neo4j_uri": "neo4j://127.0.0.1:7687",
    "neo4j_user": "neo4j",
    "neo4j_password": "your_password"
  }
}
```

3. **Start Neo4j**:
```bash
docker start neo4j
# Or create new container:
docker run -d -p 7687:7687 -p 7474:7474 --name neo4j \
  -e NEO4J_AUTH=neo4j/your_password \
  neo4j:latest
```

---

### Error: "Connection refused" (Qdrant)

**Symptoms**: Can't connect to Qdrant at `localhost:6333`

**Solutions**:

1. **Check Docker**:
```bash
docker ps -a | grep qdrant
```

2. **Check logs**:
```bash
docker logs agent-zot-qdrant
```

3. **Restart container**:
```bash
docker restart agent-zot-qdrant
```

4. **Verify port**:
```bash
curl http://localhost:6333/collections
```

Should return JSON with collections list.

---

## Indexing Problems

### Indexing is Very Slow

**Symptoms**: Taking hours to index a few hundred papers

**Causes**:
- Full-text extraction with OCR
- Too many workers
- Insufficient resources

**Solutions**:

1. **Start with metadata-only** (fast):
```bash
agent-zot update-db
```

2. **Add full-text incrementally**:
```bash
agent-zot update-db --fulltext --limit 100
# Then without limit:
agent-zot update-db --fulltext
```

3. **Adjust workers in config** (`~/.config/agent-zot/config.json`):
```json
{
  "semantic_search": {
    "batch_size": 500,  // Reduce if memory issues
    "docling": {
      "num_threads": 2  // Reduce from default
    }
  }
}
```

4. **Disable OCR** if not needed:
```json
{
  "docling": {
    "ocr": {
      "fallback_enabled": false
    }
  }
}
```

---

### Error: "PDF parsing failed"

**Symptoms**: Some PDFs fail during indexing with errors

**Causes**:
- Corrupted PDFs
- Scanned PDFs without OCR
- Very large PDFs

**Solutions**:

1. **Check which PDFs failed** (from logs):
```bash
tail -f /tmp/zotero-index.log | grep "Error parsing"
```

2. **Enable OCR fallback** for scanned PDFs:
```json
{
  "docling": {
    "ocr": {
      "fallback_enabled": true,
      "min_text_threshold": 100
    }
  }
}
```

3. **Enable Granite VLM** for complex PDFs:
```json
{
  "docling": {
    "granite_fallback_enabled": true,
    "granite_min_text_threshold": 100
  }
}
```

4. **Skip problematic PDFs**: Agent-Zot fails loudly - check logs and manually review/fix problem PDFs in Zotero

---

### Indexing Stops/Hangs

**Symptoms**: Process stops without finishing

**Causes**:
- Memory exhaustion
- Timeout on large PDF
- Docker container stopped

**Solutions**:

1. **Check memory usage**:
```bash
docker stats agent-zot-qdrant
top  # Look for Python processes
```

2. **Check Docker logs**:
```bash
docker logs agent-zot-qdrant --tail 50
```

3. **Increase timeout** in config:
```json
{
  "docling": {
    "subprocess_timeout": 7200  // 2 hours
  }
}
```

4. **Resume indexing** (deduplication prevents reprocessing):
```bash
agent-zot update-db --fulltext
```

---

## Performance Issues

### Slow Semantic Search

**Symptoms**: Queries taking >10 seconds

**Causes**:
- Large collection
- Not using hybrid search
- Quantization disabled

**Solutions**:

1. **Enable hybrid search** and **quantization**:
```json
{
  "semantic_search": {
    "enable_hybrid_search": true,
    "enable_quantization": true,
    "hnsw_m": 32,
    "hnsw_ef_construct": 200
  }
}
```

2. **Check collection size**:
```bash
agent-zot db-inspect --stats
```

If >100K chunks, consider reducing chunk size or using filters.

3. **Verify HNSW index built**:
Should happen automatically, but check Qdrant logs:
```bash
docker logs agent-zot-qdrant | grep "HNSW"
```

---

### High Memory Usage

**Symptoms**: System slowing down, OOM errors

**Causes**:
- Too many parallel workers
- Large embedding model
- Docker not limited

**Solutions**:

1. **Reduce batch size**:
```json
{
  "semantic_search": {
    "batch_size": 250  // Down from 500
  }
}
```

2. **Limit Docker memory**:
```bash
docker update --memory=8g agent-zot-qdrant
```

3. **Reduce Docling threads**:
```json
{
  "docling": {
    "num_threads": 1  // Minimum
  }
}
```

4. **Use smaller embedding model**:
```json
{
  "semantic_search": {
    "sentence_transformer_model": "BAAI/bge-small-en-v1.5"  // Smaller
  }
}
```

---

## Docker/Qdrant Problems

### Qdrant Container Won't Start

**Symptoms**: Docker fails to start Qdrant

**Solutions**:

1. **Check Docker is running**:
```bash
docker info
```

2. **Check port conflicts**:
```bash
lsof -i :6333
```

If port in use, kill process or change Qdrant port.

3. **Check storage volume**:
```bash
ls -la ~/agent-zot/qdrant_storage
```

Ensure directory exists and has permissions.

4. **Recreate container**:
```bash
docker stop agent-zot-qdrant
docker rm agent-zot-qdrant
docker run -d -p 6333:6333 \
  -v ~/agent-zot/qdrant_storage:/qdrant/storage \
  --name agent-zot-qdrant \
  qdrant/qdrant
```

---

### Lost Qdrant Data

**Symptoms**: Database shows 0 documents after restart

**Cause**: Volume not persisted

**Solutions**:

1. **Check volume mount**:
```bash
docker inspect agent-zot-qdrant | grep Mounts -A 10
```

Should show bind mount to `~/agent-zot/qdrant_storage`.

2. **Check storage directory**:
```bash
ls ~/agent-zot/qdrant_storage/collections/
```

If empty, data was not persisted.

3. **Recreate with proper volume**:
```bash
docker stop agent-zot-qdrant
docker rm agent-zot-qdrant
docker run -d -p 6333:6333 \
  -v ~/agent-zot/qdrant_storage:/qdrant/storage \
  --name agent-zot-qdrant \
  qdrant/qdrant
```

4. **Re-index if data lost**:
```bash
agent-zot update-db --force-rebuild --fulltext
```

---

## Neo4j GraphRAG Issues

### Graph Search Returns Empty Results

**Symptoms**: Graph tools work but return no results

**Causes**:
- Graph not populated yet
- Entity extraction failed
- Wrong field/concept names

**Solutions**:

1. **Check graph has data**:
```bash
# Via Neo4j browser at http://localhost:7474
# Or check stats:
curl -u neo4j:password http://localhost:7474/db/neo4j/tx/commit \
  -H "Content-Type: application/json" \
  -d '{"statements":[{"statement":"MATCH (n) RETURN count(n)"}]}'
```

2. **Re-run update-db** to populate graph:
```bash
agent-zot update-db --fulltext
```

Graph population happens during indexing.

3. **Check entity extraction logs**:
Look for "Extracting entities" in logs.

4. **Verify Ollama is running** (if using local LLM):
```bash
curl http://localhost:11434/api/tags
```

---

### Neo4j Connection Timeout

**Symptoms**: "Connection timeout" or "Unable to connect"

**Solutions**:

1. **Check Neo4j is running**:
```bash
docker ps | grep neo4j
docker logs neo4j
```

2. **Verify credentials**:
Default: `neo4j / demodemo` (or your password)

3. **Test connection**:
```bash
curl http://localhost:7474
```

Should return Neo4j info page.

---

## PDF Parsing Errors

### OCR Errors with EasyOCR

**Symptoms**: "EasyOCR failed" or OCR-related errors

**Causes**:
- EasyOCR dependencies missing
- GPU/MPS issues
- Insufficient memory

**Solutions**:

1. **Disable OCR** if not needed:
```json
{
  "docling": {
    "ocr": {
      "fallback_enabled": false
    }
  }
}
```

2. **Use Granite VLM instead**:
```json
{
  "docling": {
    "granite_fallback_enabled": true,
    "ocr": {
      "fallback_enabled": false
    }
  }
}
```

3. **Check EasyOCR installation**:
```bash
python -c "import easyocr; print(easyocr.__version__)"
```

---

### Docling V2 Backend Errors

**Symptoms**: Parsing fails with V2 backend errors

**Solution**: System will auto-fallback to Granite VLM or OCR. Check config ensures fallbacks enabled:

```json
{
  "docling": {
    "granite_fallback_enabled": true,
    "ocr": {
      "fallback_enabled": true
    }
  }
}
```

---

## Memory Issues

### Python Process Using Too Much RAM

**Symptoms**: System swap usage, slowdowns

**Solutions**:

1. **Limit embedding batch size**:
```json
{
  "semantic_search": {
    "batch_size": 100  // Much smaller
  }
}
```

2. **Reduce parallel processing**:
```json
{
  "docling": {
    "num_threads": 1
  }
}
```

3. **Use quantization**:
```json
{
  "semantic_search": {
    "enable_quantization": true
  }
}
```

4. **Restart indexing in batches**:
```bash
agent-zot update-db --fulltext --limit 500
agent-zot update-db --fulltext --limit 1000
agent-zot update-db --fulltext  # Continues from where it left off
```

---

## Claude Desktop Integration

### Claude Can't See Zotero Tools

**Symptoms**: Tools not appearing in Claude Desktop

**Solutions**:

1. **Check config file location**:
```bash
# macOS
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Linux
cat ~/.config/Claude/claude_desktop_config.json
```

2. **Verify config format**:
```json
{
  "mcpServers": {
    "zotero": {
      "command": "/path/to/agent-zot",
      "env": {
        "ZOTERO_LOCAL": "true",
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

3. **Check command path**:
```bash
which agent-zot
```

Use this path in config.

4. **Restart Claude Desktop** completely (quit and reopen)

5. **Check Claude logs**:
```bash
# macOS
tail -f ~/Library/Logs/Claude/mcp*.log
```

---

### Tools Return "Not initialized" in Claude

**Symptoms**: Tools appear but don't work

**Cause**: Database not indexed OR environment variables not set

**Solutions**:

1. **Check env vars in config**:
Must include `OPENAI_API_KEY` for embeddings.

2. **Run initial indexing**:
```bash
agent-zot update-db --fulltext
```

3. **Verify with CLI** (same environment):
```bash
agent-zot db-status
```

---

## Debugging Commands

### Useful diagnostic commands:

```bash
# System status
agent-zot setup-info

# Database status
agent-zot db-status
agent-zot db-inspect --stats

# Docker status
docker ps -a
docker stats

# Check ports
lsof -i :6333  # Qdrant
lsof -i :7687  # Neo4j
lsof -i :11434 # Ollama

# Logs
docker logs agent-zot-qdrant
docker logs neo4j
tail -f /tmp/zotero-index.log

# Test connections
curl http://localhost:6333/collections
curl http://localhost:7474
curl http://localhost:11434/api/tags
```

---

## Still Having Issues?

1. **Check logs first**: Most errors are explained in logs
2. **Verify prerequisites**: Docker, Python 3.10+, sufficient RAM (16GB recommended)
3. **Test with `--limit 10`**: Quick test without full indexing
4. **GitHub Issues**: https://github.com/anthropics/claude-code/issues
5. **Include**:
   - Error message
   - Output of `agent-zot setup-info`
   - Relevant log snippets
   - OS and Python version

---

## Performance Benchmarks

Expected indexing times (M1 Pro, 16GB RAM):

- **Metadata only**: ~2-5 items/second (~10 min for 3000 items)
- **With full-text (V2 backend)**: ~1-2 items/second (~30-50 min for 3000 items)
- **With OCR fallback**: ~10-30 seconds/PDF (hours for many PDFs)

Expected query times:

- **Semantic search**: <1 second (hybrid), <3 seconds (dense only)
- **Graph queries**: <2 seconds for most queries
- **Multi-hop (3 hops)**: 2-5 seconds

If significantly slower, check performance issues section above.
