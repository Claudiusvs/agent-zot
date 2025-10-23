#!/usr/bin/env python3
"""
CLI tool for backing up Qdrant and Neo4j databases.

Usage:
    python scripts/backup.py backup-all              # Backup everything
    python scripts/backup.py backup-qdrant           # Backup Qdrant only
    python scripts/backup.py backup-neo4j            # Backup Neo4j only
    python scripts/backup.py list                    # List available backups
    python scripts/backup.py restore-qdrant <file>   # Restore Qdrant from snapshot
"""

import sys
import argparse
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent_zot.utils.backup import create_backup_manager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cmd_backup_all(args):
    """Backup both Qdrant and Neo4j."""
    manager = create_backup_manager()

    logger.info("Starting full backup...")
    results = manager.backup_all(
        cleanup_old=not args.no_cleanup,
        keep_last=args.keep_last
    )

    # Display results
    print("\n=== Backup Results ===\n")

    # Qdrant
    for qresult in results["qdrant"]:
        if qresult["status"] == "success":
            print(f"✅ Qdrant ({qresult['collection']})")
            if qresult.get("downloaded"):
                print(f"   Snapshot: {qresult['snapshot_name']}")
                print(f"   Local: {qresult['local_path']}")
                print(f"   Size: {qresult['size_mb']:.1f} MB")
        else:
            print(f"❌ Qdrant ({qresult['collection']}): {qresult.get('error')}")

    print()

    # Neo4j
    nresult = results["neo4j"]
    if nresult["status"] == "success":
        print(f"✅ Neo4j ({nresult['database']})")
        print(f"   Dump: {Path(nresult['local_path']).name}")
        print(f"   Size: {nresult['size_mb']:.1f} MB")
        if nresult.get("stats"):
            print(f"   Nodes: {nresult['stats']['nodes']:,}")
            print(f"   Relationships: {nresult['stats']['relationships']:,}")
    else:
        print(f"❌ Neo4j ({nresult['database']}): {nresult.get('error')}")

    print()


def cmd_backup_qdrant(args):
    """Backup Qdrant only."""
    manager = create_backup_manager()

    logger.info(f"Backing up Qdrant collection '{args.collection}'...")
    result = manager.create_qdrant_snapshot(
        collection_name=args.collection,
        cleanup_old=not args.no_cleanup,
        keep_last=args.keep_last
    )

    print("\n=== Qdrant Backup Result ===\n")
    if result["status"] == "success":
        print(f"✅ Success!")
        print(f"   Snapshot: {result['snapshot_name']}")
        if result.get("downloaded"):
            print(f"   Local: {result['local_path']}")
            print(f"   Size: {result['size_mb']:.1f} MB")
    else:
        print(f"❌ Failed: {result.get('error')}")

    print()


def cmd_backup_neo4j(args):
    """Backup Neo4j only."""
    manager = create_backup_manager()

    logger.info(f"Backing up Neo4j database '{manager.neo4j_database}'...")
    result = manager.create_neo4j_dump(
        cleanup_old=not args.no_cleanup,
        keep_last=args.keep_last
    )

    print("\n=== Neo4j Backup Result ===\n")
    if result["status"] == "success":
        print(f"✅ Success!")
        print(f"   Dump: {Path(result['local_path']).name}")
        print(f"   Size: {result['size_mb']:.1f} MB")
        if result.get("stats"):
            print(f"   Nodes: {result['stats']['nodes']:,}")
            print(f"   Relationships: {result['stats']['relationships']:,}")
    else:
        print(f"❌ Failed: {result.get('error')}")

    print()


def cmd_list(args):
    """List available backups."""
    manager = create_backup_manager()
    backups = manager.list_backups()

    print("\n=== Available Backups ===\n")

    print("Qdrant Snapshots:")
    if backups["qdrant"]:
        for backup in backups["qdrant"]:
            print(f"  • {backup['filename']}")
            print(f"    {backup['size_mb']:.1f} MB - {backup['modified']}")
    else:
        print("  (none)")

    print("\nNeo4j Dumps:")
    if backups["neo4j"]:
        for backup in backups["neo4j"]:
            print(f"  • {backup['filename']}")
            print(f"    {backup['size_mb']:.1f} MB - {backup['modified']}")
    else:
        print("  (none)")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="Backup and restore Qdrant and Neo4j databases"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # backup-all command
    parser_all = subparsers.add_parser("backup-all", help="Backup both Qdrant and Neo4j")
    parser_all.add_argument("--no-cleanup", action="store_true", help="Don't remove old backups")
    parser_all.add_argument("--keep-last", type=int, default=5, help="Number of backups to keep (default: 5)")
    parser_all.set_defaults(func=cmd_backup_all)

    # backup-qdrant command
    parser_qdrant = subparsers.add_parser("backup-qdrant", help="Backup Qdrant only")
    parser_qdrant.add_argument("--collection", default="zotero_library_qdrant", help="Collection name")
    parser_qdrant.add_argument("--no-cleanup", action="store_true", help="Don't remove old backups")
    parser_qdrant.add_argument("--keep-last", type=int, default=5, help="Number of backups to keep (default: 5)")
    parser_qdrant.set_defaults(func=cmd_backup_qdrant)

    # backup-neo4j command
    parser_neo4j = subparsers.add_parser("backup-neo4j", help="Backup Neo4j only")
    parser_neo4j.add_argument("--no-cleanup", action="store_true", help="Don't remove old backups")
    parser_neo4j.add_argument("--keep-last", type=int, default=5, help="Number of backups to keep (default: 5)")
    parser_neo4j.set_defaults(func=cmd_backup_neo4j)

    # list command
    parser_list = subparsers.add_parser("list", help="List available backups")
    parser_list.set_defaults(func=cmd_list)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
