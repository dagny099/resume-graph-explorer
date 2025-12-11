/**
 * Export Panel Component
 *
 * Provides controls for exporting graph in various RDF formats
 */

import React, { useState } from 'react';
import { exportSessionGraph, getSessionStats } from '../services/api';
import './ExportPanel.css';

const ExportPanel = ({ sessionId, refreshKey }) => {
  const [exporting, setExporting] = useState(false);
  const [stats, setStats] = useState(null);

  React.useEffect(() => {
    if (sessionId) {
      loadStats();
    }
  }, [sessionId, refreshKey]);

  const loadStats = async () => {
    try {
      const data = await getSessionStats(sessionId);
      setStats(data);
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  const handleExport = async (format) => {
    try {
      setExporting(true);
      await exportSessionGraph(sessionId, format);
    } catch (error) {
      console.error('Export failed:', error);
      alert('Export failed: ' + (error.response?.data?.error || error.message));
    } finally {
      setExporting(false);
    }
  };

  if (!sessionId) {
    return null;
  }

  return (
    <div className="export-panel">
      <h3>Export Graph</h3>

      {stats && (
        <div className="export-stats">
          <div className="stat-item">
            <span className="stat-value">{stats.total_documents}</span>
            <span className="stat-label">Documents</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{stats.total_entities.jobs}</span>
            <span className="stat-label">Jobs</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{stats.total_entities.skills}</span>
            <span className="stat-label">Skills</span>
          </div>
        </div>
      )}

      <div className="export-buttons">
        <button
          className="export-btn"
          onClick={() => handleExport('turtle')}
          disabled={exporting}
        >
          📄 Export Turtle (.ttl)
        </button>
        <button
          className="export-btn"
          onClick={() => handleExport('rdfxml')}
          disabled={exporting}
        >
          📄 Export RDF/XML (.rdf)
        </button>
        <button
          className="export-btn"
          onClick={() => handleExport('jsonld')}
          disabled={exporting}
        >
          📄 Export JSON-LD (.jsonld)
        </button>
      </div>
    </div>
  );
};

export default ExportPanel;
