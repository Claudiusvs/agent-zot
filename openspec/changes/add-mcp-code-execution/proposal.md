# Change: Add MCP Code Execution Pattern

## Why

Agent-zot currently exposes tools via MCP protocol where all data flows through Claude's context window. This creates significant token costs when processing large result sets (100+ papers can consume 80k-100k tokens).

**Problem**: When Claude searches for papers, filters results, and processes data, ALL intermediate data passes through its expensive context window, even data that will ultimately be filtered out.

**Opportunity**: Following Anthropic's MCP code execution pattern (https://www.anthropic.com/engineering/code-execution-with-mcp), we can replace callable MCP tools with importable code resources, enabling data processing in the execution environment before results enter Claude's context. This solves BOTH problems described in the article:
- **Problem 1**: Tool definition overload (8 tool descriptions consuming upfront tokens)
- **Problem 2**: Intermediate result bloat (data flowing through Claude's context unnecessarily)

**Impact**: 95-98% token reduction for workflows involving large datasets, plus elimination of upfront tool definition token costs.

## What Changes

This change implements Anthropic's MCP code execution pattern in agent-zot by:

1. **Replace MCP Tools with Resources**
   - Remove all `@mcp.tool()` decorators from server.py
   - Add `@mcp.resource()` decorators exposing tool implementations
   - Resources accessible via `agent-zot://tools/<tool-name>.py`
   - Implements filesystem-based resource discovery pattern

2. **Create `mcp_tools/` Directory**
   - New directory: `src/agent_zot/mcp_tools/`
   - Contains importable Python modules for each tool
   - Naming: Match tool names (e.g., `zot_search.py`, `zot_summarize.py`)
   - Same implementation as existing tools, packaged for import

3. **Create Agent-Zot-Research Skill**
   - New PAI skill: `~/.claude/skills/agent-zot-research/`
   - Teaches code execution pattern usage
   - Provides patterns for efficient filtering and processing
   - Includes example workflows and token optimization strategies
   - Documents migration from old tool-based pattern

4. **Update Documentation**
   - Document resource access pattern in README.md
   - Add code execution examples
   - Document breaking change and migration guide
   - Update all usage examples

**BREAKING CHANGE**: Tools are no longer callable via MCP protocol. All workflows must migrate to code execution pattern. Git tag `v2.1-pre-code-execution` available for rollback.

## Impact

### Affected Capabilities
- **mcp-server**: Replace tool pattern with resource-based code execution pattern

### Affected Code
- `src/agent_zot/core/server.py` - Remove `@mcp.tool()` decorators, add `@mcp.resource()` decorators
- `src/agent_zot/mcp_tools/` - New directory with importable tool modules
- `README.md` - Update with code execution documentation and migration guide
- `~/.claude/skills/agent-zot-research/` - New skill (PAI repository)

### User-Facing Changes
- **BREAKING**: Tools no longer callable via `mcp__agent-zot__zot_search()` pattern
- New resource URIs: `agent-zot://tools/<tool-name>.py`
- New usage pattern: Import and execute tools in scripts
- Token cost reduction: 95-98% for large dataset workflows
- Elimination of upfront tool definition token costs

### Migration Path
- **Phase 1**: Review workflows using agent-zot tools
- **Phase 2**: Deploy new version with resource-only pattern
- **Phase 3**: Migrate workflows to code execution pattern using agent-zot-research skill guidance
- **Phase 4**: Validate all workflows function correctly
- **Rollback available**: Git tag `v2.1-pre-code-execution` for instant rollback

### Risk Assessment
- **Medium risk**: Breaking change, but controlled deployment
- **Rollback**: Git tag `v2.1-pre-code-execution` for instant rollback
- **Testing**: Validate resource access and code execution patterns work
- **Migration support**: Comprehensive skill provides migration guidance

## Reference
- Implementation guide: `~/toolboxes/PAI/notes/mcp-code-execution-optimization-guide.md`
- Anthropic article: https://www.anthropic.com/engineering/code-execution-with-mcp
- Git rollback tag: `v2.1-pre-code-execution`
