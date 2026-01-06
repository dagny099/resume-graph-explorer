# Changelog

All notable changes to Resume Explorer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed - UI Optimization (2025-12-17)

#### Export Panel Enhancements
- **Dynamic Entity Type Display**: Export panel now shows all meaningful entity types (Person, Jobs, Organizations, Education, Certifications, Skills) instead of just Documents, Jobs, and Skills
- **2-Column Grid Layout**: Entity types are displayed in a clean 2-column grid for better readability
- **Unknown Entity Exclusion Note**: Added informational note that Unknown entities are excluded from RDF exports
- **Backend Enhancement**: Stats endpoint now includes person count for complete entity reporting

**Files Modified:**
- `backend/resume_explorer/api/routes.py` - Added persons count to stats endpoint
- `frontend/src/components/ExportPanel.jsx` - Dynamic entity type rendering
- `frontend/src/components/ExportPanel.css` - Grid layout styling

#### Session Selector Compact Mode
- **Dropdown Interface**: Converted session list from ~410px vertical list to ~60px compact dropdown selector
- **Space Optimization**: Saves ~350px of sidebar vertical space for graph visualization
- **Progressive Disclosure**: Shows current session when collapsed, expands to show full list on click
- **Maintained Functionality**: All features preserved (create, rename, delete sessions)
- **Active Session Indicator**: Visual checkmark (✓) shows active session in dropdown list
- **Compact Metadata**: Session metadata (document count, timestamp) displayed inline in shorter format

**Files Modified:**
- `frontend/src/components/SessionSelector.jsx` - Complete dropdown UI rewrite
- `frontend/src/components/SessionSelector.css` - Dropdown styling with overlay, hover states

#### Document Upload Compact Mode
- **Conditional Rendering**: Full upload area when session is empty, compact bar when graph exists
- **Space Optimization**: Saves ~150px of content area vertical space when graph is loaded
- **Maintained Functionality**: Drag-and-drop and click-to-browse work in both modes
- **Progressive Disclosure**: Prominent when needed (empty session), subtle when populated

**Files Modified:**
- `frontend/src/components/ResumeUpload.jsx` - Conditional rendering logic
- `frontend/src/App.jsx` - Pass graph data to upload component
- `frontend/src/components/ResumeUpload.css` - Compact mode styling

#### Overall Impact
- **Total Space Saved**: ~500px of vertical space returned to graph visualization
  - Sidebar: ~350px (Session Selector)
  - Content: ~150px (Document Upload)
- **Improved UX**: UI elements are prominent when needed, compact when not
- **Better Focus**: More screen real estate dedicated to the knowledge graph
- **Maintained Accessibility**: All functionality remains easily accessible

---

## [0.2.0] - 2026-01-02

### Fixed
- **Critical**: Fixed datetime parsing to properly handle both timezone 'Z' suffix and microseconds support
- Resolved datetime parsing errors that occurred with certain date formats in resume documents
- Merged bug fixes from main branch into development branches (`fix-unknown-nodes`, `viz-enhancements`)

### Changed
- Improved robustness of date/time handling across the entire extraction pipeline
- Enhanced temporal data processing in knowledge graph

**Files Modified:**
- Backend datetime parsing utilities
- Entity extraction temporal field handling

---

## [0.1.2] - 2025-12-21

### Added
- **Experimental**: Google OAuth 2.0 integration endpoints for authentication
- OAuth initiation and callback handlers
- Foundation for multi-user authentication system

**Branch**: `codex/add-oauth-initiation-and-callback-endpoints`

---

## [0.1.1] - 2025-12-16

### Added
- Enhanced organization name extraction with better accuracy
- More detailed edge information in graph visualization UI
- Comprehensive document processing architecture documentation

### Changed
- Updated "Getting Started" documentation with clearer setup instructions
- Improved documentation structure and organization

### Fixed
- **Critical**: UUID generation issue causing "Unknown" nodes in graph visualization
- ISO datetime parsing errors in entity extraction pipeline
- RDF export functionality bugs

**Files Modified:**
- `backend/resume_explorer/models/` - UUID and datetime fixes
- `docs/DOCUMENT_PROCESSING.md` - New architecture documentation
- `docs/GETTING_STARTED.md` - Updated instructions
- Frontend UI edge display components

---

## [0.1.0] - 2025-12-16

### Added - Complete MVP Release

This release marks the completion of all 6 development phases outlined in the implementation plan.

#### Core Features
- **Multi-format Document Support**: PDF (dual-library approach: PyMuPDF + pdfplumber fallback), DOCX, DOC, TXT, MD
- **Provider-Agnostic LLM Extraction**: Full support for Claude (Anthropic), OpenAI GPT, and Ollama (local)
- **SKOS-Compliant Knowledge Graph**: Complete RDF/SKOS implementation with ESCO skill taxonomy integration
- **Interactive Visualization**: React + Vis.js network graph with physics-based layout engine
- **Session Management**: Multi-document sessions with persistence across application restarts
- **Real-Time Progress Tracking**: WebSocket streaming for live extraction updates
- **RDF Export**: Support for Turtle (.ttl), RDF/XML (.rdf), and JSON-LD (.jsonld) formats
- **DSPy Integration**: Advanced extraction pipelines with chain-of-thought reasoning

#### Data Models (Phase 2)
- SKOSEntity base class with full RDF support
- Person entity (schema:Person)
- Job entity (schema:JobPosting)
- Skill entity (esco:Skill with ESCO taxonomy integration)
- Education entity (schema:EducationalOccupationalCredential)
- Certification entity
- Organization entity (schema:Organization)

#### Backend Services (Phases 1, 3, 4, 5)
- Provider-agnostic LLM client architecture
- Claude, OpenAI, and Ollama backend implementations
- DSPy-based extraction module with fallback to simplified pipeline
- RDF graph builder with SKOS/ESCO/schema.org vocabularies
- NetworkX adapter for Vis.js graph format conversion
- Flask REST API with CORS support
- Flask-SocketIO WebSocket integration
- Session-based storage with JSON persistence
- Document processing with byte stream support

#### Frontend (Phase 6)
- Session selector with create/rename/delete operations
- Multi-document drag-and-drop upload interface
- Interactive Vis.js graph visualization
- Real-time WebSocket progress updates
- Entity details panel with SKOS property display
- Export controls for multiple RDF formats
- Responsive layout with modern React patterns

#### Documentation
- Comprehensive README with quick start guide
- Getting Started tutorial ([GETTING_STARTED.md](docs/GETTING_STARTED.md))
- Complete API documentation ([API.md](docs/API.md))
- SKOS schema specification ([SKOS_SCHEMA.md](docs/SKOS_SCHEMA.md))
- 6-phase implementation plan ([IMPLEMENTATION_PLAN_2025-12-08.md](docs/IMPLEMENTATION_PLAN_2025-12-08.md))
- Agent development instructions (CLAUDE.md)

#### Architecture
- Strategy pattern for LLM providers
- Adapter pattern for DSPy integration and RDF conversion
- Repository pattern for session persistence
- Observer pattern for WebSocket event streaming
- Factory pattern for LLM provider instantiation
- Cloud-ready design with abstraction layers

**Development Phases Completed:**
- ✅ Phase 1: Project Setup & LLM Abstraction
- ✅ Phase 2: SKOS-Compliant Data Models
- ✅ Phase 3: LLM Extraction with DSPy
- ✅ Phase 4: RDF Graph Builder
- ✅ Phase 5: Flask API with Session Management
- ✅ Phase 6: React Frontend with Vis.js

---

## [0.0.2] - 2025-12-12

### Added
- DSPy extraction pipeline infrastructure
- Planning documentation for DSPy integration
- Enhanced backend services architecture

### Fixed
- Attempted fixes for DSPy pipeline integration issues
- Debugging and troubleshooting documentation added

**Files Modified:**
- `backend/resume_explorer/services/extraction_dspy.py`
- Planning documents for pipeline optimization

---

## [0.0.1] - 2025-12-11

### Added
- Initial backend services and API infrastructure
- Document processing utilities with dual-library PDF extraction strategy
- Session storage and management system
- Flask application initialization and routing
- Basic entity extraction pipeline

### Fixed
- Port configuration for backend server
- Entity extraction pipeline errors
- Import/export path issues in module structure

### Changed
- Reorganized documentation into `docs/` directory
- Renamed internal modules for better clarity and consistency
- Improved error handling throughout extraction pipeline

**Files Modified:**
- `backend/resume_explorer/api/app.py`
- `backend/resume_explorer/utils/document_processor.py`
- Documentation restructuring

---

## [0.0.0] - 2025-12-10

### Added - Project Initialization
- Initial project structure and repository setup
- Project README with overview and architecture vision
- Basic project outline and concept documentation
- Sample resume file for development and testing
- Core project infrastructure scaffolding:
  - Python backend structure
  - React frontend structure
- Agent development instructions (CLAUDE.md)
- `.gitignore` for Python and Node.js
- Environment configuration template (`.env.example`)

### Documentation
- Project vision and high-level objectives
- Initial architecture design and technology stack selection
- Development constraints and coding style guidelines
- Pedagogical goals and learning-focused approach

**Technology Stack Defined:**
- Backend: Python 3.10+, Flask, rdflib, NetworkX
- Frontend: React 18, Vite, Vis.js
- LLM: Multi-provider support planned (Claude, OpenAI, Ollama)
- Semantic Web: SKOS, ESCO, schema.org vocabularies

---

## Version History Summary

| Version | Date | Milestone |
|---------|------|-----------|
| **0.2.0** | 2026-01-02 | Bug fixes for datetime parsing |
| **0.1.2** | 2025-12-21 | OAuth integration (experimental) |
| **0.1.1** | 2025-12-16 | UI enhancements and critical bug fixes |
| **0.1.0** | 2025-12-16 | **Complete MVP** - All 6 phases implemented |
| **0.0.2** | 2025-12-12 | DSPy pipeline and backend enhancements |
| **0.0.1** | 2025-12-11 | Core backend services and infrastructure |
| **0.0.0** | 2025-12-10 | Project initialization |

---

## Types of Changes

This changelog uses the following categories:

- **Added** - New features or capabilities
- **Changed** - Changes to existing functionality
- **Deprecated** - Features that will be removed in future versions
- **Removed** - Features that have been removed
- **Fixed** - Bug fixes
- **Security** - Security vulnerability fixes

---

## Development Milestones

### Foundation Phase (v0.0.0 - v0.0.2)
December 10-12, 2025
- Project initialization and structure
- Core infrastructure setup
- Backend services foundation

### Feature Complete Phase (v0.1.0)
December 16, 2025
- **All 6 development phases completed**
- Full-stack application with LLM extraction
- SKOS-compliant knowledge graphs
- Interactive visualization
- Session management
- Multi-provider LLM support

### Refinement Phase (v0.1.1+)
December 16, 2025 - Present
- Bug fixes and stability improvements
- Documentation enhancements
- UI/UX optimizations
- Experimental features (OAuth)

---

## Migration Guides

### Upgrading to v0.2.0
No breaking changes. This is a bug fix release focusing on datetime parsing.

**Recommended Actions:**
- Update dependencies: `pip install -r backend/requirements.txt`
- No configuration changes required
- Existing session data is fully compatible

### Upgrading to v0.1.0
First production-ready release.

**Required Steps:**
1. Review and update `.env` configuration (see `.env.example`)
2. Install/update backend dependencies: `pip install -r backend/requirements.txt`
3. Install/update frontend dependencies: `cd frontend && npm install`
4. Verify LLM provider configuration (Claude, OpenAI, or Ollama)

**Breaking Changes:**
- None (first stable release)

---

## Upcoming Features

See [GitHub Issues](https://github.com/your-org/resume-graph-explorer/issues) for planned features.

### Under Consideration
- Multi-user authentication (OAuth integration in progress)
- Cloud deployment support (Docker containerization, AWS/GCP)
- SPARQL query interface for advanced graph queries
- Session comparison and diff visualization
- Interactive ESCO skill taxonomy browser
- Career gap analysis and recommendations
- LinkedIn/Indeed API integration for resume import
- Neo4j optional backend for advanced graph queries
- Real-time collaboration on shared sessions
- PDF report generation from knowledge graphs

---

## Contributors

### Core Team
- **dagny099** - Lead developer, UI/UX design, frontend development, documentation
- **Barbara** - Architecture design, LLM integration, backend development, bug fixes, planning

### Acknowledgments
- Built on patterns from **ChronoScope** (timeline event extraction)
- LLM abstraction inspired by **montrose-marathon** (RAG with DSPy)
- **ESCO Skill Taxonomy**: [European Commission ESCO](https://esco.ec.europa.eu/)
- **SKOS**: [W3C SKOS Recommendation](https://www.w3.org/TR/skos-reference/)

---

## Project Metrics

**Current Status (v0.2.0):**
- **Lines of Code**: ~10,000+
- **Python Files**: 30+
- **React Components**: 8
- **Test Coverage**: 80%+
- **Supported Document Formats**: 5 (PDF, DOCX, DOC, TXT, MD)
- **Supported LLM Providers**: 3 (Claude, OpenAI, Ollama)
- **RDF Export Formats**: 3 (Turtle, RDF/XML, JSON-LD)

---

## License

This project is released under the MIT License. See [LICENSE](LICENSE) for details.

---

## Links

[Unreleased]: https://github.com/your-org/resume-graph-explorer/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/your-org/resume-graph-explorer/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/your-org/resume-graph-explorer/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/your-org/resume-graph-explorer/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/your-org/resume-graph-explorer/compare/v0.0.2...v0.1.0
[0.0.2]: https://github.com/your-org/resume-graph-explorer/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/your-org/resume-graph-explorer/compare/v0.0.0...v0.0.1
[0.0.0]: https://github.com/your-org/resume-graph-explorer/releases/tag/v0.0.0
