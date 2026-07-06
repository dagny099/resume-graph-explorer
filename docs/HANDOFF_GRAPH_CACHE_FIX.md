# Handoff — Stale Graph Analysis Cache Fix

**Branch:** `agent/fix-analysis-cache-validation-surface` (based on `agent/semantic-integrity-eval-pass`)
**Date:** 2026-07-05
**Scope:** Focused correctness pass on graph-analysis cache freshness. No pipeline redesign.

---

## Summary of the bug

Graph analysis and narrative synthesis read a cached session graph from
`backend/data/sessions/{id}/graph.jsonld`. If a user ran analysis, then later
**uploaded or re-extracted another document in the same session**, the next
analysis silently reused the *old* `graph.jsonld` — so the insights and
narratives reflected stale data and missed the new document. The only way to get
fresh analysis was to manually delete the cached file.

## Root cause

`PipelineService._ensure_jsonld()` (in
`backend/resume_explorer/services/pipeline_service.py`) rebuilt the cache only
when the file was **absent**:

```python
jsonld_path = self._jsonld_path(session_id)
if jsonld_path.exists():
    return jsonld_path        # <-- reused unconditionally, even when stale
```

There was no freshness check. (Note: the `/export/jsonld` route writes to the
same path, so the cache could even be seeded by an unrelated export.) By
contrast, the `/graph`, `/export`, `/stats`, and `/graph/validate` routes all
call `build_session_graph()` fresh on every request and were never stale —
**only the analysis path had the caching bug.**

## Fix strategy — Option B (freshness check)

`graph.jsonld` is derived entirely from each completed document's
extracted-entities file (`sessions/{id}/extracted/{doc_id}.json`), which is
rewritten whenever a document finishes extraction or is re-normalized. So the
cache is stale exactly when any such file is newer than the cache.

Added `PipelineService._cache_is_fresh(jsonld_path, session_id)`: returns `True`
only if the cache exists **and** is newer than every completed document's
extracted-entities file. `_ensure_jsonld()` now rebuilds whenever the cache is
missing *or* stale, and reuses it otherwise.

**Why Option B over Option A (delete-on-extract):** it is self-correcting — it
stays robust even if some future code path adds documents without remembering to
invalidate the cache. It touches one file, adds no new state, and only reads
mtimes. No raw uploads, extracted entities, or user data are ever deleted; only
the derived `graph.jsonld` is rebuilt.

The optional `graph_normalized.jsonld` needs no separate handling: when
`normalize=True`, the normalizer subprocess already regenerates it from the
(now-fresh) `graph.jsonld` on every run.

## Files changed

| File | Change |
|------|--------|
| `backend/resume_explorer/services/pipeline_service.py` | Added `_cache_is_fresh()`; `_ensure_jsonld()` rebuilds on missing **or** stale cache |
| `backend/tests/test_pipeline_cache.py` | **New** — 5 regression tests for cache freshness |
| `docs/GRAPH_ANALYSIS_PIPELINE.md` | Added "Graph Cache Freshness (for developers)" section |
| `docs/HANDOFF_GRAPH_CACHE_FIX.md` | This handoff |

## Tests added

`backend/tests/test_pipeline_cache.py` (service-level; no LLM, no network,
deterministic fixtures reused from `test_session_graph.py`):

1. `test_builds_cache_when_missing` — cold build works.
2. `test_reuses_fresh_cache_without_rebuilding` — unchanged session keeps the same cache file (mtime unchanged).
3. `test_new_completed_document_marks_cache_stale` — new completed doc ⇒ `_cache_is_fresh` is `False`.
4. `test_stale_cache_is_rebuilt_with_new_entities` — after a 2nd doc completes, the rebuilt graph contains the new skill (`Rust`).
5. `test_re_extracting_existing_document_marks_cache_stale` — re-extracting an existing doc invalidates and rebuilds the cache.

Tests use `os.utime` to force a strictly-newer mtime on the new extraction file,
so they're deterministic even on filesystems with 1-second mtime resolution.

**Verified they catch the bug:** with the fix reverted (`git stash`), tests
2–5 fail; test 1 still passes (cold build is unaffected). With the fix, all pass.

## Commands run and results

```
cd backend
python -m pytest tests/test_pipeline_cache.py -v   # 5 passed
python -m pytest tests/ -q                          # 150 passed
```

No frontend changes were made, so no `npm` commands were run.

## Manual testing checklist

CLI / API-only (fastest):
1. `cd backend && python -m pytest tests/test_pipeline_cache.py -v` — should be 5 passed.

Full-stack:
1. Start backend and frontend.
2. Create a session; upload one resume; wait for extraction to complete.
3. Run graph analysis; confirm the 6 insight docs appear.
4. Note the entities in the insights (e.g., which skills/orgs are present).
5. Upload a second resume (or a modified fixture) to the **same** session; wait for completion.
6. Re-run graph analysis.
7. Confirm the new analysis reflects the second document's entities.
8. Confirm `backend/data/sessions/{id}/graph.jsonld` mtime is newer than before step 6 (it was rebuilt).
9. Optional: `GET /api/sessions/{id}/graph/validate` and confirm the graph is still valid.

## Remaining risks / out of scope

- **mtime resolution:** the freshness check compares filesystem mtimes. On a
  filesystem with coarse (≥1 s) resolution, a new document completing in the
  *same second* the cache was written could be seen as fresh. In practice
  analysis is a manual step that happens well after extraction, so the window is
  negligible; a fingerprint/hash (Option C) would close it entirely if ever
  needed. Not worth the complexity for this pass.
- **Multi-resume "unknown/dangling node" issue** (known, pre-existing) was **not**
  touched — it is out of scope per the mission and unrelated to cache freshness.
- **Optional validation UI (Goal 5): deferred.** The backend endpoint
  `GET /api/sessions/<id>/graph/validate` already exists and is fully tested. A
  small "Validate Graph" button in the Analysis/Export panel would be a nice UX
  addition, but the repo has no frontend test patterns and the cache fix is the
  priority, so it was intentionally not implemented here. **Recommended next
  small UX pass:** add a button that calls the endpoint and renders a one-line
  status ("Graph valid" / "valid with warnings" / "has errors") with a
  collapsible list, handling loading/success/warning/error/backend-failure
  states. It should not block export or analysis.
