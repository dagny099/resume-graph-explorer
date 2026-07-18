"""
Tests for multi-resume unknown node bug.

History: This bug survived 3 prior fix attempts (commits 8dab15d, 515d788, ee07f0d).
The lesson: write a failing test BEFORE touching production code.

WHAT NOT TO DO (preserved from prior investigation):
1. Don't patch add_person without a test that first fails.
2. Don't assume dedup caches are the problem — code review showed they correctly
   map IDs on both creation and dedup-hit. Verify with logging before touching them.
3. Don't fix normalization without fixing the save-loop index mismatch first.
   The index mismatch is a real bug that can corrupt entity data across documents.
4. Don't test with just one resume — the bug only manifests with 2+ resumes.
5. Don't use all_persons[0] without merging all persons' reference lists. The first
   person's skills/jobs/etc. contain only IDs from its own extraction.

ROOT CAUSES (confirmed):
A. Index mismatch in routes.py save loop: collection loop filters docs with `if entities`
   but save loop iterates unfiltered completed_docs → wrong entities saved to wrong doc.
B. get_session_graph uses all_persons[0] whose .skills/.jobs only contain Doc 1 IDs.
C. export_session_graph adds person before jobs (wrong order) and omits orgs/edu/certs.
D. Ghost URI fallback in add_person: unresolved IDs create URIs with no rdf:type → "unknown".
"""

import uuid
import pytest
from rdflib.namespace import RDF

from resume_explorer.graph.rdf_graph_builder import RDFGraphBuilder
from resume_explorer.graph.networkx_adapter import NetworkXAdapter
from resume_explorer.models.person import Person
from resume_explorer.models.skill import Skill
from resume_explorer.models.job import Job
from resume_explorer.models.organization import Organization


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unknown_nodes(builder: RDFGraphBuilder):
    """Return list of Vis.js node dicts whose group == 'unknown'."""
    adapter = NetworkXAdapter(builder.graph)
    vis = adapter.convert()
    return [n for n in vis['nodes'] if n['group'] == 'unknown']


def _skill(label: str) -> Skill:
    return Skill(label=label)


def _job(title: str, org_id: str = "", start_date=None) -> Job:
    j = Job(title=title, label=title)
    j.organization_id = org_id
    j.start_date = start_date
    return j


def _org(name: str) -> Organization:
    return Organization(name=name, label=name)


def _person(name: str, skills=None, jobs=None) -> Person:
    p = Person(name=name, label=name)
    p.skills = [s.id for s in (skills or [])]
    p.jobs = [j.id for j in (jobs or [])]
    return p


# ---------------------------------------------------------------------------
# Baseline: single resume
# ---------------------------------------------------------------------------

class TestSingleResume:
    def test_no_unknown_nodes(self):
        """Single resume with correct entity ordering produces zero unknown nodes."""
        skill = _skill("Python")
        job = _job("Engineer")
        person = _person("Alice", skills=[skill], jobs=[job])

        builder = RDFGraphBuilder()
        builder.build_from_entities(
            person=person, jobs=[job], skills=[skill],
            education=[], certifications=[], organizations=[]
        )

        assert _unknown_nodes(builder) == []

    def test_skill_count(self):
        """Single resume: skill count matches added skills."""
        skills = [_skill("Python"), _skill("SQL"), _skill("Docker")]
        person = _person("Alice", skills=skills)

        builder = RDFGraphBuilder()
        builder.build_from_entities(
            person=person, jobs=[], skills=skills,
            education=[], certifications=[], organizations=[]
        )

        stats = builder.get_graph_stats()
        assert stats['entity_counts']['skill'] == 3


# ---------------------------------------------------------------------------
# Document existing bugs (tests that assert the bug EXISTS)
# These help ensure we fix root causes, not just symptoms.
# ---------------------------------------------------------------------------

class TestUnknownNodeBugFixed:
    """
    These tests verify Step 1.4 fix: add_person now skips unresolved IDs
    (logs a warning) instead of creating ghost URIs with no rdf:type.

    Prior to fix: a person referencing an ID not in the builder's caches
    would create a fallback URI → no rdf:type triple → "unknown" node.
    """

    def test_unresolved_skill_id_skipped_not_ghost(self):
        """
        Unresolved skill ID in person.skills → skipped with warning, not ghost URI.
        Was the root cause of ~8-10 unknown nodes in multi-resume sessions.
        """
        stale_skill_id = str(uuid.uuid4())
        person = Person(name="Alice", label="Alice")
        person.skills = [stale_skill_id]

        builder = RDFGraphBuilder()
        builder.build_from_entities(
            person=person, jobs=[], skills=[],
            education=[], certifications=[], organizations=[]
        )

        assert _unknown_nodes(builder) == [], (
            "Unresolved skill ID must be skipped (not a ghost URI)."
        )

    def test_unresolved_job_id_skipped_not_ghost(self):
        """Unresolved job ID in person.jobs → skipped with warning, not ghost URI."""
        stale_job_id = str(uuid.uuid4())
        person = Person(name="Alice", label="Alice")
        person.jobs = [stale_job_id]

        builder = RDFGraphBuilder()
        builder.build_from_entities(
            person=person, jobs=[], skills=[],
            education=[], certifications=[], organizations=[]
        )

        assert _unknown_nodes(builder) == [], (
            "Unresolved job ID must be skipped (not a ghost URI)."
        )

    def test_export_omits_org_creates_ghost_uri(self):
        """
        Documents the export completeness bug.
        export_session_graph adds Person/Job/Skill but NOT Organization.
        add_job references organization_id via _org_id_to_uri; if org was never
        add_organization()'d, a fallback URI is created with no rdf:type → unknown.
        """
        org = _org("Acme Corp")
        job = _job("Engineer", org_id=org.id)
        skill = _skill("Python")
        person = _person("Alice", skills=[skill], jobs=[job])

        builder = RDFGraphBuilder()
        # Simulate current export_session_graph: skill + job + person, but NO org
        builder.add_skill(skill)
        builder.add_job(job)    # job.organization_id → not in _org_id_to_uri → ghost URI
        builder.add_person(person)

        unknowns = _unknown_nodes(builder)
        assert len(unknowns) > 0, (
            "Job referencing an org that was never add_organization()'d should create a ghost URI."
        )


# ---------------------------------------------------------------------------
# Fix verification tests
# These assert CORRECT behavior. They guide which fixes to make.
# ---------------------------------------------------------------------------

class TestFixes:
    def test_export_org_included_no_ghost_uri(self):
        """
        Step 1.5 fix: export collects orgs (and edu/certs) before building.
        When org is included, job's org reference resolves → no ghost URI.
        """
        org = _org("Acme Corp")
        job = _job("Engineer", org_id=org.id)
        skill = _skill("Python")
        person = _person("Alice", skills=[skill], jobs=[job])

        builder = RDFGraphBuilder()
        builder.build_from_entities(
            person=person, jobs=[job], skills=[skill],
            education=[], certifications=[], organizations=[org]
        )

        assert _unknown_nodes(builder) == []

    def test_correct_ordering_no_ghost_uri(self):
        """
        Step 1.5 fix: export must add orgs/skills/jobs BEFORE adding person.
        Correct ordering (as build_from_entities does) produces zero unknown nodes.
        """
        skill = _skill("Python")
        job = _job("Engineer")
        person = _person("Alice", skills=[skill], jobs=[job])

        builder = RDFGraphBuilder()
        # CORRECT order
        builder.add_skill(skill)
        builder.add_job(job)
        builder.add_person(person)

        assert _unknown_nodes(builder) == []

    def test_merged_person_resolves_all_ids(self):
        """
        Step 1.3 fix: build a merged person whose reference lists union all persons' IDs.
        This approach ensures all skill/job IDs referenced by the person are in the cache.
        """
        skill1 = _skill("Python")
        skill2 = _skill("SQL")
        job1 = _job("Engineer")
        job2 = _job("Analyst")

        person1 = _person("Alice", skills=[skill1], jobs=[job1])
        person2 = _person("Alice", skills=[skill2], jobs=[job2])

        # The fix: union all reference lists across persons
        merged = Person(name="Alice", label="Alice")
        merged.skills = list({sid for p in [person1, person2] for sid in p.skills})
        merged.jobs = list({jid for p in [person1, person2] for jid in p.jobs})

        builder = RDFGraphBuilder()
        builder.build_from_entities(
            person=merged,
            jobs=[job1, job2], skills=[skill1, skill2],
            education=[], certifications=[], organizations=[]
        )

        assert _unknown_nodes(builder) == []


# ---------------------------------------------------------------------------
# End-to-end multi-resume acceptance test
# ---------------------------------------------------------------------------

class TestMultiResumeAcceptance:
    def test_two_resume_versions_same_person_no_unknown_nodes(self):
        """
        Two resume versions for the same person should produce:
        - Zero unknown nodes
        - Exactly 1 person node
        - Deduplicated skills (same label → same node)
        - All jobs correctly linked
        """
        skill_py1 = _skill("Python")  # same label in both docs
        skill_py2 = _skill("Python")  # will be deduped by graph builder
        skill_sql = _skill("SQL")     # only in doc2
        org = _org("Acme Corp")
        job1 = _job("Engineer", org_id=org.id)
        job2 = _job("Senior Engineer", org_id=org.id)

        person1 = _person("Alice Smith", skills=[skill_py1], jobs=[job1])
        person2 = _person("Alice Smith", skills=[skill_py2, skill_sql], jobs=[job2])

        # Merged person (the fix for get_session_graph)
        merged = Person(name="Alice Smith", label="Alice Smith")
        merged.skills = list({sid for p in [person1, person2] for sid in p.skills})
        merged.jobs = list({jid for p in [person1, person2] for jid in p.jobs})

        builder = RDFGraphBuilder()
        builder.build_from_entities(
            person=merged,
            jobs=[job1, job2],
            skills=[skill_py1, skill_py2, skill_sql],
            education=[], certifications=[],
            organizations=[org]
        )

        # Zero unknown nodes
        assert _unknown_nodes(builder) == []

        stats = builder.get_graph_stats()

        # Exactly 1 person node
        assert stats['entity_counts']['person'] == 1

        # Skill dedup: "Python" appears twice but should collapse to 1 node
        assert stats['entity_counts']['skill'] == 2, (
            "Two distinct skills: 'Python' (deduped) and 'SQL'"
        )

        # Both jobs present
        assert stats['entity_counts']['job'] == 2

        # Org deduped
        assert stats['entity_counts']['organization'] == 1

    def test_duplicate_skill_label_deduplicated(self):
        """Skills with the same label (case-insensitive) across two resumes → 1 node."""
        skill1 = _skill("Machine Learning")
        skill2 = _skill("machine learning")  # same, different case

        person1 = _person("Alice", skills=[skill1])
        person2 = _person("Alice", skills=[skill2])

        merged = Person(name="Alice", label="Alice")
        merged.skills = list({sid for p in [person1, person2] for sid in p.skills})

        builder = RDFGraphBuilder()
        builder.build_from_entities(
            person=merged,
            jobs=[], skills=[skill1, skill2],
            education=[], certifications=[], organizations=[]
        )

        stats = builder.get_graph_stats()
        assert stats['entity_counts']['skill'] == 1, (
            "Case-insensitive skill dedup should merge 'Machine Learning' and 'machine learning'."
        )
        assert _unknown_nodes(builder) == []

    def test_same_org_fuzzy_dedup(self):
        """'BigCo' and 'BigCo, Inc.' should deduplicate to one org node."""
        org1 = _org("BigCo")
        org2 = _org("BigCo, Inc.")

        builder = RDFGraphBuilder()
        builder.add_organization(org1)
        builder.add_organization(org2)  # should hit fuzzy cache

        stats = builder.get_graph_stats()
        assert stats['entity_counts']['organization'] == 1, (
            "Fuzzy org matching should collapse 'BigCo' and 'BigCo, Inc.' to one node."
        )

    def test_multi_suffix_org_dedup(self):
        """
        'Acme Corp' and 'Acme Corp, Inc.' should deduplicate.
        Currently FAILS: _normalize_org_name strips only one suffix per call (has break),
        so 'Acme Corp, Inc.' → 'Acme Corp' (strips ', inc.') but 'Acme Corp' → 'Acme'
        (strips ' corp'). Different cache keys → no dedup.
        Passes after _normalize_org_name is fixed to strip all matching suffixes.
        """
        org1 = _org("Acme Corp")
        org2 = _org("Acme Corp, Inc.")

        builder = RDFGraphBuilder()
        builder.add_organization(org1)
        builder.add_organization(org2)

        stats = builder.get_graph_stats()
        assert stats['entity_counts']['organization'] == 1, (
            "After fix: 'Acme Corp' and 'Acme Corp, Inc.' should deduplicate to one node."
        )
