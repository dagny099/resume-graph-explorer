#!/usr/bin/env python3
"""
Run the extraction evaluation comparison from the command line.

Usage (from backend/):
    # Compare one extraction output against gold labels
    python evaluation/run_eval.py \
        --extracted data/sessions/<id>/extracted/<doc>.json \
        --expected evaluation/fixtures/sample_resume_001.expected.json

    # Demo mode: compare the bundled simulated extraction against the gold file
    python evaluation/run_eval.py --demo

    # Batch mode: run every fixture in fixtures/manifest.json and aggregate
    python evaluation/run_eval.py --all
    python evaluation/run_eval.py --all --mode normalized
    python evaluation/run_eval.py --all --extracted-dir evaluation/live_runs/<ts>
    python evaluation/run_eval.py --all --strict

Everything here is deterministic and offline — no LLM calls, no API keys.

Exit codes:
    single / --demo:  0 if every expected entity was found (no misses), 1 otherwise.
    --all:            0 if the batch ran; with --strict, 1 if ANY fixture has a
                      missing or unexpected entity. Note: the bundled simulated
                      extractions are deliberately imperfect, so
                      `--all --strict` against them exits 1 by design — strict
                      mode is meant for real extraction outputs
                      (--extracted-dir) once they should be clean.
    2 on usage/configuration errors (argparse default).
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from compare import compare_extraction, format_report  # noqa: E402
from batch import FIXTURES_DIR, MODES, run_batch, has_discrepancies, format_batch_report  # noqa: E402


def _run_single(extracted_path: Path, expected_path: Path) -> int:
    extracted = json.loads(extracted_path.read_text())
    expected = json.loads(expected_path.read_text())

    report = compare_extraction(extracted, expected)
    print(f"Extraction: {extracted_path}")
    print(f"Gold:       {expected_path}\n")
    print(format_report(report))

    all_found = all(not r["missing"] for r in report["by_type"].values())
    return 0 if all_found else 1


def _run_all(mode: str, extracted_dir: str, strict: bool) -> int:
    results = run_batch(
        fixtures_dir=FIXTURES_DIR,
        mode=mode,
        extracted_dir=Path(extracted_dir) if extracted_dir else None,
    )
    print(format_batch_report(results))
    if strict and has_discrepancies(results):
        print("\n--strict: discrepancies found, exiting 1")
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extracted", help="Path to extraction output JSON")
    parser.add_argument("--expected", help="Path to expected-entities gold JSON")
    parser.add_argument(
        "--demo", action="store_true",
        help="Use the bundled sample_resume_001 fixtures instead of --extracted/--expected",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Batch mode: evaluate every fixture in fixtures/manifest.json",
    )
    parser.add_argument(
        "--mode", choices=MODES, default="raw",
        help="Batch gold labels: 'raw' (surface forms) or 'normalized' "
             "(canonical labels; fixtures without a normalized gold are skipped)",
    )
    parser.add_argument(
        "--extracted-dir",
        help="Batch mode: directory of real extraction outputs named "
             "<fixture-id>.json (default: bundled simulated .extracted.json files)",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Batch mode: exit 1 if any fixture has a missing or unexpected entity",
    )
    args = parser.parse_args()

    if args.all:
        return _run_all(args.mode, args.extracted_dir, args.strict)
    if args.demo:
        return _run_single(
            FIXTURES_DIR / "sample_resume_001.extracted.json",
            FIXTURES_DIR / "sample_resume_001.expected.json",
        )
    if args.extracted and args.expected:
        return _run_single(Path(args.extracted), Path(args.expected))
    parser.error("Provide --extracted and --expected, use --demo, or use --all")


if __name__ == "__main__":
    sys.exit(main())
