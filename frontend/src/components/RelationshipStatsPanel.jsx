import React, { useState } from 'react';
import './RelationshipStatsPanel.css';

const RelationshipStatsPanel = ({ stats }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [expandedCategories, setExpandedCategories] = useState(new Set());

  if (!stats) {
    return null;
  }

  const { edge_type_counts = {}, predicates_by_edge_type = {} } = stats;

  // Don't render if no edge data
  if (Object.keys(edge_type_counts).length === 0) {
    return null;
  }

  const toggleCategory = (category, event) => {
    event.stopPropagation();
    setExpandedCategories(prev => {
      const newSet = new Set(prev);
      if (newSet.has(category)) {
        newSet.delete(category);
      } else {
        newSet.add(category);
      }
      return newSet;
    });
  };

  const edgeTypeColors = {
    'ownership': '#2E7D32',
    'organizational': '#1565C0',
    'usage': '#6A1B9A',
    'hierarchical': '#EF6C00',
    'typing': '#BDBDBD',
    'other': '#757575'
  };

  return (
    <div className="relationship-stats-panel">
      <div className="stats-header" onClick={() => setIsExpanded(!isExpanded)}>
        <h4>Relationship Statistics</h4>
        <span className="toggle-icon">{isExpanded ? '▼' : '▶'}</span>
      </div>

      {isExpanded && (
        <div className="stats-content">
          <div className="stats-section">
            <h5>Edge Type Summary</h5>
            <div className="edge-type-list">
              {Object.entries(edge_type_counts)
                .sort((a, b) => b[1] - a[1]) // Sort by count descending
                .map(([type, count]) => {
                  const isExpanded = expandedCategories.has(type);
                  const predicates = predicates_by_edge_type[type] || {};
                  const hasPredicates = Object.keys(predicates).length > 0;

                  return (
                    <div key={type} className="edge-type-container">
                      <div
                        className="edge-type-item"
                        onClick={(e) => hasPredicates && toggleCategory(type, e)}
                        style={{ cursor: hasPredicates ? 'pointer' : 'default' }}
                      >
                        <span
                          className="edge-type-color"
                          style={{ backgroundColor: edgeTypeColors[type] || '#757575' }}
                        />
                        <span className="edge-type-label">{type}</span>
                        <span className="edge-type-count">{count}</span>
                        {hasPredicates && (
                          <span className="expand-icon">
                            {isExpanded ? '▼' : '▶'}
                          </span>
                        )}
                      </div>

                      {isExpanded && hasPredicates && (
                        <div className="predicate-list">
                          {Object.entries(predicates)
                            .sort((a, b) => b[1] - a[1]) // Sort by count descending
                            .map(([predicate, predicateCount]) => (
                              <div key={predicate} className="predicate-item">
                                <span className="predicate-label">• {predicate}</span>
                                <span className="predicate-count">{predicateCount}</span>
                              </div>
                            ))}
                        </div>
                      )}
                    </div>
                  );
                })}
            </div>
          </div>

          <div className="stats-note">
            ℹ️ Stats include all relationships (including hidden nodes)
          </div>
        </div>
      )}
    </div>
  );
};

export default RelationshipStatsPanel;
