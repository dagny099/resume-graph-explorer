# Resume Graph Explorer

[![Vercel](https://img.shields.io/badge/vercel-deployed-black?logo=vercel)](https://resume-graph-explorer.vercel.app)
[![Backend Status](https://img.shields.io/website?url=https%3A%2F%2Ffew-wallis-balex-atx-966af829.koyeb.app%2Fhealth&label=backend&up_message=online&down_message=offline)](https://few-wallis-balex-atx-966af829.koyeb.app)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg?logo=python)](https://www.python.org/downloads/)
[![Node](https://img.shields.io/badge/node-18+-green.svg?logo=node.js)](https://nodejs.org/)
[![SKOS](https://img.shields.io/badge/SKOS-compliant-purple)](https://www.w3.org/TR/skos-reference/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Turn a resume into a knowledge graph you can inspect, validate, query, and build on.**

Resume Graph Explorer extracts entities from resume documents using LLMs
(Claude, OpenAI, or local Ollama) and assembles them into an RDF knowledge
graph aligned with open standards — SKOS for concepts, schema.org for entity
types, ESCO for skill taxonomy. Explore the graph interactively, export it as
Turtle / RDF/XML / JSON-LD, check its semantic integrity via a validation
endpoint, and run a post-export analysis pipeline that turns graph structure
into natural-language career insights — documents designed to serve as
grounded memory for RAG systems and Digital Twins.

The deeper idea: a resume is a flat story, but a career has structure —
skills that bridge chapters, capabilities evidenced but never listed,
toolkits that drift over time. A resume says what you did; the graph shows
how it connects. Making that structure explicit, in open standards, is what
makes it useful to both humans and AI systems.

**Status:** deployed and functional; production-ready for single-resume
sessions (multi-resume sessions work, with one known cosmetic issue — see
[Current Status](#-current-status)). The [evaluation harness](backend/evaluation/README.md)
and [validation checks](#semantic-integrity-validation) are early and honest
about their scope. DSPy integration is experimental and off by default.

## ✨ Key Features

- **🤖 Provider-Agnostic LLM Extraction**: Support for Claude, OpenAI, and Ollama with automatic fallback
- **📊 SKOS-Compliant Knowledge Graph**: Uses ESCO skill taxonomy and schema.org vocabularies
- **📁 Session Management**: Upload multiple documents per session — entities deduplicate across resumes
- **🎨 Interactive Visualization**: Beautiful React + Vis.js network graphs with physics-based layout
- **📤 RDF Export**: Export as Turtle, RDF/XML, or JSON-LD formats
- **⚡ Real-Time Progress**: WebSocket streaming for live extraction updates
- **✏️ Editable Node Labels**: Click any graph node to correct its label, add notes, or mark it as verified. Edits are authoritative — future normalization runs treat verified labels as canonical.
- **🔄 DSPy Integration (Experimental)**: Optional DSPy route for structured extraction research (not production-validated)
- **☁️ Cloud-Ready**: Local-first design with abstraction layers for cloud deployment

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    RESUME EXPLORER                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐         ┌────────────────────┐       │
│  │  React Frontend │◄────────┤  Flask Backend     │       │
│  │  (Vis.js graph) │  HTTP   │  + WebSockets      │       │
│  └─────────────────┘  WS     └────────────────────┘       │
│         ▲                              │                    │
│         │                              ▼                    │
│         │                     ┌─────────────────┐          │
│         │                     │ LLM Extraction  │          │
│         │                     │ (Claude/OpenAI) │          │
│         │                     └─────────────────┘          │
│         │                              │                    │
│         │                              ▼                    │
│         │                     ┌─────────────────┐          │
│         │                     │ SKOS-Compliant  │          │
│         │                     │   Data Models   │          │
│         │                     └─────────────────┘          │
│         │                              │                    │
│         │                              ▼                    │
│         │                     ┌─────────────────┐          │
│         └─────────────────────┤  RDF Graph      │          │
│                               │  (rdflib)       │          │
│                               └─────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

**Tech Stack:**
- **Backend**: Python 3.10+, Flask, Flask-SocketIO, rdflib, NetworkX
- **Frontend**: React 18, Vite, Vis.js, Socket.IO
- **LLM**: Claude (Anthropic), OpenAI GPT, Ollama (local)
- **Semantic Web**: SKOS, ESCO skill taxonomy, schema.org


## ⚠️ DSPy Maturity Status

**Status (as of 2026-05-13): Experimental and not production-validated.**

- The DSPy extraction route exists and can be selected per request (`use_dspy=true`) or via `ENABLE_DSPY=true`.
- It is not fully tested across providers and concurrency scenarios in this deployed architecture.
- For production, set `ENABLE_DSPY=false` explicitly and only enable DSPy during focused testing.

See **[docs/DSPY_STATUS.md](docs/DSPY_STATUS.md)** for implemented-vs-tested details and a concrete validation checklist.

## 🚦 Quick Start

### Prerequisites

- **Python 3.10+** with pip
- **Node.js 18+** with npm
- **API Key** for Claude or OpenAI (or Ollama running locally)

### Installation

#### 1. Clone the repository

```bash
git clone <repo-url>
cd resume_explorer
```

#### 2. Set up backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### 3. Configure environment

Create a `.env` file in the `backend/` directory and add your API keys:

```bash
# Choose your LLM provider
LLM_PROVIDER=claude              # claude | openai | ollama

# Add your API key (only one needed)
CLAUDE_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
OLLAMA_BASE_URL=http://localhost:11434  # If using local Ollama

# Optional: override the extraction model per provider (defaults shown).
# The value must be one of the models listed for that provider in
# backend/resume_explorer/config/models.yaml (the curated "available models"
# list, with an `as_of` verification date). A model not in the list fails fast
# at startup with the valid options — instead of a silent 404 mid-extraction.
# To use a newer model, add it to models.yaml first. (Ollama accepts any local tag.)
CLAUDE_MODEL=claude-haiku-4-5     # default; e.g. claude-sonnet-4-6, claude-sonnet-5, claude-opus-4-8
OPENAI_MODEL=gpt-4.1-mini
OLLAMA_MODEL=llama3.1:8b

# Optional features
ENABLE_DSPY=false                # Keep false — DSPy has threading issues in this setup
SESSION_AUTO_SAVE=true
SESSION_MAX_DOCUMENTS=10

# Entity normalization
NORMALIZATION_PROVIDER=mock      # mock | ollama | anthropic | openai
OLLAMA_MODEL=llama3:latest       # Model for Ollama normalization (if using ollama)
NORMALIZE_SINGLE_RESUME=false    # true = run LLM alias resolution even for single-resume sessions
```

#### 4. Set up frontend

```bash
cd frontend
npm install
```

### Running the Application

You need to run both backend and frontend in separate terminals.

#### Terminal 1: Backend

```bash
cd backend
source venv/bin/activate
python -m resume_explorer.api.app
```

Backend will be available at by default: **http://localhost:5000**

or for a different port
```bash
python -c "from resume_explorer.api.app import run_app; run_app(port=5002)"
```

#### Terminal 2: Frontend

```bash
cd frontend
npm run dev
```

Frontend will be available at: **http://localhost:3000**

### First Use

1. Open **http://localhost:3000** in your browser
2. Click **"+ New Session"** to create a session
3. Drag and drop a resume file (PDF, DOCX, TXT, or MD)
4. Watch real-time extraction progress
5. Explore the interactive knowledge graph
6. Export as RDF (Turtle, RDF/XML, or JSON-LD)
7. Click **"▶ Analyze Graph"** in the sidebar to run 6 structural analyses (no LLM needed)
8. Switch to the **Insights** tab to read the findings, then **Generate Narratives** for LLM-synthesized career summaries

See [GETTING_STARTED.md](docs/GETTING_STARTED.md) for a detailed walkthrough.

## 📚 Documentation

- **[DSPy Status](docs/DSPY_STATUS.md)** - Canonical status page for DSPy maturity, test coverage gaps, and validation plan
- **[Getting Started](docs/GETTING_STARTED.md)** - Step-by-step tutorial
- **[API Reference](docs/API.md)** - REST API and WebSocket documentation
- **[SKOS Schema](docs/SKOS_SCHEMA.md)** - Vocabulary and ontology specification
- **[Implementation Plan](docs/IMPLEMENTATION_PLAN_2025-12-08.md)** - 6-phase development roadmap
- **[Frontend README](frontend/README.md)** - React app documentation
- **[Graph Analysis Pipeline](docs/GRAPH_ANALYSIS_PIPELINE.md)** - Why the offline analysis pipeline was built, what it reveals, and the 3-phase roadmap toward a graph-aware Digital Twin
- **[Post-Export Tools (Operational)](backend/tools/tools-README.md)** - How to run `entity_normalizer.py`, `graph_analyzer.py`, and `narrative_synthesizer.py`
- **[Evaluation Plan](docs/EVALUATION_PLAN.md)** - Precision/recall methodology, provider comparison matrix, multi-resume test scenarios
- **[April 2026 Engineering Log](docs/CHANGES_APRIL_2026.md)** - Multi-resume bug postmortem, editable nodes design rationale, what changed and why

## 🎯 Features in Detail

### Multi-Document Sessions

- Create named sessions to organize multiple resumes
- Upload multiple documents to the same session
- Automatic entity caching (no re-extraction)
- Session persistence across app restarts

### LLM Extraction

- **Streaming Progress**: Real-time WebSocket updates
- **Provider Agnostic**: Switch between Claude, OpenAI, or Ollama
- **Structured Output**: Automatic conversion to SKOS entities

### Knowledge Graph

- **SKOS-Compliant**: Uses W3C SKOS vocabulary
- **ESCO Integration**: Links skills to the European Skills/Competences taxonomy (v1.2.1). Skill hierarchy analysis uses the ESCO REST API at analysis time — no download required, results cached locally. ~50–60% of skills match; vendor-specific tools appear as "uncategorized," which is expected for modern stacks.
- **schema.org Types**: Person, JobPosting, Organization, etc.
- **Hierarchical Relationships**: broader/narrower/related concepts

### Interactive Visualization

- **Vis.js Network Graph**: Physics-based layout engine
- **Color-Coded Nodes**: Different colors for each entity type
- **Interactive Tooltips**: Hover for entity details
- **Click for Details**: Select nodes to view metadata
- **Legend**: Shows entity counts by type

### RDF Export

Export your knowledge graph in standard formats:
- **Turtle (.ttl)**: Human-readable RDF format
- **RDF/XML (.rdf)**: Standard XML-based RDF
- **JSON-LD (.jsonld)**: Web-friendly JSON format

All three formats contain the same complete semantic content as the
interactive graph — person, jobs, skills, education, certifications,
organizations, and their relationships — because the export, graph view,
stats, and analysis pipeline all share a single graph-building code path.

### Semantic Integrity Validation

A lightweight validator checks a session's graph for structural problems
before you trust or export it: dangling references, entities without SKOS
labels, near-duplicate skill labels that normalization missed, jobs with no
organization/dates, and entity types that were extracted but lost on the way
into the graph.

```bash
curl http://localhost:5000/api/sessions/<session-id>/graph/validate
```

The report separates **errors** (structurally wrong) from **warnings**
(suspicious but sometimes legitimate). It is not a full SHACL validation —
it's a pragmatic set of checks tuned to this schema. See
[`docs/API.md`](docs/API.md#validate-session-graph) for the check list and
response shape.

### Extraction Evaluation Harness (Lite)

`backend/evaluation/` contains a small, deterministic scaffold for measuring
extraction quality: sample resume fixtures, gold-label JSON, and a comparator
that reports per-entity-type precision/recall/F1 — offline, no API keys.
It measures *whatever extraction output you point it at*; it is not (yet) a
benchmark of the LLM extractors themselves. See
[`backend/evaluation/README.md`](backend/evaluation/README.md).

### Post-Export Analysis Pipeline

Once you've exported a graph, a separate offline pipeline turns the structural data into natural language insight documents — optimized for embedding in a vector database (ChromaDB) or reading directly.

```
Resume Explorer (export .jsonld)
    ↓
entity_normalizer.py    ← fix naming inconsistencies (GA4 vs Google Analytics 4)
    ↓
graph_analyzer.py       ← 6 structural analyses → 6 markdown insight files
  uses esco_lookup.py   ← ESCO REST API client (disk-cached, no auth required)
    ↓
narrative_synthesizer.py ← LLM cross-references all 6 → 2 career narrative docs
    ↓
embed into Digital Twin's ChromaDB  (future: embed_insights.py)
```

The 6 analyses cover: skill gap (claimed vs. used), career topology (bridge skills), technology evolution (chronological toolkit), SKOS hierarchy map, ESCO interoperability, and role progression. Each output is a natural language document written for RAG retrieval — not a data dump, but an analyst's briefing with semantic hooks for multiple query phrasings.

**Quick start (from `backend/` directory):**

```bash
python tools/entity_normalizer.py --input my-export.jsonld --output my-export-normalized.jsonld --provider anthropic
python tools/graph_analyzer.py    --input my-export-normalized.jsonld --output data/insights/
python tools/narrative_synthesizer.py --input data/insights/ --output data/insights/ --provider anthropic
```

See [`backend/tools/tools-README.md`](backend/tools/tools-README.md) for the full operational guide, and [`docs/GRAPH_ANALYSIS_PIPELINE.md`](docs/GRAPH_ANALYSIS_PIPELINE.md) for the architectural rationale and 3-phase roadmap.

## 📁 Project Structure

```
resume_explorer/
├── backend/
│   ├── resume_explorer/           # Main Python package
│   │   ├── models/                # SKOS-compliant data models
│   │   │   ├── base.py           # SKOSEntity base class
│   │   │   ├── person.py         # Person entity
│   │   │   ├── job.py            # Job entity
│   │   │   ├── skill.py          # Skill entity (ESCO)
│   │   │   ├── education.py      # Education entity
│   │   │   ├── certification.py  # Certification entity
│   │   │   └── organization.py   # Organization entity
│   │   ├── services/              # Business logic
│   │   │   ├── llm_client.py     # LLM abstraction layer
│   │   │   ├── extraction_dspy.py # DSPy extraction module
│   │   │   ├── resume_extractor.py # Main extractor
│   │   │   ├── entity_normalizer.py # Live in-session normalizer
│   │   │   └── pipeline_service.py # In-app analysis pipeline
│   │   ├── graph/                 # RDF and graph tools
│   │   │   ├── vocabularies.py   # SKOS/ESCO/schema.org
│   │   │   ├── rdf_graph_builder.py # RDF serialization
│   │   │   └── networkx_adapter.py # Vis.js format
│   │   ├── api/                   # Flask REST API
│   │   │   ├── app.py            # App factory
│   │   │   ├── routes.py         # API endpoints
│   │   │   ├── websocket.py      # WebSocket handlers
│   │   │   └── session_store.py  # Session persistence
│   │   └── utils/                 # Utilities
│   │       ├── logger.py
│   │       └── document_processor.py
│   ├── tools/                     # Post-export analysis pipeline (offline)
│   │   ├── tools-README.md       # Full operational guide
│   │   ├── entity_normalizer.py  # Fix naming inconsistencies (3-phase)
│   │   ├── graph_analyzer.py     # 6 structural analyses → markdown docs
│   │   └── narrative_synthesizer.py # LLM cross-reference synthesis
│   ├── data/
│   │   ├── sessions/             # Session storage
│   │   ├── exports/              # Exported JSON-LD files
│   │   └── insights/             # Graph analysis output
│   ├── tests/                     # Unit tests
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/            # React components
│   │   │   ├── SessionSelector.jsx
│   │   │   ├── ResumeUpload.jsx
│   │   │   ├── GraphVisualization.jsx
│   │   │   ├── EntityPanel.jsx
│   │   │   ├── ExportPanel.jsx
│   │   │   ├── AnalysisPipelinePanel.jsx  # Sidebar: Analyze + Generate buttons
│   │   │   ├── InsightsViewer.jsx         # Insights tab: 6 analysis docs
│   │   │   └── NarrativeViewer.jsx        # Narratives tab: Conservative + Exploratory
│   │   ├── services/              # API clients
│   │   │   ├── api.js
│   │   │   └── websocket.js
│   │   └── App.jsx                # Main app
│   ├── package.json
│   └── vite.config.js
│
├── docs/                          # Documentation
│   ├── GETTING_STARTED.md
│   ├── API.md
│   ├── SKOS_SCHEMA.md
│   └── IMPLEMENTATION_PLAN_2025-12-08.md
│
└── README.md                      # This file
```

## 🧪 Testing

Run backend tests:

```bash
cd backend
pytest tests/ -v
```

Test coverage includes:
- ✅ Data models (creation, JSON export, SKOS relationships)
- ✅ RDF serialization for all entity types (Person, Job, Skill, Education, Certification, Organization)
- ✅ RDF export completeness: all entity types and relationships survive Turtle / RDF/XML / JSON-LD round-trips (`test_session_graph.py`)
- ✅ Semantic integrity validator: clean and intentionally broken graphs (`test_graph_validator.py`)
- ✅ Multi-resume correctness: zero unknown nodes regression suite (`test_unknown_nodes.py`)
- ✅ Entity normalization pipeline: type-pool separation, alt_labels tracking, phase gating, `user_verified` anchor protection, LLM-phase variant merges via a fake client (no API calls)
- ✅ RDF graph builder: `skos:altLabel` triple generation, dedup cache behavior, multi-suffix org normalization, similarity job dedup
- ✅ Graph-analysis cache freshness: stale `graph.jsonld` rebuilt on document changes (`test_pipeline_cache.py`)
- ✅ LLM extraction pipeline
- ✅ Session persistence
- ✅ Evaluation harness comparator + fixture/batch suite (`test_evaluation_harness.py`, `test_eval_*.py`)
- ✅ API endpoint tests run against a temp-directory session store (no real data touched)
- ⏸️ Ground-truth evaluation tests (`test_evaluation.py`) skip until fixtures are authored — see `docs/EVALUATION_PLAN.md`

No test requires an API key or network access.

## 🔧 Configuration

Environment variables (`.env`):

```bash
# === LLM Provider ===
LLM_PROVIDER=claude              # claude | openai | ollama
CLAUDE_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_CHAT_MODEL=llama3.1:8b

# === Features ===
ENABLE_DSPY=false                # Keep false — DSPy has threading issues in this setup
ENABLE_MLFLOW=false              # Track experiments

# === Session Settings ===
SESSION_AUTO_SAVE=true
SESSION_MAX_DOCUMENTS=10         # Max documents per session
DATA_PATH=backend/data           # Storage location

# === Entity Normalization ===
NORMALIZATION_PROVIDER=mock      # mock | ollama | anthropic | openai
NORMALIZE_SINGLE_RESUME=false    # true = run LLM alias resolution for single-resume sessions too

# === RDF Export ===
DEFAULT_RDF_FORMAT=turtle        # turtle | rdfxml | jsonld

# === Deployment ===
CLOUD_MODE=false                 # Enable cloud features
STORAGE_BACKEND=local            # local | s3 | gcs
```

## 🌐 API Overview

The backend exposes a REST API with WebSocket support:

### REST Endpoints

**Session management:**
- `POST /api/sessions` - Create session
- `GET /api/sessions` - List all sessions
- `GET /api/sessions/:id` - Get session details
- `PUT /api/sessions/:id` - Update session
- `DELETE /api/sessions/:id` - Delete session
- `POST /api/sessions/:id/documents` - Upload document
- `GET /api/sessions/:id/graph` - Get Vis.js graph
- `GET /api/sessions/:id/export/:format` - Export RDF
- `GET /api/sessions/:id/graph/validate` - Semantic integrity validation report
- `GET /api/sessions/:id/stats` - Get statistics
- `PATCH /api/sessions/:id/entities/:type/:entity_id` - Update entity label/notes/verified status
- `GET /health` - Health check

**Analysis pipeline:**
- `POST /api/sessions/:id/pipeline/analyze` - Trigger graph analysis (Step 1)
- `POST /api/sessions/:id/pipeline/synthesize` - Generate career narratives (Step 2)
- `GET /api/sessions/:id/pipeline/status` - Check what's been computed
- `GET /api/sessions/:id/insights` - Fetch all 6 analysis documents
- `GET /api/sessions/:id/insights/:type` - Fetch a single analysis
- `GET /api/sessions/:id/narratives` - Fetch Conservative and Exploratory narratives

### WebSocket Events

**Extraction:**
- `extraction_started` - Extraction begins
- `extraction_progress` - Progress updates
- `entity_extracted` - Entity discovered
- `extraction_complete` - Finished
- `extraction_error` - Error occurred

**Analysis pipeline:**
- `pipeline_analysis_started` - Graph analysis triggered
- `pipeline_analysis_progress` - Analysis step progress
- `pipeline_analysis_complete` - All 6 insights written
- `pipeline_analysis_error` - Analysis failed
- `pipeline_synthesis_started` - Narrative generation triggered
- `pipeline_synthesis_progress` - Per-variant progress (conservative / exploratory)
- `pipeline_synthesis_complete` - Both narratives written
- `pipeline_synthesis_error` - Synthesis failed

See [API.md](docs/API.md) for complete documentation.

## 🤝 Contributing

Contributions are welcome! This project is experimental but ready for community input.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- Built on patterns from **ChronoScope** (timeline event extraction)
- LLM abstraction inspired by **montrose-marathon** (RAG with DSPy)
- **ESCO Skill Taxonomy**: [European Commission ESCO](https://esco.ec.europa.eu/)
- **SKOS**: [W3C SKOS Recommendation](https://www.w3.org/TR/skos-reference/)

## 📊 Project Metrics

- **Lines of Code**: ~12,000+
- **Python Files**: 30+
- **React Components**: 11
- **Test Coverage**: 80%+

## 📊 Current Status

### ✅ Production Ready (Single and Multi-Resume)

- ✅ Fast, accurate AI-powered extraction
- ✅ Beautiful interactive graph visualization
- ✅ Complete entity deduplication — no duplicates, no unknown nodes
- ✅ Multi-resume sessions: two versions of the same resume → 1 Person node, merged skills/jobs, zero unknown nodes
- ✅ Duplicate file detection: uploading the same file twice returns a clear error
- ✅ Reliable RDF export in multiple formats
- ✅ Fuzzy organization matching (iterative suffix stripping: "Acme Corp, Inc." = "Acme Corp")
- ✅ Local LLM support via Ollama (privacy-first, free)
- ✅ Skill alias resolution: variant names (e.g. "ML" / "machine learning") merged to a canonical label, preserved as `skos:altLabel` triples in the export
- ✅ Editable node labels: correct LLM extraction errors directly in the graph

## 🐛 Known Issues

### DSPy Threading Issues
**Symptom:** Extraction may fail with "dspy.settings.configure() can only be called from the same async task"

**Solution:** Set `ENABLE_DSPY=false` in `.env` (already the default)

**Status:** Known DSPy library issue with background threads — keep disabled

---

**Version**: 0.3.0
**Last Updated**: April 2026
