# Research Workflow Guide

This guide demonstrates common research workflows using Agent-Zot's advanced query capabilities.

## 🆕 Recommended: Intelligent Unified Tools

**As of October 2025**, use these intelligent tools for most research workflows:

### `zot_search` - Finding Papers
The **recommended default** for literature discovery. Automatically:
- Detects query intent (relationship/metadata/semantic)
- Selects optimal backend combination
- Expands vague queries
- Escalates when quality is inadequate

### `zot_summarize` - Understanding Papers
The **recommended default** for paper analysis. Automatically:
- Detects desired depth (quick/targeted/comprehensive/full)
- Optimizes cost (prevents unnecessary full-text extraction)
- Orchestrates multi-aspect summaries
- Returns 4 key aspects: research question, methodology, findings, conclusions

**Complete Workflow Example:**
```
1. zot_search("neural mechanisms of cognitive control") → Find relevant papers
2. zot_summarize(item_key, "Summarize comprehensively") → Understand each paper
3. [Use specialized tools below for deeper analysis]
```

**Use specialized tools** (listed below) for specific graph analysis tasks like citation networks, concept evolution, and collaboration analysis.

## Table of Contents

1. [Literature Review Workflows](#literature-review-workflows)
2. [Citation Analysis](#citation-analysis)
3. [Topic Discovery & Trends](#topic-discovery--trends)
4. [Collaboration Networks](#collaboration-networks)
5. [Publication Strategy](#publication-strategy)
6. [Query Patterns Reference](#query-patterns-reference)

---

## Literature Review Workflows

### Finding Foundational Papers

**Goal**: Identify the most influential papers in your library or field.

**Tools**: `zot_find_seminal_papers`, `zot_semantic_search`

**Workflow**:
```
1. "Find the most influential papers in my library"
   → Uses PageRank on citation graph

2. "Find seminal papers in machine learning" (if field tagged)
   → Filters by field, ranks by citations

3. For each seminal paper:
   → "Get full metadata for paper KEY"
   → "Show me papers citing this one"
```

**Example Prompts**:
- "What are the 15 most influential papers in my library?"
- "Find seminal papers in natural language processing"
- "Show me highly-cited papers on transformers"

---

### Discovering Research Trajectories

**Goal**: Understand how a topic evolved over time.

**Tools**: `zot_track_topic_evolution`, `zot_find_recent_developments`

**Workflow**:
```
1. "Track how research on attention mechanisms evolved from 2014-2024"
   → Shows yearly paper counts, emerging concepts, trends

2. "Find recent developments on diffusion models (last 2 years)"
   → Temporal filter + semantic search

3. "What concepts emerged alongside transformers?"
   → Related concepts from evolution tracking
```

**Example Prompts**:
- "How has LLM research evolved from 2018-2025?"
- "Show me recent papers on multimodal learning (last 3 years)"
- "Track the evolution of reinforcement learning from human feedback"

---

### Exploring Concept Relationships

**Goal**: Find related concepts and papers through knowledge graph traversal.

**Tools**: `zot_explore_concept_network`, `zot_semantic_search`

**Workflow**:
```
1. "What concepts are related to self-attention through 2 hops?"
   → Multi-hop concept propagation

2. For interesting related concepts:
   → "Find papers discussing [concept] and transformers"

3. "Show me papers bridging self-attention and cross-attention"
```

**Example Prompts**:
- "Explore the concept network around graph neural networks (2 hops)"
- "What research areas connect reinforcement learning and language models?"
- "Find concepts related to vision transformers through intermediate papers"

---

## Citation Analysis

### Citation Chain Discovery

**Goal**: Find extended citation networks (papers citing papers citing X).

**Tools**: `zot_find_citation_chain`, `zot_find_related_papers`

**Workflow**:
```
1. Find a key paper:
   → "Search for 'Attention Is All You Need'"

2. "Find the citation chain for paper KEY (2 hops)"
   → Papers citing papers that cite it

3. Analyze patterns:
   → "Which of these citation chain papers are most recent?"
   → "Show me the abstracts for the top 3 papers in the chain"
```

**Example Prompts**:
- "Find papers citing papers that cite BERT"
- "Show me the citation chain for ResNet (3 hops)"
- "What papers build on work that built on GPT-2?"

---

### Identifying Paper Relationships

**Goal**: Find papers related through shared entities.

**Tools**: `zot_find_related_papers`, `zot_graph_search`

**Workflow**:
```
1. "Find papers related to KEY through the knowledge graph"
   → Shared authors, concepts, methods

2. "Search the knowledge graph for papers using [Method]"
   → Find methodological connections

3. "Show me papers discussing both [Concept A] and [Concept B]"
```

**Example Prompts**:
- "Find papers related to this one through shared methods"
- "Papers using similar datasets to KEY"
- "Show me work by authors who collaborate with Yoshua Bengio"

---

## Topic Discovery & Trends

### Finding Emerging Topics

**Goal**: Discover recent research developments and trends.

**Tools**: `zot_find_recent_developments`, `zot_track_topic_evolution`, `zot_semantic_search`

**Workflow**:
```
1. "Find recent developments on large language models (last 2 years)"
   → Recent papers with temporal filter

2. "Track how LLM research evolved from 2020-2025"
   → Identify acceleration points and emerging concepts

3. For emerging concepts:
   → "Semantic search for papers on [emerging concept]"
   → "When did papers start discussing [concept]?"
```

**Example Prompts**:
- "What are the latest papers on diffusion models?"
- "Show me recent work on mixture of experts (last year)"
- "Find papers from 2024-2025 on AI safety"

---

### Cross-Topic Analysis

**Goal**: Find connections between different research areas.

**Tools**: `zot_explore_concept_network`, `zot_hybrid_vector_graph_search`

**Workflow**:
```
1. "Explore concepts related to both vision and language (2 hops)"
   → Find bridging concepts

2. "Hybrid search for papers combining [Topic A] and [Topic B]"
   → Semantic + graph search

3. "What methods transfer between computer vision and NLP?"
```

**Example Prompts**:
- "Find papers connecting reinforcement learning and language models"
- "Show me work at the intersection of graphs and transformers"
- "Papers applying diffusion models to text generation"

---

## Collaboration Networks

### Finding Collaborators

**Goal**: Discover collaboration patterns and potential collaborators.

**Tools**: `zot_find_collaborator_network`, `zot_graph_search`

**Workflow**:
```
1. "Find collaborators of Geoffrey Hinton (2 hops)"
   → Extended co-authorship network

2. "Search the graph for authors working on [Topic]"
   → Find experts in specific areas

3. "Show me papers co-authored by [Author A] and [Author B]"
```

**Example Prompts**:
- "Who are the collaborators of Yann LeCun's collaborators?"
- "Find authors in my library who work on graph neural networks"
- "Show me the co-authorship network around Ilya Sutskever"

---

### Institution Analysis

**Goal**: Identify institutional research strengths.

**Tools**: `zot_graph_search`, `zot_analyze_venues`

**Workflow**:
```
1. "Search the graph for papers from Stanford"
   → Filter by institution

2. "What topics do Stanford researchers focus on in my library?"

3. "Find collaborations between MIT and OpenAI"
```

**Example Prompts**:
- "Show me papers from DeepMind in my library"
- "What research comes from UC Berkeley?"
- "Find inter-institution collaborations on AI safety"

---

## Publication Strategy

### Venue Analysis

**Goal**: Identify top publication venues for your research.

**Tools**: `zot_analyze_venues`, `zot_find_seminal_papers`

**Workflow**:
```
1. "Analyze top publication venues in machine learning"
   → Ranked by paper count

2. "Find seminal papers in NeurIPS" (if venue tagged as field)
   → See what gets highly cited

3. "Show me recent papers published in ICLR (last 2 years)"
   → Understand current trends
```

**Example Prompts**:
- "What are the top 10 journals/conferences in my library?"
- "Analyze publication venues for computer vision"
- "Where do the most influential papers get published?"

---

### Research Gap Identification

**Goal**: Find underexplored areas or combinations.

**Tools**: `zot_explore_concept_network`, `zot_track_topic_evolution`, `zot_semantic_search`

**Workflow**:
```
1. "Track evolution of [Topic] - identify declining concepts"
   → Find areas with decreasing activity

2. "Explore concept network around [Topic] - look for sparse connections"
   → Find weak concept links

3. "Search for papers combining [Concept A] and [Concept B]"
   → If few results, potential gap!
```

**Example Prompts**:
- "What concepts related to RL have declining research activity?"
- "Find sparse connections in the transformer concept network"
- "Are there papers combining meta-learning and causal inference?"

---

## Query Patterns Reference

### Semantic Search Patterns

**Best for**: Finding papers by meaning, topic, or abstract concepts

```
✅ Good queries:
- "Papers about self-supervised learning for vision"
- "Work on scaling laws for neural networks"
- "Research combining graphs and attention"

❌ Less effective:
- "Paper by Smith" (use metadata search instead)
- "Papers from 2023" (use recent developments instead)
```

---

### Graph Search Patterns

**Best for**: Finding relationships, networks, and connections

```
✅ Good queries:
- "Papers citing papers that cite attention mechanisms"
- "Collaborators of collaborators of Hinton"
- "Concepts related to transformers through 2 hops"
- "Find seminal papers in my library"

❌ Less effective:
- "Papers about X" (use semantic search)
- "Recent papers" (use temporal filtering)
```

---

### Hybrid Search Patterns

**Best for**: Combining semantic meaning with graph relationships

```
✅ Good queries:
- "Papers semantically similar to KEY with shared authors"
- "Recent work (2 years) on topic X with graph connections"
- "Papers discussing [Concept] by [Author's] network"
```

---

### Temporal Patterns

**Best for**: Time-based analysis and recent developments

```
✅ Good queries:
- "Recent developments on diffusion models (last 2 years)"
- "Track how LLMs evolved from 2018-2025"
- "Papers from 2024 on AI safety"

💡 Tip: Combine with semantic or graph search for powerful queries
```

---

## Advanced Workflow Examples

### Example 1: Comprehensive Literature Review

```
Goal: Understand the state of research on vision transformers

1. "Find seminal papers on vision transformers"
   → Identify foundational work

2. "Track how vision transformer research evolved from 2020-2025"
   → Understand development trajectory

3. "Find recent developments on vision transformers (last year)"
   → Latest innovations

4. "Explore concepts related to vision transformers (2 hops)"
   → Adjacent research areas

5. "Analyze top publication venues for vision research"
   → Where to publish
```

---

### Example 2: Finding Collaboration Opportunities

```
Goal: Identify potential collaborators in graph learning

1. "Search the graph for authors working on graph neural networks"
   → Find experts

2. "Find collaborator networks of [top 3 authors]"
   → Extended network

3. "What institutions are these researchers from?"

4. "Show me recent papers by these authors (2 years)"
   → Current work

5. "Find their most influential papers"
   → Assess research impact
```

---

### Example 3: Identifying Research Gaps

```
Goal: Find underexplored combinations of RL and language models

1. "Track evolution of reinforcement learning (2015-2025)"
   → RL trajectory

2. "Track evolution of language models (2015-2025)"
   → LM trajectory

3. "Search for papers combining RL and language models"
   → Existing work

4. "Explore concept network around RLHF (2 hops)"
   → Related concepts

5. Identify gaps: concepts appearing in one evolution but not the intersection
```

---

## Tips for Effective Research

### 1. Start Broad, Then Narrow

Begin with semantic search or seminal papers, then use graph tools to explore relationships.

### 2. Leverage Multi-Hop Queries

2-3 hop traversals reveal non-obvious connections. Start with 2 hops, increase if needed.

### 3. Combine Tools

Most powerful workflows use 3-4 different tools in sequence.

### 4. Use Temporal Filters

Always check recent developments (last 1-2 years) to understand current state.

### 5. Follow the Citation Chain

Highly-cited papers → citation chains → recent papers citing them = complete picture.

### 6. Verify with Semantic Search

After graph queries, use semantic search to find additional papers that might not be in the graph yet.

---

## Common Pitfalls

### ❌ Don't:
- Use graph search for broad topical queries (use semantic search)
- Ignore temporal dimensions (research moves fast!)
- Stop after finding 1 seminal paper (there are usually several)
- Forget to explore related concepts (they reveal adjacent opportunities)

### ✅ Do:
- Combine multiple query types for comprehensive coverage
- Track evolution over time to understand trends
- Explore 2-3 hops for non-obvious connections
- Use both semantic and graph approaches
- Check recent developments after historical analysis

---

## Getting Help

- **Tool Descriptions**: Each MCP tool has detailed descriptions - ask Claude to explain any tool
- **Examples**: Ask for examples of specific query types
- **Debugging**: Use `agent-zot db-status` to check database health
- **Stats**: Use `agent-zot db-inspect --stats` for collection statistics

---

## Feedback

Found this guide helpful? Have suggestions for additional workflows? Open an issue on GitHub:
https://github.com/anthropics/claude-code/issues
