"""
Unit tests for GraphitiClient.

Tests verify error handling, logging, and graceful degradation when
Graphiti MCP server is available or unavailable.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from agent_zot.clients.graphiti_client import (
    GraphitiClient,
    GraphitiClientError,
    GraphitiUnavailableError,
    EntityNode,
    RelationshipFact,
)


@pytest.fixture
def mock_mcp_tool_caller():
    """Mock MCP tool caller for testing."""
    return Mock()


@pytest.fixture
def graphiti_client(mock_mcp_tool_caller):
    """Create GraphitiClient instance with mocked MCP tool caller."""
    return GraphitiClient(
        group_id="test-group",
        mcp_timeout_seconds=5,
        mcp_tool_caller=mock_mcp_tool_caller,
    )


@pytest.mark.unit
def test_graphiti_client_initialization():
    """Test GraphitiClient initialization with defaults."""
    client = GraphitiClient()

    assert client.group_id == "agent-zot-discovery"
    assert client.timeout == 10
    assert client._available is None


@pytest.mark.unit
def test_graphiti_client_custom_config():
    """Test GraphitiClient initialization with custom config."""
    client = GraphitiClient(
        group_id="custom-group",
        mcp_timeout_seconds=30,
    )

    assert client.group_id == "custom-group"
    assert client.timeout == 30


@pytest.mark.unit
def test_is_available_success(graphiti_client, mock_mcp_tool_caller):
    """Test is_available when Graphiti server is responding."""
    # Mock successful MCP call
    mock_mcp_tool_caller.return_value = {"nodes": []}

    result = graphiti_client.is_available()

    assert result is True
    assert graphiti_client._available is True
    mock_mcp_tool_caller.assert_called_once()


@pytest.mark.unit
def test_is_available_failure(graphiti_client, mock_mcp_tool_caller):
    """Test is_available when Graphiti server is unavailable."""
    # Mock failed MCP call
    mock_mcp_tool_caller.side_effect = Exception("Connection refused")

    result = graphiti_client.is_available()

    assert result is False
    assert graphiti_client._available is False


@pytest.mark.unit
def test_is_available_cached(graphiti_client):
    """Test that is_available caches result."""
    # Set cached availability
    graphiti_client._available = True

    # Should not call MCP tool
    result = graphiti_client.is_available()

    assert result is True
    # MCP tool caller should not be invoked (cached)


@pytest.mark.unit
def test_add_paper_chunk_success(graphiti_client, mock_mcp_tool_caller):
    """Test adding paper chunk to Graphiti."""
    # Mock availability and successful add
    graphiti_client._available = True
    mock_mcp_tool_caller.return_value = {"status": "queued"}

    result = graphiti_client.add_paper_chunk(
        chunk_text="This is a test chunk about neural networks.",
        paper_key="ABC123",
        metadata={"title": "Test Paper", "authors": "John Doe"},
    )

    assert result["success"] is True
    assert result["paper_key"] == "ABC123"
    assert "elapsed_seconds" in result
    mock_mcp_tool_caller.assert_called_once()

    # Verify MCP tool call parameters
    call_args = mock_mcp_tool_caller.call_args
    assert call_args[0][0] == "mcp__graphiti__add_memory"
    assert call_args[1]["episode_body"] == "This is a test chunk about neural networks."
    assert call_args[1]["group_id"] == "test-group"
    assert "Test Paper" in call_args[1]["source_description"]


@pytest.mark.unit
def test_add_paper_chunk_unavailable(graphiti_client):
    """Test adding paper chunk when Graphiti is unavailable."""
    graphiti_client._available = False

    with pytest.raises(GraphitiUnavailableError):
        graphiti_client.add_paper_chunk(
            chunk_text="Test",
            paper_key="ABC123",
        )


@pytest.mark.unit
def test_add_paper_chunk_failure(graphiti_client, mock_mcp_tool_caller):
    """Test handling of failed paper chunk ingestion."""
    graphiti_client._available = True
    mock_mcp_tool_caller.side_effect = Exception("Ingestion failed")

    with pytest.raises(GraphitiClientError) as exc_info:
        graphiti_client.add_paper_chunk(
            chunk_text="Test",
            paper_key="ABC123",
        )

    assert "Failed to add paper chunk" in str(exc_info.value)


@pytest.mark.unit
def test_search_entities_success(graphiti_client, mock_mcp_tool_caller):
    """Test searching for entities in Graphiti."""
    graphiti_client._available = True

    # Mock MCP response with entities
    mock_mcp_tool_caller.return_value = {
        "nodes": [
            {
                "name": "Neural Networks",
                "uuid": "uuid-1",
                "summary": "A computational model",
                "entity_type": "Concept",
            },
            {
                "name": "Transformers",
                "uuid": "uuid-2",
                "summary": "An architecture",
                "entity_type": "Method",
            },
        ]
    }

    result = graphiti_client.search_entities(
        query="neural networks",
        max_nodes=10,
    )

    assert len(result) == 2
    assert isinstance(result[0], EntityNode)
    assert result[0].name == "Neural Networks"
    assert result[0].uuid == "uuid-1"
    assert result[0].entity_type == "Concept"
    assert result[1].name == "Transformers"


@pytest.mark.unit
def test_search_entities_empty(graphiti_client, mock_mcp_tool_caller):
    """Test searching entities with no results."""
    graphiti_client._available = True
    mock_mcp_tool_caller.return_value = {"nodes": []}

    result = graphiti_client.search_entities(query="nonexistent")

    assert len(result) == 0
    assert result == []


@pytest.mark.unit
def test_search_entities_unavailable(graphiti_client):
    """Test searching entities when Graphiti is unavailable."""
    graphiti_client._available = False

    with pytest.raises(GraphitiUnavailableError):
        graphiti_client.search_entities(query="test")


@pytest.mark.unit
def test_search_relationships_success(graphiti_client, mock_mcp_tool_caller):
    """Test searching for relationship facts."""
    graphiti_client._available = True

    # Mock MCP response with facts
    mock_mcp_tool_caller.return_value = {
        "facts": [
            {
                "uuid": "fact-1",
                "fact": "Neural networks are used in transformers",
                "valid_at": "2025-01-01",
                "invalid_at": None,
            },
            {
                "uuid": "fact-2",
                "fact": "Transformers improve attention mechanisms",
                "valid_at": "2025-01-02",
                "invalid_at": None,
            },
        ]
    }

    result = graphiti_client.search_relationships(
        query="neural networks and transformers",
        max_facts=10,
    )

    assert len(result) == 2
    assert isinstance(result[0], RelationshipFact)
    assert result[0].uuid == "fact-1"
    assert "Neural networks" in result[0].fact
    assert result[0].valid_at == "2025-01-01"


@pytest.mark.unit
def test_search_relationships_empty(graphiti_client, mock_mcp_tool_caller):
    """Test searching relationships with no results."""
    graphiti_client._available = True
    mock_mcp_tool_caller.return_value = {"facts": []}

    result = graphiti_client.search_relationships(query="nonexistent")

    assert len(result) == 0


@pytest.mark.unit
def test_get_paper_entities(graphiti_client, mock_mcp_tool_caller):
    """Test retrieving entities for a specific paper."""
    graphiti_client._available = True

    # Mock entity search result
    mock_mcp_tool_caller.return_value = {
        "nodes": [
            {
                "name": "Neural Networks",
                "uuid": "uuid-1",
                "summary": "Found in Paper ABC123",
                "entity_type": "Concept",
            }
        ]
    }

    result = graphiti_client.get_paper_entities(paper_key="ABC123")

    assert len(result) == 1
    assert result[0].name == "Neural Networks"

    # Verify search query includes paper key
    call_args = mock_mcp_tool_caller.call_args
    assert "ABC123" in call_args[1]["query"]


@pytest.mark.unit
def test_get_status(graphiti_client):
    """Test getting client status."""
    graphiti_client._available = True

    status = graphiti_client.get_status()

    assert status["available"] is True
    assert status["group_id"] == "test-group"
    assert status["timeout_seconds"] == 5


@pytest.mark.unit
def test_entity_node_dataclass():
    """Test EntityNode dataclass."""
    node = EntityNode(
        name="Test Entity",
        uuid="uuid-123",
        summary="A test entity",
        entity_type="Concept",
    )

    assert node.name == "Test Entity"
    assert node.uuid == "uuid-123"
    assert node.summary == "A test entity"
    assert node.entity_type == "Concept"


@pytest.mark.unit
def test_relationship_fact_dataclass():
    """Test RelationshipFact dataclass."""
    fact = RelationshipFact(
        uuid="fact-123",
        fact="Entity A relates to Entity B",
        valid_at="2025-01-01",
        invalid_at="2025-12-31",
    )

    assert fact.uuid == "fact-123"
    assert fact.fact == "Entity A relates to Entity B"
    assert fact.valid_at == "2025-01-01"
    assert fact.invalid_at == "2025-12-31"


@pytest.mark.unit
def test_fallback_mcp_integration_import(mock_mcp_tool_caller):
    """Test fallback when mcp_tool_caller is not provided."""
    # Create client without mcp_tool_caller
    client = GraphitiClient()

    # Should attempt to import from mcp_integration
    # This will fail in test environment, triggering fallback
    with patch('agent_zot.clients.graphiti_client.logger') as mock_logger:
        result = client._call_mcp_tool("test_tool", param="value")

        # Should return mock result and log warning
        assert result == {"status": "mock"}
        mock_logger.warning.assert_called_once()


@pytest.mark.unit
def test_structured_logging(graphiti_client, mock_mcp_tool_caller):
    """Test that structured logging includes relevant context."""
    graphiti_client._available = True
    mock_mcp_tool_caller.return_value = {"status": "queued"}

    with patch('agent_zot.clients.graphiti_client.logger') as mock_logger:
        graphiti_client.add_paper_chunk(
            chunk_text="Test chunk",
            paper_key="ABC123",
        )

        # Verify structured logging was called
        assert mock_logger.info.called
        call_args = mock_logger.info.call_args
        assert "extra" in call_args[1]
        assert call_args[1]["extra"]["paper_key"] == "ABC123"
