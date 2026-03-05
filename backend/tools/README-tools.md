# Resume Explorer — Post-Export Analysis Pipeline

**Location:** `backend/tools/`

These scripts operate on JSON-LD files exported from Resume Explorer. They normalize entities, analyze graph structure, and (optionally) embed the results into ChromaDB for the Digital Twin's retrieval pipeline.

They are **not** part of the deployed app. They run on localhost, after Resume Explorer has processed one or more resumes and exported the graph.

```
                    ┌──────────────────────┐
                    │   Resume Explorer    │
                    │   (Koyeb + Vercel)   │
                    └──────────┬───────────┘
                               │ Export .jsonld
                               ▼
┌─────────────────────────────────────────────────────────┐
│                  LOCAL PIPELINE (this directory)        │
│                                                         │
│  ┌─────────────────────┐    ┌──────────────────────┐    │
│  │ entity_normalizer.py │───▶│  graph_analyzer.py   │   │
│  │                      │    │                      │   │
│  │ • URL-decode cleanup │    │ • Skill gap analysis │   │
│  │ • Case normalization │    │ • Career topology    │   │
│  │ • LLM semantic merge │    │ • Tech evolution     │   │
│  │                      │    │ • ESCO coverage      │   │
│  └──────────┬───────────┘    │ • Role progression   │   │
│             │                │ • Hierarchy map      │   │
│    normalized.jsonld         └──────────┬───────────┘   │
│                                         │               │
│                                   insights/*.md         │
│                                         │               │
│                              ┌──────────▼───────────┐   │
│                              │  embed_insights.py   │   │
│                              │  (future)            │   │
│                              │  → ChromaDB          │   │
│                              └──────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │     Digital Twin     │
                    │   (HuggingFace)      │
                    └──────────────────────┘
```

---

## Prerequisites

These scripts use dependencies that are already in the backend's `requirements.txt`. If you're running from within the backend virtual environment, you should be set. If not:

```bash
pip install networkx anthropic   # or openai, depending on your provider
```

No other dependencies required. The scripts read/write JSON and Markdown — no database, no web server, no frontend build.

---

## Quick Start (the 3-command version)

```bash
# From the backend/ directory, after exporting a .jsonld from Resume Explorer:

# 1. Normalize entities (fix "GA4" vs "Google Analytics 4", etc.)
python tools/entity_normalizer.py \
  --input  my-export.jsonld \
  --output my-export-normalized.jsonld \
  --provider anthropic

# 2. Analyze the graph structure
python tools/graph_analyzer.py \
  --input  my-export-normalized.jsonld \
  --output insights/

# 3. Read the results
ls insights/
cat insights/skill_gap.md
```

That's it. You now have 6 insight documents derived from graph topology, ready to embed into the Digital Twin or read directly.

---

## Step-by-Step Guide

### Step 0: Export from Resume Explorer

1. Open Resume Explorer in your browser (local or deployed)
2. Upload one or more resume variants (uploading multiple builds a richer graph)
3. Click **Export → JSON-LD** in the Export Panel
4. Save the `.jsonld` file somewhere accessible (e.g., `backend/data/exports/`)

**Tip:** For the richest analysis, upload your 2–3 most distinct resume variants (AI Engineer, Solutions Architect, etc.) in the same session before exporting. Resume Explorer accumulates entities across uploads within a session.

---

### Step 1: Entity Normalization

**What it does:** Fixes naming inconsistencies that degrade downstream analysis. Three phases:

| Phase | What it catches | Cost |
|-------|----------------|------|
| Deterministic | URL encoding (`GUI%20development` → `GUI development`), case variants (`wiki` → `Wiki`) | Free, instant |
| ESCO-anchored | Two skills sharing the same ESCO URI | Free, instant |
| LLM batch | Semantic aliases (`GA4` ↔ `Google Analytics 4`) | ~$0.01–0.05, seconds |

**Run it:**

```bash
# With LLM semantic resolution (recommended)
python tools/entity_normalizer.py \
  --input  data/exports/my-resume.jsonld \
  --output data/exports/my-resume-normalized.jsonld \
  --provider anthropic

# Without LLM (deterministic phases only — good for testing)
python tools/entity_normalizer.py \
  --input  data/exports/my-resume.jsonld \
  --output data/exports/my-resume-normalized.jsonld \
  --provider mock

# Dry run (see what would change without writing files)
python tools/entity_normalizer.py \
  --input  data/exports/my-resume.jsonld \
  --output data/exports/my-resume-normalized.jsonld \
  --provider anthropic \
  --dry-run
```

**Output:**
- `my-resume-normalized.jsonld` — cleaned JSON-LD, drop-in replacement for the original
- `my-resume-normalized.jsonld.report.json` — every merge decision with reasoning (for transparency)

**What to look for:**
- The console shows all label changes. Verify they make sense.
- If the LLM merged something it shouldn't have (false merge), you have a problem. Check the report's `reasoning` field. False merges are worse than missed duplicates — they lose information.
- If running with `--provider mock`, you'll only get case/encoding fixes. Run with `anthropic` or `openai` at least once to catch semantic aliases.

**Provider options:**
- `anthropic` — uses Claude Sonnet via the Anthropic API. Set `ANTHROPIC_API_KEY` env var.
- `openai` — uses GPT-4o-mini via the OpenAI API. Set `OPENAI_API_KEY` env var.
- `mock` — skips the LLM entirely. Useful for testing the pipeline without API keys.

---

### Step 2: Graph Analysis

**What it does:** Runs 6 structural analyses against the (normalized) graph and serializes findings as natural language documents optimized for embedding retrieval.

| Analysis | What it reveals |
|----------|----------------|
| Skill Gap | Skills claimed but never used, technologies used but never claimed |
| Career Topology | Bridge technologies, isolated roles, career connectivity |
| Tech Evolution | How the technology toolkit changed across roles chronologically |
| Hierarchy Map | SKOS broader/narrower relationships, orphan skills |
| ESCO Coverage | Which skills have global identifiers vs. string-only |
| Role Progression | Career arc, tenure patterns, title trajectory |

**Run it:**

```bash
# Basic usage
python tools/graph_analyzer.py \
  --input  data/exports/my-resume-normalized.jsonld \
  --output data/insights/

# The output directory will be created if it doesn't exist
```

**Output:**
- `data/insights/skill_gap.md`
- `data/insights/career_topology.md`
- `data/insights/tech_evolution.md`
- `data/insights/hierarchy_map.md`
- `data/insights/esco_coverage.md`
- `data/insights/role_progression.md`

Each file includes YAML front matter with metadata, tags, and query hints (the phrases someone might use when searching for this type of information).

**What to look for:**
- Read `skill_gap.md` first — it's the most immediately interesting.
- Check whether the claimed-vs-used overlap makes sense. If a skill shows as "ungrounded" but you know you've used it, there may be a naming mismatch the normalizer didn't catch.
- The topology analysis reveals your career's connective tissue. If it says you have 0 bridge technologies, that's a real (and interesting) finding — it means your value is methodological, not tool-specific.

---

### Step 3: Embed into Digital Twin (future)

This step is not yet implemented as a script. When it is, it will:

```bash
# Future usage (embed_insights.py doesn't exist yet)
python tools/embed_insights.py \
  --input     data/insights/ \
  --collection digital_twin \
  --chromadb-path /path/to/twin/chromadb
```

**For now, the manual process is:**

1. Copy the 6 `.md` files from `data/insights/` into your Digital Twin's `knowledge_base/` directory
2. Re-run the Digital Twin's embedding pipeline (however you currently ingest documents into ChromaDB)
3. Test: ask the Twin "What hidden skills does Dagny have?" — it should retrieve the skill gap analysis

---

## Testing the Pipeline (validation checklist)

### Validate entity_normalizer.py

```bash
# 1. Run in mock mode — should produce deterministic output
python tools/entity_normalizer.py \
  --input test-export.jsonld \
  --output test-normalized-mock.jsonld \
  --provider mock

# 2. Run again — output should be identical (idempotent)
python tools/entity_normalizer.py \
  --input test-export.jsonld \
  --output test-normalized-mock-2.jsonld \
  --provider mock

diff test-normalized-mock.jsonld test-normalized-mock-2.jsonld
# Should report: no differences

# 3. Run with LLM — check that semantic merges make sense
python tools/entity_normalizer.py \
  --input test-export.jsonld \
  --output test-normalized-live.jsonld \
  --provider anthropic

# 4. Read the report
cat test-normalized-live.jsonld.report.json | python -m json.tool

# 5. Verify the normalized file is still valid JSON-LD
python -c "import json; json.load(open('test-normalized-live.jsonld')); print('Valid JSON')"
```

**What to check:**
- [ ] Mock mode produces only case/encoding fixes (no semantic merges)
- [ ] Mock mode is idempotent (same input → same output)
- [ ] LLM mode catches known aliases (e.g., GA4 ↔ Google Analytics 4)
- [ ] LLM mode does NOT false-merge distinct concepts (e.g., PowerBI ≠ Business Intelligence)
- [ ] Output is valid JSON-LD
- [ ] Report file documents every merge decision

### Validate graph_analyzer.py

```bash
# 1. Run against normalized output
python tools/graph_analyzer.py \
  --input test-normalized-live.jsonld \
  --output test-insights/

# 2. Check all 6 files were created
ls test-insights/
# Should show: skill_gap.md, career_topology.md, tech_evolution.md,
#              hierarchy_map.md, esco_coverage.md, role_progression.md

# 3. Verify content isn't empty
wc -c test-insights/*.md
# Each file should be 500+ characters

# 4. Check YAML front matter is valid
python -c "
import yaml
for f in ['skill_gap','career_topology','tech_evolution','hierarchy_map','esco_coverage','role_progression']:
    with open(f'test-insights/{f}.md') as fh:
        content = fh.read()
        # Extract YAML between --- markers
        parts = content.split('---')
        if len(parts) >= 3:
            meta = yaml.safe_load(parts[1])
            print(f'{f}: {meta.get(\"title\", \"NO TITLE\")}')
        else:
            print(f'{f}: MISSING FRONT MATTER')
"
```

**What to check:**
- [ ] All 6 insight files created
- [ ] Each file has valid YAML front matter with title, tags, query_hints
- [ ] Skill gap numbers are plausible (declared skills, used technologies, overlap count)
- [ ] No Python tracebacks in the output
- [ ] Running against the same input produces the same output (deterministic)

### Validate the full pipeline (end-to-end)

```bash
# The complete sequence
python tools/entity_normalizer.py \
  --input  data/exports/my-resume.jsonld \
  --output data/exports/my-resume-normalized.jsonld \
  --provider anthropic

python tools/graph_analyzer.py \
  --input  data/exports/my-resume-normalized.jsonld \
  --output data/insights/

# Verify: compare raw vs normalized analysis
python tools/graph_analyzer.py \
  --input  data/exports/my-resume.jsonld \
  --output data/insights-raw/

# Then diff the skill gap findings
diff data/insights-raw/skill_gap.md data/insights/skill_gap.md
# Should show: fewer false positives after normalization
```

---

## Troubleshooting

**"ModuleNotFoundError: No module named 'networkx'"**
→ Install dependencies: `pip install networkx`

**"Could not resolve authentication method" (entity_normalizer.py)**
→ Set your API key: `export ANTHROPIC_API_KEY=sk-ant-...` (or `OPENAI_API_KEY` if using `--provider openai`)
→ Or run with `--provider mock` to skip LLM normalization

**"Expected a JSON array at top level"**
→ The input file isn't a Resume Explorer JSON-LD export. Check that you exported from Resume Explorer's Export Panel, not from another tool.

**Skill gap shows skills you know you've used as "ungrounded"**
→ The normalizer didn't catch a naming alias. Check the report file for what was merged, and consider whether the source resume needs to be re-processed with more consistent naming.

**Graph analyzer reports 0 jobs or 0 skills**
→ The JSON-LD might be from an older export format. Check that entities have `@type` values matching `http://data.europa.eu/esco/Skill` and `http://schema.org/JobPosting`.

---

## Design Decisions

**Why are these standalone scripts, not part of the deployed app?**
They operate on *exported* data, not live session data. They require LLM API keys the deployed app doesn't need. They produce files for a different system (the Digital Twin). Keeping them separate means the deployed app stays lean and these tools can evolve independently.

**Why does entity_normalizer.py use batch LLM instead of fuzzy matching?**
Resume graphs have 20–50 entities. At that scale, a single LLM call is cheaper, faster, and more accurate than tuning fuzzy thresholds. The podcast project (GraphRAG) used fuzzy matching because it had 720 concepts — the scale difference changes the optimal strategy. See the script's docstring for the full rationale.

**Why does graph_analyzer.py write Markdown instead of JSON?**
The downstream consumer is ChromaDB (via the Digital Twin), which embeds text documents. Markdown with YAML front matter gives us both human-readable output (you can read the insights directly) and machine-parseable metadata (tags, query hints for retrieval). JSON would be harder to read and wouldn't embed as well.

---

## File Reference

| File | Purpose | Input | Output |
|------|---------|-------|--------|
| `entity_normalizer.py` | Fix naming inconsistencies across entity types | `.jsonld` | `.jsonld` + `.report.json` |
| `graph_analyzer.py` | Run 6 structural analyses on the graph | `.jsonld` | 6 × `.md` files |
| `embed_insights.py` | Embed insight docs into ChromaDB (future) | `.md` files | ChromaDB collection |
