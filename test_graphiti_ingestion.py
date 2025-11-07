#!/usr/bin/env python3
"""
Test script for Graphiti ingestion with 15 diverse papers.

This script bypasses the tag filter and directly ingests specified papers
to Graphiti for quality evaluation.
"""
import asyncio
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agent_zot.daemon.orchestrator import UpdateOrchestrator
from agent_zot.daemon.queue import UpdateJob


async def test_graphiti_ingestion():
    """Test Graphiti ingestion with 15 diverse papers."""

    # 2 test papers to avoid memory exhaustion
    test_papers = [
        "C93XCB7U",  # Prefrontal-hippocampal pathways (executive function)
        "H96QG37U",  # Fear and the brain (emotion)
    ]

    print(f"🧪 Testing Graphiti ingestion with {len(test_papers)} papers")
    print(f"📋 Papers: {', '.join(test_papers)}")
    print()

    # Initialize orchestrator
    config_path = str(Path.home() / ".config" / "agent-zot" / "config.json")
    orchestrator = UpdateOrchestrator(config_path=config_path)

    # Create update job
    job = UpdateJob(
        item_keys=test_papers,
        source="manual_test",
        timestamp=time.time(),
        extract_fulltext=True
    )

    # Process job
    print("⏳ Processing papers (this may take 5-10 minutes)...")
    stats = await orchestrator.process_update_job(job)

    # Display results
    print("\n" + "="*60)
    print("📊 INGESTION RESULTS")
    print("="*60)
    print(f"✅ Processed items: {stats.get('processed_items', 0)}")
    print(f"✅ Added items: {stats.get('added_items', 0)}")
    print(f"⊙ Skipped items: {stats.get('skipped_items', 0)}")
    print(f"❌ Errors: {stats.get('errors', 0)}")

    # Graphiti stats
    graphiti_stats = stats.get('graphiti', {})
    print(f"\n🧠 GRAPHITI STATISTICS")
    print(f"  Items processed: {graphiti_stats.get('items_processed', 0)}")
    print(f"  Chunks processed: {graphiti_stats.get('chunks_processed', 0)}")
    print(f"  Episodes created: {graphiti_stats.get('episodes_created', 0)}")
    print(f"  Errors: {graphiti_stats.get('errors', 0)}")
    print(f"  Skipped: {graphiti_stats.get('skipped', 0)}")

    # Overall orchestrator stats
    overall_stats = orchestrator.get_stats()
    print(f"\n📈 ORCHESTRATOR OVERALL")
    print(f"  Total jobs: {overall_stats['total_jobs']}")
    print(f"  Total items: {overall_stats['total_items_processed']}")
    print(f"  Graphiti items: {overall_stats['graphiti_items_processed']}")
    print(f"  Graphiti episodes: {overall_stats['graphiti_episodes_created']}")

    print("\n✅ Test complete! Check Graphiti with search_memory_nodes.")


if __name__ == "__main__":
    asyncio.run(test_graphiti_ingestion())
