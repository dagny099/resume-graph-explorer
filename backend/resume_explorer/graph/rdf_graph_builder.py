"""
RDF Graph Builder

Builds SKOS-compliant RDF knowledge graph from resume entities.
Supports export to Turtle, RDF/XML, and JSON-LD formats.
"""

from __future__ import annotations

from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, SKOS, XSD, DCTERMS
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from pathlib import Path
from datetime import datetime

from .vocabularies import SCHEMA, ESCO, RE, RESUME, EntityType, bind_namespaces
from ..utils.logger import logger

if TYPE_CHECKING:
    from ..models import Person, Job, Skill, Education, Certification, Organization


class RDFGraphBuilder:
    """
    Builds SKOS-compliant RDF graph from resume entities.

    Features:
    - SKOS vocabulary compliance
    - ESCO skill taxonomy integration
    - schema.org entity types
    - Provenance tracking
    - Multiple export formats
    """

    def __init__(self, base_namespace: Optional[Namespace] = None):
        """
        Initialize RDF graph builder.

        Args:
            base_namespace: Base namespace for entity URIs (default: RESUME)
        """
        self.graph = Graph()
        self.base_namespace = base_namespace or RESUME

        # Bind all standard namespaces
        bind_namespaces(self.graph)

        logger.info("RDFGraphBuilder initialized")

    def add_person(self, person: Person) -> URIRef:
        """
        Add Person entity to RDF graph.

        Args:
            person: Person entity

        Returns:
            URIRef of the person entity
        """
        # Add base SKOS properties via entity's to_rdf method
        uri = person.to_rdf(self.graph, self.base_namespace)

        # Add RDF type
        self.graph.add((uri, RDF.type, EntityType.PERSON))

        # Add schema.org properties
        if person.name:
            self.graph.add((uri, SCHEMA.name, Literal(person.name)))
        if person.email:
            self.graph.add((uri, SCHEMA.email, Literal(person.email)))
        if person.phone:
            self.graph.add((uri, SCHEMA.telephone, Literal(person.phone)))
        if person.location:
            self.graph.add((uri, SCHEMA.address, Literal(person.location)))
        if person.summary:
            self.graph.add((uri, SCHEMA.description, Literal(person.summary)))

        # Add relationships to jobs
        for job_id in person.jobs:
            job_uri = self.base_namespace[job_id]
            self.graph.add((uri, RE.hasJob, job_uri))

        # Add relationships to skills
        for skill_id in person.skills:
            skill_uri = self.base_namespace[skill_id]
            self.graph.add((uri, RE.hasSkill, skill_uri))

        # Add relationships to education
        for edu_id in person.education:
            edu_uri = self.base_namespace[edu_id]
            self.graph.add((uri, SCHEMA.alumniOf, edu_uri))

        # Add relationships to certifications
        for cert_id in person.certifications:
            cert_uri = self.base_namespace[cert_id]
            self.graph.add((uri, RE.hasCertification, cert_uri))

        # Add provenance
        self._add_provenance(uri, person)

        logger.debug(f"Added Person: {person.name}")
        return uri

    def add_job(self, job: Job) -> URIRef:
        """
        Add Job entity to RDF graph.

        Args:
            job: Job entity

        Returns:
            URIRef of the job entity
        """
        uri = job.to_rdf(self.graph, self.base_namespace)

        # Add RDF type
        self.graph.add((uri, RDF.type, EntityType.JOB))

        # Add schema.org properties
        if job.title:
            self.graph.add((uri, SCHEMA.title, Literal(job.title)))
        if job.location:
            self.graph.add((uri, SCHEMA.jobLocation, Literal(job.location)))
        if job.description:
            self.graph.add((uri, SCHEMA.description, Literal(job.description)))

        # Add temporal properties
        if job.start_date:
            self.graph.add((uri, SCHEMA.startDate, Literal(job.start_date, datatype=XSD.date)))
        if job.end_date:
            self.graph.add((uri, SCHEMA.endDate, Literal(job.end_date, datatype=XSD.date)))

        # Add custom properties
        self.graph.add((uri, RE.isCurrent, Literal(job.is_current, datatype=XSD.boolean)))

        # Add relationship to organization
        if job.organization_id:
            org_uri = self.base_namespace[job.organization_id]
            self.graph.add((uri, SCHEMA.hiringOrganization, org_uri))

        # Add relationships to skills used
        for skill_id in job.skills_used:
            skill_uri = self.base_namespace[skill_id]
            self.graph.add((uri, RE.usedSkill, skill_uri))

        # Add technologies used
        for tech in job.technologies_used:
            self.graph.add((uri, RE.usedTechnology, Literal(tech)))

        # Add achievements
        for achievement in job.achievements:
            self.graph.add((uri, RE.achievement, Literal(achievement)))

        # Add provenance
        self._add_provenance(uri, job)

        logger.debug(f"Added Job: {job.title}")
        return uri

    def add_skill(self, skill: Skill) -> URIRef:
        """
        Add Skill entity to RDF graph with SKOS properties.

        Args:
            skill: Skill entity

        Returns:
            URIRef of the skill entity
        """
        uri = skill.to_rdf(self.graph, self.base_namespace)

        # Add RDF type
        self.graph.add((uri, RDF.type, EntityType.SKILL))

        # Add custom properties
        if skill.category:
            self.graph.add((uri, RE.skillCategory, Literal(skill.category)))
        if skill.proficiency_level:
            self.graph.add((uri, RE.proficiencyLevel, Literal(skill.proficiency_level)))
        if skill.years_experience:
            self.graph.add((uri, RE.yearsExperience, Literal(skill.years_experience, datatype=XSD.float)))

        # Add provenance
        self._add_provenance(uri, skill)

        logger.debug(f"Added Skill: {skill.label}")
        return uri

    def add_education(self, education: Education) -> URIRef:
        """
        Add Education entity to RDF graph.

        Args:
            education: Education entity

        Returns:
            URIRef of the education entity
        """
        uri = education.to_rdf(self.graph, self.base_namespace)

        # Add RDF type
        self.graph.add((uri, RDF.type, EntityType.EDUCATION))

        # Add schema.org properties
        if education.degree_type:
            self.graph.add((uri, SCHEMA.credentialCategory, Literal(education.degree_type)))
        if education.field_of_study:
            self.graph.add((uri, SCHEMA.educationalCredentialAwarded, Literal(education.field_of_study)))

        # Add temporal properties
        if education.start_date:
            self.graph.add((uri, SCHEMA.startDate, Literal(education.start_date, datatype=XSD.date)))
        if education.end_date:
            self.graph.add((uri, SCHEMA.endDate, Literal(education.end_date, datatype=XSD.date)))

        # Add custom properties
        self.graph.add((uri, RE.isCurrent, Literal(education.is_current, datatype=XSD.boolean)))
        if education.gpa:
            self.graph.add((uri, RE.gpa, Literal(education.gpa, datatype=XSD.float)))

        # Add relationship to institution
        if education.institution_id:
            inst_uri = self.base_namespace[education.institution_id]
            self.graph.add((uri, SCHEMA.recognizedBy, inst_uri))

        # Add provenance
        self._add_provenance(uri, education)

        logger.debug(f"Added Education: {education.degree_type}")
        return uri

    def add_certification(self, certification: Certification) -> URIRef:
        """
        Add Certification entity to RDF graph.

        Args:
            certification: Certification entity

        Returns:
            URIRef of the certification entity
        """
        uri = certification.to_rdf(self.graph, self.base_namespace)

        # Add RDF type
        self.graph.add((uri, RDF.type, EntityType.CERTIFICATION))

        # Add schema.org properties
        if certification.name:
            self.graph.add((uri, SCHEMA.name, Literal(certification.name)))

        # Add custom properties
        if certification.issuing_organization:
            self.graph.add((uri, RE.issuingOrganization, Literal(certification.issuing_organization)))
        if certification.issue_date:
            self.graph.add((uri, RE.issueDate, Literal(certification.issue_date, datatype=XSD.date)))
        if certification.expiration_date:
            self.graph.add((uri, RE.expirationDate, Literal(certification.expiration_date, datatype=XSD.date)))
        if certification.credential_id:
            self.graph.add((uri, RE.credentialId, Literal(certification.credential_id)))
        if certification.credential_url:
            self.graph.add((uri, RE.credentialUrl, URIRef(certification.credential_url)))

        self.graph.add((uri, RE.isActive, Literal(certification.is_active, datatype=XSD.boolean)))
        self.graph.add((uri, RE.isExpired, Literal(certification.is_expired(), datatype=XSD.boolean)))

        # Add provenance
        self._add_provenance(uri, certification)

        logger.debug(f"Added Certification: {certification.name}")
        return uri

    def add_organization(self, organization: Organization) -> URIRef:
        """
        Add Organization entity to RDF graph.

        Args:
            organization: Organization entity

        Returns:
            URIRef of the organization entity
        """
        uri = organization.to_rdf(self.graph, self.base_namespace)

        # Add RDF type
        self.graph.add((uri, RDF.type, EntityType.ORGANIZATION))

        # Add schema.org properties
        if organization.name:
            self.graph.add((uri, SCHEMA.name, Literal(organization.name)))
        if organization.location:
            self.graph.add((uri, SCHEMA.address, Literal(organization.location)))
        if organization.website:
            self.graph.add((uri, SCHEMA.url, URIRef(organization.website)))
        if organization.description:
            self.graph.add((uri, SCHEMA.description, Literal(organization.description)))

        # Add custom properties
        if organization.org_type:
            self.graph.add((uri, RE.organizationType, Literal(organization.org_type)))
        if organization.industry:
            self.graph.add((uri, RE.industry, Literal(organization.industry)))

        # Add provenance
        self._add_provenance(uri, organization)

        logger.debug(f"Added Organization: {organization.name}")
        return uri

    def build_from_entities(
        self,
        person: Person,
        jobs: List[Job],
        skills: List[Skill],
        education: List[Education],
        certifications: List[Certification],
        organizations: List[Organization]
    ) -> Graph:
        """
        Build complete RDF graph from all entities.

        Args:
            person: Person entity
            jobs: List of Job entities
            skills: List of Skill entities
            education: List of Education entities
            certifications: List of Certification entities
            organizations: List of Organization entities

        Returns:
            Complete RDF graph
        """
        logger.info("Building RDF graph from entities")

        # Add organizations first (referenced by jobs and education)
        for org in organizations:
            self.add_organization(org)

        # Add skills (referenced by jobs)
        for skill in skills:
            self.add_skill(skill)

        # Add jobs
        for job in jobs:
            self.add_job(job)

        # Add education
        for edu in education:
            self.add_education(edu)

        # Add certifications
        for cert in certifications:
            self.add_certification(cert)

        # Add person (references all other entities)
        self.add_person(person)

        logger.info(f"Graph built: {len(self.graph)} triples")
        return self.graph

    def _add_provenance(self, uri: URIRef, entity) -> None:
        """
        Add provenance metadata to entity.

        Args:
            uri: Entity URI
            entity: Entity object with provenance fields
        """
        if hasattr(entity, 'confidence'):
            self.graph.add((uri, RE.confidence, Literal(entity.confidence, datatype=XSD.float)))

        if hasattr(entity, 'source_doc') and entity.source_doc:
            self.graph.add((uri, RE.sourceDocument, Literal(entity.source_doc)))

        if hasattr(entity, 'created_at'):
            self.graph.add((uri, RE.createdAt, Literal(entity.created_at, datatype=XSD.dateTime)))

    def export_turtle(self, filepath: str) -> None:
        """
        Export graph as Turtle format.

        Args:
            filepath: Output file path
        """
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        self.graph.serialize(destination=filepath, format='turtle', encoding='utf-8')
        logger.info(f"Exported Turtle: {filepath}")

    def export_rdfxml(self, filepath: str) -> None:
        """
        Export graph as RDF/XML format.

        Args:
            filepath: Output file path
        """
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        self.graph.serialize(destination=filepath, format='xml', encoding='utf-8')
        logger.info(f"Exported RDF/XML: {filepath}")

    def export_jsonld(self, filepath: str) -> None:
        """
        Export graph as JSON-LD format.

        Args:
            filepath: Output file path
        """
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        self.graph.serialize(destination=filepath, format='json-ld', encoding='utf-8')
        logger.info(f"Exported JSON-LD: {filepath}")

    def export_all_formats(self, base_path: str, filename: str) -> Dict[str, str]:
        """
        Export graph to all supported formats.

        Args:
            base_path: Base directory for exports
            filename: Base filename (without extension)

        Returns:
            Dictionary mapping format to filepath
        """
        base_dir = Path(base_path)
        base_dir.mkdir(parents=True, exist_ok=True)

        filepaths = {
            'turtle': str(base_dir / f"{filename}.ttl"),
            'rdfxml': str(base_dir / f"{filename}.rdf"),
            'jsonld': str(base_dir / f"{filename}.jsonld")
        }

        self.export_turtle(filepaths['turtle'])
        self.export_rdfxml(filepaths['rdfxml'])
        self.export_jsonld(filepaths['jsonld'])

        logger.info(f"Exported all formats for: {filename}")
        return filepaths

    def get_graph_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the graph.

        Returns:
            Dictionary with graph statistics
        """
        stats = {
            'triple_count': len(self.graph),
            'entity_counts': {},
            'namespaces': list(self.graph.namespaces())
        }

        # Count entities by type
        for entity_type_name in ['PERSON', 'JOB', 'SKILL', 'EDUCATION', 'CERTIFICATION', 'ORGANIZATION']:
            entity_type = getattr(EntityType, entity_type_name)
            count = len(list(self.graph.subjects(RDF.type, entity_type)))
            stats['entity_counts'][entity_type_name.lower()] = count

        return stats

    def query_sparql(self, query: str) -> List[Dict]:
        """
        Execute SPARQL query on the graph.

        Args:
            query: SPARQL query string

        Returns:
            List of result rows as dictionaries
        """
        results = self.graph.query(query)

        # Convert results to list of dicts
        result_list = []
        for row in results:
            result_dict = {}
            for var in results.vars:
                result_dict[str(var)] = str(row[var])
            result_list.append(result_dict)

        return result_list


__all__ = ['RDFGraphBuilder']
