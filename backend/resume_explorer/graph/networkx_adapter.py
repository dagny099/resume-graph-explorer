"""
NetworkX Adapter for Vis.js Visualization

Converts RDF graph to NetworkX format, then to Vis.js compatible JSON.
Provides interactive graph visualization data for the frontend.
"""

import networkx as nx
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, SKOS
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict

from .vocabularies import SCHEMA, ESCO, RE, RESUME, EntityType
from ..utils.logger import logger


class NetworkXAdapter:
    """
    Converts RDF graph to NetworkX and Vis.js compatible format.

    Features:
    - Node grouping by entity type (for coloring)
    - Edge labeling with relationship types
    - Hierarchical layout hints
    - Interactive tooltips
    - Confidence visualization
    """

    # Color scheme for entity types
    ENTITY_COLORS = {
        'person': '#FF6B6B',       # Red
        'job': '#4ECDC4',          # Teal
        'skill': '#45B7D1',        # Blue
        'education': '#96CEB4',    # Green
        'certification': '#FFEAA7', # Yellow
        'organization': '#DDA15E', # Orange
        'unknown': '#95A5A6'       # Gray
    }

    # Node shapes by entity type
    ENTITY_SHAPES = {
        'person': 'diamond',
        'job': 'box',
        'skill': 'ellipse',
        'education': 'box',
        'certification': 'ellipse',
        'organization': 'box',
        'unknown': 'dot'
    }

    def __init__(self, rdf_graph: Graph):
        """
        Initialize adapter with RDF graph.

        Args:
            rdf_graph: RDFLib Graph instance
        """
        self.rdf_graph = rdf_graph
        self.nx_graph = nx.MultiDiGraph()
        self.node_cache: Dict[str, Dict] = {}
        self.edge_cache: List[Dict] = []

        logger.info("NetworkXAdapter initialized")

    def convert(self) -> Dict[str, Any]:
        """
        Convert RDF graph to Vis.js compatible JSON format.

        Returns:
            Dictionary with 'nodes' and 'edges' arrays for Vis.js
        """
        logger.info("Converting RDF graph to Vis.js format")

        nodes_dict = {}
        edges_list = []

        # Process all triples
        for subj, pred, obj in self.rdf_graph:
            # Create subject node
            if isinstance(subj, URIRef):
                subj_str = str(subj)
                if subj_str not in nodes_dict:
                    nodes_dict[subj_str] = self._create_node(subj)

            # Create object node if it's a URI (not a literal)
            # Only visualize object nodes/edges for relationship triples
            if isinstance(obj, URIRef) and pred not in {SKOS.exactMatch, RDF.type}:
                obj_str = str(obj)
                if obj_str not in nodes_dict:
                    nodes_dict[obj_str] = self._create_node(obj)

                # Create edge
                edge = self._create_edge(subj, pred, obj)
                edges_list.append(edge)

        # Convert dict to list
        nodes_list = list(nodes_dict.values())

        # Compute edge statistics
        edge_stats = self._count_edge_statistics(edges_list)

        result = {
            'nodes': nodes_list,
            'edges': edges_list,
            'stats': {
                'node_count': len(nodes_list),
                'edge_count': len(edges_list),
                'entity_type_counts': self._count_entity_types(nodes_list),
                'edge_type_counts': edge_stats['edge_type_counts'],
                'predicate_counts': edge_stats['predicate_counts'],
                'predicates_by_edge_type': edge_stats['predicates_by_edge_type']
            }
        }

        logger.info(f"Converted graph: {len(nodes_list)} nodes, {len(edges_list)} edges")
        return result

    def _create_node(self, uri: URIRef) -> Dict[str, Any]:
        """
        Create Vis.js node from RDF URI.

        Args:
            uri: RDF URI reference

        Returns:
            Node dictionary for Vis.js
        """
        uri_str = str(uri)

        # Get node label (prefer skos:prefLabel, then schema:name, then URI)
        label = self._get_node_label(uri)

        # Determine entity type
        entity_type = self._get_entity_type(uri)

        # Get confidence if available
        confidence = self._get_node_confidence(uri)

        # Build tooltip with all properties
        tooltip = self._build_node_tooltip(uri, label, entity_type, confidence)

        # Create node
        node = {
            'id': uri_str,
            'label': label,
            'group': entity_type,
            'title': tooltip,  # Hover tooltip
            'shape': self.ENTITY_SHAPES.get(entity_type, 'dot'),
            'color': {
                'background': self.ENTITY_COLORS.get(entity_type, '#95A5A6'),
                'border': self._get_border_color(confidence)
            },
            'font': {
                'size': self._get_font_size(entity_type)
            },
            'value': self._get_node_size(entity_type, confidence),
            'metadata': {
                'uri': uri_str,
                'entity_type': entity_type,
                'confidence': confidence
            }
        }

        return node

    def _create_edge(self, subj: URIRef, pred: URIRef, obj: URIRef) -> Dict[str, Any]:
        """
        Create Vis.js edge from RDF triple.

        Args:
            subj: Subject URI
            pred: Predicate URI
            obj: Object URI

        Returns:
            Edge dictionary for Vis.js
        """
        # Get readable edge label
        edge_label = self._get_predicate_label(pred)

        # Determine edge type/color
        edge_type = self._classify_edge(pred)

        edge = {
            'from': str(subj),
            'to': str(obj),
            'label': edge_label,
            'arrows': 'to',
            'color': self._get_edge_color(edge_type),
            'width': self._get_edge_width(edge_type),
            'smooth': {
                'type': 'curvedCW',
                'roundness': 0.2
            },
            'metadata': {
                'predicate': str(pred),
                'edge_type': edge_type
            }
        }

        return edge

    def _get_node_label(self, uri: URIRef) -> str:
        """Get readable label for node."""
        # Try SKOS prefLabel
        label = self.rdf_graph.value(uri, SKOS.prefLabel)
        if label:
            return str(label)

        # Try schema:name
        label = self.rdf_graph.value(uri, SCHEMA.name)
        if label:
            return str(label)

        # Try schema:title (for jobs)
        label = self.rdf_graph.value(uri, SCHEMA.title)
        if label:
            return str(label)

        # Use last part of URI
        uri_str = str(uri)
        if '#' in uri_str:
            return uri_str.split('#')[-1]
        elif '/' in uri_str:
            return uri_str.split('/')[-1]
        else:
            return uri_str

    def _get_entity_type(self, uri: URIRef) -> str:
        """Determine entity type from RDF type."""
        rdf_type = self.rdf_graph.value(uri, RDF.type)

        if not rdf_type:
            return 'unknown'

        type_map = {
            EntityType.PERSON: 'person',
            EntityType.JOB: 'job',
            EntityType.SKILL: 'skill',
            EntityType.EDUCATION: 'education',
            EntityType.CERTIFICATION: 'certification',
            EntityType.ORGANIZATION: 'organization'
        }

        return type_map.get(rdf_type, 'unknown')

    def _get_node_confidence(self, uri: URIRef) -> float:
        """Get confidence score for node."""
        confidence = self.rdf_graph.value(uri, RE.confidence)
        if confidence:
            try:
                return float(confidence)
            except (ValueError, TypeError):
                pass
        return 1.0

    def _build_node_tooltip(self, uri: URIRef, label: str, entity_type: str, confidence: float) -> str:
        """Build HTML tooltip for node hover."""
        lines = [f"<b>{label}</b>"]
        lines.append(f"<i>Type: {entity_type}</i>")

        # Add type-specific properties
        if entity_type == 'person':
            email = self.rdf_graph.value(uri, SCHEMA.email)
            if email:
                lines.append(f"Email: {email}")
            location = self.rdf_graph.value(uri, SCHEMA.address)
            if location:
                lines.append(f"Location: {location}")

        elif entity_type == 'job':
            title = self.rdf_graph.value(uri, SCHEMA.title)
            org = self.rdf_graph.value(uri, SCHEMA.hiringOrganization)
            if title:
                lines.append(f"Title: {title}")
            if org:
                org_name = self._get_node_label(org)
                lines.append(f"Organization: {org_name}")

        elif entity_type == 'skill':
            category = self.rdf_graph.value(uri, RE.skillCategory)
            proficiency = self.rdf_graph.value(uri, RE.proficiencyLevel)
            if category:
                lines.append(f"Category: {category}")
            if proficiency:
                lines.append(f"Proficiency: {proficiency}")

        elif entity_type == 'education':
            degree = self.rdf_graph.value(uri, SCHEMA.credentialCategory)
            field = self.rdf_graph.value(uri, SCHEMA.educationalCredentialAwarded)
            if degree:
                lines.append(f"Degree: {degree}")
            if field:
                lines.append(f"Field: {field}")

        # Add confidence
        if confidence < 1.0:
            lines.append(f"Confidence: {confidence:.0%}")

        return "<br>".join(lines)

    def _get_border_color(self, confidence: float) -> str:
        """Get border color based on confidence."""
        if confidence >= 0.9:
            return '#2E7D32'  # Dark green
        elif confidence >= 0.7:
            return '#F9A825'  # Dark yellow
        else:
            return '#C62828'  # Dark red

    def _get_font_size(self, entity_type: str) -> int:
        """Get font size based on entity type."""
        if entity_type == 'person':
            return 18
        elif entity_type in ['job', 'organization']:
            return 14
        else:
            return 12

    def _get_node_size(self, entity_type: str, confidence: float) -> int:
        """Get node size based on entity type and confidence."""
        base_size = {
            'person': 30,
            'job': 20,
            'organization': 20,
            'skill': 15,
            'education': 15,
            'certification': 15,
            'unknown': 10
        }.get(entity_type, 10)

        # Adjust by confidence
        return int(base_size * (0.7 + 0.3 * confidence))

    def _get_predicate_label(self, pred: URIRef) -> str:
        """Get readable label for predicate."""
        pred_str = str(pred)

        # Map common predicates to labels
        label_map = {
            str(RE.hasJob): 'has job',
            str(RE.hasSkill): 'has skill',
            str(RE.hasCertification): 'has certification',
            str(SCHEMA.alumniOf): 'alumni of',
            str(SCHEMA.hiringOrganization): 'works at',
            str(RE.usedSkill): 'uses skill',
            str(RE.usedTechnology): 'uses tech',
            str(SCHEMA.recognizedBy): 'from',
            str(SKOS.broader): 'broader than',
            str(SKOS.narrower): 'narrower than',
            str(SKOS.related): 'related to',
            str(RDF.type): 'type'
        }

        if pred_str in label_map:
            return label_map[pred_str]

        # Use last part of URI
        if '#' in pred_str:
            return pred_str.split('#')[-1]
        elif '/' in pred_str:
            return pred_str.split('/')[-1]
        else:
            return pred_str

    def _classify_edge(self, pred: URIRef) -> str:
        """
        Classify edge type for visualization styling.
        
        Custom classification scheme for Resume Explorer:
        - ownership: Person possesses/has something (hasJob, hasSkill, etc.)
        - organizational: Connections to organizations
        - usage: Application/use of skills or technology
        - hierarchical: Taxonomy relationships (SKOS)
        - typing: RDF type declarations
        - other: Uncategorized relationships
        """
        pred_str = str(pred)

        if pred_str in [str(RE.hasJob), str(RE.hasSkill), str(RE.hasCertification), str(SCHEMA.alumniOf)]:
            return 'ownership'
        elif pred_str in [str(SCHEMA.hiringOrganization), str(SCHEMA.recognizedBy)]:
            return 'organizational'
        elif pred_str in [str(RE.usedSkill), str(RE.usedTechnology)]:
            return 'usage'
        elif pred_str in [str(SKOS.broader), str(SKOS.narrower), str(SKOS.related)]:
            return 'hierarchical'
        elif pred_str == str(RDF.type):
            return 'typing'
        else:
            return 'other'

    def _get_edge_color(self, edge_type: str) -> str:
        """Get edge color based on type."""
        color_map = {
            'ownership': '#2E7D32',      # Green
            'organizational': '#1565C0', # Blue
            'usage': '#6A1B9A',          # Purple
            'hierarchical': '#EF6C00',   # Orange
            'typing': '#BDBDBD',         # Gray
            'other': '#757575'           # Dark gray
        }
        return color_map.get(edge_type, '#757575')

    def _get_edge_width(self, edge_type: str) -> int:
        """Get edge width based on type."""
        width_map = {
            'ownership': 3,
            'organizational': 2,
            'usage': 2,
            'hierarchical': 1,
            'typing': 1,
            'other': 1
        }
        return width_map.get(edge_type, 1)

    def _count_entity_types(self, nodes: List[Dict]) -> Dict[str, int]:
        """Count nodes by entity type."""
        counts = defaultdict(int)
        for node in nodes:
            entity_type = node.get('group', 'unknown')
            counts[entity_type] += 1
        return dict(counts)

    def _count_edge_statistics(self, edges: List[Dict]) -> Dict[str, Dict[str, int]]:
        """
        Count edges by type and predicate.

        Args:
            edges: List of edge dictionaries with metadata

        Returns:
            Dictionary with edge_type_counts, predicate_counts, and predicates_by_edge_type
        """
        edge_type_counts = defaultdict(int)
        predicate_counts = defaultdict(int)
        predicates_by_edge_type = defaultdict(lambda: defaultdict(int))

        for edge in edges:
            # Count by edge type classification
            edge_type = edge.get('metadata', {}).get('edge_type', 'other')
            edge_type_counts[edge_type] += 1

            # Count by specific predicate
            predicate_uri = edge.get('metadata', {}).get('predicate', 'unknown')
            if predicate_uri and predicate_uri != 'unknown':
                predicate_label = self._get_predicate_label(URIRef(predicate_uri))
                predicate_counts[predicate_label] += 1
                # Group predicate under its edge type
                predicates_by_edge_type[edge_type][predicate_label] += 1
            else:
                predicate_counts['unknown'] += 1
                predicates_by_edge_type[edge_type]['unknown'] += 1

        return {
            'edge_type_counts': dict(edge_type_counts),
            'predicate_counts': dict(predicate_counts),
            'predicates_by_edge_type': {k: dict(v) for k, v in predicates_by_edge_type.items()}
        }

    def to_networkx(self) -> nx.MultiDiGraph:
        """
        Convert RDF graph to NetworkX MultiDiGraph.

        Returns:
            NetworkX graph
        """
        logger.info("Converting RDF to NetworkX")

        for subj, pred, obj in self.rdf_graph:
            if isinstance(subj, URIRef) and isinstance(obj, URIRef):
                # Add nodes
                self.nx_graph.add_node(
                    str(subj),
                    label=self._get_node_label(subj),
                    entity_type=self._get_entity_type(subj)
                )
                self.nx_graph.add_node(
                    str(obj),
                    label=self._get_node_label(obj),
                    entity_type=self._get_entity_type(obj)
                )

                # Add edge
                self.nx_graph.add_edge(
                    str(subj),
                    str(obj),
                    predicate=str(pred),
                    label=self._get_predicate_label(pred)
                )

        logger.info(f"NetworkX graph: {self.nx_graph.number_of_nodes()} nodes, "
                   f"{self.nx_graph.number_of_edges()} edges")

        return self.nx_graph

    def get_subgraph(self, center_uri: str, depth: int = 1) -> Dict[str, Any]:
        """
        Get subgraph centered on a specific entity.

        Args:
            center_uri: URI of center node
            depth: Number of hops from center (default 1)

        Returns:
            Vis.js format subgraph
        """
        if not self.nx_graph.number_of_nodes():
            self.to_networkx()

        # Get ego graph (subgraph within depth)
        try:
            ego = nx.ego_graph(self.nx_graph, center_uri, radius=depth, undirected=True)
        except nx.NetworkXError:
            logger.warning(f"Node {center_uri} not found in graph")
            return {'nodes': [], 'edges': []}

        # Convert to Vis.js format
        nodes = []
        edges = []

        for node in ego.nodes():
            uri = URIRef(node)
            nodes.append(self._create_node(uri))

        for u, v, key, data in ego.edges(keys=True, data=True):
            pred = URIRef(data.get('predicate', ''))
            edges.append(self._create_edge(URIRef(u), pred, URIRef(v)))

        return {
            'nodes': nodes,
            'edges': edges,
            'center': center_uri,
            'depth': depth
        }


__all__ = ['NetworkXAdapter']
