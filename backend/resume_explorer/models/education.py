"""
Education Entity - Represents educational credentials

Maps to schema:EducationalOccupationalCredential from schema.org
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional
from urllib.parse import quote

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

from .base import SKOSEntity
from ..graph.vocabularies import SCHEMA, EntityType, RE, RelationType


@dataclass
class Education(SKOSEntity):
    """
    Represents an educational credential (degree, diploma, certificate).

    Maps to schema:EducationalOccupationalCredential
    (http://schema.org/EducationalOccupationalCredential).

    Attributes:
        degree_type: Type of degree (e.g., "PhD", "MS", "BS", "Certificate")
        field_of_study: Field or major (e.g., "Computer Science", "Biology")
        institution_id: ID of Organization entity (schema:educationalLevel)
        start_date: Start date of program
        end_date: Graduation/completion date
        is_current: Whether currently enrolled
        location: Institution location
        description: Additional details (thesis title, honors, etc.)
        gpa: Grade point average (optional)
    """

    degree_type: str = ""  # e.g., "PhD", "MS", "BS"
    field_of_study: Optional[str] = None
    institution_id: str = ""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: bool = False
    location: Optional[str] = None
    description: Optional[str] = None
    gpa: Optional[float] = None

    def to_rdf(self, graph: Graph, base_namespace: Namespace) -> URIRef:
        """
        Add Education to RDF graph with schema.org properties.

        Args:
            graph: RDF graph
            base_namespace: Base namespace for URIs

        Returns:
            URIRef of the education entity
        """
        # Add base SKOS properties
        uri = super().to_rdf(graph, base_namespace)

        # Add RDF type
        graph.add((uri, RDF.type, EntityType.EDUCATION))

        # Add schema.org properties
        if self.degree_type:
            graph.add((uri, SCHEMA.credentialCategory, Literal(self.degree_type)))
        if self.field_of_study:
            graph.add((uri, SCHEMA.educationalCredentialAwarded, Literal(self.field_of_study)))
        if self.institution_id:
            institution_uri = base_namespace[quote(self.institution_id, safe='')]
            graph.add((uri, SCHEMA.recognizedBy, institution_uri))
        if self.location:
            graph.add((uri, SCHEMA.availableAtOrFrom, Literal(self.location)))
        if self.description:
            graph.add((uri, SCHEMA.description, Literal(self.description)))

        # Temporal properties
        if self.start_date:
            graph.add((uri, RelationType.START_DATE, Literal(self.start_date, datatype=XSD.date)))
        if self.end_date:
            graph.add((uri, RelationType.END_DATE, Literal(self.end_date, datatype=XSD.date)))

        # Custom properties
        graph.add((uri, RE.isCurrent, Literal(self.is_current, datatype=XSD.boolean)))
        if self.gpa is not None:
            graph.add((uri, RE.gpa, Literal(self.gpa, datatype=XSD.float)))

        return uri

    def to_dict(self) -> dict:
        """Export Education as dictionary."""
        data = super().to_dict()
        data.update({
            "degree_type": self.degree_type,
            "field_of_study": self.field_of_study,
            "institution_id": self.institution_id,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "is_current": self.is_current,
            "location": self.location,
            "description": self.description,
            "gpa": self.gpa,
        })
        return data


__all__ = ["Education"]
