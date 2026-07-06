"""
Validation tests for the evaluation fixture suite (backend/evaluation/fixtures/).

These enforce the annotation discipline the suite depends on:
  - every manifest fixture has its .txt / .expected.json / .extracted.json files
  - expected files conform to the schema shape the comparator understands
  - intentionally absent entity types are present-but-empty in the gold labels
  - intentionally excluded near-matches (e.g. 'Python' from 'Python Creek
    Ventures') never leak into the gold labels
  - no fixture contains real personal data or secret-looking strings

All offline — no LLM calls, no network.
"""

import json
import re
from pathlib import Path

import pytest

from evaluation.batch import FIXTURES_DIR, load_manifest
from evaluation.compare import _KEY_FUNCS, _norm

MANIFEST = load_manifest()
FIXTURE_IDS = [f["id"] for f in MANIFEST["fixtures"]]

ALLOWED_EXPECTED_KEYS = {
    "_comment", "person", "jobs", "skills", "education",
    "certifications", "organizations",
}
LIST_TYPES = ["jobs", "skills", "education", "certifications", "organizations"]
ALLOWED_TARGETS = {"raw-extraction", "normalization", "parsing", "graph-construction"}
REQUIRED_METADATA = [
    "id", "profile", "tests", "failure_modes", "target",
    "present_types", "absent_types", "excluded_near_matches",
    "has_normalized_expected",
]


def _fixture(fixture_id):
    return next(f for f in MANIFEST["fixtures"] if f["id"] == fixture_id)


def _expected(fixture_id, normalized=False):
    suffix = ".expected.normalized.json" if normalized else ".expected.json"
    return json.loads((FIXTURES_DIR / f"{fixture_id}{suffix}").read_text())


class TestManifest:
    def test_manifest_has_a_diagnostic_suite(self):
        """The suite grew from 1 fixture to a small diagnostic set."""
        assert len(FIXTURE_IDS) >= 5

    def test_fixture_ids_unique(self):
        assert len(FIXTURE_IDS) == len(set(FIXTURE_IDS))

    @pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
    def test_metadata_complete(self, fixture_id):
        fixture = _fixture(fixture_id)
        for key in REQUIRED_METADATA:
            assert key in fixture, f"{fixture_id} manifest entry missing '{key}'"
        assert fixture["profile"].strip()
        assert fixture["tests"].strip()
        assert fixture["failure_modes"], f"{fixture_id} must name its failure modes"
        assert fixture["target"] in ALLOWED_TARGETS

    @pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
    def test_fixture_files_exist(self, fixture_id):
        for suffix in (".txt", ".expected.json", ".extracted.json"):
            path = FIXTURES_DIR / f"{fixture_id}{suffix}"
            assert path.exists(), f"missing {path.name}"
        normalized = FIXTURES_DIR / f"{fixture_id}.expected.normalized.json"
        assert normalized.exists() == _fixture(fixture_id)["has_normalized_expected"], (
            f"{fixture_id}: has_normalized_expected must match whether "
            f"{normalized.name} exists"
        )


class TestExpectedSchema:
    @pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
    def test_expected_shape(self, fixture_id):
        expected = _expected(fixture_id)
        assert set(expected) <= ALLOWED_EXPECTED_KEYS, (
            f"{fixture_id}: unknown keys {set(expected) - ALLOWED_EXPECTED_KEYS}"
        )
        assert isinstance(expected["person"], dict)
        assert expected["person"]["name"].strip()
        for etype in LIST_TYPES:
            assert etype in expected, f"{fixture_id}: '{etype}' must be present (even if empty)"
            assert isinstance(expected[etype], list)
            for entry in expected[etype]:
                assert isinstance(entry, (str, dict))

    @pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
    def test_extracted_is_valid_json_with_person(self, fixture_id):
        extracted = json.loads(
            (FIXTURES_DIR / f"{fixture_id}.extracted.json").read_text()
        )
        assert isinstance(extracted, dict)
        assert extracted["person"]["name"].strip()

    @pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
    def test_person_name_appears_in_resume_text(self, fixture_id):
        text = (FIXTURES_DIR / f"{fixture_id}.txt").read_text()
        name = _expected(fixture_id)["person"]["name"]
        assert name in text, f"{fixture_id}: gold person name not found in resume text"


class TestAnnotationDiscipline:
    @pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
    def test_absent_types_are_empty_in_gold(self, fixture_id):
        """Intentionally absent entity types must be present-but-empty lists."""
        fixture = _fixture(fixture_id)
        expected = _expected(fixture_id)
        for etype in fixture["absent_types"]:
            assert expected[etype] == [], (
                f"{fixture_id}: '{etype}' is declared absent but gold has entries"
            )
            assert etype not in fixture["present_types"]

    @pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
    def test_present_types_are_nonempty_in_gold(self, fixture_id):
        fixture = _fixture(fixture_id)
        expected = _expected(fixture_id)
        for etype in fixture["present_types"]:
            if etype == "person":
                assert expected["person"]["name"]
            else:
                assert expected[etype], (
                    f"{fixture_id}: '{etype}' is declared present but gold is empty"
                )

    @pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
    def test_excluded_near_matches_not_in_gold(self, fixture_id):
        """Terms the fixture is designed NOT to extract must not be gold labels."""
        fixture = _fixture(fixture_id)
        for etype, terms in fixture["excluded_near_matches"].items():
            key_fn = _KEY_FUNCS[etype]
            gold_keys = {key_fn(e) for e in _expected(fixture_id)[etype]}
            for term in terms:
                assert key_fn(term) not in gold_keys, (
                    f"{fixture_id}: excluded near-match '{term}' leaked into "
                    f"the '{etype}' gold labels"
                )

    def test_suite_includes_absent_type_cases(self):
        """At least one fixture tests empty certifications and one empty education."""
        absent = [t for f in MANIFEST["fixtures"] for t in f["absent_types"]]
        assert "certifications" in absent
        assert "education" in absent

    def test_suite_includes_near_match_traps(self):
        excluded = [
            term
            for f in MANIFEST["fixtures"]
            for terms in f["excluded_near_matches"].values()
            for term in terms
        ]
        assert len(excluded) >= 5, "suite should keep its adversarial near-matches"

    def test_normalized_gold_differs_only_where_intended(self):
        """The 004 normalized gold canonicalizes skills but keeps other types."""
        raw = _expected("sample_resume_004")
        normalized = _expected("sample_resume_004", normalized=True)
        assert {"ML", "GA4"} <= set(raw["skills"])
        assert {"Machine Learning", "Google Analytics 4"} <= set(normalized["skills"])
        assert "ML" not in normalized["skills"]
        for etype in ("jobs", "education", "certifications", "organizations"):
            assert raw[etype] == normalized[etype]


class TestNoPrivateDataOrSecrets:
    FIXTURE_FILES = sorted(
        p for p in FIXTURES_DIR.iterdir()
        if p.suffix in (".txt", ".json") and p.name != ".DS_Store"
    )

    SECRET_PATTERNS = [
        r"sk-[A-Za-z0-9_-]{8,}",          # OpenAI/Anthropic-style keys
        r"AKIA[0-9A-Z]{16}",              # AWS access key ids
        r"ghp_[A-Za-z0-9]{20,}",          # GitHub tokens
        r"BEGIN( RSA| EC)? PRIVATE KEY",
        r"(?i)api[_-]?key\s*[:=]",
        r"\b\d{3}-\d{2}-\d{4}\b",         # SSN-shaped
    ]

    @pytest.mark.parametrize("path", FIXTURE_FILES, ids=lambda p: p.name)
    def test_no_secret_patterns(self, path):
        content = path.read_text()
        for pattern in self.SECRET_PATTERNS:
            assert not re.search(pattern, content), (
                f"{path.name} matches secret-looking pattern {pattern!r}"
            )

    @pytest.mark.parametrize("path", FIXTURE_FILES, ids=lambda p: p.name)
    def test_emails_are_synthetic(self, path):
        emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", path.read_text())
        for email in emails:
            domain = email.split("@")[1].rstrip(".")
            assert domain in ("example.com", "example.org"), (
                f"{path.name}: non-synthetic email domain '{domain}'"
            )
