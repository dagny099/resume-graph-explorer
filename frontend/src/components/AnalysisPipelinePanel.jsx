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

const BYOK_MODE = import.meta.env.VITE_BYOK_MODE === 'true';

const byokStorageKey = (provider) => `byok_key_${provider}`;

const KEY_LINKS = {
  anthropic: 'https://console.anthropic.com/account/keys',
  openai: 'https://platform.openai.com/api-keys',
};

const PROVIDER_MODELS = {
  anthropic: [
    { id: 'claude-sonnet-4-20250514', label: 'Claude Sonnet 4 (default)' },
    { id: 'claude-opus-4-6',          label: 'Claude Opus 4.6 (most capable)' },
    { id: 'claude-haiku-4-5-20251001', label: 'Claude Haiku 4.5 (fastest)' },
  ],
  openai: [
    { id: 'gpt-4.1-mini', label: 'GPT-4.1 Mini (default)' },
    { id: 'gpt-4o',       label: 'GPT-4o' },
    { id: 'gpt-4o-mini',  label: 'GPT-4o Mini (faster)' },
  ],
};

const AnalysisPipelinePanel = ({
  sessionId,
  pipelineStatus,
  onAnalysisComplete,
  onSynthesisComplete,
}) => {
  const [normalize, setNormalize]           = useState(true);
  const [provider, setProvider]             = useState('anthropic');
  const [analyzing, setAnalyzing]           = useState(false);
  const [synthesizing, setSynthesizing]     = useState(false);
  const [analysisMessage, setAnalysisMessage]     = useState('');
  const [synthesisMessage, setSynthesisMessage]   = useState('');
  const [analysisError, setAnalysisError]         = useState('');
  const [synthesisError, setSynthesisError]       = useState('');
  const [model, setModel]     = useState(PROVIDER_MODELS.anthropic[0].id);
  const [apiKey, setApiKey]   = useState(() =>
    BYOK_MODE ? (sessionStorage.getItem(byokStorageKey('anthropic')) || '') : ''
  );
  const [showKey, setShowKey] = useState(false);

  // WebSocket listeners for pipeline events
  useEffect(() => {
    if (!sessionId) return;

    const handleAnalysisStarted = (data) => {
      if (data.session_id !== sessionId) return;
      setAnalyzing(true);
      setAnalysisError('');
      setAnalysisMessage('Starting analysis…');
    };

    const handleAnalysisProgress = (data) => {
      if (data.session_id !== sessionId) return;
      setAnalysisMessage(data.message || '');
    };

    const handleAnalysisComplete = (data) => {
      if (data.session_id !== sessionId) return;
      setAnalyzing(false);
      setAnalysisMessage(`✓ ${data.insights_count || 6} insights ready`);
      onAnalysisComplete?.();  // calls the prop (App's loadPipelineStatus)
    };

    const handleAnalysisError = (data) => {
      if (data.session_id !== sessionId) return;
      setAnalyzing(false);
      setAnalysisError(data.error || 'Analysis failed');
      setAnalysisMessage('');
    };

    const handleSynthesisStarted = (data) => {
      if (data.session_id !== sessionId) return;
      setSynthesizing(true);
      setSynthesisError('');
      setSynthesisMessage('Starting synthesis…');
    };

    const handleSynthesisProgress = (data) => {
      if (data.session_id !== sessionId) return;
      setSynthesisMessage(data.message || '');
    };

    const handleSynthesisComplete = (data) => {
      if (data.session_id !== sessionId) return;
      setSynthesizing(false);
      setSynthesisMessage('✓ Both narratives ready');
      onSynthesisComplete?.();  // calls the prop (App's loadPipelineStatus)
    };

    const handleSynthesisError = (data) => {
      if (data.session_id !== sessionId) return;
      setSynthesizing(false);
      setSynthesisError(data.error || 'Synthesis failed');
      setSynthesisMessage('');
    };

    wsClient.on('pipeline_analysis_started',  handleAnalysisStarted);
    wsClient.on('pipeline_analysis_progress', handleAnalysisProgress);
    wsClient.on('pipeline_analysis_complete', handleAnalysisComplete);
    wsClient.on('pipeline_analysis_error',    handleAnalysisError);
    wsClient.on('pipeline_synthesis_started',  handleSynthesisStarted);
    wsClient.on('pipeline_synthesis_progress', handleSynthesisProgress);
    wsClient.on('pipeline_synthesis_complete', handleSynthesisComplete);
    wsClient.on('pipeline_synthesis_error',    handleSynthesisError);

    return () => {
      wsClient.off('pipeline_analysis_started',  handleAnalysisStarted);
      wsClient.off('pipeline_analysis_progress', handleAnalysisProgress);
      wsClient.off('pipeline_analysis_complete', handleAnalysisComplete);
      wsClient.off('pipeline_analysis_error',    handleAnalysisError);
      wsClient.off('pipeline_synthesis_started',  handleSynthesisStarted);
      wsClient.off('pipeline_synthesis_progress', handleSynthesisProgress);
      wsClient.off('pipeline_synthesis_complete', handleSynthesisComplete);
      wsClient.off('pipeline_synthesis_error',    handleSynthesisError);
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

  const handleProviderChange = (newProvider) => {
    setProvider(newProvider);
    setModel(PROVIDER_MODELS[newProvider][0].id);
    if (BYOK_MODE) {
      setApiKey(sessionStorage.getItem(byokStorageKey(newProvider)) || '');
    }
  };

  const handleApiKeyChange = (value) => {
    setApiKey(value);
    sessionStorage.setItem(byokStorageKey(provider), value);
  };

  const handleSynthesize = async () => {
    try {
      setSynthesisError('');
      setSynthesisMessage('Sending request…');
      await runSynthesis(sessionId, {
        provider,
        model,
        apiKey: BYOK_MODE ? apiKey.trim() : undefined,
      });
      // Further updates come via WebSocket
    } catch (err) {
      setSynthesizing(false);
      setSynthesisError(err.response?.data?.error || err.message);
      setSynthesisMessage('');
    }
  };

  const insightsReady = pipelineStatus?.insights_available > 0;

  // In BYOK mode, require a key with the expected prefix before enabling synthesis.
  const keyValid = !BYOK_MODE || (
    provider === 'anthropic'
      ? apiKey.trim().startsWith('sk-ant-')
      : apiKey.trim().startsWith('sk-')
  );

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
            onChange={(e) => handleProviderChange(e.target.value)}
            disabled={synthesizing}
          >
            <option value="anthropic">Claude (Anthropic)</option>
            <option value="openai">GPT-4o (OpenAI)</option>
          </select>
        </label>

        <label className="provider-label">
          Model:
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            disabled={synthesizing}
          >
            {PROVIDER_MODELS[provider].map((m) => (
              <option key={m.id} value={m.id}>{m.label}</option>
            ))}
          </select>
        </label>

        {BYOK_MODE && (
          <div className="byok-key-input">
            <label className="byok-key-label">
              API Key:
              <div className="key-input-row">
                <input
                  type={showKey ? 'text' : 'password'}
                  className="byok-key-field"
                  placeholder={provider === 'anthropic' ? 'sk-ant-...' : 'sk-...'}
                  value={apiKey}
                  onChange={(e) => handleApiKeyChange(e.target.value)}
                  disabled={synthesizing}
                  autoComplete="off"
                  spellCheck={false}
                />
                <button
                  type="button"
                  className="key-toggle-btn"
                  onClick={() => setShowKey((v) => !v)}
                  tabIndex={-1}
                >
                  {showKey ? 'Hide' : 'Show'}
                </button>
              </div>
            </label>
            <small className="byok-key-hint">
              Stored for this browser session only.{' '}
              <a href={KEY_LINKS[provider]} target="_blank" rel="noopener noreferrer">
                Get a key
              </a>
            </small>
          </div>
        )}

        <button
          className="pipeline-btn"
          onClick={handleSynthesize}
          disabled={synthesizing || !insightsReady || !keyValid}
          title={
            !insightsReady
              ? 'Run Step 1 first'
              : !keyValid
              ? 'Enter a valid API key above'
              : ''
          }
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
