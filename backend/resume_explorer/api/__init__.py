"""
Resume Explorer API Module

Exports Flask app factory, WebSocket components, and session storage.
"""

from .websocket import socketio, init_socketio, ExtractionEventEmitter, emit_to_session
from .session_store import Session, Document, SessionStore
from .app import create_app, run_app
from .routes import api_bp

__all__ = [
    # WebSocket
    'socketio',
    'init_socketio',
    'ExtractionEventEmitter',
    'emit_to_session',

    # Session storage
    'Session',
    'Document',
    'SessionStore',

    # Flask app
    'create_app',
    'run_app',
    'api_bp'
]
