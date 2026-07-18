# Resume Explorer — Evaluation Plan

> **Format:** Hybrid. Automated pytest for structural correctness and precision/recall. Markdown checklists for qualitative assessment (narrative quality, provider comparison).

---

## 1. Structural Correctness (Automated)

Run `pytest tests/ -v` before any merge to main. All of the following must pass:

| Test file | What it covers |
|-----------|---------------|
| `tests/test_unknown_nodes.py` | Zero unknown nodes in single and multi-resume graphs |
| `tests/test_normalizer.py` | Deterministic and ESCO-anchored normalization regressions |
| `tests/test_graph.py` | RDF graph builder dedup caches, edge creation |
| `tests/test_models.py` | Entity model serialization / deserialization |

Regression guard: **all 4 files must pass with zero failures** before any PR is merged to `main`.

---

## 2. Precision + Recall (Automated, requires fixtures)

Tests live in `tests/test_evaluation.py`. They skip automatically if fixture files are missing.

### Setup

**Step 1 — Author ground truth files**

Copy `tests/fixtures/ground_truth_schema.json` to:
- `tests/fixtures/resume_v1_gt.json` (Barbara's Atlassian resume)
- `tests/fixtures/resume_v2_gt.json` (second resume version)

Fill in the values by hand based on what each resume actually contains. See the schema file for field descriptions.

**Step 2 — Save pre-recorded extraction output**

Run the extraction pipeline once on each resume. Copy the JSON entities from the `/documents/{id}/entities` API response to:
- `tests/fixtures/resume_v1_extracted.json`
- `tests/fixtures/resume_v2_extracted.json`

Review this output before saving — this is what the tests measure against.

**Step 3 — Run evaluation tests**

```bash
cd backend
pytest tests/test_evaluation.py -v
```

### Current thresholds

| Metric | Threshold | Rationale |
|--------|-----------|-----------|
| Skill recall | ≥ 80% | Most skills should be found |
| Skill precision | ≥ 70% | Up to 30% false positives acceptable (LLMs are creative) |
| Job recall | ≥ 75% | Some jobs may not be extracted cleanly from dense layouts |
| Org recall | ≥ 75% | Org names vary; fuzzy dedup may collapse some |

Adjust thresholds in `test_evaluation.py` as you calibrate against your actual resumes.

---

## 3. Entity Quality Rubric (Manual)

After each extraction run, spot-check with this checklist:

**Skills**
- [ ] Skill labels are normalized (no "machine learning" vs "Machine Learning" duplicates)
- [ ] No vendor-specific skills hallucinated (e.g., tools not mentioned in the resume)
- [ ] SKOS URIs populated for common skills where ESCO matches (check `skos_uri` field)
- [ ] `alt_labels` contain expected aliases after normalization (e.g., "ML" merged into "Machine Learning")

**Jobs**
- [ ] Job titles are complete (not truncated or split incorrectly)
- [ ] Date ranges extracted where present
- [ ] Organization linked via `organization_id` (not orphaned)
- [ ] `technologies_used` list is populated and reasonable

**Organizations**
- [ ] "Acme Corp" and "Acme Corp, Inc." → one node (multi-suffix dedup)
- [ ] Short company names (e.g., "IBM") not incorrectly merged with others
- [ ] No blank organization names

**Education**
- [ ] Degree abbreviations normalized (not "Master of Science" and "MS" as two nodes)
- [ ] Field of study captured

---

## 4. Multi-Resume Scenarios (Manual checklist)

### Scenario A: Same person, two resume versions

1. Upload Resume v1 → note entity counts
2. Upload Resume v2 (same session) → verify:
   - [ ] Still exactly 1 person node
   - [ ] Skills appearing in both versions deduplicated (counts don't double)
   - [ ] New skills from v2 appear as additional nodes
   - [ ] Zero unknown nodes
   - [ ] `source_doc` on each entity indicates which resume it came from

### Scenario B: Identical file uploaded twice

1. Upload Resume v1
2. Upload Resume v1 again (same session) → verify:
   - [ ] HTTP 409 returned with `duplicate_of` field
   - [ ] Graph unchanged (no duplicated nodes)

### Scenario C: Two different people (edge case)

1. Upload Alice's resume
2. Upload Bob's resume (same session) → verify:
   - [ ] 2 person nodes (one per person)
   - [ ] No skills or jobs incorrectly merged across people
   - [ ] Zero unknown nodes

---

## 5. Narrative Quality Rubric (Qualitative)

After running the full pipeline (`/pipeline/analyze` → `/pipeline/synthesize`), rate the output on a 1–5 scale:

| Dimension | 1 (poor) | 3 (ok) | 5 (excellent) |
|-----------|----------|--------|---------------|
| **Factual accuracy** | Contains facts not in the resume | Mostly accurate, minor drift | All statements traceable to the resume |
| **Career arc** | Doesn't reflect trajectory | Captures rough arc | Accurately narrates progression (IC → management, domain shift, etc.) |
| **Skill representation** | Key skills missing or wrong emphasis | Major skills present | Correct emphasis, ESCO-aligned groupings visible |
| **Tone** | Generic, resume-speak | Readable | Specific, engaging, sounds like the person |
| **Conservative vs exploratory** | Indistinguishable | Some difference | Clearly distinct registers (factual vs forward-looking) |

Target: average ≥ 3.5 across dimensions before publishing a provider as "supported."

---

## 6. Provider Comparison Matrix

Run the same resume (Barbara's Atlassian resume, v1) through each provider. Record:

| Provider | Skill recall | Skill precision | Job recall | Latency (s) | Cost per run | Notes |
|----------|-------------|-----------------|------------|-------------|--------------|-------|
| Claude (claude-sonnet-4-6) | — | — | — | — | — | |
| OpenAI (gpt-4o) | — | — | — | — | — | |
| Ollama (llama3) | — | — | — | — | — | |

Fill in by running `pytest tests/test_evaluation.py` with each provider configured in `.env`.

**Decision criterion:** Recall ≥ 80% AND precision ≥ 70% AND latency ≤ 30s → "supported."

---

## 7. Export Fidelity

After any change to `export_session_graph` or `get_session_graph`, verify:

- [ ] Entity counts in Turtle export match entity counts in in-app graph (`/sessions/{id}/stats`)
- [ ] All skills from both resumes appear in the export (not just one document's worth)
- [ ] `skos:altLabel` triples present for merged/normalized skills
- [ ] `re:sourceDocument` triple present on each entity

Manual check: export as Turtle, open in a text editor, count `skos:prefLabel` occurrences.

---

## 8. Editable Node Labels

After implementing the edit feature, verify:

- [ ] Edit a skill label → graph refreshes with new label immediately
- [ ] New label persists after page refresh (stored in session entities)
- [ ] `user_verified=True` entity label not overwritten by subsequent normalization
- [ ] `user_notes` appears in the entity panel after save
- [ ] Editing a deduped skill updates both source documents (check raw JSON in `data/sessions/`)
- [ ] PATCH to unknown entity → 404
- [ ] PATCH with unknown field → 400

---

## File locations

| File | Purpose |
|------|---------|
| `backend/tests/test_evaluation.py` | Automated precision/recall + structural tests |
| `backend/tests/conftest.py` | Fixture loading (ground truth + pre-recorded extractions) |
| `backend/tests/fixtures/ground_truth_schema.json` | Schema template for ground truth files |
| `backend/tests/fixtures/resume_v1_gt.json` | Ground truth for Resume 1 (author manually) |
| `backend/tests/fixtures/resume_v1_extracted.json` | Pre-recorded extraction for Resume 1 (save after one run) |
| `backend/tests/test_unknown_nodes.py` | Regression guard for the multi-resume unknown-node bug |
