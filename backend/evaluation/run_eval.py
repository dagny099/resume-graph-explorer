#!/usr/bin/env python3
"""
Run the extraction evaluation comparison from the command line.

Usage (from backend/):
    # Compare an extraction output against gold labels
    python evaluation/run_eval.py \
        --extracted data/sessions/<id>/extracted/<doc>.json \
        --expected evaluation/fixtures/sample_resume_001.expected.json

    # Demo mode: compare the bundled simulated extraction against the gold file
    python evaluation/run_eval.py --demo

Exit code is 0 if every expected entity was found (recall == 1.0 for all
types), 1 otherwise — so this can gate CI once a real eval set exists.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from compare import compare_extraction, format_report  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extracted", help="Path to extraction output JSON")
    parser.add_argument("--expected", help="Path to expected-entities gold JSON")
    parser.add_argument(
        "--demo", action="store_true",
        help="Use the bundled sample fixtures instead of --extracted/--expected",
    )
    args = parser.parse_args()

    if args.demo:
        extracted_path = FIXTURES / "sample_resume_001.extracted.json"
        expected_path = FIXTURES / "sample_resume_001.expected.json"
    elif args.extracted and args.expected:
        extracted_path = Path(args.extracted)
        expected_path = Path(args.expected)
    else:
        parser.error("Provide --extracted and --expected, or use --demo")

    extracted = json.loads(extracted_path.read_text())
    expected = json.loads(expected_path.read_text())

    report = compare_extraction(extracted, expected)
    print(f"Extraction: {extracted_path}")
    print(f"Gold:       {expected_path}\n")
    print(format_report(report))

    all_found = all(
        not r["missing"] for r in report["by_type"].values()
    )
    return 0 if all_found else 1


if __name__ == "__main__":
    sys.exit(main())
