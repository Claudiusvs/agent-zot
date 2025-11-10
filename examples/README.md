# Agent-Zot v3.0+ Code Execution Examples

This directory contains practical examples demonstrating the **MCP Code Execution Pattern** introduced in agent-zot v3.0.

## 🎯 Why Code Execution?

**Token Efficiency**: Process large datasets BEFORE results enter Claude's context window.

| Pattern | v2.1 (MCP Tools) | v3.0 (Code Execution) | Reduction |
|---------|------------------|----------------------|-----------|
| Basic search (50 papers) | 40,000 tokens | 4,000 tokens | **90%** |
| Search + filter (100 papers) | 80,000 tokens | 2,000 tokens | **97.5%** |
| Batch processing (50 queries) | 800,000 tokens | 60,000 tokens | **92.5%** |

---

## 📚 Examples

### 1. `basic_search.py` - Simple Semantic Search

**Use case**: Find and display papers on a topic

**Key concept**: Execute search, display subset

```bash
python examples/basic_search.py
```

**Token savings**: 90% (50 papers → top 10 displayed)

---

### 2. `search_and_filter.py` - Multi-Criteria Filtering

**Use case**: Complex filtering (year, authors, citations)

**Key concept**: Filter 100 papers → 5 papers BEFORE entering context

```bash
python examples/search_and_filter.py
```

**Token savings**: 97.5% (100 papers → 5 papers)

**This is THE killer feature!** All filtering happens in your Python environment.

---

### 3. `batch_processing.py` - Multiple Queries

**Use case**: Literature review across multiple topics

**Key concept**: Process 50+ queries, keep top 3 results per query

```bash
python examples/batch_processing.py
```

**Token savings**: 92.5% (1,000 total papers → 15 displayed)

---

## 🚀 Running Examples

### Prerequisites

1. **Install agent-zot**:
   ```bash
   cd ~/toolboxes/agent-zot
   source .venv/bin/activate
   pip install -e .
   ```

2. **Index your Zotero library**:
   ```bash
   agent-zot update-db --fulltext
   ```

3. **Ensure Zotero is running** (if using ZOTERO_LOCAL="true")

### Execute

```bash
# Navigate to agent-zot directory
cd ~/toolboxes/agent-zot

# Activate virtual environment
source .venv/bin/activate

# Run any example
python examples/basic_search.py
python examples/search_and_filter.py
python examples/batch_processing.py
```

---

## 🎓 Learning Path

### 1. Start with `basic_search.py`
- Understand the import pattern
- See how to execute search directly
- Learn basic result handling

### 2. Progress to `search_and_filter.py`
- Grasp the core value proposition
- Practice multi-criteria filtering
- Understand token savings mechanism

### 3. Master `batch_processing.py`
- Scale to multiple queries
- Handle large datasets efficiently
- Apply to real research workflows

---

## 📖 Additional Resources

**Complete Documentation**:
- **`~/.claude/skills/agent-zot-research/SKILL.md`**: Full v3.0 guide (1,459 lines)
- **`~/toolboxes/PAI/notes/mcp-code-execution-optimization-for-agent-zot.md`**: Implementation details (606 lines)

**Migration Guide**: See README.md Breaking Change section

**Troubleshooting**:
- Import errors? `pip install -e .` from agent-zot directory
- Module not found? Check you're in virtual environment
- Connection errors? Ensure Zotero is running (if ZOTERO_LOCAL="true")

---

## 🤝 Contributing

Have an example that showcases the code execution pattern? Submit a PR!

**Good example criteria**:
- Demonstrates clear token savings
- Solves real research workflow problem
- Well-commented with token calculations
- Includes usage instructions

---

## 📄 License

Same as parent project - see [agent-zot LICENSE](../LICENSE)
