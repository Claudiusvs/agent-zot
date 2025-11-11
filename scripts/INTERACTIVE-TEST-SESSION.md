# Interactive Agent-Zot Test Session

Complete this test session to validate all 9 tools and 48 modes.

**Estimated time:** 15-20 minutes
**Prerequisites:** Claude Desktop running, `/mcp` reconnected to agent-zot

---

## Test Session Results Tracker

Copy this to a new file and check off each test as you complete it.

### Backend Tests ✅ (COMPLETED)
- [x] Docker containers running
- [x] Qdrant accessible (234k chunks)
- [x] Neo4j accessible (25k nodes)

---

## TOOL TESTS (Do these sequentially in Claude Desktop)

### 1. zot_search (5 modes) - Estimated 5 minutes

**Test 1.1: Fast Mode**
```
Query: papers about working memory
Expected: Fast semantic search (Qdrant only), ~2-3 seconds
```
- [ ] Run query
- [ ] Check mode_executed = "fast" (if shown in output)
- [ ] Verify 3-10 relevant results returned
- [ ] Note execution time: _____ seconds

**Test 1.2: Entity-enriched Mode**
```
Query: which methods appear in papers about attention?
Expected: Qdrant + Neo4j entities, ~4 seconds
```
- [ ] Run query
- [ ] Check mode includes entity discovery
- [ ] Verify methods/entities extracted
- [ ] Note execution time: _____ seconds

**Test 1.3: Graph-enriched Mode**
```
Query: who collaborated with Anderson?
Expected: Qdrant + Neo4j graph, ~4 seconds
```
- [ ] Run query
- [ ] Check collaboration network returned
- [ ] Verify co-author relationships shown
- [ ] Note execution time: _____ seconds

**Test 1.4: Metadata-enriched Mode**
```
Query: papers by Anderson published in 2015
Expected: Qdrant + Zotero API, ~4 seconds
```
- [ ] Run query
- [ ] Check author/year filtering applied
- [ ] Verify metadata accurate
- [ ] Note execution time: _____ seconds

**Test 1.5: Comprehensive Mode (forced)**
```
Query: zot_search("neural mechanisms", force_mode="comprehensive", limit=3)
Expected: All backends sequential, ~6-8 seconds
```
- [ ] Run query with force_mode parameter
- [ ] Check mode_executed = "comprehensive"
- [ ] Verify results from multiple backends
- [ ] Note execution time: _____ seconds

**zot_search Summary:**
- [ ] All 5 modes tested
- [ ] Intent detection working correctly
- [ ] Results relevant to queries
- [ ] Execution times reasonable

---

### 2. zot_summarize (4 modes) - Estimated 5 minutes

**First, get a test paper:**
```
Run: zot_search("working memory", limit=1)
Get item_key from results: ____________
```

**Test 2.1: Quick Mode**
```
Query: zot_summarize(item_key, "What is this paper about?")
Expected: Metadata + abstract, ~1 second, 500-800 tokens
```
- [ ] Run query
- [ ] Check mode_executed = "quick"
- [ ] Verify metadata + abstract returned
- [ ] Token count: _____ tokens
- [ ] Note execution time: _____ seconds

**Test 2.2: Targeted Mode**
```
Query: zot_summarize(item_key, "What methodology did they use?")
Expected: Semantic Q&A on chunks, ~2-3 seconds, 2k-5k tokens
```
- [ ] Run query
- [ ] Check mode_executed = "targeted"
- [ ] Verify specific methodology answered
- [ ] Token count: _____ tokens
- [ ] Note execution time: _____ seconds

**Test 2.3: Comprehensive Mode**
```
Query: zot_summarize(item_key, "Summarize this paper comprehensively")
Expected: 4 aspects covered, ~8-10 seconds, 8k-15k tokens
```
- [ ] Run query
- [ ] Check mode_executed = "comprehensive"
- [ ] Verify covers: research question, methods, findings, conclusions
- [ ] Token count: _____ tokens
- [ ] Note execution time: _____ seconds

**Test 2.4: Full Mode (EXPENSIVE - Optional)**
```
Query: zot_summarize(item_key, force_mode="full")
Expected: Complete PDF text, ~10-30 seconds, 10k-100k tokens
```
- [ ] SKIP (too expensive) OR run if curious
- [ ] If run, verify complete text extracted
- [ ] Token count: _____ tokens
- [ ] Note execution time: _____ seconds

**zot_summarize Summary:**
- [ ] All tested modes worked correctly
- [ ] Depth detection accurate
- [ ] Token counts within expected ranges
- [ ] Execution times reasonable

---

### 3. zot_explore_graph (5 key modes) - Estimated 5 minutes

**Test 3.1: Influence Mode**
```
Query: zot_explore_graph("Find influential papers on working memory", limit=5)
Expected: PageRank-ranked papers, ~3-5 seconds
```
- [ ] Run query
- [ ] Check mode_executed = "influence"
- [ ] Verify papers ranked by citations
- [ ] Note execution time: _____ seconds

**Test 3.2: Content Similarity Mode**
```
Query: zot_explore_graph("Papers similar to [item_key]", paper_key=item_key, limit=5)
Expected: Vector similarity, ~2-3 seconds
```
- [ ] Run query with paper_key from earlier
- [ ] Check mode_executed = "content_similarity"
- [ ] Verify similar papers returned
- [ ] Note execution time: _____ seconds

**Test 3.3: Collaboration Mode**
```
Query: zot_explore_graph("Who collaborated with Anderson?", author="Anderson", limit=5)
Expected: Co-authorship network, ~3-5 seconds
```
- [ ] Run query
- [ ] Check mode_executed = "collaboration"
- [ ] Verify co-authors listed
- [ ] Note execution time: _____ seconds

**Test 3.4: Temporal Mode**
```
Query: zot_explore_graph("How has attention research evolved from 2010 to 2020?", start_year=2010, end_year=2020)
Expected: Timeline analysis, ~3-5 seconds
```
- [ ] Run query
- [ ] Check mode_executed = "temporal"
- [ ] Verify year-by-year trends shown
- [ ] Note execution time: _____ seconds

**Test 3.5: Related Papers Mode**
```
Query: zot_explore_graph("Papers related to [item_key]", paper_key=item_key, limit=5)
Expected: Shared entities, ~3-5 seconds
```
- [ ] Run query
- [ ] Check mode_executed = "related_papers"
- [ ] Verify shared entities/concepts shown
- [ ] Note execution time: _____ seconds

**zot_explore_graph Summary:**
- [ ] All 5 modes tested
- [ ] Graph queries executed successfully
- [ ] Results show connections/relationships
- [ ] Execution times reasonable

---

### 4. Management Tools (Quick Smoke Tests) - Estimated 3 minutes

**Test 4.1: zot_manage_collections**
```
Query: zot_manage_collections("list all collections")
Expected: List of collections with counts
```
- [ ] Run query
- [ ] Verify collections listed
- [ ] Note number of collections: _____

**Test 4.2: zot_manage_tags**
```
Query: zot_manage_tags("list all tags")
Expected: List of tags with usage counts
```
- [ ] Run query
- [ ] Verify tags listed
- [ ] Note number of tags: _____

**Test 4.3: zot_manage_database**
```
Query: zot_manage_database("show status")
Expected: Database health and statistics
```
- [ ] Run query
- [ ] Verify Qdrant and Neo4j status shown
- [ ] Check chunk count: _____
- [ ] Check node count: _____

**Test 4.4: zot_daemon_status**
```
Query: zot_daemon_status()
Expected: Daemon running state and statistics
```
- [ ] Run query
- [ ] Verify daemon running
- [ ] Check last update time
- [ ] Verify config mode shown

**Test 4.5: zot_manage_notes (Optional)**
```
Query: zot_manage_notes("show my notes", limit=5)
Expected: Recent notes listed
```
- [ ] Run query OR skip
- [ ] If run, verify notes shown

**Management Tools Summary:**
- [ ] All tested tools worked
- [ ] Data returned correctly
- [ ] No errors encountered

---

## FINAL TEST SUMMARY

### Overall Results
- Backend Tests: ✅ 3/3 passed
- zot_search: __ / 5 modes passed
- zot_summarize: __ / 4 modes passed
- zot_explore_graph: __ / 5 modes passed
- Management tools: __ / 4 tools passed

### Performance Summary
- Average search time: _____ seconds
- Average summarize time: _____ seconds
- Average graph explore time: _____ seconds

### Issues Encountered
List any errors, unexpected behavior, or failed tests:
1.
2.
3.

### Intent Detection Accuracy
- [ ] Search mode selection correct in all cases
- [ ] Summarize depth detection correct in all cases
- [ ] Graph exploration strategy correct in all cases
- [ ] Parameter extraction from queries accurate

### Overall Assessment
- [ ] ✅ All tools working as expected
- [ ] ⚠️ Some issues need investigation
- [ ] ❌ Major problems found

---

## Next Steps After Testing

If all tests pass:
- [ ] Document completion in progress.md
- [ ] Consider these tools production-ready

If issues found:
- [ ] Document specific failures in bugs.md
- [ ] Prioritize fixes based on severity
- [ ] Re-test after fixes applied

---

**Test session completed:** _____ / _____ / _____
**Total time:** _____ minutes
**Tester:** _____________
