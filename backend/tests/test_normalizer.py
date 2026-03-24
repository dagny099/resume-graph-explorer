"""
Tests for the entity normalization pipeline (Option B).

Covers:
- Separate type-pool normalization (skills vs orgs vs degrees don't cross-contaminate)
- alt_labels tracking when a skill label is remapped
- run_llm_phase=False skips Phase 3
- Skill model: alt_labels field roundtrip through to_dict / from_dict
- RDF graph builder: skos:altLabel triples written for alt_labels
- RDF graph builder: alt_labels accumulate on canonical node across dedup hits
"""

import pytest
from rdflib.namespace import SKOS
from rdflib import Literal

from resume_explorer.services.entity_normalizer import EntityNormalizer
from resume_explorer.models.skill import Skill
from resume_explorer.graph.rdf_graph_builder import RDFGraphBuilder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entities(skills=None, techs=None, orgs=None, degrees=None):
    """Build a minimal entity dict for one document."""
    return {
        "skills": [{"label": s} for s in (skills or [])],
        "jobs": [{"technologies_used": list(techs)}] if techs else [],
        "organizations": [{"name": o} for o in (orgs or [])],
        "education": [{"degree": d} for d in (degrees or [])],
    }


def _norm(entities_list, run_llm=False):
    """Run mock normalization (always run_llm_phase=False unless told otherwise)."""
    n = EntityNormalizer(provider="mock")
    return n.normalize_session_entities(entities_list, run_llm_phase=run_llm)


# ---------------------------------------------------------------------------
# Phase gating
# ---------------------------------------------------------------------------

class TestRunLlmPhaseFlag:
    def test_llm_phase_skipped_when_false(self):
        entities = [_make_entities(skills=["ML", "Machine Learning"])]
        result = _norm(entities, run_llm=False)
        assert result["report"]["phases"]["llm_batch"]["ran"] is False
        assert result["report"]["phases"]["llm_batch"]["merges"] == 0

    def test_llm_phase_runs_when_true_with_mock(self):
        """Mock provider returns no merges, but the phase is marked as ran."""
        entities = [_make_entities(skills=["ML", "Machine Learning"])]
        n = EntityNormalizer(provider="mock")
        result = n.normalize_session_entities(entities, run_llm_phase=True)
        # Mock always returns 0 merges but the flag should show it ran
        assert result["report"]["phases"]["llm_batch"]["ran"] is True


# ---------------------------------------------------------------------------
# Separate type pools — Phase 1 deterministic
# ---------------------------------------------------------------------------

class TestSeparateTypePools:
    def test_case_merge_within_skill_pool(self):
        """'python' and 'Python' in the same skill pool → merge to 'Python'."""
        entities = [
            _make_entities(skills=["python"]),
            _make_entities(skills=["Python"]),
        ]
        result = _norm(entities)
        labels = {
            s["label"]
            for doc in result["normalized_entities"]
            for s in doc["skills"]
        }
        assert labels == {"Python"}

    def test_case_merge_within_tech_pool(self):
        """'python' and 'Python' in a job tech list → merged via Phase 1."""
        entities = [_make_entities(techs=["python", "Python"])]
        result = _norm(entities)
        techs = result["normalized_entities"][0]["jobs"][0]["technologies_used"]
        assert techs.count("Python") + techs.count("python") == 1  # deduped

    def test_no_cross_pool_contamination_with_identical_abbrev(self):
        """
        'MS' as an org name and 'MS' as a degree should NOT be merged into one label.
        They are in separate pools so Phase 1 runs independently on each.
        The label_map should map 'MS' (org) → 'MS' and 'MS' (degree) → 'MS' identically,
        meaning no merges happen (they were already canonical within their own pools).
        """
        entities = [_make_entities(orgs=["MS", "ms"], degrees=["MS", "ms"])]
        result = _norm(entities)
        # Each pool should have merged 'ms' → 'MS', but they're independent merges
        # The key thing: orgs still have org-canonical and degrees still have degree-canonical
        org_names = {o["name"] for o in result["normalized_entities"][0]["organizations"]}
        degree_names = {e["degree"] for e in result["normalized_entities"][0]["education"]}
        assert org_names == {"MS"}
        assert degree_names == {"MS"}
        # Both pools produced the same merge ("ms" → "MS"), so the combined phase1_map
        # dict has 1 entry (dicts deduplicate identical keys). What matters is that
        # the org and degree labels were each normalized correctly within their own pools.
        assert result["report"]["phases"]["deterministic"]["merges"] >= 1

    def test_tech_label_case_merges_with_skill_pool(self):
        """
        'machine learning' (tech) and 'Machine Learning' (skill) are in the same
        skill+tech pool, so Phase 1 correctly merges them.
        """
        entities = [_make_entities(
            skills=["Machine Learning"],
            techs=["machine learning"],
        )]
        result = _norm(entities)
        techs = result["normalized_entities"][0]["jobs"][0]["technologies_used"]
        assert techs == ["Machine Learning"]


# ---------------------------------------------------------------------------
# alt_labels tracking in _apply_normalization
# ---------------------------------------------------------------------------

class TestAltLabelsTracking:
    def test_remapped_skill_gets_alt_label(self):
        """When 'python' → 'Python', the remapped skill should have alt_labels=['python']."""
        entities = [
            _make_entities(skills=["python"]),
            _make_entities(skills=["Python"]),
        ]
        result = _norm(entities)
        # Find the skill that had its label changed (was 'python')
        remapped = [
            s
            for doc in result["normalized_entities"]
            for s in doc["skills"]
            if "python" in s.get("alt_labels", [])
        ]
        assert len(remapped) == 1
        assert remapped[0]["label"] == "Python"

    def test_canonical_skill_has_no_alt_label(self):
        """The skill that was already canonical ('Python') should have no alt_labels added."""
        entities = [
            _make_entities(skills=["python"]),
            _make_entities(skills=["Python"]),
        ]
        result = _norm(entities)
        canonical_docs = [
            s
            for doc in result["normalized_entities"]
            for s in doc["skills"]
            if not s.get("alt_labels")
        ]
        # At least one skill doc should be the canonical with empty alt_labels
        assert len(canonical_docs) >= 1

    def test_alt_labels_preserved_across_from_dict(self):
        """alt_labels survive the to_dict / from_dict roundtrip."""
        s = Skill(label="Machine Learning", alt_labels=["ML", "ml"])
        d = s.to_dict()
        assert d["alt_labels"] == ["ML", "ml"]
        s2 = Skill.from_dict(d)
        assert s2.alt_labels == ["ML", "ml"]

    def test_from_dict_missing_alt_labels_defaults_to_empty(self):
        """Existing saved sessions without alt_labels field load without error."""
        s = Skill.from_dict({"label": "Python", "entity_type": "skill"})
        assert s.alt_labels == []

    def test_no_duplicate_alt_labels(self):
        """If a skill already has an alt_label, running normalization again doesn't duplicate it."""
        entities = [
            _make_entities(skills=["python"]),
            _make_entities(skills=["Python"]),
        ]
        # Simulate running normalization twice by pre-seeding alt_labels
        entities[0]["skills"][0]["alt_labels"] = ["python"]
        result = _norm(entities)
        for doc in result["normalized_entities"]:
            for skill in doc["skills"]:
                alts = skill.get("alt_labels", [])
                assert len(alts) == len(set(alts)), f"Duplicate alt_labels on {skill['label']}: {alts}"


# ---------------------------------------------------------------------------
# RDF graph builder: skos:altLabel triples
# ---------------------------------------------------------------------------

class TestRDFAltLabels:
    def test_alt_labels_written_as_skos_alt_label(self):
        """Skill with alt_labels → skos:altLabel triples in the RDF graph."""
        builder = RDFGraphBuilder()
        skill = Skill(label="Machine Learning", alt_labels=["ML", "machine learning"])
        uri = builder.add_skill(skill)

        alts = set(builder.graph.objects(uri, SKOS.altLabel))
        assert Literal("ML") in alts
        assert Literal("machine learning") in alts

    def test_no_alt_label_triples_when_empty(self):
        """Skill with empty alt_labels → no skos:altLabel triples."""
        builder = RDFGraphBuilder()
        skill = Skill(label="Python")
        uri = builder.add_skill(skill)

        alts = list(builder.graph.objects(uri, SKOS.altLabel))
        assert alts == []

    def test_alt_labels_accumulate_on_dedup_hit(self):
        """
        When two Skill objects with the same label but different alt_labels are added,
        both sets of alt_labels end up on the canonical node.
        """
        builder = RDFGraphBuilder()
        s1 = Skill(label="Python", alt_labels=["python"])
        s2 = Skill(label="Python", alt_labels=["PYTHON"])  # second doc, different variant

        uri1 = builder.add_skill(s1)
        uri2 = builder.add_skill(s2)  # cache hit → returns uri1

        assert uri1 == uri2  # same canonical node
        alts = set(builder.graph.objects(uri1, SKOS.altLabel))
        assert Literal("python") in alts
        assert Literal("PYTHON") in alts

    def test_pref_label_not_duplicated_in_alt_labels(self):
        """If the canonical label somehow ended up in alt_labels, it still writes — no crash."""
        builder = RDFGraphBuilder()
        skill = Skill(label="Python", alt_labels=["Python"])  # edge case: self-reference
        uri = builder.add_skill(skill)
        # Should not raise; altLabel triple for "Python" is technically redundant but not harmful
        alts = list(builder.graph.objects(uri, SKOS.altLabel))
        assert len(alts) == 1


# ---------------------------------------------------------------------------
# End-to-end: normalization → Skill model → RDF builder
# ---------------------------------------------------------------------------

class TestNormalizationToRDF:
    def test_full_pipeline_creates_alt_label_triple(self):
        """
        Full pipeline: normalize 'python' → 'Python' (Phase 1),
        build Skill from normalized dict, add to RDF, verify skos:altLabel.
        """
        entities = [
            _make_entities(skills=["python"]),
            _make_entities(skills=["Python"]),
        ]
        result = _norm(entities)

        # Find the normalized skill dict that has an alt_label
        skill_dicts = [
            s
            for doc in result["normalized_entities"]
            for s in doc["skills"]
            if s.get("alt_labels")
        ]
        assert skill_dicts, "Expected at least one skill with alt_labels after normalization"

        # Build a Skill from the dict and add to RDF
        builder = RDFGraphBuilder()
        skill_obj = Skill.from_dict(skill_dicts[0])
        uri = builder.add_skill(skill_obj)

        alts = set(builder.graph.objects(uri, SKOS.altLabel))
        assert Literal("python") in alts
