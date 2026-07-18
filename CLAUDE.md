You are the **coding agent** for **Resume Explorer**, a full-stack application that transforms resumes into interactive SKOS-compliant knowledge graphs. The project is **deployed and functional** — you are working on an evolving codebase, not starting from scratch.

## Current State (as of April 2026)

The app is production-ready for both single and multi-resume sessions, deployed on Render/Koyeb. The codebase has ~12k+ lines across a Flask backend and React frontend.

**What exists and works:**
- Flask backend with REST API + WebSocket streaming for real-time extraction progress
- React + Vis.js interactive graph visualization
- LLM-powered entity extraction (Claude, OpenAI, Ollama) → SKOS-compliant RDF graph
- RDF export in Turtle, RDF/XML, JSON-LD
- Multi-document session management with file-based persistence (`backend/data/sessions/`)
- Entity normalization: 3-phase pipeline (deterministic → ESCO-anchored → LLM batch), runs automatically on upload. Includes type-pool normalization, `skos:altLabel` preservation for merged skill aliases, and `user_verified` anchor protection.
- Multi-resume sessions: zero unknown nodes (4-part bug fix, April 2026). Two resumes of the same person → 1 Person node, merged skill/job lists, correct dedup.
- Duplicate file detection: uploading the same file twice to a session returns HTTP 409.
- Editable node labels: click any graph node → Edit → correct the label, add notes, mark as verified. Verified labels are authoritative anchors for future normalization runs.
- Post-export offline analysis pipeline (`backend/tools/`): entity_normalizer → graph_analyzer (6 structural analyses → markdown docs) → narrative_synthesizer
- Evaluation framework: `tests/test_evaluation.py` (precision/recall), `docs/EVALUATION_PLAN.md` (full methodology)

**Known issues to preserve/not regress:**
- DSPy threading issues: `ENABLE_DSPY` must stay `false` in deployed config

## Architecture Decisions to Know

**Two normalizers, two jobs:**
- `backend/resume_explorer/services/entity_normalizer.py` — LIVE, runs during upload, prevents duplicate entity nodes across multi-doc sessions. Phase 3 (LLM) only runs for 2+ docs unless `NORMALIZE_SINGLE_RESUME=true`.
- `backend/tools/entity_normalizer.py` — OFFLINE, runs post-export on JSON-LD files, reconciles skill prefLabels against job `usedTechnology` strings for clean graph analysis output. See `docs/GRAPH_ANALYSIS_PIPELINE.md`.

**RDF graph builder dedup caches** (first-defense before the normalizer):
- Skills: case-insensitive label (`_skill_cache`)
- Orgs: fuzzy-normalized name, iterative suffix stripping ("Corp", "Inc.", "LLC", etc.) — `_normalize_org_name`. Iterative loop, not `break`-on-first-match, so "Acme Corp, Inc." and "Acme Corp" collapse correctly.
- Jobs: exact `(title, org_uri, start_date)` tuple first; then fuzzy title similarity (≥0.85 SequenceMatcher) at same org within 30 days. Handles "Senior Engineer" ↔ "Sr. Software Engineer" dedup.
- Education: (degree, field, institution) tuple

**`alt_labels` on Skill** (added March 2026): When the normalizer merges a variant label (e.g. "ML" → "Machine Learning"), the original is stored in `skill.alt_labels` and written as `skos:altLabel` triples in the RDF export. When a user edits a skill label via the UI, the old label is also preserved as `alt_label`. Adding new optional fields with defaults to `SKOSEntity` subclasses is backward-compatible: `from_dict` filters to `__dataclass_fields__`, so old sessions without the field load safely.

**`user_verified` and `user_notes` on `SKOSEntity`** (added April 2026): Two optional fields on the base dataclass. `user_verified=True` makes an entity's label authoritative — the normalizer protects it from being remapped (identity override in `label_map`) and skips it during `_apply_normalization`. New uploads normalize *toward* verified labels, never away. `user_notes` is freeform. Both backward-compatible.

**Editable nodes** (added April 2026): `PATCH /api/sessions/{id}/entities/{entity_type}/{entity_id}` — mutable fields: `label`, `user_verified`, `user_notes`. Whitelist-validated (unknown fields → 400). Searches by UUID (primary) then by normalized label (secondary, covers cross-doc dedup cases). Propagates to all source documents in the session.

**WebSocket + Flask-SocketIO**: Uses eventlet. In deployment, gunicorn must use `--worker-class eventlet -w 1`. Nginx needs `Upgrade`/`Connection` headers for WebSocket proxying.

**Offline pipeline (Avenue 3 / Phase 1)**: `backend/tools/` scripts are standalone — they operate on exported JSON-LD, need different API keys, and produce files for a downstream Digital Twin. They are not part of the deployed app. See `docs/GRAPH_ANALYSIS_PIPELINE.md` for the 3-phase roadmap.

**ESCO skill hierarchy (`backend/tools/esco_lookup.py`)** — added March 2026:
- Uses the ESCO REST API at *analysis* time (not upload time) — no CSV download, no auth required.
- Cache: `backend/data/esco/skill_cache.json` (already gitignored via `backend/data/`). Populated on first analysis run (~0.1 s/skill), instant thereafter.
- `graph_analyzer.py` adds the tools directory to `sys.path` at module level so `esco_lookup` is importable both as a CLI script and when loaded via `importlib.util.spec_from_file_location()` from `pipeline_service.py`.
- The old `_CLUSTER_HINTS` list and `_infer_skill_clusters()` function in `graph_analyzer.py` were removed. Do not re-add them.
- Match rate ~50–60% for typical resumes. Vendor-specific tools (AWS, TensorFlow, Kubernetes) correctly return no ESCO match — this is expected, not a bug.

## Document Processing Architecture

Resume Explorer supports multiple document formats with a robust extraction pipeline.

### Supported Formats
- **PDF**: Dual-library approach (PyMuPDF primary, pdfplumber fallback)
- **DOCX/DOC**: Microsoft Word via python-docx
- **TXT**: Plain text (direct read)
- **MD**: Markdown (direct read)

### PDF Extraction Strategy

**1. Primary: PyMuPDF (fitz)** — fast, handles standard PDFs page-by-page

**2. Fallback: pdfplumber** — slower but handles complex layouts, tables, forms

### Implementation Location
- File: `backend/resume_explorer/utils/document_processor.py`
- Class: `DocumentProcessor`
- Byte stream processing for file uploads supported

If adding new file formats, follow the pattern in `DocumentProcessor`. Always provide fallback mechanisms. See `docs/DOCUMENT_PROCESSING.md`.

## Key Configuration

```bash
LLM_PROVIDER=claude              # claude | openai | ollama
ENABLE_DSPY=false                # MUST stay false — threading issues
NORMALIZATION_PROVIDER=mock      # mock | ollama | anthropic | openai
NORMALIZE_SINGLE_RESUME=false    # true = run LLM Phase 3 for single-resume sessions
```

## Working Model

- Prioritize simplicity and not breaking existing functionality
- The hardest-won features are org fuzzy dedup and skill normalization — be cautious in those areas
- When modifying entity models, check `from_dict` and `to_dict` for both the model and its base class (`SKOSEntity`)
- When modifying normalization, run `pytest tests/test_normalizer.py` to verify no regressions
- Tests live in `backend/tests/` — run with `cd backend && pytest tests/ -v`

## Style

Code should be:
- Clean, modular, documented
- Pythonic and readable
- Minimal — avoid adding abstraction layers or error handling for scenarios that can't happen

When something is unclear, ask rather than guessing.
