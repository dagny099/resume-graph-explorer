"""
Evaluation tests for Resume Explorer entity extraction quality.

These tests measure precision and recall against manually authored ground truth
stored in tests/fixtures/resume_v*_gt.json. They are marked @pytest.mark.slow
because they load pre-recorded extraction fixtures (not live LLM calls), but
they exercise the full precision/recall arithmetic.

Run with:
    pytest tests/test_evaluation.py -v

Skip via:
    pytest tests/ --ignore=tests/test_evaluation.py   (for fast CI)

Ground truth authoring workflow:
  1. Run extraction pipeline on your resume.
  2. Copy the JSON entities output to tests/fixtures/resume_v1_extracted.json.
  3. Create tests/fixtures/resume_v1_gt.json using ground_truth_schema.json as template.
  4. Fill in the expected values by hand (what the resume actually contains).
  5. Run these tests — tune thresholds based on acceptable error rates.
"""

import pytest


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

SKILL_RECALL_MIN = 0.80     # ≥80% of ground-truth skills must be extracted
SKILL_PRECISION_MIN = 0.70  # ≤30% of extracted skills may be hallucinated
JOB_RECALL_MIN = 0.75       # ≥75% of ground-truth jobs must appear
ORG_RECALL_MIN = 0.75


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _label_set(entity_list, key="label"):
    """Return a lowercase set of labels from a list of entity dicts."""
    return {e.get(key, "").lower().strip() for e in entity_list if e.get(key)}


def _recall(gt_set, extracted_set):
    if not gt_set:
        return 1.0
    return len(gt_set & extracted_set) / len(gt_set)


def _precision(gt_set, extracted_set):
    if not extracted_set:
        return 1.0
    return len(gt_set & extracted_set) / len(extracted_set)


# ---------------------------------------------------------------------------
# Single-resume accuracy (Resume 1)
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestSingleResumeAccuracy:
    """
    Precision + recall tests for Resume 1 against manually authored ground truth.

    All tests skip automatically if the fixture files are missing.
    """

    def test_person_name_extracted(self, extracted_entities_v1, ground_truth_v1):
        """Person name in extracted output must contain the ground-truth name."""
        expected_name = ground_truth_v1["person"]["name"].lower()
        person = extracted_entities_v1.get("person") or {}
        extracted_name = (person.get("name") or person.get("label") or "").lower()
        assert expected_name in extracted_name or extracted_name in expected_name, (
            f"Expected name {expected_name!r} not found in extracted {extracted_name!r}"
        )

    def test_skill_recall(self, extracted_entities_v1, ground_truth_v1):
        """At least SKILL_RECALL_MIN of ground-truth skills must be extracted."""
        gt = {s.lower() for s in ground_truth_v1.get("skills", [])}
        extracted = _label_set(extracted_entities_v1.get("skills", []))
        if not gt:
            pytest.skip("No ground-truth skills defined")
        recall = _recall(gt, extracted)
        assert recall >= SKILL_RECALL_MIN, (
            f"Skill recall {recall:.0%} below {SKILL_RECALL_MIN:.0%} threshold.\n"
            f"Missing: {sorted(gt - extracted)}"
        )

    def test_skill_precision(self, extracted_entities_v1, ground_truth_v1):
        """No more than (1 - SKILL_PRECISION_MIN) of extracted skills should be hallucinated."""
        gt = {s.lower() for s in ground_truth_v1.get("skills", [])}
        extracted = _label_set(extracted_entities_v1.get("skills", []))
        if not extracted:
            pytest.skip("No skills extracted")
        precision = _precision(gt, extracted)
        assert precision >= SKILL_PRECISION_MIN, (
            f"Skill precision {precision:.0%} below {SKILL_PRECISION_MIN:.0%} threshold.\n"
            f"Hallucinated: {sorted(extracted - gt)}"
        )

    def test_skill_count_in_range(self, extracted_entities_v1, ground_truth_v1):
        """Extracted skill count must be within declared min/max."""
        gt_person = ground_truth_v1.get("person", {})
        min_skills = gt_person.get("expected_skills_min", 0)
        max_skills = gt_person.get("expected_skills_max", 999)
        count = len(extracted_entities_v1.get("skills", []))
        assert min_skills <= count <= max_skills, (
            f"Extracted {count} skills — expected [{min_skills}, {max_skills}]"
        )

    def test_job_recall(self, extracted_entities_v1, ground_truth_v1):
        """At least JOB_RECALL_MIN of ground-truth jobs must be found."""
        gt_jobs = ground_truth_v1.get("jobs", [])
        if not gt_jobs:
            pytest.skip("No ground-truth jobs defined")
        gt_titles = {j["title"].lower() for j in gt_jobs if j.get("title")}
        extracted_titles = _label_set(extracted_entities_v1.get("jobs", []), key="title")
        recall = _recall(gt_titles, extracted_titles)
        assert recall >= JOB_RECALL_MIN, (
            f"Job recall {recall:.0%} below {JOB_RECALL_MIN:.0%} threshold.\n"
            f"Missing titles: {sorted(gt_titles - extracted_titles)}"
        )

    def test_organization_recall(self, extracted_entities_v1, ground_truth_v1):
        """At least ORG_RECALL_MIN of ground-truth orgs must be found."""
        gt_orgs = {o.lower() for o in ground_truth_v1.get("organizations", [])}
        if not gt_orgs:
            pytest.skip("No ground-truth organizations defined")
        extracted_orgs = _label_set(extracted_entities_v1.get("organizations", []), key="name")
        recall = _recall(gt_orgs, extracted_orgs)
        assert recall >= ORG_RECALL_MIN, (
            f"Org recall {recall:.0%} below {ORG_RECALL_MIN:.0%} threshold.\n"
            f"Missing: {sorted(gt_orgs - extracted_orgs)}"
        )

    def test_no_unknown_nodes_in_graph(self, extracted_entities_v1):
        """Building the graph from extracted entities must produce zero unknown nodes."""
        from resume_explorer.graph.rdf_graph_builder import RDFGraphBuilder
        from resume_explorer.graph.networkx_adapter import NetworkXAdapter
        from resume_explorer.models.person import Person
        from resume_explorer.models.skill import Skill
        from resume_explorer.models.job import Job
        from resume_explorer.models.organization import Organization
        from resume_explorer.models.education import Education
        from resume_explorer.models.certification import Certification

        person_dict = extracted_entities_v1.get("person")
        person = Person.from_dict(person_dict) if isinstance(person_dict, dict) else Person(name="Unknown")
        skills = [Skill.from_dict(s) for s in extracted_entities_v1.get("skills", []) if isinstance(s, dict)]
        jobs = [Job.from_dict(j) for j in extracted_entities_v1.get("jobs", []) if isinstance(j, dict)]
        orgs = [Organization.from_dict(o) for o in extracted_entities_v1.get("organizations", []) if isinstance(o, dict)]
        edu = [Education.from_dict(e) for e in extracted_entities_v1.get("education", []) if isinstance(e, dict)]
        certs = [Certification.from_dict(c) for c in extracted_entities_v1.get("certifications", []) if isinstance(c, dict)]

        builder = RDFGraphBuilder()
        builder.build_from_entities(
            person=person, jobs=jobs, skills=skills,
            education=edu, certifications=certs, organizations=orgs
        )

        adapter = NetworkXAdapter(builder.graph)
        vis = adapter.convert()
        unknowns = [n for n in vis['nodes'] if n['group'] == 'unknown']
        assert unknowns == [], f"Found {len(unknowns)} unknown nodes: {[n['label'] for n in unknowns]}"


# ---------------------------------------------------------------------------
# Multi-resume structural correctness (Resumes 1 + 2)
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestMultiResumeEvaluation:
    """
    Structural correctness tests for two-resume sessions.
    Uses pre-recorded extraction fixtures for both versions.
    """

    def test_single_person_node(self, extracted_entities_v1, extracted_entities_v2):
        """Two versions of the same person → exactly 1 person node in the graph."""
        from resume_explorer.graph.rdf_graph_builder import RDFGraphBuilder
        from resume_explorer.models.person import Person
        from resume_explorer.models.skill import Skill
        from resume_explorer.models.job import Job
        from resume_explorer.models.organization import Organization

        def _load(entities, cls_map):
            return {k: [cls_map[k].from_dict(e) for e in entities.get(k, []) if isinstance(e, dict)]
                    for k in cls_map}

        cls_map = {'skills': Skill, 'jobs': Job, 'organizations': Organization}
        loaded_v1 = _load(extracted_entities_v1, cls_map)
        loaded_v2 = _load(extracted_entities_v2, cls_map)

        p1_dict = extracted_entities_v1.get("person")
        p2_dict = extracted_entities_v2.get("person")
        p1 = Person.from_dict(p1_dict) if isinstance(p1_dict, dict) else Person(name="Unknown")
        p2 = Person.from_dict(p2_dict) if isinstance(p2_dict, dict) else Person(name="Unknown")

        # Merged person (the fix from Phase 1.3)
        merged = Person(name=p1.name, label=p1.label)
        merged.skills = list({sid for p in [p1, p2] for sid in p.skills})
        merged.jobs = list({jid for p in [p1, p2] for jid in p.jobs})

        builder = RDFGraphBuilder()
        builder.build_from_entities(
            person=merged,
            jobs=loaded_v1['jobs'] + loaded_v2['jobs'],
            skills=loaded_v1['skills'] + loaded_v2['skills'],
            education=[], certifications=[],
            organizations=loaded_v1['organizations'] + loaded_v2['organizations'],
        )

        stats = builder.get_graph_stats()
        assert stats['entity_counts']['person'] == 1, (
            f"Expected 1 person node, got {stats['entity_counts']['person']}"
        )

    def test_zero_unknown_nodes_multi_resume(self, extracted_entities_v1, extracted_entities_v2):
        """Two-resume graph must have zero unknown nodes."""
        from resume_explorer.graph.rdf_graph_builder import RDFGraphBuilder
        from resume_explorer.graph.networkx_adapter import NetworkXAdapter
        from resume_explorer.models.person import Person
        from resume_explorer.models.skill import Skill
        from resume_explorer.models.job import Job
        from resume_explorer.models.organization import Organization

        skills = [Skill.from_dict(s) for s in
                  extracted_entities_v1.get("skills", []) + extracted_entities_v2.get("skills", [])
                  if isinstance(s, dict)]
        jobs = [Job.from_dict(j) for j in
                extracted_entities_v1.get("jobs", []) + extracted_entities_v2.get("jobs", [])
                if isinstance(j, dict)]
        orgs = [Organization.from_dict(o) for o in
                extracted_entities_v1.get("organizations", []) + extracted_entities_v2.get("organizations", [])
                if isinstance(o, dict)]

        p1_dict = extracted_entities_v1.get("person")
        p2_dict = extracted_entities_v2.get("person")
        p1 = Person.from_dict(p1_dict) if isinstance(p1_dict, dict) else Person(name="Unknown")
        p2 = Person.from_dict(p2_dict) if isinstance(p2_dict, dict) else Person(name="Unknown")

        merged = Person(name=p1.name, label=p1.label)
        merged.skills = list({sid for p in [p1, p2] for sid in p.skills})
        merged.jobs = list({jid for p in [p1, p2] for jid in p.jobs})

        builder = RDFGraphBuilder()
        builder.build_from_entities(
            person=merged, jobs=jobs, skills=skills,
            education=[], certifications=[], organizations=orgs
        )

        adapter = NetworkXAdapter(builder.graph)
        vis = adapter.convert()
        unknowns = [n for n in vis['nodes'] if n['group'] == 'unknown']
        assert unknowns == [], f"{len(unknowns)} unknown nodes in multi-resume graph"

    def test_skill_dedup_across_versions(self, extracted_entities_v1, extracted_entities_v2, ground_truth_v1):
        """
        Skills appearing in both resume versions should deduplicate to one node.
        Uses ground truth skill list as the reference for expected skill count.
        """
        from resume_explorer.graph.rdf_graph_builder import RDFGraphBuilder
        from resume_explorer.models.person import Person
        from resume_explorer.models.skill import Skill

        skills_v1 = [Skill.from_dict(s) for s in extracted_entities_v1.get("skills", []) if isinstance(s, dict)]
        skills_v2 = [Skill.from_dict(s) for s in extracted_entities_v2.get("skills", []) if isinstance(s, dict)]

        p1_dict = extracted_entities_v1.get("person")
        p2_dict = extracted_entities_v2.get("person")
        p1 = Person.from_dict(p1_dict) if isinstance(p1_dict, dict) else Person(name="Unknown")
        p2 = Person.from_dict(p2_dict) if isinstance(p2_dict, dict) else Person(name="Unknown")

        merged = Person(name=p1.name, label=p1.label)
        merged.skills = list({sid for p in [p1, p2] for sid in p.skills})

        builder = RDFGraphBuilder()
        builder.build_from_entities(
            person=merged, jobs=[], skills=skills_v1 + skills_v2,
            education=[], certifications=[], organizations=[]
        )

        stats = builder.get_graph_stats()
        extracted_count = stats['entity_counts']['skill']
        gt_count = len(ground_truth_v1.get("skills", []))

        # Deduped count should be ≤ sum of both versions (dedup worked)
        total_raw = len(skills_v1) + len(skills_v2)
        assert extracted_count < total_raw or total_raw == 0, (
            f"No deduplication occurred: {extracted_count} nodes from {total_raw} raw skills"
        )

        # Deduped count should be ≥ ground truth count (we didn't under-extract)
        if gt_count:
            assert extracted_count >= int(gt_count * 0.7), (
                f"After dedup, only {extracted_count} skill nodes remain; expected ≥{int(gt_count * 0.7)}"
            )
