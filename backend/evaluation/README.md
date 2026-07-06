# Evaluation Suite

A compact, deterministic evaluation suite for measuring resume extraction
quality over time. The offline core does **not** call any LLM — it compares
extraction output (JSON) against hand-written gold labels and reports
per-entity-type precision, recall, and F1. A separate opt-in script drives a
running backend to evaluate real LLM extractions against the same gold labels.

## What this proves (and what it doesn't)

**Proves:** given an extraction output, exactly which expected entities were
found, missed, or hallucinated — reproducibly, offline, without API keys.
The fixture suite is deliberately adversarial (absent sections, aliases,
near-matches, messy formatting), so it also proves the harness *detects* the
failure modes the project cares about.

**Does not prove:** overall LLM extraction quality on real-world resumes.
The fixtures are synthetic and small. Real conclusions require running live
extractions (`run_live_eval.py`) across providers/prompts and, eventually, a
larger fixture set.

## Layout

```
backend/evaluation/
├── compare.py            # pure comparison logic + metrics (single fixture)
├── batch.py              # batch runner + aggregation across the suite
├── run_eval.py           # CLI: single-fixture, --demo, and --all batch modes
├── run_live_eval.py      # opt-in: drive a running backend, score real extractions
├── fixtures/
│   ├── manifest.json                          # per-fixture metadata (what each tests)
│   ├── sample_resume_NNN.txt                  # synthetic resume text
│   ├── sample_resume_NNN.expected.json        # gold labels (raw surface forms)
│   ├── sample_resume_NNN.extracted.json       # simulated extraction (offline demo)
│   └── sample_resume_004.expected.normalized.json  # canonical-label gold (normalized mode)
├── live_runs/             # gitignored — outputs collected by run_live_eval.py
└── README.md
```

## The fixture suite

Seven synthetic resumes, each designed to probe a specific failure mode.
`fixtures/manifest.json` is the source of truth — for every fixture it records
the profile, what it tests, which entity types are intentionally present or
absent, which near-matches must **not** be extracted, and which pipeline stage
it targets (raw extraction, normalization, parsing, graph construction).

| Fixture | Profile | Probes |
|---------|---------|--------|
| 001 | Clean technical (data scientist) | baseline; org legal-suffix variation |
| 002 | Career changer (research → consulting → ML) | empty certifications; "partnered with the AWS team" is not an AWS skill |
| 003 | Academic/research (neuroscience postdoc) | journals/conferences are not organizations; one org node for two roles |
| 004 | Abbreviation-heavy data engineer | raw vs normalized gold (ML/GA4/GCP…); aspirational skills excluded |
| 005 | IT sysadmin, messy two-column text | parsing artifacts; `Northwind Data, LLC` = `Northwind Data` |
| 006 | Healthcare/operations (emergency nurse) | non-software skills; soft-skill adjectives excluded; cert issuers are not employers |
| 007 | Executive/product strategy | empty education + certifications; `Python`/`Tableau` inside proper names are not skills |

The bundled `*.extracted.json` files are **simulated** extractions that
deliberately fail each fixture's trap, so the offline batch report always
demonstrates non-trivial detection. They are demo/test data, not model output.

## Running it

From `backend/`:

```bash
# Demo: one fixture, bundled simulated extraction vs. gold labels
python evaluation/run_eval.py --demo

# Batch: the whole suite, aggregated per-fixture and per-entity-type
python evaluation/run_eval.py --all

# Batch against canonical-label gold files (normalization quality)
python evaluation/run_eval.py --all --mode normalized

# Batch against real extraction outputs collected in a directory
python evaluation/run_eval.py --all --extracted-dir evaluation/live_runs/<ts>

# Compare one arbitrary extraction against one gold file
python evaluation/run_eval.py \
    --extracted data/sessions/<session-id>/extracted/<document-id>.json \
    --expected evaluation/fixtures/sample_resume_001.expected.json
```

**Exit codes:** single/`--demo` mode exits 0 only when every expected entity
was found. `--all` exits 0 when the batch runs; add `--strict` to exit 1 on
any missing/unexpected entity. The bundled simulated extractions are
deliberately imperfect, so `--all --strict` against them fails by design —
strict mode is for gating real outputs via `--extracted-dir`.

The suite is also exercised by pytest (no network, no keys):
`tests/test_evaluation_harness.py`, `tests/test_eval_fixtures.py`,
`tests/test_eval_batch.py`.

## Raw extraction vs. post-normalization evaluation

These are different questions and the suite keeps them separate:

- **Raw mode** (`--mode raw`, the default) scores against
  `<id>.expected.json`, whose gold labels preserve the resume's *surface
  forms*. If the resume says `GA4`, raw gold says `GA4`; an extractor that
  returns `Google Analytics 4` is *editorializing* and scores a miss plus an
  unexpected. Raw mode answers: *did the extractor faithfully capture what
  the document says?*
- **Normalized mode** (`--mode normalized`) scores against
  `<id>.expected.normalized.json`, whose gold labels use canonical names
  (`Machine Learning`, `Google Analytics 4`, …). It answers: *after the
  entity normalizer runs, does the pipeline land on canonical labels?*
  Fixtures without a normalized gold file are skipped in this mode —
  currently only fixture 004 (the abbreviation-heavy one) carries both golds.

To actually evaluate the normalizer, feed normalized pipeline output (e.g.
entities stored after a multi-document session, or a single-document session
with `NORMALIZE_SINGLE_RESUME=true`) to `--all --mode normalized
--extracted-dir <dir>`. Extension point: add
`<id>.expected.normalized.json` files (and flip `has_normalized_expected` in
the manifest) for more fixtures as the normalizer's canonical vocabulary
firms up.

## Matching rules

Deliberately simple string matching, normalized (casefold, whitespace
collapse; org names also drop legal suffixes like ", Inc."):

| Type           | Matched on                       |
|----------------|----------------------------------|
| person         | `name`                           |
| skills         | `label` (or `name`)              |
| jobs           | `title`                          |
| education      | `degree_type` + `field_of_study` |
| certifications | `name`                           |
| organizations  | `name` (suffix-stripped)         |

Known strictness: certification gold uses the full printed surface form, so
an extractor returning `BLS` against gold `Basic Life Support (BLS)` scores a
miss + an unexpected (fixture 006 demonstrates this on purpose). Matching is
set-based per document, so duplicate entries with the same key collapse.

## Gold-label annotation rules

The gold labels follow explicit rules — they do not simply mirror what a
likely extractor would output:

1. Include entities that are explicitly stated or strongly evidenced.
2. Exclude adjacency ("partnered with the AWS team" ≠ AWS skill),
   aspiration ("interested in learning Rust" ≠ Rust skill), and words inside
   other proper names ("Python Creek Ventures" ≠ Python skill).
3. Generic soft-skill adjectives ("strategic thinker", "compassionate
   communicator") are not skills; named, evidenced practices (OKRs,
   A/B testing) are.
4. Certification issuers, journals, and conferences are not organizations —
   organizations are employers/institutions the person was affiliated with.
5. One organization node per organization, regardless of role count or
   legal-suffix variation.
6. Absent entity types are present-but-empty lists (`"certifications": []`),
   so hallucinations into them are caught.
7. When in doubt, document the decision in the fixture's `_comment` and its
   manifest entry.

`tests/test_eval_fixtures.py` enforces the mechanical parts of these rules
(absent types empty, excluded near-matches not in gold, synthetic emails only).

## Adding a new eval case

1. Add `fixtures/sample_resume_NNN.txt` — a small **synthetic** resume
   (never real personal data; emails must be `@example.com`/`@example.org`).
   Give it a job: what failure mode does it probe that no existing fixture does?
2. Add `fixtures/sample_resume_NNN.expected.json` — gold labels following the
   annotation rules above. Include every list type, empty if intentionally
   absent.
3. Add `fixtures/sample_resume_NNN.extracted.json` — a simulated extraction
   that fails the fixture's trap, so the offline batch demo demonstrates
   detection.
4. Add a manifest entry with all metadata fields (see existing entries).
5. Run `pytest tests/test_eval_fixtures.py tests/test_eval_batch.py` — the
   fixture-discipline tests will tell you what's missing.

## Live extraction evaluation (opt-in, costs tokens)

`run_live_eval.py` drives a **running** backend over HTTP: it creates one
session per fixture, uploads the resume, polls until extraction completes,
saves the stored entities to `evaluation/live_runs/<timestamp>/`, deletes the
session, and scores the collected outputs with the same batch comparator.

```bash
# 1. Start the backend with a real API key in ITS environment
cd backend && python -m resume_explorer.api.app

# 2. In another terminal, from backend/:
python evaluation/run_live_eval.py                       # all fixtures
python evaluation/run_live_eval.py --fixture sample_resume_004
python evaluation/run_live_eval.py --collect-only        # score later
```

Notes:
- The script never sees or logs API keys — the backend holds them.
- `live_runs/` is gitignored; never commit generated session data.
- The backend runs deterministic + ESCO normalization automatically after
  extraction, so collected entities are "as-persisted", not the raw LLM
  response (see the script docstring for the exact caveat).
- It is never run by pytest.
- Extension point: run it once per provider/prompt variant and diff the
  saved `live_runs/` directories to compare configurations.
