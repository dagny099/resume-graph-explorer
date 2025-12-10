"""
Organization Entity - Represents companies, institutions, etc.

Maps to schema:Organization from schema.org
"""

from dataclasses import dataclass
from typing import Optional

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF

from .base import SKOSEntity
from ..graph.vocabularies import SCHEMA, EntityType, RE


@dataclass
class Organization(SKOSEntity):
    """
    Represents an organization (company, institution, etc.).

    Maps to schema:Organization (http://schema.org/Organization).

    Can represent:
    - Companies (employment)
    - Educational institutions (schema:EducationalOrganization)
    - Certification issuers

    Attributes:
        name: Organization name (schema:name)
        org_type: Type ("Company", "University", "Government", etc.)
        industry: Industry sector
        location: Primary location
        website: Organization website URL
        description: Organization description
    """

    name: str = ""
    org_type: Optional[str] = None  # "Company", "University", etc.
    industry: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None

    def to_rdf(self, graph: Graph, base_namespace: Namespace) -> URIRef:
        """
        Add Organization to RDF graph with schema.org properties.

        Args:
            graph: RDF graph
            base_namespace: Base namespace for URIs

        Returns:
            URIRef of the organization entity
        """
        # Add base SKOS properties
        uri = super().to_rdf(graph, base_namespace)

        # Add RDF type
        graph.add((uri, RDF.type, EntityType.ORGANIZATION))

        # Add schema.org properties
        if self.name:
            graph.add((uri, SCHEMA.name, Literal(self.name)))
        if self.location:
            graph.add((uri, SCHEMA.address, Literal(self.location)))
        if self.website:
            graph.add((uri, SCHEMA.url, URIRef(self.website)))
        if self.description:
            graph.add((uri, SCHEMA.description, Literal(self.description)))

        # Custom properties
        if self.org_type:
            graph.add((uri, RE.organizationType, Literal(self.org_type)))
        if self.industry:
            graph.add((uri, RE.industry, Literal(self.industry)))

        return uri

    def to_dict(self) -> dict:
        """Export Organization as dictionary."""
        data = super().to_dict()
        data.update({
            "name": self.name,
            "org_type": self.org_type,
            "industry": self.industry,
            "location": self.location,
            "website": self.website,
            "description": self.description,
        })
        return data


__all__ = ["Organization"]
