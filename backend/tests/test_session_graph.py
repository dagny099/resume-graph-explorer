"""
Tests for the shared session graph builder and RDF export completeness.

Covers:
- collect_session_entities gathers every entity type from a session
- build_session_graph produces a graph containing all six entity types
- JSON-LD / Turtle / RDF/XML exports carry the same complete content
- Relationships (person→job, job→org, person→education, person→cert)
  survive serialization round-trips
- The /export API route produces complete RDF (regression test for the
  export route that used to drop education/certifications/organizations)
"""

import pytest
from datetime import date
from pathlib import Path

from rdflib import Graph
from rdflib.namespace import RDF

from resume_explorer.api import create_app, SessionStore
from resume_explorer.graph import EntityType, RE, RESUME, SCHEMA
from resume_explorer.graph.session_graph import (
    build_graph_from_collected,
    build_session_graph,
    collect_session_entities,
    extracted_entity_counts,
)
from resume_explorer.models import (
    Certification, Education, Job, Organization, Person, Skill,
)


def make_full_entity_set():
    """Representative extraction result covering all six entity types."""
    org = Organization(id="org-tech", name="Tech Corp", label="Tech Corp", org_type="Company")
    university = Organization(id="org-uni", name="State University", label="State University", org_type="University")
    skill = Skill(id="skill-python", label="Python", category="Technical")
    job = Job(
        id="job-1",
        label="Data Scientist",
        title="Data Scientist",
        organization_id="org-tech",
        start_date=date(2020, 1, 1),
        end_date=date(2023, 6, 30),
        skills_used=["skill-python"],
        technologies_used=["Python"],
    )
    education = Education(
        id="edu-1",
        label="PhD in Cognitive Science",
        degree_type="PhD",
        field_of_study="Cognitive Science",
        institution_id="org-uni",
    )
    cert = Certification(
        id="cert-1",
        label="AWS Solutions Architect",
        name="AWS Solutions Architect",
        issuing_organization="Amazon Web Services",
    )
    person = Person(
        id="person-1",
        label="Test Person",
        name="Test Person",
        jobs=["job-1"],
        skills=["skill-python"],
        education=["edu-1"],
        certifications=["cert-1"],
    )
    return {
        'person': person,
        'jobs': [job],
        'skills': [skill],
        'education': [education],
        'certifications': [cert],
        'organizations': [org, university],
    }


@pytest.fixture
def store_with_session(tmp_path):
    """SessionStore in a temp dir with one completed document."""
    store = SessionStore(base_path=str(tmp_path))
    session = store.create_session(name="Test Session")
    doc = store.add_document(session.id, "resume.txt", b"stub resume text")
    store.save_extracted_entities(doc.id, make_full_entity_set())
    store.update_document_status(doc.id, 'complete')
    return store, session.id


ALL_ENTITY_TYPES = {
    'person': EntityType.PERSON,
    'job': EntityType.JOB,
    'skill': EntityType.SKILL,
    'education': EntityType.EDUCATION,
    'certification': EntityType.CERTIFICATION,
    'organization': EntityType.ORGANIZATION,
}


def assert_all_types_present(graph: Graph):
    """Assert the graph has at least one subject of every entity type."""
    for name, type_uri in ALL_ENTITY_TYPES.items():
        subjects = list(graph.subjects(RDF.type, type_uri))
        assert subjects, f"No {name} entities in graph"


class TestCollectSessionEntities:
    def test_collects_all_types(self, store_with_session):
        store, session_id = store_with_session
        collected = collect_session_entities(store, session_id)

        assert collected is not None
        assert len(collected['persons']) == 1
        assert len(collected['jobs']) == 1
        assert len(collected['skills']) == 1
        assert len(collected['education']) == 1
        assert len(collected['certifications']) == 1
        assert len(collected['organizations']) == 2

    def test_returns_none_without_completed_docs(self, tmp_path):
        store = SessionStore(base_path=str(tmp_path))
        session = store.create_session(name="Empty")
        assert collect_session_entities(store, session.id) is None

    def test_extracted_counts(self, store_with_session):
        store, session_id = store_with_session
        collected = collect_session_entities(store, session_id)
        counts = extracted_entity_counts(collected)
        assert counts == {
            'person': 1, 'job': 1, 'skill': 1,
            'education': 1, 'certification': 1, 'organization': 2,
        }


class TestBuildSessionGraph:
    def test_graph_contains_all_entity_types(self, store_with_session):
        store, session_id = store_with_session
        builder, _ = build_session_graph(store, session_id)
        assert_all_types_present(builder.graph)

    def test_relationships_present(self, store_with_session):
        store, session_id = store_with_session
        builder, _ = build_session_graph(store, session_id)
        g = builder.graph

        person = RESUME["person-1"]
        assert (person, RE.hasJob, RESUME["job-1"]) in g
        assert (person, RE.hasSkill, RESUME["skill-python"]) in g
        assert (person, SCHEMA.alumniOf, RESUME["edu-1"]) in g
        assert (person, RE.hasCertification, RESUME["cert-1"]) in g
        assert (RESUME["job-1"], SCHEMA.hiringOrganization, RESUME["org-tech"]) in g
        assert (RESUME["edu-1"], SCHEMA.recognizedBy, RESUME["org-uni"]) in g


class TestExportCompleteness:
    """All three RDF export formats must carry the same complete content."""

    FORMATS = [('turtle', 'turtle'), ('xml', 'xml'), ('json-ld', 'json-ld')]

    def export_and_reparse(self, builder, tmp_path, fmt):
        path = tmp_path / f"graph.{fmt.replace('/', '')}"
        if fmt == 'turtle':
            builder.export_turtle(str(path))
        elif fmt == 'xml':
            builder.export_rdfxml(str(path))
        else:
            builder.export_jsonld(str(path))
        g = Graph()
        g.parse(str(path), format=fmt)
        return g

    @pytest.mark.parametrize("fmt", ['turtle', 'xml', 'json-ld'])
    def test_all_entity_types_survive_export(self, store_with_session, tmp_path, fmt):
        store, session_id = store_with_session
        builder, _ = build_session_graph(store, session_id)

        reparsed = self.export_and_reparse(builder, tmp_path, fmt)
        assert_all_types_present(reparsed)

    @pytest.mark.parametrize("fmt", ['turtle', 'xml', 'json-ld'])
    def test_relationships_survive_export(self, store_with_session, tmp_path, fmt):
        store, session_id = store_with_session
        builder, _ = build_session_graph(store, session_id)

        g = self.export_and_reparse(builder, tmp_path, fmt)
        person = RESUME["person-1"]
        assert (person, RE.hasJob, RESUME["job-1"]) in g
        assert (RESUME["job-1"], SCHEMA.hiringOrganization, RESUME["org-tech"]) in g
        assert (person, SCHEMA.alumniOf, RESUME["edu-1"]) in g
        assert (person, RE.hasCertification, RESUME["cert-1"]) in g

    @pytest.mark.parametrize("fmt", ['turtle', 'xml', 'json-ld'])
    def test_formats_have_identical_triple_counts(self, store_with_session, tmp_path, fmt):
        store, session_id = store_with_session
        builder, _ = build_session_graph(store, session_id)

        reparsed = self.export_and_reparse(builder, tmp_path, fmt)
        assert len(reparsed) == len(builder.graph)


class TestExportRoute:
    """API-level regression test: the export route must include all entity types."""

    @pytest.fixture
    def app(self, tmp_path):
        app = create_app(config={
            'TESTING': True,
            'DATA_PATH': str(tmp_path),
            'ENABLE_DSPY': False,
        })
        return app

    @pytest.fixture
    def session_id(self, app):
        store = app.session_store
        session = store.create_session(name="Export Test")
        doc = store.add_document(session.id, "resume.txt", b"stub")
        store.save_extracted_entities(doc.id, make_full_entity_set())
        store.update_document_status(doc.id, 'complete')
        return session.id

    @pytest.mark.parametrize("api_fmt,rdflib_fmt", [
        ('turtle', 'turtle'),
        ('rdfxml', 'xml'),
        ('jsonld', 'json-ld'),
    ])
    def test_export_endpoint_is_complete(self, app, session_id, api_fmt, rdflib_fmt):
        client = app.test_client()
        response = client.get(f'/api/sessions/{session_id}/export/{api_fmt}')

        assert response.status_code == 200
        g = Graph()
        g.parse(data=response.data, format=rdflib_fmt)
        assert_all_types_present(g)

    def test_validate_endpoint_reports_clean_graph(self, app, session_id):
        client = app.test_client()
        response = client.get(f'/api/sessions/{session_id}/graph/validate')

        assert response.status_code == 200
        report = response.get_json()
        assert report['valid'] is True
        assert report['errors'] == []
        assert report['stats']['entity_counts']['organization'] == 2

    def test_validate_endpoint_without_documents(self, app):
        client = app.test_client()
        store = app.session_store
        session = store.create_session(name="Empty")

        response = client.get(f'/api/sessions/{session.id}/graph/validate')
        assert response.status_code == 404
        payload = response.get_json()
        assert 'hint' in payload
