# Changelog

All notable changes to Resume Explorer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed - UI Optimization (2025-12-17)

#### Export Panel Enhancements
- **Dynamic Entity Type Display**: Export panel now shows all meaningful entity types (Person, Jobs, Organizations, Education, Certifications, Skills) instead of just Documents, Jobs, and Skills
- **2-Column Grid Layout**: Entity types are displayed in a clean 2-column grid for better readability
- **Unknown Entity Exclusion Note**: Added informational note that Unknown entities are excluded from RDF exports
- **Backend Enhancement**: Stats endpoint now includes person count for complete entity reporting

**Files Modified:**
- `backend/resume_explorer/api/routes.py` - Added persons count to stats endpoint
- `frontend/src/components/ExportPanel.jsx` - Dynamic entity type rendering
- `frontend/src/components/ExportPanel.css` - Grid layout styling

#### Session Selector Compact Mode
- **Dropdown Interface**: Converted session list from ~410px vertical list to ~60px compact dropdown selector
- **Space Optimization**: Saves ~350px of sidebar vertical space for graph visualization
- **Progressive Disclosure**: Shows current session when collapsed, expands to show full list on click
- **Maintained Functionality**: All features preserved (create, rename, delete sessions)
- **Active Session Indicator**: Visual checkmark (✓) shows active session in dropdown list
- **Compact Metadata**: Session metadata (document count, timestamp) displayed inline in shorter format

**Files Modified:**
- `frontend/src/components/SessionSelector.jsx` - Complete dropdown UI rewrite
- `frontend/src/components/SessionSelector.css` - Dropdown styling with overlay, hover states

#### Document Upload Compact Mode
- **Conditional Rendering**: Full upload area when session is empty, compact bar when graph exists
- **Space Optimization**: Saves ~150px of content area vertical space when graph is loaded
- **Maintained Functionality**: Drag-and-drop and click-to-browse work in both modes
- **Progressive Disclosure**: Prominent when needed (empty session), subtle when populated

**Files Modified:**
- `frontend/src/components/ResumeUpload.jsx` - Conditional rendering logic
- `frontend/src/App.jsx` - Pass graph data to upload component
- `frontend/src/components/ResumeUpload.css` - Compact mode styling

#### Overall Impact
- **Total Space Saved**: ~500px of vertical space returned to graph visualization
  - Sidebar: ~350px (Session Selector)
  - Content: ~150px (Document Upload)
- **Improved UX**: UI elements are prominent when needed, compact when not
- **Better Focus**: More screen real estate dedicated to the knowledge graph
- **Maintained Accessibility**: All functionality remains easily accessible

---

## [Previous Releases]

(Previous changelog entries would go here)
