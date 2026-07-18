/**
 * Entity Panel Component
 *
 * Displays details of selected graph node.
 * When sessionId and onNodeUpdated are provided, shows an Edit button
 * that lets users correct the node's label, mark it verified, or add notes.
 * Edits are authoritative: they update the stored session entities so future
 * normalization runs treat the corrected label as canonical.
 */

import React, { useState, useEffect } from 'react';
import { updateEntity } from '../services/api';
import './EntityPanel.css';

// Fields that are computed/immutable — shown read-only even in edit mode
const IMMUTABLE_KEYS = new Set(['id', 'confidence', 'skos_uri', 'source_doc', 'created_at']);

const EntityPanel = ({ selectedNode, sessionId, onNodeUpdated }) => {
  const [editing, setEditing] = useState(false);
  const [draftLabel, setDraftLabel] = useState('');
  const [draftNotes, setDraftNotes] = useState('');
  const [draftVerified, setDraftVerified] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);

  // Reset edit state whenever the selected node changes
  useEffect(() => {
    setEditing(false);
    setSaveError(null);
    if (selectedNode) {
      setDraftLabel(selectedNode.label || '');
      setDraftNotes(selectedNode.metadata?.user_notes || '');
      setDraftVerified(selectedNode.metadata?.user_verified || false);
    }
  }, [selectedNode]);

  if (!selectedNode) {
    return (
      <div className="entity-panel empty">
        <p>Click on a node to view details</p>
      </div>
    );
  }

  const { label, group, metadata, title } = selectedNode;
  const canEdit = !!(sessionId && onNodeUpdated);

  const handleSave = async () => {
    if (!draftLabel.trim()) {
      setSaveError('Label cannot be empty.');
      return;
    }
    setSaving(true);
    setSaveError(null);
    try {
      const patch = {
        label: draftLabel.trim(),
        user_verified: draftVerified,
        user_notes: draftNotes,
      };
      const result = await updateEntity(sessionId, group, selectedNode.id, patch);
      setEditing(false);
      onNodeUpdated(result.entity);
    } catch (err) {
      const msg = err.response?.data?.error || err.message || 'Save failed.';
      setSaveError(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setEditing(false);
    setSaveError(null);
    setDraftLabel(selectedNode.label || '');
    setDraftNotes(selectedNode.metadata?.user_notes || '');
    setDraftVerified(selectedNode.metadata?.user_verified || false);
  };

  // Metadata entries to display (immutable section, shown below edit fields)
  const immutableEntries = metadata
    ? Object.entries(metadata).filter(([k]) => IMMUTABLE_KEYS.has(k) && metadata[k] != null)
    : [];

  return (
    <div className="entity-panel">
      <div className="entity-header">
        <span className={`entity-badge entity-${group}`}>{group}</span>
        <h3>{editing ? draftLabel || <em>editing…</em> : label}</h3>
        {canEdit && !editing && (
          <button className="btn-edit-node" onClick={() => setEditing(true)} title="Edit this node">
            Edit
          </button>
        )}
      </div>

      {!editing && title && (
        <div className="entity-tooltip" dangerouslySetInnerHTML={{ __html: title }} />
      )}

      {editing && (
        <div className="entity-edit-form">
          <label className="edit-field-label">
            Label
            <input
              type="text"
              className="edit-input"
              value={draftLabel}
              onChange={e => setDraftLabel(e.target.value)}
              autoFocus
            />
          </label>

          <label className="edit-field-label">
            Notes
            <textarea
              className="edit-textarea"
              value={draftNotes}
              onChange={e => setDraftNotes(e.target.value)}
              rows={3}
              placeholder="Optional annotation…"
            />
          </label>

          <label className="edit-checkbox-label">
            <input
              type="checkbox"
              checked={draftVerified}
              onChange={e => setDraftVerified(e.target.checked)}
            />
            Mark as verified
          </label>

          {saveError && <p className="edit-error">{saveError}</p>}

          <div className="edit-actions">
            <button className="btn-save" onClick={handleSave} disabled={saving}>
              {saving ? 'Saving…' : 'Save'}
            </button>
            <button className="btn-cancel" onClick={handleCancel} disabled={saving}>
              Cancel
            </button>
          </div>

          {immutableEntries.length > 0 && (
            <div className="entity-immutable">
              <h4>Extraction metadata</h4>
              <dl>
                {immutableEntries.map(([key, value]) => (
                  <div key={key} className="metadata-item">
                    <dt>{key}</dt>
                    <dd>{String(value)}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
        </div>
      )}

      {!editing && metadata && (
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
