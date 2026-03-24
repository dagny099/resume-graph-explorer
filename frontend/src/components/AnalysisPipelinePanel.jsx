/**
 * AnalysisPipelinePanel
 *
 * Sidebar component that controls the two-step post-export analysis pipeline:
 *   Step 1 — Graph Analysis (deterministic, fast, no LLM required)
 *   Step 2 — Career Narratives (LLM-powered, ~30 seconds)
 *
 * Progress messages are received via WebSocket events.
 */

import React, { useState, useEffect } from 'react';
import wsClient from '../services/websocket';
import { runGraphAnalysis, runSynthesis, getPipelineStatus } from '../services/api';
import './AnalysisPipelinePanel.css';

const NORMALIZE_TOOLTIP =
  'Runs a quick deterministic pass to fix URL-encoding and casing ' +
  'inconsistencies before analysis (free, no API key needed). ' +
  'Recommended if your resume has inconsistent skill naming.';

const AnalysisPipelinePanel = ({
  sessionId,
  pipelineStatus,
  onAnalysisComplete,
  onSynthesisComplete,
}) => {
  const [normalize, setNormalize]           = useState(false);
  const [provider, setProvider]             = useState('anthropic');
  const [analyzing, setAnalyzing]           = useState(false);
  const [synthesizing, setSynthesizing]     = useState(false);
  const [analysisMessage, setAnalysisMessage]     = useState('');
  const [synthesisMessage, setSynthesisMessage]   = useState('');
  const [analysisError, setAnalysisError]         = useState('');
  const [synthesisError, setSynthesisError]       = useState('');

  // WebSocket listeners for pipeline events
  useEffect(() => {
    if (!sessionId) return;

    const onAnalysisStarted = (data) => {
      if (data.session_id !== sessionId) return;
      setAnalyzing(true);
      setAnalysisError('');
      setAnalysisMessage('Starting analysis…');
    };

    const onAnalysisProgress = (data) => {
      if (data.session_id !== sessionId) return;
      setAnalysisMessage(data.message || '');
    };

    const onAnalysisComplete = (data) => {
      if (data.session_id !== sessionId) return;
      setAnalyzing(false);
      setAnalysisMessage(`✓ ${data.insights_count || 6} insights ready`);
      onAnalysisComplete?.();
    };

    const onAnalysisError = (data) => {
      if (data.session_id !== sessionId) return;
      setAnalyzing(false);
      setAnalysisError(data.error || 'Analysis failed');
      setAnalysisMessage('');
    };

    const onSynthesisStarted = (data) => {
      if (data.session_id !== sessionId) return;
      setSynthesizing(true);
      setSynthesisError('');
      setSynthesisMessage('Starting synthesis…');
    };

    const onSynthesisProgress = (data) => {
      if (data.session_id !== sessionId) return;
      setSynthesisMessage(data.message || '');
    };

    const onSynthesisComplete = (data) => {
      if (data.session_id !== sessionId) return;
      setSynthesizing(false);
      setSynthesisMessage('✓ Both narratives ready');
      onSynthesisComplete?.();
    };

    const onSynthesisError = (data) => {
      if (data.session_id !== sessionId) return;
      setSynthesizing(false);
      setSynthesisError(data.error || 'Synthesis failed');
      setSynthesisMessage('');
    };

    wsClient.on('pipeline_analysis_started',  onAnalysisStarted);
    wsClient.on('pipeline_analysis_progress', onAnalysisProgress);
    wsClient.on('pipeline_analysis_complete', onAnalysisComplete);
    wsClient.on('pipeline_analysis_error',    onAnalysisError);
    wsClient.on('pipeline_synthesis_started',  onSynthesisStarted);
    wsClient.on('pipeline_synthesis_progress', onSynthesisProgress);
    wsClient.on('pipeline_synthesis_complete', onSynthesisComplete);
    wsClient.on('pipeline_synthesis_error',    onSynthesisError);

    return () => {
      wsClient.off('pipeline_analysis_started',  onAnalysisStarted);
      wsClient.off('pipeline_analysis_progress', onAnalysisProgress);
      wsClient.off('pipeline_analysis_complete', onAnalysisComplete);
      wsClient.off('pipeline_analysis_error',    onAnalysisError);
      wsClient.off('pipeline_synthesis_started',  onSynthesisStarted);
      wsClient.off('pipeline_synthesis_progress', onSynthesisProgress);
      wsClient.off('pipeline_synthesis_complete', onSynthesisComplete);
      wsClient.off('pipeline_synthesis_error',    onSynthesisError);
    };
  }, [sessionId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Seed status messages from pipelineStatus on load
  useEffect(() => {
    if (!pipelineStatus) return;
    if (pipelineStatus.insights_available > 0 && !analysisMessage && !analyzing) {
      setAnalysisMessage(`✓ ${pipelineStatus.insights_available}/6 insights ready`);
    }
    if (
      pipelineStatus.narratives_conservative &&
      pipelineStatus.narratives_exploratory &&
      !synthesisMessage && !synthesizing
    ) {
      setSynthesisMessage('✓ Both narratives ready');
    }
  }, [pipelineStatus]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleAnalyze = async () => {
    try {
      setAnalysisError('');
      setAnalysisMessage('Sending request…');
      await runGraphAnalysis(sessionId, { normalize });
      // Further updates come via WebSocket
    } catch (err) {
      setAnalyzing(false);
      setAnalysisError(err.response?.data?.error || err.message);
      setAnalysisMessage('');
    }
  };

  const handleSynthesize = async () => {
    try {
      setSynthesisError('');
      setSynthesisMessage('Sending request…');
      await runSynthesis(sessionId, { provider });
      // Further updates come via WebSocket
    } catch (err) {
      setSynthesizing(false);
      setSynthesisError(err.response?.data?.error || err.message);
      setSynthesisMessage('');
    }
  };

  const insightsReady = pipelineStatus?.insights_available > 0;

  return (
    <div className="pipeline-panel">
      <h3>Analysis Pipeline</h3>

      {/* ── Step 1: Graph Analysis ── */}
      <div className="pipeline-step">
        <div className="pipeline-step-header">Step 1 — Graph Analysis</div>

        <label className="normalize-label" title={NORMALIZE_TOOLTIP}>
          <input
            type="checkbox"
            checked={normalize}
            onChange={(e) => setNormalize(e.target.checked)}
            disabled={analyzing}
          />
          <span>Normalize entity labels</span>
          <span className="tooltip-icon" title={NORMALIZE_TOOLTIP}>ⓘ</span>
        </label>

        <button
          className="pipeline-btn"
          onClick={handleAnalyze}
          disabled={analyzing}
        >
          {analyzing ? '⏳ Analyzing…' : '▶ Analyze Graph'}
        </button>

        {analysisMessage && (
          <p className="pipeline-status-msg">{analysisMessage}</p>
        )}
        {analysisError && (
          <p className="pipeline-error-msg">⚠ {analysisError}</p>
        )}
      </div>

      {/* ── Step 2: Narrative Synthesis ── */}
      <div className="pipeline-step">
        <div className="pipeline-step-header">Step 2 — Career Narratives</div>
        <p className="pipeline-step-note">2 LLM calls · ~30 seconds</p>

        <label className="provider-label">
          Provider:
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            disabled={synthesizing}
          >
            <option value="anthropic">Claude (Anthropic)</option>
            <option value="openai">GPT-4o (OpenAI)</option>
          </select>
        </label>

        <button
          className="pipeline-btn"
          onClick={handleSynthesize}
          disabled={synthesizing || !insightsReady}
          title={!insightsReady ? 'Run Step 1 first' : ''}
        >
          {synthesizing ? '⏳ Generating…' : '▶ Generate Narratives'}
        </button>

        {synthesisMessage && (
          <p className="pipeline-status-msg">{synthesisMessage}</p>
        )}
        {synthesisError && (
          <p className="pipeline-error-msg">⚠ {synthesisError}</p>
        )}
      </div>
    </div>
  );
};

export default AnalysisPipelinePanel;
