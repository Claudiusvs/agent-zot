"""
Pytest configuration and fixtures for Agent-Zot tests.
"""

import pytest
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def mock_config_path(tmp_path):
    """Create a temporary config file for testing."""
    config = {
        "client_env": {
            "ZOTERO_LOCAL": "false",
            "ZOTERO_API_KEY": "test_api_key",
            "ZOTERO_LIBRARY_ID": "12345",
            "OPENAI_API_KEY": "test_openai_key"
        },
        "semantic_search": {
            "embedding_model": "openai",
            "openai_model": "text-embedding-3-large",
            "collection_name": "test_collection",
            "qdrant_url": "http://localhost:6333"
        }
    }

    config_file = tmp_path / "config.json"
    import json
    with open(config_file, 'w') as f:
        json.dump(config, f)

    return str(config_file)


@pytest.fixture
def mock_zotero_item():
    """Sample Zotero item for testing."""
    return {
        "key": "TEST123",
        "version": 1,
        "data": {
            "itemType": "journalArticle",
            "title": "Test Article on Machine Learning",
            "creators": [
                {"creatorType": "author", "firstName": "John", "lastName": "Doe"},
                {"creatorType": "author", "firstName": "Jane", "lastName": "Smith"}
            ],
            "abstractNote": "This is a test abstract about machine learning.",
            "date": "2024-01-15",
            "publicationTitle": "Journal of Test Science",
            "DOI": "10.1234/test.2024.001",
            "tags": [{"tag": "machine learning"}, {"tag": "testing"}],
            "url": "https://example.com/test-article"
        }
    }
