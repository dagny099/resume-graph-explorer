/**
 * Resume Upload Component
 *
 * Features:
 * - Drag-and-drop file upload
 * - Upload progress tracking
 * - Real-time extraction progress via WebSocket
 * - Document status display
 */

import React, { useState, useRef } from 'react';
import { uploadDocument, getDocument } from '../services/api';
import wsClient from '../services/websocket';
import './ResumeUpload.css';

const ResumeUpload = ({ sessionId, onUploadComplete, graphData }) => {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [extractionProgress, setExtractionProgress] = useState({});
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);
  // Tracks polling intervals keyed by documentId so they can be cancelled
  const pollingIntervals = useRef({});
  // Guards against calling onUploadComplete twice (WebSocket + polling race)
  const completedDocs = useRef(new Set());

  React.useEffect(() => {
    // Connect WebSocket and join session once connected
    const socket = wsClient.connect();

    if (sessionId) {
      if (wsClient.connected) {
        wsClient.joinSession(sessionId);
      } else if (socket) {
        // Queue join for when connection is established
        socket.once('connect', () => wsClient.joinSession(sessionId));
      }
    }

    // Listen for extraction events
    const handleExtractionStarted = (data) => {
      setExtractionProgress((prev) => ({
        ...prev,
        [data.document_id]: { status: 'processing', progress: 0 },
      }));
    };

    const handleExtractionProgress = (data) => {
      setExtractionProgress((prev) => ({
        ...prev,
        [data.document_id]: {
          status: 'processing',
          progress: data.progress || 50,
        },
      }));
    };

    const handleExtractionComplete = (data) => {
      setExtractionProgress((prev) => ({
        ...prev,
        [data.document_id]: { status: 'complete', progress: 100 },
      }));
      hideAfterComplete(data.document_id);

      // Cancel any polling for this document (WebSocket won the race)
      if (pollingIntervals.current[data.document_id]) {
        clearInterval(pollingIntervals.current[data.document_id]);
        delete pollingIntervals.current[data.document_id];
      }

      if (!completedDocs.current.has(data.document_id)) {
        completedDocs.current.add(data.document_id);
        if (onUploadComplete) onUploadComplete(data);
      }
    };

    const handleExtractionError = (data) => {
      setExtractionProgress((prev) => ({
        ...prev,
        [data.document_id]: { status: 'error', error: data.error },
      }));
    };

    wsClient.on('extraction_started', handleExtractionStarted);
    wsClient.on('extraction_progress', handleExtractionProgress);
    wsClient.on('extraction_complete', handleExtractionComplete);
    wsClient.on('extraction_error', handleExtractionError);

    return () => {
      wsClient.off('extraction_started', handleExtractionStarted);
      wsClient.off('extraction_progress', handleExtractionProgress);
      wsClient.off('extraction_complete', handleExtractionComplete);
      wsClient.off('extraction_error', handleExtractionError);

      // Clean up any active polling intervals
      Object.values(pollingIntervals.current).forEach(clearInterval);
      pollingIntervals.current = {};
    };
  }, [sessionId, onUploadComplete]);

  const hideAfterComplete = (documentId) => {
    setTimeout(() => {
      setExtractionProgress((prev) => {
        const next = { ...prev };
        delete next[documentId];
        return next;
      });
    }, 2000);
  };

  const startPollingForCompletion = (documentId) => {
    // Show extraction progress immediately
    setExtractionProgress((prev) => ({
      ...prev,
      [documentId]: { status: 'processing', progress: 10 },
    }));

    let attempts = 0;
    const maxAttempts = 40; // 40 * 3s = 2 min timeout

    const intervalId = setInterval(async () => {
      attempts++;
      try {
        const docData = await getDocument(documentId);
        const status = docData.document?.status;

        if (status === 'complete') {
          clearInterval(intervalId);
          delete pollingIntervals.current[documentId];

          setExtractionProgress((prev) => ({
            ...prev,
            [documentId]: { status: 'complete', progress: 100 },
          }));
          hideAfterComplete(documentId);

          if (!completedDocs.current.has(documentId)) {
            completedDocs.current.add(documentId);
            if (onUploadComplete) onUploadComplete({ document_id: documentId });
          }
        } else if (status === 'error') {
          clearInterval(intervalId);
          delete pollingIntervals.current[documentId];

          setExtractionProgress((prev) => ({
            ...prev,
            [documentId]: {
              status: 'error',
              // Surface the backend's actual failure reason when available
              error: docData.document?.error_message || 'Extraction failed',
            },
          }));
        } else if (attempts >= maxAttempts) {
          // Timeout — try loading anyway
          clearInterval(intervalId);
          delete pollingIntervals.current[documentId];

          if (!completedDocs.current.has(documentId)) {
            completedDocs.current.add(documentId);
            if (onUploadComplete) onUploadComplete({ document_id: documentId });
          }
        } else {
          // Still processing — animate progress
          setExtractionProgress((prev) => ({
            ...prev,
            [documentId]: {
              status: 'processing',
              progress: Math.min(90, 10 + attempts * 2),
            },
          }));
        }
      } catch {
        // Ignore transient poll errors
      }
    }, 3000);

    pollingIntervals.current[documentId] = intervalId;
  };

  const handleFileSelect = async (files) => {
    if (!files || files.length === 0 || !sessionId) {
      return;
    }

    const file = files[0];

    try {
      setUploading(true);
      setUploadProgress(0);

      const data = await uploadDocument(sessionId, file, setUploadProgress);
      const documentId = data.document?.id;

      console.log('Upload complete:', data);
      setUploading(false);
      setUploadProgress(0);

      // Start polling as fallback — if WebSocket fires first it will cancel the interval
      if (documentId) {
        startPollingForCompletion(documentId);
      }
    } catch (error) {
      console.error('Upload failed:', error);
      alert('Upload failed: ' + (error.response?.data?.error || error.message));
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    handleFileSelect(e.dataTransfer.files);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragOver(false);
  };

  return (
    <div className={`resume-upload ${graphData ? 'compact' : 'full'}`}>
      <div
        className={`upload-area ${graphData ? 'compact' : ''} ${dragOver ? 'drag-over' : ''} ${uploading ? 'uploading' : ''}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => !uploading && fileInputRef.current?.click()}
      >
        {uploading ? (
          <div className="upload-status">
            <p>Uploading...</p>
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${uploadProgress}%` }} />
            </div>
            <p className="progress-text">{uploadProgress}%</p>
          </div>
        ) : graphData ? (
          <div className="upload-prompt-compact">
            <span className="upload-icon-compact">📄</span>
            <span className="upload-text-compact">
              Add another document <span className="upload-hint-inline">(click or drag & drop)</span>
            </span>
          </div>
        ) : (
          <div className="upload-prompt">
            <p className="upload-icon">📄</p>
            <p>Drag & drop a resume file here</p>
            <p className="upload-hint">or click to browse</p>
            <p className="upload-formats">Supported: PDF, DOCX, TXT, MD</p>
          </div>
        )}

        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.doc,.txt,.md"
          onChange={(e) => handleFileSelect(e.target.files)}
          style={{ display: 'none' }}
        />
      </div>

      {Object.keys(extractionProgress).length > 0 && (
        <div className="extraction-status">
          <h4>Extraction Progress</h4>
          {Object.entries(extractionProgress).map(([docId, status]) => (
            <div key={docId} className="extraction-item">
              <div className="extraction-info">
                <span className="doc-id">{docId.substring(0, 8)}...</span>
                <span className={`status-badge status-${status.status}`}>
                  {status.status}
                </span>
              </div>
              {status.status === 'processing' && (
                <div className="progress-bar small">
                  <div
                    className="progress-fill"
                    style={{ width: `${status.progress || 0}%` }}
                  />
                </div>
              )}
              {status.status === 'error' && (
                <p className="error-message">{status.error}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ResumeUpload;
