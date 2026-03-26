/**
 * InsightsViewer
 *
 * Displays the 6 structural analysis documents from graph_analyzer.py.
 * Each analysis is rendered as markdown with a tab to switch between them.
 * YAML front matter is stripped before rendering.
 */

import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { getInsight } from '../services/api';
import './InsightsViewer.css';

const ANALYSIS_TYPES = [
  { type: 'skill_gap',       label: 'Skill Gap' },
  { type: 'career_topology', label: 'Career Topology' },
  { type: 'tech_evolution',  label: 'Tech Evolution' },
  { type: 'hierarchy_map',   label: 'Hierarchy Map' },
  { type: 'esco_coverage',   label: 'ESCO Coverage' },
  { type: 'role_progression',label: 'Role Progression' },
];

/**
 * Optional info banners shown above the markdown for specific analyses.
 * Explains what the analysis does and doesn't tell you — set expectations
 * before the reader encounters numbers that might seem surprising.
 */
const ANALYSIS_INFO = {
  hierarchy_map: (
    <div className="insight-info">
      <strong>About ESCO Categories:</strong> Skills are grouped using the{' '}
      <a href="https://esco.ec.europa.eu" target="_blank" rel="noreferrer">
        European Skills/Competences taxonomy
      </a>{' '}
      (ESCO v1.2.1), a standard used by HR and job-matching systems across the EU.
      Expect ~50–60% of modern tech skills to match — vendor-specific tools (AWS,
      TensorFlow) and emerging AI frameworks (LangChain, LlamaIndex) rarely have
      ESCO entries. A large "uncategorized" group often signals a cutting-edge,
      specialized stack — not a gap in your profile.
    </div>
  ),
  esco_coverage: (
    <div className="insight-info">
      <strong>About ESCO coverage:</strong> Skills with a real ESCO URI are
      discoverable across any ESCO-aligned system (job boards, ATS, EU talent
      platforms). Vendor-specific tools typically have no ESCO entry — this is
      expected, not a problem. The coverage percentage reflects how interoperable
      your declared skill set is, not how impressive it is.
    </div>
  ),
};

/** Strip YAML front matter (--- ... ---) from markdown content. */
function stripFrontMatter(content) {
  if (!content) return '';
  const parts = content.split('---');
  if (parts.length >= 3) {
    return parts.slice(2).join('---').trim();
  }
  return content.trim();
}

const InsightsViewer = ({ sessionId, pipelineStatus }) => {
  const [activeType, setActiveType] = useState('skill_gap');
  const [contentCache, setContentCache] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const availableSet = new Set(pipelineStatus?.insights_list || []);
  const hasAny = availableSet.size > 0;

  // Load content when switching tabs (if not already cached)
  useEffect(() => {
    if (!sessionId || !availableSet.has(activeType)) return;
    if (contentCache[activeType]) return;

    const load = async () => {
      setLoading(true);
      setError('');
      try {
        const data = await getInsight(sessionId, activeType);
        setContentCache(prev => ({ ...prev, [activeType]: data.content || '' }));
      } catch (err) {
        setError(err.response?.data?.error || err.message);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [activeType, sessionId, availableSet.size]); // eslint-disable-line react-hooks/exhaustive-deps

  // When new analyses become available, invalidate cache for any refreshed types
  useEffect(() => {
    setContentCache({});
  }, [pipelineStatus?.insights_available]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!hasAny) {
    return (
      <div className="insights-viewer insights-empty">
        <div className="insights-placeholder">
          <span className="insights-placeholder-icon">🔬</span>
          <h3>No Insights Yet</h3>
          <p>
            Run <strong>Step 1 — Analyze Graph</strong> in the Analysis Pipeline
            sidebar to generate 6 structural analyses of your resume graph.
          </p>
        </div>
      </div>
    );
  }

  const content = contentCache[activeType];
  const isAvailable = availableSet.has(activeType);

  return (
    <div className="insights-viewer">
      {/* Tab strip */}
      <div className="insights-tabs">
        {ANALYSIS_TYPES.map(({ type, label }) => (
          <button
            key={type}
            className={`insights-tab ${activeType === type ? 'active' : ''} ${availableSet.has(type) ? '' : 'unavailable'}`}
            onClick={() => setActiveType(type)}
          >
            {availableSet.has(type) ? '✓ ' : '○ '}
            {label}
          </button>
        ))}
      </div>

      {/* Content area */}
      <div className="insights-content">
        {!isAvailable ? (
          <div className="insights-not-available">
            <p>This analysis was not generated. Try re-running graph analysis.</p>
          </div>
        ) : loading ? (
          <div className="insights-loading"><p>Loading…</p></div>
        ) : error ? (
          <div className="insights-error"><p>⚠ {error}</p></div>
        ) : content ? (
          <>
            {ANALYSIS_INFO[activeType] && (
              <div className="insight-info-wrapper">
                {ANALYSIS_INFO[activeType]}
              </div>
            )}
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {stripFrontMatter(content)}
            </ReactMarkdown>
          </>
        ) : null}
      </div>
    </div>
  );
};

export default InsightsViewer;
