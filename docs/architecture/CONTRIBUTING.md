# Contributing to Agent-Zot

Thank you for your interest in contributing to Agent-Zot! This document provides guidelines and best practices for contributors.

## Quick Start

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Run tests: `pytest tests/`
5. Commit with conventional commits: `git commit -m "feat: add new feature"`
6. Push and create pull request

## Development Setup

### Prerequisites
- Python 3.12+
- Docker (for Qdrant and Neo4j)
- Git
- Virtual environment tool (venv, conda, etc.)

### Installation

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/agent-zot.git
cd agent-zot

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e .

# Install development dependencies
pip install pytest black flake8 mypy

# Start required services
docker-compose up -d  # (if available)
# OR manually start Qdrant and Neo4j
```

### Configuration

```bash
# Copy example config
cp config_examples/config_qdrant.json ~/.config/agent-zot/config.json

# Edit with your settings
nano ~/.config/agent-zot/config.json
```

## Code Style

### Python Style Guide
- **PEP 8** compliance (use `black` for formatting)
- **Type hints** for all function signatures
- **Docstrings** for public functions (Google style)
- **Line length:** 120 characters max

### Example:
```python
from typing import List, Dict, Optional

def process_items(
    items: List[str],
    limit: Optional[int] = None,
    *,
    include_metadata: bool = False
) -> Dict[str, any]:
    """
    Process a list of items and return metadata.

    Args:
        items: List of item keys to process
        limit: Maximum number of items to process (optional)
        include_metadata: Whether to include full metadata (default: False)

    Returns:
        Dictionary with processing results

    Raises:
        ValueError: If items list is empty
    """
    if not items:
        raise ValueError("Items list cannot be empty")

    # Implementation
    ...
```

### Formatting Tools

```bash
# Format code with black
black src/

# Check style with flake8
flake8 src/

# Type check with mypy
mypy src/agent_zot/
```

## Commit Guidelines

### Conventional Commits

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

#### Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring (no feature/bug change)
- `perf`: Performance improvements
- `test`: Test additions or changes
- `chore`: Build process, dependencies, etc.

#### Examples:
```bash
# Feature
git commit -m "feat(search): add query decomposition for complex queries"

# Bug fix
git commit -m "fix(parser): handle corrupted PDFs gracefully"

# Documentation
git commit -m "docs: update configuration guide with Neo4j setup"

# Performance
git commit -m "perf(qdrant): increase batch size to 500 for 5x speedup"
```

### Good Commit Messages

**Good:**
```
feat(mcp): add zot_ask_paper tool for Q&A over papers

- Semantic search to find relevant chunks
- Returns source text, not AI-generated answers
- Includes relevance scores and context
- Closes #123
```

**Bad:**
```
fix stuff
```

```
added new feature
```

## Pull Request Process

### Before Submitting

1. **Test your changes:**
   ```bash
   pytest tests/
   ```

2. **Format code:**
   ```bash
   black src/ tests/
   flake8 src/ tests/
   ```

3. **Update documentation:**
   - Add docstrings to new functions
   - Update `docs/` if adding features
   - Update `README.md` if changing setup

4. **Write tests:**
   - Add unit tests for new functions
   - Add integration tests for MCP tools
   - Aim for 80%+ coverage

### PR Title Format

Use conventional commit format:

```
feat(search): implement query refinement with iterative improvement
fix(neo4j): resolve entity resolution merge conflicts
docs: add architecture diagram to ARCHITECTURE.md
```

### PR Description Template

```markdown
## Description
Brief description of changes

## Motivation
Why is this change needed?

## Changes Made
- Bullet list of changes
- Another change

## Testing
How was this tested?

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Code formatted with black
- [ ] Type hints added
- [ ] Changelog updated (if applicable)

## Related Issues
Closes #123
```

## Testing Guidelines

### Unit Tests

**Location:** `tests/unit/`

**Example:**
```python
# tests/unit/test_semantic.py
import pytest
from agent_zot.search.semantic import SemanticSearch

def test_create_semantic_search():
    """Test SemanticSearch initialization."""
    search = SemanticSearch()
    assert search is not None

def test_search_with_empty_query():
    """Test search raises error on empty query."""
    search = SemanticSearch()
    with pytest.raises(ValueError):
        search.search(query="")
```

### Integration Tests

**Location:** `tests/integration/`

**Example:**
```python
# tests/integration/test_mcp_tools.py
import pytest
from agent_zot.core.server import mcp

@pytest.mark.integration
def test_zot_semantic_search():
    """Test semantic search tool end-to-end."""
    result = mcp.tools["zot_semantic_search"](
        query="cognitive control",
        limit=5
    )
    assert "Results:" in result
    assert len(result.split("\n")) >= 5
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_semantic.py

# Run with coverage
pytest --cov=agent_zot tests/

# Run integration tests only
pytest -m integration
```

## Adding New Features

### 1. MCP Tools

**Steps:**
1. Add tool definition in `src/agent_zot/core/server.py`
2. Implement logic in appropriate module
3. Add tests in `tests/integration/test_mcp_tools.py`
4. Update `docs/guides/QUICK_REFERENCE.md`

**Template:**
```python
@mcp.tool(
    name="zot_my_new_tool",
    description="Clear description for LLM"
)
def my_new_tool(
    param: str,
    *,
    ctx: Context
) -> str:
    """
    Detailed docstring for developers.

    Args:
        param: Parameter description
        ctx: MCP context for logging

    Returns:
        Markdown-formatted results
    """
    try:
        ctx.info(f"Processing {param}")
        # Implementation
        return "# Results\n\nFormatted output"
    except Exception as e:
        ctx.error(f"Error: {e}")
        return f"Error: {e}"
```

### 2. Search Features

**Location:** `src/agent_zot/search/`

**Steps:**
1. Create new module: `src/agent_zot/search/your_feature.py`
2. Implement search logic
3. Integrate in `semantic.py`
4. Add configuration to `config.json`
5. Update documentation

### 3. PDF Parsers

**Location:** `src/agent_zot/parsers/`

**Interface:**
```python
from typing import List, Dict
from abc import ABC, abstractmethod

class BasePDFParser(ABC):
    @abstractmethod
    def parse_pdf(self, pdf_path: str) -> List[Dict[str, any]]:
        """
        Parse PDF and return chunks.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of chunk dictionaries with keys:
            - text: Chunk text
            - metadata: Chunk metadata (page, headings, etc.)
        """
        pass
```

## Documentation

### Code Documentation

- **Docstrings:** Use Google style
- **Type hints:** Required for all function signatures
- **Comments:** Explain "why", not "what"

### User Documentation

**Location:** `docs/guides/`

**Update when:**
- Adding new MCP tools
- Changing configuration options
- Adding new features
- Fixing bugs affecting users

### Developer Documentation

**Location:** `docs/development/`

**Update when:**
- Changing architecture
- Adding new modules
- Changing extension points
- Updating dependencies

## Code Review Process

### As a Reviewer

1. **Check functionality:** Does it work as intended?
2. **Review code quality:** Is it readable, maintainable?
3. **Verify tests:** Are there adequate tests?
4. **Check documentation:** Is it documented properly?
5. **Test locally:** Can you reproduce the results?

### As a Contributor

1. **Respond to feedback:** Address all review comments
2. **Ask questions:** Clarify unclear feedback
3. **Update PR:** Push fixes to same branch
4. **Be patient:** Reviews take time

## Project Structure

```
agent-zot/
├── src/agent_zot/          # Main package
│   ├── core/               # MCP server, CLI
│   ├── clients/            # External integrations
│   ├── parsers/            # PDF parsers
│   ├── database/           # Database access
│   ├── search/             # Search features
│   └── utils/              # Utilities
├── tests/                  # Test suite
│   ├── unit/               # Unit tests
│   └── integration/        # Integration tests
├── docs/                   # Documentation
│   ├── guides/             # User guides
│   ├── development/        # Developer docs
│   └── examples/           # Config examples
└── scripts/                # Utility scripts
    ├── migration/          # Migration scripts
    ├── maintenance/        # Maintenance scripts
    └── utilities/          # Utility scripts
```

## Release Process

### Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR:** Breaking changes
- **MINOR:** New features (backward-compatible)
- **PATCH:** Bug fixes (backward-compatible)

### Creating a Release

1. **Update version:** `src/agent_zot/_version.py`
2. **Update CHANGELOG:** Document all changes
3. **Create tag:** `git tag -a v1.2.0 -m "Release v1.2.0"`
4. **Push tag:** `git push origin v1.2.0`
5. **Create GitHub release:** Add release notes

## Community Guidelines

### Code of Conduct

- Be respectful and professional
- Welcome newcomers
- Provide constructive feedback
- Focus on the code, not the person

### Getting Help

- **Issues:** Search existing issues first
- **Discussions:** Use GitHub Discussions for questions
- **Pull Requests:** Ask for clarification if needed

### Reporting Bugs

**Use this template:**

```markdown
## Description
Clear description of the bug

## Steps to Reproduce
1. Step one
2. Step two
3. Error occurs

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: macOS 14.5
- Python: 3.12.0
- Agent-Zot: v1.0.0
- Qdrant: 1.7.0

## Logs
```
Paste relevant logs here
```
```

## Resources

- **Architecture:** [`docs/development/ARCHITECTURE.md`](./ARCHITECTURE.md)
- **Tool Hierarchy:** [`docs/development/TOOL_HIERARCHY.md`](./TOOL_HIERARCHY.md)
- **Configuration:** [`docs/guides/configuration.md`](../guides/configuration.md)
- **Quick Reference:** [`docs/guides/QUICK_REFERENCE.md`](../guides/QUICK_REFERENCE.md)

## Questions?

- Open a GitHub Discussion
- Check existing issues
- Review documentation

**Thank you for contributing to Agent-Zot!** 🚀
