# Technical Design: MCP Code Execution Pattern

## Context

Agent-zot currently exposes research tools via MCP protocol using `@mcp.tool()` decorators. This pattern works well but creates token inefficiency when workflows involve:
- Large result sets (100+ papers)
- Multi-step processing (search → filter → analyze)
- Data transformations before presenting to user

**Current token flow:**
```
Claude → zot_search(limit=100) → 100 papers (80k tokens) → Claude context
Claude filters manually → presents 5 papers
Total cost: 80k tokens
```

**Desired token flow:**
```
Claude writes script → imports zot_search → executes locally
Script filters 100 → 5 papers → returns to Claude
Total cost: 2-3k tokens (95-98% reduction)
```

## Goals / Non-Goals

### Goals
- ✅ Enable code execution pattern for agent-zot tools
- ✅ Eliminate upfront tool definition token costs (Problem 1)
- ✅ Eliminate intermediate result bloat (Problem 2)
- ✅ Achieve 95-98% token reduction for large dataset workflows
- ✅ Keep implementation simple and maintainable
- ✅ Fully align with Anthropic's recommended pattern

### Non-Goals
- ❌ Maintain backward compatibility with existing tool calls (breaking change accepted)
- ❌ Support dual-mode (tools + resources) architecture
- ❌ Change tool signatures or behavior
- ❌ Optimize for remote execution (assume local agent-zot)

## Decisions

### Decision 1: Pure Resource Pattern (Resources Only)

**Choice**: Replace all MCP tools with MCP resources (importable code only)

**Rationale**:
- **Solves both problems**: Eliminates upfront tool definition tokens (Problem 1) AND intermediate result bloat (Problem 2)
- **Cleaner architecture**: Single access pattern, no confusion about "which to use when"
- **Fully aligns with Anthropic article**: Implements the pattern exactly as recommended
- **Controlled deployment**: We control the MCP server, can manage migration
- **Future-proof**: As more MCP servers are added, every reduction in upfront token load helps
- **Simpler maintenance**: No dual-mode complexity, single code path

**Alternatives Considered**:
- **Option A**: Dual-mode (tools + resources)
  - ❌ Only solves Problem 2 (intermediate result bloat)
  - ❌ Doesn't eliminate upfront tool definition costs
  - ❌ More complex (two access patterns to maintain)
  - ❌ User confusion about which pattern to use when

- **Option B**: Create separate "code execution" tools
  - ❌ Duplicate implementations
  - ❌ Maintenance burden
  - ❌ Still doesn't solve Problem 1

- **Option C**: Selected - Pure resources (remove all tools)
  - ✅ Solves BOTH Problem 1 and Problem 2 completely
  - ✅ Cleaner, simpler architecture
  - ✅ Fully aligns with Anthropic's pattern
  - ✅ Git rollback available (v2.1-pre-code-execution)
  - ⚠️ Breaking change, but acceptable given benefits

### Decision 2: Tool Module Location

**Choice**: Create `src/agent_zot/mcp_tools/` directory for importable modules

**Rationale**:
- Clear naming: Distinguishes MCP-specific code from core logic
- Importable: Standard Python package structure
- Organized: Separates tool interface from implementation
- Discoverable: Easy to find all MCP tool implementations

**Structure**:
```python
src/agent_zot/
├── core/
│   └── server.py           # MCP server with @mcp.tool() and @mcp.resource()
├── mcp_tools/              # NEW: Importable tool implementations
│   ├── __init__.py         # Exports all tools
│   ├── zot_search.py       # Search tool implementation
│   ├── zot_summarize.py    # Summarize tool implementation
│   └── ...
├── search/                 # Existing: Core search logic
├── clients/                # Existing: Backend clients
└── utils/                  # Existing: Utilities
```

**Tool modules contain**:
- Function with same signature as MCP tool
- Same implementation logic
- Properly typed parameters
- Docstrings for guidance

**Example (`mcp_tools/zot_search.py`)**:
```python
"""
Importable implementation of zot_search tool.

Usage:
    from agent_zot.mcp_tools.zot_search import zot_search
    results = zot_search("attention mechanisms", limit=100)
    filtered = [r for r in results if r['year'] >= 2020]
"""

from typing import Dict, List, Optional
from agent_zot.search.unified_smart import unified_smart_search

def zot_search(
    query: str,
    limit: int = 10,
    force_mode: Optional[str] = None
) -> List[Dict]:
    """Search for papers with intelligent backend selection."""
    return unified_smart_search(query, limit, force_mode)
```

### Decision 3: Resource URI Pattern

**Choice**: Use `agent-zot://tools/<tool-name>.py` URI pattern

**Rationale**:
- Follows MCP resource conventions
- Clear namespace (`agent-zot://`)
- Descriptive path (`tools/`)
- File extension indicates Python code (`.py`)
- Consistent with tool names

**Examples**:
```
agent-zot://tools/zot_search.py
agent-zot://tools/zot_summarize.py
agent-zot://tools/zot_explore_graph.py
```

**MCP Server Implementation**:
```python
@mcp.resource("agent-zot://tools/zot_search.py")
def get_zot_search_code():
    """Returns zot_search tool as importable Python code."""
    return open("src/agent_zot/mcp_tools/zot_search.py").read()
```

### Decision 4: Skill-Based Guidance

**Choice**: Create `agent-zot-research` skill to teach code execution pattern

**Rationale**:
- Users need guidance on the new code execution pattern
- Skill provides migration guidance from old tool-based pattern
- Examples demonstrate token savings
- Reduces support burden (self-documenting)

**Skill location**: `~/.claude/skills/agent-zot-research/SKILL.md`

**Skill teaches**:
- How to use code execution pattern with agent-zot
- Importing and executing tools in scripts
- Common patterns (search → filter, batch processing)
- Token cost comparisons vs old tool pattern
- Migration guide from tool-based workflows
- Troubleshooting tips

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│ Claude Code Execution Environment                       │
│                                                         │
│             ┌──────────────────────┐                   │
│             │ Code Execution Path  │                   │
│             │                      │                   │
│             │ from agent_zot.mcp_  │                   │
│             │   tools.zot_search   │                   │
│             │   import zot_search  │                   │
│             │                      │                   │
│             │ results = zot_search │                   │
│             │   ("query", limit=100│                   │
│             │                      │                   │
│             │ # Filter locally     │                   │
│             │ filtered = [r for r  │                   │
│             │   in results if      │                   │
│             │   r['year'] >= 2020] │                   │
│             │                      │                   │
│             │ return filtered      │                   │
│             │ # Only 5 papers      │                   │
│             │ # (2k tokens)        │                   │
│             └──────────┬───────────┘                   │
│                        ↓                               │
│             ┌────────────────────┐                    │
│             │ Agent-Zot MCP      │                    │
│             │ Server             │                    │
│             │                    │                    │
│             │ @mcp.resource()    │                    │
│             │ "agent-zot://tools │                    │
│             │  /zot_search.py"   │                    │
│             │                    │                    │
│             │ Returns:           │                    │
│             │ src/agent_zot/mcp_ │                    │
│             │   tools/zot_search │                    │
│             │   .py source code  │                    │
│             └────────────────────┘                    │
│                        ↓                               │
│             ┌────────────────────┐                    │
│             │ Core Implementation│                    │
│             │ unified_smart_     │                    │
│             │ search()           │                    │
│             └────────────────────┘                    │
│                                                         │
│ Note: No @mcp.tool() decorators - tools not callable   │
│ via MCP protocol. All access via code execution only.  │
└─────────────────────────────────────────────────────────┘
```

## Risks / Trade-offs

### Risk 1: Breaking Change Migration
**Risk**: Existing workflows break when tools no longer callable
**Mitigation**:
- Git tag v2.1-pre-code-execution available for instant rollback
- Comprehensive migration guide in agent-zot-research skill
- Clear documentation of breaking change
- Controlled deployment (we control the MCP server)

### Risk 2: Import Path Complexity
**Risk**: Users might struggle with correct import paths
**Mitigation**:
- Clear examples in skill documentation
- Standardized import pattern in all examples
- Error messages with import suggestions

### Risk 3: Environment Dependencies
**Risk**: Code execution requires agent-zot importable in environment
**Mitigation**:
- Document environment setup requirements
- Skill checks for import errors and suggests fixes
- Clear troubleshooting guide

### Risk 4: Learning Curve
**Risk**: Users need to learn new pattern
**Mitigation**:
- agent-zot-research skill provides comprehensive guidance
- Documentation includes clear examples
- Migration guide shows before/after code

## Trade-offs

**Breaking Change Accepted:**
- ✅ Solves both Problem 1 (tool definition overload) and Problem 2 (intermediate result bloat)
- ✅ Cleaner architecture (single pattern, no dual-mode complexity)
- ✅ Fully aligns with Anthropic's recommended approach
- ✅ Future-proof for multi-MCP-server environments
- ⚠️ Requires workflow migration (but migration guide provided)
- ⚠️ Slightly more complex than simple tool calls (but dramatically better token efficiency)

**Code Execution Pattern Benefits:**
- **Token cost**: 95-98% reduction for large dataset workflows
- **Flexibility**: Full control over data processing and filtering
- **No upfront cost**: Tool definitions no longer consume tokens at session start
- **Best for**: Any workflow involving filtering, transformation, or multi-step processing

## Migration Plan

### Phase 1: Implementation
1. Create `mcp_tools/` directory with importable tool modules
2. Add `@mcp.resource()` decorators to server.py
3. Remove all `@mcp.tool()` decorators
4. Update server initialization

### Phase 2: Documentation
1. Create agent-zot-research skill with migration guide
2. Update README.md with breaking change notice
3. Add code execution examples
4. Document token savings and migration path

### Phase 3: Testing
1. Test resource access (new pattern)
2. Test code execution workflows
3. Verify tools no longer callable via MCP (expected)
4. Compare token usage before/after
5. Validate error handling

### Phase 4: Rollout
1. Commit and push changes
2. Tag `v2.2-code-execution-breaking`
3. Restart MCP server
4. Migrate existing workflows using agent-zot-research skill

### Rollback Plan
If issues arise:
1. `git checkout v2.1-pre-code-execution`
2. Restart MCP server
3. Verify tools work as before (traditional callable pattern restored)

**Rollback impact**: Clean rollback to previous working state, no data loss

## Open Questions

1. **Q**: Should we expose all tools as resources or just the high-traffic ones?
   **A**: Start with all 8 unified tools for consistency. Can deprecate unused ones later.

2. **Q**: Do we need telemetry to track usage patterns?
   **A**: Out of scope for initial implementation. Can add later if needed.

3. **Q**: Should the skill be agent-specific or general MCP pattern?
   **A**: Agent-zot-specific initially. Can extract general patterns later.

4. **Q**: How do we handle tool updates? Do resources auto-update?
   **A**: Resources return current code from filesystem. Updates are automatic.

## Success Metrics

**Post-implementation, we should see:**
- ✅ Zero regression in existing tool functionality
- ✅ 95-98% token reduction in large dataset workflows (measured)
- ✅ Clear documentation and examples accessible
- ✅ Positive user feedback on token savings
- ✅ No increase in support requests

**Monitoring approach:**
- Compare token usage before/after for same workflows
- Track adoption via skill usage patterns
- Collect user feedback on documentation clarity
- Measure support ticket volume

## References

- Anthropic article: https://www.anthropic.com/engineering/code-execution-with-mcp
- Implementation guide: `~/toolboxes/PAI/notes/mcp-code-execution-optimization-guide.md`
- Git rollback tag: `v2.1-pre-code-execution`
