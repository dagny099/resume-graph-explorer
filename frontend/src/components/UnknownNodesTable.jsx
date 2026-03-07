import React, { useState } from 'react';
import './UnknownNodesTable.css';

const UnknownNodesTable = ({ nodes, edges, hiddenTypes }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // Filter unknown nodes
  const unknownNodes = nodes.filter(node => node.group === 'unknown');

  if (unknownNodes.length === 0) {
    return null; // Don't render if no unknown nodes
  }

  // Helper: Count relationships for a node
  const countRelationships = (nodeId) => {
    return edges.filter(edge => edge.from === nodeId || edge.to === nodeId).length;
  };

  // Helper: Get connected node labels (limit to 3)
  const getConnectedNodes = (nodeId) => {
    const connectedIds = new Set();

    edges.forEach(edge => {
      if (edge.from === nodeId) {
        connectedIds.add(edge.to);
      } else if (edge.to === nodeId) {
        connectedIds.add(edge.from);
      }
    });

    const connectedLabels = Array.from(connectedIds)
      .map(id => {
        const node = nodes.find(n => n.id === id);
        return node ? node.label : null;
      })
      .filter(label => label)
      .slice(0, 3);

    if (connectedIds.size > 3) {
      return connectedLabels.join(', ') + '...';
    }
    return connectedLabels.join(', ') || 'None';
  };

  // Helper: Format confidence as percentage with color
  const formatConfidence = (confidence) => {
    const percent = Math.round(confidence * 100);
    let className = 'confidence-low';
    if (percent >= 90) className = 'confidence-high';
    else if (percent >= 70) className = 'confidence-medium';

    return <span className={`confidence ${className}`}>{percent}%</span>;
  };

  const isHidden = hiddenTypes.has('unknown');

  return (
    <div className="unknown-nodes-table">
      <div className="table-header" onClick={() => setIsExpanded(!isExpanded)}>
        <h4>
          Unknown Nodes
          <span className="unknown-badge">{unknownNodes.length}</span>
          {isHidden && <span className="hidden-indicator">(currently hidden)</span>}
        </h4>
        <span className="toggle-icon">{isExpanded ? '▼' : '▶'}</span>
      </div>

      {isExpanded && (
        <div className="table-content">
          <table>
            <thead>
              <tr>
                <th>Label</th>
                <th>Confidence</th>
                <th>Relationships</th>
                <th>Connected To</th>
              </tr>
            </thead>
            <tbody>
              {unknownNodes.map(node => (
                <tr key={node.id}>
                  <td className="node-label">{node.label}</td>
                  <td>{formatConfidence(node.metadata?.confidence || 1.0)}</td>
                  <td className="relationship-count">
                    {countRelationships(node.id)}
                  </td>
                  <td className="connected-nodes">
                    {getConnectedNodes(node.id)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="table-help">
            <span className="help-icon">ℹ️</span>
            <span className="help-text">
              Unknown nodes appear when entities are referenced in relationships
              but lack explicit type information. Higher confidence suggests
              stronger evidence from context.
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default UnknownNodesTable;
