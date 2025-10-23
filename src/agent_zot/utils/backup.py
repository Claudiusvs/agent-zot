"""
Automated backup utilities for Qdrant and Neo4j databases.

Provides snapshot and dump capabilities with multiple automation options:
- Manual: On-demand backups via CLI
- Scheduled: Cron-based periodic backups
- Event-driven: Backup after library updates

Best practices based on:
- Qdrant snapshots documentation
- Neo4j backup/restore procedures
- Docker volume persistence patterns
"""

import subprocess
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
import requests
import shutil

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages backups for Qdrant vector database and Neo4j knowledge graph."""

    def __init__(
        self,
        backup_root: Path,
        qdrant_url: str = "http://localhost:6333",
        neo4j_container: str = "agent-zot-neo4j",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "demodemo",
        neo4j_database: str = "neo4j"
    ):
        """
        Initialize backup manager.

        Args:
            backup_root: Root directory for backups
            qdrant_url: Qdrant API URL
            neo4j_container: Neo4j Docker container name
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            neo4j_database: Neo4j database name
        """
        self.backup_root = Path(backup_root)
        self.qdrant_url = qdrant_url
        self.neo4j_container = neo4j_container
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.neo4j_database = neo4j_database

        # Create backup directories
        self.qdrant_backup_dir = self.backup_root / "qdrant"
        self.neo4j_backup_dir = self.backup_root / "neo4j"
        self.qdrant_backup_dir.mkdir(parents=True, exist_ok=True)
        self.neo4j_backup_dir.mkdir(parents=True, exist_ok=True)

    def create_qdrant_snapshot(
        self,
        collection_name: str = "zotero_library_qdrant",
        download: bool = True,
        cleanup_old: bool = True,
        keep_last: int = 5
    ) -> Dict[str, Any]:
        """
        Create Qdrant snapshot and optionally download it.

        Args:
            collection_name: Name of Qdrant collection
            download: Whether to download snapshot to local backup dir
            cleanup_old: Whether to remove old snapshots
            keep_last: Number of recent snapshots to keep

        Returns:
            Dictionary with snapshot info and status
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        try:
            # Create snapshot using Qdrant API
            logger.info(f"Creating Qdrant snapshot for collection '{collection_name}'...")
            response = requests.post(
                f"{self.qdrant_url}/collections/{collection_name}/snapshots",
                timeout=300  # 5 minute timeout for large collections
            )
            response.raise_for_status()

            snapshot_info = response.json()
            snapshot_name = snapshot_info["result"]["name"]

            logger.info(f"Snapshot created: {snapshot_name}")

            result = {
                "status": "success",
                "collection": collection_name,
                "snapshot_name": snapshot_name,
                "timestamp": timestamp,
                "downloaded": False,
                "local_path": None
            }

            # Download snapshot if requested
            if download:
                download_result = self._download_qdrant_snapshot(
                    collection_name, snapshot_name, timestamp
                )
                result.update(download_result)

            # Cleanup old snapshots if requested
            if cleanup_old:
                self._cleanup_old_qdrant_snapshots(collection_name, keep_last)

            return result

        except Exception as e:
            logger.error(f"Error creating Qdrant snapshot: {e}")
            return {
                "status": "error",
                "error": str(e),
                "collection": collection_name,
                "timestamp": timestamp
            }

    def _download_qdrant_snapshot(
        self,
        collection_name: str,
        snapshot_name: str,
        timestamp: str
    ) -> Dict[str, Any]:
        """Download Qdrant snapshot to local backup directory."""
        try:
            logger.info(f"Downloading snapshot '{snapshot_name}'...")

            # Download snapshot
            response = requests.get(
                f"{self.qdrant_url}/collections/{collection_name}/snapshots/{snapshot_name}",
                stream=True,
                timeout=600  # 10 minute timeout for downloads
            )
            response.raise_for_status()

            # Save to local backup directory
            local_filename = f"{collection_name}-backup-{timestamp}.snapshot"
            local_path = self.qdrant_backup_dir / local_filename

            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            file_size_mb = local_path.stat().st_size / (1024 * 1024)
            logger.info(f"Snapshot downloaded: {local_path} ({file_size_mb:.1f} MB)")

            # Create backup info file
            info_file = self.qdrant_backup_dir / "BACKUP_INFO.md"
            with open(info_file, "w") as f:
                f.write(f"# Qdrant Backup Information\n\n")
                f.write(f"**Collection:** {collection_name}\n")
                f.write(f"**Timestamp:** {timestamp}\n")
                f.write(f"**Snapshot:** {snapshot_name}\n")
                f.write(f"**Local File:** {local_filename}\n")
                f.write(f"**Size:** {file_size_mb:.1f} MB\n\n")
                f.write(f"## Restore Command\n\n")
                f.write(f"```bash\n")
                f.write(f"# First, upload snapshot to Qdrant container\n")
                f.write(f"docker cp {local_path} <container>:/qdrant/snapshots/{collection_name}/\n\n")
                f.write(f"# Then restore via API\n")
                f.write(f"curl -X PUT '{self.qdrant_url}/collections/{collection_name}/snapshots/recover' \\\n")
                f.write(f"  -H 'Content-Type: application/json' \\\n")
                f.write(f"  -d '{{\"location\":\"file:///qdrant/snapshots/{collection_name}/{local_filename}\"}}'\n")
                f.write(f"```\n")

            return {
                "downloaded": True,
                "local_path": str(local_path),
                "size_mb": file_size_mb
            }

        except Exception as e:
            logger.error(f"Error downloading snapshot: {e}")
            return {
                "downloaded": False,
                "download_error": str(e)
            }

    def _cleanup_old_qdrant_snapshots(self, collection_name: str, keep_last: int):
        """Remove old Qdrant snapshots, keeping only the most recent N."""
        try:
            # Get all snapshot files
            snapshots = sorted(
                self.qdrant_backup_dir.glob(f"{collection_name}-backup-*.snapshot"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            # Remove old snapshots
            for old_snapshot in snapshots[keep_last:]:
                logger.info(f"Removing old snapshot: {old_snapshot.name}")
                old_snapshot.unlink()

        except Exception as e:
            logger.warning(f"Error cleaning up old snapshots: {e}")

    def create_neo4j_dump(
        self,
        cleanup_old: bool = True,
        keep_last: int = 5
    ) -> Dict[str, Any]:
        """
        Create Neo4j database dump.

        Args:
            cleanup_old: Whether to remove old dumps
            keep_last: Number of recent dumps to keep

        Returns:
            Dictionary with dump info and status
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        dump_filename = f"neo4j-{self.neo4j_database}-{timestamp}.dump"

        import time

        try:
            logger.info(f"Creating Neo4j dump for database '{self.neo4j_database}'...")
            logger.warning(f"⚠️  Neo4j will be briefly unavailable during backup")
            logger.warning(f"⚠️  Do not query Neo4j for the next ~60 seconds")

            # Get Neo4j version from container
            get_version = subprocess.run(
                ["docker", "inspect", "--format={{.Config.Image}}", self.neo4j_container],
                capture_output=True, text=True
            )
            neo4j_image = get_version.stdout.strip() if get_version.returncode == 0 else "neo4j:latest"

            # Create dump using temporary container with same volumes
            # This is safer than stopping the main container
            logger.info("Creating dump via temporary container (1-2 minutes)...")

            # First, stop the main container to ensure clean dump
            logger.info("Stopping main Neo4j container...")
            subprocess.run(["docker", "stop", self.neo4j_container], capture_output=True, timeout=60)
            time.sleep(3)

            # Run dump in temporary container
            # Save to /data which is the shared volume
            cmd_dump = [
                "docker", "run",
                "--rm",
                "--volumes-from", self.neo4j_container,
                neo4j_image,
                "neo4j-admin", "database", "dump",
                self.neo4j_database,
                "--to-path=/data",
                "--overwrite-destination=true"
            ]

            result = subprocess.run(
                cmd_dump,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )

            if result.returncode != 0:
                # Restart container before raising error
                logger.error("Dump failed, restarting container...")
                subprocess.run(["docker", "start", self.neo4j_container], capture_output=True)
                time.sleep(10)
                raise Exception(f"Neo4j dump failed: {result.stderr}")

            # Dump succeeded, copy it out before restarting
            # The dump is saved to /data/<database>.dump
            dump_path_container = f"/data/{self.neo4j_database}.dump"
            logger.info(f"Dump created, copying from container...")

            # Copy dump to host via docker cp from the main container (which has the volume)
            local_path = self.neo4j_backup_dir / dump_filename
            cmd_copy = [
                "docker", "cp",
                f"{self.neo4j_container}:{dump_path_container}",
                str(local_path)
            ]
            copy_result = subprocess.run(cmd_copy, capture_output=True, text=True)

            if copy_result.returncode != 0:
                # Try to restart anyway
                logger.error("Copy failed, restarting container...")
                subprocess.run(["docker", "start", self.neo4j_container], capture_output=True)
                time.sleep(10)
                raise Exception(f"Failed to copy dump: {copy_result.stderr}")

            # Restart the main container
            logger.info("Restarting main Neo4j container...")
            subprocess.run(["docker", "start", self.neo4j_container], capture_output=True, timeout=60)

            # Wait for Neo4j to come back online
            logger.info("Waiting for Neo4j to come back online...")
            time.sleep(15)

            logger.info(f"✅ Backup complete, Neo4j is back online")

            # Get file size (local_path was already set earlier)
            file_size_mb = local_path.stat().st_size / (1024 * 1024)
            logger.info(f"Neo4j dump saved: {local_path} ({file_size_mb:.1f} MB)")

            # Get database statistics
            stats = self._get_neo4j_stats()

            # Create backup info file
            info_file = self.neo4j_backup_dir / f"BACKUP_INFO_{timestamp}.md"
            with open(info_file, "w") as f:
                f.write(f"# Neo4j Backup Information\n\n")
                f.write(f"**Database:** {self.neo4j_database}\n")
                f.write(f"**Timestamp:** {timestamp}\n")
                f.write(f"**Dump File:** {dump_filename}\n")
                f.write(f"**Size:** {file_size_mb:.1f} MB\n\n")
                f.write(f"## Database Statistics\n\n")
                f.write(f"- **Nodes:** {stats.get('nodes', 'N/A'):,}\n")
                f.write(f"- **Relationships:** {stats.get('relationships', 'N/A'):,}\n\n")
                if stats.get('node_breakdown'):
                    f.write(f"### Node Types\n\n")
                    for node_type, count in stats['node_breakdown'][:10]:
                        f.write(f"- {node_type}: {count:,}\n")
                    f.write(f"\n")
                f.write(f"## Restore Command\n\n")
                f.write(f"```bash\n")
                f.write(f"# Stop Neo4j\n")
                f.write(f"docker exec {self.neo4j_container} neo4j stop\n\n")
                f.write(f"# Copy dump to container\n")
                f.write(f"docker cp {local_path} {self.neo4j_container}:/tmp/\n\n")
                f.write(f"# Load dump\n")
                f.write(f"docker exec {self.neo4j_container} neo4j-admin database load \\\n")
                f.write(f"  --from-path=/tmp \\\n")
                f.write(f"  --database={self.neo4j_database} \\\n")
                f.write(f"  --overwrite-destination=true\n\n")
                f.write(f"# Start Neo4j\n")
                f.write(f"docker exec {self.neo4j_container} neo4j start\n")
                f.write(f"```\n")

            # Cleanup old dumps if requested
            if cleanup_old:
                self._cleanup_old_neo4j_dumps(keep_last)

            # Remove dump from container
            subprocess.run(
                ["docker", "exec", self.neo4j_container, "rm", dump_path_container],
                capture_output=True
            )

            return {
                "status": "success",
                "database": self.neo4j_database,
                "timestamp": timestamp,
                "local_path": str(local_path),
                "size_mb": file_size_mb,
                "stats": stats
            }

        except Exception as e:
            logger.error(f"Error creating Neo4j dump: {e}")
            return {
                "status": "error",
                "error": str(e),
                "database": self.neo4j_database,
                "timestamp": timestamp
            }

    def _get_neo4j_stats(self) -> Dict[str, Any]:
        """Get Neo4j database statistics."""
        try:
            # Count nodes
            cmd_nodes = [
                "docker", "exec", self.neo4j_container,
                "cypher-shell",
                "-u", self.neo4j_user,
                "-p", self.neo4j_password,
                "MATCH (n) RETURN count(n) as total"
            ]
            result = subprocess.run(cmd_nodes, capture_output=True, text=True)
            nodes = int(result.stdout.strip().split('\n')[-1])

            # Count relationships
            cmd_rels = [
                "docker", "exec", self.neo4j_container,
                "cypher-shell",
                "-u", self.neo4j_user,
                "-p", self.neo4j_password,
                "MATCH ()-[r]->() RETURN count(r) as total"
            ]
            result = subprocess.run(cmd_rels, capture_output=True, text=True)
            relationships = int(result.stdout.strip().split('\n')[-1])

            # Node breakdown
            cmd_breakdown = [
                "docker", "exec", self.neo4j_container,
                "cypher-shell",
                "-u", self.neo4j_user,
                "-p", self.neo4j_password,
                "MATCH (n) RETURN labels(n)[0] as type, count(n) as count ORDER BY count DESC LIMIT 10"
            ]
            result = subprocess.run(cmd_breakdown, capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            node_breakdown = []
            for line in lines:
                if ', ' in line:
                    parts = line.split(', ')
                    if len(parts) == 2:
                        node_type = parts[0].strip('"')
                        count = int(parts[1])
                        node_breakdown.append((node_type, count))

            return {
                "nodes": nodes,
                "relationships": relationships,
                "node_breakdown": node_breakdown
            }

        except Exception as e:
            logger.warning(f"Error getting Neo4j stats: {e}")
            return {}

    def _cleanup_old_neo4j_dumps(self, keep_last: int):
        """Remove old Neo4j dumps, keeping only the most recent N."""
        try:
            # Get all dump files
            dumps = sorted(
                self.neo4j_backup_dir.glob(f"neo4j-{self.neo4j_database}-*.dump"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            # Remove old dumps
            for old_dump in dumps[keep_last:]:
                logger.info(f"Removing old dump: {old_dump.name}")
                old_dump.unlink()
                # Also remove corresponding info file
                info_file = old_dump.parent / f"BACKUP_INFO_{old_dump.stem.split('-')[-1]}.md"
                if info_file.exists():
                    info_file.unlink()

        except Exception as e:
            logger.warning(f"Error cleaning up old dumps: {e}")

    def backup_all(
        self,
        qdrant_collections: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Backup both Qdrant and Neo4j.

        Args:
            qdrant_collections: List of Qdrant collections to backup (default: ["zotero_library_qdrant"])
            **kwargs: Additional arguments passed to backup methods

        Returns:
            Dictionary with backup results for all databases
        """
        if qdrant_collections is None:
            qdrant_collections = ["zotero_library_qdrant"]

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"Starting full backup at {timestamp}")

        results = {
            "timestamp": timestamp,
            "qdrant": [],
            "neo4j": None
        }

        # Backup Qdrant collections
        for collection in qdrant_collections:
            result = self.create_qdrant_snapshot(collection, **kwargs)
            results["qdrant"].append(result)

        # Backup Neo4j
        results["neo4j"] = self.create_neo4j_dump(**kwargs)

        logger.info("Full backup completed")
        return results

    def list_backups(self) -> Dict[str, List[Dict[str, Any]]]:
        """List all available backups."""
        backups = {
            "qdrant": [],
            "neo4j": []
        }

        # List Qdrant snapshots
        for snapshot_path in sorted(self.qdrant_backup_dir.glob("*.snapshot"), reverse=True):
            stat = snapshot_path.stat()
            backups["qdrant"].append({
                "filename": snapshot_path.name,
                "path": str(snapshot_path),
                "size_mb": stat.st_size / (1024 * 1024),
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })

        # List Neo4j dumps
        for dump_path in sorted(self.neo4j_backup_dir.glob("*.dump"), reverse=True):
            stat = dump_path.stat()
            backups["neo4j"].append({
                "filename": dump_path.name,
                "path": str(dump_path),
                "size_mb": stat.st_size / (1024 * 1024),
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })

        return backups


def create_backup_manager(config_path: Optional[str] = None) -> BackupManager:
    """
    Create BackupManager from agent-zot configuration.

    Args:
        config_path: Path to config.json (default: ~/.config/agent-zot/config.json)

    Returns:
        Configured BackupManager instance
    """
    if config_path is None:
        config_path = Path.home() / ".config" / "agent-zot" / "config.json"
    else:
        config_path = Path(config_path)

    # Load config
    with open(config_path) as f:
        config = json.load(f)

    # Determine backup root
    backup_root = Path(__file__).parent.parent.parent.parent / "backups"

    # Get Qdrant config
    qdrant_url = config.get("semantic_search", {}).get("qdrant_url", "http://localhost:6333")

    # Get Neo4j config
    neo4j_config = config.get("neo4j_graphrag", {})
    neo4j_uri = neo4j_config.get("neo4j_uri", "neo4j://127.0.0.1:7687")
    neo4j_user = neo4j_config.get("neo4j_user", "neo4j")
    neo4j_password = neo4j_config.get("neo4j_password", "demodemo")
    neo4j_database = neo4j_config.get("neo4j_database", "neo4j")

    return BackupManager(
        backup_root=backup_root,
        qdrant_url=qdrant_url,
        neo4j_container="agent-zot-neo4j",
        neo4j_user=neo4j_user,
        neo4j_password=neo4j_password,
        neo4j_database=neo4j_database
    )
