"""
Tests for the evaluation harness lite (backend/evaluation/).

All comparisons are deterministic and offline — no LLM calls, no network.
"""

import json
from pathlib import Path

import pytest

from evaluation.compare import compare_extraction, format_report

FIXTURES = Path(__file__).parent.parent / "evaluation" / "fixtures"


@pytest.fixture
def expected():
    return json.loads((FIXTURES / "sample_resume_001.expected.json").read_text())


@pytest.fixture
def extracted():
    return json.loads((FIXTURES / "sample_resume_001.extracted.json").read_text())


class TestPerfectExtraction:
    def test_gold_vs_itself_is_perfect(self, expected):
        """Comparing gold labels against themselves scores 1.0 everywhere."""
        report = compare_extraction(expected, expected)
        for etype, result in report["by_type"].items():
            assert result["precision"] == 1.0, etype
            assert result["recall"] == 1.0, etype
            assert result["missing"] == []
            assert result["unexpected"] == []
        assert report["totals"]["f1"] == 1.0


class TestSimulatedExtraction:
    """The bundled simulated extraction is deliberately imperfect."""

    def test_person_matches(self, extracted, expected):
        report = compare_extraction(extracted, expected)
        assert report["by_type"]["person"]["recall"] == 1.0

    def test_missing_skill_detected(self, extracted, expected):
        report = compare_extraction(extracted, expected)
        skills = report["by_type"]["skills"]
        # 'Tableau' was not extracted; 'GA4' doesn't match 'Google Analytics 4' raw
        assert "tableau" in skills["missing"]
        assert "google analytics 4" in skills["missing"]

    def test_hallucinated_skill_detected(self, extracted, expected):
        report = compare_extraction(extracted, expected)
        skills = report["by_type"]["skills"]
        assert "data science" in skills["unexpected"]
        assert "ga4" in skills["unexpected"]

    def test_org_suffix_normalization(self, extracted, expected):
        """'Acme Analytics, Inc.' (extracted) matches 'Acme Analytics' (gold)."""
        report = compare_extraction(extracted, expected)
        orgs = report["by_type"]["organizations"]
        assert orgs["recall"] == 1.0
        assert orgs["unexpected"] == []

    def test_jobs_and_education_match(self, extracted, expected):
        report = compare_extraction(extracted, expected)
        assert report["by_type"]["jobs"]["f1"] == 1.0
        assert report["by_type"]["education"]["f1"] == 1.0

    def test_totals_are_consistent(self, extracted, expected):
        report = compare_extraction(extracted, expected)
        totals = report["totals"]
        summed = {
            key: sum(len(r[key]) for r in report["by_type"].values())
            for key in ("matched", "missing", "unexpected")
        }
        assert totals["matched"] == summed["matched"]
        assert totals["missing"] == summed["missing"]
        assert totals["unexpected"] == summed["unexpected"]


class TestEdgeCases:
    def test_empty_extraction(self, expected):
        """Nothing extracted → recall 0, everything missing, no crash."""
        report = compare_extraction({}, expected)
        assert report["totals"]["recall"] == 0.0
        assert report["totals"]["matched"] == 0

    def test_case_insensitive_matching(self):
        report = compare_extraction(
            {"skills": [{"label": "PYTHON"}]},
            {"skills": ["Python"]},
        )
        assert report["by_type"]["skills"]["f1"] == 1.0

    def test_string_and_dict_entries_equivalent(self):
        report = compare_extraction(
            {"skills": ["Python"]},
            {"skills": [{"label": "Python"}]},
        )
        assert report["by_type"]["skills"]["f1"] == 1.0

    def test_format_report_renders(self, extracted, expected):
        text = format_report(compare_extraction(extracted, expected))
        assert "TOTAL" in text
        assert "skills" in text

    def test_comparison_is_deterministic(self, extracted, expected):
        r1 = compare_extraction(extracted, expected)
        r2 = compare_extraction(extracted, expected)
        assert r1 == r2
