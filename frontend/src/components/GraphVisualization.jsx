/**
 * Graph Visualization Component (Vis.js)
 *
 * Interactive knowledge graph visualization featuring:
 * - Color-coded nodes by entity type
 * - Interactive tooltips
 * - Click handlers for entity details
 * - Physics-based layout
 */

import React, { useEffect, useRef, useState, useMemo } from 'react';
import { Network } from 'vis-network';
import RelationshipStatsPanel from './RelationshipStatsPanel';
import EntitySummaryPanel from './EntitySummaryPanel';
import UnknownNodesTable from './UnknownNodesTable';
import './GraphVisualization.css';

const GraphVisualization = ({ graphData, onNodeClick }) => {
  const containerRef = useRef(null);
  const networkRef = useRef(null);
  const [stats, setStats] = useState(null);
  const [hiddenNodeTypes, setHiddenNodeTypes] = useState(new Set());
  const [isExpanded, setIsExpanded] = useState(false);

  const toggleExpanded = () => setIsExpanded(prev => !prev);

  // Refit the graph after the CSS transition gives the container its new size
  useEffect(() => {
    const timer = setTimeout(() => networkRef.current?.fit(), 150);
    return () => clearTimeout(timer);
  }, [isExpanded]);

  // Toggle node type visibility
  const handleLegendToggle = (nodeType) => {
    setHiddenNodeTypes(prev => {
      const newSet = new Set(prev);
      if (newSet.has(nodeType)) {
        newSet.delete(nodeType);
      } else {
        newSet.add(nodeType);
      }
      return newSet;
    });
  };

  // Filter visible nodes
  const visibleNodes = useMemo(() => {
    if (!graphData?.nodes) return [];
    return graphData.nodes.filter(node => !hiddenNodeTypes.has(node.group));
  }, [graphData?.nodes, hiddenNodeTypes]);

  // Filter visible edges (only include if both nodes visible)
  const visibleEdges = useMemo(() => {
    if (!graphData?.edges) return [];
    const visibleNodeIds = new Set(visibleNodes.map(n => n.id));
    return graphData.edges.filter(edge =>
      visibleNodeIds.has(edge.from) && visibleNodeIds.has(edge.to)
    );
  }, [graphData?.edges, visibleNodes]);

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

    // Create network with filtered data
    networkRef.current = new Network(
      containerRef.current,
      {
        nodes: visibleNodes,
        edges: visibleEdges,
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
  }, [graphData, onNodeClick, visibleNodes, visibleEdges]);

  if (!graphData) {
    return (
      <div className="graph-visualization empty">
        <p>No graph data available</p>
        <p>Upload a resume to visualize the knowledge graph</p>
      </div>
    );
  }

  return (
    <div className={`graph-visualization${isExpanded ? ' expanded' : ''}`}>
      <div className="graph-header">
        <h3>
          {(() => {
            const name = graphData?.nodes?.find(n => n.group === 'person')?.label;
            return name
              ? <>Knowledge Graph for <span className="graph-person-name">{name}</span></>
              : 'Knowledge Graph';
          })()}
        </h3>
        <div className="graph-header-right">
          {stats && (
            <div className="graph-stats">
              <span>{stats.node_count} nodes</span>
              <span>{stats.edge_count} relationships</span>
            </div>
          )}
          <button
            className="fullscreen-btn"
            onClick={toggleExpanded}
            title={isExpanded ? 'Collapse graph' : 'Expand graph'}
            aria-label={isExpanded ? 'Collapse graph' : 'Expand graph'}
          >
            {isExpanded ? (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3" />
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
              </svg>
            )}
            <span>{isExpanded ? 'Collapse' : 'Expand'}</span>
          </button>
        </div>
      </div>

      <div ref={containerRef} className="graph-container" />

      {stats && stats.entity_type_counts && (
        <div className="graph-legend">
          <div className="legend-header">
            <h4>Legend</h4>
            <span className="legend-hint">Click a label to toggle visibility</span>
          </div>
          <div className="legend-items">
            {Object.entries(stats.entity_type_counts).map(([type, count]) => (
              <div
                key={type}
                className={`legend-item ${hiddenNodeTypes.has(type) ? 'hidden' : ''}`}
                onClick={() => handleLegendToggle(type)}
                role="button"
                tabIndex={0}
                onKeyPress={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    handleLegendToggle(type);
                  }
                }}
              >
                <span className={`legend-color legend-${type}`} />
                <span className="legend-label">
                  {type.charAt(0).toUpperCase() + type.slice(1)} ({count})
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <EntitySummaryPanel nodes={graphData?.nodes} />

      <RelationshipStatsPanel stats={stats} />

      <UnknownNodesTable
        nodes={graphData?.nodes || []}
        edges={graphData?.edges || []}
        hiddenTypes={hiddenNodeTypes}
      />
    </div>
  );
};

export default GraphVisualization;
