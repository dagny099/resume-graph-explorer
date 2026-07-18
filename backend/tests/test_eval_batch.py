"""
Tests for batch evaluation (backend/evaluation/batch.py).

Runs the deterministic batch comparator over the bundled fixture suite and
checks aggregation math, mode handling, and that the designed adversarial
traps are actually detected. All offline — no LLM calls, no network.
"""

import json
import shutil

import pytest

from evaluation.batch import (
    FIXTURES_DIR,
    format_batch_report,
    has_discrepancies,
    load_manifest,
    run_batch,
)

MANIFEST = load_manifest()


@pytest.fixture(scope="module")
def raw_results():
    return run_batch(mode="raw")


def _entry(results, fixture_id):
    return next(f for f in results["fixtures"] if f["id"] == fixture_id)


class TestRawBatch:
    def test_every_manifest_fixture_evaluated(self, raw_results):
        assert len(raw_results["fixtures"]) == len(MANIFEST["fixtures"])
        assert all(f["report"] is not None for f in raw_results["fixtures"])
        assert all(f["skipped"] is None for f in raw_results["fixtures"])

    def test_aggregate_totals_equal_sum_of_fixture_totals(self, raw_results):
        agg = raw_results["aggregate"]["totals"]
        for key in ("matched", "missing", "unexpected"):
            summed = sum(f["report"]["totals"][key] for f in raw_results["fixtures"])
            assert agg[key] == summed, key

    def test_aggregate_prf_computed_from_counts(self, raw_results):
        for etype, r in raw_results["aggregate"]["by_type"].items():
            extracted_n = r["matched"] + r["unexpected"]
            expected_n = r["matched"] + r["missing"]
            assert r["precision"] == round(r["matched"] / extracted_n, 3), etype
            assert r["recall"] == round(r["matched"] / expected_n, 3), etype

    def test_missing_and_unexpected_lists_name_fixtures(self, raw_results):
        for item in raw_results["missing_counts"] + raw_results["unexpected_counts"]:
            assert item["fixtures"], item
            for fid in item["fixtures"]:
                assert fid in [f["id"] for f in raw_results["fixtures"]]

    def test_bundled_simulated_extractions_are_imperfect(self, raw_results):
        """The demo suite is deliberately imperfect — strict mode would fail."""
        assert has_discrepancies(raw_results)

    def test_report_renders(self, raw_results):
        text = format_batch_report(raw_results)
        assert "TOTAL" in text
        assert "sample_resume_001" in text
        assert "Intentionally absent entity types" in text
        assert "Most common unexpected entities" in text

    def test_invalid_mode_rejected(self):
        with pytest.raises(ValueError):
            run_batch(mode="bogus")


class TestDesignedTrapsAreDetected:
    """Each adversarial fixture's simulated extraction fails its trap on
    purpose; the comparator must flag exactly those failures."""

    def test_002_mentioned_but_not_evidenced_aws(self, raw_results):
        skills = _entry(raw_results, "sample_resume_002")["report"]["by_type"]["skills"]
        assert "aws" in skills["unexpected"]

    def test_002_empty_certifications_stay_silent(self, raw_results):
        """Both gold and extraction have no certifications — no false counts."""
        report = _entry(raw_results, "sample_resume_002")["report"]
        assert "certifications" not in report["by_type"]

    def test_003_publication_venue_flagged_as_unexpected_org(self, raw_results):
        orgs = _entry(raw_results, "sample_resume_003")["report"]["by_type"]["organizations"]
        assert "journal of cognitive neuroscience" in orgs["unexpected"]

    def test_004_aspirational_skill_flagged(self, raw_results):
        skills = _entry(raw_results, "sample_resume_004")["report"]["by_type"]["skills"]
        assert "rust" in skills["unexpected"]

    def test_005_org_suffix_variants_collapse_to_one_match(self, raw_results):
        orgs = _entry(raw_results, "sample_resume_005")["report"]["by_type"]["organizations"]
        assert orgs["recall"] == 1.0
        assert orgs["unexpected"] == []

    def test_005_column_split_damage_detected(self, raw_results):
        report = _entry(raw_results, "sample_resume_005")["report"]
        assert "vmware vsphere" in report["by_type"]["skills"]["missing"]
        assert "vmware" in report["by_type"]["skills"]["unexpected"]
        assert "aas|network administration" in report["by_type"]["education"]["missing"]

    def test_006_soft_skill_promotion_flagged(self, raw_results):
        skills = _entry(raw_results, "sample_resume_006")["report"]["by_type"]["skills"]
        assert "compassionate communication" in skills["unexpected"]

    def test_006_cert_issuer_flagged_as_unexpected_org(self, raw_results):
        orgs = _entry(raw_results, "sample_resume_006")["report"]["by_type"]["organizations"]
        assert "board of certification for emergency nursing" in orgs["unexpected"]

    def test_007_tool_names_inside_proper_names_flagged(self, raw_results):
        report = _entry(raw_results, "sample_resume_007")["report"]
        assert "python" in report["by_type"]["skills"]["unexpected"]
        assert "tableau" in report["by_type"]["skills"]["unexpected"]
        assert "tableau health initiative" in report["by_type"]["organizations"]["unexpected"]

    def test_007_hallucination_into_absent_education_detected(self, raw_results):
        """Gold education is intentionally empty; the invented MBA must be
        reported as unexpected, with nothing counted as missing."""
        education = _entry(raw_results, "sample_resume_007")["report"]["by_type"]["education"]
        assert education["unexpected"] == ["mba|business administration"]
        assert education["missing"] == []
        assert education["precision"] == 0.0


class TestNormalizedMode:
    @pytest.fixture(scope="class")
    def results(self):
        return run_batch(mode="normalized")

    def test_only_fixtures_with_normalized_gold_run(self, results):
        for f in results["fixtures"]:
            manifest_entry = next(m for m in MANIFEST["fixtures"] if m["id"] == f["id"])
            if manifest_entry["has_normalized_expected"]:
                assert f["report"] is not None
            else:
                assert f["report"] is None
                assert "normalized" in f["skipped"]

    def test_raw_surface_forms_score_poorly_against_normalized_gold(self, results):
        """The 004 simulated extraction keeps abbreviations, so normalized
        mode reports them as unexpected and the canonical labels as missing."""
        skills = _entry(results, "sample_resume_004")["report"]["by_type"]["skills"]
        assert "machine learning" in skills["missing"]
        assert "ml" in skills["unexpected"]
        assert "google analytics 4" in skills["missing"]
        assert "ga4" in skills["unexpected"]


class TestExtractedDirOverride:
    def test_perfect_outputs_have_no_discrepancies(self, tmp_path):
        """Scoring gold-as-extraction for one fixture: perfect metrics; the
        other fixtures are skipped because no output file exists for them."""
        shutil.copy(
            FIXTURES_DIR / "sample_resume_007.expected.json",
            tmp_path / "sample_resume_007.json",
        )
        results = run_batch(mode="raw", extracted_dir=tmp_path)

        entry = _entry(results, "sample_resume_007")
        assert entry["report"]["totals"]["f1"] == 1.0
        # intentionally absent types produce no counts at all when respected
        assert "education" not in entry["report"]["by_type"]
        assert "certifications" not in entry["report"]["by_type"]

        others = [f for f in results["fixtures"] if f["id"] != "sample_resume_007"]
        assert all(f["skipped"] and "missing extraction output" in f["skipped"]
                   for f in others)
        assert not has_discrepancies(results)

    def test_partial_run_aggregates_only_evaluated_fixtures(self, tmp_path):
        extraction = {"person": {"name": "Marcus Webb"}, "skills": [{"label": "OKRs"}]}
        (tmp_path / "sample_resume_007.json").write_text(json.dumps(extraction))
        results = run_batch(mode="raw", extracted_dir=tmp_path)

        entry = _entry(results, "sample_resume_007")
        totals = entry["report"]["totals"]
        assert results["aggregate"]["totals"]["matched"] == totals["matched"]
        assert results["aggregate"]["totals"]["missing"] == totals["missing"]
        assert has_discrepancies(results)
