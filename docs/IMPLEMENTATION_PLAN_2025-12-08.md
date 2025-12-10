# Resume Explorer - Implementation Plan
*Plan Date: December 8, 2025*
*Version: 1.0 - Initial architecture and development roadmap*

## Executive Summary

Build Resume Explorer as a new project that extracts core components from ChronoScope and montrose-marathon, adding:
1. **SKOS-compliant data models** with RDF export using hybrid vocabulary approach (ESCO + schema.org + custom)
2. **Provider-agnostic LLM architecture** supporting Claude, OpenAI, and Ollama with DSPy integration
3. **Flask + WebSocket backend** for real-time extraction streaming
4. **React + Vis.js frontend** for interactive knowledge graph visualization
5. **Session management** supporting multiple documents with cached extraction and persistence
6. **Cloud-ready design** with abstraction layers for future deployment

**Estimated Timeline**: 16-22 days for full-featured MVP

---

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Directory Structure](#directory-structure)
3. [Development Phases](#development-phases)
4. [Architectural Decisions](#architectural-decisions)
5. [Dependencies](#dependencies)
6. [Success Criteria](#success-criteria)

---

## Architecture Overview

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
│         │                     │ Provider-Agnostic          │
│         │                     │ LLM Backend     │          │
│         │                     │ (Claude/GPT/Ollama)        │
│         │                     └─────────────────┘          │
│         │                              │                    │
│         │                              ▼                    │
│         │                     ┌─────────────────┐          │
│         │                     │ SKOS-Compliant  │          │
│         │                     │   Data Models   │          │
│         │                     │ (ESCO + schema.org)        │
│         │                     └─────────────────┘          │
│         │                              │                    │
│         │                              ▼                    │
│         │                     ┌─────────────────┐          │
│         └─────────────────────┤  RDF Graph      │          │
│                               │  (rdflib)       │          │
│                               └─────────────────┘          │
│                                       │                     │
│                                       ▼                     │
│                               ┌─────────────────┐          │
│                               │ Session Storage │          │
│                               │ (RDF/TTL + JSON)│          │
│                               └─────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

**Key Architectural Patterns**:
- **Strategy Pattern**: Provider-agnostic LLM backends
- **Adapter Pattern**: DSPy integration, RDF → NetworkX conversion
- **Repository Pattern**: Session and entity persistence
- **Observer Pattern**: WebSocket event streaming
- **Factory Pattern**: LLM provider creation

---

## Directory Structure

```
resume_explorer/
├── backend/
│   ├── resume_explorer/                    # Main Python package
│   │   ├── __init__.py
│   │   ├── models/                         # SKOS-compliant data models
│   │   │   ├── __init__.py
│   │   │   ├── base.py                     # SKOSEntity base class
│   │   │   ├── person.py                   # schema:Person entity
│   │   │   ├── job.py                      # schema:JobPosting entity
│   │   │   ├── skill.py                    # esco:Skill entity
│   │   │   ├── education.py                # schema:EducationalOccupationalCredential
│   │   │   ├── certification.py            # Certification entity
│   │   │   ├── organization.py             # schema:Organization entity
│   │   │   ├── session.py                  # Session & Document models
│   │   │   └── datetime_manager.py         # [FROM CHRONOSCOPE] Date utilities
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── llm_client.py               # [FROM MONTROSE-MARATHON] LLM abstraction
│   │   │   ├── resume_extractor.py         # Resume-specific extraction logic
│   │   │   ├── extraction_dspy.py          # DSPy signatures and modules
│   │   │   ├── session_store.py            # Session persistence
│   │   │   └── storage.py                  # Storage abstraction (local/cloud)
│   │   ├── graph/
│   │   │   ├── __init__.py
│   │   │   ├── vocabularies.py             # SKOS, ESCO, schema.org namespaces
│   │   │   ├── rdf_graph_builder.py        # Build RDF graph from entities
│   │   │   └── networkx_adapter.py         # Convert RDF to Vis.js format
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── app.py                      # Flask app initialization
│   │   │   ├── routes.py                   # REST endpoints
│   │   │   └── websocket.py                # WebSocket handlers
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── logger.py                   # [FROM CHRONOSCOPE] Logging
│   │       └── config.py                   # Configuration management
│   ├── data/                               # Local data storage
│   │   └── sessions/                       # Session-based storage
│   │       ├── session-uuid-1/
│   │       │   ├── metadata.json
│   │       │   ├── documents/              # Uploaded files
│   │       │   ├── extracted/              # Cached entity extractions
│   │       │   ├── graph.ttl               # Combined RDF graph
│   │       │   └── graph.jsonld
│   │       └── sessions.index.json
│   ├── tests/
│   │   ├── test_models.py
│   │   ├── test_extraction.py
│   │   ├── test_rdf_graph.py
│   │   ├── test_session_store.py
│   │   └── test_api.py
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── Dockerfile                          # Cloud-ready containerization
│   └── README.md
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── GraphVisualization.jsx      # Vis.js graph component
│   │   │   ├── SessionSelector.jsx         # Session management UI
│   │   │   ├── ResumeUpload.jsx            # File upload with progress
│   │   │   ├── EntityPanel.jsx             # Display entity details
│   │   │   └── ExportPanel.jsx             # RDF/JSON export controls
│   │   ├── services/
│   │   │   ├── api.js                      # API client
│   │   │   └── websocket.js                # WebSocket client
│   │   ├── App.jsx
│   │   └── index.js
│   ├── package.json
│   └── README.md
│
├── docs/
│   ├── IMPLEMENTATION_PLAN_2025-12-08.md   # This document
│   ├── SKOS_SCHEMA.md                      # SKOS vocabulary documentation
│   ├── API.md                              # API documentation
│   └── ARCHITECTURE.md                     # Architecture decisions log
│
├── scripts/
│   ├── setup_dev.sh                        # Development environment setup
│   └── extract_dependencies.py             # Extract from ChronoScope/montrose-marathon
│
├── .env.example
├── .gitignore
├── CLAUDE.md                               # Agent instructions
└── README.md
```

---

## Development Phases

### Phase 1: Project Setup & LLM Abstraction (2-3 days)

**Objectives**:
- Initialize repository structure
- Extract LLM provider-agnostic architecture from montrose-marathon
- Extract datetime utilities from ChronoScope
- Set up cloud-ready storage abstraction
- Create session management foundations

**Tasks**:
1. **Repository Initialization**
   - Create directory structure
   - Initialize git repository on `dev` branch
   - Copy CLAUDE.md from current project
   - Create .env.example with API keys template
   - Set up .gitignore (Python + Node.js + data/)
   - Create Dockerfile for cloud readiness

2. **Extract from montrose-marathon**
   - Copy `LLMBackend` abstract class → `services/llm_client.py`
   - Copy `OllamaBackend` implementation
   - Implement `ClaudeBackend` (Anthropic API)
   - Implement `OpenAIBackend` (OpenAI API)
   - Copy `DSPyLMAdapter` for experimental pipelines
   - Copy `LenientChatAdapter` for small model support
   - Set up provider factory pattern

3. **Extract from ChronoScope**
   - Copy `datetime_manager.py` → `models/datetime_manager.py`
   - Copy `logger.py` → `utils/logger.py`

4. **Storage Abstraction Layer**
   - Create `LocalFileStore` class (filesystem-based)
   - Define `StorageBackend` interface (for future S3/GCS)
   - Create session directory structure

5. **Session Management Models**
   - Create `Session` dataclass (id, name, documents, metadata)
   - Create `Document` dataclass (id, session_id, filename, status)
   - Implement `SessionStore` with JSON persistence

**Dependencies** (`backend/requirements.txt`):
```txt
# Core Flask
flask>=3.0.0
flask-cors>=4.0.0
flask-socketio>=5.3.0
python-socketio>=5.10.0

# LLM Provider Abstraction (from montrose-marathon)
dspy-ai>=2.4.9
anthropic>=0.18.0
openai>=1.12.0
requests>=2.31.0              # For Ollama

# RDF & SKOS
rdflib>=7.0.0
rdflib-jsonld>=0.6.2

# Graph & Visualization
networkx>=3.2

# Document Processing
PyMuPDF>=1.23.0               # PDF extraction
pdfplumber>=0.10.0            # Fallback PDF
python-docx>=1.1.0            # Word documents

# Data & Utils
pydantic>=2.5.0               # Data validation
python-dateutil>=2.8.2
python-dotenv>=1.0.0

# Optional: Experiment tracking
mlflow>=2.10.0                # For comparing extraction quality
```

**Deliverables**:
- ✅ Working repository structure on `dev` branch
- ✅ Provider-agnostic LLM backend with 3 implementations
- ✅ DSPy integration ready
- ✅ Storage abstraction layer (local + cloud interface)
- ✅ Session management data models
- ✅ Dependencies installed and tested

---

### Phase 2: SKOS-Compliant Data Models with Hybrid Vocabulary (2-3 days)

**Objectives**:
- Design SKOS-compliant entity models using hybrid vocabulary
- Implement RDF serialization from the start
- Support ESCO skill taxonomy integration
- Enable hierarchical concept relationships

**Tasks**:
1. **Define Vocabulary Mappings** (`graph/vocabularies.py`)
   ```python
   from rdflib import Namespace

   # Standard vocabularies
   SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
   SCHEMA = Namespace("http://schema.org/")
   ESCO = Namespace("http://data.europa.eu/esco/")

   # Custom Resume Explorer namespace
   RE = Namespace("http://resumeexplorer.org/ontology#")
   RESUME = Namespace("http://resumeexplorer.org/resource/")
   ```

2. **Base SKOS Entity Class** (`models/base.py`)
   - Implement `SKOSEntity` dataclass
   - Methods: `get_uri()`, `to_rdf()`, `to_dict()`
   - Support for broader/narrower/related concepts
   - Confidence scoring and provenance tracking

3. **Specific Entity Models**:
   - **Person** (`models/person.py`) - Maps to `schema:Person`
   - **Job** (`models/job.py`) - Maps to `schema:JobPosting`
   - **Skill** (`models/skill.py`) - Maps to `esco:Skill`
   - **Education** (`models/education.py`) - Maps to `schema:EducationalOccupationalCredential`
   - **Certification** (`models/certification.py`) - Custom entity
   - **Organization** (`models/organization.py`) - Maps to `schema:Organization`

4. **ESCO Integration**
   - Create mapping dictionary for common skills → ESCO URIs
   - Implement ESCO skill hierarchy lookup
   - Document ESCO usage in `docs/SKOS_SCHEMA.md`

**Deliverables**:
- ✅ SKOSEntity base class with full RDF support
- ✅ 6 entity models (Person, Job, Skill, Education, Certification, Organization)
- ✅ All models support `to_dict()` and `to_rdf()`
- ✅ ESCO vocabulary integration
- ✅ Unit tests for model serialization
- ✅ Documentation: `docs/SKOS_SCHEMA.md`

---

### Phase 3: LLM Extraction with DSPy Signatures (3-4 days)

**Objectives**:
- Implement resume entity extraction using provider-agnostic LLM
- Create DSPy signatures for structured extraction
- Support streaming extraction via WebSocket
- Test with Claude, OpenAI, and Ollama

**Tasks**:
1. **Production Extraction Pipeline** (`services/resume_extractor.py`)
   - Simple prompt-based extraction
   - Parse JSON response into entity objects
   - WebSocket event emission (started, progress, complete)

2. **DSPy Signatures** (`services/extraction_dspy.py`)
   ```python
   class ExtractResumeEntities(dspy.Signature):
       """Extract structured entities from resume following SKOS schema."""
       resume_text: str = dspy.InputField()
       person: dict = dspy.OutputField(desc="schema:Person entity")
       jobs: list[dict] = dspy.OutputField(desc="List of schema:JobPosting")
       skills: list[dict] = dspy.OutputField(desc="List of esco:Skill with URIs")
       education: list[dict] = dspy.OutputField(desc="Education records")
       certifications: list[dict] = dspy.OutputField(desc="Certifications")
       reasoning: str = dspy.OutputField(desc="Extraction reasoning")
   ```

3. **DSPy Modules**
   - `ResumeExtractionModule` with ChainOfThought
   - Graceful fallback to production pipeline if DSPy fails
   - Integration with montrose-marathon's `LenientChatAdapter`

4. **WebSocket Integration** (`api/websocket.py`)
   - Flask-SocketIO setup
   - Event emitter class for extraction progress
   - Namespace: `/extraction`

5. **Multi-Provider Testing**
   - Test with Claude (primary)
   - Test with OpenAI (fallback)
   - Test with Ollama (local, privacy-first)
   - Compare extraction quality across providers

**Deliverables**:
- ✅ Production extraction pipeline
- ✅ DSPy-based experimental pipeline
- ✅ WebSocket streaming support
- ✅ Tested with 3 LLM providers
- ✅ Integration tests with sample resume

---

### Phase 4: RDF Graph Builder (2-3 days)

**Objectives**:
- Build SKOS-compliant RDF graph from extracted entities
- Support export to Turtle, RDF/XML, JSON-LD
- Convert RDF to Vis.js-compatible format

**Tasks**:
1. **RDF Graph Builder** (`graph/rdf_graph_builder.py`)
   - Namespace binding (SKOS, ESCO, schema.org, RE)
   - Entity-to-RDF conversion using `to_rdf()` methods
   - Relationship creation (WORKS_AT, HAS_SKILL, etc.)
   - Temporal property handling (start_date, end_date)

2. **Export Functionality**
   - `export_turtle()` → `.ttl` files
   - `export_rdfxml()` → `.rdf` files
   - `export_jsonld()` → `.jsonld` files

3. **NetworkX Adapter** (`graph/networkx_adapter.py`)
   - Convert RDF graph to Vis.js JSON format
   - Node creation with type-based styling
   - Edge creation with relationship labels
   - Deduplication logic

**Deliverables**:
- ✅ RDFGraphBuilder with full SKOS support
- ✅ Export to 3 RDF formats
- ✅ NetworkX → Vis.js adapter
- ✅ Unit tests for graph construction
- ✅ Validation against SKOS specification

---

### Phase 5: Flask API with Session Management (3-4 days)

**Objectives**:
- REST API for session and document management
- WebSocket streaming for real-time extraction
- Multi-document upload within sessions
- Combined graph generation from session documents

**Tasks**:
1. **Flask App Setup** (`api/app.py`)
   - CORS configuration for React frontend
   - Blueprint registration
   - WebSocket initialization

2. **Session Management Endpoints** (`api/routes.py`)
   - `GET /api/sessions` - List all sessions
   - `POST /api/sessions` - Create new session
   - `GET /api/sessions/<id>` - Get session details
   - `DELETE /api/sessions/<id>` - Delete session

3. **Document Management Endpoints**
   - `POST /api/sessions/<id>/documents` - Upload document to session
   - `GET /api/sessions/<id>/documents` - List session documents
   - `GET /api/sessions/<id>/documents/<doc_id>` - Get document details

4. **Graph Endpoints**
   - `GET /api/sessions/<id>/graph` - Get combined Vis.js graph
   - `GET /api/sessions/<id>/export/turtle` - Export session as .ttl
   - `GET /api/sessions/<id>/export/jsonld` - Export session as .jsonld

5. **Session Persistence** (`services/session_store.py`)
   - JSON-based session index
   - Per-session directory structure
   - Cached extraction results
   - Combined graph state

**Deliverables**:
- ✅ Flask REST API with 10+ endpoints
- ✅ WebSocket integration for extraction streaming
- ✅ Session CRUD operations
- ✅ Multi-document support
- ✅ Session export functionality
- ✅ API documentation: `docs/API.md`

---

### Phase 6: React Frontend with Session UI (4-5 days)

**Objectives**:
- Interactive session management interface
- Real-time extraction progress display
- Vis.js graph visualization
- Export controls

**Tasks**:
1. **Session Selector** (`components/SessionSelector.jsx`)
   - List all sessions
   - Create new session dialog
   - Select/load existing session
   - Delete session with confirmation

2. **Multi-Document Upload** (`components/ResumeUpload.jsx`)
   - Drag-and-drop file upload
   - Multiple file support within session
   - Real-time progress bars
   - WebSocket progress updates

3. **Graph Visualization** (`components/GraphVisualization.jsx`)
   - Vis.js network component
   - Type-based node coloring (Person, Job, Skill, etc.)
   - Interactive zoom/pan
   - Node click → entity details
   - Physics simulation for layout

4. **Entity Panel** (`components/EntityPanel.jsx`)
   - Display selected entity details
   - Show SKOS properties (broader, narrower, related)
   - Display confidence scores
   - Per-document provenance

5. **Export Panel** (`components/ExportPanel.jsx`)
   - Export session as Turtle
   - Export session as JSON-LD
   - Download combined graph
   - Copy RDF to clipboard

6. **Main App** (`App.jsx`)
   - Session state management
   - WebSocket connection lifecycle
   - Error handling and user feedback
   - Responsive layout

**Dependencies** (`frontend/package.json`):
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "vis-network": "^9.1.9",
    "axios": "^1.6.0",
    "socket.io-client": "^4.6.0"
  }
}
```

**Deliverables**:
- ✅ Working React app with session management
- ✅ Multi-document upload interface
- ✅ Interactive Vis.js graph visualization
- ✅ Real-time WebSocket updates
- ✅ Export controls for RDF formats
- ✅ Responsive design
- ✅ Component tests with React Testing Library

---

## Architectural Decisions

### 1. SKOS Vocabulary Strategy: Hybrid Approach

**Decision**: Combination of existing vocabularies + custom extensions

**Pros**:
- ✅ Interoperability with ESCO (EU skills taxonomy) and schema.org
- ✅ Semantic richness from established ontologies
- ✅ Flexibility for resume-specific concepts
- ✅ Community support (ESCO maintained by EU Commission)
- ✅ Future-proof (can add new mappings incrementally)

**Cons**:
- ⚠️ More complex initial setup (learning curve for multiple vocabularies)
- ⚠️ Potential namespace conflicts (mitigated by careful URI design)
- ⚠️ Maintenance overhead (tracking vocabulary updates)

**Recommended Mappings**:
- **SKOS Core** - Base concept scheme (`http://www.w3.org/2004/02/skos/core#`)
- **ESCO** - Skills taxonomy (`http://data.europa.eu/esco/`)
- **schema.org** - Person, Organization, EducationalOrganization
- **Custom RE namespace** - Resume-specific relationships (worksAt, hasCertification)

**Rationale**: Maximize interoperability while allowing project-specific extensions. Start with standards, extend only when necessary.

---

### 2. LLM Provider: Provider-Agnostic with DSPy

**Decision**: Implement provider-agnostic architecture based on montrose-marathon patterns

**Architecture**:
```python
# Abstract base class
class LLMBackend(ABC):
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

# Concrete implementations
class ClaudeBackend(LLMBackend): ...
class OpenAIBackend(LLMBackend): ...
class OllamaBackend(LLMBackend): ...

# DSPy adapter (shares backend with production)
class DSPyLMAdapter(dspy.LM):
    def __init__(self, backend: LLMBackend):
        self.backend = backend
```

**Key Benefits**:
- ✅ Swap providers via environment variable
- ✅ Single backend instance shared between production and DSPy
- ✅ Graceful fallback for local models
- ✅ Future-proof (easy to add new providers)

**Provider Priority**:
1. **Claude (Anthropic)** - Best for structured output, nuanced extraction
2. **GPT-4 (OpenAI)** - Excellent reliability, widely tested
3. **Ollama (local)** - Privacy-first, no API costs

**Configuration** (`.env`):
```bash
LLM_PROVIDER=claude  # claude | openai | ollama
CLAUDE_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
OLLAMA_BASE_URL=http://localhost:11434
ENABLE_DSPY=true
```

---

### 3. Hosting: Local-First with Cloud-Ready Design

**Initial Deployment**: Local only (filesystem storage, no external services)

**Future Cloud Deployment Path**: Abstraction layers for seamless migration

**Architectural Implications**:

| Component | Local Design | Cloud-Ready Adaptation |
|-----------|-------------|------------------------|
| **File Storage** | Local filesystem (`data/sessions/`) | `StorageBackend` interface → S3/GCS/Azure Blob |
| **Session Persistence** | JSON files | PostgreSQL/MongoDB |
| **Graph Storage** | RDF files + in-memory rdflib | Apache Jena Fuseki (triplestore) |
| **Authentication** | None (single user) | Flask-Login or OAuth |
| **WebSocket** | Flask-SocketIO (in-process) | Redis pub/sub for multi-instance |
| **API** | Single-process Flask | Docker + Cloud Run/ECS |
| **Frontend** | Serve from Flask static folder | Deploy to CDN (Netlify/Vercel) |

**Design Principles for Cloud Readiness**:
1. **Abstraction Layers**: `LocalFileStore` vs `S3FileStore` implement `StorageBackend`
2. **Environment-Driven Config**: All paths/URLs from environment variables
3. **Stateless API**: Session state in database, not server memory
4. **Containerization**: Dockerfile from day one
5. **Health Endpoints**: `/health` and `/ready` for orchestrators

**Timeline Impact**:
- ✅ No delay to MVP (local is simpler)
- ✅ Clean migration path (abstraction prevents refactoring)
- ⚠️ Extra planning upfront (+1-2 days in Phase 1)

---

### 4. Multi-Resume Sessions with Persistence

**Requirements**:
1. Upload multiple documents within a "session"
2. Sessions persist across browser restarts
3. Load/resume previous sessions
4. Cache extraction results to avoid re-processing

**Session Data Model**:
```python
@dataclass
class Session:
    id: str                        # UUID
    name: str                      # User-provided or auto-generated
    created_at: datetime
    updated_at: datetime
    documents: List[str]           # Document IDs
    graph_state: str               # Path to combined RDF file
    metadata: Dict                 # User notes, tags, etc.

@dataclass
class Document:
    id: str                        # UUID
    session_id: str                # Foreign key
    filename: str
    upload_date: datetime
    file_path: str                 # Original file location
    extracted_entities: Dict       # Cached extraction results
    status: str                    # "processing" | "complete" | "error"
```

**Storage Structure**:
```
data/sessions/
├── session-uuid-1/
│   ├── metadata.json              # Session info
│   ├── documents/
│   │   ├── doc-uuid-1.pdf
│   │   ├── doc-uuid-2.md
│   ├── extracted/
│   │   ├── doc-uuid-1.json        # Cached entities
│   │   ├── doc-uuid-2.json
│   ├── graph.ttl                  # Combined RDF graph
│   └── graph.jsonld
├── session-uuid-2/
│   └── ...
└── sessions.index.json            # Quick lookup
```

**Caching Strategy**:
- Entity extraction results cached to `extracted/doc-uuid.json`
- Graph rebuilt only when new document added
- WebSocket events emit progress per-document

**Timeline Impact**: +2-3 days across Phase 5 (API) and Phase 6 (Frontend)

---

## Dependencies

### Backend (`backend/requirements.txt`)
```txt
# Core Flask
flask>=3.0.0
flask-cors>=4.0.0
flask-socketio>=5.3.0
python-socketio>=5.10.0

# LLM Provider Abstraction (from montrose-marathon)
dspy-ai>=2.4.9
anthropic>=0.18.0
openai>=1.12.0
requests>=2.31.0              # For Ollama

# RDF & SKOS
rdflib>=7.0.0
rdflib-jsonld>=0.6.2

# Graph & Visualization
networkx>=3.2

# Document Processing
PyMuPDF>=1.23.0               # PDF extraction
pdfplumber>=0.10.0            # Fallback PDF
python-docx>=1.1.0            # Word documents

# Data & Utils
pydantic>=2.5.0               # Data validation
python-dateutil>=2.8.2
python-dotenv>=1.0.0

# Optional: Experiment tracking
mlflow>=2.10.0                # For comparing extraction quality
```

### Frontend (`frontend/package.json`)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "vis-network": "^9.1.9",
    "axios": "^1.6.0",
    "socket.io-client": "^4.6.0"
  }
}
```

### Environment Configuration (`.env.example`)
```bash
# LLM Provider Selection
LLM_PROVIDER=claude                    # claude | openai | ollama
CLAUDE_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_CHAT_MODEL=llama3.1:8b

# Feature Flags
ENABLE_DSPY=true
ENABLE_MLFLOW=false                    # Optional experiment tracking

# Deployment Mode
CLOUD_MODE=false                       # Set to true for cloud deployment
STORAGE_BACKEND=local                  # local | s3 | gcs

# Session Settings
SESSION_AUTO_SAVE=true
SESSION_MAX_DOCUMENTS=10               # Per session limit

# RDF Export
DEFAULT_RDF_FORMAT=turtle              # turtle | rdfxml | jsonld
```

---

## Success Criteria

### MVP (Local Deployment)
- [ ] Upload multiple resumes to a single session
- [ ] Extract entities using provider-agnostic LLM backend (Claude/OpenAI/Ollama)
- [ ] Switch between providers via environment variable
- [ ] Generate SKOS + ESCO compliant RDF graph
- [ ] Visualize combined graph in React with Vis.js
- [ ] Export session as Turtle/JSON-LD
- [ ] Load previous session on app restart
- [ ] Real-time extraction progress via WebSocket
- [ ] Test with sample resume (Barbara's resume)

### Future Enhancements
- [ ] Cloud deployment (containerized, S3 storage)
- [ ] DSPy optimization for extraction quality
- [ ] SPARQL query interface for advanced graph queries
- [ ] Session comparison (diff two sessions)
- [ ] ESCO skill taxonomy browser
- [ ] Career gap analysis
- [ ] Import from LinkedIn/Indeed APIs
- [ ] Neo4j optional backend for advanced queries

---

## Timeline

- **Phase 1**: 2-3 days (setup + LLM abstraction + storage interface)
- **Phase 2**: 2-3 days (SKOS models + ESCO integration)
- **Phase 3**: 3-4 days (LLM extraction + DSPy + multi-provider testing)
- **Phase 4**: 2-3 days (RDF graph builder)
- **Phase 5**: 3-4 days (Flask API + session management)
- **Phase 6**: 4-5 days (React frontend + session UI)

**Total**: 16-22 days for full-featured MVP (with sessions, multi-provider, cloud-ready)

---

## Critical Files to Extract

### From ChronoScope (`/Users/bhs/PROJECTS/chrono-scope/`)
1. `chrono_scope/models/datetime_manager.py` → `backend/resume_explorer/models/datetime_manager.py`
2. `chrono_scope/utils/logger.py` → `backend/resume_explorer/utils/logger.py`

### From montrose-marathon (`/Users/bhs/PROJECTS/montrose-marathon/`)
1. `llm_client.py` (LLMBackend, OllamaBackend, DSPyLMAdapter, LenientChatAdapter)
   - Extract to `backend/resume_explorer/services/llm_client.py`
   - Adapt to add ClaudeBackend and OpenAIBackend

---

## Next Steps

1. ✅ Plan approved and saved to `/docs/IMPLEMENTATION_PLAN_2025-12-08.md`
2. Initialize git repository on `dev` branch
3. Commit initial plan
4. Begin Phase 1: Project Setup & LLM Abstraction

---

*Plan Version 1.0 - December 8, 2025*
*Contributors: Human architect + Claude Sonnet 4.5*
