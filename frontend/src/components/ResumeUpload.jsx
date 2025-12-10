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
import { uploadDocument, getSession } from '../services/api';
import wsClient from '../services/websocket';
import './ResumeUpload.css';

const ResumeUpload = ({ sessionId, onUploadComplete }) => {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [extractionProgress, setExtractionProgress] = useState({});
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);

  React.useEffect(() => {
    // Connect WebSocket
    wsClient.connect();

    if (sessionId) {
      wsClient.joinSession(sessionId);
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

      if (onUploadComplete) {
        onUploadComplete(data);
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
    };
  }, [sessionId, onUploadComplete]);

  const handleFileSelect = async (files) => {
    if (!files || files.length === 0 || !sessionId) {
      return;
    }

    const file = files[0];

    try {
      setUploading(true);
      setUploadProgress(0);

      const data = await uploadDocument(sessionId, file, setUploadProgress);

      console.log('Upload complete:', data);
      setUploading(false);
      setUploadProgress(0);
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
    <div className="resume-upload">
      <div
        className={`upload-area ${dragOver ? 'drag-over' : ''} ${uploading ? 'uploading' : ''}`}
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
