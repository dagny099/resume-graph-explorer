"""
Session Storage and Persistence Layer

Manages resume extraction sessions with multi-document support.
Uses JSON-based file storage for local deployment.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from collections import defaultdict

from ..utils.logger import logger


@dataclass
class Document:
    """Represents a document within a session."""
    id: str
    session_id: str
    filename: str
    upload_date: datetime
    file_path: str
    extracted_entities_path: Optional[str] = None
    status: str = "pending"  # pending, processing, complete, error
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Export as dictionary with ISO datetime."""
        data = asdict(self)
        data['upload_date'] = self.upload_date.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Document':
        """Create from dictionary."""
        data = data.copy()
        data['upload_date'] = datetime.fromisoformat(data['upload_date'])
        return cls(**data)


@dataclass
class Session:
    """Represents an extraction session."""
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    documents: List[str] = field(default_factory=list)  # Document IDs
    graph_state_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Export as dictionary with ISO datetime."""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        """Create from dictionary."""
        data = data.copy()
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)


class SessionStore:
    """
    File-based session storage manager.

    Storage structure:
    data/
    ├── sessions/
    │   ├── session-{uuid}/
    │   │   ├── metadata.json
    │   │   ├── documents/
    │   │   │   ├── {filename}
    │   │   ├── extracted/
    │   │   │   ├── doc-{uuid}.json
    │   │   ├── graph.ttl
    │   │   ├── graph.rdf
    │   │   └── graph.jsonld
    └── sessions.index.json
    """

    def __init__(self, base_path: str = "backend/data"):
        """
        Initialize session store.

        Args:
            base_path: Base directory for data storage
        """
        self.base_path = Path(base_path)
        self.sessions_path = self.base_path / "sessions"
        self.index_path = self.base_path / "sessions.index.json"

        # Create directories
        self.sessions_path.mkdir(parents=True, exist_ok=True)

        # Load or create index
        self._index: Dict[str, Session] = {}
        self._documents: Dict[str, Document] = {}
        self._load_index()

        logger.info(f"SessionStore initialized: {self.sessions_path}")

    def _load_index(self):
        """Load session index from disk."""
        if self.index_path.exists():
            try:
                with open(self.index_path, 'r') as f:
                    data = json.load(f)

                # Load sessions
                for session_data in data.get('sessions', []):
                    session = Session.from_dict(session_data)
                    self._index[session.id] = session

                # Load documents
                for doc_data in data.get('documents', []):
                    doc = Document.from_dict(doc_data)
                    self._documents[doc.id] = doc

                logger.info(f"Loaded {len(self._index)} sessions, {len(self._documents)} documents")

            except Exception as e:
                logger.error(f"Failed to load session index: {e}")
                self._index = {}
                self._documents = {}
        else:
            logger.info("No existing session index found")

    def _save_index(self):
        """Save session index to disk."""
        try:
            data = {
                'sessions': [s.to_dict() for s in self._index.values()],
                'documents': [d.to_dict() for d in self._documents.values()],
                'last_updated': datetime.now().isoformat()
            }

            with open(self.index_path, 'w') as f:
                json.dump(data, f, indent=2)

            logger.debug("Session index saved")

        except Exception as e:
            logger.error(f"Failed to save session index: {e}")

    def create_session(self, name: Optional[str] = None) -> Session:
        """
        Create new session.

        Args:
            name: Session name (auto-generated if not provided)

        Returns:
            Created session
        """
        session_id = str(uuid.uuid4())
        now = datetime.now()

        if not name:
            name = f"Session {now.strftime('%Y-%m-%d %H:%M')}"

        session = Session(
            id=session_id,
            name=name,
            created_at=now,
            updated_at=now
        )

        # Create session directory
        session_dir = self._get_session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "documents").mkdir(exist_ok=True)
        (session_dir / "extracted").mkdir(exist_ok=True)

        # Save session metadata
        self._save_session_metadata(session)

        # Add to index
        self._index[session_id] = session
        self._save_index()

        logger.info(f"Created session: {session_id} - {name}")
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session or None if not found
        """
        return self._index.get(session_id)

    def list_sessions(self) -> List[Session]:
        """
        Get all sessions.

        Returns:
            List of sessions sorted by updated_at (newest first)
        """
        sessions = list(self._index.values())
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions

    def update_session(self, session_id: str, **kwargs) -> Optional[Session]:
        """
        Update session properties.

        Args:
            session_id: Session identifier
            **kwargs: Properties to update (name, metadata)

        Returns:
            Updated session or None if not found
        """
        session = self._index.get(session_id)
        if not session:
            return None

        # Update properties
        if 'name' in kwargs:
            session.name = kwargs['name']
        if 'metadata' in kwargs:
            session.metadata.update(kwargs['metadata'])

        session.updated_at = datetime.now()

        # Save metadata
        self._save_session_metadata(session)
        self._save_index()

        logger.info(f"Updated session: {session_id}")
        return session

    def delete_session(self, session_id: str) -> bool:
        """
        Delete session and all its data.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        session = self._index.get(session_id)
        if not session:
            return False

        # Delete session directory
        session_dir = self._get_session_dir(session_id)
        if session_dir.exists():
            import shutil
            shutil.rmtree(session_dir)

        # Remove documents from index
        for doc_id in session.documents:
            self._documents.pop(doc_id, None)

        # Remove session from index
        self._index.pop(session_id)
        self._save_index()

        logger.info(f"Deleted session: {session_id}")
        return True

    def add_document(
        self,
        session_id: str,
        filename: str,
        file_bytes: bytes
    ) -> Optional[Document]:
        """
        Add document to session.

        Args:
            session_id: Session identifier
            filename: Original filename
            file_bytes: File content

        Returns:
            Created document or None if session not found
        """
        session = self._index.get(session_id)
        if not session:
            return None

        doc_id = str(uuid.uuid4())

        # Save file
        file_path = self._get_session_dir(session_id) / "documents" / filename
        file_path.write_bytes(file_bytes)

        # Create document
        document = Document(
            id=doc_id,
            session_id=session_id,
            filename=filename,
            upload_date=datetime.now(),
            file_path=str(file_path),
            status="pending"
        )

        # Add to session
        session.documents.append(doc_id)
        session.updated_at = datetime.now()

        # Save
        self._documents[doc_id] = document
        self._save_session_metadata(session)
        self._save_index()

        logger.info(f"Added document {doc_id} to session {session_id}: {filename}")
        return document

    def get_document(self, document_id: str) -> Optional[Document]:
        """Get document by ID."""
        return self._documents.get(document_id)

    def get_session_documents(self, session_id: str) -> List[Document]:
        """Get all documents for a session."""
        session = self._index.get(session_id)
        if not session:
            return []

        return [
            self._documents[doc_id]
            for doc_id in session.documents
            if doc_id in self._documents
        ]

    def update_document_status(
        self,
        document_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> Optional[Document]:
        """
        Update document processing status.

        Args:
            document_id: Document identifier
            status: New status (pending, processing, complete, error)
            error_message: Error message if status is error

        Returns:
            Updated document or None if not found
        """
        document = self._documents.get(document_id)
        if not document:
            return None

        document.status = status
        if error_message:
            document.error_message = error_message

        # Update session timestamp
        session = self._index.get(document.session_id)
        if session:
            session.updated_at = datetime.now()
            self._save_session_metadata(session)

        self._save_index()
        return document

    def save_extracted_entities(
        self,
        document_id: str,
        entities: Dict[str, Any]
    ) -> Optional[str]:
        """
        Save extracted entities for a document.

        Args:
            document_id: Document identifier
            entities: Extracted entities dictionary

        Returns:
            Path to saved entities file or None if document not found
        """
        document = self._documents.get(document_id)
        if not document:
            return None

        # Save entities to JSON
        extracted_dir = self._get_session_dir(document.session_id) / "extracted"
        entities_path = extracted_dir / f"{document_id}.json"

        with open(entities_path, 'w') as f:
            json.dump(entities, f, indent=2, default=str)

        # Update document
        document.extracted_entities_path = str(entities_path)
        self._save_index()

        logger.info(f"Saved extracted entities for document {document_id}")
        return str(entities_path)

    def load_extracted_entities(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Load extracted entities for a document.

        Args:
            document_id: Document identifier

        Returns:
            Entities dictionary or None if not found
        """
        document = self._documents.get(document_id)
        if not document or not document.extracted_entities_path:
            return None

        try:
            with open(document.extracted_entities_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load entities for document {document_id}: {e}")
            return None

    def get_session_graph_path(self, session_id: str, format: str = "turtle") -> Path:
        """
        Get path for session graph file.

        Args:
            session_id: Session identifier
            format: RDF format (turtle, rdfxml, jsonld)

        Returns:
            Path to graph file
        """
        session_dir = self._get_session_dir(session_id)

        extension_map = {
            'turtle': 'ttl',
            'rdfxml': 'rdf',
            'jsonld': 'jsonld'
        }

        ext = extension_map.get(format, 'ttl')
        return session_dir / f"graph.{ext}"

    def _get_session_dir(self, session_id: str) -> Path:
        """Get session directory path."""
        return self.sessions_path / session_id

    def _save_session_metadata(self, session: Session):
        """Save session metadata to disk."""
        session_dir = self._get_session_dir(session.id)
        metadata_path = session_dir / "metadata.json"

        with open(metadata_path, 'w') as f:
            json.dump(session.to_dict(), f, indent=2)

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        total_documents = len(self._documents)
        docs_by_status = defaultdict(int)

        for doc in self._documents.values():
            docs_by_status[doc.status] += 1

        return {
            'total_sessions': len(self._index),
            'total_documents': total_documents,
            'documents_by_status': dict(docs_by_status),
            'storage_path': str(self.sessions_path)
        }


__all__ = ['Session', 'Document', 'SessionStore']
