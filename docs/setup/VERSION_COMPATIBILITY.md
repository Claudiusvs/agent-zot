# Version Compatibility Guide

## Overview

This document explains version pinning strategy to prevent compatibility issues between agent-zot components.

## Version Requirements

### Qdrant (Vector Database)

**Server Version**: `v1.15.1` (pinned)
**Python Client**: `qdrant-client==1.15.1` (pinned)

**Why Pinned?**
- Qdrant server API changes between minor versions can break compatibility
- The Python client must match the server version for optimal compatibility
- Using `:latest` tag causes unpredictable behavior when Docker auto-updates

**Docker Command**:
```bash
docker run -d -p 6333:6333 -p 6334:6334 \
  -v agent-zot-qdrant-data:/qdrant/storage \
  --name agent-zot-qdrant \
  --restart unless-stopped \
  qdrant/qdrant:v1.15.1
```

**⚠️ DO NOT USE**: `qdrant/qdrant:latest` or `qdrant/qdrant` (defaults to latest)

### Neo4j (Knowledge Graph)

**Server Version**: `neo4j:5.23.0-community` or newer (5.23.0+ required for relationship vectors)
**Python Driver**: `neo4j>=5.14.0`

**Docker Command**:
```bash
docker run -d -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/demodemo \
  -e NEO4J_PLUGINS='["apoc"]' \
  -v agent-zot-neo4j-data:/data \
  --name agent-zot-neo4j \
  --restart unless-stopped \
  neo4j:5.23.0-community
```

## Updating Versions

### When to Update

Update versions when:
1. Security vulnerabilities are disclosed
2. Critical bug fixes are released
3. New features are required that only exist in newer versions

### How to Update Safely

1. **Check Compatibility**:
   - Read Qdrant/Neo4j release notes for breaking changes
   - Verify Python client version matches server version

2. **Update Python Client First**:
   ```bash
   pip install --upgrade qdrant-client==<new_version>
   ```

3. **Test Code Changes**:
   - Run agent-zot with new client against old server
   - Fix any API compatibility issues in code

4. **Update Docker Container**:
   ```bash
   docker stop agent-zot-qdrant
   docker rm agent-zot-qdrant
   docker run -d ... qdrant/qdrant:v<new_version>
   ```

5. **Verify**:
   ```bash
   agent-zot get-search-database-status
   ```

6. **Update Documentation**:
   - Update version pins in README.md
   - Update this file
   - Update scripts/index-background.sh

## Troubleshooting Version Mismatches

### Symptoms
- `'VectorParams' object has no attribute 'get'` errors
- Search operations hang or timeout
- Status reporting shows 0 documents despite populated database
- MCP server failures with cryptic API errors

### Diagnosis
```bash
# Check Qdrant server version
curl -s http://localhost:6333 | python3 -m json.tool | grep version

# Check Python client version
pip show qdrant-client | grep Version

# Check Docker image
docker inspect agent-zot-qdrant | grep '"Image"'
```

### Fix
1. Match versions (upgrade Python client or downgrade Docker image)
2. Update code for API compatibility if needed
3. Restart MCP server

## History

### 2025-10-26: Qdrant v1.15.5 Compatibility Issue
**Problem**: Docker auto-updated to v1.15.5, Python client at v1.15.1. API incompatibility caused VectorParams errors.

**Fix**:
- Updated `get_collection_info()` to handle VectorParams objects (commit b9ad84a)
- Pinned Docker image to v1.15.1 in documentation
- Created this compatibility guide

**Lesson**: Always pin versions for production dependencies.
