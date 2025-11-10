# Implementation Tasks

## 1. Preparation

> **Execution:** SEQUENTIAL
> **Dependencies:** None

- [ ] 1.1 Review current MCP tool implementations in `src/agent_zot/core/server.py`
- [ ] 1.2 Identify all active tools (zot_search, zot_summarize, zot_explore_graph, zot_manage_*)
- [ ] 1.3 Document tool import dependencies and required modules

## 2. Create Tools Directory Structure

> **Execution:** SEQUENTIAL
> **Dependencies:** Section 1 complete

- [ ] 2.1 Create directory: `src/agent_zot/mcp_tools/`
- [ ] 2.2 Create `__init__.py` with tool exports
- [ ] 2.3 Add directory to Python package structure

## 3. Extract Tool Implementations

> **Execution:** PARALLEL
> **Groups:** 8 (one per tool)
> **Dependencies:** Section 2 complete
> **Worktree Pattern:** `extract-{tool-name}`

### 3.1 Extract zot_search
- [x] 3.1.1 Read current zot_search implementation in server.py
- [x] 3.1.2 Create `mcp_tools/zot_search.py` with module docstring
- [x] 3.1.3 Add required imports (typing, unified_smart_search)
- [x] 3.1.4 Copy zot_search function implementation
- [x] 3.1.5 Add function docstring with usage examples
- [x] 3.1.6 Test: `python -c "from agent_zot.mcp_tools.zot_search import zot_search"`

### 3.2 Extract zot_summarize
- [x] 3.2.1 Read current zot_summarize implementation in server.py
- [x] 3.2.2 Create `mcp_tools/zot_summarize.py` with module docstring
- [x] 3.2.3 Add required imports
- [x] 3.2.4 Copy zot_summarize function implementation
- [x] 3.2.5 Add function docstring with usage examples
- [x] 3.2.6 Test: `python -c "from agent_zot.mcp_tools.zot_summarize import zot_summarize"`

### 3.3 Extract zot_explore_graph
- [x] 3.3.1 Read current zot_explore_graph implementation in server.py
- [x] 3.3.2 Create `mcp_tools/zot_explore_graph.py` with module docstring
- [x] 3.3.3 Add required imports
- [x] 3.3.4 Copy zot_explore_graph function implementation
- [x] 3.3.5 Add function docstring with usage examples
- [x] 3.3.6 Test: `python -c "from agent_zot.mcp_tools.zot_explore_graph import zot_explore_graph"`

### 3.4 Extract zot_manage_collections
- [x] 3.4.1 Read current zot_manage_collections implementation in server.py
- [x] 3.4.2 Create `mcp_tools/zot_manage_collections.py` with module docstring
- [x] 3.4.3 Add required imports
- [x] 3.4.4 Copy zot_manage_collections function implementation
- [x] 3.4.5 Add function docstring with usage examples
- [x] 3.4.6 Test: `python -c "from agent_zot.mcp_tools.zot_manage_collections import zot_manage_collections"`

### 3.5 Extract zot_manage_tags
- [x] 3.5.1 Read current zot_manage_tags implementation in server.py
- [x] 3.5.2 Create `mcp_tools/zot_manage_tags.py` with module docstring
- [x] 3.5.3 Add required imports
- [x] 3.5.4 Copy zot_manage_tags function implementation
- [x] 3.5.5 Add function docstring with usage examples
- [x] 3.5.6 Test: `python -c "from agent_zot.mcp_tools.zot_manage_tags import zot_manage_tags"`

### 3.6 Extract zot_manage_notes
- [x] 3.6.1 Read current zot_manage_notes implementation in server.py
- [x] 3.6.2 Create `mcp_tools/zot_manage_notes.py` with module docstring
- [x] 3.6.3 Add required imports
- [x] 3.6.4 Copy zot_manage_notes function implementation
- [x] 3.6.5 Add function docstring with usage examples
- [x] 3.6.6 Test: `python -c "from agent_zot.mcp_tools.zot_manage_notes import zot_manage_notes"`

### 3.7 Extract zot_export
- [x] 3.7.1 Read current zot_export implementation in server.py
- [x] 3.7.2 Create `mcp_tools/zot_export.py` with module docstring
- [x] 3.7.3 Add required imports
- [x] 3.7.4 Copy zot_export function implementation
- [x] 3.7.5 Add function docstring with usage examples
- [x] 3.7.6 Test: `python -c "from agent_zot.mcp_tools.zot_export import zot_export"`

### 3.8 Extract zot_manage_database
- [x] 3.8.1 Read current zot_manage_database implementation in server.py
- [x] 3.8.2 Create `mcp_tools/zot_manage_database.py` with module docstring
- [x] 3.8.3 Add required imports
- [x] 3.8.4 Copy zot_manage_database function implementation
- [x] 3.8.5 Add function docstring with usage examples
- [x] 3.8.6 Test: `python -c "from agent_zot.mcp_tools.zot_manage_database import zot_manage_database"`

## 4. Add MCP Resource Decorators

> **Execution:** SEQUENTIAL
> **Dependencies:** Section 3 complete

### 4.1 Add resource for zot_search
- [x] 4.1.1 Create resource handler function in server.py
- [x] 4.1.2 Add `@mcp.resource("agent-zot://tools/zot_search.py")` decorator
- [x] 4.1.3 Implement file read from `src/agent_zot/mcp_tools/zot_search.py`
- [x] 4.1.4 Add error handling for file not found
- [x] 4.1.5 Test: Verify resource returns correct file contents

### 4.2 Add resource for zot_summarize
- [x] 4.2.1 Create resource handler function in server.py
- [x] 4.2.2 Add `@mcp.resource("agent-zot://tools/zot_summarize.py")` decorator
- [x] 4.2.3 Implement file read from `src/agent_zot/mcp_tools/zot_summarize.py`
- [x] 4.2.4 Add error handling for file not found
- [x] 4.2.5 Test: Verify resource returns correct file contents

### 4.3 Add resource for zot_explore_graph
- [x] 4.3.1 Create resource handler function in server.py
- [x] 4.3.2 Add `@mcp.resource("agent-zot://tools/zot_explore_graph.py")` decorator
- [x] 4.3.3 Implement file read from `src/agent_zot/mcp_tools/zot_explore_graph.py`
- [x] 4.3.4 Add error handling for file not found
- [x] 4.3.5 Test: Verify resource returns correct file contents

### 4.4 Add resource for zot_manage_collections
- [x] 4.4.1 Create resource handler function in server.py
- [x] 4.4.2 Add `@mcp.resource("agent-zot://tools/zot_manage_collections.py")` decorator
- [x] 4.4.3 Implement file read from `src/agent_zot/mcp_tools/zot_manage_collections.py`
- [x] 4.4.4 Add error handling for file not found
- [x] 4.4.5 Test: Verify resource returns correct file contents

### 4.5 Add resource for zot_manage_tags
- [x] 4.5.1 Create resource handler function in server.py
- [x] 4.5.2 Add `@mcp.resource("agent-zot://tools/zot_manage_tags.py")` decorator
- [x] 4.5.3 Implement file read from `src/agent_zot/mcp_tools/zot_manage_tags.py`
- [x] 4.5.4 Add error handling for file not found
- [x] 4.5.5 Test: Verify resource returns correct file contents

### 4.6 Add resource for zot_manage_notes
- [x] 4.6.1 Create resource handler function in server.py
- [x] 4.6.2 Add `@mcp.resource("agent-zot://tools/zot_manage_notes.py")` decorator
- [x] 4.6.3 Implement file read from `src/agent_zot/mcp_tools/zot_manage_notes.py`
- [x] 4.6.4 Add error handling for file not found
- [x] 4.6.5 Test: Verify resource returns correct file contents

### 4.7 Add resource for zot_export
- [x] 4.7.1 Create resource handler function in server.py
- [x] 4.7.2 Add `@mcp.resource("agent-zot://tools/zot_export.py")` decorator
- [x] 4.7.3 Implement file read from `src/agent_zot/mcp_tools/zot_export.py`
- [x] 4.7.4 Add error handling for file not found
- [x] 4.7.5 Test: Verify resource returns correct file contents

### 4.8 Add resource for zot_manage_database
- [x] 4.8.1 Create resource handler function in server.py
- [x] 4.8.2 Add `@mcp.resource("agent-zot://tools/zot_manage_database.py")` decorator
- [x] 4.8.3 Implement file read from `src/agent_zot/mcp_tools/zot_manage_database.py`
- [x] 4.8.4 Add error handling for file not found
- [x] 4.8.5 Test: Verify resource returns correct file contents

## 5. Remove MCP Tool Decorators (Breaking Change)

> **Execution:** SEQUENTIAL
> **Dependencies:** Section 4 complete

### 5.1 Remove zot_search tool
- [ ] 5.1.1 Locate zot_search `@mcp.tool()` decorator in server.py
- [ ] 5.1.2 Remove `@mcp.tool()` decorator
- [ ] 5.1.3 Remove zot_search function definition
- [ ] 5.1.4 Test: Verify zot_search not in MCP tool registry

### 5.2 Remove zot_summarize tool
- [ ] 5.2.1 Locate zot_summarize `@mcp.tool()` decorator in server.py
- [ ] 5.2.2 Remove `@mcp.tool()` decorator
- [ ] 5.2.3 Remove zot_summarize function definition
- [ ] 5.2.4 Test: Verify zot_summarize not in MCP tool registry

### 5.3 Remove zot_explore_graph tool
- [ ] 5.3.1 Locate zot_explore_graph `@mcp.tool()` decorator in server.py
- [ ] 5.3.2 Remove `@mcp.tool()` decorator
- [ ] 5.3.3 Remove zot_explore_graph function definition
- [ ] 5.3.4 Test: Verify zot_explore_graph not in MCP tool registry

### 5.4 Remove zot_manage_collections tool
- [ ] 5.4.1 Locate zot_manage_collections `@mcp.tool()` decorator in server.py
- [ ] 5.4.2 Remove `@mcp.tool()` decorator
- [ ] 5.4.3 Remove zot_manage_collections function definition
- [ ] 5.4.4 Test: Verify zot_manage_collections not in MCP tool registry

### 5.5 Remove zot_manage_tags tool
- [ ] 5.5.1 Locate zot_manage_tags `@mcp.tool()` decorator in server.py
- [ ] 5.5.2 Remove `@mcp.tool()` decorator
- [ ] 5.5.3 Remove zot_manage_tags function definition
- [ ] 5.5.4 Test: Verify zot_manage_tags not in MCP tool registry

### 5.6 Remove zot_manage_notes tool
- [ ] 5.6.1 Locate zot_manage_notes `@mcp.tool()` decorator in server.py
- [ ] 5.6.2 Remove `@mcp.tool()` decorator
- [ ] 5.6.3 Remove zot_manage_notes function definition
- [ ] 5.6.4 Test: Verify zot_manage_notes not in MCP tool registry

### 5.7 Remove zot_export tool
- [ ] 5.7.1 Locate zot_export `@mcp.tool()` decorator in server.py
- [ ] 5.7.2 Remove `@mcp.tool()` decorator
- [ ] 5.7.3 Remove zot_export function definition
- [ ] 5.7.4 Test: Verify zot_export not in MCP tool registry

### 5.8 Remove zot_manage_database tool
- [ ] 5.8.1 Locate zot_manage_database `@mcp.tool()` decorator in server.py
- [ ] 5.8.2 Remove `@mcp.tool()` decorator
- [ ] 5.8.3 Remove zot_manage_database function definition
- [ ] 5.8.4 Test: Verify zot_manage_database not in MCP tool registry

### 5.9 Verify complete tool removal
- [ ] 5.9.1 Check server.py has no remaining `@mcp.tool()` decorators
- [ ] 5.9.2 Restart MCP server
- [ ] 5.9.3 Verify NO tools appear in MCP tool registry
- [ ] 5.9.4 Test: Tool calls fail with clear error message

## 6. Create Agent-Zot-Research Skill

> **Execution:** SEQUENTIAL
> **Dependencies:** Section 5 complete

### 6.1 Scaffold skill structure
- [ ] 6.1.1 Create directory: `~/.claude/skills/agent-zot-research/`
- [ ] 6.1.2 Create `SKILL.md` file with header
- [ ] 6.1.3 Add skill metadata (purpose, when to activate)

### 6.2 Document code execution pattern
- [ ] 6.2.1 Write "How to Use Code Execution Pattern" section
- [ ] 6.2.2 Document import pattern: `from agent_zot.mcp_tools.* import *`
- [ ] 6.2.3 Add basic usage example (search → filter)
- [ ] 6.2.4 Document resource URI pattern for reference

### 6.3 Add migration guide
- [ ] 6.3.1 Write "Migrating from v2.1 Tool Pattern" section
- [ ] 6.3.2 Add before/after code example for simple search
- [ ] 6.3.3 Add before/after code example for search + filter
- [ ] 6.3.4 Document breaking change and rollback procedure

### 6.4 Document common patterns
- [ ] 6.4.1 Add "search → filter → summarize" workflow example
- [ ] 6.4.2 Add "batch processing" workflow example
- [ ] 6.4.3 Add "complex filtering with multiple conditions" example
- [ ] 6.4.4 Add "combining multiple tools" example

### 6.5 Add token optimization guidance
- [ ] 6.5.1 Write "Token Cost Comparison" section
- [ ] 6.5.2 Add calculation example: 100 papers @ 800 tokens each
- [ ] 6.5.3 Show before (80k tokens) vs after (2k tokens) comparison
- [ ] 6.5.4 Explain when token savings are most significant

### 6.6 Add troubleshooting guide
- [ ] 6.6.1 Document "ImportError: No module named agent_zot" fix
- [ ] 6.6.2 Document environment setup requirements
- [ ] 6.6.3 Add "Module not found" common issue resolution
- [ ] 6.6.4 Add verification commands for testing imports

## 7. Update Documentation

> **Execution:** SEQUENTIAL
> **Dependencies:** Section 6 complete

### 7.1 Update README.md
- [ ] 7.1.1 Add breaking change banner at top of README.md
- [ ] 7.1.2 Add "⚠️ Breaking Change in v2.2" section
- [ ] 7.1.3 Remove old MCP tool call examples
- [ ] 7.1.4 Add "Quick Start with Code Execution" section
- [ ] 7.1.5 Add basic import example
- [ ] 7.1.6 Add search + filter workflow example

### 7.2 Document resource pattern
- [ ] 7.2.1 Create "Resource Access" section in README.md
- [ ] 7.2.2 Document resource URI pattern: `agent-zot://tools/<name>.py`
- [ ] 7.2.3 List all 8 available resources
- [ ] 7.2.4 Explain resource vs tool distinction

### 7.3 Add token cost comparison
- [ ] 7.3.1 Create "Token Optimization" section in README.md
- [ ] 7.3.2 Show concrete before/after example
- [ ] 7.3.3 Add token cost table: v2.1 vs v2.2
- [ ] 7.3.4 Explain when savings are most significant

### 7.4 Document migration
- [ ] 7.4.1 Create "Migration Guide" section in README.md
- [ ] 7.4.2 Document rollback procedure (git tag v2.1-pre-code-execution)
- [ ] 7.4.3 Add step-by-step migration instructions
- [ ] 7.4.4 Link to agent-zot-research skill for detailed guidance
- [ ] 7.4.5 Link to comprehensive guide in PAI notes

## 8. Testing & Validation

> **Execution:** SEQUENTIAL
> **Dependencies:** Section 7 complete

### 8.1 Test resource access
- [ ] 8.1.1 Test zot_search resource returns valid Python code
- [ ] 8.1.2 Test zot_summarize resource returns valid Python code
- [ ] 8.1.3 Test zot_explore_graph resource returns valid Python code
- [ ] 8.1.4 Test zot_manage_collections resource returns valid Python code
- [ ] 8.1.5 Test zot_manage_tags resource returns valid Python code
- [ ] 8.1.6 Test zot_manage_notes resource returns valid Python code
- [ ] 8.1.7 Test zot_export resource returns valid Python code
- [ ] 8.1.8 Test zot_manage_database resource returns valid Python code
- [ ] 8.1.9 Verify all resources appear in resource list

### 8.2 Test code execution workflows
- [ ] 8.2.1 Test: Import zot_search and execute basic search
- [ ] 8.2.2 Test: Search → filter by year
- [ ] 8.2.3 Test: Search → filter → summarize workflow
- [ ] 8.2.4 Test: Multiple tool combination (search + explore_graph)
- [ ] 8.2.5 Test: Batch processing with multiple queries
- [ ] 8.2.6 Verify all imports work correctly

### 8.3 Verify breaking change
- [ ] 8.3.1 Attempt to call zot_search via MCP protocol (should fail)
- [ ] 8.3.2 Verify error message is clear and helpful
- [ ] 8.3.3 Verify error directs to code execution pattern
- [ ] 8.3.4 Test all 8 tools fail when called via MCP
- [ ] 8.3.5 Verify NO tools appear in MCP tool registry

### 8.4 Compare token usage
- [ ] 8.4.1 Measure tokens: v2.1 search for 100 papers
- [ ] 8.4.2 Measure tokens: v2.2 search + filter for 100 papers
- [ ] 8.4.3 Calculate % reduction
- [ ] 8.4.4 Document actual savings achieved
- [ ] 8.4.5 Verify 95-98% reduction for large datasets

### 8.5 Validate skill guidance
- [ ] 8.5.1 Follow agent-zot-research skill migration guide
- [ ] 8.5.2 Verify all examples in skill work correctly
- [ ] 8.5.3 Test troubleshooting steps resolve common issues
- [ ] 8.5.4 Verify before/after code examples are accurate

## 9. Quality Assurance

> **Execution:** SEQUENTIAL
> **Dependencies:** Section 8 complete

### 9.1 OpenSpec validation
- [ ] 9.1.1 Run `openspec validate add-mcp-code-execution --strict`
- [ ] 9.1.2 Resolve any validation errors
- [ ] 9.1.3 Verify all spec deltas are properly formatted
- [ ] 9.1.4 Verify all scenarios use correct WHEN/THEN/AND format

### 9.2 Git status check
- [ ] 9.2.1 Run `git status` and verify all changes intentional
- [ ] 9.2.2 Check for unintended file modifications
- [ ] 9.2.3 Verify no secrets or credentials in code
- [ ] 9.2.4 Review all diffs before committing

### 9.3 Rollback testing
- [ ] 9.3.1 Tag current state as `v2.2-code-execution-breaking`
- [ ] 9.3.2 Test checkout to `v2.1-pre-code-execution`
- [ ] 9.3.3 Verify v2.1 tools work correctly after rollback
- [ ] 9.3.4 Return to v2.2 and verify implementation
- [ ] 9.3.5 Document rollback procedure in README.md

### 9.4 Documentation review
- [ ] 9.4.1 Review all documentation for accuracy
- [ ] 9.4.2 Document any caveats or limitations discovered
- [ ] 9.4.3 Verify all links work correctly
- [ ] 9.4.4 Check for typos and formatting issues

### 9.5 Create examples
- [ ] 9.5.1 Create `examples/` directory in agent-zot
- [ ] 9.5.2 Add `basic_search.py` example
- [ ] 9.5.3 Add `search_and_filter.py` example
- [ ] 9.5.4 Add `batch_processing.py` example
- [ ] 9.5.5 Add `README.md` in examples/ explaining usage

## 10. Deployment

> **Execution:** SEQUENTIAL
> **Dependencies:** Section 9 complete

### 10.1 Commit and push changes
- [ ] 10.1.1 Stage all changes: `git add .`
- [ ] 10.1.2 Review staged changes one final time
- [ ] 10.1.3 Write comprehensive commit message (note breaking change)
- [ ] 10.1.4 Commit changes with proper attribution
- [ ] 10.1.5 Push to GitHub: `git push origin main`

### 10.2 Create git tags
- [ ] 10.2.1 Tag as `v2.2-code-execution-breaking`
- [ ] 10.2.2 Push tags to GitHub: `git push --tags`
- [ ] 10.2.3 Verify tags visible on GitHub
- [ ] 10.2.4 Document tag in CHANGELOG.md

### 10.3 Update CHANGELOG
- [ ] 10.3.1 Add v2.2-code-execution-breaking entry
- [ ] 10.3.2 Document breaking change clearly
- [ ] 10.3.3 List all major changes (8 tools → 8 resources)
- [ ] 10.3.4 Add migration guide section
- [ ] 10.3.5 Link to agent-zot-research skill
- [ ] 10.3.6 Commit and push CHANGELOG.md

### 10.4 Restart MCP server
- [ ] 10.4.1 Stop agent-zot MCP server
- [ ] 10.4.2 Restart agent-zot MCP server
- [ ] 10.4.3 Verify server starts without errors
- [ ] 10.4.4 Verify resources available (not tools)
- [ ] 10.4.5 Test resource access with sample query

### 10.5 Migrate workflows
- [ ] 10.5.1 Identify all existing workflows using agent-zot tools
- [ ] 10.5.2 Follow agent-zot-research skill for each workflow
- [ ] 10.5.3 Update workflow code to use imports instead of tool calls
- [ ] 10.5.4 Test each migrated workflow
- [ ] 10.5.5 Document any migration issues encountered

### 10.6 Monitor and iterate
- [ ] 10.6.1 Monitor for errors in first 24 hours
- [ ] 10.6.2 Address any urgent issues discovered
- [ ] 10.6.3 Document common issues in troubleshooting guide
- [ ] 10.6.4 Iterate on skill guidance based on real usage
- [ ] 10.6.5 Archive OpenSpec change once stable
