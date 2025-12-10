"""
Person Entity - Represents the resume owner

Maps to schema:Person from schema.org
"""

from dataclasses import dataclass, field
from typing import List, Optional

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF

from .base import SKOSEntity
from ..graph.vocabularies import SCHEMA, EntityType, RE


@dataclass
class Person(SKOSEntity):
    """
    Represents the person who owns the resume.

    Maps to schema:Person (http://schema.org/Person).

    Attributes:
        name: Full name (schema:name)
        email: Email address (schema:email)
        phone: Phone number (schema:telephone)
        location: Geographic location (schema:address)
        summary: Professional summary/bio (schema:description)
        jobs: List of Job entity IDs
        skills: List of Skill entity IDs
        education: List of Education entity IDs
        certifications: List of Certification entity IDs
    """

    name: str = ""
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None

    # Relationships (stored as entity IDs)
    jobs: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    education: List[str] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)

    def to_rdf(self, graph: Graph, base_namespace: Namespace) -> "URIRef":
        """
        Add Person to RDF graph with schema.org properties.

        Args:
            graph: RDF graph
            base_namespace: Base namespace for URIs

        Returns:
            URIRef of the person entity
        """
        # Add base SKOS properties
        uri = super().to_rdf(graph, base_namespace)

        # Add RDF type
        graph.add((uri, RDF.type, EntityType.PERSON))

        # Add schema.org properties
        if self.name:
            graph.add((uri, SCHEMA.name, Literal(self.name)))
        if self.email:
            graph.add((uri, SCHEMA.email, Literal(self.email)))
        if self.phone:
            graph.add((uri, SCHEMA.telephone, Literal(self.phone)))
        if self.location:
            graph.add((uri, SCHEMA.address, Literal(self.location)))
        if self.summary:
            graph.add((uri, SCHEMA.description, Literal(self.summary)))

        return uri

    def to_dict(self) -> dict:
        """Export Person as dictionary."""
        data = super().to_dict()
        data.update({
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "location": self.location,
            "summary": self.summary,
            "jobs": self.jobs,
            "skills": self.skills,
            "education": self.education,
            "certifications": self.certifications,
        })
        return data


__all__ = ["Person"]
