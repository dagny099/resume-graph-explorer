"""
Job Entity - Represents a job position/employment

Maps to schema:JobPosting from schema.org
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional, List
from urllib.parse import quote

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

from .base import SKOSEntity
from ..graph.vocabularies import RESUME, SCHEMA, EntityType, RE, RelationType


@dataclass
class Job(SKOSEntity):
    """
    Represents a job position from a resume.

    Maps to schema:JobPosting (http://schema.org/JobPosting).

    Attributes:
        title: Job title (schema:title)
        organization_id: ID of Organization entity (schema:hiringOrganization)
        start_date: Employment start date (schema:startDate)
        end_date: Employment end date (schema:endDate) or None if current
        is_current: Whether this is the current position
        location: Job location (schema:jobLocation)
        description: Job description/responsibilities (schema:description)
        skills_used: List of Skill entity IDs used in this role
        technologies_used: List of Technology entity IDs
        achievements: List of achievement descriptions
    """

    title: str = ""
    organization_id: str = ""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: bool = False
    location: Optional[str] = None
    description: Optional[str] = None

    # Relationships
    skills_used: List[str] = field(default_factory=list)
    technologies_used: List[str] = field(default_factory=list)
    achievements: List[str] = field(default_factory=list)

    def duration_months(self) -> Optional[int]:
        """
        Calculate job duration in months.

        Returns:
            Number of months or None if start_date is not set
        """
        if not self.start_date:
            return None

        end = self.end_date if self.end_date else date.today()
        months = (end.year - self.start_date.year) * 12 + (end.month - self.start_date.month)
        return max(months, 0)  # Ensure non-negative

    def duration_years(self) -> Optional[float]:
        """
        Calculate job duration in years.

        Returns:
            Number of years (decimal) or None
        """
        months = self.duration_months()
        return round(months / 12, 1) if months is not None else None

    def to_rdf(self, graph: Graph, base_namespace: Namespace = RESUME) -> URIRef:
        """
        Add Job to RDF graph with schema.org properties.

        Args:
            graph: RDF graph
            base_namespace: Base namespace for URIs

        Returns:
            URIRef of the job entity
        """
        # Add base SKOS properties
        uri = super().to_rdf(graph, base_namespace)

        # Add RDF type
        graph.add((uri, RDF.type, EntityType.JOB))

        # Add schema.org properties
        if self.title:
            graph.add((uri, SCHEMA.title, Literal(self.title)))
        if self.organization_id:
            org_uri = base_namespace[quote(self.organization_id, safe='')]
            graph.add((uri, SCHEMA.hiringOrganization, org_uri))
        if self.location:
            graph.add((uri, SCHEMA.jobLocation, Literal(self.location)))
        if self.description:
            graph.add((uri, SCHEMA.description, Literal(self.description)))

        # Temporal properties
        if self.start_date:
            graph.add((uri, RelationType.START_DATE, Literal(self.start_date, datatype=XSD.date)))
        if self.end_date:
            graph.add((uri, RelationType.END_DATE, Literal(self.end_date, datatype=XSD.date)))

        # Custom properties
        graph.add((uri, RE.isCurrent, Literal(self.is_current, datatype=XSD.boolean)))

        # Skill relationships
        for skill_id in self.skills_used:
            skill_uri = base_namespace[quote(skill_id, safe='')]
            graph.add((uri, RelationType.USED_SKILL, skill_uri))

        # Technology relationships
        for tech_id in self.technologies_used:
            tech_uri = base_namespace[quote(tech_id, safe='')]
            graph.add((uri, RelationType.USED_TECHNOLOGY, tech_uri))

        # Achievements
        for achievement in self.achievements:
            graph.add((uri, RE.achievement, Literal(achievement)))

        return uri

    def to_dict(self) -> dict:
        """Export Job as dictionary."""
        data = super().to_dict()
        data.update({
            "title": self.title,
            "organization_id": self.organization_id,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "is_current": self.is_current,
            "location": self.location,
            "description": self.description,
            "skills_used": self.skills_used,
            "technologies_used": self.technologies_used,
            "achievements": self.achievements,
            "duration_months": self.duration_months(),
            "duration_years": self.duration_years(),
        })
        return data


__all__ = ["Job"]
