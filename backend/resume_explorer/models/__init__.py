"""
Resume Explorer Data Models

SKOS-compliant entity models for resume knowledge graph.

All models inherit from SKOSEntity and support:
- RDF serialization (to_rdf)
- JSON serialization (to_dict)
- SKOS hierarchical relationships
- Provenance tracking
"""

from .base import SKOSEntity
from .person import Person
from .job import Job
from .skill import Skill
from .education import Education
from .certification import Certification
from .organization import Organization

__all__ = [
    "SKOSEntity",
    "Person",
    "Job",
    "Skill",
    "Education",
    "Certification",
    "Organization",
]
