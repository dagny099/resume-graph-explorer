"""
SKOS-Compliant Base Entity Class

Provides foundation for all Resume Explorer entities with:
- RDF serialization support
- SKOS hierarchical relationships (broader, narrower, related)
- Provenance tracking (confidence, source)
- JSON export for API compatibility
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from urllib.parse import quote

from rdflib import URIRef, Literal, Graph, Namespace
from rdflib.namespace import RDF, RDFS, SKOS, XSD

from ..graph.vocabularies import SCHEMA, RE, RESUME


@dataclass
class SKOSEntity:
    """
    Base class for all SKOS-compliant entities in Resume Explorer.

    Every entity:
    - Has a unique identifier (UUID)
    - Has a preferred label (SKOS prefLabel)
    - Can have an optional definition (SKOS definition)
    - Can reference external SKOS vocabularies (SKOS exactMatch)
    - Supports hierarchical relationships (broader, narrower, related)
    - Tracks provenance (confidence, source document)
    - Exports to RDF and JSON

    Attributes:
        id: Unique identifier (UUID string)
        label: Preferred label (SKOS prefLabel)
        definition: Optional textual definition (SKOS definition)
        skos_uri: Optional URI to external SKOS concept (SKOS exactMatch)
        broader_concepts: List of broader concept IDs (SKOS broader)
        narrower_concepts: List of narrower concept IDs (SKOS narrower)
        related_concepts: List of related concept IDs (SKOS related)
        created_at: Timestamp of creation
        confidence: Extraction confidence score (0.0-1.0)
        source_doc: Source document filename/path
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    label: str = ""
    definition: Optional[str] = None
    skos_uri: Optional[str] = None

    # SKOS hierarchical relationships
    broader_concepts: List[str] = field(default_factory=list)
    narrower_concepts: List[str] = field(default_factory=list)
    related_concepts: List[str] = field(default_factory=list)

    # Provenance & metadata
    created_at: datetime = field(default_factory=datetime.now)
    confidence: float = 1.0  # 0.0 = low confidence, 1.0 = high confidence
    source_doc: str = ""

    # Human feedback — foundation for future editable nodes UI
    user_verified: bool = False  # user confirmed this entity is correct
    user_notes: Optional[str] = None  # freeform user annotation

    def get_uri(self, base_namespace: Namespace = RESUME) -> URIRef:
        """
        Generate RDF URI for this entity.

        Args:
            base_namespace: Namespace for resource URIs (default: RESUME)

        Returns:
            URIRef for this entity

        Example:
            >>> entity = SKOSEntity(id="abc-123", label="Python")
            >>> str(entity.get_uri())
            'http://resumeexplorer.org/resource/abc-123'
        """
        # URL-encode the ID to handle spaces and special characters
        encoded_id = quote(self.id, safe='')
        return base_namespace[encoded_id]

    def to_rdf(self, graph: Graph, base_namespace: Namespace = RESUME) -> URIRef:
        """
        Add this entity to an RDF graph with SKOS properties.

        Args:
            graph: rdflib.Graph to add triples to
            base_namespace: Namespace for resource URIs

        Returns:
            URIRef of the added entity

        Example:
            >>> from rdflib import Graph
            >>> g = Graph()
            >>> entity = SKOSEntity(id="skill-1", label="Python Programming")
            >>> uri = entity.to_rdf(g)
            >>> len(g)  # Number of triples added
            3
        """
        uri = self.get_uri(base_namespace)

        # Core SKOS properties
        graph.add((uri, SKOS.prefLabel, Literal(self.label)))

        if self.definition:
            graph.add((uri, SKOS.definition, Literal(self.definition)))

        if self.skos_uri:
            graph.add((uri, SKOS.exactMatch, URIRef(self.skos_uri)))

        # SKOS hierarchical relationships
        for broader_id in self.broader_concepts:
            broader_uri = base_namespace[quote(broader_id, safe='')]
            graph.add((uri, SKOS.broader, broader_uri))

        for narrower_id in self.narrower_concepts:
            narrower_uri = base_namespace[quote(narrower_id, safe='')]
            graph.add((uri, SKOS.narrower, narrower_uri))

        for related_id in self.related_concepts:
            related_uri = base_namespace[quote(related_id, safe='')]
            graph.add((uri, SKOS.related, related_uri))

        # Provenance metadata
        graph.add((uri, RE.confidence, Literal(self.confidence)))
        if self.source_doc:
            graph.add((uri, RE.sourceDocument, Literal(self.source_doc)))
        graph.add((uri, RE.createdAt, Literal(self.created_at, datatype=XSD.dateTime)))

        return uri

    def to_dict(self) -> Dict[str, Any]:
        """
        Export entity as JSON-serializable dictionary.

        Returns:
            Dictionary with all entity fields

        Example:
            >>> entity = SKOSEntity(id="skill-1", label="Python")
            >>> data = entity.to_dict()
            >>> data['label']
            'Python'
        """
        return {
            "id": self.id,
            "label": self.label,
            "definition": self.definition,
            "skos_uri": self.skos_uri,
            "broader_concepts": self.broader_concepts,
            "narrower_concepts": self.narrower_concepts,
            "related_concepts": self.related_concepts,
            "confidence": self.confidence,
            "source_doc": self.source_doc,
            "created_at": self.created_at.isoformat(),
            "user_verified": self.user_verified,
            "user_notes": self.user_notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SKOSEntity":
        """
        Create entity from dictionary.

        Args:
            data: Dictionary with entity fields

        Returns:
            SKOSEntity instance

        Example:
            >>> data = {"id": "skill-1", "label": "Python", "confidence": 0.95}
            >>> entity = SKOSEntity.from_dict(data)
            >>> entity.label
            'Python'
        """
        # Handle datetime parsing
        if "created_at" in data and isinstance(data["created_at"], str):
            from ..models.datetime_manager import DateTimeManager
            data["created_at"] = DateTimeManager.normalize_to_datetime(data["created_at"])

        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def add_broader_concept(self, concept_id: str):
        """
        Add a broader concept relationship.

        Args:
            concept_id: ID of the broader concept
        """
        if concept_id not in self.broader_concepts:
            self.broader_concepts.append(concept_id)

    def add_narrower_concept(self, concept_id: str):
        """
        Add a narrower concept relationship.

        Args:
            concept_id: ID of the narrower concept
        """
        if concept_id not in self.narrower_concepts:
            self.narrower_concepts.append(concept_id)

    def add_related_concept(self, concept_id: str):
        """
        Add a related concept relationship.

        Args:
            concept_id: ID of the related concept
        """
        if concept_id not in self.related_concepts:
            self.related_concepts.append(concept_id)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"{self.__class__.__name__}(id='{self.id}', label='{self.label}')"


# Export
__all__ = ["SKOSEntity"]
