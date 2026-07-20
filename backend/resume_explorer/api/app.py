"""
Flask Application Factory

Creates and configures the Resume Explorer Flask app with:
- REST API endpoints
- WebSocket support
- CORS configuration
- Error handling
"""

import os
from flask import Flask
from flask_cors import CORS

from .websocket import init_socketio
from .session_store import SessionStore
from ..services import create_llm_client
from ..utils.logger import logger


def create_app(config: dict = None) -> Flask:
    """
    Create and configure Flask application.

    Args:
        config: Optional configuration dictionary

    Returns:
        Configured Flask app
    """
    app = Flask(__name__)

    # Load configuration
    app.config.from_mapping(
        SECRET_KEY=os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production'),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max upload
        UPLOAD_FOLDER='data/sessions',
        DATA_PATH=os.getenv('DATA_PATH', 'data'),

        # LLM configuration
        LLM_PROVIDER=os.getenv('LLM_PROVIDER', 'claude'),
        # DSPy extraction is experimental and has known threading issues in
        # deployment — it must be opted into explicitly via ENABLE_DSPY=true.
        ENABLE_DSPY=os.getenv('ENABLE_DSPY', 'false').lower() == 'true',

        # Entity normalization configuration
        NORMALIZATION_PROVIDER=os.getenv('NORMALIZATION_PROVIDER', 'mock'),

        # Session configuration
        SESSION_AUTO_SAVE=os.getenv('SESSION_AUTO_SAVE', 'true').lower() == 'true',
        SESSION_MAX_DOCUMENTS=int(os.getenv('SESSION_MAX_DOCUMENTS', '10')),

        # RDF export
        DEFAULT_RDF_FORMAT=os.getenv('DEFAULT_RDF_FORMAT', 'turtle'),
    )

    # Override with provided config
    if config:
        app.config.update(config)

    # Enable CORS for all routes.
    # CORS_ORIGINS env var lets you restrict to specific domains in production
    # (e.g. "https://resume-graph-explorer.vercel.app"). Defaults to "*" so the
    # public demo works without additional configuration.
    allowed_origins = os.getenv('CORS_ORIGINS', '*')
    CORS(app, origins=allowed_origins)

    # ============================================
    # PRODUCTION: Serve frontend static files
    # ============================================
    from flask import send_from_directory

    # Path to built frontend (dist folder)
    frontend_dist = os.path.join(
        os.path.dirname(__file__),
        '../../../frontend/dist'
    )

    # Only serve static files if dist folder exists
    if os.path.exists(frontend_dist):
        @app.route('/', defaults={'path': ''})
        @app.route('/<path:path>')
        def serve_frontend(path):
            """Serve frontend static files or index.html for SPA routing"""
            # Unknown API paths must return JSON 404, not the SPA shell —
            # otherwise API clients get HTML with a misleading 200 status.
            if path.startswith('api/'):
                return {'error': f"Unknown API endpoint: /{path}"}, 404
            if path and os.path.exists(os.path.join(frontend_dist, path)):
                return send_from_directory(frontend_dist, path)
            return send_from_directory(frontend_dist, 'index.html')

        logger.info(f"Serving frontend static files from: {frontend_dist}")
    else:
        logger.warning(f"Frontend dist folder not found at: {frontend_dist}")
    # ============================================

    # Initialize WebSocket
    socketio = init_socketio(app)

    # Initialize session store — honors config['DATA_PATH'] so tests can
    # point the store at a temp directory instead of the real data dir
    session_store = SessionStore(base_path=app.config['DATA_PATH'])
    app.session_store = session_store

    # Initialize LLM client. validate=True resolves the model from
    # <PROVIDER>_MODEL / the registry default and checks it against the curated
    # allow-list in config/models.yaml, so a wrong/retired model surfaces here
    # with the valid options instead of a silent 404 during extraction.
    try:
        llm_client = create_llm_client(
            provider=app.config['LLM_PROVIDER'],
            validate=True,
        )
        app.llm_client = llm_client
        logger.info(
            f"LLM client initialized: {app.config['LLM_PROVIDER']} "
            f"(model={llm_client.backend.model_name})"
        )
    except Exception as e:
        logger.warning(f"LLM client initialization failed: {e}")
        app.llm_client = None

    # Initialize pipeline service (wraps offline graph analysis tools)
    from ..services.pipeline_service import PipelineService
    app.pipeline_service = PipelineService(
        session_store=session_store,
        data_path=app.config['DATA_PATH'],
        llm_client=app.llm_client,
    )
    logger.info("Pipeline service initialized")

    # Register blueprints
    from .routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Not found'}, 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal error: {error}")
        return {'error': 'Internal server error'}, 500

    @app.errorhandler(413)
    def too_large(error):
        return {'error': 'File too large (max 16MB)'}, 413

    # Health check endpoint
    @app.route('/health')
    def health():
        return {
            'status': 'healthy',
            'llm_available': app.llm_client is not None if hasattr(app, 'llm_client') else False,
            'sessions': session_store.get_stats() if hasattr(app, 'session_store') else {}
        }

    logger.info("Flask app created")
    return app


def run_app(host='0.0.0.0', port=5000, debug=True):
    """
    Run the Flask application with WebSocket support.

    Args:
        host: Host to bind to
        port: Port to bind to
        debug: Enable debug mode
    """
    from .websocket import socketio

    app = create_app()

    logger.info(f"Starting Resume Explorer API on {host}:{port}")
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)


__all__ = ['create_app', 'run_app']


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Resume Explorer API Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to (default: 5000)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')

    args = parser.parse_args()

    run_app(host=args.host, port=args.port, debug=args.debug)
