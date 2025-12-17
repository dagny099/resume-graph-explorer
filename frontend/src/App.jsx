/**
 * Main App Component
 *
 * Orchestrates all components:
 * - Session selector
 * - Resume upload
 * - Graph visualization
 * - Entity details
 * - Export controls
 */

import React, { useState, useEffect } from 'react';
import SessionSelector from './components/SessionSelector';
import ResumeUpload from './components/ResumeUpload';
import GraphVisualization from './components/GraphVisualization';
import EntityPanel from './components/EntityPanel';
import ExportPanel from './components/ExportPanel';
import { getSessionGraph } from './services/api';
import './App.css';

function App() {
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [graphData, setGraphData] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [loading, setLoading] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    if (currentSessionId) {
      loadGraph();
    } else {
      setGraphData(null);
      setSelectedNode(null);
    }
  }, [currentSessionId]);

  const loadGraph = async () => {
    try {
      setLoading(true);
      const data = await getSessionGraph(currentSessionId);
      setGraphData(data);
    } catch (error) {
      console.error('Failed to load graph:', error);
      // Don't show error if no completed documents
      if (!error.response || error.response.status !== 404) {
        console.warn('Graph loading error:', error.message);
      }
      setGraphData(null);
    } finally {
      setLoading(false);
    }
  };

  const handleUploadComplete = () => {
    // Reload graph and stats after extraction complete
    setTimeout(() => {
      loadGraph();
      setRefreshKey(prev => prev + 1); // Trigger stats refresh
    }, 1000);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Resume Explorer</h1>
        <p>Transform your resume into an interactive knowledge graph</p>
      </header>

      <main className="app-main">
        <div className="sidebar">
          <SessionSelector
            onSessionSelect={setCurrentSessionId}
            currentSessionId={currentSessionId}
          />

          {currentSessionId && (
            <>
              <ExportPanel sessionId={currentSessionId} refreshKey={refreshKey} />
            </>
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
                <div className="loading-state">
                  <p>Loading graph...</p>
                </div>
              ) : (
                <GraphVisualization
                  graphData={graphData}
                  onNodeClick={setSelectedNode}
                />
              )}

              {selectedNode && <EntityPanel selectedNode={selectedNode} />}
            </>
          ) : (
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
