/**
 * API Client for Resume Explorer Backend
 *
 * Provides methods for:
 * - Session management
 * - Document upload
 * - Graph retrieval
 * - Export operations
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ============================================================================
// Session Management
// ============================================================================

export const listSessions = async () => {
  const response = await api.get('/sessions');
  return response.data;
};

export const createSession = async (name) => {
  const response = await api.post('/sessions', { name });
  return response.data;
};

export const getSession = async (sessionId) => {
  const response = await api.get(`/sessions/${sessionId}`);
  return response.data;
};

export const updateSession = async (sessionId, data) => {
  const response = await api.put(`/sessions/${sessionId}`, data);
  return response.data;
};

export const deleteSession = async (sessionId) => {
  const response = await api.delete(`/sessions/${sessionId}`);
  return response.data;
};

export const getSessionStats = async (sessionId) => {
  const response = await api.get(`/sessions/${sessionId}/stats`);
  return response.data;
};

// ============================================================================
// Document Management
// ============================================================================

export const uploadDocument = async (sessionId, file, onProgress) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post(
    `/sessions/${sessionId}/documents`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onProgress(percentCompleted);
        }
      },
    }
  );

  return response.data;
};

export const getDocument = async (documentId) => {
  const response = await api.get(`/documents/${documentId}`);
  return response.data;
};

export const getDocumentEntities = async (documentId) => {
  const response = await api.get(`/documents/${documentId}/entities`);
  return response.data;
};

// ============================================================================
// Graph Operations
// ============================================================================

export const getSessionGraph = async (sessionId) => {
  const response = await api.get(`/sessions/${sessionId}/graph`);
  return response.data;
};

/** Sanitize a person name into a safe filename prefix (e.g. "José O'Brien Jr." → "jose-obrien-jr"). */
function sanitizeNameForFilename(name) {
  if (!name) return null;
  return name
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '') // strip diacritics
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')  // non-alphanumeric → hyphen
    .replace(/^-+|-+$/g, '')       // trim leading/trailing hyphens
    || null;
}

export const exportSessionGraph = async (sessionId, format = 'turtle', personName = null) => {
  const response = await api.get(`/sessions/${sessionId}/export/${format}`, {
    responseType: 'blob',
  });

  // Create download link
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;

  const extension = format === 'turtle' ? 'ttl' : format === 'rdfxml' ? 'rdf' : 'jsonld';
  const slug = sanitizeNameForFilename(personName);
  const basename = slug ? `${slug}_resume-graph` : 'resume-graph';
  link.setAttribute('download', `${basename}.${extension}`);

  document.body.appendChild(link);
  link.click();
  link.remove();

  window.URL.revokeObjectURL(url);
};

// ============================================================================
// Analysis Pipeline
// ============================================================================

export const getPipelineStatus = async (sessionId) => {
  const response = await api.get(`/sessions/${sessionId}/pipeline/status`);
  return response.data;
};

export const runGraphAnalysis = async (sessionId, options = {}) => {
  const response = await api.post(`/sessions/${sessionId}/pipeline/analyze`, options);
  return response.data;
};

export const runSynthesis = async (sessionId, options = {}) => {
  const response = await api.post(`/sessions/${sessionId}/pipeline/synthesize`, options);
  return response.data;
};

export const getInsights = async (sessionId) => {
  const response = await api.get(`/sessions/${sessionId}/insights`);
  return response.data;
};

export const getInsight = async (sessionId, analysisType) => {
  const response = await api.get(`/sessions/${sessionId}/insights/${analysisType}`);
  return response.data;
};

export const getNarratives = async (sessionId) => {
  const response = await api.get(`/sessions/${sessionId}/narratives`);
  return response.data;
};

// ============================================================================
// Statistics
// ============================================================================

export const getStorageStats = async () => {
  const response = await api.get('/stats');
  return response.data;
};

export const getHealth = async () => {
  const response = await axios.get('/health');
  return response.data;
};

export default api;
