"""
Semantic Integrity Validator for Resume Explorer RDF Graphs

Pragmatic (non-SHACL) validation of a built RDF graph. Checks that the
graph is internally consistent and semantically complete:

Errors (graph is structurally wrong — downstream consumers will misbehave):
  - dangling_reference:      a relationship points at an in-namespace URI
                             that was never materialized as a typed node
  - missing_label:           a typed entity has no (or an empty) skos:prefLabel
  - type_missing_in_export:  extraction produced entities of a type, but the
                             graph contains none of them

Warnings (suspicious but sometimes legitimate):
  - skos_dangling:           skos:broader/narrower/related targets that are
                             not materialized (skill hierarchy hints often
                             reference concepts that have no node)
  - job_missing_organization / job_missing_dates / job_no_technologies
  - near_duplicate_skills:   skill prefLabels that collapse to the same key
                             after punctuation/case stripping — a sign that
                             normalization missed a variant
  - low_entity_count:        graph has fewer than half the extracted entities
                             of a type (dedup can merge some, but losing more
                             than half deserves a look)
  - no_person:               graph contains no Person node

Usage:
    validator = GraphValidator(builder.graph)
    report = validator.validate(extracted_counts={'skill': 12, 'job': 4, ...})
    if not report['valid']:
        ...

The report is a plain dict (JSON-serializable) so it can be returned from
an API endpoint or asserted against in tests.
"""

import re
from collections import defaultdict
from typing import Dict, List, Optional

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, SKOS

from .vocabularies import SCHEMA, RE, RESUME, EntityType

# Entity types we expect to find in a session graph, keyed by short name
_ENTITY_TYPES = {
    'person': EntityType.PERSON,
    'job': EntityType.JOB,
    'skill': EntityType.SKILL,
    'education': EntityType.EDUCATION,
    'certification': EntityType.CERTIFICATION,
    'organization': EntityType.ORGANIZATION,
}

# Relationship predicates whose objects must be materialized, typed nodes
_CORE_RELATIONS = [
    RE.hasJob,
    RE.hasSkill,
    RE.hasCertification,
    RE.usedSkill,
    SCHEMA.hiringOrganization,
    SCHEMA.alumniOf,
    SCHEMA.recognizedBy,
]

# SKOS hierarchy predicates — dangling targets are common (hierarchy hints),
# so these are reported as warnings rather than errors
_SKOS_RELATIONS = [SKOS.broader, SKOS.narrower, SKOS.related]


class GraphValidator:
    """Validates semantic integrity of a Resume Explorer RDF graph."""

    def __init__(self, graph: Graph, base_namespace=RESUME):
        self.graph = graph
        self.base_namespace = str(base_namespace)

    def validate(self, extracted_counts: Optional[Dict[str, int]] = None) -> dict:
        """
        Run all checks and return a validation report.

        Args:
            extracted_counts: Optional raw entity counts from extraction
                (keys: person, job, skill, education, certification,
                organization). Enables completeness checks comparing the
                graph against what extraction actually produced.

        Returns:
            {
                'valid': bool,            # True if no errors (warnings allowed)
                'errors': [issue, ...],
                'warnings': [issue, ...],
                'stats': {'triple_count': int, 'entity_counts': {...}},
            }
            where each issue is {'check': str, 'message': str, 'subject': str}.
        """
        errors: List[dict] = []
        warnings: List[dict] = []

        typed_subjects = self._typed_subjects()
        entity_counts = {
            name: len(self._subjects_of_type(uri))
            for name, uri in _ENTITY_TYPES.items()
        }

        self._check_dangling_references(typed_subjects, errors, warnings)
        self._check_missing_labels(typed_subjects, errors)
        self._check_jobs(warnings)
        self._check_near_duplicate_skills(warnings)

        if entity_counts['person'] == 0:
            warnings.append(_issue('no_person', 'Graph contains no Person node', ''))

        if extracted_counts:
            self._check_completeness(entity_counts, extracted_counts, errors, warnings)

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'stats': {
                'triple_count': len(self.graph),
                'entity_counts': entity_counts,
            },
        }

    # ─── Individual checks ───────────────────────────────────────────────────

    def _typed_subjects(self) -> set:
        """All subjects that have an rdf:type triple."""
        return set(self.graph.subjects(RDF.type, None))

    def _subjects_of_type(self, type_uri) -> set:
        return set(self.graph.subjects(RDF.type, type_uri))

    def _check_dangling_references(self, typed_subjects, errors, warnings):
        """Relationship objects in our namespace must be materialized nodes."""
        for predicates, sink, check in (
            (_CORE_RELATIONS, errors, 'dangling_reference'),
            (_SKOS_RELATIONS, warnings, 'skos_dangling'),
        ):
            for pred in predicates:
                for subj, obj in self.graph.subject_objects(pred):
                    if not isinstance(obj, URIRef):
                        continue
                    if not str(obj).startswith(self.base_namespace):
                        continue  # external URIs (ESCO etc.) are fine
                    if obj not in typed_subjects:
                        sink.append(_issue(
                            check,
                            f"{_qname(pred)} points at {obj}, which has no typed node in the graph",
                            str(subj),
                        ))

    def _check_missing_labels(self, typed_subjects, errors):
        """Every typed entity should carry a non-empty skos:prefLabel."""
        entity_uris = set()
        for type_uri in _ENTITY_TYPES.values():
            entity_uris |= self._subjects_of_type(type_uri)

        for uri in entity_uris:
            labels = [
                str(o) for o in self.graph.objects(uri, SKOS.prefLabel)
                if isinstance(o, Literal) and str(o).strip()
            ]
            if not labels:
                errors.append(_issue(
                    'missing_label',
                    f"Entity {uri} has no non-empty skos:prefLabel",
                    str(uri),
                ))

    def _check_jobs(self, warnings):
        """Jobs should link to an organization, have dates, and use technologies."""
        for job in self._subjects_of_type(EntityType.JOB):
            label = self.graph.value(job, SKOS.prefLabel) or job

            if self.graph.value(job, SCHEMA.hiringOrganization) is None:
                warnings.append(_issue(
                    'job_missing_organization',
                    f"Job '{label}' has no schema:hiringOrganization link",
                    str(job),
                ))
            if self.graph.value(job, SCHEMA.startDate) is None:
                warnings.append(_issue(
                    'job_missing_dates',
                    f"Job '{label}' has no schema:startDate",
                    str(job),
                ))
            has_tech = self.graph.value(job, RE.usedTechnology) is not None
            has_skill = self.graph.value(job, RE.usedSkill) is not None
            if not has_tech and not has_skill:
                warnings.append(_issue(
                    'job_no_technologies',
                    f"Job '{label}' lists no usedTechnology or usedSkill",
                    str(job),
                ))

    def _check_near_duplicate_skills(self, warnings):
        """Skill labels that differ only in case/punctuation suggest a missed merge."""
        by_key = defaultdict(list)
        for skill in self._subjects_of_type(EntityType.SKILL):
            label = self.graph.value(skill, SKOS.prefLabel)
            if label is None:
                continue
            key = re.sub(r'[^a-z0-9]+', '', str(label).lower())
            if key:
                by_key[key].append(str(label))

        for key, labels in by_key.items():
            if len(set(labels)) > 1:
                warnings.append(_issue(
                    'near_duplicate_skills',
                    f"Skill labels {sorted(set(labels))} look like variants of the same skill",
                    key,
                ))

    def _check_completeness(self, entity_counts, extracted_counts, errors, warnings):
        """Compare graph entity counts against raw extraction counts."""
        for name, extracted in extracted_counts.items():
            if name not in entity_counts or not extracted:
                continue
            in_graph = entity_counts[name]
            if in_graph == 0:
                errors.append(_issue(
                    'type_missing_in_export',
                    f"Extraction produced {extracted} {name} entities but the graph contains none",
                    name,
                ))
            # Dedup legitimately merges duplicates; losing more than half is suspicious
            elif in_graph < extracted * 0.5:
                warnings.append(_issue(
                    'low_entity_count',
                    f"Graph has {in_graph} {name} entities but extraction produced {extracted} "
                    f"(more than half lost — check deduplication)",
                    name,
                ))


def _issue(check: str, message: str, subject: str) -> dict:
    return {'check': check, 'message': message, 'subject': subject}


def _qname(uri: URIRef) -> str:
    """Short readable name for a predicate URI."""
    s = str(uri)
    for sep in ('#', '/'):
        if sep in s:
            s = s.rsplit(sep, 1)[-1]
            break
    return s


__all__ = ['GraphValidator']
