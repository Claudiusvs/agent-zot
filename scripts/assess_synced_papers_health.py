#!/usr/bin/env python3
"""
Assess health of the 151 papers synced to Neo4j from Qdrant.

This script verifies:
1. Papers exist in Neo4j
2. Papers have chunks (HAS_CHUNK relationships)
3. Papers have entities extracted (CONTAINS_ENTITY relationships)
4. Papers have authors (AUTHORED_BY relationships)
5. Data quality metrics (text length, entity diversity, etc.)

Usage:
    python scripts/assess_synced_papers_health.py
"""

import sys
import json
import logging
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import GraphDatabase

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_missing_papers() -> List[str]:
    """Load the list of 151 papers that were synced."""
    with open("/tmp/missing_papers_neo4j.json", 'r') as f:
        return json.load(f)


def assess_paper_health(driver, paper_keys: List[str]) -> Dict[str, Any]:
    """
    Assess health of papers in Neo4j.

    Returns dict with:
    - papers_exist: Papers found in Neo4j
    - papers_with_chunks: Papers with HAS_CHUNK relationships
    - papers_with_entities: Papers with entities extracted
    - papers_with_authors: Papers with AUTHORED_BY relationships
    - health_summary: Per-paper health metrics
    """
    results = {
        "total_papers": len(paper_keys),
        "papers_exist": [],
        "papers_missing": [],
        "papers_with_chunks": [],
        "papers_without_chunks": [],
        "papers_with_entities": [],
        "papers_without_entities": [],
        "papers_with_authors": [],
        "papers_without_authors": [],
        "health_details": {}
    }

    logger.info(f"Assessing health of {len(paper_keys)} papers...")

    with driver.session() as session:
        for i, paper_key in enumerate(paper_keys):
            if (i + 1) % 20 == 0:
                logger.info(f"  Assessed {i + 1}/{len(paper_keys)} papers...")

            # Check if paper exists
            paper_result = session.run(
                """
                MATCH (p:Paper {item_key: $paper_key})
                RETURN
                    p.item_key as key,
                    p.title as title,
                    p.year as year,
                    size(p.authors) as author_count
                """,
                paper_key=paper_key
            )

            paper_record = paper_result.single()

            if not paper_record:
                results["papers_missing"].append(paper_key)
                continue

            results["papers_exist"].append(paper_key)

            # Get paper details
            paper_data = {
                "key": paper_key,
                "title": paper_record["title"],
                "year": paper_record["year"],
                "author_count": paper_record["author_count"] or 0
            }

            # Count chunks
            chunk_result = session.run(
                """
                MATCH (p:Paper {item_key: $paper_key})-[:HAS_CHUNK]->(c:Chunk)
                RETURN count(c) as chunk_count,
                       sum(size(c.text)) as total_text_length
                """,
                paper_key=paper_key
            )
            chunk_record = chunk_result.single()
            paper_data["chunk_count"] = chunk_record["chunk_count"]
            paper_data["total_text_length"] = chunk_record["total_text_length"] or 0

            if chunk_record["chunk_count"] > 0:
                results["papers_with_chunks"].append(paper_key)
            else:
                results["papers_without_chunks"].append(paper_key)

            # Count entities
            entity_result = session.run(
                """
                MATCH (p:Paper {item_key: $paper_key})-[:HAS_CHUNK]->(c:Chunk)-[:CONTAINS_ENTITY]->(e)
                RETURN count(DISTINCT e) as entity_count,
                       collect(DISTINCT labels(e)[0]) as entity_types
                """,
                paper_key=paper_key
            )
            entity_record = entity_result.single()
            paper_data["entity_count"] = entity_record["entity_count"]
            paper_data["entity_types"] = entity_record["entity_types"]

            if entity_record["entity_count"] > 0:
                results["papers_with_entities"].append(paper_key)
            else:
                results["papers_without_entities"].append(paper_key)

            # Check for authors
            author_result = session.run(
                """
                MATCH (p:Paper {item_key: $paper_key})-[:AUTHORED_BY]->(a:Person)
                RETURN count(a) as author_relationship_count
                """,
                paper_key=paper_key
            )
            author_record = author_result.single()
            paper_data["author_relationship_count"] = author_record["author_relationship_count"]

            if author_record["author_relationship_count"] > 0:
                results["papers_with_authors"].append(paper_key)
            else:
                results["papers_without_authors"].append(paper_key)

            results["health_details"][paper_key] = paper_data

    return results


def print_health_report(results: Dict[str, Any]) -> None:
    """Print a comprehensive health report."""
    logger.info("\n" + "=" * 80)
    logger.info("HEALTH ASSESSMENT REPORT")
    logger.info("=" * 80)

    total = results["total_papers"]

    # Paper existence
    logger.info(f"\n📄 Paper Existence:")
    logger.info(f"  Total papers assessed: {total}")
    logger.info(f"  ✅ Papers found: {len(results['papers_exist'])} ({len(results['papers_exist'])/total*100:.1f}%)")
    logger.info(f"  ❌ Papers missing: {len(results['papers_missing'])} ({len(results['papers_missing'])/total*100:.1f}%)")

    if results["papers_missing"]:
        logger.warning(f"  Missing paper keys: {results['papers_missing'][:10]}...")

    # Chunks
    logger.info(f"\n📝 Chunk Relationships (HAS_CHUNK):")
    logger.info(f"  ✅ Papers with chunks: {len(results['papers_with_chunks'])} ({len(results['papers_with_chunks'])/total*100:.1f}%)")
    logger.info(f"  ❌ Papers without chunks: {len(results['papers_without_chunks'])} ({len(results['papers_without_chunks'])/total*100:.1f}%)")

    if results["papers_without_chunks"]:
        logger.warning(f"  Papers without chunks: {results['papers_without_chunks'][:10]}...")

    # Entities
    logger.info(f"\n🏷️  Entity Extraction (CONTAINS_ENTITY):")
    logger.info(f"  ✅ Papers with entities: {len(results['papers_with_entities'])} ({len(results['papers_with_entities'])/total*100:.1f}%)")
    logger.info(f"  ❌ Papers without entities: {len(results['papers_without_entities'])} ({len(results['papers_without_entities'])/total*100:.1f}%)")

    if results["papers_without_entities"]:
        logger.warning(f"  Papers without entities: {results['papers_without_entities'][:10]}...")

    # Authors
    logger.info(f"\n👥 Author Relationships (AUTHORED_BY):")
    logger.info(f"  ✅ Papers with author relationships: {len(results['papers_with_authors'])} ({len(results['papers_with_authors'])/total*100:.1f}%)")
    logger.info(f"  ❌ Papers without author relationships: {len(results['papers_without_authors'])} ({len(results['papers_without_authors'])/total*100:.1f}%)")

    # Data quality metrics
    logger.info(f"\n📊 Data Quality Metrics:")

    chunk_counts = [d["chunk_count"] for d in results["health_details"].values()]
    entity_counts = [d["entity_count"] for d in results["health_details"].values()]
    text_lengths = [d["total_text_length"] for d in results["health_details"].values()]

    if chunk_counts:
        avg_chunks = sum(chunk_counts) / len(chunk_counts)
        logger.info(f"  Average chunks per paper: {avg_chunks:.1f}")
        logger.info(f"  Chunk count range: {min(chunk_counts)} - {max(chunk_counts)}")

    if entity_counts:
        avg_entities = sum(entity_counts) / len(entity_counts)
        logger.info(f"  Average entities per paper: {avg_entities:.1f}")
        logger.info(f"  Entity count range: {min(entity_counts)} - {max(entity_counts)}")

    if text_lengths:
        avg_text_length = sum(text_lengths) / len(text_lengths)
        logger.info(f"  Average text length per paper: {avg_text_length:,.0f} chars")

    # Entity type diversity
    all_entity_types = set()
    for details in results["health_details"].values():
        all_entity_types.update(details["entity_types"])

    if all_entity_types:
        logger.info(f"  Unique entity types found: {len(all_entity_types)}")
        logger.info(f"  Entity types: {sorted(all_entity_types)}")

    # Overall health score
    logger.info(f"\n🎯 Overall Health Score:")

    papers_exist_pct = len(results['papers_exist']) / total * 100
    chunks_pct = len(results['papers_with_chunks']) / total * 100
    entities_pct = len(results['papers_with_entities']) / total * 100
    authors_pct = len(results['papers_with_authors']) / total * 100

    overall_score = (papers_exist_pct + chunks_pct + entities_pct + authors_pct) / 4

    logger.info(f"  Paper existence: {papers_exist_pct:.1f}%")
    logger.info(f"  Chunk coverage: {chunks_pct:.1f}%")
    logger.info(f"  Entity coverage: {entities_pct:.1f}%")
    logger.info(f"  Author coverage: {authors_pct:.1f}%")
    logger.info(f"  ---")
    logger.info(f"  Overall: {overall_score:.1f}% {'✅' if overall_score >= 90 else '⚠️' if overall_score >= 75 else '❌'}")


def main():
    # Load config
    config_path = Path.home() / ".config" / "agent-zot" / "config.json"
    logger.info(f"Loading config from {config_path}")

    with open(config_path, 'r') as f:
        config = json.load(f)

    neo4j_config = config.get("neo4j_graphrag", {})
    neo4j_uri = neo4j_config.get("neo4j_uri", "neo4j://127.0.0.1:7687")
    neo4j_user = neo4j_config.get("neo4j_user", "neo4j")
    neo4j_password = neo4j_config.get("neo4j_password", "demodemo")

    # Load paper list
    logger.info("Loading list of synced papers...")
    paper_keys = load_missing_papers()
    logger.info(f"Loaded {len(paper_keys)} paper keys")

    # Connect to Neo4j
    logger.info(f"Connecting to Neo4j at {neo4j_uri}...")
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    try:
        # Assess health
        results = assess_paper_health(driver, paper_keys)

        # Print report
        print_health_report(results)

        # Save results
        output_file = Path("/tmp/synced_papers_health_report.json")
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"\n💾 Detailed results saved to {output_file}")

        # Return exit code based on health
        papers_exist_pct = len(results['papers_exist']) / results['total_papers'] * 100
        if papers_exist_pct >= 95:
            return 0  # Excellent
        elif papers_exist_pct >= 90:
            return 1  # Good but some issues
        else:
            return 2  # Problems detected

    finally:
        driver.close()


if __name__ == "__main__":
    sys.exit(main())
