"""
Deterministic comparison of extracted resume entities against gold labels.

This is the core of the "evaluation harness lite": given an extraction
result (the same JSON shape SessionStore writes to
sessions/<id>/extracted/<doc>.json) and an expected-entities gold file,
compute per-type match/miss/unexpected sets and precision/recall/F1.

No LLM calls, no network, no randomness — the comparison itself is a pure
function so it can run in CI and be re-run against new extraction outputs
as models/prompts change.

Matching rules (deliberately simple — refine as the eval set grows):
  person:         name, casefolded exact match
  skills:         label, casefolded
  jobs:           title, casefolded
  education:      (degree_type, field_of_study), casefolded
  certifications: name, casefolded
  organizations:  name, casefolded, with common suffixes stripped
                  ("Tech Corp, Inc." matches "Tech Corp")
"""

import re
from typing import Any, Dict, List, Optional


def _norm(value: Optional[str]) -> str:
    """Casefold and collapse whitespace for tolerant-but-deterministic matching."""
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip().casefold()


def _norm_org(value: Optional[str]) -> str:
    """Org names additionally drop legal suffixes and a leading 'the'."""
    name = _norm(value)
    name = re.sub(r"[,.]?\s*(inc|llc|ltd|corp|co)\.?$", "", name).strip(" ,.")
    if name.startswith("the "):
        name = name[4:]
    return name


def _first(d: Dict[str, Any], *keys: str) -> Optional[str]:
    """First non-empty value among the given keys."""
    for k in keys:
        v = d.get(k)
        if v:
            return v
    return None


# Per-type key functions. Each takes an entity (dict or string) and returns
# the normalized comparison key, or "" if the entity has no usable key.
def _skill_key(e) -> str:
    return _norm(e if isinstance(e, str) else _first(e, "label", "name"))


def _job_key(e) -> str:
    return _norm(e if isinstance(e, str) else _first(e, "title", "label"))


def _education_key(e) -> str:
    if isinstance(e, str):
        return _norm(e)
    return f"{_norm(e.get('degree_type'))}|{_norm(e.get('field_of_study'))}"


def _cert_key(e) -> str:
    return _norm(e if isinstance(e, str) else _first(e, "name", "label"))


def _org_key(e) -> str:
    return _norm_org(e if isinstance(e, str) else _first(e, "name", "label"))


_KEY_FUNCS = {
    "skills": _skill_key,
    "jobs": _job_key,
    "education": _education_key,
    "certifications": _cert_key,
    "organizations": _org_key,
}

ENTITY_TYPES = ["person"] + sorted(_KEY_FUNCS)


def _keys(items: List[Any], key_fn) -> set:
    return {k for k in (key_fn(item) for item in (items or [])) if k}


def _prf(matched: int, extracted: int, expected: int) -> Dict[str, float]:
    precision = matched / extracted if extracted else 0.0
    recall = matched / expected if expected else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
    }


def compare_extraction(extracted: Dict[str, Any], expected: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare an extraction result against gold labels.

    Args:
        extracted: Extraction output. Same shape SessionStore persists:
            {'person': {...}, 'jobs': [...], 'skills': [...], ...}
        expected: Gold labels. Same keys; entity entries may be full dicts
            or bare strings (e.g. "skills": ["Python", "SQL"]).

    Returns:
        {
            'by_type': {
                '<type>': {
                    'matched': [...], 'missing': [...], 'unexpected': [...],
                    'precision': float, 'recall': float, 'f1': float,
                }, ...
            },
            'totals': {'matched': int, 'missing': int, 'unexpected': int,
                       'precision': float, 'recall': float, 'f1': float},
        }
    """
    by_type: Dict[str, Any] = {}
    total_matched = total_missing = total_unexpected = 0
    total_extracted = total_expected = 0

    # Person: single-entity comparison by name
    expected_person = expected.get("person") or {}
    extracted_person = extracted.get("person") or {}
    expected_name = _norm(
        expected_person if isinstance(expected_person, str)
        else expected_person.get("name")
    )
    extracted_name = _norm(
        extracted_person if isinstance(extracted_person, str)
        else extracted_person.get("name")
    )
    if expected_name:
        matched = int(expected_name == extracted_name)
        by_type["person"] = {
            "matched": [expected_name] if matched else [],
            "missing": [] if matched else [expected_name],
            "unexpected": [] if matched or not extracted_name else [extracted_name],
            **_prf(matched, int(bool(extracted_name)), 1),
        }
        total_matched += matched
        total_missing += 1 - matched
        total_unexpected += 0 if matched or not extracted_name else 1
        total_extracted += int(bool(extracted_name))
        total_expected += 1

    # List types
    for etype, key_fn in _KEY_FUNCS.items():
        expected_keys = _keys(expected.get(etype), key_fn)
        extracted_keys = _keys(extracted.get(etype), key_fn)
        if not expected_keys and not extracted_keys:
            continue

        matched_keys = expected_keys & extracted_keys
        missing = expected_keys - extracted_keys
        unexpected = extracted_keys - expected_keys

        by_type[etype] = {
            "matched": sorted(matched_keys),
            "missing": sorted(missing),
            "unexpected": sorted(unexpected),
            **_prf(len(matched_keys), len(extracted_keys), len(expected_keys)),
        }
        total_matched += len(matched_keys)
        total_missing += len(missing)
        total_unexpected += len(unexpected)
        total_extracted += len(extracted_keys)
        total_expected += len(expected_keys)

    return {
        "by_type": by_type,
        "totals": {
            "matched": total_matched,
            "missing": total_missing,
            "unexpected": total_unexpected,
            **_prf(total_matched, total_extracted, total_expected),
        },
    }


def format_report(report: Dict[str, Any]) -> str:
    """Render a comparison report as a readable plain-text table."""
    lines = [
        f"{'type':<15} {'P':>6} {'R':>6} {'F1':>6}   matched / missing / unexpected",
        "-" * 72,
    ]
    for etype in ENTITY_TYPES:
        result = report["by_type"].get(etype)
        if not result:
            continue
        lines.append(
            f"{etype:<15} {result['precision']:>6.2f} {result['recall']:>6.2f} "
            f"{result['f1']:>6.2f}   {len(result['matched'])} / "
            f"{len(result['missing'])} / {len(result['unexpected'])}"
        )
    t = report["totals"]
    lines.append("-" * 72)
    lines.append(
        f"{'TOTAL':<15} {t['precision']:>6.2f} {t['recall']:>6.2f} {t['f1']:>6.2f}   "
        f"{t['matched']} / {t['missing']} / {t['unexpected']}"
    )

    for etype in ENTITY_TYPES:
        result = report["by_type"].get(etype)
        if not result:
            continue
        if result["missing"]:
            lines.append(f"  missing {etype}: {', '.join(result['missing'])}")
        if result["unexpected"]:
            lines.append(f"  unexpected {etype}: {', '.join(result['unexpected'])}")

    return "\n".join(lines)


__all__ = ["compare_extraction", "format_report", "ENTITY_TYPES"]
