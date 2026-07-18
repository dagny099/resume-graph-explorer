# Evaluation Harness (Lite)

A small, deterministic scaffold for measuring resume extraction quality
over time. It does **not** call any LLM — it compares an extraction output
(JSON) against hand-written gold labels and reports per-entity-type
precision, recall, and F1.

## What this proves (and what it doesn't)

**Proves:** given an extraction output, exactly which expected entities were
found, missed, or hallucinated — reproducibly, offline, without API keys.

**Does not prove:** overall LLM extraction quality. There is currently one
tiny synthetic resume in the eval set. Real conclusions require running
actual extractions over a larger, more varied set of resumes and gold labels.

## Layout

```
backend/evaluation/
├── compare.py                              # pure comparison logic + metrics
├── run_eval.py                             # CLI wrapper
├── fixtures/
│   ├── sample_resume_001.txt               # tiny synthetic resume
│   ├── sample_resume_001.expected.json     # gold labels for it
│   └── sample_resume_001.extracted.json    # simulated extraction (demo)
└── README.md
```

## Running it

From `backend/`:

```bash
# Demo: bundled simulated extraction vs. gold labels
python evaluation/run_eval.py --demo

# Compare a real extraction (a session's stored entities) against gold labels
python evaluation/run_eval.py \
    --extracted data/sessions/<session-id>/extracted/<document-id>.json \
    --expected evaluation/fixtures/sample_resume_001.expected.json
```

The exit code is 0 only when every expected entity was found (recall 1.0
for every type), so the CLI can gate CI later.

The comparison logic is also exercised by `tests/test_evaluation_harness.py`
(runs with the normal `pytest` suite, no network).

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

Note that "GA4" does **not** match "Google Analytics 4" here — the harness
measures raw extraction output. If you want to evaluate post-normalization
quality, run the entity normalizer first and compare its output instead.

## Adding a new eval case

1. Add `fixtures/sample_resume_NNN.txt` — a small resume (synthetic or
   fully anonymized; never commit real personal data).
2. Add `fixtures/sample_resume_NNN.expected.json` — gold labels, same
   shape as the existing expected file. Entries can be plain strings or
   dicts; the comparator normalizes both.
3. (Optional) add a matching test case in `tests/test_evaluation_harness.py`.

## Connecting to real LLM extraction

To evaluate a live extraction end-to-end:

1. Start the backend with a real API key, create a session, and upload a
   fixture resume (e.g. `fixtures/sample_resume_001.txt`).
2. When extraction completes, the raw output is stored at
   `backend/data/sessions/<session-id>/extracted/<document-id>.json`.
3. Run `run_eval.py --extracted <that file> --expected <gold file>`.

A future pass could automate this loop (batch-upload every fixture, collect
outputs, aggregate scores across the set) — the comparator and fixture
format are already designed for it.
