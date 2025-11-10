# MCP Server Capability - Code Execution Pattern

## ADDED Requirements

### Requirement: Tool Code Exposure

The MCP server SHALL expose each tool's implementation as an importable resource, replacing the existing callable tool interface.

#### Scenario: Resource URI pattern
- **WHEN** a resource is requested with URI `agent-zot://tools/<tool-name>.py`
- **THEN** the server SHALL return the Python source code for that tool
- **AND** the code SHALL be importable and executable
- **AND** the code SHALL have identical signature and behavior to previous tool implementation

#### Scenario: Tools not callable via MCP protocol
- **WHEN** a tool is called via traditional MCP tool protocol (e.g., `mcp__agent-zot__zot_search()`)
- **THEN** the call SHALL fail (tool not found)
- **AND** error message SHALL indicate tools are now resource-based only
- **AND** error message SHALL provide migration guidance

#### Scenario: Available tools as resources
- **WHEN** the server is queried for available resources
- **THEN** it SHALL list all tools with URI pattern `agent-zot://tools/<name>.py`
- **AND** resources SHALL include: zot_search, zot_summarize, zot_explore_graph, zot_manage_collections, zot_manage_tags, zot_manage_notes, zot_export, zot_manage_database

### Requirement: Tool Module Structure

The MCP server SHALL provide tool implementations in a dedicated importable module structure at `src/agent_zot/mcp_tools/`.

#### Scenario: Module organization
- **WHEN** the tools directory is inspected
- **THEN** it SHALL contain one Python file per tool
- **AND** each file SHALL be named matching the tool name (e.g., `zot_search.py`)
- **AND** the directory SHALL have an `__init__.py` exporting all tools
- **AND** modules SHALL be importable as `from agent_zot.mcp_tools.zot_search import zot_search`

#### Scenario: Module implementation
- **WHEN** a tool module is imported
- **THEN** it SHALL provide a function with identical signature to the MCP tool
- **AND** the function SHALL call the same underlying implementation
- **AND** the function SHALL include docstrings with usage examples
- **AND** the function SHALL handle all parameters the tool accepts

#### Scenario: Consistent implementation
- **WHEN** a tool is imported and executed
- **THEN** it SHALL call identical underlying functions as previous tool implementation
- **AND** it SHALL produce identical results for same inputs
- **AND** behavior SHALL match previous tool behavior exactly

### Requirement: Resource Access Pattern

The MCP server SHALL implement resource access following MCP protocol standards for code retrieval.

#### Scenario: Resource request handling
- **WHEN** Claude requests resource `agent-zot://tools/zot_search.py`
- **THEN** the server SHALL read the file from `src/agent_zot/mcp_tools/zot_search.py`
- **AND** return the complete Python source code
- **AND** include proper error handling if file not found
- **AND** respond with appropriate MIME type for Python code

#### Scenario: Resource metadata
- **WHEN** resource metadata is queried
- **THEN** it SHALL include resource URI, description, and content type
- **AND** description SHALL explain the tool's purpose
- **AND** content type SHALL indicate Python source code

### Requirement: Token Efficiency Goal

The code execution pattern SHALL enable 95-98% token reduction for large dataset workflows compared to traditional tool calls.

#### Scenario: Large result set processing
- **WHEN** a workflow searches 100+ papers, filters results, and processes data
- **THEN** using code execution SHALL consume ≤5% of tokens compared to traditional tool calls
- **AND** filtering SHALL occur in execution environment, not Claude's context
- **AND** only final filtered results SHALL enter Claude's context

#### Scenario: Multi-step workflow optimization
- **WHEN** a workflow involves search → filter → summarize steps
- **THEN** code execution SHALL process all steps in execution environment
- **AND** intermediate results SHALL NOT enter Claude's context
- **AND** only final summary SHALL be returned to Claude

### Requirement: Usage Guidance

The system SHALL provide clear guidance on when to use code execution versus traditional tool calls.

#### Scenario: Decision criteria documentation
- **WHEN** users consult the agent-zot-research skill
- **THEN** it SHALL provide clear decision tree for choosing execution pattern
- **AND** explain token cost implications of each approach
- **AND** provide examples of optimal use cases for each pattern

#### Scenario: Code execution examples
- **WHEN** users reference documentation
- **THEN** it SHALL include working examples of code execution pattern
- **AND** demonstrate search → filter → summarize workflow
- **AND** show actual token cost comparisons
- **AND** provide troubleshooting guidance for common issues

#### Scenario: Import pattern guidance
- **WHEN** users attempt to use code execution
- **THEN** documentation SHALL show correct import statements
- **AND** explain environment requirements (agent-zot must be importable)
- **AND** provide fallback strategy if imports fail
- **AND** link to comprehensive setup guide

### Requirement: Error Handling

The code execution pattern SHALL handle errors gracefully and provide clear feedback.

#### Scenario: Import failure handling
- **WHEN** Claude attempts to import an agent-zot tool module
- **AND** the import fails (environment issue, missing dependencies)
- **THEN** error message SHALL suggest checking environment setup
- **AND** recommend fallback to traditional tool call
- **AND** provide link to troubleshooting documentation

#### Scenario: Resource not found
- **WHEN** a resource URI is requested that doesn't exist
- **THEN** the server SHALL return clear error message
- **AND** list available resource URIs
- **AND** suggest checking for typos in tool name

#### Scenario: Execution environment issues
- **WHEN** code execution fails due to environment constraints
- **THEN** error SHALL explain the specific issue (import path, dependencies, etc.)
- **AND** provide actionable resolution steps
- **AND** maintain stability of MCP server (no crashes)

## MODIFIED Requirements

None - tool functionality remains identical, only the access pattern changes.

## REMOVED Requirements

### Requirement: MCP Tool Interface (REMOVED)

The MCP server SHALL NO LONGER expose tools via `@mcp.tool()` decorators.

#### Rationale
- Eliminates upfront tool definition token costs (Problem 1 from Anthropic article)
- Simplifies architecture to single access pattern (resource-based only)
- Fully aligns with Anthropic's recommended code execution pattern
- Breaking change accepted: rollback available via git tag `v2.1-pre-code-execution`

#### Scenario: Tool calls no longer supported
- **WHEN** tools are called via traditional MCP protocol (e.g., `mcp__agent-zot__zot_search()`)
- **THEN** the call SHALL fail with clear error message
- **AND** error SHALL direct users to code execution pattern
- **AND** agent-zot-research skill SHALL provide migration guide

#### Scenario: All eight tools removed from MCP tool registry
- **WHEN** MCP server initializes
- **THEN** it SHALL NOT register any tools in MCP tool registry
- **AND** only resources SHALL be available
- **AND** resources SHALL include all 8 previous tools: zot_search, zot_summarize, zot_explore_graph, zot_manage_collections, zot_manage_tags, zot_manage_notes, zot_export, zot_manage_database
