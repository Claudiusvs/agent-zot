"""
Smoke tests for Agent-Zot core functionality.

These tests verify that basic imports and module structure work correctly.
"""

import pytest


@pytest.mark.smoke
def test_imports():
    """Test that all core modules can be imported."""
    try:
        import client
        import docling_parser
        import neo4j_graphrag_client
        import qdrant_client_wrapper
        import semantic_search
        import server
        import utils
        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")


@pytest.mark.smoke
def test_client_functions_exist():
    """Test that client.py exports expected functions."""
    from client import (
        get_zotero_client,
        format_item_metadata,
        convert_to_markdown,
        generate_bibtex,
        format_creators
    )
    assert callable(get_zotero_client)
    assert callable(format_item_metadata)
    assert callable(convert_to_markdown)
    assert callable(generate_bibtex)
    assert callable(format_creators)


@pytest.mark.smoke
def test_qdrant_wrapper_class_exists():
    """Test that QdrantClientWrapper class is defined."""
    from qdrant_client_wrapper import QdrantClientWrapper
    assert QdrantClientWrapper is not None


@pytest.mark.smoke
def test_neo4j_client_class_exists():
    """Test that Neo4jGraphRAGClient class is defined."""
    from neo4j_graphrag_client import Neo4jGraphRAGClient
    assert Neo4jGraphRAGClient is not None


@pytest.mark.smoke
def test_docling_parser_class_exists():
    """Test that DoclingParser class is defined."""
    from docling_parser import DoclingParser
    assert DoclingParser is not None


@pytest.mark.smoke
def test_semantic_search_class_exists():
    """Test that SemanticSearch class is defined."""
    from semantic_search import SemanticSearch
    assert SemanticSearch is not None


@pytest.mark.smoke
def test_utils_format_creators(mock_zotero_item):
    """Test utils.format_creators with sample data."""
    from utils import format_creators

    creators = mock_zotero_item["data"]["creators"]
    result = format_creators(creators)

    assert "John Doe" in result
    assert "Jane Smith" in result


@pytest.mark.smoke
def test_bibtex_generation(mock_zotero_item):
    """Test BibTeX generation with sample item."""
    from client import generate_bibtex

    bibtex = generate_bibtex(mock_zotero_item)

    assert "@article" in bibtex
    assert "TEST123" in bibtex
    assert "Test Article on Machine Learning" in bibtex
    assert "Doe" in bibtex


@pytest.mark.smoke
def test_markdown_conversion(mock_zotero_item):
    """Test markdown conversion with sample item."""
    from client import convert_to_markdown

    markdown = convert_to_markdown(mock_zotero_item)

    assert "# Test Article on Machine Learning" in markdown
    assert "John Doe" in markdown or "Doe" in markdown
    assert "Journal of Test Science" in markdown


@pytest.mark.smoke
def test_server_mcp_instance_exists():
    """Test that FastMCP server instance is created."""
    from server import mcp
    assert mcp is not None
    assert hasattr(mcp, 'tool')
