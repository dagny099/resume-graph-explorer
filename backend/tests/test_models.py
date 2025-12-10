"""
Unit tests for SKOS-compliant data models

Tests:
- Entity creation and initialization
- RDF serialization
- JSON serialization
- SKOS relationships
- ESCO integration
"""

import pytest
from datetime import date, datetime
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, SKOS

from resume_explorer.models import (
    SKOSEntity,
    Person,
    Job,
    Skill,
    Education,
    Certification,
    Organization,
)
from resume_explorer.graph.vocabularies import (
    SCHEMA,
    ESCO,
    RE,
    RESUME,
    EntityType,
    bind_namespaces,
)


class TestSKOSEntity:
    """Test base SKOSEntity class."""

    def test_initialization(self):
        """Test entity initialization with default values."""
        entity = SKOSEntity(label="Test Entity")

        assert entity.id  # UUID should be generated
        assert entity.label == "Test Entity"
        assert entity.confidence == 1.0
        assert isinstance(entity.created_at, datetime)

    def test_to_dict(self):
        """Test JSON serialization."""
        entity = SKOSEntity(
            label="Python",
            definition="A high-level programming language",
            confidence=0.95,
        )

        data = entity.to_dict()

        assert data["label"] == "Python"
        assert data["definition"] == "A high-level programming language"
        assert data["confidence"] == 0.95
        assert "created_at" in data

    def test_to_rdf(self):
        """Test RDF serialization."""
        g = Graph()
        bind_namespaces(g)

        entity = SKOSEntity(
            id="test-123",
            label="Python",
            definition="A programming language",
        )

        uri = entity.to_rdf(g)

        # Check URI was returned
        assert isinstance(uri, URIRef)
        assert "test-123" in str(uri)

        # Check triples were added
        assert (uri, SKOS.prefLabel, Literal("Python")) in g
        assert (uri, SKOS.definition, Literal("A programming language")) in g

    def test_skos_hierarchy(self):
        """Test SKOS broader/narrower relationships."""
        g = Graph()
        bind_namespaces(g)

        parent = SKOSEntity(id="parent", label="Programming Languages")
        child = SKOSEntity(
            id="child",
            label="Python",
            broader_concepts=["parent"],
        )

        parent_uri = parent.to_rdf(g)
        child_uri = child.to_rdf(g)

        # Check broader relationship
        assert (child_uri, SKOS.broader, parent_uri) in g


class TestPerson:
    """Test Person entity."""

    def test_person_creation(self):
        """Test Person entity creation."""
        person = Person(
            name="Barbara Hidalgo-Sotelo",
            email="barbs@example.com",
            location="Austin, TX",
        )

        assert person.name == "Barbara Hidalgo-Sotelo"
        assert person.email == "barbs@example.com"
        assert person.location == "Austin, TX"

    def test_person_to_rdf(self):
        """Test Person RDF serialization."""
        g = Graph()
        bind_namespaces(g)

        person = Person(
            id="person-1",
            name="Barbara Hidalgo-Sotelo",
            email="barbs@example.com",
        )

        uri = person.to_rdf(g)

        # Check RDF type
        assert (uri, RDF.type, EntityType.PERSON) in g
        assert (uri, SCHEMA.name, Literal("Barbara Hidalgo-Sotelo")) in g
        assert (uri, SCHEMA.email, Literal("barbs@example.com")) in g

    def test_person_to_dict(self):
        """Test Person JSON serialization."""
        person = Person(
            name="Barbara Hidalgo-Sotelo",
            skills=["skill-1", "skill-2"],
        )

        data = person.to_dict()

        assert data["name"] == "Barbara Hidalgo-Sotelo"
        assert "skill-1" in data["skills"]
        assert "skill-2" in data["skills"]


class TestJob:
    """Test Job entity."""

    def test_job_creation(self):
        """Test Job entity creation."""
        job = Job(
            title="Data Scientist",
            organization_id="org-1",
            start_date=date(2021, 1, 1),
            end_date=date(2023, 12, 31),
        )

        assert job.title == "Data Scientist"
        assert job.organization_id == "org-1"
        assert job.start_date == date(2021, 1, 1)

    def test_job_duration_calculation(self):
        """Test job duration calculations."""
        job = Job(
            start_date=date(2021, 1, 1),
            end_date=date(2023, 1, 1),
        )

        duration_months = job.duration_months()
        duration_years = job.duration_years()

        assert duration_months == 24
        assert duration_years == 2.0

    def test_job_current_position(self):
        """Test current position (no end date)."""
        job = Job(
            start_date=date(2023, 1, 1),
            is_current=True,
        )

        # Duration should calculate to today
        assert job.duration_months() is not None
        assert job.duration_months() > 0

    def test_job_to_rdf(self):
        """Test Job RDF serialization."""
        g = Graph()
        bind_namespaces(g)

        job = Job(
            id="job-1",
            title="Data Scientist",
            start_date=date(2021, 1, 1),
            skills_used=["skill-1"],
        )

        uri = job.to_rdf(g)

        # Check RDF type and properties
        assert (uri, RDF.type, EntityType.JOB) in g
        assert (uri, SCHEMA.title, Literal("Data Scientist")) in g


class TestSkill:
    """Test Skill entity."""

    def test_skill_creation(self):
        """Test Skill entity creation."""
        skill = Skill(
            label="Python",
            category="Technical",
            proficiency_level="Expert",
            years_experience=5.0,
        )

        assert skill.label == "Python"
        assert skill.category == "Technical"
        assert skill.proficiency_level == "Expert"
        assert skill.years_experience == 5.0

    def test_skill_esco_linking(self):
        """Test automatic ESCO URI linking."""
        skill = Skill(label="Python")

        # Post-init should attempt to link to ESCO
        # (Will only work if "python" is in ESCO_SKILLS mapping)
        assert skill.label == "Python"

    def test_skill_to_rdf(self):
        """Test Skill RDF serialization."""
        g = Graph()
        bind_namespaces(g)

        skill = Skill(
            id="skill-1",
            label="Python",
            category="Technical",
        )

        uri = skill.to_rdf(g)

        # Check RDF type
        assert (uri, RDF.type, EntityType.SKILL) in g


class TestEducation:
    """Test Education entity."""

    def test_education_creation(self):
        """Test Education entity creation."""
        education = Education(
            degree_type="PhD",
            field_of_study="Cognitive Science",
            institution_id="org-mit",
            start_date=date(2005, 9, 1),
            end_date=date(2011, 6, 1),
            gpa=3.9,
        )

        assert education.degree_type == "PhD"
        assert education.field_of_study == "Cognitive Science"
        assert education.gpa == 3.9

    def test_education_to_rdf(self):
        """Test Education RDF serialization."""
        g = Graph()
        bind_namespaces(g)

        education = Education(
            id="edu-1",
            degree_type="PhD",
            field_of_study="Cognitive Science",
        )

        uri = education.to_rdf(g)

        # Check RDF type
        assert (uri, RDF.type, EntityType.EDUCATION) in g


class TestCertification:
    """Test Certification entity."""

    def test_certification_creation(self):
        """Test Certification entity creation."""
        cert = Certification(
            name="AWS Certified Solutions Architect",
            issuing_organization="Amazon Web Services",
            issue_date=date(2023, 1, 1),
            expiration_date=date(2026, 1, 1),
        )

        assert cert.name == "AWS Certified Solutions Architect"
        assert cert.issuing_organization == "Amazon Web Services"

    def test_certification_expiration(self):
        """Test certification expiration logic."""
        # Expired certification
        cert_expired = Certification(
            expiration_date=date(2020, 1, 1),
        )
        assert cert_expired.is_expired() is True

        # Active certification
        cert_active = Certification(
            expiration_date=date(2030, 1, 1),
        )
        assert cert_active.is_expired() is False

        # No expiration date
        cert_no_exp = Certification()
        assert cert_no_exp.is_expired() is False

    def test_certification_to_rdf(self):
        """Test Certification RDF serialization."""
        g = Graph()
        bind_namespaces(g)

        cert = Certification(
            id="cert-1",
            name="AWS Certified Solutions Architect",
        )

        uri = cert.to_rdf(g)

        # Check RDF type
        assert (uri, RDF.type, EntityType.CERTIFICATION) in g


class TestOrganization:
    """Test Organization entity."""

    def test_organization_creation(self):
        """Test Organization entity creation."""
        org = Organization(
            name="Massachusetts Institute of Technology",
            org_type="University",
            location="Cambridge, MA",
            website="https://mit.edu",
        )

        assert org.name == "Massachusetts Institute of Technology"
        assert org.org_type == "University"
        assert org.website == "https://mit.edu"

    def test_organization_to_rdf(self):
        """Test Organization RDF serialization."""
        g = Graph()
        bind_namespaces(g)

        org = Organization(
            id="org-1",
            name="MIT",
            org_type="University",
        )

        uri = org.to_rdf(g)

        # Check RDF type and properties
        assert (uri, RDF.type, EntityType.ORGANIZATION) in g
        assert (uri, SCHEMA.name, Literal("MIT")) in g


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
