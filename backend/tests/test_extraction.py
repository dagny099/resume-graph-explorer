"""
Unit tests for resume extraction pipeline

Tests:
- LLM backend initialization
- DSPy extraction module
- Simplified extraction
- Resume extractor service
- Document text extraction
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import date
import json

from resume_explorer.services.llm_client import (
    LLMBackend, LLMClient, ClaudeBackend, create_llm_client,
)
from resume_explorer.services.extraction_dspy import (
    SimplifiedExtractor,
    create_extraction_pipeline
)
from resume_explorer.services.resume_extractor import ResumeExtractor, ExtractionEvent
from resume_explorer.utils.document_processor import DocumentProcessor
from resume_explorer.models import Person, Job, Skill


class MockLLMBackend(LLMBackend):
    """Mock LLM backend for testing."""

    def __init__(self, response: str = ""):
        self.response = response
        self.call_count = 0

    def generate(self, prompt: str, **kwargs) -> str:
        self.call_count += 1
        return self.response

    def is_available(self) -> bool:
        return True


class TestSimplifiedExtractor:
    """Test simplified (non-DSPy) extraction pipeline."""

    def test_basic_extraction(self):
        """Test extraction with valid LLM response."""
        mock_response = json.dumps({
            "person": {
                "name": "John Doe",
                "email": "john@example.com",
                "location": "Austin, TX",
                "summary": "Software engineer"
            },
            "jobs": [
                {
                    "title": "Software Engineer",
                    "organization_id": "org-1",
                    "start_date": "2020-01-01",
                    "end_date": None,
                    "is_current": True,
                    "skills_used": ["Python", "JavaScript"]
                }
            ],
            "skills": [
                {
                    "label": "Python",
                    "category": "Technical",
                    "proficiency_level": "Expert"
                }
            ],
            "education": [],
            "certifications": [],
            "organizations": [
                {
                    "id": "org-1",
                    "name": "Tech Company",
                    "org_type": "Company"
                }
            ]
        })

        backend = MockLLMBackend(response=mock_response)
        extractor = SimplifiedExtractor(backend)

        resume_text = "John Doe, Software Engineer..."
        result = extractor.extract(resume_text)

        assert result['person']['name'] == "John Doe"
        assert result['person']['email'] == "john@example.com"
        assert len(result['jobs']) == 1
        assert result['jobs'][0]['title'] == "Software Engineer"
        assert len(result['skills']) == 1
        assert result['skills'][0]['label'] == "Python"
        assert backend.call_count == 1

    def test_extraction_with_markdown_response(self):
        """Test handling LLM response wrapped in markdown code blocks."""
        json_data = {
            "person": {"name": "Jane Smith"},
            "jobs": [],
            "skills": [],
            "education": [],
            "certifications": [],
            "organizations": []
        }

        # Wrap response in markdown
        mock_response = f"```json\n{json.dumps(json_data)}\n```"

        backend = MockLLMBackend(response=mock_response)
        extractor = SimplifiedExtractor(backend)

        result = extractor.extract("Resume text...")

        assert result['person']['name'] == "Jane Smith"

    def test_extraction_with_invalid_json_raises(self):
        """Unparseable output must raise (not silently return an empty result).

        A silent empty return marks a failed document as 'complete' with an empty
        graph; raising lets _run_extraction mark it 'error' with a clear message.
        """
        backend = MockLLMBackend(response="This is not JSON")
        extractor = SimplifiedExtractor(backend)

        with pytest.raises(RuntimeError):
            extractor.extract("Resume text...")

    def test_extraction_recovers_from_fenced_and_wrapped_json(self):
        """JSON wrapped in code fences or surrounding prose is still parsed."""
        payload = '{"person": {"name": "Barbara"}, "jobs": [], "skills": ["Python"]}'
        for wrapped in (
            f"```json\n{payload}\n```",
            f"Here is the JSON you requested:\n{payload}\nLet me know if you need more.",
        ):
            extractor = SimplifiedExtractor(MockLLMBackend(response=wrapped))
            result = extractor.extract("Resume text...")
            assert result['person'] == {"name": "Barbara"}
            assert result['skills'] == ["Python"]


class TestProviderFactory:
    """Test create_llm_client provider handling."""

    def test_anthropic_alias_maps_to_claude(self, monkeypatch):
        """'anthropic' is accepted as an alias for 'claude' (previously raised).

        This is what the synthesis pipeline passes; before the alias it always
        threw and silently fell back to the app's default client.
        """
        monkeypatch.setenv("CLAUDE_API_KEY", "sk-ant-test")
        monkeypatch.delenv("CLAUDE_MODEL", raising=False)

        client = create_llm_client(provider="anthropic")

        assert isinstance(client.backend, ClaudeBackend)
        assert client.backend.model_name == "claude-haiku-4-5"

    def test_claude_provider_still_works(self, monkeypatch):
        monkeypatch.setenv("CLAUDE_API_KEY", "sk-ant-test")
        client = create_llm_client(provider="claude")
        assert isinstance(client.backend, ClaudeBackend)


class TestResumeExtractor:
    """Test ResumeExtractor service."""

    def test_entity_conversion(self):
        """Test conversion from raw JSON to entity objects."""
        mock_response = json.dumps({
            "person": {
                "name": "Barbara Hidalgo-Sotelo",
                "email": "barbs@example.com",
                "location": "Austin, TX"
            },
            "jobs": [
                {
                    "title": "Data Scientist",
                    "company": "Tech Corp",
                    "start_date": "2020-01-01",
                    "end_date": "2023-12-31",
                    "is_current": False,
                    "skills_used": ["Python", "Machine Learning"]
                }
            ],
            "skills": [
                {
                    "label": "Python",
                    "category": "Technical",
                    "proficiency_level": "Expert",
                    "years_experience": 5.0
                },
                {
                    "label": "Machine Learning",
                    "category": "Domain"
                }
            ],
            "education": [
                {
                    "degree_type": "PhD",
                    "field_of_study": "Cognitive Science",
                    "institution": "MIT",
                    "start_date": "2005-09-01",
                    "end_date": "2011-06-01"
                }
            ],
            "certifications": [],
            "organizations": [
                {
                    "name": "Tech Corp",
                    "org_type": "Company",
                    "location": "San Francisco, CA"
                },
                {
                    "name": "MIT",
                    "org_type": "University"
                }
            ]
        })

        backend = MockLLMBackend(response=mock_response)
        client = LLMClient(backend)
        extractor = ResumeExtractor(client, use_dspy=False)

        result = extractor.extract_entities(
            resume_text="Resume text...",
            filename="resume.pdf"
        )

        # Check Person entity
        assert isinstance(result['person'], Person)
        assert result['person'].name == "Barbara Hidalgo-Sotelo"
        assert result['person'].email == "barbs@example.com"

        # Check Jobs
        assert len(result['jobs']) == 1
        assert isinstance(result['jobs'][0], Job)
        assert result['jobs'][0].title == "Data Scientist"
        assert result['jobs'][0].start_date == date(2020, 1, 1)
        assert result['jobs'][0].end_date == date(2023, 12, 31)

        # Check Skills
        assert len(result['skills']) == 2
        assert isinstance(result['skills'][0], Skill)
        assert result['skills'][0].label == "Python"
        assert result['skills'][0].proficiency_level == "Expert"
        assert result['skills'][0].years_experience == 5.0

        # Check metadata
        assert result['metadata']['source_filename'] == "resume.pdf"
        assert result['metadata']['use_dspy'] == False

    def test_event_emission(self):
        """Test WebSocket event emission during extraction."""
        mock_response = json.dumps({
            "person": {"name": "Test Person"},
            "jobs": [],
            "skills": [],
            "education": [],
            "certifications": [],
            "organizations": []
        })

        backend = MockLLMBackend(response=mock_response)
        client = LLMClient(backend)

        # Track emitted events
        emitted_events = []

        def mock_emitter(event_name, data):
            emitted_events.append((event_name, data))

        extractor = ResumeExtractor(client, event_emitter=mock_emitter, use_dspy=False)

        extractor.extract_entities(
            resume_text="Resume text...",
            filename="test.pdf"
        )

        # Check that events were emitted
        event_names = [e[0] for e in emitted_events]

        assert ExtractionEvent.STARTED in event_names
        assert ExtractionEvent.PROGRESS in event_names
        assert ExtractionEvent.COMPLETE in event_names

    def test_date_parsing(self):
        """Test various date format parsing."""
        mock_response = json.dumps({
            "person": {"name": "Test"},
            "jobs": [
                {
                    "title": "Job 1",
                    "start_date": "2020-01-15",  # Full date
                    "end_date": "2023-06"  # Year-month
                },
                {
                    "title": "Job 2",
                    "start_date": "2019",  # Year only
                    "end_date": "Present"  # Current position
                }
            ],
            "skills": [],
            "education": [],
            "certifications": [],
            "organizations": []
        })

        backend = MockLLMBackend(response=mock_response)
        client = LLMClient(backend)
        extractor = ResumeExtractor(client, use_dspy=False)

        result = extractor.extract_entities("Resume...", "resume.pdf")

        jobs = result['jobs']

        # Job 1
        assert jobs[0].start_date == date(2020, 1, 15)
        assert jobs[0].end_date == date(2023, 6, 1)

        # Job 2
        assert jobs[1].start_date == date(2019, 1, 1)
        assert jobs[1].end_date is None  # "Present" should be None


class TestDocumentProcessor:
    """Test document text extraction."""

    def test_text_file_extraction(self, tmp_path):
        """Test extracting text from .txt file."""
        test_file = tmp_path / "test.txt"
        test_content = "This is a test resume.\n\nJohn Doe\nSoftware Engineer"
        test_file.write_text(test_content)

        result = DocumentProcessor.extract_text(str(test_file))

        assert result == test_content

    def test_markdown_file_extraction(self, tmp_path):
        """Test extracting text from .md file."""
        test_file = tmp_path / "resume.md"
        test_content = "# Barbara Hidalgo-Sotelo\n\n## Experience\n\nData Scientist"
        test_file.write_text(test_content)

        result = DocumentProcessor.extract_text(str(test_file))

        assert result == test_content

    def test_unsupported_format(self, tmp_path):
        """Test handling unsupported file format."""
        test_file = tmp_path / "test.xyz"
        test_file.write_text("content")

        with pytest.raises(ValueError, match="Unsupported file format"):
            DocumentProcessor.extract_text(str(test_file))

    def test_file_not_found(self):
        """Test handling missing file."""
        with pytest.raises(FileNotFoundError):
            DocumentProcessor.extract_text("/nonexistent/file.txt")

    def test_extract_text_from_bytes(self):
        """Test extracting text from bytes."""
        content = "Resume content"
        file_bytes = content.encode('utf-8')

        result = DocumentProcessor.extract_text_from_bytes(file_bytes, "resume.txt")

        assert result == content

    def test_get_document_metadata(self, tmp_path):
        """Test extracting document metadata."""
        test_file = tmp_path / "resume.pdf"
        test_file.write_text("Test content")

        metadata = DocumentProcessor.get_document_metadata(str(test_file))

        assert metadata['filename'] == "resume.pdf"
        assert metadata['extension'] == ".pdf"
        assert metadata['size_bytes'] > 0
        assert metadata['size_kb'] > 0


class TestExtractionPipeline:
    """Test extraction pipeline factory."""

    def test_create_simplified_pipeline(self):
        """Test creating simplified extraction pipeline."""
        backend = MockLLMBackend()

        pipeline = create_extraction_pipeline(backend, use_dspy=False)

        assert isinstance(pipeline, SimplifiedExtractor)

    @patch('resume_explorer.services.extraction_dspy.dspy')
    def test_create_dspy_pipeline(self, mock_dspy):
        """DSPy pipeline creation defers dspy.settings.configure to the worker thread."""
        backend = MockLLMBackend()

        # Mock DSPy settings
        mock_dspy.settings.configure = Mock()

        pipeline = create_extraction_pipeline(backend, use_dspy=True)

        # DSPy is configured lazily inside the extraction worker thread to
        # avoid the known dspy.settings threading issues — creating the
        # pipeline must NOT touch global settings.
        mock_dspy.settings.configure.assert_not_called()
        assert not isinstance(pipeline, SimplifiedExtractor)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
