"""
zot_manage_database - Unified database management with natural language interface

This module provides a unified tool for managing Qdrant and Neo4j databases
using natural language commands. It supports update, backup, restore, inspect,
and monitoring operations.

Usage Examples:
    # Update operations
    zot_manage_database("update database")
    zot_manage_database("force rebuild", confirm=True)
    zot_manage_database("test on 10 papers")
    zot_manage_database("papers from last week")
    zot_manage_database("retry failed items")
    zot_manage_database("update without fulltext")

    # Backup/Restore operations
    zot_manage_database("backup databases")
    zot_manage_database("backup locally only")
    zot_manage_database("restore from latest backup", confirm=True)
    zot_manage_database("restore from icloud", confirm=True)
    zot_manage_database("show available backups")

    # Monitoring operations
    zot_manage_database("show status")
    zot_manage_database("inspect database")
    zot_manage_database("find papers about attention")
    zot_manage_database("show statistics")

    # Control operations
    zot_manage_database("cancel update")
"""

from typing import Optional
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from fastmcp import Context


# ===== HELPER FUNCTIONS =====

def _extract_number_from_query(query: str) -> Optional[int]:
    """Extract number for limit: 'test on 10 papers' → 10"""
    import re
    match = re.search(r'\b(\d+)\b', query)
    return int(match.group(1)) if match else None


def _extract_date_from_query(query: str) -> Optional[str]:
    """
    Extract date from query and convert to ISO format.

    Supports:
    - Relative: "last week", "yesterday", "3 days ago"
    - Absolute: "November 1", "2025-11-01", "Nov 1"

    Returns ISO date string or None
    """
    from datetime import datetime, timedelta
    import re

    query_lower = query.lower()

    # Relative dates
    if "last week" in query_lower:
        date = datetime.now() - timedelta(days=7)
        return date.strftime("%Y-%m-%d")
    elif "yesterday" in query_lower:
        date = datetime.now() - timedelta(days=1)
        return date.strftime("%Y-%m-%d")
    elif match := re.search(r'(\d+)\s+days?\s+ago', query_lower):
        days = int(match.group(1))
        date = datetime.now() - timedelta(days=days)
        return date.strftime("%Y-%m-%d")

    # Absolute dates - ISO format (YYYY-MM-DD)
    if match := re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', query):
        return match.group(0)

    # Month name format (November 1, Nov 1)
    month_names = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'june': 6,
        'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
    }

    for month_name, month_num in month_names.items():
        pattern = rf'{month_name}\s+(\d{{1,2}})'
        if match := re.search(pattern, query_lower):
            day = int(match.group(1))
            year = datetime.now().year
            return f"{year}-{month_num:02d}-{day:02d}"

    return None


def _extract_filter_from_query(query: str) -> Optional[str]:
    """Extract filter text: 'find papers about attention' → 'attention'"""
    import re

    # Patterns for filter extraction
    patterns = [
        r'about\s+(.+)',
        r'for\s+(.+)',
        r'containing\s+(.+)',
        r'with\s+(.+)',
        r'titled\s+(.+)',
        r'called\s+(.+)',
    ]

    query_lower = query.lower()
    for pattern in patterns:
        if match := re.search(pattern, query_lower):
            filter_text = match.group(1).strip()
            # Remove trailing words like "in the database", "from the library", etc.
            filter_text = re.sub(r'\s+(in|from|on)\s+the\s+\w+$', '', filter_text)
            return filter_text

    return None


def _extract_backup_source(query: str) -> str:
    """Extract backup source: 'restore from icloud' → 'icloud'"""
    import re

    query_lower = query.lower()

    if "icloud" in query_lower:
        return "icloud"

    # Check for timestamp pattern (YYYYMMDD-HHMMSS)
    if match := re.search(r'(\d{8}-\d{6})', query):
        return match.group(1)

    return "latest"


def _execute_backup(include_icloud: bool, ctx: Context) -> str:
    """
    Execute backup operation for Qdrant and Neo4j databases.

    Args:
        include_icloud: Whether to sync backups to iCloud Drive
        ctx: MCP context

    Returns:
        Formatted backup results
    """
    from agent_zot.utils.backup import create_backup_manager
    from pathlib import Path
    import subprocess

    try:
        ctx.info("Creating database backups...")

        # Create backup manager and execute backup
        manager = create_backup_manager()
        results = manager.backup_all(cleanup_old=True, keep_last=5)

        # Format results
        output = ["# Database Backup Results", ""]

        # Qdrant results
        output.append("## Qdrant Vector Database")
        for qresult in results["qdrant"]:
            if qresult["status"] == "success":
                output.append(f"✅ **Collection**: {qresult['collection']}")
                output.append(f"   - Snapshot: `{qresult['snapshot_name']}`")
                output.append(f"   - Size: {qresult['size_mb']:.1f} MB")
                output.append(f"   - Path: `{qresult['local_path']}`")
            else:
                output.append(f"❌ **Error**: {qresult.get('error')}")

        output.append("")

        # Neo4j results
        output.append("## Neo4j Knowledge Graph")
        nresult = results["neo4j"]
        if nresult["status"] == "success":
            output.append(f"✅ **Database**: {nresult['database']}")
            output.append(f"   - Size: {nresult['size_mb']:.1f} MB")
            if nresult.get('stats'):
                output.append(f"   - Nodes: {nresult['stats']['nodes']:,}")
                output.append(f"   - Relationships: {nresult['stats']['relationships']:,}")
            output.append(f"   - Path: `{nresult['local_path']}`")
        else:
            output.append(f"❌ **Error**: {nresult.get('error')}")

        # iCloud sync
        if include_icloud:
            output.append("")
            output.append("## iCloud Drive Sync")
            ctx.info("Syncing backups to iCloud Drive...")

            script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "sync-to-icloud.sh"
            if script_path.exists():
                result = subprocess.run([str(script_path)], capture_output=True, text=True, timeout=120)
                if result.returncode == 0:
                    output.append("✅ **Synced to iCloud Drive**")
                    output.append(f"   - Location: `~/Library/Mobile Documents/com~apple~CloudDocs/agent-zot-backups/`")
                else:
                    output.append("⚠️ **iCloud sync failed** (local backups still created)")
                    if result.stderr:
                        output.append(f"   - Error: {result.stderr[:200]}")
            else:
                output.append("⚠️ **iCloud sync script not found**")
                output.append(f"   - Expected: `{script_path}`")

        output.append("")
        output.append("---")
        output.append("✅ **Backup complete!** Databases safely backed up.")

        return "\n".join(output)

    except Exception as e:
        ctx.error(f"Backup failed: {str(e)}")
        return f"❌ **Backup error**: {str(e)}\n\nPlease check logs and try again."


def _list_available_backups(ctx: Context) -> str:
    """
    List all available backups (local and iCloud).

    Args:
        ctx: MCP context

    Returns:
        Formatted list of backups
    """
    from agent_zot.utils.backup import create_backup_manager
    from pathlib import Path

    try:
        ctx.info("Listing available backups...")

        manager = create_backup_manager()
        backups = manager.list_backups()

        output = ["# Available Backups", ""]

        # Local Qdrant backups
        output.append("## Qdrant Backups (Local)")
        if backups.get("qdrant"):
            for backup in backups["qdrant"][:10]:  # Show last 10
                output.append(f"- **{backup['timestamp']}**")
                output.append(f"  - Collection: {backup['collection']}")
                output.append(f"  - Size: {backup['size_mb']:.1f} MB")
                output.append(f"  - Path: `{backup['path']}`")
        else:
            output.append("*No Qdrant backups found*")

        output.append("")

        # Local Neo4j backups
        output.append("## Neo4j Backups (Local)")
        if backups.get("neo4j"):
            for backup in backups["neo4j"][:10]:  # Show last 10
                output.append(f"- **{backup['timestamp']}**")
                output.append(f"  - Database: {backup['database']}")
                output.append(f"  - Size: {backup['size_mb']:.1f} MB")
                if backup.get('nodes'):
                    output.append(f"  - Nodes: {backup['nodes']:,}, Relationships: {backup['relationships']:,}")
                output.append(f"  - Path: `{backup['path']}`")
        else:
            output.append("*No Neo4j backups found*")

        output.append("")

        # iCloud backups
        output.append("## iCloud Drive Backups")
        icloud_path = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "agent-zot-backups"

        if icloud_path.exists():
            # List iCloud backups
            qdrant_icloud = list((icloud_path / "qdrant").glob("*.tar.gz")) if (icloud_path / "qdrant").exists() else []
            neo4j_icloud = list((icloud_path / "neo4j").glob("*.dump")) if (icloud_path / "neo4j").exists() else []

            if qdrant_icloud or neo4j_icloud:
                output.append(f"✅ **iCloud backups available** ({len(qdrant_icloud)} Qdrant, {len(neo4j_icloud)} Neo4j)")
                output.append(f"   - Location: `{icloud_path}`")
            else:
                output.append("⚠️ **iCloud directory exists but no backups found**")
        else:
            output.append("⚠️ **iCloud backup directory not found**")
            output.append("   - Run `agent-zot backup-all` to create first backup")

        output.append("")
        output.append("---")
        output.append("💡 **Tip**: To restore from a backup, use:")
        output.append("```")
        output.append('zot_manage_database("restore from latest backup", confirm=True)')
        output.append("```")

        return "\n".join(output)

    except Exception as e:
        ctx.error(f"Failed to list backups: {str(e)}")
        return f"❌ **Error listing backups**: {str(e)}"


def _inspect_database(filter_text: Optional[str], ctx: Context) -> str:
    """
    Inspect indexed papers in Qdrant database.

    Args:
        filter_text: Optional text filter to search papers
        ctx: MCP context

    Returns:
        Formatted list of indexed papers
    """
    try:
        from agent_zot.search.semantic import create_semantic_search
        from pathlib import Path

        config_path = Path.home() / ".config" / "agent-zot" / "config.json"
        search = create_semantic_search(str(config_path))

        if filter_text:
            # Use semantic search to find papers
            ctx.info(f"Searching for papers about: {filter_text}")
            results = search.search(query=filter_text, limit=10)

            output = []
            output.append(f"# 🔍 Database Inspection - Search Results")
            output.append(f"")
            output.append(f"**Query**: {filter_text}")
            output.append(f"**Results**: {len(results)} papers")
            output.append(f"")

            for i, result in enumerate(results, 1):
                output.append(f"## {i}. {result.get('title', 'Untitled')}")
                output.append(f"- **Authors**: {', '.join(result.get('authors', []))}")
                output.append(f"- **Year**: {result.get('year', 'N/A')}")
                output.append(f"- **Key**: `{result.get('item_key', 'N/A')}`")
                output.append(f"- **Relevance**: {result.get('score', 0):.3f}")
                output.append(f"")

            return "\n".join(output)

        else:
            # Show recent indexed papers
            ctx.info("Listing recently indexed papers...")

            # Get database status for counts
            status = search.get_database_status()
            collection_info = status.get("collection_info", {})
            total_count = collection_info.get("count", 0)

            output = []
            output.append(f"# 🔍 Database Inspection - Overview")
            output.append(f"")
            output.append(f"**Total indexed chunks**: {total_count:,}")
            output.append(f"**Embedding model**: {collection_info.get('embedding_model', 'Unknown')}")
            output.append(f"")
            output.append(f"## 💡 Usage")
            output.append(f"")
            output.append(f"To search for specific papers:")
            output.append(f"```")
            output.append(f'zot_manage_database("find papers about neural networks")')
            output.append(f"```")
            output.append(f"")
            output.append(f"To get complete statistics:")
            output.append(f"```")
            output.append(f'zot_manage_database("show statistics")')
            output.append(f"```")

            return "\n".join(output)

    except Exception as e:
        ctx.error(f"Database inspection failed: {str(e)}")
        return f"❌ **Error during inspection**: {str(e)}"


def _get_database_statistics(ctx: Context) -> str:
    """
    Get aggregate statistics about indexed papers.

    Args:
        ctx: MCP context

    Returns:
        Formatted statistics report
    """
    try:
        from agent_zot.search.semantic import create_semantic_search
        from pathlib import Path

        config_path = Path.home() / ".config" / "agent-zot" / "config.json"
        search = create_semantic_search(str(config_path))

        # Get database status
        status = search.get_database_status()
        collection_info = status.get("collection_info", {})

        output = []
        output.append(f"# 📊 Database Statistics")
        output.append(f"")

        # Qdrant statistics
        output.append(f"## 🗄️ Qdrant (Vector Database)")
        output.append(f"")
        output.append(f"- **Collection**: {collection_info.get('name', 'Unknown')}")
        output.append(f"- **Total chunks**: {collection_info.get('count', 0):,}")
        output.append(f"- **Embedding model**: {collection_info.get('embedding_model', 'Unknown')}")
        output.append(f"- **Vector dimensions**: {collection_info.get('vector_size', 'Unknown')}")
        output.append(f"")

        # Neo4j statistics (if available)
        try:
            import subprocess
            cmd = [
                "docker", "exec", "agent-zot-neo4j",
                "cypher-shell", "-u", "neo4j", "-p", "demodemo",
                "MATCH (n) RETURN count(n) as total"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            nodes = int(result.stdout.strip().split('\n')[-1])

            cmd_rels = [
                "docker", "exec", "agent-zot-neo4j",
                "cypher-shell", "-u", "neo4j", "-p", "demodemo",
                "MATCH ()-[r]->() RETURN count(r) as total"
            ]
            result = subprocess.run(cmd_rels, capture_output=True, text=True, timeout=10)
            relationships = int(result.stdout.strip().split('\n')[-1])

            output.append(f"## 🔗 Neo4j (Knowledge Graph)")
            output.append(f"")
            output.append(f"- **Nodes**: {nodes:,}")
            output.append(f"- **Relationships**: {relationships:,}")
            output.append(f"- **Status**: ✅ Online")
            output.append(f"")
        except Exception as e:
            output.append(f"## 🔗 Neo4j (Knowledge Graph)")
            output.append(f"")
            output.append(f"- **Status**: ⚠️  Unavailable ({str(e)})")
            output.append(f"")

        # Update configuration
        update_config = status.get("update_config", {})
        output.append(f"## 🔄 Update Configuration")
        output.append(f"")
        output.append(f"- **Auto-update**: {update_config.get('auto_update', False)}")
        output.append(f"- **Frequency**: {update_config.get('update_frequency', 'manual')}")
        output.append(f"- **Last update**: {update_config.get('last_update', 'Never')}")
        output.append(f"")

        return "\n".join(output)

    except Exception as e:
        ctx.error(f"Statistics failed: {str(e)}")
        return f"❌ **Error getting statistics**: {str(e)}"


def _execute_restore(backup_source: str, ctx: Context) -> str:
    """
    Execute database restore from backup files.

    Args:
        backup_source: "latest" or "icloud" to select backup source
        ctx: MCP context

    Returns:
        Formatted results of restore operation
    """
    from agent_zot.utils.backup import create_backup_manager
    from pathlib import Path

    try:
        manager = create_backup_manager()

        # Get list of available backups
        backups = manager.list_backups()

        if not backups["qdrant"] or not backups["neo4j"]:
            return "❌ **No backups found**. Create backups first using 'backup databases'."

        # Determine backup source location
        if backup_source == "icloud":
            # Check iCloud Drive for backups
            icloud_path = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "agent-zot-backups"

            if not icloud_path.exists():
                return f"❌ **iCloud backup directory not found**: {icloud_path}\n\nRun 'backup databases' first to sync to iCloud."

            # Find latest Qdrant and Neo4j backups in iCloud
            qdrant_backups = sorted(icloud_path.glob("qdrant/*.snapshot"), reverse=True)
            neo4j_backups = sorted(icloud_path.glob("neo4j/*.dump"), reverse=True)

            if not qdrant_backups or not neo4j_backups:
                return f"❌ **No backups found in iCloud**: {icloud_path}"

            qdrant_snapshot_path = str(qdrant_backups[0])
            neo4j_dump_path = str(neo4j_backups[0])
            source_label = "iCloud"

        else:  # latest (local)
            # Get latest local backups
            qdrant_snapshot_path = backups["qdrant"][0]["path"]
            neo4j_dump_path = backups["neo4j"][0]["path"]
            source_label = "local"

        # Get backup info for preview
        qdrant_info = backups["qdrant"][0]
        neo4j_info = backups["neo4j"][0]

        # Show dry-run preview with detailed backup info
        output = []
        output.append(f"# 📦 Database Restore - Dry Run Preview")
        output.append(f"")
        output.append(f"**Source**: {source_label} backups")
        output.append(f"")
        output.append(f"## 🗄️ Qdrant Backup")
        output.append(f"- **File**: `{Path(qdrant_snapshot_path).name}`")
        output.append(f"- **Size**: {qdrant_info['size_mb']:.1f} MB")
        output.append(f"- **Created**: {qdrant_info['modified']}")
        output.append(f"")
        output.append(f"## 🔗 Neo4j Backup")
        output.append(f"- **File**: `{Path(neo4j_dump_path).name}`")
        output.append(f"- **Size**: {neo4j_info['size_mb']:.1f} MB")
        output.append(f"- **Created**: {neo4j_info['modified']}")
        output.append(f"")
        output.append(f"## ⚠️ Restore Process")
        output.append(f"")
        output.append(f"This will:")
        output.append(f"1. **Delete** the current Qdrant collection")
        output.append(f"2. **Restore** Qdrant from snapshot (~30-60 seconds)")
        output.append(f"3. **Stop** Neo4j container (~5 seconds)")
        output.append(f"4. **Restore** Neo4j database (~60-90 seconds)")
        output.append(f"5. **Restart** Neo4j container (~15 seconds)")
        output.append(f"")
        output.append(f"**Total downtime**: ~2-3 minutes")
        output.append(f"")
        output.append(f"⚠️  **This will permanently replace your current databases with the backup data.**")

        preview_msg = "\n".join(output)

        # Log the preview to context
        ctx.info(preview_msg)

        # Execute restore
        ctx.info("Starting database restore...")
        results = manager.restore_all(
            qdrant_snapshot_path=qdrant_snapshot_path,
            neo4j_dump_path=neo4j_dump_path
        )

        # Format results
        output = []
        output.append(f"# 📦 Database Restore Results")
        output.append(f"")
        output.append(f"**Timestamp**: {results['timestamp']}")
        output.append(f"")

        # Qdrant results
        output.append(f"## 🗄️ Qdrant")
        if results["qdrant"]["status"] == "success":
            output.append(f"✅ **Status**: Restored successfully")
            output.append(f"- **Collection**: {results['qdrant']['collection']}")
            output.append(f"- **Points**: {results['qdrant']['points_count']:,}")
            output.append(f"- **Snapshot**: {results['qdrant']['snapshot_file']}")
        else:
            output.append(f"❌ **Status**: Failed")
            output.append(f"- **Error**: {results['qdrant']['error']}")
        output.append(f"")

        # Neo4j results
        output.append(f"## 🔗 Neo4j")
        if results["neo4j"]["status"] == "success":
            output.append(f"✅ **Status**: Restored successfully")
            output.append(f"- **Database**: {results['neo4j']['database']}")
            output.append(f"- **Dump**: {results['neo4j']['dump_file']}")
            if results["neo4j"].get("stats"):
                stats = results["neo4j"]["stats"]
                output.append(f"- **Nodes**: {stats.get('nodes', 0):,}")
                output.append(f"- **Relationships**: {stats.get('relationships', 0):,}")
        else:
            output.append(f"❌ **Status**: Failed")
            output.append(f"- **Error**: {results['neo4j']['error']}")
        output.append(f"")

        # Overall status
        if results["qdrant"]["status"] == "success" and results["neo4j"]["status"] == "success":
            output.append(f"✅ **Overall**: Database restore completed successfully")
        elif results["qdrant"]["status"] == "success":
            output.append(f"⚠️  **Overall**: Qdrant restored, but Neo4j failed")
        else:
            output.append(f"❌ **Overall**: Restore failed")

        return "\n".join(output)

    except Exception as e:
        ctx.error(f"Restore failed: {str(e)}")
        return f"❌ **Error during restore**: {str(e)}"


# ===== MAIN FUNCTION =====

def zot_manage_database(
    query: str,
    force_mode: Optional[str] = None,
    confirm: bool = False,
    *,
    ctx: Context
) -> str:
    """
    Unified database management tool with natural language interface.

    Automatically detects intent and executes appropriate operation.

    **Update Operations**:
    - "update database" → Incremental update with fulltext
    - "force rebuild" → AUTO-BACKUP → full rebuild (requires confirm=True)
    - "test on 10 papers" → Test with limit
    - "papers from last week" → Modified-since filter
    - "retry failed items" → Reprocess failures
    - "update without fulltext" → Metadata only

    **Backup/Restore Operations**:
    - "backup databases" → Local + iCloud backup
    - "backup locally only" → Skip iCloud sync
    - "restore from latest backup" → Restore from most recent (requires confirm=True)
    - "restore from icloud" → Restore from iCloud backup (requires confirm=True)
    - "show available backups" → List all backups

    **Monitoring Operations**:
    - "show status" → Database health and stats
    - "inspect database" → View indexed documents
    - "find papers about X" → Search indexed papers
    - "show statistics" → Aggregate stats

    **Control Operations**:
    - "cancel update" → Stop current indexing (graceful)

    Args:
        query: Natural language command describing what to do
        force_mode: Override auto-detection (e.g., "rebuild", "backup", "restore")
        confirm: Must be True for destructive operations (rebuild, restore)
        ctx: MCP context

    Returns:
        Results of the database operation
    """
    try:
        # ===== INTENT DETECTION =====
        query_lower = query.lower()

        # Override mode if specified
        if force_mode:
            mode = force_mode

        # Backup/Restore operations (highest priority)
        elif any(word in query_lower for word in ["restore", "undo", "rollback"]):
            mode = "restore"
        elif "list backup" in query_lower or "show backup" in query_lower or "available backup" in query_lower:
            mode = "list_backups"
        elif any(word in query_lower for word in ["backup", "save", "snapshot"]):
            mode = "backup"

        # Update operations
        elif any(word in query_lower for word in ["rebuild", "scratch", "everything", "force"]):
            mode = "rebuild"
        elif any(word in query_lower for word in ["test", "try", "sample"]) and _extract_number_from_query(query):
            mode = "test"
        elif any(word in query_lower for word in ["retry", "failed", "error"]):
            mode = "retry"
        elif any(word in query_lower for word in ["since", "from", "after", "last week", "yesterday"]):
            mode = "modified_since"
        elif "metadata" in query_lower or "no fulltext" in query_lower or "without fulltext" in query_lower:
            mode = "metadata_only"

        # Monitoring operations
        elif any(word in query_lower for word in ["status", "info", "health"]):
            mode = "status"
        elif any(word in query_lower for word in ["stat", "aggregate", "distribution"]):
            mode = "statistics"
        elif any(word in query_lower for word in ["inspect", "show paper", "find paper", "search"]):
            mode = "inspect"

        # Control operations
        elif any(word in query_lower for word in ["cancel", "stop", "abort"]):
            mode = "cancel"

        # Default to safe incremental update
        else:
            mode = "update"

        ctx.info(f"Detected mode: {mode}")

        # ===== PARAMETER EXTRACTION =====
        limit = _extract_number_from_query(query) if mode == "test" else None
        date = _extract_date_from_query(query) if mode == "modified_since" else None
        filter_text = _extract_filter_from_query(query) if mode == "inspect" else None
        backup_source = _extract_backup_source(query) if mode == "restore" else "latest"
        include_icloud = "local" not in query_lower and "skip icloud" not in query_lower

        # ===== SAFETY CHECKS FOR DESTRUCTIVE OPERATIONS =====
        if mode == "rebuild" and not confirm:
            return f"""🔴 **DESTRUCTIVE OPERATION - CONFIRMATION REQUIRED**

**You requested**: Force rebuild entire database

**This will**:
1. ✅ Automatically backup databases first (local + iCloud)
2. 🔴 **DELETE** all existing Qdrant vectors
3. 🔴 **DELETE** all existing Neo4j entities and relationships
4. 🔄 Re-index all papers from scratch (estimated time: several hours)

**⚠️ Current indexed data will be deleted** (backup will be created first)

---

**Are you absolutely sure?**

To proceed, run:
```
zot_manage_database("force rebuild", confirm=True)
```

**💡 Alternative**: If you just want to add new papers without deleting anything:
```
zot_manage_database("update database")
```
(Incremental, safe, fast)
"""

        if mode == "restore" and not confirm:
            return f"""🔴 **DESTRUCTIVE OPERATION - CONFIRMATION REQUIRED**

**You requested**: Restore from backup ({backup_source})

**This will REPLACE current databases with backup data**

**⚠️ Current data will be PERMANENTLY REPLACED**

---

**Are you absolutely sure?**

**RECOMMENDED**: Backup current state first:
```
zot_manage_database("backup databases")
```

Then to proceed with restore:
```
zot_manage_database("restore from {backup_source}", confirm=True)
```

**💡 Alternative**: View available backups first:
```
zot_manage_database("show available backups")
```
"""

        # ===== EXECUTE OPERATION =====

        # For now, implement basic modes (status, update)
        # Other modes will be implemented in subsequent phases

        if mode == "status":
            # Get database status directly
            from agent_zot.search.semantic import create_semantic_search

            ctx.info("Getting semantic search database status...")
            config_path = Path.home() / ".config" / "agent-zot" / "config.json"
            search = create_semantic_search(str(config_path))
            status = search.get_database_status()

            # Format results
            output = ["# Semantic Search Database Status", ""]
            collection_info = status.get("collection_info", {})
            output.append("## Collection Information")
            output.append(f"**Name:** {collection_info.get('name', 'Unknown')}")
            output.append(f"**Document Count:** {collection_info.get('count', 0)}")
            output.append(f"**Embedding Model:** {collection_info.get('embedding_model', 'Unknown')}")
            output.append(f"**Database Path:** {collection_info.get('persist_directory', 'Unknown')}")

            if collection_info.get('error'):
                output.append(f"**Error:** {collection_info['error']}")

            output.append("")
            update_config = status.get("update_config", {})
            output.append("## Update Configuration")
            output.append(f"**Auto Update:** {update_config.get('auto_update', False)}")
            output.append(f"**Frequency:** {update_config.get('update_frequency', 'manual')}")
            output.append(f"**Last Update:** {update_config.get('last_update', 'Never')}")
            output.append(f"**Should Update Now:** {status.get('should_update', False)}")

            if update_config.get('update_days'):
                output.append(f"**Update Interval:** Every {update_config['update_days']} days")

            return "\n".join(output)

        elif mode in ["update", "test", "metadata_only"]:
            # Direct database update implementation
            from agent_zot.indexer.unified import UnifiedIndexer

            # Determine parameters based on mode
            force_rebuild = False
            extract_fulltext = mode != "metadata_only"
            update_limit = limit if mode == "test" else None

            ctx.info(f"Running database update: rebuild={force_rebuild}, fulltext={extract_fulltext}, limit={update_limit}")

            # Create indexer instance
            config_path = Path.home() / ".config" / "agent-zot" / "config.json"
            indexer = UnifiedIndexer(config_path=str(config_path))

            # Run update
            result = indexer.update_database(
                force_rebuild=force_rebuild,
                extract_fulltext=extract_fulltext,
                limit=update_limit
            )

            # Format result
            if result.get("success"):
                stats = result.get("statistics", {})
                return f"""✅ Database update completed successfully

**Papers Processed:** {stats.get('papers_indexed', 0)}
**Chunks Created:** {stats.get('chunks_created', 0)}
**Neo4j Entities:** {stats.get('neo4j_entities', 0)}
**Neo4j Relationships:** {stats.get('neo4j_relationships', 0)}
**Duration:** {stats.get('duration_seconds', 0):.1f}s
"""
            else:
                return f"❌ Database update failed: {result.get('error', 'Unknown error')}"

        elif mode == "rebuild":
            # Auto-backup before destructive rebuild
            ctx.info("🔴 Confirmation received. Proceeding with force rebuild...")
            ctx.info("📦 Step 1/2: Creating backup before rebuild...")

            # Execute backup (local + iCloud)
            backup_result = _execute_backup(include_icloud=include_icloud, ctx=ctx)

            # Check if backup succeeded
            if "❌" in backup_result or "Error" in backup_result:
                return f"""❌ **Auto-backup failed before rebuild**

{backup_result}

**Force rebuild ABORTED** (your current data is safe)

Please fix the backup issue and try again. You can also skip backup with:
```
# WARNING: This bypasses safety backup!
# Only use if you have manual backups
zot_manage_database("force rebuild locally only", confirm=True)
```
"""

            ctx.info("✅ Backup completed successfully")
            ctx.info("🔄 Step 2/2: Starting force rebuild...")

            # Now proceed with rebuild
            rebuild_result = update_search_database(
                force_rebuild=True,
                extract_fulltext=True,
                limit=None,
                ctx=ctx
            )

            # Combine backup + rebuild results
            return f"""# 🔄 Force Rebuild Complete

## 📦 Step 1: Auto-Backup (Completed)

{backup_result}

---

## 🔄 Step 2: Database Rebuild (Completed)

{rebuild_result}

---

✅ **Force rebuild completed with safety backup**
"""

        # Backup/Restore operations
        elif mode == "backup":
            return _execute_backup(include_icloud=include_icloud, ctx=ctx)

        elif mode == "list_backups":
            return _list_available_backups(ctx=ctx)

        elif mode == "restore":
            # Confirmation already checked above, proceed with restore
            ctx.info("🔴 Confirmation received. Proceeding with database restore...")
            return _execute_restore(backup_source=backup_source, ctx=ctx)

        # Phase 4 features (parameters added, full implementation pending)
        elif mode == "retry":
            # Pass retry_failed_only=True to trigger Phase 4 warning
            return update_search_database(
                force_rebuild=False,
                extract_fulltext=True,
                limit=None,
                retry_failed_only=True,
                ctx=ctx
            )

        elif mode == "modified_since":
            # Pass date to trigger Phase 4 warning
            return update_search_database(
                force_rebuild=False,
                extract_fulltext=True,
                limit=None,
                modified_since=date,
                ctx=ctx
            )

        elif mode == "cancel":
            # Pass cancel_flag to trigger Phase 4 warning
            return update_search_database(
                force_rebuild=False,
                extract_fulltext=True,
                limit=None,
                cancel_flag={"cancel": True},
                ctx=ctx
            )

        # Phase 6 features (database inspection and statistics)
        elif mode == "inspect":
            return _inspect_database(filter_text=filter_text, ctx=ctx)

        elif mode == "statistics":
            return _get_database_statistics(ctx=ctx)

        else:
            return f"Unknown mode: {mode}. This should not happen - please report this bug."

    except Exception as e:
        ctx.error(f"Error in database management: {str(e)}")
        return f"Error in database management: {str(e)}"
