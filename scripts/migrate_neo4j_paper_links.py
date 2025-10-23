#!/usr/bin/env python3
"""
Migrate Neo4j knowledge graph to link isolated Paper nodes.

This script fixes the architectural issue where Paper nodes exist but have no
relationships to Chunk or Entity nodes, making them invisible to graph queries.

Strategy:
1. Match Neo4j Chunk nodes to Qdrant points by text content
2. Create Paper→Chunk (HAS_CHUNK) relationships
3. Propagate Chunk→Entity relationships to Paper→Entity (MENTIONS + specific types)

No re-parsing or re-embedding required - uses existing Qdrant and Neo4j data.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional
import time

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from agent_zot.database.local_zotero import LocalZoteroReader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Neo4jPaperLinkMigration:
    """Migration to connect isolated Paper nodes to Chunks and Entities."""

    def __init__(
        self,
        neo4j_uri: str = "neo4j://127.0.0.1:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "demodemo",
        neo4j_database: str = "neo4j",
        qdrant_url: str = "http://localhost:6333",
        qdrant_collection: str = "zotero_library_qdrant",
        test_mode: bool = False,
        test_limit: int = 10
    ):
        """
        Initialize migration.

        Args:
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            neo4j_database: Neo4j database name
            qdrant_url: Qdrant server URL
            qdrant_collection: Qdrant collection name
            test_mode: If True, only process first test_limit papers
            test_limit: Number of papers to process in test mode
        """
        self.neo4j_driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )
        self.neo4j_database = neo4j_database

        self.qdrant = QdrantClient(url=qdrant_url)
        self.collection_name = qdrant_collection

        self.test_mode = test_mode
        self.test_limit = test_limit

        logger.info(f"Migration initialized (test_mode={test_mode})")

    def get_papers_needing_migration(self) -> List[Dict]:
        """Get list of Paper nodes that need migration."""
        with self.neo4j_driver.session(database=self.neo4j_database) as session:
            # Get papers with no HAS_CHUNK relationships
            query = """
            MATCH (p:Paper)
            WHERE NOT EXISTS((p)-[:HAS_CHUNK]->())
            RETURN p.item_key as item_key, p.title as title
            """

            if self.test_mode:
                query += f" LIMIT {self.test_limit}"

            result = session.run(query)
            papers = [{"item_key": r["item_key"], "title": r["title"]} for r in result]

            logger.info(f"Found {len(papers)} papers needing migration")
            return papers

    def get_chunks_for_paper(self, item_key: str) -> List[Dict]:
        """Get all Qdrant chunks for a paper."""
        chunks = []
        offset = None

        while True:
            results = self.qdrant.scroll(
                collection_name=self.collection_name,
                scroll_filter={
                    "should": [
                        {"key": "item_key", "match": {"value": item_key}},
                        {"key": "parent_item_key", "match": {"value": item_key}}
                    ]
                },
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )

            points = results[0]
            offset = results[1]

            if not points:
                break

            for point in points:
                chunks.append({
                    "point_id": point.id,
                    "chunk_id": point.payload.get("chunk_id"),
                    "text": point.payload.get("document", ""),
                    "item_key": point.payload.get("item_key") or point.payload.get("parent_item_key")
                })

            if offset is None:
                break

        return chunks

    def match_chunk_to_neo4j(self, chunk_text: str, chunk_index: Optional[int] = None) -> Optional[str]:
        """
        Find matching Chunk node in Neo4j by text content.

        Args:
            chunk_text: Text content to match
            chunk_index: Optional chunk index for faster matching

        Returns:
            Neo4j internal ID of matched chunk, or None
        """
        with self.neo4j_driver.session(database=self.neo4j_database) as session:
            # Try exact text match first (fastest)
            exact_match = session.run(
                """
                MATCH (c:Chunk {text: $text})
                RETURN elementId(c) as chunk_id
                LIMIT 1
                """,
                text=chunk_text
            ).single()

            if exact_match:
                return exact_match["chunk_id"]

            # Try index match if available
            if chunk_index is not None:
                index_match = session.run(
                    """
                    MATCH (c:Chunk {index: $index})
                    WHERE c.text CONTAINS $text_sample
                    RETURN elementId(c) as chunk_id
                    LIMIT 1
                    """,
                    index=chunk_index,
                    text_sample=chunk_text[:100]  # First 100 chars
                ).single()

                if index_match:
                    return index_match["chunk_id"]

            # Fallback: partial text match (slower but catches variations)
            partial_match = session.run(
                """
                MATCH (c:Chunk)
                WHERE c.text CONTAINS $text_sample
                RETURN elementId(c) as chunk_id, c.text as full_text
                LIMIT 5
                """,
                text_sample=chunk_text[:200]
            )

            # Find best match by text similarity
            best_match = None
            best_similarity = 0

            for record in partial_match:
                similarity = len(set(chunk_text.split()) & set(record["full_text"].split())) / max(len(chunk_text.split()), 1)
                if similarity > best_similarity and similarity > 0.5:  # 50% word overlap threshold
                    best_similarity = similarity
                    best_match = record["chunk_id"]

            return best_match

    def link_paper_to_chunks(self, paper_key: str, chunk_ids: List[str]) -> int:
        """
        Create HAS_CHUNK relationships from Paper to Chunks.

        Args:
            paper_key: Zotero item key
            chunk_ids: List of Neo4j chunk element IDs

        Returns:
            Number of relationships created
        """
        if not chunk_ids:
            return 0

        with self.neo4j_driver.session(database=self.neo4j_database) as session:
            result = session.run(
                """
                MATCH (p:Paper {item_key: $paper_key})
                UNWIND $chunk_ids as chunk_id
                MATCH (c:Chunk)
                WHERE elementId(c) = chunk_id
                MERGE (p)-[:HAS_CHUNK]->(c)
                RETURN count(*) as links_created
                """,
                paper_key=paper_key,
                chunk_ids=chunk_ids
            ).single()

            return result["links_created"] if result else 0

    def propagate_entities_to_paper(self, paper_key: str) -> Dict[str, int]:
        """
        Create Paper→Entity relationships from existing Chunk→Entity links.

        Creates both:
        - Generic MENTIONS relationships for all entities
        - Specific typed relationships (AUTHORED_BY, DISCUSSES_CONCEPT, etc.)

        Args:
            paper_key: Zotero item key

        Returns:
            Dict with counts of relationships created by type
        """
        with self.neo4j_driver.session(database=self.neo4j_database) as session:
            result = session.run(
                """
                MATCH (p:Paper {item_key: $paper_key})-[:HAS_CHUNK]->(c:Chunk)<-[:FROM_CHUNK]-(e)
                WHERE NOT EXISTS((p)-[:MENTIONS]->(e))
                WITH p, e, labels(e) as entity_labels

                // Create specific typed relationships based on entity type
                FOREACH (_ IN CASE WHEN 'Person' IN entity_labels THEN [1] ELSE [] END |
                    MERGE (p)-[:AUTHORED_BY]->(e)
                )
                FOREACH (_ IN CASE WHEN 'Concept' IN entity_labels THEN [1] ELSE [] END |
                    MERGE (p)-[:DISCUSSES_CONCEPT]->(e)
                )
                FOREACH (_ IN CASE WHEN 'Method' IN entity_labels THEN [1] ELSE [] END |
                    MERGE (p)-[:USES_METHOD]->(e)
                )
                FOREACH (_ IN CASE WHEN 'Dataset' IN entity_labels THEN [1] ELSE [] END |
                    MERGE (p)-[:USES_DATASET]->(e)
                )
                FOREACH (_ IN CASE WHEN 'Theory' IN entity_labels THEN [1] ELSE [] END |
                    MERGE (p)-[:APPLIES_THEORY]->(e)
                )
                FOREACH (_ IN CASE WHEN 'Institution' IN entity_labels THEN [1] ELSE [] END |
                    MERGE (p)-[:AFFILIATED_WITH]->(e)
                )
                FOREACH (_ IN CASE WHEN 'Journal' IN entity_labels THEN [1] ELSE [] END |
                    MERGE (p)-[:PUBLISHED_IN]->(e)
                )
                FOREACH (_ IN CASE WHEN 'Field' IN entity_labels THEN [1] ELSE [] END |
                    MERGE (p)-[:BELONGS_TO_FIELD]->(e)
                )

                // Also create generic MENTIONS for all entities
                MERGE (p)-[:MENTIONS]->(e)

                RETURN
                    count(DISTINCT e) as total_entities,
                    count(DISTINCT CASE WHEN 'Person' IN entity_labels THEN e END) as persons,
                    count(DISTINCT CASE WHEN 'Concept' IN entity_labels THEN e END) as concepts,
                    count(DISTINCT CASE WHEN 'Method' IN entity_labels THEN e END) as methods
                """,
                paper_key=paper_key
            ).single()

            if result:
                return {
                    "total": result["total_entities"],
                    "persons": result["persons"],
                    "concepts": result["concepts"],
                    "methods": result["methods"]
                }
            return {"total": 0, "persons": 0, "concepts": 0, "methods": 0}

    def migrate_paper(self, paper_key: str, paper_title: str) -> Dict:
        """
        Migrate a single paper.

        Args:
            paper_key: Zotero item key
            paper_title: Paper title (for logging)

        Returns:
            Migration statistics
        """
        logger.info(f"Migrating: {paper_title[:80]}")

        start_time = time.time()
        stats = {
            "paper_key": paper_key,
            "chunks_from_qdrant": 0,
            "chunks_matched": 0,
            "chunks_linked": 0,
            "entities_propagated": 0,
            "success": False,
            "error": None,
            "duration_seconds": 0
        }

        try:
            # Step 1: Get chunks from Qdrant
            qdrant_chunks = self.get_chunks_for_paper(paper_key)
            stats["chunks_from_qdrant"] = len(qdrant_chunks)

            if not qdrant_chunks:
                logger.warning(f"  No chunks found in Qdrant for {paper_key}")
                stats["error"] = "No chunks in Qdrant"
                return stats

            logger.info(f"  Found {len(qdrant_chunks)} chunks in Qdrant")

            # Step 2: Match chunks to Neo4j
            neo4j_chunk_ids = []
            for i, chunk in enumerate(qdrant_chunks):
                chunk_id = self.match_chunk_to_neo4j(chunk["text"], chunk.get("chunk_id"))
                if chunk_id:
                    neo4j_chunk_ids.append(chunk_id)

                # Progress update every 50 chunks
                if (i + 1) % 50 == 0:
                    logger.info(f"  Matched {i + 1}/{len(qdrant_chunks)} chunks...")

            stats["chunks_matched"] = len(neo4j_chunk_ids)
            logger.info(f"  Matched {len(neo4j_chunk_ids)}/{len(qdrant_chunks)} chunks to Neo4j")

            if not neo4j_chunk_ids:
                logger.warning(f"  Could not match any chunks to Neo4j for {paper_key}")
                stats["error"] = "No chunks matched"
                return stats

            # Step 3: Create Paper→Chunk links
            links_created = self.link_paper_to_chunks(paper_key, neo4j_chunk_ids)
            stats["chunks_linked"] = links_created
            logger.info(f"  Created {links_created} HAS_CHUNK relationships")

            # Step 4: Propagate entities
            entity_stats = self.propagate_entities_to_paper(paper_key)
            stats["entities_propagated"] = entity_stats["total"]
            logger.info(f"  Linked to {entity_stats['total']} entities ({entity_stats['persons']} persons, {entity_stats['concepts']} concepts, {entity_stats['methods']} methods)")

            stats["success"] = True

        except Exception as e:
            logger.error(f"  Error migrating {paper_key}: {e}", exc_info=True)
            stats["error"] = str(e)

        finally:
            stats["duration_seconds"] = time.time() - start_time

        return stats

    def run_migration(self) -> Dict:
        """
        Run the full migration.

        Returns:
            Overall migration statistics
        """
        logger.info("="*80)
        logger.info("NEO4J PAPER LINK MIGRATION")
        logger.info("="*80)

        if self.test_mode:
            logger.info(f"⚠️  TEST MODE: Processing only {self.test_limit} papers")

        overall_start = time.time()

        # Get papers needing migration
        papers = self.get_papers_needing_migration()

        if not papers:
            logger.info("✅ No papers need migration!")
            return {
                "total_papers": 0,
                "successful": 0,
                "failed": 0,
                "duration_seconds": 0
            }

        # Migrate each paper
        results = {
            "total_papers": len(papers),
            "successful": 0,
            "failed": 0,
            "total_chunks_linked": 0,
            "total_entities_linked": 0,
            "errors": []
        }

        for i, paper in enumerate(papers, 1):
            logger.info(f"\n[{i}/{len(papers)}] Processing {paper['item_key']}")

            stats = self.migrate_paper(paper["item_key"], paper["title"])

            if stats["success"]:
                results["successful"] += 1
                results["total_chunks_linked"] += stats["chunks_linked"]
                results["total_entities_linked"] += stats["entities_propagated"]
            else:
                results["failed"] += 1
                results["errors"].append({
                    "paper_key": paper["item_key"],
                    "error": stats["error"]
                })

            # Progress summary every 10 papers
            if i % 10 == 0:
                logger.info(f"\n📊 Progress: {i}/{len(papers)} papers processed ({results['successful']} successful, {results['failed']} failed)")

        results["duration_seconds"] = time.time() - overall_start

        # Final summary
        logger.info("\n" + "="*80)
        logger.info("MIGRATION COMPLETE")
        logger.info("="*80)
        logger.info(f"Total papers: {results['total_papers']}")
        logger.info(f"Successful: {results['successful']}")
        logger.info(f"Failed: {results['failed']}")
        logger.info(f"Total chunks linked: {results['total_chunks_linked']:,}")
        logger.info(f"Total entities linked: {results['total_entities_linked']:,}")
        logger.info(f"Duration: {results['duration_seconds']/60:.1f} minutes")

        if results["errors"]:
            logger.warning(f"\nErrors encountered for {len(results['errors'])} papers:")
            for error in results["errors"][:10]:  # Show first 10
                logger.warning(f"  {error['paper_key']}: {error['error']}")

        return results

    def validate_migration(self) -> Dict:
        """
        Validate that migration was successful.

        Returns:
            Validation statistics
        """
        logger.info("\n" + "="*80)
        logger.info("VALIDATING MIGRATION")
        logger.info("="*80)

        with self.neo4j_driver.session(database=self.neo4j_database) as session:
            # Check for isolated papers
            isolated = session.run("""
                MATCH (p:Paper)
                WHERE NOT (p)-[:HAS_CHUNK]->()
                RETURN count(p) as count
            """).single()

            # Check papers with entity links
            with_entities = session.run("""
                MATCH (p:Paper)-[:MENTIONS]->()
                RETURN count(DISTINCT p) as count
            """).single()

            # Check total papers
            total_papers = session.run("""
                MATCH (p:Paper)
                RETURN count(p) as count
            """).single()

            # Check relationship counts
            has_chunk_count = session.run("""
                MATCH ()-[r:HAS_CHUNK]->()
                RETURN count(r) as count
            """).single()

            mentions_count = session.run("""
                MATCH ()-[r:MENTIONS]->()
                RETURN count(r) as count
            """).single()

            validation = {
                "total_papers": total_papers["count"],
                "isolated_papers": isolated["count"],
                "papers_with_entities": with_entities["count"],
                "has_chunk_relationships": has_chunk_count["count"],
                "mentions_relationships": mentions_count["count"],
                "success": isolated["count"] == 0
            }

            logger.info(f"Total papers: {validation['total_papers']:,}")
            logger.info(f"Isolated papers: {validation['isolated_papers']:,}")
            logger.info(f"Papers with entity links: {validation['papers_with_entities']:,}")
            logger.info(f"HAS_CHUNK relationships: {validation['has_chunk_relationships']:,}")
            logger.info(f"MENTIONS relationships: {validation['mentions_relationships']:,}")

            if validation["success"]:
                logger.info("✅ VALIDATION PASSED - No isolated papers!")
            else:
                logger.warning(f"⚠️  VALIDATION INCOMPLETE - {validation['isolated_papers']} papers still isolated")

            return validation

    def close(self):
        """Close connections."""
        if self.neo4j_driver:
            self.neo4j_driver.close()


def main():
    """Run migration script."""
    import argparse

    parser = argparse.ArgumentParser(description="Migrate Neo4j Paper nodes to link with Chunks and Entities")
    parser.add_argument("--test", action="store_true", help="Test mode - only process 10 papers")
    parser.add_argument("--test-limit", type=int, default=10, help="Number of papers in test mode")
    parser.add_argument("--validate-only", action="store_true", help="Only run validation, no migration")

    args = parser.parse_args()

    migration = Neo4jPaperLinkMigration(
        test_mode=args.test,
        test_limit=args.test_limit
    )

    try:
        if args.validate_only:
            migration.validate_migration()
        else:
            migration.run_migration()
            migration.validate_migration()
    finally:
        migration.close()


if __name__ == "__main__":
    main()
