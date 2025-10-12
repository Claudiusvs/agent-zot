# Frequently Asked Questions (FAQ)

Quick answers to common questions about Agent-Zot / Zotero MCP.

## Table of Contents

- [Setup & Installation](#setup--installation)
- [Configuration](#configuration)
- [Indexing & Database](#indexing--database)
- [Search & Queries](#search--queries)
- [Performance & Optimization](#performance--optimization)
- [Costs & Resources](#costs--resources)
- [Claude Desktop Integration](#claude-desktop-integration)
- [Troubleshooting](#troubleshooting)

---

## Setup & Installation

### Q: What are the minimum system requirements?

**A:**
- **Python**: 3.10 or higher
- **RAM**: 16GB recommended (8GB minimum)
- **Docker**: Required for Qdrant vector database
- **Disk Space**:
  - ~2GB for Python dependencies
  - 1-10GB for Qdrant storage (depends on library size)
  - 5-20GB for optional Ollama models

### Q: Do I need a local Zotero installation?

**A:** No, but it's recommended. You can use either:
- **Local mode** (`ZOTERO_LOCAL=true`) - Faster, no API limits, requires local Zotero
- **Remote mode** (`ZOTERO_LOCAL=false`) - Slower, API rate limits, works from anywhere with API key

### Q: Can I use this without Docker?

**A:** Not currently. Qdrant requires Docker. Future versions may support Qdrant Cloud or other vector databases.

### Q: How long does initial setup take?

**A:**
- Installation: 5-10 minutes
- Qdrant Docker setup: 2 minutes
- First indexing (metadata only): 10-30 minutes for 3000 papers
- Full-text indexing: 1-3 hours for 3000 papers (depends on PDF complexity)

---

## Configuration

### Q: Which embedding model should I use?

**A:**

| Model | Pros | Cons | Best For |
|-------|------|------|----------|
| **OpenAI text-embedding-3-large** | Best quality, 3072D | Costs money (~$0.13/1M tokens) | Production use, large libraries |
| **BGE-M3** | Multilingual, 1024D, local | Slower embedding, requires GPU/MPS | Multilingual research, privacy |
| **OpenAI text-embedding-3-small** | Fast, cheap, 1536D | Lower quality | Testing, small libraries |

**Default**: BGE-M3 for multilingual + local inference balance.

### Q: Should I enable OCR?

**A:**

**Enable OCR if**:
- You have scanned PDFs (no digital text)
- Historical documents or handwritten notes
- You need 100% text extraction coverage

**Disable OCR if**:
- All PDFs are digital/born-digital
- Speed is critical (OCR adds 10-30 sec/PDF)
- You have limited computational resources

**Recommendation**: Start with OCR **disabled**, enable only if you get low text extraction rates.

### Q: What's the difference between Granite VLM and OCR?

**A:**

| Feature | Granite VLM | OCR (EasyOCR) |
|---------|-------------|---------------|
| **Method** | Vision-language model | Traditional OCR |
| **Quality** | Better for complex layouts | Better for simple scanned text |
| **Speed** | Slower (~30-60 sec/page) | Fast (~5-10 sec/page) |
| **Use case** | Tables, figures, complex PDFs | Scanned documents |

**Recommendation**: Use Granite VLM as primary fallback, OCR as secondary fallback.

### Q: Should I use Neo4j GraphRAG?

**A:**

**Yes, if you want**:
- Citation network analysis
- Collaboration network discovery
- Concept relationship exploration
- Multi-hop graph queries

**No, if**:
- You only need basic semantic search
- You want to minimize setup complexity
- Your library is small (<500 papers)

**Note**: GraphRAG is optional. Semantic search works independently.

### Q: Which LLM should I use for entity extraction?

**A:**

| LLM | Pros | Cons | Cost |
|-----|------|------|------|
| **Ollama Mistral 7B** (local) | Free, fast, works offline | Requires 8GB+ RAM | Free |
| **OpenAI GPT-4o-mini** | Best quality, multilingual | API costs | ~$0.15/1M input tokens |

**Recommendation**: Use **Ollama Mistral 7B** for free local extraction. Switch to GPT-4o-mini only if you need better multilingual entity extraction or more accurate entity linking.

---

## Indexing & Database

### Q: What's the difference between `update-db` and `update-db --fulltext`?

**A:**

| Flag | What it indexes | Speed | Best for |
|------|----------------|-------|----------|
| **No flags** | Metadata only (title, abstract, notes) | Fast (2-5 items/sec) | Quick setup, testing |
| `--fulltext` | Full PDF text via Docling parser | Slow (1-2 items/sec) | Complete research workflows |

**Workflow**: Start with `update-db` (fast), then run `update-db --fulltext` once.

### Q: What does `--force-rebuild` do?

**A:**
- Deletes the entire Qdrant collection
- Re-indexes everything from scratch
- Use when:
  - Changing embedding models
  - Changing chunk size/settings
  - Corruption suspected

**Warning**: Does NOT delete Neo4j graph. Use `--reset-graph` to also clear graph database.

### Q: How do I add new papers to my indexed library?

**A:** Just run:
```bash
agent-zot update-db --fulltext
```

The system automatically:
- Detects new papers in Zotero
- Skips already-indexed papers (deduplication)
- Indexes only new/changed items

### Q: Can I pause and resume indexing?

**A:** Yes! The system has built-in deduplication. If indexing stops:
1. Just run `update-db --fulltext` again
2. Already-indexed papers are skipped
3. Indexing continues from where it left off

### Q: How much disk space does indexing use?

**A:**

For a 3000-paper library:
- **Metadata only**: ~200-500 MB
- **With full-text**: ~2-5 GB (depends on chunk size and embedding model)
- **Neo4j graph**: ~100-500 MB

Use `docker system df` to check actual Qdrant storage usage.

---

## Search & Queries

### Q: When should I use semantic search vs. graph search?

**A:**

| Query Type | Use Semantic Search | Use Graph Search |
|------------|-------------------|------------------|
| **Topic-based** | "Papers about transformers" | ❌ |
| **Conceptual** | "Self-supervised learning" | ❌ |
| **Citation analysis** | ❌ | "Papers citing papers that cite X" |
| **Collaboration networks** | ❌ | "Collaborators of author Y" |
| **Multi-hop relationships** | ❌ | "Concepts related to X (2 hops)" |
| **Recent papers** | "Latest work on diffusion models (2 years)" | ❌ |

**Hybrid approach**: Use both! Example: "Semantic search for topic X, then explore citation graph around top results."

### Q: What are "hops" in graph queries?

**A:**
- **1 hop**: Direct connections (papers citing X, immediate collaborators)
- **2 hops**: Connections of connections (papers citing papers that cite X)
- **3 hops**: Extended network (rarely needed, can be slow)

**Recommendation**: Start with 2 hops. Increase only if you need broader network coverage.

### Q: How does hybrid search work?

**A:**
Combines two search methods:
1. **Dense vectors** (semantic meaning via embeddings)
2. **Sparse vectors** (keyword matching via BM25)

Results are merged using **RRF (Reciprocal Rank Fusion)** for best of both worlds.

**When to use**: Always! Hybrid search is enabled by default and provides better results than either method alone.

### Q: What's the difference between `zot_search_items` and `zot_semantic_search`?

**A:**

| Tool | Search Method | Best For |
|------|--------------|----------|
| `zot_search_items` | Metadata fields (title, creator, year) | Finding specific papers by author/title |
| `zot_semantic_search` | Vector similarity + hybrid | Finding papers by topic/concept/meaning |

**Example**:
- "Find papers by Hinton" → Use `zot_search_items`
- "Find papers about deep learning" → Use `zot_semantic_search`

---

## Performance & Optimization

### Q: Why is indexing so slow?

**A:** Common causes:
1. **Full-text extraction** - Parsing PDFs is slow (1-2 items/sec)
2. **OCR enabled** - Adds 10-30 sec per scanned PDF
3. **Too many workers** - Can cause memory issues and slow down
4. **Large PDFs** - 100+ page papers take longer to parse

**Solutions**:
- Start without `--fulltext` for quick metadata indexing
- Disable OCR if not needed
- Reduce `num_threads` in config to 1-2
- Use `--limit 100` to test with small batches

### Q: How can I speed up search queries?

**A:**
1. **Enable quantization** (reduces vector size):
   ```json
   {
     "semantic_search": {
       "enable_quantization": true
     }
   }
   ```

2. **Use hybrid search** (faster than dense-only):
   ```json
   {
     "semantic_search": {
       "enable_hybrid_search": true
     }
   }
   ```

3. **Reduce chunk size** (fewer vectors to search):
   ```json
   {
     "docling": {
       "chunk_size": 500
     }
   }
   ```

### Q: My system is using too much RAM. How do I reduce memory usage?

**A:**
1. **Reduce batch size**:
   ```json
   {
     "semantic_search": {
       "batch_size": 100
     }
   }
   ```

2. **Use smaller embedding model**:
   ```json
   {
     "semantic_search": {
       "sentence_transformer_model": "BAAI/bge-small-en-v1.5"
     }
   }
   ```

3. **Limit Docker memory**:
   ```bash
   docker update --memory=8g agent-zot-qdrant
   ```

4. **Reduce Docling workers**:
   ```json
   {
     "docling": {
       "num_threads": 1
     }
   }
   ```

---

## Costs & Resources

### Q: How much does OpenAI embedding cost?

**A:**

For **text-embedding-3-large** ($0.13 per 1M tokens):

| Library Size | Metadata Only | With Full-Text |
|-------------|---------------|----------------|
| 1,000 papers | ~$0.05-0.10 | ~$1-3 |
| 5,000 papers | ~$0.25-0.50 | ~$5-15 |
| 10,000 papers | ~$0.50-1.00 | ~$10-30 |

**Note**: Full-text costs depend heavily on PDF size and chunk settings.

**Free alternative**: Use BGE-M3 local embeddings (no API costs).

### Q: How much does Neo4j entity extraction cost?

**A:**

With **Ollama Mistral 7B** (local): **FREE**

With **OpenAI GPT-4o-mini**:
- ~$0.15 per 1M input tokens
- ~500-1000 tokens per paper
- ~$0.08-0.15 per 1000 papers

**Recommendation**: Use free Ollama for most use cases.

### Q: Can I use this completely free (no API costs)?

**A:** **Yes!** Use:
- **Embeddings**: BGE-M3 (local)
- **Entity extraction**: Ollama Mistral 7B (local)
- **Vector DB**: Qdrant (Docker, free)
- **Graph DB**: Neo4j Community Edition (Docker, free)

Only requirement: Sufficient RAM (16GB recommended) and disk space.

---

## Claude Desktop Integration

### Q: Where is the Claude Desktop config file?

**A:**

**macOS**:
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Linux**:
```
~/.config/Claude/claude_desktop_config.json
```

**Windows**:
```
%APPDATA%\Claude\claude_desktop_config.json
```

### Q: How do I verify Claude Desktop can see the tools?

**A:**
1. Open Claude Desktop
2. Look for the hammer icon (🔨) in the input area
3. Click it to see available MCP tools
4. You should see `zot_semantic_search`, `zot_get_item_metadata`, etc.

If not visible:
- Check config file syntax (must be valid JSON)
- Restart Claude Desktop completely (quit and reopen)
- Check logs: `~/Library/Logs/Claude/mcp*.log` (macOS)

### Q: Why do tools appear but return "Not initialized"?

**A:** Database not indexed yet. Run:
```bash
agent-zot update-db --fulltext
```

Then restart Claude Desktop.

### Q: Can I use Claude Desktop without indexing?

**A:** Partially. These tools work without indexing:
- `zot_search_items` (metadata search)
- `zot_get_item_metadata`
- `zot_get_collections`
- `zot_get_tags`

These require indexing:
- `zot_semantic_search`
- `zot_graph_search`
- All Neo4j GraphRAG tools

---

## Troubleshooting

### Q: Error: "Semantic search is not initialized"

**A:**
1. Check Qdrant is running: `docker ps | grep qdrant`
2. If not running: `docker start agent-zot-qdrant`
3. Check database status: `agent-zot db-status`
4. If empty: `agent-zot update-db --fulltext`

### Q: Error: "Connection refused" (Qdrant)

**A:**
```bash
# Check Docker status
docker ps -a | grep qdrant

# Restart container
docker restart agent-zot-qdrant

# Check logs
docker logs agent-zot-qdrant

# Test connection
curl http://localhost:6333/collections
```

If still failing, recreate container:
```bash
docker stop agent-zot-qdrant
docker rm agent-zot-qdrant
docker run -d -p 6333:6333 \
  -v ~/agent-zot/qdrant_storage:/qdrant/storage \
  --name agent-zot-qdrant \
  qdrant/qdrant
```

### Q: Error: "Neo4j GraphRAG is not enabled"

**A:**
1. Verify Neo4j is running: `docker ps | grep neo4j`
2. Check config has Neo4j settings:
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
3. Start Neo4j if needed:
   ```bash
   docker start neo4j
   ```

### Q: Indexing hangs or stops

**A:**
1. Check memory usage: `docker stats agent-zot-qdrant`
2. Check for stuck processes: `top` or `htop`
3. Check Docker logs: `docker logs agent-zot-qdrant --tail 50`
4. Resume indexing (deduplication prevents reprocessing): `agent-zot update-db --fulltext`

### Q: Search results are poor quality

**A:**
1. **Enable hybrid search** if not already:
   ```json
   {"semantic_search": {"enable_hybrid_search": true}}
   ```

2. **Check if full-text indexed**:
   ```bash
   agent-zot db-inspect --stats
   ```
   Look for chunk counts. If 0, full-text not indexed.

3. **Verify embedding model**:
   Larger models give better results (BGE-M3 < text-embedding-3-large)

4. **Rebuild with different chunk size**:
   Smaller chunks (500-1000 tokens) often work better for specific queries.

---

## Quick Command Reference

```bash
# Setup
agent-zot setup                    # Interactive setup wizard
agent-zot setup-info               # Show current configuration

# Indexing
agent-zot update-db                # Index metadata only (fast)
agent-zot update-db --fulltext     # Index with full PDF text
agent-zot update-db --force-rebuild --fulltext  # Rebuild everything

# Database management
agent-zot db-status                # Check database status
agent-zot db-inspect --stats       # Show collection statistics
agent-zot db-inspect --key ITEM_KEY  # Inspect specific item

# Docker
docker ps | grep qdrant             # Check Qdrant status
docker logs agent-zot-qdrant        # View logs
docker restart agent-zot-qdrant     # Restart container

# Testing
curl http://localhost:6333/collections  # Test Qdrant connection
```

---

## Additional Resources

- **Setup Guide**: README.md
- **Research Workflows**: RESEARCH_GUIDE.md
- **Detailed Troubleshooting**: TROUBLESHOOTING.md
- **Project Architecture**: CLAUDE.md
- **GitHub Issues**: https://github.com/anthropics/claude-code/issues

---

## Still Have Questions?

1. Check **TROUBLESHOOTING.md** for detailed error solutions
2. Check **RESEARCH_GUIDE.md** for workflow examples
3. Run `agent-zot setup-info` to verify your setup
4. Check logs: `docker logs agent-zot-qdrant`
5. Open an issue on GitHub with:
   - Error message
   - Output of `agent-zot setup-info`
   - Relevant log snippets
   - OS and Python version
