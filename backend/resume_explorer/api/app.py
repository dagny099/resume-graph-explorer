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
from .google_services import GoogleDriveClient, GoogleOAuthService, TokenStore


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

        # LLM configuration
        LLM_PROVIDER=os.getenv('LLM_PROVIDER', 'claude'),
        ENABLE_DSPY=os.getenv('ENABLE_DSPY', 'true').lower() == 'true',

        # Session configuration
        SESSION_AUTO_SAVE=os.getenv('SESSION_AUTO_SAVE', 'true').lower() == 'true',
        SESSION_MAX_DOCUMENTS=int(os.getenv('SESSION_MAX_DOCUMENTS', '10')),

        # RDF export
        DEFAULT_RDF_FORMAT=os.getenv('DEFAULT_RDF_FORMAT', 'turtle'),

        # Google OAuth
        GOOGLE_CLIENT_ID=os.getenv('GOOGLE_CLIENT_ID', 'demo-google-client-id'),
        GOOGLE_CLIENT_SECRET=os.getenv('GOOGLE_CLIENT_SECRET', 'demo-google-client-secret'),
        GOOGLE_REDIRECT_URI=os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:5000/api/google/callback'),
        GOOGLE_SCOPES=os.getenv('GOOGLE_SCOPES', 'https://www.googleapis.com/auth/drive.readonly'),

        # Data storage path
        DATA_PATH=os.getenv('DATA_PATH', 'data'),
    )

    # Override with provided config
    if config:
        app.config.update(config)

    # Enable CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type"]
        }
    })

    # Initialize WebSocket
    socketio = init_socketio(app)

    # Initialize session store
    session_store = SessionStore(base_path=app.config['DATA_PATH'])
    app.session_store = session_store

    # Initialize token store and Google services
    token_store = TokenStore(base_path=app.config['DATA_PATH'])
    app.token_store = token_store

    try:
        app.google_oauth_service = GoogleOAuthService(
            client_id=app.config['GOOGLE_CLIENT_ID'],
            client_secret=app.config['GOOGLE_CLIENT_SECRET'],
            redirect_uri=app.config['GOOGLE_REDIRECT_URI'],
            scopes=app.config['GOOGLE_SCOPES'],
            token_store=token_store,
        )
        app.google_drive_client = GoogleDriveClient(token_store=token_store)
    except Exception as exc:
        logger.warning(f"Google OAuth initialization failed: {exc}")
        app.google_oauth_service = None
        app.google_drive_client = None

    # Initialize LLM client
    try:
        llm_client = create_llm_client(
            provider=app.config['LLM_PROVIDER']
        )
        app.llm_client = llm_client
        logger.info(f"LLM client initialized: {app.config['LLM_PROVIDER']}")
    except Exception as e:
        logger.warning(f"LLM client initialization failed: {e}")
        app.llm_client = None

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
    run_app()
