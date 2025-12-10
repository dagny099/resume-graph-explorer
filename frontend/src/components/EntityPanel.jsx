/**
 * Entity Panel Component
 *
 * Displays details of selected graph node
 */

import React from 'react';
import './EntityPanel.css';

const EntityPanel = ({ selectedNode }) => {
  if (!selectedNode) {
    return (
      <div className="entity-panel empty">
        <p>Click on a node to view details</p>
      </div>
    );
  }

  const { label, group, metadata, title } = selectedNode;

  return (
    <div className="entity-panel">
      <div className="entity-header">
        <span className={`entity-badge entity-${group}`}>{group}</span>
        <h3>{label}</h3>
      </div>

      {title && (
        <div className="entity-tooltip" dangerouslySetInnerHTML={{ __html: title }} />
      )}

      {metadata && (
        <div className="entity-metadata">
          <h4>Metadata</h4>
          <dl>
            {Object.entries(metadata).map(([key, value]) => (
              <div key={key} className="metadata-item">
                <dt>{key}</dt>
                <dd>{value != null ? String(value) : 'N/A'}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}
    </div>
  );
};

export default EntityPanel;
