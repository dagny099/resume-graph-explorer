"""
Batch evaluation across the whole fixture suite.

Runs the deterministic comparator (compare.py) over every fixture listed in
fixtures/manifest.json and aggregates per-entity-type metrics across the
suite. No LLM calls, no network, no API keys.

Two evaluation modes:
  raw:        compare against <id>.expected.json — gold labels preserve the
              resume's surface forms (e.g. "GA4", "ML"). Measures what the
              extractor returned directly.
  normalized: compare against <id>.expected.normalized.json — gold labels use
              canonical skill names (e.g. "Google Analytics 4"). Measures the
              pipeline after entity normalization. Fixtures without a
              normalized gold file are skipped in this mode.

By default each fixture is compared against its bundled simulated extraction
(<id>.extracted.json — deliberately imperfect, for demo/testing). Pass
extracted_dir to score real outputs instead: a directory containing one
<fixture-id>.json per fixture (e.g. collected by run_live_eval.py).
"""

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Optional

try:  # package import (pytest: `from evaluation import batch`)
    from .compare import compare_extraction, ENTITY_TYPES, _prf
except ImportError:  # script import (run_eval.py puts evaluation/ on sys.path)
    from compare import compare_extraction, ENTITY_TYPES, _prf

FIXTURES_DIR = Path(__file__).parent / "fixtures"

MODES = ("raw", "normalized")


def load_manifest(fixtures_dir: Path = FIXTURES_DIR) -> Dict[str, Any]:
    """Load and return fixtures/manifest.json."""
    return json.loads((fixtures_dir / "manifest.json").read_text())


def _expected_path(fixture: Dict[str, Any], fixtures_dir: Path, mode: str) -> Optional[Path]:
    if mode == "normalized":
        if not fixture.get("has_normalized_expected"):
            return None
        return fixtures_dir / f"{fixture['id']}.expected.normalized.json"
    return fixtures_dir / f"{fixture['id']}.expected.json"


def _extracted_path(fixture: Dict[str, Any], fixtures_dir: Path,
                    extracted_dir: Optional[Path]) -> Path:
    if extracted_dir:
        return Path(extracted_dir) / f"{fixture['id']}.json"
    return fixtures_dir / f"{fixture['id']}.extracted.json"


def run_batch(fixtures_dir: Path = FIXTURES_DIR, mode: str = "raw",
              extracted_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Evaluate every manifest fixture and aggregate metrics.

    Returns:
        {
            'mode': 'raw' | 'normalized',
            'fixtures': [
                {'id', 'profile', 'target', 'absent_types',
                 'skipped': None | reason,
                 'report': <compare_extraction result> | None}, ...
            ],
            'aggregate': {
                'by_type': {<type>: {'matched', 'missing', 'unexpected',
                                     'precision', 'recall', 'f1'}},
                'totals': {...same keys...},
            },
            'missing_counts':    [{'entity', 'type', 'fixtures'}, ...],
            'unexpected_counts': [{'entity', 'type', 'fixtures'}, ...],
        }
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, got {mode!r}")

    manifest = load_manifest(fixtures_dir)
    fixture_results = []
    # per-type raw counts across the suite (micro-average)
    type_counts = defaultdict(lambda: {"matched": 0, "missing": 0, "unexpected": 0})
    miss_fixtures = defaultdict(list)    # (type, entity) -> [fixture ids]
    unexp_fixtures = defaultdict(list)

    for fixture in manifest["fixtures"]:
        entry = {
            "id": fixture["id"],
            "profile": fixture.get("profile", ""),
            "target": fixture.get("target", ""),
            "absent_types": fixture.get("absent_types", []),
            "skipped": None,
            "report": None,
        }
        expected_path = _expected_path(fixture, fixtures_dir, mode)
        extracted_path = _extracted_path(fixture, fixtures_dir, extracted_dir)

        if expected_path is None:
            entry["skipped"] = "no normalized gold file (raw-only fixture)"
        elif not expected_path.exists():
            entry["skipped"] = f"missing gold file: {expected_path.name}"
        elif not extracted_path.exists():
            entry["skipped"] = f"missing extraction output: {extracted_path.name}"
        else:
            extracted = json.loads(extracted_path.read_text())
            expected = json.loads(expected_path.read_text())
            report = compare_extraction(extracted, expected)
            entry["report"] = report
            for etype, result in report["by_type"].items():
                counts = type_counts[etype]
                counts["matched"] += len(result["matched"])
                counts["missing"] += len(result["missing"])
                counts["unexpected"] += len(result["unexpected"])
                for entity in result["missing"]:
                    miss_fixtures[(etype, entity)].append(fixture["id"])
                for entity in result["unexpected"]:
                    unexp_fixtures[(etype, entity)].append(fixture["id"])

        fixture_results.append(entry)

    # Aggregate: micro-averaged P/R/F1 from summed counts
    by_type = {}
    totals = {"matched": 0, "missing": 0, "unexpected": 0}
    for etype, c in type_counts.items():
        extracted_n = c["matched"] + c["unexpected"]
        expected_n = c["matched"] + c["missing"]
        by_type[etype] = {**c, **_prf(c["matched"], extracted_n, expected_n)}
        for key in totals:
            totals[key] += c[key]
    totals.update(_prf(totals["matched"],
                       totals["matched"] + totals["unexpected"],
                       totals["matched"] + totals["missing"]))

    def _ranked(counter_map):
        return [
            {"entity": entity, "type": etype, "fixtures": fixtures}
            for (etype, entity), fixtures in sorted(
                counter_map.items(), key=lambda kv: (-len(kv[1]), kv[0])
            )
        ]

    return {
        "mode": mode,
        "fixtures": fixture_results,
        "aggregate": {"by_type": by_type, "totals": totals},
        "missing_counts": _ranked(miss_fixtures),
        "unexpected_counts": _ranked(unexp_fixtures),
    }


def has_discrepancies(results: Dict[str, Any]) -> bool:
    """True if any evaluated fixture has a missing or unexpected entity."""
    return any(
        f["report"]["totals"]["missing"] or f["report"]["totals"]["unexpected"]
        for f in results["fixtures"]
        if f["report"] is not None
    )


def format_batch_report(results: Dict[str, Any], top_n: int = 10) -> str:
    """Render batch results as a readable plain-text report."""
    evaluated = [f for f in results["fixtures"] if f["report"]]
    skipped = [f for f in results["fixtures"] if f["skipped"]]

    lines = [
        f"Batch evaluation — mode: {results['mode']} "
        f"({len(evaluated)} fixtures evaluated, {len(skipped)} skipped)",
        "",
        f"{'fixture':<20} {'P':>6} {'R':>6} {'F1':>6}   matched / missing / unexpected",
        "-" * 78,
    ]
    for f in evaluated:
        t = f["report"]["totals"]
        lines.append(
            f"{f['id']:<20} {t['precision']:>6.2f} {t['recall']:>6.2f} "
            f"{t['f1']:>6.2f}   {t['matched']} / {t['missing']} / {t['unexpected']}"
        )
    for f in skipped:
        lines.append(f"{f['id']:<20} skipped — {f['skipped']}")

    lines += [
        "",
        "Aggregate by entity type (micro-averaged across fixtures):",
        f"{'type':<15} {'P':>6} {'R':>6} {'F1':>6}   matched / missing / unexpected",
        "-" * 78,
    ]
    by_type = results["aggregate"]["by_type"]
    for etype in ENTITY_TYPES:
        r = by_type.get(etype)
        if not r:
            continue
        lines.append(
            f"{etype:<15} {r['precision']:>6.2f} {r['recall']:>6.2f} {r['f1']:>6.2f}   "
            f"{r['matched']} / {r['missing']} / {r['unexpected']}"
        )
    t = results["aggregate"]["totals"]
    lines.append("-" * 78)
    lines.append(
        f"{'TOTAL':<15} {t['precision']:>6.2f} {t['recall']:>6.2f} {t['f1']:>6.2f}   "
        f"{t['matched']} / {t['missing']} / {t['unexpected']}"
    )

    if results["missing_counts"]:
        lines += ["", f"Most common missing entities (top {top_n}):"]
        for item in results["missing_counts"][:top_n]:
            lines.append(
                f"  {item['entity']} ({item['type']}) — {', '.join(item['fixtures'])}"
            )
    if results["unexpected_counts"]:
        lines += ["", f"Most common unexpected entities (top {top_n}):"]
        for item in results["unexpected_counts"][:top_n]:
            lines.append(
                f"  {item['entity']} ({item['type']}) — {', '.join(item['fixtures'])}"
            )

    absent = [(f["id"], f["absent_types"]) for f in results["fixtures"] if f["absent_types"]]
    if absent:
        lines += ["", "Intentionally absent entity types (per fixture design):"]
        for fid, types in absent:
            lines.append(f"  {fid}: {', '.join(types)}")

    return "\n".join(lines)


__all__ = [
    "FIXTURES_DIR", "MODES", "load_manifest", "run_batch",
    "has_discrepancies", "format_batch_report",
]
