"""
SKOS Vocabulary Definitions for Resume Explorer

Hybrid approach using:
- SKOS Core - Base concept scheme
- ESCO - European Skills, Competences, Qualifications and Occupations
- schema.org - Person, Organization, EducationalOrganization
- Custom RE namespace - Resume-specific relationships

This enables semantic web interoperability while allowing project-specific extensions.
"""

from rdflib import Namespace

# ============================================================================
# Standard Vocabularies
# ============================================================================

# SKOS Core - Simple Knowledge Organization System
# https://www.w3.org/2004/02/skos/
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")

# schema.org - Common structured data on the web
# https://schema.org/
SCHEMA = Namespace("http://schema.org/")

# ESCO - European Skills/Competences/Qualifications/Occupations
# https://esco.ec.europa.eu/
ESCO = Namespace("http://data.europa.eu/esco/")

# Dublin Core Terms - Metadata vocabulary
DCTERMS = Namespace("http://purl.org/dc/terms/")

# ============================================================================
# Custom Resume Explorer Namespace
# ============================================================================

# Ontology namespace (for classes and properties)
RE = Namespace("http://resumeexplorer.org/ontology#")

# Resource namespace (for individual entities)
RESUME = Namespace("http://resumeexplorer.org/resource/")

# ============================================================================
# Entity Type Mappings
# ============================================================================


class EntityType:
    """RDF types for Resume Explorer entities."""

    # Core entities
    PERSON = SCHEMA.Person
    JOB = SCHEMA.JobPosting
    ORGANIZATION = SCHEMA.Organization
    EDUCATION = SCHEMA.EducationalOccupationalCredential

    # ESCO-aligned entities
    SKILL = ESCO.Skill
    OCCUPATION = ESCO.Occupation

    # Custom entities
    CERTIFICATION = RE.Certification
    TECHNOLOGY = RE.Technology
    PROJECT = RE.Project


# ============================================================================
# Relationship Types
# ============================================================================


class RelationType:
    """RDF properties for relationships between entities."""

    # Employment relationships
    WORKS_AT = SCHEMA.worksFor
    EMPLOYED_BY = RE.employedBy
    HOLDS_POSITION = RE.holdsPosition

    # Skill relationships
    HAS_SKILL = RE.hasSkill
    USED_SKILL = RE.usedSkill
    REQUIRES_SKILL = SCHEMA.skills

    # Education relationships
    STUDIED_AT = SCHEMA.alumniOf
    HAS_DEGREE = SCHEMA.hasCredential
    HAS_CERTIFICATION = RE.hasCertification

    # Technology relationships
    USED_TECHNOLOGY = RE.usedTechnology
    KNOWS_TECHNOLOGY = RE.knowsTechnology

    # SKOS hierarchical relationships
    BROADER = SKOS.broader
    NARROWER = SKOS.narrower
    RELATED = SKOS.related
    EXACT_MATCH = SKOS.exactMatch

    # Temporal relationships
    START_DATE = SCHEMA.startDate
    END_DATE = SCHEMA.endDate
    DURATION = SCHEMA.duration


# ============================================================================
# ESCO Skill Taxonomy Integration
# ============================================================================

# Sample ESCO skill concept URIs
# Full ESCO taxonomy: https://esco.ec.europa.eu/en/classification/skill_main
# Note: These are examples. In production, query ESCO API or download full taxonomy.

ESCO_SKILLS = {
    # Programming Languages
    "python": "http://data.europa.eu/esco/skill/c3b1499e-77e4-42e8-be6f-676e9f1b7c91",
    "javascript": "http://data.europa.eu/esco/skill/c8b1b3e4-92c5-4e8a-8c5e-7c5e8b1b3e4a",
    "java": "http://data.europa.eu/esco/skill/a8b1b3e4-92c5-4e8a-8c5e-7c5e8b1b3e4b",
    "sql": "http://data.europa.eu/esco/skill/d8b1b3e4-92c5-4e8a-8c5e-7c5e8b1b3e4c",
    "r": "http://data.europa.eu/esco/skill/e8b1b3e4-92c5-4e8a-8c5e-7c5e8b1b3e4d",

    # Data Science & Machine Learning
    "machine_learning": "http://data.europa.eu/esco/skill/f8b1b3e4-92c5-4e8a-8c5e-7c5e8b1b3e4e",
    "data_analysis": "http://data.europa.eu/esco/skill/g8b1b3e4-92c5-4e8a-8c5e-7c5e8b1b3e4f",
    "statistical_analysis": "http://data.europa.eu/esco/skill/h8b1b3e4-92c5-4e8a-8c5e-7c5e8b1b3e4g",
    "data_visualization": "http://data.europa.eu/esco/skill/i8b1b3e4-92c5-4e8a-8c5e-7c5e8b1b3e4h",

    # Cloud & DevOps
    "aws": "http://data.europa.eu/esco/skill/j8b1b3e4-92c5-4e8a-8c5e-7c5e8b1b3e4i",
    "azure": "http://data.europa.eu/esco/skill/k8b1b3e4-92c5-4e8a-8c5e-7c5e8b1b3e4j",
    "docker": "http://data.europa.eu/esco/skill/l8b1b3e4-92c5-4e8a-8c5e-7c5e8b1b3e4k",
    "kubernetes": "http://data.europa.eu/esco/skill/m8b1b3e4-92c5-4e8a-8c5e-7c5e8b1b3e4l",

    # Soft Skills
    "leadership": "http://data.europa.eu/esco/skill/n8b1b3e4-92c5-4e8a-8c5e-7c5e8b1b3e4m",
    "communication": "http://data.europa.eu/esco/skill/o8b1b3e4-92c5-4e8a-8c5e-7c5e8b1b3e4n",
    "problem_solving": "http://data.europa.eu/esco/skill/p8b1b3e4-92c5-4e8a-8c5e-7c5e8b1b3e4o",
    "teamwork": "http://data.europa.eu/esco/skill/q8b1b3e4-92c5-4e8a-8c5e-7c5e8b1b3e4p",
}

# ESCO Occupation concept URIs
ESCO_OCCUPATIONS = {
    "data_scientist": "http://data.europa.eu/esco/occupation/8b1b3e4a-92c5-4e8a-8c5e-7c5e8b1b3e4q",
    "software_engineer": "http://data.europa.eu/esco/occupation/9b1b3e4a-92c5-4e8a-8c5e-7c5e8b1b3e4r",
    "data_analyst": "http://data.europa.eu/esco/occupation/a1b3e4a-92c5-4e8a-8c5e-7c5e8b1b3e4s",
    "machine_learning_engineer": "http://data.europa.eu/esco/occupation/b1b3e4a-92c5-4e8a-8c5e-7c5e8b1b3e4t",
    "research_scientist": "http://data.europa.eu/esco/occupation/c1b3e4a-92c5-4e8a-8c5e-7c5e8b1b3e4u",
}

# ============================================================================
# Skill Taxonomy Hierarchy
# ============================================================================

# Skill categories following ESCO classification
SKILL_CATEGORIES = {
    "technical": {
        "label": "Technical Skills",
        "broader": None,
        "narrower": [
            "programming",
            "data_science",
            "cloud_infrastructure",
            "databases",
        ],
    },
    "programming": {
        "label": "Programming Languages",
        "broader": "technical",
        "narrower": ["python", "javascript", "java", "sql", "r"],
    },
    "data_science": {
        "label": "Data Science",
        "broader": "technical",
        "narrower": [
            "machine_learning",
            "data_analysis",
            "statistical_analysis",
            "data_visualization",
        ],
    },
    "cloud_infrastructure": {
        "label": "Cloud Infrastructure",
        "broader": "technical",
        "narrower": ["aws", "azure", "docker", "kubernetes"],
    },
    "soft_skills": {
        "label": "Soft Skills",
        "broader": None,
        "narrower": [
            "leadership",
            "communication",
            "problem_solving",
            "teamwork",
        ],
    },
}


# ============================================================================
# Helper Functions
# ============================================================================


def get_esco_skill_uri(skill_name: str) -> str:
    """
    Get ESCO URI for a skill name (normalized).

    Args:
        skill_name: Skill name (e.g., "Python", "Machine Learning")

    Returns:
        ESCO URI if found, otherwise None

    Example:
        >>> get_esco_skill_uri("Python")
        'http://data.europa.eu/esco/skill/c3b1499e-77e4-42e8-be6f-676e9f1b7c91'
    """
    normalized = skill_name.lower().replace(" ", "_")
    return ESCO_SKILLS.get(normalized)


def get_esco_occupation_uri(occupation_name: str) -> str:
    """
    Get ESCO URI for an occupation name (normalized).

    Args:
        occupation_name: Occupation name (e.g., "Data Scientist")

    Returns:
        ESCO URI if found, otherwise None
    """
    normalized = occupation_name.lower().replace(" ", "_")
    return ESCO_OCCUPATIONS.get(normalized)


def get_skill_hierarchy(skill_name: str) -> dict:
    """
    Get hierarchical information for a skill.

    Args:
        skill_name: Skill name

    Returns:
        Dictionary with broader/narrower concepts
    """
    normalized = skill_name.lower().replace(" ", "_")
    return SKILL_CATEGORIES.get(normalized, {})


# ============================================================================
# Namespace Bindings for RDF Graphs
# ============================================================================


def bind_namespaces(graph):
    """
    Bind all standard and custom namespaces to an RDF graph.

    Args:
        graph: rdflib.Graph instance

    Example:
        >>> from rdflib import Graph
        >>> g = Graph()
        >>> bind_namespaces(g)
    """
    graph.bind("skos", SKOS)
    graph.bind("schema", SCHEMA)
    graph.bind("esco", ESCO)
    graph.bind("dcterms", DCTERMS)
    graph.bind("re", RE)
    graph.bind("resume", RESUME)


# Export public API
__all__ = [
    # Namespaces
    "SKOS",
    "SCHEMA",
    "ESCO",
    "DCTERMS",
    "RE",
    "RESUME",
    # Types
    "EntityType",
    "RelationType",
    # ESCO Integration
    "ESCO_SKILLS",
    "ESCO_OCCUPATIONS",
    "SKILL_CATEGORIES",
    # Helper Functions
    "get_esco_skill_uri",
    "get_esco_occupation_uri",
    "get_skill_hierarchy",
    "bind_namespaces",
]
