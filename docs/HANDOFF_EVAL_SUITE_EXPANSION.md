# Handoff: Evaluation Suite Expansion

**Branch:** `agent/eval-suite-expansion`
**Date:** 2026-07-05
**Scope:** `backend/evaluation/`, `backend/tests/test_eval_*.py`, `.gitignore`

## 1. What was added

The evaluation harness grew from one fixture + a single-file comparator into
a compact diagnostic suite:

- **Six new synthetic fixtures** (002–007) alongside the existing 001, each
  designed to expose a specific failure mode (see the table below).
- **`fixtures/manifest.json`** — per-fixture metadata: profile, what it
  tests, failure modes, intentionally present/absent entity types, excluded
  near-matches, target pipeline stage.
- **`batch.py`** — batch runner: evaluates every manifest fixture, aggregates
  micro-averaged P/R/F1 per entity type and overall, ranks the most common
  missing/unexpected entities, and reports intentionally absent types.
- **`run_eval.py --all`** — CLI for the batch, with `--mode raw|normalized`,
  `--extracted-dir <dir>` (score real outputs), and `--strict` (gating exit
  code). Single-fixture and `--demo` behavior unchanged.
- **`run_live_eval.py`** — opt-in live evaluation: drives a running backend
  over HTTP (one session per fixture: create → upload → poll → collect →
  delete), saves outputs to gitignored `evaluation/live_runs/<timestamp>/`,
  then scores them with the same comparator.
- **Raw vs normalized gold support** — fixture 004 carries a second gold file
  (`.expected.normalized.json`) with canonical skill labels; normalized mode
  skips fixtures that don't have one.
- **Two new test files** (~140 tests with parametrization):
  `tests/test_eval_fixtures.py` (fixture/manifest discipline, schema shape,
  no PII/secrets) and `tests/test_eval_batch.py` (aggregation math, mode
  handling, every designed trap actually detected).
- `backend/evaluation/live_runs/` added to `.gitignore`.

No app code was touched — `compare.py`, the extraction pipeline, the
normalizers, and the frontend are all unchanged.

## 2. How to run offline eval

From `backend/` (no API keys, no network):

```bash
python evaluation/run_eval.py --demo              # one fixture
python evaluation/run_eval.py --all               # whole suite, raw gold
python evaluation/run_eval.py --all --mode normalized
python -m pytest tests/ -v                        # includes all eval tests
```

## 3. How to interpret precision, recall, F1

Per entity type, after key normalization (casefold, whitespace collapse, org
suffix stripping):

- **Precision** = matched / extracted. Low precision means the extractor
  returns entities the gold doesn't sanction — hallucinations, promoted soft
  skills, issuers-as-employers.
- **Recall** = matched / expected. Low recall means real entities were
  missed.
- **F1** = harmonic mean. Batch aggregation is **micro-averaged** (counts
  summed across fixtures, then P/R/F1 computed), so big fixtures weigh more
  than small ones.

Edge case worth knowing: when a gold type is intentionally empty and the
extractor hallucinates into it (fixture 007's invented MBA), it shows up as
`unexpected` with precision 0.0 for that type — nothing is "missing". When
both gold and extraction are empty for a type, the type simply doesn't appear
in the report (no free 1.0 scores for doing nothing).

## 4. How to add a new fixture

Documented step-by-step in `backend/evaluation/README.md` ("Adding a new eval
case"). Short version: add `NNN.txt` + `NNN.expected.json` +
`NNN.extracted.json` + a manifest entry, then run
`pytest tests/test_eval_fixtures.py` — the discipline tests enforce the
metadata fields, empty-absent-types, excluded-near-match, and synthetic-data
rules mechanically.

## 5. How to run (or eventually run) live extraction eval

```bash
# terminal 1 — backend holds the API key; the eval script never sees it
cd backend && python -m resume_explorer.api.app

# terminal 2
cd backend && python evaluation/run_live_eval.py
```

What's automated: session creation, upload, status polling, entity
collection, session cleanup, scoring. What remains manual: starting the
backend with credentials, and choosing config (provider,
`NORMALIZATION_PROVIDER`, `NORMALIZE_SINGLE_RESUME`) for the question you're
asking. Nothing under `live_runs/` is committed.

Known caveat: the backend applies deterministic + ESCO normalization
(Phases 1–2) automatically after extraction even for single-document
sessions, so live-collected entities are "as-persisted" output, not the raw
LLM response. For a strictly-raw eval you'd need to snapshot entities before
`_maybe_normalize_session_entities` runs — a possible future extension
(e.g. a debug flag that also stores the pre-normalization JSON).

## 6. What the eval suite proves

- The comparator + fixtures reproducibly detect the failure modes the project
  cares about: hallucinated credentials, adjacency/aspiration promoted to
  skills, tool names inside proper names, publication venues and cert issuers
  extracted as organizations, soft-skill promotion, column-split parsing
  damage, org-suffix duplication.
- Batch aggregation is arithmetically consistent (tested) and runs in
  milliseconds with zero external dependencies.
- The gold labels obey written annotation rules and are mechanically checked
  against the manifest's declared intent.

## 7. What it still does not prove

- **Actual LLM extraction quality.** The bundled `.extracted.json` files are
  simulated. Until `run_live_eval.py` is run against a real provider, the
  numbers demonstrate the *harness*, not the *model*.
- **Real-world document robustness.** Fixture 005 simulates two-column text
  damage, but no fixture exercises the PDF/DOCX parsing path itself — the
  live eval uploads `.txt` files.
- **Relationship/graph quality.** The comparator scores entity sets, not
  edges (job→org links, date ranges, `usedTechnology`). Graph construction is
  only probed indirectly (org dedup via gold design).
- **Normalizer coverage.** Only fixture 004 has a normalized gold; the
  canonical vocabulary there is an editorial choice that should be reconciled
  with what the live normalizer actually produces before treating normalized
  scores as authoritative.
- **Statistical significance.** Seven small fixtures characterize failure
  modes; they don't estimate accuracy on any real resume population.

## 8. How adversarial and negative cases were included

Every fixture beyond 001 carries at least one trap, declared in its manifest
entry (`excluded_near_matches`, `absent_types`, `failure_modes`) and enforced
by tests:

- **Absent-type negatives:** 002/003 have no certifications; 007 has neither
  education nor certifications. Gold lists are present-but-empty so
  hallucinations are caught (007's simulated extraction invents an MBA and
  the batch report flags it).
- **Near-matches that must not be extracted:** AWS via someone else's team
  (002), journals/conferences as orgs (003), aspirational Rust/Kubernetes
  (004), cert issuers as orgs (005/006), Python/Tableau inside proper names
  and a partnership program as an org (007).
- **Formatting stress:** 005's text interleaves two columns, mixes bullet
  glyphs, and splits entity names across lines.
- **Ambiguous-but-resolvable:** soft-skill boundary decided and documented —
  named practices (OKRs, A/B testing) are skills; adjectives ("strategic
  thinker") are not.
- **Anti-overfitting:** simulated extractions deliberately *fail* the traps,
  so gold ≠ likely-extractor-output by construction, and the demo report
  always shows detection working.

## 9. Raw extraction eval vs post-normalization eval

Two modes, two questions:

- **Raw** (`--mode raw`, default): gold preserves surface forms (`GA4`,
  `ML`). Measures extraction fidelity — an extractor that canonicalizes on
  its own is penalized, deliberately, because canonicalization is the
  normalizer's job and doing it silently in extraction hides provenance.
- **Normalized** (`--mode normalized`): gold uses canonical labels
  (`Google Analytics 4`, `Machine Learning`). Measures the pipeline after
  entity normalization. Only fixtures with a `.expected.normalized.json`
  participate (currently 004); the rest are skipped with an explicit reason.

Fixture targeting: 004 targets normalization; 005 targets parsing; all others
target raw extraction (with graph-construction concerns encoded in gold
design, e.g. one org node per org).

## 10. Fixture reference table

| Fixture | Profile | Failure mode probed | Present types | Absent types | Excluded near-matches | Target |
|---------|---------|--------------------|---------------|--------------|----------------------|--------|
| `sample_resume_001` | Clean technical (data scientist) | baseline; org legal-suffix variation | all six | — | — | raw extraction |
| `sample_resume_002` | Career changer (research → consulting → ML) | hallucinated certs; adjacency ≠ skill | person, jobs, skills, education, orgs | certifications | skills: AWS | raw extraction |
| `sample_resume_003` | Academic/research (neuro postdoc) | venues as orgs; duplicate org nodes | person, jobs, skills, education, orgs | certifications | orgs: Journal of Cognitive Neuroscience, Society for Neuroscience | raw extraction |
| `sample_resume_004` | Abbreviation-heavy data engineer | raw/normalized boundary; aspirational skills | all six | — | skills: Rust, Kubernetes; orgs: Google Cloud | normalization |
| `sample_resume_005` | IT sysadmin, messy two-column text | column-split truncation; org suffix dup; two roles/one org | all six | — | orgs: CompTIA | parsing |
| `sample_resume_006` | Healthcare/operations (ER nurse) | soft-skill promotion; issuer as employer; cert surface-form strictness | all six | — | skills: compassionate communicator, team leader; orgs: Board of Certification for Emergency Nursing | raw extraction |
| `sample_resume_007` | Executive/product strategy | invented degrees; tool names in proper names; program as org; adjective skills | person, jobs, skills, orgs | education, certifications | skills: Python, Tableau, visionary leader, strategic thinker; orgs: Tableau Health Initiative | raw extraction |

## Recommended next steps

1. **Run the live eval once per provider** (Claude, OpenAI, Ollama) and check
   the collected outputs into a private comparison note (not the repo) — that
   turns this from harness-proof into model-measurement.
2. **Reconcile fixture 004's normalized gold** with what the live normalizer
   actually canonicalizes to, then add normalized golds for 001 and 006.
3. **Add a pre-normalization snapshot** in the backend (store raw LLM JSON
   next to the normalized entities) so raw mode can be measured live too.
4. **Extend the comparator to relationships** (job→org edges, dates) once
   entity-level scores are stable — fixture golds already carry
   `organization` fields on jobs for this.
5. Optionally wire `run_eval.py --all --strict --extracted-dir <known-good>`
   into CI once a blessed set of real outputs exists.
