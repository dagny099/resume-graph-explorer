"""
Resume Explorer Graph Module

Exports RDF graph builder, NetworkX adapter, and SKOS vocabularies.
"""

from .vocabularies import (
    SCHEMA,
    ESCO,
    RE,
    RESUME,
    DCTERMS,
    EntityType,
    ESCO_SKILLS,
    ESCO_OCCUPATIONS,
    get_esco_skill_uri,
    get_esco_occupation_uri,
    bind_namespaces
)

from .rdf_graph_builder import RDFGraphBuilder
from .networkx_adapter import NetworkXAdapter

__all__ = [
    # Vocabularies
    'SCHEMA',
    'ESCO',
    'RE',
    'RESUME',
    'DCTERMS',
    'EntityType',
    'ESCO_SKILLS',
    'ESCO_OCCUPATIONS',
    'get_esco_skill_uri',
    'get_esco_occupation_uri',
    'bind_namespaces',

    # Graph builders
    'RDFGraphBuilder',
    'NetworkXAdapter'
]
