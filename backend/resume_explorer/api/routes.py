"""
Resume Explorer REST API Routes

Endpoints for:
- Session management (CRUD)
- Document upload and extraction
- Graph retrieval and export
- Entity queries
"""

from flask import Blueprint, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename
import os
from pathlib import Path
import threading

from .session_store import SessionStore
from .websocket import ExtractionEventEmitter, emit_to_session
from ..services import ResumeExtractor, EntityNormalizer
from ..utils import DocumentProcessor, logger
from ..graph import RDFGraphBuilder, NetworkXAdapter
from ..models import Person, Job, Skill, Education, Certification, Organization


api_bp = Blueprint('api', __name__)


# ============================================================================
# Session Management Endpoints
# ============================================================================

@api_bp.route('/sessions', methods=['GET'])
def list_sessions():
    """Get all sessions."""
    session_store: SessionStore = current_app.session_store

    sessions = session_store.list_sessions()

    return jsonify({
        'sessions': [
            {
                'id': s.id,
                'name': s.name,
                'created_at': s.created_at.isoformat(),
                'updated_at': s.updated_at.isoformat(),
                'document_count': len(s.documents),
                'metadata': s.metadata
            }
            for s in sessions
        ],
        'total': len(sessions)
    })


@api_bp.route('/sessions', methods=['POST'])
def create_session():
    """Create new session."""
    session_store: SessionStore = current_app.session_store

    data = request.get_json() or {}
    name = data.get('name')

    session = session_store.create_session(name=name)

    return jsonify({
        'session': session.to_dict(),
        'message': 'Session created successfully'
    }), 201


@api_bp.route('/sessions/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get session details."""
    session_store: SessionStore = current_app.session_store

    session = session_store.get_session(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404

    # Get documents
    documents = session_store.get_session_documents(session_id)

    return jsonify({
        'session': session.to_dict(),
        'documents': [d.to_dict() for d in documents]
    })


@api_bp.route('/sessions/<session_id>', methods=['PUT'])
def update_session(session_id):
    """Update session properties."""
    session_store: SessionStore = current_app.session_store

    data = request.get_json() or {}

    session = session_store.update_session(session_id, **data)
    if not session:
        return jsonify({'error': 'Session not found'}), 404

    return jsonify({
        'session': session.to_dict(),
        'message': 'Session updated successfully'
    })


@api_bp.route('/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete session and all its data."""
    session_store: SessionStore = current_app.session_store

    success = session_store.delete_session(session_id)
    if not success:
        return jsonify({'error': 'Session not found'}), 404

    return jsonify({
        'message': 'Session deleted successfully'
    })


# ============================================================================
# Document Upload and Extraction Endpoints
# ============================================================================

@api_bp.route('/sessions/<session_id>/documents', methods=['POST'])
def upload_document(session_id):
    """Upload document to session and trigger extraction.

    Query parameters:
        use_dspy: 'true' or 'false' to override default extraction method
    """
    session_store: SessionStore = current_app.session_store

    # Check session exists
    session = session_store.get_session(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404

    # Check file
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Check session document limit
    if len(session.documents) >= current_app.config['SESSION_MAX_DOCUMENTS']:
        return jsonify({
            'error': f"Session document limit reached ({current_app.config['SESSION_MAX_DOCUMENTS']})"
        }), 400

    # Secure filename
    filename = secure_filename(file.filename)

    # Check file extension
    allowed_extensions = {'.pdf', '.docx', '.doc', '.txt', '.md'}
    file_ext = Path(filename).suffix.lower()
    if file_ext not in allowed_extensions:
        return jsonify({
            'error': f'Unsupported file type. Allowed: {", ".join(allowed_extensions)}'
        }), 400

    # Get extraction method preference (query param overrides config default)
    use_dspy_param = request.args.get('use_dspy', '').lower()
    if use_dspy_param in ('true', '1', 'yes'):
        use_dspy = True
    elif use_dspy_param in ('false', '0', 'no'):
        use_dspy = False
    else:
        # Use config default if parameter not provided or invalid
        use_dspy = current_app.config['ENABLE_DSPY']

    # Save document to session
    file_bytes = file.read()
    document = session_store.add_document(session_id, filename, file_bytes)

    if not document:
        return jsonify({'error': 'Failed to add document to session'}), 500

    # Start extraction in background thread
    # Capture app instance before thread starts
    app = current_app._get_current_object()

    def extract_async():
        with app.app_context():
            _run_extraction(session_id, document.id, filename, file_bytes, use_dspy)

    thread = threading.Thread(target=extract_async, daemon=True)
    thread.start()

    extraction_method = "DSPy" if use_dspy else "SimplifiedExtractor"
    return jsonify({
        'document': document.to_dict(),
        'message': f'Document uploaded, extraction started using {extraction_method}'
    }), 201


def _run_extraction(session_id: str, document_id: str, filename: str, file_bytes: bytes, use_dspy: bool = None):
    """Run extraction in background thread.

    Args:
        session_id: Session ID
        document_id: Document ID
        filename: Original filename
        file_bytes: File content as bytes
        use_dspy: Whether to use DSPy (overrides config if provided)
    """
    session_store: SessionStore = current_app.session_store

    try:
        # Update status to processing
        session_store.update_document_status(document_id, 'processing')

        # Extract text from document
        logger.info(f"Extracting text from {filename}")
        resume_text = DocumentProcessor.extract_text_from_bytes(file_bytes, filename)

        # Create LLM client and extractor
        llm_client = current_app.llm_client
        if not llm_client:
            raise ValueError("LLM client not initialized")

        # Use provided parameter or fall back to config
        if use_dspy is None:
            use_dspy = current_app.config['ENABLE_DSPY']

        event_emitter = ExtractionEventEmitter()
        extractor = ResumeExtractor(
            llm_client=llm_client,
            event_emitter=event_emitter.emit,
            use_dspy=use_dspy
        )

        extraction_method = "DSPy" if use_dspy else "SimplifiedExtractor"
        logger.info(f"Extracting entities from {filename} using {extraction_method}")

        # Extract entities
        entities = extractor.extract_entities(
            resume_text=resume_text,
            filename=filename,
            session_id=session_id
        )

        # Save extracted entities
        session_store.save_extracted_entities(document_id, entities)

        # Update status to complete
        session_store.update_document_status(document_id, 'complete')

        logger.info(f"Extraction complete for document {document_id}")

        # Run entity normalization if session has 2+ completed documents
        _maybe_normalize_session_entities(session_id)

    except Exception as e:
        logger.error(f"Extraction failed for document {document_id}: {e}", exc_info=True)
        session_store.update_document_status(document_id, 'error', str(e))


def _maybe_normalize_session_entities(session_id: str):
    """
    Check if session has 2+ completed documents and run normalization if so.

    This automatically deduplicates entity names across multiple resume documents
    to ensure consistent naming (e.g., "Python" vs "python", "GA4" vs "Google Analytics 4").
    """
    try:
        session_store: SessionStore = current_app.session_store

        # Get all documents in session
        documents = session_store.get_session_documents(session_id)
        completed_docs = [d for d in documents if d.status == 'complete']

        if not completed_docs:
            logger.warning(f"No completed documents found for session {session_id}")
            return

        # Tiered normalization gate:
        #   Phase 1 (deterministic) + Phase 2 (ESCO) always run — they are cheap,
        #   correct URL-encoded labels, and fix obvious case variants.
        #   Phase 3 (LLM semantic) only runs for multi-resume sessions OR when
        #   NORMALIZE_SINGLE_RESUME=true is set in config (opt-in for single-resume
        #   sessions where you want alias resolution at ingestion time).
        is_multi_doc = len(completed_docs) >= 2
        run_llm_phase = is_multi_doc or current_app.config.get('NORMALIZE_SINGLE_RESUME', False)

        logger.info(
            f"Starting entity normalization for session {session_id} "
            f"({len(completed_docs)} documents, llm_phase={run_llm_phase})"
        )

        # Collect all entities from completed documents
        all_entities = []
        for doc in completed_docs:
            entities = session_store.load_extracted_entities(doc.id)
            if entities:
                all_entities.append(entities)

        if not all_entities:
            logger.warning(f"No entities found for session {session_id}")
            return

        # Get normalization provider from config
        normalization_provider = current_app.config.get('NORMALIZATION_PROVIDER', 'mock')

        # Create normalizer with appropriate LLM client
        if normalization_provider == 'mock':
            llm_client = None
        elif normalization_provider == current_app.config.get('LLM_PROVIDER', 'claude'):
            # Use existing LLM client if providers match
            llm_client = current_app.llm_client
        else:
            # Create separate LLM client for normalization if provider differs
            from ..services import create_llm_client
            try:
                # Build provider-specific kwargs
                client_kwargs = {}
                if normalization_provider == 'ollama':
                    ollama_model = current_app.config.get('OLLAMA_MODEL', 'llama3:latest')
                    client_kwargs['model'] = ollama_model
                    logger.info(f"Creating Ollama client with model: {ollama_model}")

                llm_client = create_llm_client(provider=normalization_provider, **client_kwargs)
                logger.info(f"Created separate LLM client for normalization: {normalization_provider}")
            except Exception as e:
                logger.warning(f"Failed to create {normalization_provider} client for normalization: {e}")
                logger.warning("Falling back to mock normalization")
                normalization_provider = 'mock'
                llm_client = None

        normalizer = EntityNormalizer(provider=normalization_provider, llm_client=llm_client)

        # Run normalization
        result = normalizer.normalize_session_entities(all_entities, run_llm_phase=run_llm_phase)
        normalized_entities = result["normalized_entities"]
        label_map = result["label_map"]
        report = result["report"]

        # Log normalization results
        merges = report["summary"]["total_merges"]
        if merges > 0:
            logger.info(
                f"Normalization found {merges} entity name merges. "
                f"{report['summary']['original_labels']} labels → "
                f"{report['summary']['final_unique_labels']} unique labels"
            )
        else:
            logger.info("Normalization found no duplicates - all entity names are already unique")

        # Update all documents with normalized entities
        for i, doc in enumerate(completed_docs):
            if i < len(normalized_entities):
                session_store.save_extracted_entities(doc.id, normalized_entities[i])
                logger.info(f"Updated document {doc.id} with normalized entities")

        logger.info(f"Entity normalization complete for session {session_id}")

    except Exception as e:
        logger.error(f"Entity normalization failed for session {session_id}: {e}", exc_info=True)
        # Don't fail the extraction if normalization fails - just log and continue


@api_bp.route('/documents/<document_id>', methods=['GET'])
def get_document(document_id):
    """Get document details."""
    session_store: SessionStore = current_app.session_store

    document = session_store.get_document(document_id)
    if not document:
        return jsonify({'error': 'Document not found'}), 404

    return jsonify({'document': document.to_dict()})


@api_bp.route('/documents/<document_id>/entities', methods=['GET'])
def get_document_entities(document_id):
    """Get extracted entities for a document."""
    session_store: SessionStore = current_app.session_store

    document = session_store.get_document(document_id)
    if not document:
        return jsonify({'error': 'Document not found'}), 404

    entities = session_store.load_extracted_entities(document_id)
    if not entities:
        return jsonify({'error': 'No extracted entities found'}), 404

    return jsonify({'entities': entities})


# ============================================================================
# Graph Retrieval and Export Endpoints
# ============================================================================

@api_bp.route('/sessions/<session_id>/graph', methods=['GET'])
def get_session_graph(session_id):
    """Get combined graph for all documents in session (Vis.js format)."""
    session_store: SessionStore = current_app.session_store

    session = session_store.get_session(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404

    # Get all documents
    documents = session_store.get_session_documents(session_id)

    # Filter complete documents
    complete_docs = [d for d in documents if d.status == 'complete']

    if not complete_docs:
        return jsonify({
            'error': 'No completed extractions in this session',
            'total_documents': len(documents),
            'complete_documents': 0
        }), 404

    # Build combined graph
    builder = RDFGraphBuilder()

    all_persons = []
    all_jobs = []
    all_skills = []
    all_education = []
    all_certifications = []
    all_organizations = []

    for doc in complete_docs:
        entities = session_store.load_extracted_entities(doc.id)
        if not entities:
            continue

        # Collect entities
        person = entities.get('person')
        if person and isinstance(person, dict):
            all_persons.append(Person.from_dict(person))

        jobs = entities.get('jobs', [])
        all_jobs.extend([Job.from_dict(j) if isinstance(j, dict) else j for j in jobs])

        skills = entities.get('skills', [])
        all_skills.extend([Skill.from_dict(s) if isinstance(s, dict) else s for s in skills])

        education = entities.get('education', [])
        all_education.extend([Education.from_dict(e) if isinstance(e, dict) else e for e in education])

        certifications = entities.get('certifications', [])
        all_certifications.extend([Certification.from_dict(c) if isinstance(c, dict) else c for c in certifications])

        organizations = entities.get('organizations', [])
        all_organizations.extend([Organization.from_dict(o) if isinstance(o, dict) else o for o in organizations])

    # Use first person (or create placeholder)
    person = all_persons[0] if all_persons else Person(name="Unknown")

    # Build RDF graph
    builder.build_from_entities(
        person=person,
        jobs=all_jobs,
        skills=all_skills,
        education=all_education,
        certifications=all_certifications,
        organizations=all_organizations
    )

    # Convert to Vis.js format
    adapter = NetworkXAdapter(builder.graph)
    graph_data = adapter.convert()

    return jsonify(graph_data)


@api_bp.route('/sessions/<session_id>/export/<format>', methods=['GET'])
def export_session_graph(session_id, format):
    """Export session graph as RDF file."""
    session_store: SessionStore = current_app.session_store

    session = session_store.get_session(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404

    # Validate format
    if format not in ['turtle', 'rdfxml', 'jsonld']:
        return jsonify({'error': 'Invalid format. Use: turtle, rdfxml, or jsonld'}), 400

    # Build graph (same logic as get_session_graph)
    documents = session_store.get_session_documents(session_id)
    complete_docs = [d for d in documents if d.status == 'complete']

    if not complete_docs:
        return jsonify({'error': 'No completed extractions in this session'}), 404

    builder = RDFGraphBuilder()

    # Collect and build entities (abbreviated for brevity)
    for doc in complete_docs:
        entities = session_store.load_extracted_entities(doc.id)
        if not entities:
            continue

        person = entities.get('person')
        if person:
            if isinstance(person, dict):
                person = Person.from_dict(person)
            builder.add_person(person)

        for job in entities.get('jobs', []):
            if isinstance(job, dict):
                job = Job.from_dict(job)
            builder.add_job(job)

        for skill in entities.get('skills', []):
            if isinstance(skill, dict):
                skill = Skill.from_dict(skill)
            builder.add_skill(skill)

    # Export graph
    graph_path = session_store.get_session_graph_path(session_id, format)

    if format == 'turtle':
        builder.export_turtle(str(graph_path))
    elif format == 'rdfxml':
        builder.export_rdfxml(str(graph_path))
    elif format == 'jsonld':
        builder.export_jsonld(str(graph_path))

    # Send file
    return send_file(
        str(graph_path),
        as_attachment=True,
        download_name=f"{session.name.replace(' ', '_')}.{graph_path.suffix}"
    )


@api_bp.route('/sessions/<session_id>/stats', methods=['GET'])
def get_session_stats(session_id):
    """Get statistics for session graph (deduplicated counts from RDF graph)."""
    session_store: SessionStore = current_app.session_store

    session = session_store.get_session(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404

    documents = session_store.get_session_documents(session_id)
    complete_docs = [d for d in documents if d.status == 'complete']

    stats = {
        'session_id': session_id,
        'session_name': session.name,
        'total_documents': len(documents),
        'documents_by_status': {},
        'total_entities': {
            'jobs': 0,
            'skills': 0,
            'education': 0,
            'certifications': 0,
            'organizations': 0,
            'persons': 0
        }
    }

    # Count documents by status
    for doc in documents:
        status = doc.status
        stats['documents_by_status'][status] = stats['documents_by_status'].get(status, 0) + 1

    # Count entities from deduplicated graph (not raw storage)
    if complete_docs:
        # Build graph with deduplication (same logic as get_session_graph)
        builder = RDFGraphBuilder()

        all_persons = []
        all_jobs = []
        all_skills = []
        all_education = []
        all_certifications = []
        all_organizations = []

        for doc in complete_docs:
            entities = session_store.load_extracted_entities(doc.id)
            if not entities:
                continue

            person = entities.get('person')
            if person and isinstance(person, dict):
                all_persons.append(Person.from_dict(person))

            jobs = entities.get('jobs', [])
            all_jobs.extend([Job.from_dict(j) if isinstance(j, dict) else j for j in jobs])

            skills = entities.get('skills', [])
            all_skills.extend([Skill.from_dict(s) if isinstance(s, dict) else s for s in skills])

            education = entities.get('education', [])
            all_education.extend([Education.from_dict(e) if isinstance(e, dict) else e for e in education])

            certifications = entities.get('certifications', [])
            all_certifications.extend([Certification.from_dict(c) if isinstance(c, dict) else c for c in certifications])

            organizations = entities.get('organizations', [])
            all_organizations.extend([Organization.from_dict(o) if isinstance(o, dict) else o for o in organizations])

        # Build graph (deduplication happens here)
        person = all_persons[0] if all_persons else Person(name="Unknown")
        for org in all_organizations:
            builder.add_organization(org)
        for skill in all_skills:
            builder.add_skill(skill)
        for job in all_jobs:
            builder.add_job(job)
        for edu in all_education:
            builder.add_education(edu)
        for cert in all_certifications:
            builder.add_certification(cert)

        # Get deduplicated counts from graph
        graph_stats = builder.get_graph_stats()
        entity_counts = graph_stats['entity_counts']

        # Expose person name for filename generation
        stats['person_name'] = person.name if person.name and person.name != 'Unknown' else None

        # Map field names to match frontend expectations (plural forms)
        stats['total_entities'] = {
            'persons': entity_counts.get('person', 0),
            'jobs': entity_counts.get('job', 0),
            'skills': entity_counts.get('skill', 0),
            'education': entity_counts.get('education', 0),
            'certifications': entity_counts.get('certification', 0),
            'organizations': entity_counts.get('organization', 0)
        }

    return jsonify(stats)


# ============================================================================
# Storage Statistics
# ============================================================================

@api_bp.route('/stats', methods=['GET'])
def get_storage_stats():
    """Get overall storage statistics."""
    session_store: SessionStore = current_app.session_store

    return jsonify(session_store.get_stats())


# ============================================================================
# Analysis Pipeline Endpoints
# ============================================================================

VALID_ANALYSIS_TYPES = {
    'skill_gap', 'career_topology', 'tech_evolution',
    'hierarchy_map', 'esco_coverage', 'role_progression',
}


def _run_analysis_in_background(session_id: str, normalize: bool, app):
    """Run graph analysis in a background thread (mirrors _run_extraction pattern)."""
    def _task():
        with app.app_context():
            emit_fn = lambda event, data: emit_to_session(session_id, event, data)
            try:
                app.pipeline_service.run_analysis(session_id, normalize, emit_fn)
            except Exception as e:
                logger.error(f"Background analysis failed for {session_id}: {e}")

    threading.Thread(target=_task, daemon=True).start()


def _run_synthesis_in_background(session_id: str, provider: str, model, app):
    """Run narrative synthesis in a background thread."""
    def _task():
        with app.app_context():
            emit_fn = lambda event, data: emit_to_session(session_id, event, data)
            try:
                app.pipeline_service.run_synthesis(session_id, provider, model, emit_fn)
            except Exception as e:
                logger.error(f"Background synthesis failed for {session_id}: {e}")

    threading.Thread(target=_task, daemon=True).start()


@api_bp.route('/sessions/<session_id>/pipeline/analyze', methods=['POST'])
def run_pipeline_analyze(session_id):
    """
    Trigger graph analysis for a session.

    Body (JSON, all optional):
        normalize (bool): Run deterministic entity normalization first. Default false.

    Returns 202 immediately; progress is streamed via WebSocket.
    """
    session_store: SessionStore = current_app.session_store

    session = session_store.get_session(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404

    documents = session_store.get_session_documents(session_id)
    complete_docs = [d for d in documents if d.status == 'complete']
    if not complete_docs:
        return jsonify({'error': 'No completed extractions in this session'}), 409

    data = request.get_json() or {}
    normalize = bool(data.get('normalize', False))

    app = current_app._get_current_object()
    _run_analysis_in_background(session_id, normalize, app)

    return jsonify({
        'message': 'Analysis started',
        'session_id': session_id,
        'normalize': normalize,
    }), 202


@api_bp.route('/sessions/<session_id>/pipeline/synthesize', methods=['POST'])
def run_pipeline_synthesize(session_id):
    """
    Trigger narrative synthesis for a session.

    Requires graph analysis (Step 1) to have been run first.

    Body (JSON, all optional):
        provider (str): 'anthropic' or 'openai'. Default 'anthropic'.
        model (str):    Model override. Default is provider default.

    Returns 202 immediately; progress is streamed via WebSocket.
    """
    session_store: SessionStore = current_app.session_store

    session = session_store.get_session(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404

    # Verify insights exist before accepting the request
    status = current_app.pipeline_service.get_pipeline_status(session_id)
    if status['insights_available'] == 0:
        return jsonify({
            'error': 'No insights found. Run graph analysis first.',
            'hint': 'POST /sessions/{id}/pipeline/analyze',
        }), 400

    data = request.get_json() or {}
    provider = data.get('provider', 'anthropic')
    model = data.get('model', None)

    if provider not in ('anthropic', 'openai'):
        return jsonify({'error': "provider must be 'anthropic' or 'openai'"}), 400

    app = current_app._get_current_object()
    _run_synthesis_in_background(session_id, provider, model, app)

    return jsonify({
        'message': 'Narrative synthesis started',
        'session_id': session_id,
        'provider': provider,
    }), 202


@api_bp.route('/sessions/<session_id>/pipeline/status', methods=['GET'])
def get_pipeline_status(session_id):
    """Return pipeline status: which insights and narratives are available."""
    session_store: SessionStore = current_app.session_store

    if not session_store.get_session(session_id):
        return jsonify({'error': 'Session not found'}), 404

    status = current_app.pipeline_service.get_pipeline_status(session_id)
    return jsonify(status)


@api_bp.route('/sessions/<session_id>/insights', methods=['GET'])
def get_insights(session_id):
    """Return all 6 analysis documents with content (null if not yet run)."""
    session_store: SessionStore = current_app.session_store

    if not session_store.get_session(session_id):
        return jsonify({'error': 'Session not found'}), 404

    return jsonify(current_app.pipeline_service.get_insights(session_id))


@api_bp.route('/sessions/<session_id>/insights/<analysis_type>', methods=['GET'])
def get_insight(session_id, analysis_type):
    """Return a specific analysis document by type."""
    session_store: SessionStore = current_app.session_store

    if not session_store.get_session(session_id):
        return jsonify({'error': 'Session not found'}), 404

    if analysis_type not in VALID_ANALYSIS_TYPES:
        return jsonify({
            'error': f"Invalid analysis type '{analysis_type}'",
            'valid': sorted(VALID_ANALYSIS_TYPES),
        }), 400

    insights = current_app.pipeline_service.get_insights(session_id)
    for analysis in insights['analyses']:
        if analysis['type'] == analysis_type:
            if not analysis['available']:
                return jsonify({
                    'error': 'Analysis not yet run',
                    'hint': f"POST /sessions/{session_id}/pipeline/analyze",
                }), 404
            return jsonify(analysis)

    return jsonify({'error': 'Analysis not found'}), 404


@api_bp.route('/sessions/<session_id>/narratives', methods=['GET'])
def get_narratives(session_id):
    """Return conservative and exploratory narratives (null if not yet run)."""
    session_store: SessionStore = current_app.session_store

    if not session_store.get_session(session_id):
        return jsonify({'error': 'Session not found'}), 404

    return jsonify(current_app.pipeline_service.get_narratives(session_id))


__all__ = ['api_bp']
