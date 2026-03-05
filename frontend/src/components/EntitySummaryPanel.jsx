import React, { useState } from 'react';
import './EntitySummaryPanel.css';

const ENTITY_COLORS = {
  person:        '#FF6B6B',
  job:           '#4ECDC4',
  organization:  '#DDA15E',
  education:     '#96CEB4',
  certification: '#FFEAA7',
  skill:         '#45B7D1',
};

// Display order — most structurally important first, skills last (longest list)
const TYPE_ORDER = ['person', 'job', 'organization', 'education', 'certification', 'skill'];

const EntitySummaryPanel = ({ nodes }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [expandedTypes, setExpandedTypes] = useState(new Set());

  if (!nodes || nodes.length === 0) return null;

  // Group by type, exclude unknown
  const grouped = {};
  for (const node of nodes) {
    if (node.group === 'unknown') continue;
    if (!grouped[node.group]) grouped[node.group] = [];
    grouped[node.group].push(node.label);
  }

  const orderedTypes = [
    ...TYPE_ORDER.filter(t => grouped[t]),
    ...Object.keys(grouped).filter(t => !TYPE_ORDER.includes(t) && grouped[t]),
  ];

  if (orderedTypes.length === 0) return null;

  const totalKnown = orderedTypes.reduce((sum, t) => sum + grouped[t].length, 0);

  const toggleType = (type, e) => {
    e.stopPropagation();
    setExpandedTypes(prev => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type); else next.add(type);
      return next;
    });
  };

  return (
    <div className="entity-summary-panel">
      <div className="summary-header" onClick={() => setIsExpanded(!isExpanded)}>
        <h4>Extracted Entities</h4>
        <div className="summary-header-right">
          <span className="summary-total">{totalKnown} entities</span>
          <span className="toggle-icon">{isExpanded ? '▼' : '▶'}</span>
        </div>
      </div>

      {isExpanded && (
        <div className="summary-content">
          {orderedTypes.map(type => {
            const labels = [...grouped[type]].sort((a, b) => a.localeCompare(b));
            const typeExpanded = expandedTypes.has(type);
            return (
              <div key={type} className="summary-type-container">
                <div className="summary-type-header" onClick={(e) => toggleType(type, e)}>
                  <span
                    className="summary-type-dot"
                    style={{ backgroundColor: ENTITY_COLORS[type] || '#95A5A6' }}
                  />
                  <span className="summary-type-label">
                    {type.charAt(0).toUpperCase() + type.slice(1)}
                  </span>
                  <span className="summary-type-count">{labels.length}</span>
                  <span className="expand-icon">{typeExpanded ? '▼' : '▶'}</span>
                </div>

                {typeExpanded && (
                  <ul className="summary-items">
                    {labels.map((label, i) => (
                      <li key={i} className="summary-item">{label}</li>
                    ))}
                  </ul>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default EntitySummaryPanel;
