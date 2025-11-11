"""
Test suite for Graphiti metadata linking strategy.

Verifies that Zotero item_key is correctly embedded in episode names
and metadata for cross-schema linking between Graphiti and Agent-Zot.
"""

import pytest
from unittest.mock import Mock

from agent_zot.ingestion.graphiti_ingestion import _create_batches
from agent_zot.clients.graphiti_client import GraphitiClient


class TestGraphitiMetadataLinking:
    """Test metadata linking between Graphiti episodes and Zotero papers."""

    def test_create_batches_embeds_item_key_in_episode_name(self):
        """Verify episode names follow pattern: Paper {item_key} - Part X/Y"""
        paper_key = "ABC123"
        chunks = ["chunk1", "chunk2", "chunk3"]
        metadata = {"title": "Test Paper", "authors": "Smith et al."}

        batches = _create_batches(
            paper_key=paper_key,
            chunks=chunks,
            metadata=metadata,
            batch_size=2,  # Creates 2 batches (2 + 1 chunks)
        )

        # Verify batch count
        assert len(batches) == 2, f"Expected 2 batches, got {len(batches)}"

        # Verify episode name pattern for batch 1
        assert batches[0].episode_name == "Paper ABC123 - Part 1/2"

        # Verify episode name pattern for batch 2
        assert batches[1].episode_name == "Paper ABC123 - Part 2/2"

    def test_create_batches_augments_metadata_with_item_key(self):
        """Verify batch metadata includes zotero_item_key field."""
        paper_key = "XYZ789"
        chunks = ["chunk1"]
        metadata = {"title": "Test Paper", "authors": "Doe et al."}

        batches = _create_batches(
            paper_key=paper_key,
            chunks=chunks,
            metadata=metadata,
            batch_size=10,
        )

        # Verify metadata augmentation
        assert "zotero_item_key" in batches[0].metadata
        assert batches[0].metadata["zotero_item_key"] == paper_key

        # Verify original metadata preserved
        assert batches[0].metadata["title"] == "Test Paper"
        assert batches[0].metadata["authors"] == "Doe et al."

    def test_add_paper_chunk_includes_item_key_in_source_description(self):
        """Verify source_description includes [item_key=...] tag for searchability."""
        mock_tool_caller = Mock(return_value={"status": "success"})

        client = GraphitiClient(
            group_id="test-group",
            mcp_tool_caller=mock_tool_caller,
        )
        client._available = True  # Bypass availability check

        paper_key = "TEST123"
        metadata = {"title": "Neural Networks", "authors": "LeCun et al."}

        result = client.add_paper_chunk(
            chunk_text="Test chunk content",
            paper_key=paper_key,
            metadata=metadata,
            episode_name=f"Paper {paper_key} - Part 1/1",
        )

        # Verify MCP tool was called
        assert mock_tool_caller.called

        # Get the call arguments
        call_args = mock_tool_caller.call_args[1]

        # Verify source_description contains item_key tag
        source_desc = call_args["source_description"]
        assert f"[item_key={paper_key}]" in source_desc
        assert "Neural Networks" in source_desc
        assert "LeCun et al." in source_desc

    def test_add_paper_chunk_returns_episode_name_in_result(self):
        """Verify result dict includes episode_name for tracking."""
        mock_tool_caller = Mock(return_value={"status": "success"})

        client = GraphitiClient(
            group_id="test-group",
            mcp_tool_caller=mock_tool_caller,
        )
        client._available = True

        paper_key = "RESULT456"
        episode_name = f"Paper {paper_key} - Part 1/5"

        result = client.add_paper_chunk(
            chunk_text="Test content",
            paper_key=paper_key,
            metadata=None,
            episode_name=episode_name,
        )

        # Verify result includes episode_name
        assert result["success"] is True
        assert result["episode_name"] == episode_name
        assert result["paper_key"] == paper_key

    def test_episode_name_parsing_pattern(self):
        """Verify episode name pattern is parseable to extract item_key."""
        import re

        test_cases = [
            ("Paper ABC123 - Part 1/3", "ABC123"),
            ("Paper XYZ789 - Part 5/10", "XYZ789"),
            ("Paper A1B2C3 - Part 1/1", "A1B2C3"),
        ]

        pattern = r"Paper ([A-Z0-9]+) - Part \d+/\d+"

        for episode_name, expected_key in test_cases:
            match = re.match(pattern, episode_name)
            assert match is not None, f"Pattern failed for: {episode_name}"
            extracted_key = match.group(1)
            assert extracted_key == expected_key

    def test_get_paper_entities_uses_episode_name_pattern(self):
        """Verify get_paper_entities() searches using episode name pattern."""
        mock_tool_caller = Mock(
            return_value={
                "nodes": [
                    {
                        "name": "Test Entity",
                        "uuid": "entity-123",
                        "summary": "Test summary",
                        "entity_type": "Concept",
                    }
                ]
            }
        )

        client = GraphitiClient(
            group_id="test-group",
            mcp_tool_caller=mock_tool_caller,
        )
        client._available = True

        paper_key = "SEARCH789"
        entities = client.get_paper_entities(paper_key)

        # Verify search was called
        assert mock_tool_caller.called

        # Verify query uses episode name pattern
        call_args = mock_tool_caller.call_args[1]
        assert call_args["query"] == f"Paper {paper_key}"

        # Verify entities returned
        assert len(entities) == 1
        assert entities[0].name == "Test Entity"

    def test_batch_metadata_does_not_mutate_original(self):
        """Verify _create_batches doesn't mutate input metadata dict."""
        paper_key = "IMMUTABLE999"
        chunks = ["chunk1"]
        original_metadata = {"title": "Original Title"}
        metadata_copy = dict(original_metadata)

        batches = _create_batches(
            paper_key=paper_key,
            chunks=chunks,
            metadata=original_metadata,
            batch_size=10,
        )

        # Verify batch metadata has item_key
        assert "zotero_item_key" in batches[0].metadata

        # Verify original metadata unchanged
        assert original_metadata == metadata_copy
        assert "zotero_item_key" not in original_metadata


class TestCrossSchemaLinkingScenarios:
    """Integration-style tests for cross-schema linking workflows."""

    def test_round_trip_ingestion_and_retrieval(self):
        """Test complete workflow: ingest paper → retrieve entities by paper_key."""
        mock_tool_caller = Mock(
            return_value={
                "nodes": [
                    {
                        "name": "Extracted Entity",
                        "uuid": "entity-456",
                        "summary": "Entity from paper",
                        "entity_type": "Concept",
                    }
                ]
            }
        )

        client = GraphitiClient(
            group_id="test-group",
            mcp_tool_caller=mock_tool_caller,
        )
        client._available = True

        paper_key = "ROUNDTRIP123"
        chunks = ["Chunk with important concepts"]
        metadata = {"title": "Important Paper"}

        # Step 1: Create batches (simulates ingestion)
        batches = _create_batches(
            paper_key=paper_key,
            chunks=chunks,
            metadata=metadata,
            batch_size=10,
        )

        # Verify batch has correct episode name
        assert batches[0].episode_name == f"Paper {paper_key} - Part 1/1"

        # Step 2: Simulate adding to Graphiti
        result = client.add_paper_chunk(
            chunk_text=batches[0].combined_text,
            paper_key=paper_key,
            metadata=batches[0].metadata,
            episode_name=batches[0].episode_name,
        )

        assert result["success"] is True

        # Step 3: Retrieve entities by paper_key
        entities = client.get_paper_entities(paper_key)

        # Verify retrieval used correct query pattern
        call_args = mock_tool_caller.call_args[1]
        assert call_args["query"] == f"Paper {paper_key}"

        # Verify entities returned
        assert len(entities) == 1
        assert entities[0].name == "Extracted Entity"

    def test_multiple_batches_maintain_item_key_linking(self):
        """Verify all batches from same paper maintain consistent item_key linking."""
        paper_key = "MULTIBATCH456"
        chunks = ["c1", "c2", "c3", "c4", "c5"]  # 5 chunks
        metadata = {"title": "Multi-Batch Paper"}

        batches = _create_batches(
            paper_key=paper_key,
            chunks=chunks,
            metadata=metadata,
            batch_size=2,  # Creates 3 batches (2 + 2 + 1)
        )

        assert len(batches) == 3

        # Verify all batches have item_key in metadata
        for i, batch in enumerate(batches, 1):
            assert batch.metadata["zotero_item_key"] == paper_key
            assert batch.episode_name == f"Paper {paper_key} - Part {i}/3"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
