"""
Regression tests for graph analysis cache freshness (stale-cache bug).

Bug: PipelineService cached sessions/{id}/graph.jsonld and reused it whenever
the file existed. If a user ran analysis, then uploaded or re-extracted another
document in the same session, the next analysis silently reused the old graph.

Fix: PipelineService._ensure_jsonld() rebuilds the cache whenever any completed
document's extracted-entities file is newer than the cached graph.jsonld
(see PipelineService._cache_is_fresh).

These tests exercise the cache logic directly (no LLM, no network, no graph
analysis) so they are fast and deterministic. They would pass trivially if the
old "reuse whenever the file exists" behavior were restored ONLY for the
happy-path test — the stale-cache tests below fail under the old behavior.
"""

import os

import pytest
from rdflib import Graph
from rdflib.namespace import RDF

from resume_explorer.api import SessionStore
from resume_explorer.graph import EntityType
from resume_explorer.models import Organization, Person, Skill
from resume_explorer.services.pipeline_service import PipelineService

from tests.test_session_graph import make_full_entity_set


def make_second_doc_entities():
    """A second document introducing a distinctive skill and organization."""
    return {
        'person': Person(id="person-1", label="Test Person", name="Test Person",
                         skills=["skill-rust"]),
        'jobs': [],
        'skills': [Skill(id="skill-rust", label="Rust", category="Technical")],
        'education': [],
        'certifications': [],
        'organizations': [
            Organization(id="org-startup", name="New Startup",
                         label="New Startup", org_type="Company"),
        ],
    }


@pytest.fixture
def store_and_service(tmp_path):
    """SessionStore + PipelineService sharing a temp data dir, one completed doc."""
    store = SessionStore(base_path=str(tmp_path))
    service = PipelineService(session_store=store, data_path=str(tmp_path))
    session = store.create_session(name="Cache Test")
    doc = store.add_document(session.id, "resume.txt", b"stub resume text")
    store.save_extracted_entities(doc.id, make_full_entity_set())
    store.update_document_status(doc.id, 'complete')
    return store, service, session.id


def _skill_labels(jsonld_path):
    """Return skill entity labels present in the cached graph."""
    g = Graph()
    g.parse(str(jsonld_path), format='json-ld')
    labels = set()
    for skill in g.subjects(RDF.type, EntityType.SKILL):
        for label in g.objects(skill, None):
            labels.add(str(label))
    return labels


def _touch_newer(path, reference_path, delta=10):
    """Force `path`'s mtime to be strictly newer than `reference_path`.

    Guards against coarse (1-second) filesystem mtime resolution so the test is
    deterministic regardless of how fast the writes happened.
    """
    ref_mtime = os.stat(reference_path).st_mtime
    os.utime(path, (ref_mtime + delta, ref_mtime + delta))


class TestCacheFreshness:
    def test_builds_cache_when_missing(self, store_and_service):
        store, service, session_id = store_and_service
        jsonld_path = service._jsonld_path(session_id)
        assert not jsonld_path.exists()

        built = service._ensure_jsonld(session_id)
        assert built == jsonld_path
        assert jsonld_path.exists()

    def test_reuses_fresh_cache_without_rebuilding(self, store_and_service):
        store, service, session_id = store_and_service
        jsonld_path = service._ensure_jsonld(session_id)
        first_mtime = jsonld_path.stat().st_mtime

        # Nothing changed → the same cache file must be reused, not rewritten.
        assert service._cache_is_fresh(jsonld_path, session_id) is True
        service._ensure_jsonld(session_id)
        assert jsonld_path.stat().st_mtime == first_mtime

    def test_new_completed_document_marks_cache_stale(self, store_and_service):
        store, service, session_id = store_and_service
        jsonld_path = service._ensure_jsonld(session_id)

        # A second document completes AFTER the graph was cached.
        doc2 = store.add_document(session_id, "resume2.txt", b"second resume")
        entities_path = store.save_extracted_entities(doc2.id, make_second_doc_entities())
        store.update_document_status(doc2.id, 'complete')
        _touch_newer(entities_path, jsonld_path)

        assert service._cache_is_fresh(jsonld_path, session_id) is False

    def test_stale_cache_is_rebuilt_with_new_entities(self, store_and_service):
        store, service, session_id = store_and_service
        jsonld_path = service._ensure_jsonld(session_id)
        assert 'Rust' not in _skill_labels(jsonld_path)

        doc2 = store.add_document(session_id, "resume2.txt", b"second resume")
        entities_path = store.save_extracted_entities(doc2.id, make_second_doc_entities())
        store.update_document_status(doc2.id, 'complete')
        _touch_newer(entities_path, jsonld_path)

        rebuilt = service._ensure_jsonld(session_id)
        # The stale cache must have been rebuilt to include the new document.
        assert 'Rust' in _skill_labels(rebuilt), (
            "Analysis reused a stale graph cache and missed the new document"
        )

    def test_re_extracting_existing_document_marks_cache_stale(self, store_and_service):
        """Re-extraction rewrites the same doc's entities file; cache must rebuild."""
        store, service, session_id = store_and_service
        jsonld_path = service._ensure_jsonld(session_id)
        assert 'Rust' not in _skill_labels(jsonld_path)

        # Re-extract the original document with different entities.
        doc = store.get_session_documents(session_id)[0]
        entities_path = store.save_extracted_entities(doc.id, make_second_doc_entities())
        store.update_document_status(doc.id, 'complete')
        _touch_newer(entities_path, jsonld_path)

        assert service._cache_is_fresh(jsonld_path, session_id) is False
        rebuilt = service._ensure_jsonld(session_id)
        assert 'Rust' in _skill_labels(rebuilt)
