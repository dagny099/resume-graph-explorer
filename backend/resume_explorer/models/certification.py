"""
Certification Entity - Represents professional certifications

Custom entity type for Resume Explorer
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

from .base import SKOSEntity
from ..graph.vocabularies import SCHEMA, EntityType, RE


@dataclass
class Certification(SKOSEntity):
    """
    Represents a professional certification or accreditation.

    Custom entity type (RE:Certification).

    Attributes:
        name: Certification name (e.g., "AWS Certified Solutions Architect")
        issuing_organization: Name of issuing body (e.g., "Amazon Web Services")
        issue_date: Date certification was issued
        expiration_date: Expiration date (None if no expiration)
        credential_id: Credential/certificate ID or number
        credential_url: URL to verify credential
        is_active: Whether certification is currently active
    """

    name: str = ""
    issuing_organization: Optional[str] = None
    issue_date: Optional[date] = None
    expiration_date: Optional[date] = None
    credential_id: Optional[str] = None
    credential_url: Optional[str] = None
    is_active: bool = True

    def is_expired(self) -> bool:
        """
        Check if certification has expired.

        Returns:
            True if expired, False otherwise
        """
        if not self.expiration_date:
            return False  # No expiration means always valid
        return self.expiration_date < date.today()

    def to_rdf(self, graph: Graph, base_namespace: Namespace) -> URIRef:
        """
        Add Certification to RDF graph.

        Args:
            graph: RDF graph
            base_namespace: Base namespace for URIs

        Returns:
            URIRef of the certification entity
        """
        # Add base SKOS properties
        uri = super().to_rdf(graph, base_namespace)

        # Add RDF type
        graph.add((uri, RDF.type, EntityType.CERTIFICATION))

        # Add properties
        if self.name:
            graph.add((uri, SCHEMA.name, Literal(self.name)))
        if self.issuing_organization:
            graph.add((uri, RE.issuingOrganization, Literal(self.issuing_organization)))
        if self.issue_date:
            graph.add((uri, RE.issueDate, Literal(self.issue_date, datatype=XSD.date)))
        if self.expiration_date:
            graph.add((uri, RE.expirationDate, Literal(self.expiration_date, datatype=XSD.date)))
        if self.credential_id:
            graph.add((uri, RE.credentialId, Literal(self.credential_id)))
        if self.credential_url:
            graph.add((uri, RE.credentialUrl, URIRef(self.credential_url)))

        graph.add((uri, RE.isActive, Literal(self.is_active, datatype=XSD.boolean)))
        graph.add((uri, RE.isExpired, Literal(self.is_expired(), datatype=XSD.boolean)))

        return uri

    def to_dict(self) -> dict:
        """Export Certification as dictionary."""
        data = super().to_dict()
        data.update({
            "name": self.name,
            "issuing_organization": self.issuing_organization,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "expiration_date": self.expiration_date.isoformat() if self.expiration_date else None,
            "credential_id": self.credential_id,
            "credential_url": self.credential_url,
            "is_active": self.is_active,
            "is_expired": self.is_expired(),
        })
        return data


__all__ = ["Certification"]
