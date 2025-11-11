# Root Directory Cleanup Proposal

**Date**: November 11, 2025
**Purpose**: Move audit documents from root to organized location

---

## Files to Relocate (4 audit documents)

All from today's cleanup session (November 11, 2025):

1. **DIRECTORY_AUDIT_2025-11-11.md** (10K) - Root directory initial audit
2. **SCRIPTS_AUDIT_2025-11-11.md** (10K) - Scripts folder audit
3. **SCRIPTS_REORGANIZATION_PROPOSAL.md** (15K) - Scripts reorganization options
4. **DOCS_AUDIT_2025-11-11.md** (14K) - Docs folder audit
5. **TESTS_AUDIT_2025-11-11.md** (11K) - Tests folder audit

**Total**: 5 files, ~60K documentation

---

## Proposed Solution: Create docs/audits/2025-11/

**Pattern**: Follows October precedent (docs/audits/2025-10/)

**New structure**:
```
docs/audits/
├── 2025-10/              # October audits (11 files) - Existing
└── 2025-11/              # 🆕 November audits (5 files)
    ├── DIRECTORY_AUDIT_2025-11-11.md
    ├── SCRIPTS_AUDIT_2025-11-11.md
    ├── SCRIPTS_REORGANIZATION_PROPOSAL.md
    ├── DOCS_AUDIT_2025-11-11.md
    └── TESTS_AUDIT_2025-11-11.md
```

---

## Migration Commands

### Step 1: Create November audits directory
```bash
mkdir -p docs/audits/2025-11
```

### Step 2: Move all 5 audit documents
```bash
mv DIRECTORY_AUDIT_2025-11-11.md docs/audits/2025-11/
mv SCRIPTS_AUDIT_2025-11-11.md docs/audits/2025-11/
mv SCRIPTS_REORGANIZATION_PROPOSAL.md docs/audits/2025-11/
mv DOCS_AUDIT_2025-11-11.md docs/audits/2025-11/
mv TESTS_AUDIT_2025-11-11.md docs/audits/2025-11/
```

---

## Result

**Root directory cleanup**:
- ✅ Remove 5 audit documents (60K total)
- ✅ Keep only essential project files (README, CLAUDE, bugs, decisions, progress, etc.)
- ✅ Consistent with October audit organization

**docs/audits/ organization**:
- ✅ Clear chronological structure (by month)
- ✅ Easy to find historical audits
- ✅ Scalable for future audits

---

## Files That Stay in Root (Correct)

**Essential project documentation**:
- README.md - User-facing documentation
- CLAUDE.md - AI assistant context
- bugs.md - Bug tracking
- decisions.md - Architectural decisions
- progress.md - Implementation timeline
- AGENTS.md - OpenSpec agents guide
- INGESTION_PIPELINE_CONTROLS.md - Pipeline documentation
- LICENSE - Legal
- setup.py, pytest.ini - Configuration

**These are correct in root** - Core project documentation that belongs there

---

## Execution

```bash
# Create directory and move files
mkdir -p docs/audits/2025-11
mv DIRECTORY_AUDIT_2025-11-11.md docs/audits/2025-11/
mv SCRIPTS_AUDIT_2025-11-11.md docs/audits/2025-11/
mv SCRIPTS_REORGANIZATION_PROPOSAL.md docs/audits/2025-11/
mv DOCS_AUDIT_2025-11-11.md docs/audits/2025-11/
mv TESTS_AUDIT_2025-11-11.md docs/audits/2025-11/

# Commit
git add -A
git commit -m "chore: Move November 2025 audit documents to docs/audits/2025-11/

CLEANUP:
- Move 5 audit documents from root to docs/audits/2025-11/
- Follows October precedent (docs/audits/2025-10/)
- Clears root directory clutter (60K documentation)

FILES MOVED:
- DIRECTORY_AUDIT_2025-11-11.md (initial root audit)
- SCRIPTS_AUDIT_2025-11-11.md (scripts folder audit)
- SCRIPTS_REORGANIZATION_PROPOSAL.md (scripts reorganization options)
- DOCS_AUDIT_2025-11-11.md (docs folder audit)
- TESTS_AUDIT_2025-11-11.md (tests folder audit)

STRUCTURE:
- docs/audits/2025-10/ - October audits (11 files)
- docs/audits/2025-11/ - November audits (5 files)

RESULT:
- Clean root directory with only essential project files
- Organized audit history by month
- Easy to find historical documentation

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Confidence: ✅ HIGH

**Why safe**:
- Audit documents are historical reference (not active documentation)
- No code dependencies
- Consistent with October audit organization
- Improves root directory cleanliness
