/**
 * Session Selector Component
 *
 * Displays list of sessions and allows:
 * - Creating new sessions
 * - Selecting existing sessions
 * - Deleting sessions
 * - Renaming sessions
 */

import React, { useState, useEffect, useRef } from 'react';
import { listSessions, createSession, deleteSession, updateSession } from '../services/api';
import './SessionSelector.css';

const SessionSelector = ({ onSessionSelect, currentSessionId }) => {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNewDialog, setShowNewDialog] = useState(false);
  const [newSessionName, setNewSessionName] = useState('');
  const [editingSessionId, setEditingSessionId] = useState(null);
  const [editName, setEditName] = useState('');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

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

  const formatDateShort = (isoString) => {
    const date = new Date(isoString);
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const time = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    return `${month}/${day} ${time}`;
  };

  const handleSessionSelect = (sessionId) => {
    onSessionSelect(sessionId);
    setIsDropdownOpen(false);
  };

  // Click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
    };

    if (isDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isDropdownOpen]);

  // Get current session object
  const currentSession = sessions.find(s => s.id === currentSessionId);

  if (loading) {
    return <div className="session-selector loading">Loading sessions...</div>;
  }

  return (
    <div className="session-selector compact">
      <div className="session-dropdown-container">
        <div className="session-dropdown-header">
          <label className="session-label">Session</label>
          <button
            className="session-dropdown-trigger"
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
          >
            <span className="current-session-name">
              {currentSession ? currentSession.name : 'Select a session...'}
            </span>
            <span className="dropdown-icon">{isDropdownOpen ? '▲' : '▼'}</span>
          </button>
        </div>

        {isDropdownOpen && (
          <div className="session-dropdown-list" ref={dropdownRef}>
            {sessions.length === 0 ? (
              <div className="dropdown-empty-state">
                No sessions yet
              </div>
            ) : (
              sessions.map((session) => (
                <div
                  key={session.id}
                  className={`session-dropdown-item ${currentSessionId === session.id ? 'active' : ''}`}
                  onClick={() => handleSessionSelect(session.id)}
                >
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
                    <>
                      <div className="session-item-main">
                        {currentSessionId === session.id && <span className="check-icon">✓</span>}
                        <span className="session-item-name">{session.name}</span>
                      </div>
                      <div className="session-item-meta">
                        {session.document_count} docs · {formatDateShort(session.updated_at)}
                      </div>
                      <div className="session-item-actions" onClick={(e) => e.stopPropagation()}>
                        <button
                          className="btn-icon-small"
                          onClick={(e) => startEditing(session, e)}
                          title="Rename"
                        >
                          ✏️
                        </button>
                        <button
                          className="btn-icon-small"
                          onClick={(e) => handleDeleteSession(session.id, e)}
                          title="Delete"
                        >
                          🗑️
                        </button>
                      </div>
                    </>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>

      <button className="btn-new-session-compact" onClick={() => setShowNewDialog(true)}>
        + New Session
      </button>

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
    </div>
  );
};

export default SessionSelector;
