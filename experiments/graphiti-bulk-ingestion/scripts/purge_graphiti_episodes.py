#!/usr/bin/env python3
"""
Safely purge Graphiti episodes created by bulk_ingest_graphiti.py.

ONLY deletes episodes with names starting with "Paper " (our bulk ingestion pattern).
This is safe because only bulk_ingest_graphiti.py uses this naming convention.

Usage:
    python scripts/purge_graphiti_episodes.py --dry-run  # Preview what will be deleted
    python scripts/purge_graphiti_episodes.py           # Actually delete (requires confirmation)
"""

import asyncio
import os
import sys
from pathlib import Path

# Set OpenAI API key from environment variable (required by Graphiti SDK)
# Set via: export OPENAI_API_KEY="your-key-here"
if "OPENAI_API_KEY" not in os.environ:
    print("⚠️  Warning: OPENAI_API_KEY environment variable not set")
    print("   Set via: export OPENAI_API_KEY=\"your-key-here\"")
    print()
else:
    os.environ["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY"]

# Disable Graphiti telemetry (PostHog analytics)
os.environ["GRAPHITI_TELEMETRY_ENABLED"] = "false"

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent_zot.clients.graphiti_client import GraphitiClient


async def purge_bulk_ingestion_episodes(dry_run: bool = False):
    """
    Purge all episodes created by bulk_ingest_graphiti.py.

    Safety features:
    - Only targets episodes with "Paper " prefix (unique to bulk ingestion)
    - Shows preview before deletion
    - Requires explicit confirmation
    - Dry-run mode available

    Args:
        dry_run: If True, only show what would be deleted
    """
    print("=" * 70)
    print("🧹 GRAPHITI EPISODE PURGE")
    print("=" * 70)
    print()

    # Initialize Graphiti client
    # Use default Neo4j config from agent-zot
    client = GraphitiClient(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="demodemo",
        group_id="agent-zot-discovery",
    )

    # Check availability
    if not await client.is_available():
        print("❌ Graphiti server unavailable")
        sys.exit(1)

    print("✅ Connected to Graphiti")
    print()

    # Get all episodes for our group
    print("🔍 Searching for bulk ingestion episodes...")

    # Graphiti SDK doesn't have search_episodes, so we need to get all episodes
    # and filter manually
    try:
        from datetime import datetime, timezone

        # Get episodes (retrieve_episodes requires reference_time and uses last_n parameter)
        # Set reference_time to now, last_n to 1000 (max we can retrieve)
        episodes_data = await client.graphiti.retrieve_episodes(
            reference_time=datetime.now(timezone.utc),
            last_n=1000,
            group_ids=[client.group_id]
        )

        all_episodes = episodes_data if isinstance(episodes_data, list) else [episodes_data]

        # Filter for "Paper " prefix
        paper_episodes = [
            ep for ep in all_episodes
            if ep.name.startswith("Paper ")
        ]

        print(f"✅ Found {len(all_episodes)} total episodes")
        print(f"📋 Found {len(paper_episodes)} bulk ingestion episodes to delete")
        print()

        if len(paper_episodes) == 0:
            print("✨ No episodes to delete - Graphiti is clean!")
            return

        # Show preview
        print("📝 Preview of episodes to delete:")
        print()
        for i, ep in enumerate(paper_episodes[:10]):
            print(f"  {i+1}. {ep.name}")

        if len(paper_episodes) > 10:
            print(f"  ... and {len(paper_episodes) - 10} more")
        print()

        # Show statistics
        paper_keys = set()
        for ep in paper_episodes:
            # Extract paper key from "Paper ABC123 - Part X/Y"
            parts = ep.name.split(" - ")
            if len(parts) >= 1:
                paper_key = parts[0].replace("Paper ", "")
                paper_keys.add(paper_key)

        print(f"📊 Statistics:")
        print(f"   - Total episodes: {len(paper_episodes)}")
        print(f"   - Unique papers: {len(paper_keys)}")
        print(f"   - Avg episodes/paper: {len(paper_episodes) / len(paper_keys) if paper_keys else 0:.1f}")
        print()

        if dry_run:
            print("🔍 DRY RUN - No changes made")
            return

        # Require confirmation
        print("⚠️  WARNING: This will permanently delete these episodes!")
        print("   Graphiti will auto-cleanup orphaned nodes and facts.")
        print()
        response = input("Type 'DELETE' to confirm: ")

        if response != "DELETE":
            print("❌ Cancelled")
            return

        print()
        print("🗑️  Deleting episodes...")

        # Delete episodes
        deleted = 0
        errors = 0

        for ep in paper_episodes:
            try:
                await client.graphiti.remove_episode(ep.uuid)
                deleted += 1
                if deleted % 10 == 0:
                    print(f"   Deleted {deleted}/{len(paper_episodes)}...")
            except Exception as e:
                print(f"   ❌ Error deleting {ep.name}: {e}")
                errors += 1

        print()
        print("=" * 70)
        print("✅ PURGE COMPLETE")
        print("=" * 70)
        print(f"✅ Deleted: {deleted} episodes")
        if errors > 0:
            print(f"❌ Errors: {errors}")
        print()

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def main():
    """Main entry point."""
    import sys

    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv

    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        print()

    await purge_bulk_ingestion_episodes(dry_run=dry_run)


if __name__ == "__main__":
    asyncio.run(main())
