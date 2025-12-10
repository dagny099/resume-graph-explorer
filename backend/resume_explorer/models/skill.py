"""
Skill Entity - Represents a skill or competency

Maps to esco:Skill from ESCO taxonomy
"""

from dataclasses import dataclass
from typing import Optional

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF

from .base import SKOSEntity
from ..graph.vocabularies import ESCO, EntityType, RE, get_esco_skill_uri, get_skill_hierarchy


@dataclass
class Skill(SKOSEntity):
    """
    Represents a skill or competency.

    Maps to esco:Skill (http://data.europa.eu/esco/skill).
    Uses SKOS hierarchy for skill taxonomies.

    Attributes:
        category: Skill category (e.g., "Technical", "Soft Skill", "Domain")
        proficiency_level: Proficiency level (e.g., "Expert", "Intermediate", "Beginner")
        years_experience: Years of experience with this skill

    SKOS Hierarchy Example:
        - "Python" broader: "Programming Languages"
        - "Python" related: "Data Science", "Machine Learning"
        - "Python" exactMatch: http://dbpedia.org/resource/Python_(programming_language)
    """

    category: Optional[str] = None  # e.g., "Technical", "Soft Skill"
    proficiency_level: Optional[str] = None  # e.g., "Expert", "Intermediate"
    years_experience: Optional[float] = None

    def __post_init__(self):
        """
        Post-initialization: attempt to link to ESCO taxonomy.

        If no skos_uri is provided, try to find one from ESCO.
        Also populate broader/narrower concepts from skill hierarchy.
        """
        # Try to link to ESCO if not already linked
        if not self.skos_uri and self.label:
            esco_uri = get_esco_skill_uri(self.label)
            if esco_uri:
                self.skos_uri = esco_uri

        # Populate skill hierarchy if available
        if self.label and not self.broader_concepts and not self.narrower_concepts:
            hierarchy = get_skill_hierarchy(self.label)
            if hierarchy:
                broader = hierarchy.get("broader")
                if broader and broader not in self.broader_concepts:
                    self.broader_concepts.append(broader)

                narrower_list = hierarchy.get("narrower", [])
                for narrower in narrower_list:
                    if narrower not in self.narrower_concepts:
                        self.narrower_concepts.append(narrower)

    def to_rdf(self, graph: Graph, base_namespace: Namespace) -> URIRef:
        """
        Add Skill to RDF graph with ESCO properties.

        Args:
            graph: RDF graph
            base_namespace: Base namespace for URIs

        Returns:
            URIRef of the skill entity
        """
        # Add base SKOS properties
        uri = super().to_rdf(graph, base_namespace)

        # Add RDF type
        graph.add((uri, RDF.type, EntityType.SKILL))

        # Add custom properties
        if self.category:
            graph.add((uri, RE.skillCategory, Literal(self.category)))
        if self.proficiency_level:
            graph.add((uri, RE.proficiencyLevel, Literal(self.proficiency_level)))
        if self.years_experience is not None:
            graph.add((uri, RE.yearsExperience, Literal(self.years_experience)))

        return uri

    def to_dict(self) -> dict:
        """Export Skill as dictionary."""
        data = super().to_dict()
        data.update({
            "category": self.category,
            "proficiency_level": self.proficiency_level,
            "years_experience": self.years_experience,
        })
        return data


__all__ = ["Skill"]
