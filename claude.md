You are the **coding agent** for **Resume Explorer**, a full-stack application that transforms resumes into interactive SKOS-compliant knowledge graphs. The project is **deployed and functional** — you are working on an evolving codebase, not starting from scratch.

## Current State (as of March 2026)

The app is production-ready for single-resume sessions and deployed on Render/Koyeb. The codebase has ~10k+ lines across a Flask backend and React frontend.

**What exists and works:**
- Flask backend with REST API + WebSocket streaming for real-time extraction progress
- React + Vis.js interactive graph visualization
- LLM-powered entity extraction (Claude, OpenAI, Ollama) → SKOS-compliant RDF graph
- RDF export in Turtle, RDF/XML, JSON-LD
- Multi-document session management with file-based persistence (`backend/data/sessions/`)
- Entity normalization: 3-phase pipeline (deterministic → ESCO-anchored → LLM batch), runs automatically on upload. As of March 2026, includes separate type-pool normalization and `skos:altLabel` preservation for merged skill aliases.
- Post-export offline analysis pipeline (`backend/tools/`): entity_normalizer → graph_analyzer (6 structural analyses → markdown docs) → narrative_synthesizer

**Known issues to preserve/not regress:**
- DSPy threading issues: `ENABLE_DSPY` must stay `false` in deployed config
- ~8-10 "unknown nodes" in multi-resume sessions (orphaned Person references after normalization — cosmetic only, fix in progress)
- Single-resume sessions are recommended; multi-resume is functional but has the above cosmetic issue

## Architecture Decisions to Know

**Two normalizers, two jobs:**
- `backend/resume_explorer/services/entity_normalizer.py` — LIVE, runs during upload, prevents duplicate entity nodes across multi-doc sessions. Phase 3 (LLM) only runs for 2+ docs unless `NORMALIZE_SINGLE_RESUME=true`.
- `backend/tools/entity_normalizer.py` — OFFLINE, runs post-export on JSON-LD files, reconciles skill prefLabels against job `usedTechnology` strings for clean graph analysis output. See `docs/GRAPH_ANALYSIS_PIPELINE.md`.

**RDF graph builder dedup caches** (first-defense before the normalizer):
- Skills: case-insensitive label (`_skill_cache`)
- Orgs: fuzzy-normalized name, strips "Inc.", "The " prefix (`_normalize_org_name`)
- Jobs: (title, org, start_date) tuple
- Education: (degree, field, institution) tuple

**`alt_labels` on Skill** (added March 2026): When the normalizer merges a variant label (e.g. "ML" → "Machine Learning"), the original is stored in `skill.alt_labels` and written as `skos:altLabel` triples in the RDF export. Adding new optional fields with defaults to `SKOSEntity` subclasses is backward-compatible: `from_dict` filters to `__dataclass_fields__`, so old sessions without the field load safely.

**WebSocket + Flask-SocketIO**: Uses eventlet. In deployment, gunicorn must use `--worker-class eventlet -w 1`. Nginx needs `Upgrade`/`Connection` headers for WebSocket proxying.

**Offline pipeline (Avenue 3 / Phase 1)**: `backend/tools/` scripts are standalone — they operate on exported JSON-LD, need different API keys, and produce files for a downstream Digital Twin. They are not part of the deployed app. See `docs/GRAPH_ANALYSIS_PIPELINE.md` for the 3-phase roadmap.

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
