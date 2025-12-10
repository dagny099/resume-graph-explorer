"""
Unit tests for RDF graph builder and NetworkX adapter

Tests:
- RDF graph construction
- Entity serialization to RDF
- SKOS compliance
- Export to multiple formats
- NetworkX conversion
- Vis.js format generation
"""

import pytest
from datetime import date, datetime
from pathlib import Path
import tempfile
import json

from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, SKOS

from resume_explorer.models import Person, Job, Skill, Education, Certification, Organization
from resume_explorer.graph import (
    RDFGraphBuilder,
    NetworkXAdapter,
    SCHEMA,
    RE,
    RESUME,
    EntityType,
    bind_namespaces
)


class TestRDFGraphBuilder:
    """Test RDF graph construction and entity serialization."""

    def test_graph_initialization(self):
        """Test graph builder initialization."""
        builder = RDFGraphBuilder()

        assert builder.graph is not None
        assert len(builder.graph) == 0
        assert builder.base_namespace == RESUME

    def test_add_person(self):
        """Test adding Person entity to graph."""
        builder = RDFGraphBuilder()

        person = Person(
            id="person-1",
            name="Barbara Hidalgo-Sotelo",
            email="barbs@example.com",
            location="Austin, TX",
            summary="Data Scientist and AI researcher"
        )

        uri = builder.add_person(person)

        # Check URI
        assert isinstance(uri, URIRef)
        assert "person-1" in str(uri)

        # Check triples
        assert (uri, RDF.type, EntityType.PERSON) in builder.graph
        assert (uri, SCHEMA.name, Literal("Barbara Hidalgo-Sotelo")) in builder.graph
        assert (uri, SCHEMA.email, Literal("barbs@example.com")) in builder.graph

    def test_add_job(self):
        """Test adding Job entity to graph."""
        builder = RDFGraphBuilder()

        job = Job(
            id="job-1",
            title="Data Scientist",
            organization_id="org-1",
            start_date=date(2020, 1, 1),
            end_date=date(2023, 12, 31),
            is_current=False,
            location="San Francisco, CA"
        )

        uri = builder.add_job(job)

        # Check RDF type
        assert (uri, RDF.type, EntityType.JOB) in builder.graph

        # Check properties
        assert (uri, SCHEMA.title, Literal("Data Scientist")) in builder.graph
        assert (uri, SCHEMA.jobLocation, Literal("San Francisco, CA")) in builder.graph

        # Check temporal properties exist
        date_triples = list(builder.graph.triples((uri, SCHEMA.startDate, None)))
        assert len(date_triples) == 1

    def test_add_skill_with_hierarchy(self):
        """Test adding Skill with SKOS hierarchy."""
        builder = RDFGraphBuilder()

        skill = Skill(
            id="skill-python",
            label="Python",
            category="Technical",
            proficiency_level="Expert",
            years_experience=5.0,
            broader_concepts=["skill-programming"],
            related_concepts=["skill-data-science"]
        )

        uri = builder.add_skill(skill)

        # Check RDF type
        assert (uri, RDF.type, EntityType.SKILL) in builder.graph

        # Check SKOS properties
        assert (uri, SKOS.prefLabel, Literal("Python")) in builder.graph

        # Check SKOS hierarchy (from base class)
        broader_uri = RESUME["skill-programming"]
        assert (uri, SKOS.broader, broader_uri) in builder.graph

        # Check custom properties
        assert (uri, RE.skillCategory, Literal("Technical")) in builder.graph
        assert (uri, RE.proficiencyLevel, Literal("Expert")) in builder.graph

    def test_add_education(self):
        """Test adding Education entity to graph."""
        builder = RDFGraphBuilder()

        education = Education(
            id="edu-1",
            degree_type="PhD",
            field_of_study="Cognitive Science",
            institution_id="org-mit",
            start_date=date(2005, 9, 1),
            end_date=date(2011, 6, 1),
            gpa=3.9
        )

        uri = builder.add_education(education)

        # Check RDF type
        assert (uri, RDF.type, EntityType.EDUCATION) in builder.graph

        # Check properties
        assert (uri, SCHEMA.credentialCategory, Literal("PhD")) in builder.graph
        assert (uri, SCHEMA.educationalCredentialAwarded, Literal("Cognitive Science")) in builder.graph

    def test_add_certification(self):
        """Test adding Certification entity to graph."""
        builder = RDFGraphBuilder()

        cert = Certification(
            id="cert-1",
            name="AWS Certified Solutions Architect",
            issuing_organization="Amazon Web Services",
            issue_date=date(2023, 1, 1),
            expiration_date=date(2026, 1, 1),
            is_active=True
        )

        uri = builder.add_certification(cert)

        # Check RDF type
        assert (uri, RDF.type, EntityType.CERTIFICATION) in builder.graph

        # Check properties
        assert (uri, SCHEMA.name, Literal("AWS Certified Solutions Architect")) in builder.graph
        assert (uri, RE.issuingOrganization, Literal("Amazon Web Services")) in builder.graph

    def test_add_organization(self):
        """Test adding Organization entity to graph."""
        builder = RDFGraphBuilder()

        org = Organization(
            id="org-1",
            name="Massachusetts Institute of Technology",
            org_type="University",
            location="Cambridge, MA",
            website="https://mit.edu"
        )

        uri = builder.add_organization(org)

        # Check RDF type
        assert (uri, RDF.type, EntityType.ORGANIZATION) in builder.graph

        # Check properties
        assert (uri, SCHEMA.name, Literal("Massachusetts Institute of Technology")) in builder.graph
        assert (uri, RE.organizationType, Literal("University")) in builder.graph

    def test_build_complete_graph(self):
        """Test building complete graph from all entities."""
        builder = RDFGraphBuilder()

        # Create entities
        org = Organization(
            id="org-1",
            name="Tech Corp",
            org_type="Company"
        )

        skill = Skill(
            id="skill-1",
            label="Python",
            category="Technical"
        )

        job = Job(
            id="job-1",
            title="Data Scientist",
            organization_id="org-1",
            skills_used=["skill-1"]
        )

        person = Person(
            id="person-1",
            name="Test Person",
            jobs=["job-1"],
            skills=["skill-1"]
        )

        # Build graph
        builder.build_from_entities(
            person=person,
            jobs=[job],
            skills=[skill],
            education=[],
            certifications=[],
            organizations=[org]
        )

        # Check graph has multiple entities
        stats = builder.get_graph_stats()
        assert stats['entity_counts']['person'] == 1
        assert stats['entity_counts']['job'] == 1
        assert stats['entity_counts']['skill'] == 1
        assert stats['entity_counts']['organization'] == 1

        # Check relationships exist
        person_uri = RESUME["person-1"]
        job_uri = RESUME["job-1"]
        skill_uri = RESUME["skill-1"]

        assert (person_uri, RE.hasJob, job_uri) in builder.graph
        assert (person_uri, RE.hasSkill, skill_uri) in builder.graph
        assert (job_uri, RE.usedSkill, skill_uri) in builder.graph

    def test_export_turtle(self):
        """Test exporting graph to Turtle format."""
        builder = RDFGraphBuilder()

        person = Person(id="person-1", name="Test Person")
        builder.add_person(person)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.ttl"
            builder.export_turtle(str(filepath))

            # Check file exists
            assert filepath.exists()

            # Check content
            content = filepath.read_text()
            assert "person-1" in content
            assert "Test Person" in content

            # Verify it's valid RDF by re-parsing
            g = Graph()
            g.parse(str(filepath), format='turtle')
            assert len(g) > 0

    def test_export_rdfxml(self):
        """Test exporting graph to RDF/XML format."""
        builder = RDFGraphBuilder()

        person = Person(id="person-1", name="Test Person")
        builder.add_person(person)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.rdf"
            builder.export_rdfxml(str(filepath))

            assert filepath.exists()

            # Verify valid RDF/XML
            g = Graph()
            g.parse(str(filepath), format='xml')
            assert len(g) > 0

    def test_export_jsonld(self):
        """Test exporting graph to JSON-LD format."""
        builder = RDFGraphBuilder()

        person = Person(id="person-1", name="Test Person")
        builder.add_person(person)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.jsonld"
            builder.export_jsonld(str(filepath))

            assert filepath.exists()

            # Verify valid JSON-LD
            g = Graph()
            g.parse(str(filepath), format='json-ld')
            assert len(g) > 0

    def test_export_all_formats(self):
        """Test exporting to all formats at once."""
        builder = RDFGraphBuilder()

        person = Person(id="person-1", name="Test Person")
        builder.add_person(person)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepaths = builder.export_all_formats(tmpdir, "resume")

            # Check all formats were created
            assert 'turtle' in filepaths
            assert 'rdfxml' in filepaths
            assert 'jsonld' in filepaths

            assert Path(filepaths['turtle']).exists()
            assert Path(filepaths['rdfxml']).exists()
            assert Path(filepaths['jsonld']).exists()

    def test_provenance_tracking(self):
        """Test that provenance metadata is added."""
        builder = RDFGraphBuilder()

        person = Person(
            id="person-1",
            name="Test Person",
            confidence=0.95,
            source_doc="resume.pdf",
            created_at=datetime(2025, 12, 8, 10, 30, 0)
        )

        uri = builder.add_person(person)

        # Check provenance triples
        assert (uri, RE.confidence, Literal(0.95)) in builder.graph
        assert (uri, RE.sourceDocument, Literal("resume.pdf")) in builder.graph

        # Check created_at exists
        created_at_triples = list(builder.graph.triples((uri, RE.createdAt, None)))
        assert len(created_at_triples) == 1

    def test_graph_stats(self):
        """Test graph statistics calculation."""
        builder = RDFGraphBuilder()

        # Add multiple entities
        person = Person(id="person-1", name="Person 1")
        job1 = Job(id="job-1", title="Job 1")
        job2 = Job(id="job-2", title="Job 2")
        skill1 = Skill(id="skill-1", label="Skill 1")

        builder.add_person(person)
        builder.add_job(job1)
        builder.add_job(job2)
        builder.add_skill(skill1)

        stats = builder.get_graph_stats()

        assert stats['entity_counts']['person'] == 1
        assert stats['entity_counts']['job'] == 2
        assert stats['entity_counts']['skill'] == 1
        assert stats['triple_count'] > 0


class TestNetworkXAdapter:
    """Test NetworkX adapter and Vis.js conversion."""

    def create_sample_graph(self) -> RDFGraphBuilder:
        """Create sample RDF graph for testing."""
        builder = RDFGraphBuilder()

        org = Organization(id="org-1", name="Tech Corp")
        skill = Skill(id="skill-1", label="Python", category="Technical")
        job = Job(
            id="job-1",
            title="Data Scientist",
            organization_id="org-1",
            skills_used=["skill-1"]
        )
        person = Person(
            id="person-1",
            name="Barbara",
            jobs=["job-1"],
            skills=["skill-1"]
        )

        builder.build_from_entities(
            person=person,
            jobs=[job],
            skills=[skill],
            education=[],
            certifications=[],
            organizations=[org]
        )

        return builder

    def test_adapter_initialization(self):
        """Test NetworkX adapter initialization."""
        builder = self.create_sample_graph()
        adapter = NetworkXAdapter(builder.graph)

        assert adapter.rdf_graph is not None
        assert adapter.nx_graph is not None

    def test_convert_to_visjs(self):
        """Test conversion to Vis.js format."""
        builder = self.create_sample_graph()
        adapter = NetworkXAdapter(builder.graph)

        result = adapter.convert()

        # Check structure
        assert 'nodes' in result
        assert 'edges' in result
        assert 'stats' in result

        # Check nodes
        assert len(result['nodes']) > 0
        for node in result['nodes']:
            assert 'id' in node
            assert 'label' in node
            assert 'group' in node
            assert 'title' in node  # Tooltip

        # Check edges
        assert len(result['edges']) > 0
        for edge in result['edges']:
            assert 'from' in edge
            assert 'to' in edge
            assert 'label' in edge

    def test_node_grouping(self):
        """Test that nodes are correctly grouped by entity type."""
        builder = self.create_sample_graph()
        adapter = NetworkXAdapter(builder.graph)

        result = adapter.convert()

        # Find person node
        person_nodes = [n for n in result['nodes'] if n['group'] == 'person']
        assert len(person_nodes) == 1

        # Find job nodes
        job_nodes = [n for n in result['nodes'] if n['group'] == 'job']
        assert len(job_nodes) == 1

        # Check stats
        assert result['stats']['entity_type_counts']['person'] == 1
        assert result['stats']['entity_type_counts']['job'] == 1

    def test_node_colors(self):
        """Test that nodes have appropriate colors."""
        builder = self.create_sample_graph()
        adapter = NetworkXAdapter(builder.graph)

        result = adapter.convert()

        for node in result['nodes']:
            assert 'color' in node
            assert 'background' in node['color']
            assert node['color']['background'].startswith('#')

    def test_edge_labels(self):
        """Test that edges have readable labels."""
        builder = self.create_sample_graph()
        adapter = NetworkXAdapter(builder.graph)

        result = adapter.convert()

        # Find hasJob edge
        has_job_edges = [e for e in result['edges'] if 'job' in e['label'].lower()]
        assert len(has_job_edges) > 0

        # Find usedSkill edge
        used_skill_edges = [e for e in result['edges'] if 'skill' in e['label'].lower()]
        assert len(used_skill_edges) > 0

    def test_to_networkx(self):
        """Test conversion to NetworkX graph."""
        builder = self.create_sample_graph()
        adapter = NetworkXAdapter(builder.graph)

        nx_graph = adapter.to_networkx()

        # Check graph type
        assert nx_graph.number_of_nodes() > 0
        assert nx_graph.number_of_edges() > 0

        # Check node attributes
        for node in nx_graph.nodes():
            node_data = nx_graph.nodes[node]
            assert 'label' in node_data
            assert 'entity_type' in node_data

    def test_subgraph_extraction(self):
        """Test extracting subgraph around a node."""
        builder = self.create_sample_graph()
        adapter = NetworkXAdapter(builder.graph)

        # First convert to NetworkX
        adapter.to_networkx()

        # Get subgraph centered on person
        person_uri = str(RESUME["person-1"])
        subgraph = adapter.get_subgraph(person_uri, depth=1)

        # Check structure
        assert 'nodes' in subgraph
        assert 'edges' in subgraph
        assert 'center' in subgraph

        # Person should be in subgraph
        node_ids = [n['id'] for n in subgraph['nodes']]
        assert person_uri in node_ids

    def test_confidence_visualization(self):
        """Test that confidence affects node visualization."""
        builder = RDFGraphBuilder()

        # High confidence skill
        skill_high = Skill(id="skill-1", label="Python", confidence=0.95)
        builder.add_skill(skill_high)

        # Low confidence skill
        skill_low = Skill(id="skill-2", label="Unknown", confidence=0.5)
        builder.add_skill(skill_low)

        adapter = NetworkXAdapter(builder.graph)
        result = adapter.convert()

        # Find both skills
        skill1 = next(n for n in result['nodes'] if 'skill-1' in n['id'])
        skill2 = next(n for n in result['nodes'] if 'skill-2' in n['id'])

        # Check that border colors differ
        assert skill1['color']['border'] != skill2['color']['border']

    def test_tooltip_content(self):
        """Test that tooltips contain useful information."""
        builder = RDFGraphBuilder()

        person = Person(
            id="person-1",
            name="Barbara Hidalgo-Sotelo",
            email="barbs@example.com",
            location="Austin, TX"
        )
        builder.add_person(person)

        adapter = NetworkXAdapter(builder.graph)
        result = adapter.convert()

        person_node = result['nodes'][0]
        tooltip = person_node['title']

        # Check tooltip contains key info
        assert "Barbara" in tooltip
        assert "person" in tooltip.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
