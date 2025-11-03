# Git Rollback Guide - Agent-Zot Version Control

Complete guide for using git tags to create snapshots and roll back to previous versions.

---

## 🎯 What Are Git Tags?

Git tags are **permanent markers** that point to specific commits in your repository's history. They're perfect for creating **restore points** before making risky changes.

Think of them as **bookmarks** in your project's timeline that you can jump back to instantly.

---

## 📌 Current Tags

### v2.1.0-icloud-backup (Current - November 2025)
**Status:** Production-ready iCloud backup integration

**Features:**
- ✅ CLI command: `agent-zot backup-all`
- ✅ iCloud Drive off-site backup
- ✅ Smart sync with dry-run support
- ✅ Dual storage (local + cloud)
- ✅ Comprehensive documentation

**System Status:**
- Qdrant: 236,490 chunks
- Neo4j: 25,184 nodes, 134,068 relationships

**Restore command:**
```bash
git checkout v2.1.0-icloud-backup
```

### Previous Tags
```bash
# List all available tags
git tag -l

# Output:
# pre-grobid-migration
# pre-refactor-stable
# pre-streaming-batch-refactor
# pre-unified-search-consolidation
# v1.0-subprocess-isolation
# v1.1-grobid-hybrid
# v2.1.0-icloud-backup (current)
```

---

## 🔄 How to Roll Back to a Previous Version

### Method 1: Temporary Checkout (Safe - Read-Only)

**Use this when you want to:**
- Test an old version
- Compare with current version
- Retrieve old files

```bash
# 1. View available tags
git tag -l

# 2. Checkout a specific tag (read-only)
git checkout v2.1.0-icloud-backup

# You'll see: "You are in 'detached HEAD' state"
# This is SAFE - you're just looking at old code

# 3. To return to current version
git checkout main
```

**Example:**
```bash
# Go back to v2.1.0
git checkout v2.1.0-icloud-backup

# Test something, read files, etc.
# ...

# Return to latest version
git checkout main
```

---

### Method 2: Permanent Rollback (Destructive)

**⚠️ WARNING: This DELETES changes made after the tag!**

**Use this when you want to:**
- Permanently undo recent changes
- Start over from a known good state

```bash
# 1. Create a backup branch (safety net)
git branch backup-before-rollback

# 2. Rollback main branch to tag
git checkout main
git reset --hard v2.1.0-icloud-backup

# 3. Force push to GitHub (if needed)
git push origin main --force

# 4. If you regret it, restore from backup
git checkout main
git reset --hard backup-before-rollback
```

**Example:**
```bash
# Safety backup
git branch backup-nov-3-2025

# Rollback to v2.1.0
git reset --hard v2.1.0-icloud-backup

# Push to GitHub
git push origin main --force
```

---

### Method 3: Create New Branch from Tag (Recommended)

**Use this when you want to:**
- Experiment without affecting main
- Keep both versions available

```bash
# Create new branch from tag
git checkout -b experiment-from-v2.1.0 v2.1.0-icloud-backup

# Now you're on a new branch based on v2.1.0
# Make changes, test, etc.

# Switch back to main anytime
git checkout main
```

---

## 🆕 Creating New Snapshot Tags

### When to Create a Tag

Create a new tag **before**:
- Major new features
- Risky refactoring
- Database schema changes
- Dependency upgrades
- Production deployments

### How to Create a Tag

```bash
# 1. Make sure everything is committed
git status
# Should show: "nothing to commit, working tree clean"

# 2. Create annotated tag
git tag -a v2.2.0-new-feature -m "Release v2.2.0: New Feature Name

Description of what's new:
- Feature 1
- Feature 2
- Bug fixes

System status at this point:
- Qdrant: X chunks
- Neo4j: Y nodes, Z relationships
"

# 3. Push tag to GitHub
git push origin v2.2.0-new-feature

# 4. Verify
git tag -l -n9 v2.2.0-new-feature
```

---

## 📋 Tag Naming Convention

**Recommended format:**
```
vMAJOR.MINOR.PATCH-description
```

**Examples:**
- `v2.1.0-icloud-backup` - Feature release
- `v2.1.1-bugfix` - Bug fix
- `v2.2.0-neo4j-upgrade` - Infrastructure change
- `v3.0.0-breaking-changes` - Major version bump

**Or use descriptive names:**
- `pre-refactor-stable`
- `before-qdrant-upgrade`
- `working-backup-2025-11-03`

---

## 🔍 Viewing Tag Information

### List All Tags
```bash
git tag -l
```

### Show Tag Details
```bash
# Short info
git tag -l -n1 v2.1.0-icloud-backup

# Full annotation (9 lines)
git tag -l -n9 v2.1.0-icloud-backup

# Complete details
git show v2.1.0-icloud-backup
```

### View Code at Tag
```bash
# See files at that point
git checkout v2.1.0-icloud-backup
ls -la

# View specific file
git show v2.1.0-icloud-backup:README.md

# Return to current
git checkout main
```

---

## 🗑️ Deleting Tags

### Delete Local Tag
```bash
git tag -d v2.1.0-icloud-backup
```

### Delete Remote Tag (GitHub)
```bash
git push origin --delete v2.1.0-icloud-backup
```

### Delete Both
```bash
# Local
git tag -d v2.1.0-icloud-backup

# Remote
git push origin --delete v2.1.0-icloud-backup
```

---

## 🎯 Common Scenarios

### Scenario 1: "I broke something, need to go back"

```bash
# Quick rollback to last known good version
git checkout v2.1.0-icloud-backup

# Test if it works
# ...

# If it's good, make it permanent
git checkout main
git reset --hard v2.1.0-icloud-backup
git push origin main --force
```

---

### Scenario 2: "Creating a restore point before risky change"

```bash
# 1. Commit current work
git add -A
git commit -m "Current state before risky change"

# 2. Create tag
git tag -a before-risky-change -m "Stable state before experimenting"

# 3. Push tag
git push origin before-risky-change

# Now experiment freely - you can always return
```

---

### Scenario 3: "Compare current version with old version"

```bash
# 1. Save current state
git stash

# 2. Checkout old version
git checkout v2.1.0-icloud-backup

# 3. Run tests, compare files, etc.
diff -r . /path/to/current/version

# 4. Return to current
git checkout main
git stash pop
```

---

### Scenario 4: "I want to test both versions side-by-side"

```bash
# Clone repository to different location
cd ~/Downloads
git clone ~/toolboxes/agent-zot agent-zot-v2.1.0
cd agent-zot-v2.1.0
git checkout v2.1.0-icloud-backup

# Now you have:
# ~/toolboxes/agent-zot (current version)
# ~/Downloads/agent-zot-v2.1.0 (v2.1.0)
```

---

## 📊 Best Practices

### 1. Tag Before Major Changes
```bash
# Always create tag first
git tag -a pre-major-refactor -m "Stable before refactoring"
git push origin pre-major-refactor

# Then make changes
```

### 2. Use Descriptive Names
```bash
# ✅ Good
git tag -a v2.1.0-icloud-backup -m "..."
git tag -a before-qdrant-upgrade -m "..."

# ❌ Bad
git tag backup1
git tag temp
```

### 3. Document System State
```bash
# Include current status in tag message
git tag -a v2.1.0 -m "Release v2.1.0

System Status:
- Qdrant: 236,490 chunks
- Neo4j: 25,184 nodes
- Docker: Qdrant v1.15.1, Neo4j 5.x
- Last tested: 2025-11-03
"
```

### 4. Keep Tags on GitHub
```bash
# Always push tags to remote
git push origin v2.1.0-icloud-backup

# Or push all tags
git push origin --tags
```

### 5. Regular Snapshots
**Recommended schedule:**
- After each major feature: `v2.1.0`, `v2.2.0`
- Before risky operations: `pre-refactor-stable`
- Weekly: `working-backup-2025-11-03`
- Before production: `prod-release-2025-11-03`

---

## 🆘 Emergency Recovery

**If everything is broken and you need to restore:**

```bash
# 1. Don't panic - your tagged versions are safe

# 2. Check available tags
git tag -l

# 3. Checkout last known good tag
git checkout v2.1.0-icloud-backup

# 4. Test if it works
# ...

# 5. If it works, make permanent
git branch broken-version  # Save broken state (optional)
git checkout main
git reset --hard v2.1.0-icloud-backup
git push origin main --force

# Done! You're back to v2.1.0
```

---

## 📚 Related Documentation

- **git-scm.com/docs/git-tag** - Official git tag documentation
- **git-scm.com/book/en/v2/Git-Basics-Tagging** - Git tagging guide
- **progress.md** - Project timeline and milestones
- **decisions.md** - Architectural decisions at each version

---

## ✅ Summary

**Tags give you:**
- ✅ **Instant rollback** to any previous state
- ✅ **Safe experimentation** (create tag → experiment → rollback if needed)
- ✅ **Version history** markers for major milestones
- ✅ **Peace of mind** before risky changes

**Current stable tag:** `v2.1.0-icloud-backup`

**Quick rollback:**
```bash
git checkout v2.1.0-icloud-backup
```

**Create new snapshot:**
```bash
git tag -a v2.2.0-description -m "Release notes"
git push origin v2.2.0-description
```

---

**You now have a permanent restore point! Make changes with confidence knowing you can always roll back.** 🎉
