/**
 * Graph Visualization Component (Vis.js)
 *
 * Interactive knowledge graph visualization featuring:
 * - Color-coded nodes by entity type
 * - Interactive tooltips
 * - Click handlers for entity details
 * - Physics-based layout
 */

import React, { useEffect, useRef, useState } from 'react';
import { Network } from 'vis-network';
import './GraphVisualization.css';

const GraphVisualization = ({ graphData, onNodeClick }) => {
  const containerRef = useRef(null);
  const networkRef = useRef(null);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    if (!graphData || !containerRef.current) {
      return;
    }

    const options = {
      nodes: {
        shape: 'dot',
        size: 16,
        font: {
          size: 14,
          color: '#343434',
        },
        borderWidth: 2,
        shadow: true,
      },
      edges: {
        arrows: {
          to: {
            enabled: true,
            scaleFactor: 0.5,
          },
        },
        smooth: {
          type: 'continuous',
          roundness: 0.5,
        },
        font: {
          size: 11,
          align: 'middle',
        },
      },
      physics: {
        enabled: true,
        barnesHut: {
          gravitationalConstant: -2000,
          centralGravity: 0.3,
          springLength: 150,
          springConstant: 0.04,
          damping: 0.09,
        },
        stabilization: {
          iterations: 200,
        },
      },
      interaction: {
        hover: true,
        navigationButtons: true,
        keyboard: true,
        tooltipDelay: 100,
      },
      layout: {
        improvedLayout: true,
        hierarchical: false,
      },
    };

    // Create network
    networkRef.current = new Network(
      containerRef.current,
      {
        nodes: graphData.nodes || [],
        edges: graphData.edges || [],
      },
      options
    );

    // Event handlers
    networkRef.current.on('click', (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        const node = graphData.nodes.find((n) => n.id === nodeId);

        if (onNodeClick && node) {
          onNodeClick(node);
        }
      }
    });

    networkRef.current.on('hoverNode', () => {
      containerRef.current.style.cursor = 'pointer';
    });

    networkRef.current.on('blurNode', () => {
      containerRef.current.style.cursor = 'default';
    });

    // Set stats
    if (graphData.stats) {
      setStats(graphData.stats);
    }

    return () => {
      if (networkRef.current) {
        networkRef.current.destroy();
      }
    };
  }, [graphData, onNodeClick]);

  if (!graphData) {
    return (
      <div className="graph-visualization empty">
        <p>No graph data available</p>
        <p>Upload a resume to visualize the knowledge graph</p>
      </div>
    );
  }

  return (
    <div className="graph-visualization">
      <div className="graph-header">
        <h3>Knowledge Graph</h3>
        {stats && (
          <div className="graph-stats">
            <span>{stats.node_count} nodes</span>
            <span>{stats.edge_count} relationships</span>
          </div>
        )}
      </div>

      <div ref={containerRef} className="graph-container" />

      {stats && stats.entity_type_counts && (
        <div className="graph-legend">
          <h4>Legend</h4>
          <div className="legend-items">
            {Object.entries(stats.entity_type_counts).map(([type, count]) => (
              <div key={type} className="legend-item">
                <span className={`legend-color legend-${type}`} />
                <span className="legend-label">
                  {type.charAt(0).toUpperCase() + type.slice(1)} ({count})
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default GraphVisualization;
