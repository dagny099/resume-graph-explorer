"""
Unit tests for Flask API endpoints

Tests:
- Session management (CRUD)
- Document upload
- Graph retrieval
- Export endpoints
- Error handling
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime

from resume_explorer.api import create_app, SessionStore
from resume_explorer.api.google_services import OAuthToken


@pytest.fixture
def app():
    """Create test Flask app."""
    with tempfile.TemporaryDirectory() as tmpdir:
        app = create_app(config={
            'TESTING': True,
            'DATA_PATH': tmpdir,
            'LLM_PROVIDER': 'claude',
            'ENABLE_DSPY': False
        })

        # Replace LLM client with mock
        app.llm_client = None  # Will cause extraction to fail gracefully

        yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def session_store(app):
    """Get session store from app."""
    return app.session_store


class TestSessionEndpoints:
    """Test session management endpoints."""

    def test_create_session(self, client):
        """Test POST /api/sessions."""
        response = client.post('/api/sessions', json={'name': 'Test Session'})

        assert response.status_code == 201
        data = response.get_json()

        assert 'session' in data
        assert data['session']['name'] == 'Test Session'
        assert 'id' in data['session']

    def test_create_session_auto_name(self, client):
        """Test creating session without name."""
        response = client.post('/api/sessions', json={})

        assert response.status_code == 201
        data = response.get_json()

        # Should have auto-generated name
        assert 'Session' in data['session']['name']

    def test_list_sessions(self, client):
        """Test GET /api/sessions."""
        # Create some sessions
        client.post('/api/sessions', json={'name': 'Session 1'})
        client.post('/api/sessions', json={'name': 'Session 2'})

        response = client.get('/api/sessions')

        assert response.status_code == 200
        data = response.get_json()

        assert 'sessions' in data
        assert data['total'] == 2
        assert len(data['sessions']) == 2

    def test_get_session(self, client):
        """Test GET /api/sessions/<id>."""
        # Create session
        create_response = client.post('/api/sessions', json={'name': 'Test'})
        session_id = create_response.get_json()['session']['id']

        # Get session
        response = client.get(f'/api/sessions/{session_id}')

        assert response.status_code == 200
        data = response.get_json()

        assert data['session']['id'] == session_id
        assert data['session']['name'] == 'Test'
        assert 'documents' in data

    def test_get_nonexistent_session(self, client):
        """Test getting non-existent session."""
        response = client.get('/api/sessions/nonexistent-id')

        assert response.status_code == 404
        assert 'error' in response.get_json()

    def test_update_session(self, client):
        """Test PUT /api/sessions/<id>."""
        # Create session
        create_response = client.post('/api/sessions', json={'name': 'Original'})
        session_id = create_response.get_json()['session']['id']

        # Update session
        response = client.put(
            f'/api/sessions/{session_id}',
            json={'name': 'Updated', 'metadata': {'key': 'value'}}
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data['session']['name'] == 'Updated'
        assert data['session']['metadata']['key'] == 'value'

    def test_delete_session(self, client):
        """Test DELETE /api/sessions/<id>."""
        # Create session
        create_response = client.post('/api/sessions', json={'name': 'To Delete'})
        session_id = create_response.get_json()['session']['id']

        # Delete session
        response = client.delete(f'/api/sessions/{session_id}')

        assert response.status_code == 200

        # Verify deleted
        get_response = client.get(f'/api/sessions/{session_id}')
        assert get_response.status_code == 404


class TestDocumentEndpoints:
    """Test document upload and management endpoints."""

    def test_upload_document(self, client):
        """Test POST /api/sessions/<id>/documents."""
        # Create session
        create_response = client.post('/api/sessions', json={'name': 'Test'})
        session_id = create_response.get_json()['session']['id']

        # Create test file
        data = {
            'file': (Path(__file__).parent / 'fixtures' / 'sample_resume.txt', 'sample.txt')
        }

        # If fixture doesn't exist, create in-memory file
        import io
        data = {
            'file': (io.BytesIO(b"Test resume content"), 'resume.txt')
        }

        response = client.post(
            f'/api/sessions/{session_id}/documents',
            data=data,
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()

        assert 'document' in data
        assert data['document']['filename'] == 'resume.txt'
        assert data['document']['status'] in ['pending', 'processing']

    def test_upload_invalid_file_type(self, client):
        """Test uploading unsupported file type."""
        # Create session
        create_response = client.post('/api/sessions', json={'name': 'Test'})
        session_id = create_response.get_json()['session']['id']

        # Upload invalid file
        import io
        data = {
            'file': (io.BytesIO(b"content"), 'file.xyz')
        }

        response = client.post(
            f'/api/sessions/{session_id}/documents',
            data=data,
            content_type='multipart/form-data'
        )

        assert response.status_code == 400
        assert 'Unsupported' in response.get_json()['error']

    def test_upload_no_file(self, client):
        """Test uploading without file."""
        create_response = client.post('/api/sessions', json={'name': 'Test'})
        session_id = create_response.get_json()['session']['id']

        response = client.post(
            f'/api/sessions/{session_id}/documents',
            data={},
            content_type='multipart/form-data'
        )

        assert response.status_code == 400

    def test_get_document(self, client, session_store):
        """Test GET /api/documents/<id>."""
        # Create session and add document manually
        session = session_store.create_session('Test')

        import io
        document = session_store.add_document(
            session.id,
            'test.txt',
            b"Test content"
        )

        response = client.get(f'/api/documents/{document.id}')

        assert response.status_code == 200
        data = response.get_json()

        assert data['document']['id'] == document.id
        assert data['document']['filename'] == 'test.txt'


class TestGraphEndpoints:
    """Test graph retrieval and export endpoints."""

    def test_get_session_graph_empty(self, client):
        """Test getting graph for session with no completed documents."""
        # Create session
        create_response = client.post('/api/sessions', json={'name': 'Test'})
        session_id = create_response.get_json()['session']['id']

        response = client.get(f'/api/sessions/{session_id}/graph')

        assert response.status_code == 404
        assert 'No completed extractions' in response.get_json()['error']

    def test_get_session_stats(self, client):
        """Test GET /api/sessions/<id>/stats."""
        # Create session
        create_response = client.post('/api/sessions', json={'name': 'Test'})
        session_id = create_response.get_json()['session']['id']

        response = client.get(f'/api/sessions/{session_id}/stats')

        assert response.status_code == 200
        data = response.get_json()

        assert data['session_id'] == session_id
        assert 'total_documents' in data
        assert 'total_entities' in data

    def test_export_session_graph_invalid_format(self, client):
        """Test exporting with invalid format."""
        create_response = client.post('/api/sessions', json={'name': 'Test'})
        session_id = create_response.get_json()['session']['id']

        response = client.get(f'/api/sessions/{session_id}/export/invalid')

        assert response.status_code == 400
        assert 'Invalid format' in response.get_json()['error']


class TestStorageStats:
    """Test storage statistics endpoint."""

    def test_get_storage_stats(self, client):
        """Test GET /api/stats."""
        # Create some sessions
        client.post('/api/sessions', json={'name': 'Session 1'})
        client.post('/api/sessions', json={'name': 'Session 2'})

        response = client.get('/api/stats')

        assert response.status_code == 200
        data = response.get_json()

        assert 'total_sessions' in data
        assert data['total_sessions'] == 2
        assert 'total_documents' in data


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test GET /health."""
        response = client.get('/health')

        assert response.status_code == 200
        data = response.get_json()

        assert data['status'] == 'healthy'
        assert 'llm_available' in data
        assert 'sessions' in data


class TestGoogleIntegration:
    """Test Google OAuth and Drive routes."""

    def test_google_auth_url(self, client):
        """Test POST /api/google/auth returns consent URL."""
        create_response = client.post('/api/sessions', json={'name': 'Google Session'})
        session_id = create_response.get_json()['session']['id']

        response = client.post('/api/google/auth', json={'session_id': session_id})

        assert response.status_code == 200
        data = response.get_json()
        assert 'url' in data
        assert 'client_id' in data['url']

    def test_google_callback_stores_tokens(self, client, app, monkeypatch):
        """Test exchanging code stores tokens."""
        create_response = client.post('/api/sessions', json={'name': 'Google Session'})
        session_id = create_response.get_json()['session']['id']

        fake_token = OAuthToken(
            access_token='access',
            refresh_token='refresh',
            expires_at=datetime.utcnow(),
            scope='scope'
        )

        monkeypatch.setattr(
            app.google_oauth_service,
            'exchange_code_for_tokens',
            lambda code: fake_token
        )

        response = client.post('/api/google/callback', json={
            'code': 'test-code',
            'session_id': session_id
        })

        assert response.status_code == 200
        stored = app.token_store.get_tokens(session_id)
        assert stored is not None
        assert stored.access_token == 'access'

    def test_fetch_google_document(self, client, app, monkeypatch):
        """Test enqueuing a Google document download."""
        create_response = client.post('/api/sessions', json={'name': 'Google Session'})
        session_id = create_response.get_json()['session']['id']

        token = OAuthToken(
            access_token='access',
            refresh_token='refresh',
            expires_at=datetime.utcnow()
        )
        app.token_store.set_tokens(session_id, token)

        monkeypatch.setattr(
            app.google_drive_client,
            'download_file',
            lambda file_id, file_type, token: (b'content', 'FILE123.pdf')
        )

        response = client.post(
            f'/api/sessions/{session_id}/google/fetch',
            json={'url': 'https://docs.google.com/spreadsheets/d/FILE123/edit'}
        )

        assert response.status_code == 201
        data = response.get_json()
        assert 'document' in data
        assert data['document']['filename'] == 'FILE123.pdf'


class TestSessionStore:
    """Test SessionStore directly."""

    def test_session_persistence(self):
        """Test that sessions persist across store instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create session
            store1 = SessionStore(base_path=tmpdir)
            session = store1.create_session('Test Session')
            session_id = session.id

            # Create new store instance
            store2 = SessionStore(base_path=tmpdir)

            # Session should be loaded
            loaded_session = store2.get_session(session_id)
            assert loaded_session is not None
            assert loaded_session.name == 'Test Session'

    def test_document_persistence(self):
        """Test that documents persist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_path=tmpdir)
            session = store.create_session('Test')

            # Add document
            doc = store.add_document(session.id, 'test.txt', b"content")

            # Create new store
            store2 = SessionStore(base_path=tmpdir)

            # Document should be loaded
            loaded_doc = store2.get_document(doc.id)
            assert loaded_doc is not None
            assert loaded_doc.filename == 'test.txt'

    def test_save_and_load_entities(self):
        """Test saving and loading extracted entities."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_path=tmpdir)
            session = store.create_session('Test')
            doc = store.add_document(session.id, 'test.txt', b"content")

            # Save entities
            entities = {
                'person': {'name': 'Test Person'},
                'jobs': [{'title': 'Engineer'}],
                'skills': []
            }

            store.save_extracted_entities(doc.id, entities)

            # Load entities
            loaded = store.load_extracted_entities(doc.id)

            assert loaded is not None
            assert loaded['person']['name'] == 'Test Person'
            assert loaded['jobs'][0]['title'] == 'Engineer'


class TestErrorHandling:
    """Test error handling."""

    def test_404_handler(self, client):
        """Test 404 error handler."""
        response = client.get('/nonexistent')

        assert response.status_code == 404
        assert 'error' in response.get_json()

    def test_large_file_upload(self, client):
        """Test uploading file larger than limit."""
        create_response = client.post('/api/sessions', json={'name': 'Test'})
        session_id = create_response.get_json()['session']['id']

        # Create large file (17MB, over 16MB limit)
        import io
        large_file = io.BytesIO(b"x" * (17 * 1024 * 1024))

        data = {
            'file': (large_file, 'large.txt')
        }

        response = client.post(
            f'/api/sessions/{session_id}/documents',
            data=data,
            content_type='multipart/form-data'
        )

        assert response.status_code == 413


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
