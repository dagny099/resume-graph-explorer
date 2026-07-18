"""
Shared pytest fixtures for Resume Explorer test suite.

Ground truth fixtures live in tests/fixtures/ and are authored manually
(see ground_truth_schema.json for the format). Pre-recorded extraction
results are stored alongside them so evaluation tests can run without a
live LLM call.
"""

import json
import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_json(path: Path):
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def ground_truth_v1():
    """Ground truth for Resume 1 (manually authored)."""
    data = _load_json(FIXTURES_DIR / "resume_v1_gt.json")
    if data is None:
        pytest.skip("resume_v1_gt.json not found — author it to run evaluation tests")
    return data


@pytest.fixture(scope="session")
def ground_truth_v2():
    """Ground truth for Resume 2 (manually authored)."""
    data = _load_json(FIXTURES_DIR / "resume_v2_gt.json")
    if data is None:
        pytest.skip("resume_v2_gt.json not found — author it to run evaluation tests")
    return data


@pytest.fixture(scope="session")
def extracted_entities_v1():
    """
    Pre-recorded extraction result for Resume 1.

    To generate: run the extraction pipeline once, review the output,
    then save it as tests/fixtures/resume_v1_extracted.json.
    This keeps evaluation tests fast (no live LLM call) and reproducible.
    """
    data = _load_json(FIXTURES_DIR / "resume_v1_extracted.json")
    if data is None:
        pytest.skip(
            "resume_v1_extracted.json not found — run extraction once and save the output"
        )
    return data


@pytest.fixture(scope="session")
def extracted_entities_v2():
    """Pre-recorded extraction result for Resume 2."""
    data = _load_json(FIXTURES_DIR / "resume_v2_extracted.json")
    if data is None:
        pytest.skip("resume_v2_extracted.json not found")
    return data
