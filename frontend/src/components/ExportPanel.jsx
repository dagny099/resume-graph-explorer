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

      {stats && (() => {
        // Define entity type display order (logical grouping)
        const entityTypeOrder = [
          { key: 'documents', label: 'Documents' },
          { key: 'persons', label: 'Person' },
          { key: 'jobs', label: 'Jobs' },
          { key: 'organizations', label: 'Organizations' },
          { key: 'education', label: 'Education' },
          { key: 'certifications', label: 'Certifications' },
          { key: 'skills', label: 'Skills' }
        ];

        // Build array of types to display (count > 0 only)
        const entitiesToDisplay = entityTypeOrder
          .map(({ key, label }) => {
            const count = key === 'documents'
              ? stats.total_documents
              : stats.total_entities[key] || 0;
            return { key, count, label };
          })
          .filter(({ count }) => count > 0);

        return (
          <>
            <div className="export-stats-grid">
              {entitiesToDisplay.map(({ key, count, label }) => (
                <div key={key} className="stat-item">
                  <span className="stat-value">{count}</span>
                  <span className="stat-label">{label}</span>
                </div>
              ))}
            </div>
          </>
        );
      })()}

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
