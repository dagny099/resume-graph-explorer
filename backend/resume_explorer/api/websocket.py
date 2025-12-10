"""
WebSocket Event Emitter

Handles real-time communication with frontend during extraction.
Uses Flask-SocketIO for WebSocket support.
"""

from flask_socketio import SocketIO, emit
from typing import Dict, Any, Optional
from ..utils.logger import logger


# Global SocketIO instance (initialized by Flask app)
socketio: Optional[SocketIO] = None


def init_socketio(app) -> SocketIO:
    """
    Initialize Flask-SocketIO with the Flask app.

    Args:
        app: Flask application instance

    Returns:
        Configured SocketIO instance
    """
    global socketio

    socketio = SocketIO(
        app,
        cors_allowed_origins="*",  # Allow all origins for development
        async_mode='threading',     # Use threading for compatibility
        logger=True,
        engineio_logger=False
    )

    logger.info("SocketIO initialized")
    return socketio


class ExtractionEventEmitter:
    """
    Event emitter for extraction progress.

    Sends WebSocket events to connected clients during resume extraction.
    """

    def __init__(self, namespace: str = '/extraction'):
        """
        Initialize event emitter.

        Args:
            namespace: WebSocket namespace (default: /extraction)
        """
        self.namespace = namespace

    def emit(self, event_name: str, data: Dict[str, Any]):
        """
        Emit event to all connected clients.

        Args:
            event_name: Event type (e.g., 'extraction_started')
            data: Event payload
        """
        if socketio is None:
            logger.warning("SocketIO not initialized, cannot emit event")
            return

        try:
            socketio.emit(
                event_name,
                data,
                namespace=self.namespace,
                broadcast=True
            )
            logger.debug(f"Emitted {event_name}: {data.get('document_id', 'N/A')}")
        except Exception as e:
            logger.error(f"Failed to emit event {event_name}: {e}")


# WebSocket event handlers
@socketio.on('connect', namespace='/extraction')
def handle_connect():
    """Handle client connection."""
    logger.info("Client connected to extraction stream")
    emit('connected', {
        'status': 'ready',
        'message': 'Connected to extraction stream'
    })


@socketio.on('disconnect', namespace='/extraction')
def handle_disconnect():
    """Handle client disconnection."""
    logger.info("Client disconnected from extraction stream")


@socketio.on('ping', namespace='/extraction')
def handle_ping(data):
    """Handle ping from client (keep-alive)."""
    emit('pong', {'timestamp': data.get('timestamp')})


# Progress tracking event handlers
@socketio.on('subscribe_document', namespace='/extraction')
def handle_subscribe_document(data):
    """
    Subscribe to updates for a specific document.

    Args:
        data: {'document_id': '...'}
    """
    document_id = data.get('document_id')
    logger.info(f"Client subscribed to document: {document_id}")

    emit('subscribed', {
        'document_id': document_id,
        'status': 'subscribed'
    })


@socketio.on('cancel_extraction', namespace='/extraction')
def handle_cancel_extraction(data):
    """
    Handle extraction cancellation request.

    Args:
        data: {'document_id': '...'}
    """
    document_id = data.get('document_id')
    logger.warning(f"Extraction cancellation requested for: {document_id}")

    # TODO: Implement cancellation logic in extractor
    emit('extraction_cancelled', {
        'document_id': document_id,
        'status': 'cancelled'
    })


# Session management event handlers
@socketio.on('join_session', namespace='/extraction')
def handle_join_session(data):
    """
    Join a specific session room for updates.

    Args:
        data: {'session_id': '...'}
    """
    from flask_socketio import join_room

    session_id = data.get('session_id')
    if session_id:
        join_room(session_id)
        logger.info(f"Client joined session room: {session_id}")

        emit('session_joined', {
            'session_id': session_id,
            'status': 'joined'
        })


@socketio.on('leave_session', namespace='/extraction')
def handle_leave_session(data):
    """
    Leave a session room.

    Args:
        data: {'session_id': '...'}
    """
    from flask_socketio import leave_room

    session_id = data.get('session_id')
    if session_id:
        leave_room(session_id)
        logger.info(f"Client left session room: {session_id}")

        emit('session_left', {
            'session_id': session_id,
            'status': 'left'
        })


def emit_to_session(session_id: str, event_name: str, data: Dict[str, Any]):
    """
    Emit event to all clients in a specific session room.

    Args:
        session_id: Session identifier
        event_name: Event type
        data: Event payload
    """
    if socketio is None:
        logger.warning("SocketIO not initialized, cannot emit to session")
        return

    try:
        socketio.emit(
            event_name,
            data,
            namespace='/extraction',
            room=session_id
        )
        logger.debug(f"Emitted {event_name} to session {session_id}")
    except Exception as e:
        logger.error(f"Failed to emit to session {session_id}: {e}")


__all__ = [
    'socketio',
    'init_socketio',
    'ExtractionEventEmitter',
    'emit_to_session'
]
