/**
 * Main App Component
 *
 * Supports two deployment modes, controlled by the VITE_AUTO_SESSION env var:
 *
 * VITE_AUTO_SESSION=true  (public / demo deploy — e.g. Vercel)
 *   - Silently creates a session on first visit and stores the ID in localStorage.
 *   - Restores the session on return visits; transparently creates a new one if it
 *     has expired (free-tier backends wipe state on restart).
 *   - Visitors land directly on the upload/graph view with zero manual setup.
 *   - A subtle "↺ New Session" button lets users start fresh.
 *
 * VITE_AUTO_SESSION not set, or =false  (default — personal / open-source deploy)
 *   - Shows the full SessionSelector UI: create, rename, delete, and switch sessions.
 *   - No localStorage side effects; all session management is explicit.
 *   - Welcome screen is shown until the user creates or selects a session.
 */

import React, { useState, useEffect } from 'react';
import SessionSelector from './components/SessionSelector';
import ResumeUpload from './components/ResumeUpload';
import GraphVisualization from './components/GraphVisualization';
import EntityPanel from './components/EntityPanel';
import ExportPanel from './components/ExportPanel';
import { createSession, getSession, getSessionGraph } from './services/api';
import './App.css';

// Resolved once at module load — changing the env var requires a rebuild.
const AUTO_SESSION = import.meta.env.VITE_AUTO_SESSION === 'true';

// localStorage key used to persist the auto-created session ID across page loads.
const SESSION_STORAGE_KEY = 'resume_explorer_session_id';

// ─── Header — shared across all render states ────────────────────────────────
const AppHeader = () => (
  <header className="app-header">
    <h1>Resume Explorer</h1>
    <p>Transform your resume into an interactive knowledge graph</p>
  </header>
);

function App() {
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [graphData, setGraphData] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [loading, setLoading] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  // Manual mode: immediately ready (user drives session creation via SessionSelector).
  // Auto mode: starts false — we wait for async init before rendering the main UI.
  const [sessionReady, setSessionReady] = useState(!AUTO_SESSION);

  // Auto mode only: true if the backend was unreachable during init.
  const [sessionError, setSessionError] = useState(false);

  // ─── Auto-session initialization ──────────────────────────────────────────
  // Runs once on mount. Skipped entirely in manual mode.
  //
  // Flow:
  //   1. Check localStorage for a previously stored session ID.
  //   2. Validate it still exists on the backend (free-tier servers wipe on restart).
  //   3. If missing or expired, create a fresh session silently.
  useEffect(() => {
    if (!AUTO_SESSION) return;

    const initSession = async () => {
      const savedId = localStorage.getItem(SESSION_STORAGE_KEY);

      if (savedId) {
        try {
          await getSession(savedId); // throws a 404 if the session no longer exists
          setCurrentSessionId(savedId);
          setSessionReady(true);
          return;
        } catch {
          // Session gone (e.g. server restarted) — fall through to create a new one
          localStorage.removeItem(SESSION_STORAGE_KEY);
        }
      }

      try {
        const data = await createSession(); // backend auto-generates a session name
        localStorage.setItem(SESSION_STORAGE_KEY, data.session.id);
        setCurrentSessionId(data.session.id);
      } catch (err) {
        console.error('Failed to initialize session:', err);
        setSessionError(true);
      } finally {
        // Always unblock the UI, whether we succeeded or failed
        setSessionReady(true);
      }
    };

    initSession();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ─── Graph loading ─────────────────────────────────────────────────────────
  // Re-runs whenever the active session changes (including on first successful init).
  useEffect(() => {
    if (currentSessionId) {
      loadGraph();
    } else {
      setGraphData(null);
      setSelectedNode(null);
    }
  }, [currentSessionId]); // eslint-disable-line react-hooks/exhaustive-deps

  const loadGraph = async () => {
    try {
      setLoading(true);
      const data = await getSessionGraph(currentSessionId);
      setGraphData(data);
    } catch (error) {
      // 404 is expected when no documents have completed extraction yet — not an error
      if (!error.response || error.response.status !== 404) {
        console.warn('Graph loading error:', error.message);
      }
      setGraphData(null);
    } finally {
      setLoading(false);
    }
  };

  const handleUploadComplete = () => {
    // Brief delay gives the backend time to finish writing before we re-poll
    setTimeout(() => {
      loadGraph();
      setRefreshKey(prev => prev + 1); // signals ExportPanel to refresh its stats
    }, 1000);
  };

  // ─── Reset to a fresh session (auto mode only) ────────────────────────────
  // Discards the stored session ID and creates a new one, clearing the UI.
  const handleNewSession = async () => {
    try {
      localStorage.removeItem(SESSION_STORAGE_KEY);
      const data = await createSession();
      localStorage.setItem(SESSION_STORAGE_KEY, data.session.id);
      setCurrentSessionId(data.session.id);
      setGraphData(null);
      setSelectedNode(null);
    } catch (err) {
      console.error('Failed to create new session:', err);
    }
  };

  // ─── Loading screen — auto mode only, shown during async init ─────────────
  if (!sessionReady) {
    return (
      <div className="app">
        <AppHeader />
        <div className="loading-state"><p>Starting up...</p></div>
      </div>
    );
  }

  // ─── Error screen — auto mode only, shown if backend was unreachable ───────
  if (AUTO_SESSION && sessionError) {
    return (
      <div className="app">
        <AppHeader />
        <div className="loading-state">
          <p>Could not connect to the backend. Please try refreshing the page.</p>
        </div>
      </div>
    );
  }

  // ─── Main UI ───────────────────────────────────────────────────────────────
  return (
    <div className="app">
      <AppHeader />

      <main className="app-main">
        <div className="sidebar">
          {/* Manual mode: full session management UI (create, rename, delete, switch) */}
          {!AUTO_SESSION && (
            <SessionSelector
              onSessionSelect={setCurrentSessionId}
              currentSessionId={currentSessionId}
            />
          )}

          {/* Export controls — shown once a session is active in either mode */}
          {currentSessionId && (
            <ExportPanel sessionId={currentSessionId} refreshKey={refreshKey} />
          )}

          {/* Auto mode: unobtrusive reset button at the bottom of the sidebar */}
          {AUTO_SESSION && (
            <button
              className="btn-reset"
              onClick={handleNewSession}
              title="Clear current data and start fresh"
            >
              ↺ New Session
            </button>
          )}
        </div>

        <div className="content">
          {currentSessionId ? (
            <>
              <ResumeUpload
                sessionId={currentSessionId}
                onUploadComplete={handleUploadComplete}
                graphData={graphData}
              />

              {loading ? (
                <div className="loading-state"><p>Loading graph...</p></div>
              ) : (
                <GraphVisualization
                  graphData={graphData}
                  onNodeClick={setSelectedNode}
                />
              )}

              {selectedNode && <EntityPanel selectedNode={selectedNode} />}
            </>
          ) : (
            // Manual mode only: currentSessionId is null until the user creates/selects one.
            // Auto mode never reaches here — it either has a session or shows the error screen.
            <div className="welcome-state">
              <h2>Welcome to Resume Explorer</h2>
              <p>Select a session or create a new one to get started</p>
              <div className="features">
                <div className="feature">
                  <span className="feature-icon">📊</span>
                  <h3>Knowledge Graph</h3>
                  <p>Visualize your resume as an interactive graph</p>
                </div>
                <div className="feature">
                  <span className="feature-icon">🤖</span>
                  <h3>AI Extraction</h3>
                  <p>Powered by advanced language models</p>
                </div>
                <div className="feature">
                  <span className="feature-icon">🔗</span>
                  <h3>SKOS Compliant</h3>
                  <p>Export to standard RDF formats</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
