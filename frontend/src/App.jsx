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
 *   - A subtle "↺ Clear Session" button lets users start fresh.
 *
 * VITE_AUTO_SESSION not set, or =false  (default — personal / open-source deploy)
 *   - Shows the full SessionSelector UI: create, rename, delete, and switch sessions.
 *   - No localStorage side effects; all session management is explicit.
 *   - Welcome screen is shown until the user creates or selects a session.
 */

import React, { useState, useEffect, useCallback } from 'react';
import SessionSelector from './components/SessionSelector';
import ResumeUpload from './components/ResumeUpload';
import GraphVisualization from './components/GraphVisualization';
import EntityPanel from './components/EntityPanel';
import ExportPanel from './components/ExportPanel';
import AnalysisPipelinePanel from './components/AnalysisPipelinePanel';
import InsightsViewer from './components/InsightsViewer';
import NarrativeViewer from './components/NarrativeViewer';
import { createSession, getSession, getSessionGraph, getPipelineStatus, warmupBackend } from './services/api';
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

  // Active content tab: 'graph' | 'insights' | 'narratives'
  const [activeTab, setActiveTab] = useState('graph');

  // Pipeline status — refreshed after analysis/synthesis completes
  const [pipelineStatus, setPipelineStatus] = useState(null);

  // Manual mode: immediately ready (user drives session creation via SessionSelector).
  // Auto mode: starts false — we wait for async init before rendering the main UI.
  const [sessionReady, setSessionReady] = useState(!AUTO_SESSION);

  // Auto mode only: true if the backend was unreachable during init.
  const [sessionError, setSessionError] = useState(false);

  // Connection status for better UX during cold starts
  const [connectionStatus, setConnectionStatus] = useState('connecting'); // 'connecting' | 'warming' | 'retrying' | 'ready' | 'error'

  // Welcome screen: shown initially in both modes.
  // Auto mode: dismissed by clicking "Get Started". Auto-dismissed if returning user has graph data.
  // Manual mode: dismissed when user creates/selects a session (currentSessionId becomes non-null).
  const [showWelcome, setShowWelcome] = useState(AUTO_SESSION);

  // ─── Auto-session initialization ──────────────────────────────────────────
  useEffect(() => {
    if (!AUTO_SESSION) return;

    const initSession = async () => {
      setConnectionStatus('connecting');

      // Warm up the backend first (wakes from cold start)
      setConnectionStatus('warming');
      await warmupBackend();

      const savedId = localStorage.getItem(SESSION_STORAGE_KEY);

      if (savedId) {
        try {
          setConnectionStatus('connecting');
          await getSession(savedId);
          setCurrentSessionId(savedId);
          setSessionReady(true);
          setConnectionStatus('ready');
          return;
        } catch {
          localStorage.removeItem(SESSION_STORAGE_KEY);
          setConnectionStatus('retrying');
        }
      }

      try {
        setConnectionStatus('connecting');
        const data = await createSession();
        localStorage.setItem(SESSION_STORAGE_KEY, data.session.id);
        setCurrentSessionId(data.session.id);
        setConnectionStatus('ready');
      } catch (err) {
        console.error('Failed to initialize session:', err);
        setSessionError(true);
        setConnectionStatus('error');
      } finally {
        setSessionReady(true);
      }
    };

    initSession();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ─── Graph loading ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (currentSessionId) {
      loadGraph();
      loadPipelineStatus();
    } else {
      setGraphData(null);
      setSelectedNode(null);
      setPipelineStatus(null);
      setActiveTab('graph');
    }
  }, [currentSessionId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto mode: if a returning user already has graph data, skip the welcome screen.
  useEffect(() => {
    if (AUTO_SESSION && graphData && showWelcome) {
      setShowWelcome(false);
    }
  }, [graphData]); // eslint-disable-line react-hooks/exhaustive-deps

  const loadGraph = async () => {
    try {
      setLoading(true);
      const data = await getSessionGraph(currentSessionId);
      setGraphData(data);
    } catch (error) {
      if (!error.response || error.response.status !== 404) {
        console.warn('Graph loading error:', error.message);
      }
      setGraphData(null);
    } finally {
      setLoading(false);
    }
  };

  const loadPipelineStatus = async () => {
    if (!currentSessionId) return;
    try {
      const status = await getPipelineStatus(currentSessionId);
      setPipelineStatus(status);
    } catch {
      // Pipeline status is non-critical — silently ignore failures
    }
  };

  const handleUploadComplete = useCallback(() => {
    setRefreshKey(prev => prev + 1);
    let attempts = 0;
    const tryLoad = async () => {
      attempts++;
      try {
        setLoading(true);
        const data = await getSessionGraph(currentSessionId);
        setGraphData(data);
        setLoading(false);
      } catch (error) {
        if (attempts < 5 && (!error.response || error.response.status === 404)) {
          setTimeout(tryLoad, 3000);
        } else {
          setLoading(false);
          if (!error.response || error.response.status !== 404) {
            console.warn('Graph loading error:', error.message);
          }
        }
      }
    };
    tryLoad();
  }, [currentSessionId]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleClearSession = async () => {
    if (AUTO_SESSION) {
      try {
        localStorage.removeItem(SESSION_STORAGE_KEY);
        const data = await createSession();
        localStorage.setItem(SESSION_STORAGE_KEY, data.session.id);
        setCurrentSessionId(data.session.id);
        setGraphData(null);
        setSelectedNode(null);
        setPipelineStatus(null);
        setActiveTab('graph');
      } catch (err) {
        console.error('Failed to create new session:', err);
      }
    } else {
      setCurrentSessionId(null);
    }
  };

  // Refresh pipeline status after analysis or synthesis completes
  const handleAnalysisComplete = useCallback(() => {
    loadPipelineStatus();
  }, [currentSessionId]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSynthesisComplete = useCallback(() => {
    loadPipelineStatus();
  }, [currentSessionId]); // eslint-disable-line react-hooks/exhaustive-deps

  // ─── Loading / error screens ───────────────────────────────────────────────
  if (!sessionReady) {
    const statusMessages = {
      connecting: 'Connecting to backend…',
      warming: '⏳ Waking up backend from sleep…',
      retrying: 'Retrying connection…',
    };

    return (
      <div className="app">
        <AppHeader />
        <div className="loading-state">
          <p>{statusMessages[connectionStatus] || 'Starting up…'}</p>
          {connectionStatus === 'warming' && (
            <p style={{ fontSize: '14px', opacity: 0.8, marginTop: '10px' }}>
              First visit can take 5-10 seconds while the server starts up
            </p>
          )}
        </div>
      </div>
    );
  }

  if (AUTO_SESSION && sessionError) {
    return (
      <div className="app">
        <AppHeader />
        <div className="loading-state" style={{ textAlign: 'center' }}>
          <p style={{ fontSize: '18px', marginBottom: '10px' }}>⏳ Backend is waking up from sleep...</p>
          <p style={{ fontSize: '14px', opacity: 0.8, marginBottom: '20px' }}>
            This can take 5-10 seconds on first visit. The connection will retry automatically.
          </p>
          <button
            onClick={() => window.location.reload()}
            style={{
              padding: '10px 20px',
              fontSize: '14px',
              cursor: 'pointer',
              borderRadius: '4px',
              border: '1px solid #ccc',
              background: '#f5f5f5',
            }}
          >
            Retry Now
          </button>
        </div>
      </div>
    );
  }

  // ─── Tab badge helpers ─────────────────────────────────────────────────────
  const insightsCount = pipelineStatus?.insights_available || 0;
  const narrativesReady =
    pipelineStatus?.narratives_conservative && pipelineStatus?.narratives_exploratory;

  // ─── Main UI ───────────────────────────────────────────────────────────────
  return (
    <div className="app">
      <AppHeader />

      <main className="app-main">
        <div className="sidebar">
          {!AUTO_SESSION && (
            <SessionSelector
              onSessionSelect={setCurrentSessionId}
              currentSessionId={currentSessionId}
            />
          )}

          {currentSessionId && !showWelcome && (
            <ExportPanel sessionId={currentSessionId} refreshKey={refreshKey} />
          )}

          {currentSessionId && !showWelcome && (
            <AnalysisPipelinePanel
              sessionId={currentSessionId}
              pipelineStatus={pipelineStatus}
              onAnalysisComplete={handleAnalysisComplete}
              onSynthesisComplete={handleSynthesisComplete}
            />
          )}

          {currentSessionId && !showWelcome && (
            <button
              className="btn-reset"
              onClick={handleClearSession}
              title="Clear current data and start fresh"
            >
              ↺ Clear Session
            </button>
          )}
        </div>

        <div className="content">
          {(AUTO_SESSION ? showWelcome : !currentSessionId) ? (
            <div className="welcome-state">
              <h2>Welcome to Resume Explorer</h2>
              <p>
                {AUTO_SESSION
                  ? 'Upload your resume to explore it as an interactive knowledge graph'
                  : 'Select a session or create a new one to get started'}
              </p>
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
              {AUTO_SESSION && (
                <button
                  className="btn-get-started btn-get-started-main"
                  onClick={() => setShowWelcome(false)}
                >
                  Get Started
                </button>
              )}
            </div>
          ) : currentSessionId ? (
            <>
              {/* Content tab strip */}
              <div className="content-tabs">
                <button
                  className={`content-tab ${activeTab === 'graph' ? 'active' : ''}`}
                  onClick={() => setActiveTab('graph')}
                >
                  📊 Graph
                </button>
                <button
                  className={`content-tab ${activeTab === 'insights' ? 'active' : ''}`}
                  onClick={() => setActiveTab('insights')}
                >
                  🔬 Insights
                  {insightsCount > 0 && (
                    <span className="tab-badge">{insightsCount}/6</span>
                  )}
                </button>
                <button
                  className={`content-tab ${activeTab === 'narratives' ? 'active' : ''}`}
                  onClick={() => setActiveTab('narratives')}
                >
                  📖 Narratives
                  {narrativesReady && <span className="tab-badge">✓</span>}
                </button>
              </div>

              {/* Graph tab */}
              {activeTab === 'graph' && (
                <>
                  <ResumeUpload
                    sessionId={currentSessionId}
                    onUploadComplete={handleUploadComplete}
                    graphData={graphData}
                  />
                  {loading ? (
                    <div className="loading-state"><p>Loading graph…</p></div>
                  ) : (
                    <GraphVisualization
                      graphData={graphData}
                      onNodeClick={setSelectedNode}
                    />
                  )}
                  {selectedNode && <EntityPanel selectedNode={selectedNode} />}
                </>
              )}

              {/* Insights tab */}
              {activeTab === 'insights' && (
                <InsightsViewer
                  sessionId={currentSessionId}
                  pipelineStatus={pipelineStatus}
                />
              )}

              {/* Narratives tab */}
              {activeTab === 'narratives' && (
                <NarrativeViewer
                  sessionId={currentSessionId}
                  pipelineStatus={pipelineStatus}
                />
              )}
            </>
          ) : (
            <div className="loading-state"><p>Starting up…</p></div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
