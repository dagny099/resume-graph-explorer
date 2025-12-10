/**
 * Session Selector Component
 *
 * Displays list of sessions and allows:
 * - Creating new sessions
 * - Selecting existing sessions
 * - Deleting sessions
 * - Renaming sessions
 */

import React, { useState, useEffect } from 'react';
import { listSessions, createSession, deleteSession, updateSession } from '../services/api';
import './SessionSelector.css';

const SessionSelector = ({ onSessionSelect, currentSessionId }) => {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNewDialog, setShowNewDialog] = useState(false);
  const [newSessionName, setNewSessionName] = useState('');
  const [editingSessionId, setEditingSessionId] = useState(null);
  const [editName, setEditName] = useState('');

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      setLoading(true);
      const data = await listSessions();
      setSessions(data.sessions);
    } catch (error) {
      console.error('Failed to load sessions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSession = async () => {
    if (!newSessionName.trim()) {
      return;
    }

    try {
      const data = await createSession(newSessionName);
      setSessions([data.session, ...sessions]);
      setShowNewDialog(false);
      setNewSessionName('');
      onSessionSelect(data.session.id);
    } catch (error) {
      console.error('Failed to create session:', error);
      alert('Failed to create session');
    }
  };

  const handleDeleteSession = async (sessionId, event) => {
    event.stopPropagation();

    if (!confirm('Are you sure you want to delete this session? This cannot be undone.')) {
      return;
    }

    try {
      await deleteSession(sessionId);
      setSessions(sessions.filter((s) => s.id !== sessionId));

      if (currentSessionId === sessionId) {
        onSessionSelect(null);
      }
    } catch (error) {
      console.error('Failed to delete session:', error);
      alert('Failed to delete session');
    }
  };

  const handleRenameSession = async (sessionId) => {
    if (!editName.trim()) {
      setEditingSessionId(null);
      return;
    }

    try {
      const data = await updateSession(sessionId, { name: editName });
      setSessions(sessions.map((s) => (s.id === sessionId ? data.session : s)));
      setEditingSessionId(null);
    } catch (error) {
      console.error('Failed to rename session:', error);
      alert('Failed to rename session');
    }
  };

  const startEditing = (session, event) => {
    event.stopPropagation();
    setEditingSessionId(session.id);
    setEditName(session.name);
  };

  const formatDate = (isoString) => {
    const date = new Date(isoString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  if (loading) {
    return <div className="session-selector loading">Loading sessions...</div>;
  }

  return (
    <div className="session-selector">
      <div className="session-header">
        <h2>My Sessions</h2>
        <button className="btn-new-session" onClick={() => setShowNewDialog(true)}>
          + New Session
        </button>
      </div>

      {showNewDialog && (
        <div className="new-session-dialog">
          <input
            type="text"
            placeholder="Session name"
            value={newSessionName}
            onChange={(e) => setNewSessionName(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleCreateSession()}
            autoFocus
          />
          <div className="dialog-buttons">
            <button className="btn-primary" onClick={handleCreateSession}>
              Create
            </button>
            <button className="btn-secondary" onClick={() => setShowNewDialog(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="session-list">
        {sessions.length === 0 ? (
          <div className="empty-state">
            <p>No sessions yet.</p>
            <p>Create a new session to get started!</p>
          </div>
        ) : (
          sessions.map((session) => (
            <div
              key={session.id}
              className={`session-item ${currentSessionId === session.id ? 'active' : ''}`}
              onClick={() => onSessionSelect(session.id)}
            >
              <div className="session-main">
                {editingSessionId === session.id ? (
                  <input
                    type="text"
                    className="session-name-edit"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleRenameSession(session.id)}
                    onBlur={() => handleRenameSession(session.id)}
                    autoFocus
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <div className="session-name" title={session.name}>
                    {session.name}
                  </div>
                )}

                <div className="session-meta">
                  <span className="session-docs">{session.document_count} documents</span>
                  <span className="session-date">{formatDate(session.updated_at)}</span>
                </div>
              </div>

              <div className="session-actions">
                <button
                  className="btn-icon"
                  onClick={(e) => startEditing(session, e)}
                  title="Rename"
                >
                  ✏️
                </button>
                <button
                  className="btn-icon btn-delete"
                  onClick={(e) => handleDeleteSession(session.id, e)}
                  title="Delete"
                >
                  🗑️
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default SessionSelector;
