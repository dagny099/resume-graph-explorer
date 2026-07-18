# Engineering Log — April 2026 Changes

> Personal reference. Written to capture the *why*, not just the *what* — because git log tells you what changed, not why three prior attempts failed.

---

## Executive Summary

Four compounding root causes behind the multi-resume "unknown nodes" bug were identified and fixed after surviving three previous fix attempts. Three foundation improvements were borrowed from the ChronoScope sister project. A user-facing editable nodes feature was added to let you correct LLM extraction errors directly in the graph. A hybrid evaluation framework (automated precision/recall + manual rubric) was built to make future assessment rigorous and repeatable.

**The four things that shipped:**

1. **Multi-resume bug fully resolved** — zero unknown nodes in two-resume sessions, confirmed by a new regression test suite (`tests/test_unknown_nodes.py`, 12 tests). Multi-resume is now production-quality, not "experimental."
2. **Foundation improvements** — MD5 duplicate file detection (409 on re-upload), `user_verified`/`user_notes` fields on all entities, similarity-based job dedup.
3. **Editable node labels** — click any graph node → Edit → correct the label, add notes, mark as verified. Edits are authoritative: future normalization runs treat verified labels as anchors that can't be overwritten.
4. **Evaluation framework** — `tests/test_evaluation.py` for precision/recall against ground truth, `docs/EVALUATION_PLAN.md` for the full hybrid methodology.

---

## The Multi-Resume Bug: Why It Survived Three Prior Attempts

This is worth preserving in detail because the lesson has teeth.

**The symptom:** After uploading two resumes to the same session, ~8-10 nodes appeared with UUID labels and no entity type — "unknown nodes" in Vis.js. They didn't affect extraction quality but cluttered the graph and implied something was deeply wrong.

**Why prior fixes failed:**
1. Each attempt patched one mechanism while leaving others intact.
2. Tests were written *after* code changes, so they validated the fix rather than confirming the bug. A test that can't fail before the fix tells you nothing.
3. The root causes were in *three different files* and only compounded into visible symptoms together.

**The fix discipline this time:** Wrote `tests/test_unknown_nodes.py` first. Confirmed which tests failed. Made no production code changes until there was a failing test. This is the lesson from the old bug doc (`docs/plan-for-fixing-unknown-bugs-prompt.md`, now retired) — it's preserved in the test file's header comment.

### Root Cause A — Index mismatch in the save loop

**File:** `backend/resume_explorer/api/routes.py`, `_maybe_normalize_session_entities()`

**Problem:** The collection loop used `if entities` to skip documents with no extracted entities. So `all_entities = [doc_A_entities, doc_C_entities]` when doc B had nothing. But the save loop iterated `completed_docs` (unfiltered), so index 1 wrote doc_C's normalized entities into doc_B's slot. Real data corruption — not cosmetic.

**Fix:** Track `docs_with_entities` explicitly during collection so both loops stay aligned.

### Root Cause B — `get_session_graph` used `all_persons[0]`

**File:** `backend/resume_explorer/api/routes.py`, `get_session_graph()`

**Problem:** When building the combined graph for a multi-resume session, the code used `all_persons[0]` — the Person object from the first document — as the graph's person node. That Person's `.skills` and `.jobs` lists only contained IDs from Document 1. Document 2's entity IDs were added to the graph (via `add_skill`, `add_job`) but `add_person` never referenced them, so no edges were created.

**Fix:** Build a synthetic merged-person whose reference lists are the *union* of all persons' IDs across all documents.

```python
merged_person.skills = list({sid for p in all_persons for sid in p.skills})
merged_person.jobs   = list({jid for p in all_persons for jid in p.jobs})
```

The same fix was applied to `export_session_graph`.

### Root Cause C — `export_session_graph` omitted organizations (and education, certifications)

**File:** `backend/resume_explorer/api/routes.py`, `export_session_graph()`

**Problem:** The export path only collected Person, Jobs, and Skills. Organizations were never passed to `build_from_entities`. When `add_job` encountered a job with `organization_id` that wasn't in `_org_id_to_uri`, it created a fallback URI with no `rdf:type` triple → "unknown" node.

**Fix:** Copy the org/education/certification collection logic from `get_session_graph` into `export_session_graph`.

### Root Cause D — Ghost URI fallback in `add_person`

**File:** `backend/resume_explorer/graph/rdf_graph_builder.py`, `add_person()`

**Problem:** When a skill/job/edu/cert ID referenced by a Person wasn't in the builder's cache, the original code used `dict.get(id, fallback_uri)` — generating a URI with no `rdf:type`. The NetworkXAdapter classified any untyped URI as "unknown."

**Fix:** Replace fallback with skip-and-warn:
```python
skill_uri = self._skill_id_to_uri.get(skill_id)
if skill_uri is None:
    logger.warning(f"add_person: unresolved skill_id {skill_id!r} — skipping edge")
    continue
```

This is a safety net. Root causes A–C, when fixed, mean the ID should always be resolvable. But if a future bug reintroduces a mismatch, you get a warning log instead of a silent corrupt node.

### Bonus fix — Multi-suffix org normalization

**File:** `backend/resume_explorer/graph/rdf_graph_builder.py`, `_normalize_org_name()`

**Problem:** The suffix-stripping loop used `break` after the first match. So "Acme Corp, Inc." → "Acme Corp" (stripped `, Inc.`), then stopped. But "Acme Corp" on its own → "Acme" (stripped ` Corp`). Different cache keys → no dedup.

**Fix:** Iterative stripping — loop until no more suffixes match.

---

## Phase 2: Foundation Improvements (from ChronoScope)

Three patterns from the ChronoScope sister project were evaluated. Three were incorporated; one (ChronoScope's flat event model) doesn't transfer to Resume Explorer's cascading graph relationships.

### MD5 duplicate file detection

**File:** `backend/resume_explorer/api/routes.py`, `upload_document()`

Before processing, compute MD5 of the uploaded bytes. Check if any existing document in the session has the same hash. If yes: return HTTP 409 with `{"error": "...", "duplicate_of": "<doc_id>"}`.

Why: uploading the same resume twice to a session was silent before — you'd just get doubled entity counts.

### `user_verified` and `user_notes` fields on `SKOSEntity`

**File:** `backend/resume_explorer/models/base.py`

Added two optional fields with defaults to the base dataclass:
```python
user_verified: bool = False
user_notes: Optional[str] = None
```

Backward-compatible: `from_dict` filters to `__dataclass_fields__`, so old sessions without these fields load safely. These are the data model foundation for the editable nodes feature (Phase 3A).

### Similarity-based job dedup

**File:** `backend/resume_explorer/graph/rdf_graph_builder.py`, `add_job()`

The previous dedup key was exact: `(title.lower(), org_uri, start_date)`. "Senior Engineer" and "Sr. Software Engineer" at the same org created two nodes.

New: after an exact cache miss, scan existing jobs at the same org using `SequenceMatcher.ratio()`. If similarity ≥ 0.85 and dates are within 30 days → treat as duplicate.

---

## Phase 3A: Editable Node Labels

### The problem it solves

LLMs make extraction errors. "Machine Learning" gets extracted as "ML" in one resume and "machine learning" in another. The normalizer handles this, but can't correct everything — especially when the source text is ambiguous or the LLM made a judgment call you disagree with. Before this feature, corrections required editing the raw JSON files in `data/sessions/`.

### What was built

**Backend:** `PATCH /api/sessions/{session_id}/entities/{entity_type}/{entity_id}`

Accepts `{"label": "...", "user_verified": true, "user_notes": "..."}`. Whitelist-validates fields (rejects anything else with 400). Searches all session documents for the entity by ID (primary match) and by normalized label (secondary match, for cross-doc deduped entities). Updates all occurrences. Preserves old label as `alt_label` on Skill entities.

**Normalizer protection:** Entities with `user_verified=True` are treated as anchors in the normalization pipeline. Two behaviors:
- Their labels are forced to identity in the final `label_map` (they can't be remapped by any phase)
- In `_apply_normalization`, verified entities are skipped entirely (their label isn't touched)

This means: if you correct "ML" → "Machine Learning" and mark it verified, the next upload's "machine learning" skill normalizes *to* it — not the other way around.

**Frontend:** `EntityPanel.jsx` gains an inline edit mode. Click any node → "Edit" button appears in the panel header. Edit form shows: label input, notes textarea, verified checkbox, Save/Cancel buttons, immutable fields below (confidence, source doc, SKOS URI). On save: PATCH is sent, graph re-fetches, panel updates immediately. If save fails: inline error, stays in edit mode.

### Immutable vs. mutable field distinction

Follows the ChronoScope pattern explicitly: extraction-computed fields (`confidence`, `skos_uri`, `source_doc`, `created_at`, `id`) are read-only in the UI. User-curation fields (`label`, `user_verified`, `user_notes`) are editable. The UI shows both sections — editable fields as inputs, immutable fields as read-only metadata below.

---

## Phase 3B: Evaluation Framework

### Why this was needed

Prior evaluation was entirely informal: upload a resume, eyeball the graph, count nodes. This made it impossible to:
- Know if a code change improved or regressed extraction quality
- Compare providers (Claude vs OpenAI vs Ollama) on anything measurable
- Catch regressions in normalization without manually testing

### What was built

**`backend/tests/test_evaluation.py`** — 10 tests across two classes. `TestSingleResumeAccuracy`: person name, skill recall (≥80%), skill precision (≥70%), skill count bounds, job recall, org recall, no-unknown-nodes. `TestMultiResumeEvaluation`: single person node, zero unknown nodes, skill dedup correctness. All tests skip gracefully when fixture files don't exist — they activate as you add ground truth.

**`backend/tests/conftest.py`** — Session-scoped fixtures loading ground truth and pre-recorded extraction JSON from `tests/fixtures/`.

**`backend/tests/fixtures/ground_truth_schema.json`** — Schema template with authoring instructions. Copy → fill in → run tests.

**`pytest.ini`** — Created (was missing). Registers the `slow` mark, preserves `asyncio_mode = strict`.

**`docs/EVALUATION_PLAN.md`** — Full 8-section evaluation methodology: structural correctness, precision/recall setup, entity quality rubric, multi-resume scenarios (3 concrete scenarios), narrative quality rating rubric (5-dimension, 1–5 scale), provider comparison matrix, export fidelity checks, editable node label verification.

### To activate the evaluation tests

```bash
# 1. Upload a resume through the app UI
# 2. GET /api/documents/{id}/entities → copy the JSON response body
# 3. Save it:
cp /dev/stdin backend/tests/fixtures/resume_v1_extracted.json

# 4. Author ground truth manually (fill in what the resume actually contains):
cp backend/tests/fixtures/ground_truth_schema.json backend/tests/fixtures/resume_v1_gt.json
# edit resume_v1_gt.json by hand

# 5. Run:
cd backend && pytest tests/test_evaluation.py -v
```

---

## How to Test These Updates

### 1. Run the regression test suite

```bash
cd backend
pytest tests/test_unknown_nodes.py tests/test_normalizer.py tests/test_graph.py tests/test_models.py -v
```

Expected: all pass. The 4 pre-existing failures in `test_api.py` and `test_extraction.py` are unrelated (confirmed via git stash before/after).

### 2. Multi-resume: zero unknown nodes

1. Start the app locally
2. Create a new session
3. Upload Resume v1 (any PDF or DOCX)
4. Upload Resume v2 (a different version of the same resume)
5. Observe the graph — **zero UUID-labeled nodes should appear**
6. Check entity counts: 1 person, skills from both resumes merged, no duplicates

### 3. Duplicate file detection

1. Upload a resume
2. Upload the **exact same file** again
3. Expect: toast/error message with HTTP 409, graph unchanged

### 4. Editable node labels

1. Upload a resume and let extraction complete
2. Click any node in the graph (e.g., a skill)
3. Verify "Edit" button appears in the EntityPanel
4. Click Edit → change the label → Save
5. Verify: graph refreshes with the new label; panel shows updated label
6. **Test authoritative normalization:** Upload a second resume. The corrected, verified skill label should be the canonical form that the new resume normalizes to.
7. **Test multi-doc propagation:** In a two-resume session, edit a skill that appears in both. Check `data/sessions/{session_id}/extracted/` — both JSON files should reflect the new label.

### 5. Test the PATCH endpoint directly

```bash
# Get a skill entity ID from the graph
curl http://localhost:5000/api/sessions/{session_id}/graph | python -m json.tool | grep '"group": "skill"' -A2

# PATCH it
curl -X PATCH http://localhost:5000/api/sessions/{session_id}/entities/skill/{entity_id} \
  -H "Content-Type: application/json" \
  -d '{"label": "Corrected Label", "user_verified": true, "user_notes": "Fixed by hand"}'
# Expect: {"updated": 1, "entity": {...}}

# PATCH unknown entity
curl -X PATCH http://localhost:5000/api/sessions/{session_id}/entities/skill/nonexistent-id \
  -d '{}'
# Expect: 404

# PATCH with invalid field
curl -X PATCH http://localhost:5000/api/sessions/{session_id}/entities/skill/{entity_id} \
  -H "Content-Type: application/json" \
  -d '{"confidence": 0.99}'
# Expect: 400
```

### 6. Export fidelity

After building a multi-resume graph:
1. Use in-app graph view — note entity counts in the legend
2. Export as Turtle
3. Run: `grep "skos:prefLabel" export.ttl | wc -l`
4. Counts should match

---

## Files Modified

| File | What changed |
|------|-------------|
| `backend/resume_explorer/api/routes.py` | Index mismatch fix (save loop); merged-person in `get_session_graph`; export completeness in `export_session_graph`; MD5 dedup on upload; new `PATCH /sessions/{id}/entities/{type}/{id}` endpoint |
| `backend/resume_explorer/graph/rdf_graph_builder.py` | Ghost-URI → skip-with-warning in `add_person`; iterative multi-suffix org normalization; `_job_title_similarity()` + fuzzy job dedup |
| `backend/resume_explorer/models/base.py` | `user_verified: bool`, `user_notes: Optional[str]` added to `SKOSEntity` |
| `backend/resume_explorer/services/entity_normalizer.py` | `verified_labels` collection; `label_map` identity override for verified labels; skip verified entities in `_apply_normalization` |
| `frontend/src/services/api.js` | `updateEntity()` added |
| `frontend/src/components/EntityPanel.jsx` | Full rewrite: added inline edit mode |
| `frontend/src/components/EntityPanel.css` | Edit mode styles |
| `frontend/src/App.jsx` | `handleNodeUpdated` callback; `sessionId` + `onNodeUpdated` props wired to EntityPanel |
| `backend/tests/test_unknown_nodes.py` | **NEW** — 12 tests, replaces retired bug doc |
| `backend/tests/test_evaluation.py` | **NEW** — precision/recall + structural evaluation tests |
| `backend/tests/conftest.py` | **NEW** — fixture loading for evaluation tests |
| `backend/tests/fixtures/ground_truth_schema.json` | **NEW** — schema template for ground truth authoring |
| `backend/pytest.ini` | **NEW** — registers `slow` mark, `asyncio_mode = strict` |
| `docs/EVALUATION_PLAN.md` | **NEW** — 8-section hybrid evaluation methodology |
| `docs/plan-for-fixing-unknown-bugs-prompt.md` | **DELETED** — lessons preserved in `test_unknown_nodes.py` header |

---

## What's Still Pending

- **Ground truth fixtures:** `resume_v1_gt.json` and `resume_v1_extracted.json` need to be authored before evaluation tests activate. See the "To activate" section above.
- **Provider comparison matrix:** `docs/EVALUATION_PLAN.md` section 6 has blank cells. Fill in by running extraction with each provider.
- **`claude.md` duplicate:** Both `CLAUDE.md` and `claude.md` exist at the repo root with identical content. One should be deleted.
