/**
 * WebSocket Client for Real-time Extraction Progress
 *
 * Connects to Flask-SocketIO backend for:
 * - Extraction progress updates
 * - Real-time status changes
 * - Session-scoped events
 */

import { io } from 'socket.io-client';

const WS_URL = import.meta.env.VITE_WS_URL || 'http://localhost:5000';

class WebSocketClient {
  constructor() {
    this.socket = null;
    this.handlers = {};
    this.connected = false;
  }

  connect() {
    if (this.socket) {
      return this.socket;
    }

    // Connect to /extraction namespace to match backend
    this.socket = io(`${WS_URL}/extraction`, {
      path: '/socket.io',
      transports: ['websocket', 'polling'],
    });

    // Connection handlers
    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      this.connected = true;

      // Join extraction namespace
      this.socket.emit('ping', { timestamp: Date.now() });
    });

    this.socket.on('disconnect', () => {
      console.log('WebSocket disconnected');
      this.connected = false;
    });

    this.socket.on('connected', (data) => {
      console.log('Connected to extraction stream:', data);
    });

    this.socket.on('pong', (data) => {
      console.log('Pong received:', data);
    });

    // Extraction event handlers
    this.socket.on('extraction_started', (data) => {
      this._emit('extraction_started', data);
    });

    this.socket.on('extraction_progress', (data) => {
      this._emit('extraction_progress', data);
    });

    this.socket.on('entity_extracted', (data) => {
      this._emit('entity_extracted', data);
    });

    this.socket.on('extraction_complete', (data) => {
      this._emit('extraction_complete', data);
    });

    this.socket.on('extraction_error', (data) => {
      this._emit('extraction_error', data);
    });

    return this.socket;
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.connected = false;
    }
  }

  on(event, handler) {
    if (!this.handlers[event]) {
      this.handlers[event] = [];
    }
    this.handlers[event].push(handler);
  }

  off(event, handler) {
    if (this.handlers[event]) {
      this.handlers[event] = this.handlers[event].filter((h) => h !== handler);
    }
  }

  _emit(event, data) {
    if (this.handlers[event]) {
      this.handlers[event].forEach((handler) => handler(data));
    }
  }

  joinSession(sessionId) {
    if (this.socket && this.connected) {
      this.socket.emit('join_session', { session_id: sessionId });
    }
  }

  leaveSession(sessionId) {
    if (this.socket && this.connected) {
      this.socket.emit('leave_session', { session_id: sessionId });
    }
  }

  subscribeDocument(documentId) {
    if (this.socket && this.connected) {
      this.socket.emit('subscribe_document', { document_id: documentId });
    }
  }

  cancelExtraction(documentId) {
    if (this.socket && this.connected) {
      this.socket.emit('cancel_extraction', { document_id: documentId });
    }
  }
}

// Singleton instance
const wsClient = new WebSocketClient();

export default wsClient;

// Hook for React components
export const useWebSocket = (sessionId) => {
  const [isConnected, setIsConnected] = React.useState(wsClient.connected);

  React.useEffect(() => {
    wsClient.connect();

    const handleConnect = () => setIsConnected(true);
    const handleDisconnect = () => setIsConnected(false);

    wsClient.on('connect', handleConnect);
    wsClient.on('disconnect', handleDisconnect);

    if (sessionId) {
      wsClient.joinSession(sessionId);
    }

    return () => {
      wsClient.off('connect', handleConnect);
      wsClient.off('disconnect', handleDisconnect);

      if (sessionId) {
        wsClient.leaveSession(sessionId);
      }
    };
  }, [sessionId]);

  return {
    isConnected,
    on: wsClient.on.bind(wsClient),
    off: wsClient.off.bind(wsClient),
    subscribeDocument: wsClient.subscribeDocument.bind(wsClient),
    cancelExtraction: wsClient.cancelExtraction.bind(wsClient),
  };
};
