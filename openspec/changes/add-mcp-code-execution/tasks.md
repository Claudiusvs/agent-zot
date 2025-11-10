# Implementation Tasks

## 1. Preparation
- [ ] 1.1 Review current MCP tool implementations in `src/agent_zot/core/server.py`
- [ ] 1.2 Identify all active tools (zot_search, zot_summarize, zot_explore_graph, zot_manage_*)
- [ ] 1.3 Document tool import dependencies and required modules

## 2. Create Tools Directory Structure
- [ ] 2.1 Create directory: `src/agent_zot/mcp_tools/`
- [ ] 2.2 Create `__init__.py` with tool exports
- [ ] 2.3 Add directory to Python package structure

## 3. Extract Tool Implementations
- [ ] 3.1 Extract `zot_search` implementation to `mcp_tools/zot_search.py`
- [ ] 3.2 Extract `zot_summarize` implementation to `mcp_tools/zot_summarize.py`
- [ ] 3.3 Extract `zot_explore_graph` implementation to `mcp_tools/zot_explore_graph.py`
- [ ] 3.4 Extract `zot_manage_collections` implementation to `mcp_tools/zot_manage_collections.py`
- [ ] 3.5 Extract `zot_manage_tags` implementation to `mcp_tools/zot_manage_tags.py`
- [ ] 3.6 Extract `zot_manage_notes` implementation to `mcp_tools/zot_manage_notes.py`
- [ ] 3.7 Extract `zot_export` implementation to `mcp_tools/zot_export.py`
- [ ] 3.8 Extract `zot_manage_database` implementation to `mcp_tools/zot_manage_database.py`

## 4. Add MCP Resource Decorators and Remove Tool Decorators
- [ ] 4.1 Add `@mcp.resource()` decorator for `zot_search` tool code
- [ ] 4.2 Add `@mcp.resource()` decorator for `zot_summarize` tool code
- [ ] 4.3 Add `@mcp.resource()` decorator for `zot_explore_graph` tool code
- [ ] 4.4 Add `@mcp.resource()` decorator for `zot_manage_collections` tool code
- [ ] 4.5 Add `@mcp.resource()` decorator for `zot_manage_tags` tool code
- [ ] 4.6 Add `@mcp.resource()` decorator for `zot_manage_notes` tool code
- [ ] 4.7 Add `@mcp.resource()` decorator for `zot_export` tool code
- [ ] 4.8 Add `@mcp.resource()` decorator for `zot_manage_database` tool code

## 5. Remove MCP Tool Decorators (Breaking Change)
- [ ] 5.1 Remove all `@mcp.tool()` decorators from server.py
- [ ] 5.2 Update server initialization to remove tool registration
- [ ] 5.3 Verify tools no longer appear in MCP tool registry
- [ ] 5.4 Test that tool calls fail with appropriate error message

## 6. Create Agent-Zot-Research Skill
- [ ] 6.1 Create skill directory: `~/.claude/skills/agent-zot-research/`
- [ ] 6.2 Write `SKILL.md` with workflow guidance
- [ ] 6.3 Document code execution pattern usage and migration from old tool pattern
- [ ] 6.4 Provide filtering and processing patterns
- [ ] 6.5 Include token optimization examples
- [ ] 6.6 Add migration guide with before/after code examples
- [ ] 6.7 Add troubleshooting guide

## 7. Update Documentation
- [ ] 7.1 Update `README.md` with breaking change notice
- [ ] 7.2 Add code execution examples
- [ ] 7.3 Document resource URI pattern: `agent-zot://tools/<name>.py`
- [ ] 7.4 Add token cost comparison: before (tool calls) vs after (code execution)
- [ ] 7.5 Document migration path from v2.1-pre-code-execution
- [ ] 7.6 Link to comprehensive guide in PAI notes

## 8. Testing & Validation
- [ ] 8.1 Test resource access for all 8 tools
- [ ] 8.2 Test search → filter → summarize workflow via code execution
- [ ] 8.3 Verify tools are NOT callable via MCP protocol (expected behavior)
- [ ] 8.4 Verify error messages direct to code execution pattern
- [ ] 8.5 Compare token usage: v2.1 (tool calls) vs v2.2 (code execution)
- [ ] 8.6 Test with various tool combinations in code execution
- [ ] 8.7 Validate skill migration guidance is accurate

## 9. Quality Assurance
- [ ] 9.1 Run `openspec validate add-mcp-code-execution --strict`
- [ ] 9.2 Verify git status clean (no unintended changes)
- [ ] 9.3 Test rollback to `v2.1-pre-code-execution` tag
- [ ] 9.4 Document any caveats or limitations
- [ ] 9.5 Create examples directory with sample workflows

## 10. Deployment
- [ ] 10.1 Commit changes to agent-zot with descriptive message (note breaking change)
- [ ] 10.2 Push to GitHub repository
- [ ] 10.3 Tag as `v2.2-code-execution-breaking`
- [ ] 10.4 Update CHANGELOG.md with breaking change notice and migration guide
- [ ] 10.5 Restart MCP server to load new resource-only pattern
- [ ] 10.6 Migrate existing workflows using agent-zot-research skill
- [ ] 10.7 Monitor initial usage and address issues
