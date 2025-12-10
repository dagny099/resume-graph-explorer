# Resume Explorer - Frontend

Interactive React application for visualizing resume knowledge graphs.

## Features

- **Session Management**: Create and manage multiple extraction sessions
- **Document Upload**: Drag-and-drop resume files (PDF, DOCX, TXT, MD)
- **Real-time Progress**: WebSocket-powered extraction progress tracking
- **Interactive Graph**: Vis.js-based knowledge graph visualization
- **Entity Details**: Click nodes to view detailed information
- **RDF Export**: Export graphs in Turtle, RDF/XML, or JSON-LD formats

## Tech Stack

- React 18
- Vite (build tool)
- Vis.js (graph visualization)
- Axios (HTTP client)
- Socket.IO (WebSocket client)

## Development

### Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:5000`

### Setup

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The app will be available at `http://localhost:3000`

### Build for Production

```bash
npm run build
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/         # React components
│   │   ├── SessionSelector.jsx
│   │   ├── ResumeUpload.jsx
│   │   ├── GraphVisualization.jsx
│   │   ├── EntityPanel.jsx
│   │   └── ExportPanel.jsx
│   ├── services/           # API and WebSocket clients
│   │   ├── api.js
│   │   └── websocket.js
│   ├── App.jsx             # Main app component
│   └── index.jsx           # Entry point
├── package.json
└── vite.config.js
```

## API Endpoints

The frontend communicates with the backend API at `/api/*`:

- `POST /api/sessions` - Create session
- `GET /api/sessions` - List sessions
- `POST /api/sessions/:id/documents` - Upload document
- `GET /api/sessions/:id/graph` - Get Vis.js graph
- `GET /api/sessions/:id/export/:format` - Export RDF

## WebSocket Events

Real-time extraction progress via Socket.IO:

- `extraction_started` - Extraction begins
- `extraction_progress` - Progress updates
- `extraction_complete` - Extraction finished
- `extraction_error` - Extraction failed

## License

MIT
