# Resume Explorer API Reference

Complete API documentation for the Resume Explorer backend.

**Base URL**: `http://localhost:5000`
**API Prefix**: `/api`
**WebSocket Namespace**: `/extraction`

---

## Table of Contents

- [Authentication](#authentication)
- [REST API Endpoints](#rest-api-endpoints)
  - [Health Check](#health-check)
  - [Session Management](#session-management)
  - [Document Upload](#document-upload)
  - [Graph Operations](#graph-operations)
  - [Statistics](#statistics)
- [WebSocket Events](#websocket-events)
- [Error Responses](#error-responses)
- [Rate Limiting](#rate-limiting)

---

## Authentication

**Current Version**: No authentication required (local deployment)

For production deployment, consider adding:
- API keys
- JWT tokens
- OAuth 2.0

---

## REST API Endpoints

### Health Check

#### `GET /health`

Check API server health and LLM availability.

**Response** (200 OK):
```json
{
  "status": "healthy",
  "llm_available": true,
  "sessions": {
    "total_sessions": 5,
    "total_documents": 12,
    "documents_by_status": {
      "complete": 10,
      "processing": 1,
      "pending": 1
    },
    "storage_path": "backend/data/sessions"
  }
}
```

---

## Session Management

### Create Session

#### `POST /api/sessions`

Create a new extraction session.

**Request Body**:
```json
{
  "name": "My Resume Session"  // Optional, auto-generated if omitted
}
```

**Response** (201 Created):
```json
{
  "session": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "name": "My Resume Session",
    "created_at": "2025-12-10T10:30:00Z",
    "updated_at": "2025-12-10T10:30:00Z",
    "documents": [],
    "graph_state_path": null,
    "metadata": {}
  },
  "message": "Session created successfully"
}
```

**Example**:
```bash
curl -X POST http://localhost:5000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"name": "My Resume Session"}'
```

---

### List Sessions

#### `GET /api/sessions`

Get all sessions, sorted by `updated_at` (newest first).

**Response** (200 OK):
```json
{
  "sessions": [
    {
      "id": "session-id-1",
      "name": "My Resume Session",
      "created_at": "2025-12-10T10:30:00Z",
      "updated_at": "2025-12-10T11:45:00Z",
      "document_count": 3,
      "metadata": {}
    },
    {
      "id": "session-id-2",
      "name": "Another Session",
      "created_at": "2025-12-09T14:20:00Z",
      "updated_at": "2025-12-09T15:10:00Z",
      "document_count": 1,
      "metadata": {}
    }
  ],
  "total": 2
}
```

**Example**:
```bash
curl http://localhost:5000/api/sessions
```

---

### Get Session

#### `GET /api/sessions/:id`

Get session details with all documents.

**Parameters**:
- `id` (string) - Session ID

**Response** (200 OK):
```json
{
  "session": {
    "id": "session-id-1",
    "name": "My Resume Session",
    "created_at": "2025-12-10T10:30:00Z",
    "updated_at": "2025-12-10T11:45:00Z",
    "documents": ["doc-id-1", "doc-id-2"],
    "graph_state_path": "/path/to/graph.ttl",
    "metadata": {}
  },
  "documents": [
    {
      "id": "doc-id-1",
      "session_id": "session-id-1",
      "filename": "resume.pdf",
      "upload_date": "2025-12-10T10:35:00Z",
      "file_path": "/path/to/resume.pdf",
      "extracted_entities_path": "/path/to/entities.json",
      "status": "complete",
      "error_message": null,
      "metadata": {}
    }
  ]
}
```

**Response** (404 Not Found):
```json
{
  "error": "Session not found"
}
```

**Example**:
```bash
curl http://localhost:5000/api/sessions/session-id-1
```

---

### Update Session

#### `PUT /api/sessions/:id`

Update session properties (name, metadata).

**Parameters**:
- `id` (string) - Session ID

**Request Body**:
```json
{
  "name": "Updated Session Name",
  "metadata": {
    "category": "engineering",
    "priority": "high"
  }
}
```

**Response** (200 OK):
```json
{
  "session": {
    "id": "session-id-1",
    "name": "Updated Session Name",
    "created_at": "2025-12-10T10:30:00Z",
    "updated_at": "2025-12-10T12:00:00Z",
    "documents": ["doc-id-1"],
    "metadata": {
      "category": "engineering",
      "priority": "high"
    }
  },
  "message": "Session updated successfully"
}
```

**Example**:
```bash
curl -X PUT http://localhost:5000/api/sessions/session-id-1 \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Name"}'
```

---

### Delete Session

#### `DELETE /api/sessions/:id`

Delete session and all associated data (documents, extracted entities, graphs).

**Parameters**:
- `id` (string) - Session ID

**Response** (200 OK):
```json
{
  "message": "Session deleted successfully"
}
```

**Response** (404 Not Found):
```json
{
  "error": "Session not found"
}
```

**Example**:
```bash
curl -X DELETE http://localhost:5000/api/sessions/session-id-1
```

---

## Document Upload

### Upload Document

#### `POST /api/sessions/:id/documents`

Upload a resume document to a session and trigger extraction.

**Parameters**:
- `id` (string) - Session ID

**Request**:
- **Content-Type**: `multipart/form-data`
- **Body**:
  - `file` (file) - Resume file (PDF, DOCX, TXT, MD)

**Supported Formats**:
- `.pdf` - PDF documents
- `.docx`, `.doc` - Microsoft Word
- `.txt` - Plain text
- `.md` - Markdown

**File Size Limit**: 16 MB

**Response** (201 Created):
```json
{
  "document": {
    "id": "doc-id-1",
    "session_id": "session-id-1",
    "filename": "resume.pdf",
    "upload_date": "2025-12-10T10:35:00Z",
    "file_path": "/path/to/resume.pdf",
    "extracted_entities_path": null,
    "status": "processing",
    "error_message": null,
    "metadata": {}
  },
  "message": "Document uploaded, extraction started"
}
```

**Response** (400 Bad Request):
```json
{
  "error": "Unsupported file type. Allowed: .pdf, .docx, .doc, .txt, .md"
}
```

**Response** (413 Payload Too Large):
```json
{
  "error": "File too large (max 16MB)"
}
```

**Example**:
```bash
curl -X POST http://localhost:5000/api/sessions/session-id-1/documents \
  -F "file=@/path/to/resume.pdf"
```

**Notes**:
- Extraction runs asynchronously in background thread
- Real-time progress via WebSocket events (see [WebSocket Events](#websocket-events))
- Document status changes: `pending` → `processing` → `complete` or `error`

---

### Get Document

#### `GET /api/documents/:id`

Get document details.

**Parameters**:
- `id` (string) - Document ID

**Response** (200 OK):
```json
{
  "document": {
    "id": "doc-id-1",
    "session_id": "session-id-1",
    "filename": "resume.pdf",
    "upload_date": "2025-12-10T10:35:00Z",
    "file_path": "/path/to/resume.pdf",
    "extracted_entities_path": "/path/to/entities.json",
    "status": "complete",
    "error_message": null,
    "metadata": {}
  }
}
```

**Example**:
```bash
curl http://localhost:5000/api/documents/doc-id-1
```

---

### Get Document Entities

#### `GET /api/documents/:id/entities`

Get extracted entities for a document.

**Parameters**:
- `id` (string) - Document ID

**Response** (200 OK):
```json
{
  "entities": {
    "person": {
      "id": "person-123",
      "name": "Barbara Hidalgo-Sotelo",
      "email": "barbs@example.com",
      "location": "Austin, TX",
      "summary": "Data Scientist and AI researcher",
      "jobs": ["job-1", "job-2"],
      "skills": ["skill-1", "skill-2"],
      "education": ["edu-1"],
      "certifications": []
    },
    "jobs": [
      {
        "id": "job-1",
        "title": "Data Scientist",
        "organization_id": "org-1",
        "start_date": "2020-01-01",
        "end_date": "2023-12-31",
        "is_current": false,
        "location": "San Francisco, CA",
        "skills_used": ["skill-1", "skill-2"],
        "achievements": ["Improved model accuracy by 25%"]
      }
    ],
    "skills": [
      {
        "id": "skill-1",
        "label": "Python",
        "category": "Technical",
        "proficiency_level": "Expert",
        "years_experience": 5.0,
        "skos_uri": "http://data.europa.eu/esco/skill/..."
      }
    ],
    "education": [...],
    "certifications": [...],
    "organizations": [...],
    "metadata": {
      "source_filename": "resume.pdf",
      "extraction_timestamp": "2025-12-10T10:40:00Z",
      "reasoning": "...",
      "use_dspy": true
    }
  }
}
```

**Response** (404 Not Found):
```json
{
  "error": "No extracted entities found"
}
```

**Example**:
```bash
curl http://localhost:5000/api/documents/doc-id-1/entities
```

---

## Graph Operations

### Get Session Graph

#### `GET /api/sessions/:id/graph`

Get combined knowledge graph for all documents in session (Vis.js format).

**Parameters**:
- `id` (string) - Session ID

**Response** (200 OK):
```json
{
  "nodes": [
    {
      "id": "http://resumeexplorer.org/resource/person-123",
      "label": "Barbara Hidalgo-Sotelo",
      "group": "person",
      "title": "<b>Barbara Hidalgo-Sotelo</b><br><i>Type: person</i><br>Email: barbs@example.com",
      "shape": "diamond",
      "color": {
        "background": "#FF6B6B",
        "border": "#2E7D32"
      },
      "font": {
        "size": 18
      },
      "value": 30,
      "metadata": {
        "uri": "http://resumeexplorer.org/resource/person-123",
        "entity_type": "person",
        "confidence": 1.0
      }
    },
    {
      "id": "http://resumeexplorer.org/resource/job-1",
      "label": "Data Scientist",
      "group": "job",
      "title": "<b>Data Scientist</b><br><i>Type: job</i><br>Organization: Tech Corp",
      "shape": "box",
      "color": {
        "background": "#4ECDC4",
        "border": "#2E7D32"
      },
      "value": 20,
      "metadata": {
        "uri": "http://resumeexplorer.org/resource/job-1",
        "entity_type": "job",
        "confidence": 0.95
      }
    }
  ],
  "edges": [
    {
      "from": "http://resumeexplorer.org/resource/person-123",
      "to": "http://resumeexplorer.org/resource/job-1",
      "label": "has job",
      "arrows": "to",
      "color": "#2E7D32",
      "width": 3,
      "smooth": {
        "type": "curvedCW",
        "roundness": 0.2
      },
      "metadata": {
        "predicate": "http://resumeexplorer.org/ontology#hasJob",
        "edge_type": "ownership"
      }
    }
  ],
  "stats": {
    "node_count": 15,
    "edge_count": 22,
    "entity_type_counts": {
      "person": 1,
      "job": 3,
      "skill": 8,
      "organization": 3
    }
  }
}
```

**Response** (404 Not Found):
```json
{
  "error": "No completed extractions in this session",
  "total_documents": 2,
  "complete_documents": 0
}
```

**Example**:
```bash
curl http://localhost:5000/api/sessions/session-id-1/graph
```

**Notes**:
- Only includes documents with `status: "complete"`
- Combines entities from all documents in session
- Returns Vis.js-compatible format for frontend visualization

---

### Export Session Graph

#### `GET /api/sessions/:id/export/:format`

Export session graph as RDF file.

**Parameters**:
- `id` (string) - Session ID
- `format` (string) - RDF format: `turtle`, `rdfxml`, or `jsonld`

**Response** (200 OK):
- **Content-Type**:
  - `text/turtle` (for turtle)
  - `application/rdf+xml` (for rdfxml)
  - `application/ld+json` (for jsonld)
- **Body**: RDF file content
- **Headers**: `Content-Disposition: attachment; filename="resume-graph.{ext}"`

**Response** (400 Bad Request):
```json
{
  "error": "Invalid format. Use: turtle, rdfxml, or jsonld"
}
```

**Example (Turtle)**:
```bash
curl http://localhost:5000/api/sessions/session-id-1/export/turtle \
  -o resume-graph.ttl
```

**Example (JSON-LD)**:
```bash
curl http://localhost:5000/api/sessions/session-id-1/export/jsonld \
  -o resume-graph.jsonld
```

**Sample Output (Turtle)**:
```turtle
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix schema: <http://schema.org/> .
@prefix resume: <http://resumeexplorer.org/resource/> .
@prefix re: <http://resumeexplorer.org/ontology#> .

resume:person-123 a schema:Person ;
    schema:name "Barbara Hidalgo-Sotelo" ;
    schema:email "barbs@example.com" ;
    re:hasJob resume:job-1 ;
    re:hasSkill resume:skill-python .

resume:job-1 a schema:JobPosting ;
    schema:title "Data Scientist" ;
    schema:hiringOrganization resume:org-1 ;
    re:usedSkill resume:skill-python .

resume:skill-python a <http://data.europa.eu/esco/Skill> ;
    skos:prefLabel "Python" ;
    re:skillCategory "Technical" ;
    re:proficiencyLevel "Expert" .
```

---

### Get Session Statistics

#### `GET /api/sessions/:id/stats`

Get entity statistics for a session.

**Parameters**:
- `id` (string) - Session ID

**Response** (200 OK):
```json
{
  "session_id": "session-id-1",
  "session_name": "My Resume Session",
  "total_documents": 3,
  "documents_by_status": {
    "complete": 2,
    "processing": 1,
    "pending": 0,
    "error": 0
  },
  "total_entities": {
    "jobs": 6,
    "skills": 15,
    "education": 2,
    "certifications": 1,
    "organizations": 4
  }
}
```

**Example**:
```bash
curl http://localhost:5000/api/sessions/session-id-1/stats
```

---

## Statistics

### Get Storage Statistics

#### `GET /api/stats`

Get overall storage statistics.

**Response** (200 OK):
```json
{
  "total_sessions": 5,
  "total_documents": 12,
  "documents_by_status": {
    "complete": 10,
    "processing": 1,
    "pending": 0,
    "error": 1
  },
  "storage_path": "backend/data/sessions"
}
```

**Example**:
```bash
curl http://localhost:5000/api/stats
```

---

## WebSocket Events

Connect to WebSocket namespace `/extraction` for real-time extraction progress.

**Connection URL**: `ws://localhost:5000/socket.io/?transport=websocket`

### Client Events (Emit)

#### `connect`
Client connects to extraction stream.

**Server Response**:
```json
{
  "event": "connected",
  "data": {
    "status": "ready",
    "message": "Connected to extraction stream"
  }
}
```

#### `ping`
Keep-alive ping.

**Payload**:
```json
{
  "timestamp": 1702200000000
}
```

**Server Response**:
```json
{
  "event": "pong",
  "data": {
    "timestamp": 1702200000000
  }
}
```

#### `join_session`
Join a session room for scoped updates.

**Payload**:
```json
{
  "session_id": "session-id-1"
}
```

**Server Response**:
```json
{
  "event": "session_joined",
  "data": {
    "session_id": "session-id-1",
    "status": "joined"
  }
}
```

#### `leave_session`
Leave a session room.

**Payload**:
```json
{
  "session_id": "session-id-1"
}
```

#### `subscribe_document`
Subscribe to updates for specific document.

**Payload**:
```json
{
  "document_id": "doc-id-1"
}
```

**Server Response**:
```json
{
  "event": "subscribed",
  "data": {
    "document_id": "doc-id-1",
    "status": "subscribed"
  }
}
```

#### `cancel_extraction`
Request extraction cancellation (not yet implemented).

**Payload**:
```json
{
  "document_id": "doc-id-1"
}
```

---

### Server Events (Listen)

#### `extraction_started`
Extraction begins for a document.

**Payload**:
```json
{
  "document_id": "doc-id-1",
  "filename": "resume.pdf",
  "session_id": "session-id-1",
  "timestamp": "2025-12-10T10:35:00Z"
}
```

#### `extraction_progress`
Progress update during extraction.

**Payload**:
```json
{
  "document_id": "doc-id-1",
  "stage": "extraction_complete",
  "progress": 50
}
```

**Stages**:
- `extraction_complete` (progress: 50)
- `conversion_complete` (progress: 100)

#### `entity_extracted`
An entity type has been extracted.

**Payload**:
```json
{
  "document_id": "doc-id-1",
  "entity_type": "skills",
  "count": 8
}
```

#### `extraction_complete`
Extraction finished successfully.

**Payload**:
```json
{
  "document_id": "doc-id-1",
  "filename": "resume.pdf",
  "session_id": "session-id-1",
  "entity_count": 25,
  "timestamp": "2025-12-10T10:40:00Z"
}
```

#### `extraction_error`
Extraction failed.

**Payload**:
```json
{
  "document_id": "doc-id-1",
  "filename": "resume.pdf",
  "error": "LLM client not initialized",
  "timestamp": "2025-12-10T10:36:00Z"
}
```

---

### JavaScript Example

```javascript
import { io } from 'socket.io-client';

const socket = io('http://localhost:5000', {
  path: '/socket.io',
  transports: ['websocket', 'polling'],
});

socket.on('connect', () => {
  console.log('Connected to extraction stream');

  // Join session room
  socket.emit('join_session', { session_id: 'session-id-1' });
});

socket.on('extraction_started', (data) => {
  console.log('Extraction started:', data.filename);
});

socket.on('extraction_progress', (data) => {
  console.log(`Progress: ${data.progress}%`);
});

socket.on('extraction_complete', (data) => {
  console.log(`Complete! Extracted ${data.entity_count} entities`);
});

socket.on('extraction_error', (data) => {
  console.error('Error:', data.error);
});
```

---

## Error Responses

All error responses follow this format:

```json
{
  "error": "Error message here"
}
```

### Common HTTP Status Codes

- **200 OK**: Success
- **201 Created**: Resource created successfully
- **400 Bad Request**: Invalid request (missing parameters, invalid format)
- **404 Not Found**: Resource not found
- **413 Payload Too Large**: File exceeds size limit
- **500 Internal Server Error**: Server error

---

## Rate Limiting

**Current Version**: No rate limiting

For production, consider:
- Rate limiting by IP address
- Session-based throttling
- Document upload limits per time window

---

## Notes

- All timestamps are in ISO 8601 format (UTC)
- Document IDs and Session IDs are UUIDs
- File uploads are processed asynchronously
- WebSocket events are broadcast to all connected clients in the same session room
- Extracted entities are cached to avoid re-extraction

---

**Version**: 1.0.0
**Last Updated**: December 10, 2025
