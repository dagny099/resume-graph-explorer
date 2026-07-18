"""
Shared Session Graph Building

Single source of truth for turning a session's extracted entities into a
deduplicated RDF graph. Used by the /graph, /export/<format>, /stats, and
/graph/validate routes and by PipelineService._ensure_jsonld(), so every
consumer sees the same complete semantic content (person, jobs, skills,
education, certifications, organizations).

Before this module existed, the export route duplicated the collection loop
and only added person/jobs/skills — education, certifications, and
organizations were silently missing from exported RDF.
"""

import copy
from typing import Any, Dict, List, Optional, Tuple

from .rdf_graph_builder import RDFGraphBuilder
from ..models import Person, Job, Skill, Education, Certification, Organization
from ..utils.logger import logger


# Maps entity-dict keys to their model classes for from_dict conversion
_ENTITY_TYPES = {
    'jobs': Job,
    'skills': Skill,
    'education': Education,
    'certifications': Certification,
    'organizations': Organization,
}


def collect_session_entities(session_store, session_id: str) -> Optional[Dict[str, List[Any]]]:
    """
    Collect entity objects from all completed documents in a session.

    Args:
        session_store: SessionStore instance
        session_id: Session identifier

    Returns:
        Dict with keys 'persons', 'jobs', 'skills', 'education',
        'certifications', 'organizations' (lists of entity objects),
        or None if the session has no completed extractions.
    """
    documents = session_store.get_session_documents(session_id)
    complete_docs = [d for d in documents if d.status == 'complete']

    if not complete_docs:
        return None

    collected = {'persons': []}
    for key in _ENTITY_TYPES:
        collected[key] = []

    for doc in complete_docs:
        entities = session_store.load_extracted_entities(doc.id)
        if not entities:
            continue

        person = entities.get('person')
        if person:
            collected['persons'].append(
                Person.from_dict(person) if isinstance(person, dict) else person
            )

        for key, model_cls in _ENTITY_TYPES.items():
            for item in entities.get(key, []):
                collected[key].append(
                    model_cls.from_dict(item) if isinstance(item, dict) else item
                )

    return collected


def _merge_persons(persons: List[Person]) -> Person:
    """
    Build one graph person for the session (a session describes one person).

    Identity fields come from the first person, but the skill/job/education/
    certification reference lists are the *union* across all documents. Using
    only persons[0]'s reference lists would leave a second resume's entity IDs
    unreferenced, producing ghost URIs / "unknown" nodes in multi-resume
    sessions (multi-resume Root Cause B).
    """
    if not persons:
        return Person(name="Unknown")

    # Copy the first person (preserving id, name, contact fields, etc.) and
    # replace only the reference lists with the cross-document union. A fresh
    # Person() would get a new id/URI and orphan the person node.
    merged = copy.copy(persons[0])
    merged.skills = list({sid for p in persons for sid in p.skills})
    merged.jobs = list({jid for p in persons for jid in p.jobs})
    merged.education = list({eid for p in persons for eid in p.education})
    merged.certifications = list({cid for p in persons for cid in p.certifications})
    return merged


def build_graph_from_collected(collected: Dict[str, List[Any]]) -> RDFGraphBuilder:
    """
    Build a deduplicated RDF graph from collected session entities.

    A session describes one person; their reference lists are unioned across
    all documents (see _merge_persons). Falls back to a placeholder person if
    extraction found none.
    """
    person = _merge_persons(collected['persons'])

    builder = RDFGraphBuilder()
    builder.build_from_entities(
        person=person,
        jobs=collected['jobs'],
        skills=collected['skills'],
        education=collected['education'],
        certifications=collected['certifications'],
        organizations=collected['organizations'],
    )
    return builder


def build_session_graph(
    session_store, session_id: str
) -> Optional[Tuple[RDFGraphBuilder, Dict[str, List[Any]]]]:
    """
    Collect a session's entities and build its complete RDF graph.

    Returns:
        (builder, collected_entities) tuple, or None if the session has
        no completed extractions.
    """
    collected = collect_session_entities(session_store, session_id)
    if collected is None:
        return None

    builder = build_graph_from_collected(collected)
    logger.info(
        f"Built session graph for {session_id}: {len(builder.graph)} triples from "
        f"{len(collected['persons'])} persons, {len(collected['jobs'])} jobs, "
        f"{len(collected['skills'])} skills, {len(collected['education'])} education, "
        f"{len(collected['certifications'])} certifications, "
        f"{len(collected['organizations'])} organizations"
    )
    return builder, collected


def extracted_entity_counts(collected: Dict[str, List[Any]]) -> Dict[str, int]:
    """Raw (pre-deduplication) entity counts, for validation comparisons."""
    return {
        'person': len(collected['persons']),
        'job': len(collected['jobs']),
        'skill': len(collected['skills']),
        'education': len(collected['education']),
        'certification': len(collected['certifications']),
        'organization': len(collected['organizations']),
    }


__all__ = [
    'collect_session_entities',
    'build_graph_from_collected',
    'build_session_graph',
    'extracted_entity_counts',
]
