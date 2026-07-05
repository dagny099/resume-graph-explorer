# Handoff: Semantic Integrity & Evaluation-Readiness Pass

**Branch:** `agent/semantic-integrity-eval-pass`
**Date:** July 2026
**Scope:** Reliability, semantic-integrity, and evaluation-readiness — no redesign, no new frameworks.

This document is written for you, the project owner. Sections 4–5 are the
"what do I actually do" parts; everything else is context.

---

## 1. What changed

### RDF export completeness (the big fix)

Your suspicion was correct. The `/export/<format>` route only serialized
**person, jobs, and skills** — education, certifications, and organizations
were silently dropped from every Turtle/RDF-XML/JSON-LD download. (The
interactive graph and the stats panel built all six types, which is why the
app *looked* right while the exports were incomplete. It also explains the
"ghost node" org-001…org-005 findings documented in
`GRAPH_ANALYSIS_PIPELINE.md`.)

The export route also added entities in the wrong order (person before
jobs/skills), so person→job and person→skill links bypassed the
deduplication caches.

**Fix:** all four consumers — `/graph`, `/export/<format>`, `/stats`, and
the analysis pipeline's JSON-LD bootstrap — now share one graph-building
code path: `backend/resume_explorer/graph/session_graph.py`. There is no
longer a way for the export to diverge from what you see on screen.

One deliberate behavior note: multi-resume sessions previously exported one
Person node *per document*; exports now use the first person found, matching
the graph view and stats (a session describes one person).

### Semantic graph validation

New: `backend/resume_explorer/graph/graph_validator.py` plus a read-only
endpoint `GET /api/sessions/<id>/graph/validate`.

It separates **errors** (dangling references, entities without SKOS labels,
entity types that were extracted but never made it into the graph) from
**warnings** (near-duplicate skill labels, jobs missing organization/dates/
technologies, SKOS hierarchy references that aren't materialized, entity
counts dropping more than half between extraction and graph, no Person
node). It is intentionally *not* SHACL — it's ~200 lines of checks tuned to
this exact schema.

### Test coverage

- `tests/test_session_graph.py` (new, 19 tests): every entity type and
  relationship survives export in all three formats; API-level regression
  test on the actual `/export` endpoint; validate endpoint behavior.
- `tests/test_graph_validator.py` (new, 15 tests): clean graphs pass;
  intentionally broken graphs (dangling org, empty label, "Scikit-Learn" vs
  "scikit learn", bare jobs, lost entity types) are caught.
- `tests/test_normalizer.py` (+4 tests): Phase-3 LLM merges tested with a
  fake LLM client returning canned JSON — deterministic, no API calls.
  Covers "GA4" → "Google Analytics 4", declared-skill-vs-usedTechnology
  merges, alt_label preservation, and malformed-LLM-output safety.
- `tests/test_evaluation_harness.py` (new, 12 tests): the eval comparator.
- **Fixed test isolation:** the API tests were running against (and writing
  into!) your real `backend/data/sessions` directory — `create_app` ignored
  the `DATA_PATH` the test fixture passed. It now honors config, so tests
  run in a temp dir. This fixed 2 tests that failed depending on how many
  real sessions you had, and stops test sessions polluting your data.
- Updated 2 stale tests to assert current intended behavior (lazy DSPy
  configuration; JSON 404 for unknown API routes).

Result: **145 passed, 0 failed** (baseline before this pass: 91 passed, 4 failed).

### Evaluation harness lite

New directory `backend/evaluation/`: a tiny synthetic resume fixture, a
gold-labels JSON, a simulated extraction output, a pure comparator
(`compare.py`) producing per-entity-type precision/recall/F1, and a CLI
(`run_eval.py`). Runs offline with no API keys. See section "What the
harness does and does not prove" below.

### Error clarity

- **Upload with no LLM client** → immediate `503` with a hint naming the
  provider and the env vars to check (previously: upload "succeeded", then
  extraction failed invisibly in a background thread).
- **Unknown `/api/*` paths** → JSON `404` (previously the SPA catch-all
  returned `index.html` with a misleading `200`).
- **"No completed extractions"** responses (graph/export/validate/analyze)
  now include a `hint` that distinguishes "still processing — retry" from
  "all documents failed" from "nothing uploaded yet", plus per-status
  document counts.
- **Frontend extraction-failure display** now shows the backend's actual
  `error_message` instead of the generic "Extraction failed".
- **`ENABLE_DSPY` now defaults to `false`** in code. It previously
  defaulted to `true` when the env var was unset, contradicting the
  documented "must stay false" constraint. Deployments that explicitly set
  `ENABLE_DSPY=false` are unaffected; anyone running without a `.env` was
  unknowingly on the experimental DSPy path.

### Documentation

README (export/validation/eval/testing sections), `docs/API.md` (validate
endpoint, upload 503, export completeness), `docs/GRAPH_ANALYSIS_PIPELINE.md`
(ghost-nodes root cause + fix note), `backend/evaluation/README.md` (new),
and this handoff.

---

## 2. Why these changes matter

The project's pitch is "resumes become *trustworthy* semantic knowledge
graphs that downstream AI (RAG, Digital Twin) can rely on." That claim
rests on three legs this pass reinforces:

1. **The export is the product.** Downstream consumers see the exported
   RDF, not the app UI. An export that silently drops half the entity types
   undermines the entire Digital Twin story. Now export == graph == stats,
   enforced by one shared code path plus regression tests.
2. **Integrity must be checkable, not assumed.** "SKOS-compliant" is a
   verifiable property. The validator turns "trust me" into a report you
   (or a CI job, or the analysis pipeline) can run in one request.
3. **Extraction quality must be measurable before it can improve.** You
   can't compare prompts, models, or the DSPy route without gold labels and
   a deterministic scorer. The harness is small, but it's the seed structure
   that makes "is extraction getting better?" an answerable question.

### What the evaluation harness does and does not prove

**Does:** given any extraction output (including the JSON the app already
stores per document), it tells you exactly which expected entities were
found, missed, or hallucinated, with per-type precision/recall — the same
way every time, offline.

**Does not:** prove your LLM extraction is good. There's one small synthetic
resume in the set, and the bundled "extracted" file is simulated. Real
claims need real extraction runs over a bigger fixture set — the README in
`backend/evaluation/` describes exactly how to grow it.

---

## 3. Files changed

### New files
| File | What it is |
|---|---|
| `backend/resume_explorer/graph/session_graph.py` | Shared session→RDF graph builder used by all routes and the pipeline |
| `backend/resume_explorer/graph/graph_validator.py` | Semantic integrity validator (errors vs. warnings report) |
| `backend/evaluation/compare.py` | Deterministic extraction-vs-gold comparator with P/R/F1 |
| `backend/evaluation/run_eval.py` | CLI for the comparator (`--demo` mode included) |
| `backend/evaluation/fixtures/…` | Synthetic sample resume + gold labels + simulated extraction |
| `backend/evaluation/README.md` | How to run and extend the harness |
| `backend/tests/test_session_graph.py` | Export completeness + relationship survival tests |
| `backend/tests/test_graph_validator.py` | Validator tests (clean + broken graphs) |
| `backend/tests/test_evaluation_harness.py` | Comparator tests |

### Modified files
| File | What changed |
|---|---|
| `backend/resume_explorer/api/routes.py` | Export/graph/stats routes use shared builder; new `/graph/validate` endpoint; 503 on missing LLM client; hint-carrying error payloads |
| `backend/resume_explorer/api/app.py` | `ENABLE_DSPY` defaults false; JSON 404 for unknown `/api/*`; `DATA_PATH` honored from config |
| `backend/resume_explorer/services/pipeline_service.py` | `_ensure_jsonld` uses shared builder (deleted 40 lines of duplicated collection code) |
| `backend/tests/test_api.py` | Upload test asserts new 503; 404 test targets `/api/*` |
| `backend/tests/test_extraction.py` | DSPy test asserts lazy configuration (current intended behavior) |
| `backend/tests/test_normalizer.py` | +4 LLM-variant merge tests with fake client |
| `frontend/src/components/ResumeUpload.jsx` | Polling failure shows the backend's real `error_message` |
| `README.md`, `docs/API.md`, `docs/GRAPH_ANALYSIS_PIPELINE.md` | Documentation updates described above |

---

## 4. How to run automated checks

### Backend tests

```bash
cd backend
python -m pytest tests/ -v        # (or: .venv/bin/python -m pytest tests/ -v)
```

**Passing looks like:** `145 passed` (plus a handful of third-party
DeprecationWarnings — pre-existing, harmless). Nothing needs an API key or
network. Verified passing on this pass.

### Evaluation harness demo

```bash
cd backend
python evaluation/run_eval.py --demo
```

**Passing looks like:** a P/R/F1 table where person/jobs/education/certs/orgs
score 1.00 and skills score ~0.78, with `missing skills: google analytics 4,
tableau` and `unexpected skills: data science, ga4` listed. (The simulated
extraction is deliberately imperfect so you can see the metrics work; exit
code is 1 because entities are missing — that's correct.)

### Frontend build/lint

```bash
cd frontend
npm install
npm run build
npm run lint
```

**Status at handoff time:**
- `npm run build` — **passes** (with Vite's pre-existing chunk-size warning
  about the 924 kB bundle; informational, not an error).
- `npm run lint` — **fails before linting anything**, on `main` too: the
  `eslintConfig` in `package.json` extends `"react-app"` but
  `eslint-config-react-app` is not installed. Pre-existing configuration
  issue, not caused by this pass (only `ResumeUpload.jsx` was touched, and
  it builds fine). Fix when convenient with
  `npm install --save-dev eslint-config-react-app`, or switch to a flat
  ESLint config.

---

## 5. Manual testing checklist

- [ ] Start the backend: from `backend/`, run `python -m resume_explorer.api.app` (make sure your `.env` has a valid API key, e.g. `CLAUDE_API_KEY`).
- [ ] Start the frontend: from `frontend/`, run `npm run dev` and open the printed local URL.
- [ ] Create a new session (or let auto-session mode create one).
- [ ] Upload a small resume — `backend/evaluation/fixtures/sample_resume_001.txt` works well and exercises jobs, education, certifications, and organizations.
- [ ] Wait until extraction status shows complete and the graph renders.
- [ ] **Check the graph** has organization, education, and certification nodes (different colors/groups), not just person/job/skill.
- [ ] **Check entity counts** in the Export panel sidebar — Organizations, Education, and Certifications should all be non-zero for the sample resume.
- [ ] Export **JSON-LD**, **Turtle**, and **RDF/XML** from the Export panel.
- [ ] Open the Turtle file in a text editor and confirm it contains `schema:Organization`, `schema:EducationalOccupationalCredential`, and `re:Certification` entries (this is the core fix — before this pass those were absent).
- [ ] **Run validation:** `curl http://localhost:5000/api/sessions/<session-id>/graph/validate` (session ID is visible in the UI/localStorage or via `GET /api/sessions`). Expect `"valid": true` with few or no errors; warnings like `job_missing_dates` are informational.
- [ ] Run the graph analysis pipeline (sidebar → "Analyze Graph") and confirm all 6 insights appear under the Insights tab, each with content.
- [ ] Generate narratives (Step 2) and confirm both Conservative and Exploratory render under the Narratives tab.
- [ ] **Test an improved error:** with a *fresh empty session*, click "Analyze Graph" before uploading anything → the error should say "No completed extractions…" with the hint "Upload a resume document to this session first."
- [ ] **Test another improved error (optional):** stop the backend, remove/rename the API key in `.env`, restart, and try to upload → you should get an immediate alert "LLM client is not available (provider: …)" instead of a stuck "processing" document. Restore the key afterward.
- [ ] **Test the API 404 fix:** `curl -i http://localhost:5000/api/definitely-not-a-route` → `404` with a JSON body (previously `200` + HTML).
- [ ] Run the evaluation harness: from `backend/`, `python evaluation/run_eval.py --demo` and skim the table.
- [ ] (Optional, closes the loop) After uploading `sample_resume_001.txt`, find its stored extraction at `backend/data/sessions/<session-id>/extracted/<doc-id>.json` and run `python evaluation/run_eval.py --extracted <that file> --expected evaluation/fixtures/sample_resume_001.expected.json` to score your *real* LLM extraction against the gold labels.

---

## 6. What to look for in the app

Signs the changes are working:

- The graph shows **six node groups** for a full resume, and the Export
  panel counts match what the graph shows.
- Exported files contain organization/education/certification triples and
  relationship predicates (`schema:hiringOrganization`, `schema:alumniOf`,
  `re:hasCertification`) — open the `.ttl` export and search for them.
- `/graph/validate` returns a structured JSON report, and its
  `stats.entity_counts` match the Export panel.
- Insights render in all six tabs after analysis; the Narratives button
  stays disabled (with a "Run Step 1 first" tooltip) until analysis has run
  — that gating already existed and is preserved.
- Error states name the actual problem and what to do next, instead of
  generic failures or silent hangs.

---

## 7. Known limitations

Honest list of what this pass does **not** do:

- **Does not prove LLM extraction quality.** The eval set is one synthetic
  resume; the harness measures whatever you feed it.
- **Does not make DSPy production-ready.** DSPy remains experimental and now
  genuinely defaults to off; the threading issues are untouched.
- **Not full SHACL validation.** The validator is a pragmatic checklist for
  this schema. If interoperability claims grow, a real SHACL shapes file
  would be the successor (rdflib has `pyshacl` available as a path).
- **ESCO matching coverage unchanged** (~50–60% for typical resumes;
  vendor-specific tools correctly have no ESCO match).
- **The multi-resume "unknown nodes" cosmetic issue is not fixed** — but the
  validator's `dangling_reference` check now *detects and lists* those
  orphaned references, which should make the eventual fix straightforward.
- **Validation is on-demand only.** Nothing runs it automatically on upload
  or export yet, and there's no UI surface for it — it's an API endpoint and
  a Python utility.
- The analysis pipeline's `graph.jsonld` is cached per session; if you
  upload another document *after* running analysis, the cached file (and
  hence re-analysis) can be stale until it's deleted. Pre-existing behavior,
  out of scope here, worth a future look.

---

## 8. Recommended next steps

**Do now**
1. Run the manual checklist above on a real resume of yours; eyeball the
   `.ttl` export and the `/graph/validate` report.
2. Merge the branch if satisfied — the export fix affects anything
   downstream consuming exports, so the sooner it lands the better.

**Good next coding-agent pass**
1. Fix the multi-resume "unknown nodes" issue using the validator's
   `dangling_reference` output as the spec and regression test.
2. Surface validation in the UI: a small badge in the Export panel
   (✓ valid / n warnings) hitting the existing endpoint.
3. Grow the eval set to 3–5 resumes (varied formats: no certifications,
   career changer, multi-column PDF) and add a script that batch-uploads
   fixtures, waits for extraction, and scores all of them.
4. Invalidate the cached `graph.jsonld` when a new document completes
   extraction.

**Longer-term roadmap**
1. Real SHACL shapes for the resume ontology (`pyshacl`), replacing the
   pragmatic validator for interoperability claims.
2. Wire eval scores into CI once live-extraction eval runs exist.
3. Avenue 3 Phase 2+ (per `GRAPH_ANALYSIS_PIPELINE.md`): embed insight
   documents into the Digital Twin's vector store — now with a validation
   gate so only clean graphs get embedded.
