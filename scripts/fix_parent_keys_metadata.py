#!/usr/bin/env python3
"""
Fix parent_item_key metadata in Qdrant without re-indexing.

This script updates existing Qdrant points to use correct parent paper keys
instead of attachment keys, preserving all embeddings.
"""

import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / ".venv" / "lib" / "python3.12" / "site-packages"))

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from agent_zot.database.local_zotero import LocalZoteroReader
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def resolve_attachment_to_parent(item_key: str, reader: LocalZoteroReader) -> str:
    """
    Resolve attachment key to parent paper key.

    Args:
        item_key: The item key (might be attachment or parent)
        reader: LocalZoteroReader instance

    Returns:
        Parent paper key, or original key if not an attachment
    """
    try:
        conn = reader._get_connection()
        cursor = conn.cursor()

        # Get itemID for this key
        cursor.execute("SELECT itemID FROM items WHERE key = ?", (item_key,))
        result = cursor.fetchone()
        if not result:
            logger.warning(f"Item {item_key} not found in database")
            return item_key

        item_id = result[0]

        # Check if this is an attachment
        cursor.execute("""
            SELECT ia.parentItemID
            FROM itemAttachments ia
            WHERE ia.itemID = ?
        """, (item_id,))

        attach_result = cursor.fetchone()
        if attach_result and attach_result[0]:
            # This is an attachment, get parent key
            parent_id = attach_result[0]
            cursor.execute("SELECT key FROM items WHERE itemID = ?", (parent_id,))
            parent_result = cursor.fetchone()
            if parent_result:
                return parent_result[0]

        # Not an attachment or parent not found
        return item_key

    except Exception as e:
        logger.error(f"Error resolving {item_key}: {e}")
        return item_key


def main():
    logger.info("="*80)
    logger.info("QDRANT PARENT_ITEM_KEY METADATA FIX")
    logger.info("="*80)
    logger.info("This script updates parent_item_key metadata without re-embedding")
    logger.info("")

    # Connect to Qdrant
    client = QdrantClient(url='http://localhost:6333')
    collection_name = 'zotero_library_qdrant'

    # Get collection info
    collection_info = client.get_collection(collection_name)
    total_points = collection_info.points_count
    logger.info(f"Collection: {collection_name}")
    logger.info(f"Total points: {total_points:,}")
    logger.info("")

    # Connect to Zotero DB
    reader = LocalZoteroReader()

    # Process in batches
    batch_size = 1000
    offset = None
    processed = 0
    updated = 0
    errors = 0

    # Cache for resolved keys (avoid repeated DB queries)
    resolution_cache = {}

    logger.info("Starting metadata update...")
    logger.info("")

    while True:
        # Scroll through points
        scroll_result = client.scroll(
            collection_name=collection_name,
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=False  # Don't need vectors, just metadata
        )

        points, next_offset = scroll_result

        if not points:
            break

        updates = []

        for point in points:
            processed += 1

            try:
                payload = point.payload
                current_parent_key = payload.get('parent_item_key')

                if not current_parent_key:
                    # No parent_item_key set (shouldn't happen but skip if so)
                    continue

                # Check cache first
                if current_parent_key in resolution_cache:
                    correct_parent_key = resolution_cache[current_parent_key]
                else:
                    # Resolve attachment to parent
                    correct_parent_key = resolve_attachment_to_parent(current_parent_key, reader)
                    resolution_cache[current_parent_key] = correct_parent_key

                # Only update if parent key changed
                if correct_parent_key != current_parent_key:
                    # Prepare payload updates
                    payload_updates = {
                        'parent_item_key': correct_parent_key
                    }

                    # Also update neo4j_paper_id if present
                    if 'neo4j_paper_id' in payload:
                        payload_updates['neo4j_paper_id'] = f"paper:{correct_parent_key}"

                    # Add to update batch (just store point ID and updates)
                    updates.append((point.id, payload_updates))

                    updated += 1

                    if updated % 100 == 0:
                        logger.info(f"Progress: {processed:,}/{total_points:,} processed, {updated:,} updated")

            except Exception as e:
                logger.error(f"Error processing point {point.id}: {e}")
                errors += 1

        # Batch update to Qdrant using set_payload (only updates metadata, not vectors)
        # Group by payload content to minimize API calls
        if updates:
            try:
                # Group updates by identical payload changes
                update_groups = {}
                for point_id, payload_updates in updates:
                    key = tuple(sorted(payload_updates.items()))
                    if key not in update_groups:
                        update_groups[key] = []
                    update_groups[key].append(point_id)

                # Apply each group of updates in one API call
                for payload_items, point_ids in update_groups.items():
                    payload_dict = dict(payload_items)
                    client.set_payload(
                        collection_name=collection_name,
                        payload=payload_dict,
                        points=point_ids
                    )
            except Exception as e:
                logger.error(f"Error updating batch: {e}")
                errors += len(updates)

        # Progress update
        if processed % 10000 == 0:
            logger.info(f"Progress: {processed:,}/{total_points:,} processed, {updated:,} updated, {errors} errors")

        # Move to next batch
        offset = next_offset
        if offset is None:
            break

    logger.info("")
    logger.info("="*80)
    logger.info("UPDATE COMPLETE")
    logger.info("="*80)
    logger.info(f"Total points processed: {processed:,}")
    logger.info(f"Points updated: {updated:,}")
    logger.info(f"Errors: {errors}")
    logger.info(f"Cache entries: {len(resolution_cache)}")
    logger.info("")

    # Show sample resolutions
    logger.info("Sample resolutions from cache:")
    for i, (old_key, new_key) in enumerate(list(resolution_cache.items())[:10]):
        if old_key != new_key:
            logger.info(f"  {old_key} → {new_key}")
    logger.info("")

    # Verify a known case
    logger.info("Verifying known test case (GXSFLH4R)...")
    try:
        results = client.scroll(
            collection_name=collection_name,
            scroll_filter={'must': [{'key': 'item_key', 'match': {'value': 'GXSFLH4R_chunk_0'}}]},
            limit=1,
            with_payload=True
        )
        if results[0]:
            payload = results[0][0].payload
            parent_key = payload.get('parent_item_key')
            expected = 'ZJQBYQM6'
            status = "✅" if parent_key == expected else "❌"
            logger.info(f"{status} GXSFLH4R_chunk_0 parent_item_key: {parent_key} (expected: {expected})")
    except Exception as e:
        logger.error(f"Verification failed: {e}")

    logger.info("")
    logger.info("Done! Metadata updated without re-indexing.")


if __name__ == "__main__":
    main()
