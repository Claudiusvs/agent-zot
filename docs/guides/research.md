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

### `zot_explore_graph` - Exploring Connections
The **recommended default** for graph exploration and network analysis. Automatically:
- Detects exploration strategy (citation/collaboration/concept/temporal/influence/venue)
- Selects optimal Neo4j traversal pattern
- Extracts parameters from queries (author names, years, concepts)
- Provides 7 specialized modes + comprehensive mode

**Complete Workflow Example:**
```
1. zot_search("neural mechanisms of cognitive control") → Find relevant papers
2. zot_summarize(item_key, "Summarize comprehensively") → Understand each paper
3. zot_explore_graph("Who collaborated with [author]?") → Explore connections
4. zot_explore_graph("How has [topic] evolved from 2015-2025?") → Track evolution
```

**Legacy tools** (listed below) are still available for manual control when needed, but the three intelligent tools above handle 95% of research workflows automatically.

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

**Recommended Tool**: `zot_explore_graph` (Influence Mode)

**Quick Start**:
```
Simply ask in natural language:
→ "Find the most influential papers in my library"
→ "What are the seminal papers in neuroscience?"
→ "Show me highly-cited papers on memory"

The tool automatically:
- Detects "influence" intent (90% confidence)
- Uses PageRank analysis on citation graph
- Ranks papers by citation impact
```

**Legacy Workflow** (for manual control):
```
Tools: `zot_find_seminal_papers`, `zot_semantic_search`

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

**Recommended Tool**: `zot_explore_graph` (Temporal Mode)

**Quick Start**:
```
Simply ask in natural language:
→ "How has research on attention evolved from 2014-2024?"
→ "Track the evolution of transformers from 2017 to 2025"
→ "Show me how memory research changed from 2010-2024"

The tool automatically:
- Detects "temporal" intent (85% confidence)
- Extracts concept and year range from query
- Performs yearly aggregation + concept filtering
- Shows emerging trends over time
```

**Legacy Workflow** (for manual control):
```
Tools: `zot_track_topic_evolution`, `zot_find_recent_developments`

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

**Recommended Tool**: `zot_explore_graph` (Concept Network Mode)

**Quick Start**:
```
Simply ask in natural language:
→ "What concepts are related to self-attention?"
→ "Explore concepts around working memory"
→ "What connects attention and memory?"

The tool automatically:
- Detects "concept" intent (85% confidence)
- Extracts concept from query
- Performs multi-hop concept propagation (2 hops default)
- Shows related concepts through intermediate papers
```

**Legacy Workflow** (for manual control):
```
Tools: `zot_explore_concept_network`, `zot_semantic_search`

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

**Recommended Tool**: `zot_explore_graph` (Citation Chain Mode)

**Quick Start**:
```
Simply ask in natural language:
→ "Find papers citing papers that cite [paper_key]"
→ "Show me the citation chain for this paper"
→ "What papers build on work citing BERT?"

The tool automatically:
- Detects "citation" intent (90% confidence)
- Performs multi-hop citation traversal (2 hops default)
- Returns extended citation network with paper details
```

**Legacy Workflow** (for manual control):
```
Tools: `zot_find_citation_chain`, `zot_find_related_papers`

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

**Recommended Tool**: `zot_explore_graph` (Collaboration Mode)

**Quick Start**:
```
Simply ask in natural language:
→ "Who collaborated with Geoffrey Hinton?"
→ "Find the collaborators of Yann LeCun"
→ "Who has worked with Lanius?"

The tool automatically:
- Detects "collaboration" intent (90% confidence)
- Extracts author name from query
- Performs multi-hop co-authorship traversal (2 hops default)
- Returns extended collaboration network
```

**Legacy Workflow** (for manual control):
```
Tools: `zot_find_collaborator_network`, `zot_graph_search`

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

**Recommended Tool**: `zot_explore_graph` (Venue Analysis Mode)

**Quick Start**:
```
Simply ask in natural language:
→ "What are the top journals in my library?"
→ "Show me the best publication venues"
→ "Analyze venues for neuroscience"

The tool automatically:
- Detects "venue" intent (80% confidence)
- Extracts field filter if present
- Aggregates publication venue statistics
- Ranks by paper count with metadata
```

**Legacy Workflow** (for manual control):
```
Tools: `zot_analyze_venues`, `zot_find_seminal_papers`

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

Using the three intelligent tools:

1. zot_search("vision transformers")
   → Find relevant papers (Fast or Comprehensive mode)

2. zot_summarize(item_key, "Summarize comprehensively")
   → Understand each key paper (4 aspects: question, methods, findings, conclusions)

3. zot_explore_graph("Find the most influential papers on vision transformers")
   → Identify foundational work (Influence Mode - automatic)

4. zot_explore_graph("How has vision transformer research evolved from 2020-2025?")
   → Development trajectory (Temporal Mode - automatic parameter extraction)

5. zot_explore_graph("What concepts are related to vision transformers?")
   → Adjacent research areas (Concept Network Mode - 2 hops)

6. zot_explore_graph("What are the top venues for vision research?")
   → Publication outlets (Venue Analysis Mode)

All modes detected automatically - just ask in natural language!
```

---

### Example 2: Finding Collaboration Opportunities

```
Goal: Identify potential collaborators in graph learning

Using the three intelligent tools:

1. zot_search("graph neural networks")
   → Find papers in this area (Fast or Graph-enriched mode)

2. zot_explore_graph("Who collaborated with [top author from results]?")
   → Extended network (Collaboration Mode - automatic author extraction)

3. zot_search("papers by [collaborator name] published in 2023-2024")
   → Current work (Metadata-enriched mode - automatic intent detection)

4. zot_explore_graph("Find the most influential papers by [author]")
   → Assess impact (Influence Mode with author filter)

5. zot_summarize(item_key, "What methodology did they use?")
   → Understand approach (Targeted Mode - semantic Q&A)

Collaboration network → Impact → Current work → Methodology
All detected automatically!
```

---

### Example 3: Identifying Research Gaps

```
Goal: Find underexplored combinations of RL and language models

Using the three intelligent tools:

1. zot_explore_graph("How has reinforcement learning evolved from 2015-2025?")
   → RL trajectory (Temporal Mode - automatic parameter extraction)

2. zot_explore_graph("How have language models evolved from 2015-2025?")
   → LM trajectory (Temporal Mode)

3. zot_search("papers combining reinforcement learning and language models")
   → Existing work (Fast or Comprehensive mode)

4. zot_explore_graph("What concepts connect RL and language models?")
   → Bridging concepts (Concept Network Mode)

5. zot_summarize(item_key, "Summarize comprehensively")
   → Understand existing RL+LM work (Comprehensive Mode - 4 aspects)

Identify gaps: concepts in each evolution but sparse in the intersection
All modes and parameters detected automatically!
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
