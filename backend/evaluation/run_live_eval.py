#!/usr/bin/env python3
"""
Live extraction evaluation: drive a RUNNING backend over HTTP, upload every
fixture resume, collect the real LLM extraction outputs, and score them
against the fixture gold labels.

This is the opt-in, non-deterministic counterpart to `run_eval.py --all`
(which is offline and scores bundled simulated extractions). It is never run
by pytest and it costs real LLM tokens.

Prerequisites:
    1. Start the backend with a real LLM key in its environment, e.g.:
           cd backend && python -m resume_explorer.api.app
       (This script never sees or logs the API key — the backend holds it.)
    2. Run from backend/:
           python evaluation/run_live_eval.py
           python evaluation/run_live_eval.py --base-url http://localhost:5000
           python evaluation/run_live_eval.py --fixture sample_resume_004
           python evaluation/run_live_eval.py --keep-sessions

What it does, per fixture:
    - creates a fresh single-document session (POST /api/sessions) — one
      session per fixture so multi-document normalization never mixes fixtures
    - uploads <fixture>.txt (POST /api/sessions/<id>/documents)
    - polls GET /api/documents/<doc-id> until status is complete/error
    - fetches GET /api/documents/<doc-id>/entities and writes it to
      evaluation/live_runs/<UTC timestamp>/<fixture-id>.json
    - deletes the session afterwards unless --keep-sessions is passed

Then it scores the collected outputs with the same batch comparator:
    equivalent to `run_eval.py --all --extracted-dir <output dir>`.

Caveat on "raw": the backend runs deterministic + ESCO normalization
(Phases 1–2) automatically after extraction even for single-document
sessions, so the stored entities are "as-persisted" output, not the raw LLM
response. Phase 3 (LLM alias resolution) only runs if NORMALIZE_SINGLE_RESUME
is enabled — leave it off for raw-leaning scores, turn it on and use
`--mode normalized` to evaluate the full normalization pipeline.

Outputs land in evaluation/live_runs/ which is gitignored — never commit
generated session data.
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from batch import FIXTURES_DIR, MODES, load_manifest, run_batch, format_batch_report  # noqa: E402

LIVE_RUNS_DIR = Path(__file__).parent / "live_runs"


def _api(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/api{path}"


def evaluate_fixture(base_url: str, fixture_id: str, output_dir: Path,
                     timeout: float, poll_interval: float,
                     keep_sessions: bool) -> bool:
    """Upload one fixture resume, wait for extraction, save the entities JSON."""
    resume_path = FIXTURES_DIR / f"{fixture_id}.txt"
    session_id = None
    try:
        resp = requests.post(
            _api(base_url, "/sessions"),
            json={"name": f"eval-{fixture_id}"},
            timeout=30,
        )
        resp.raise_for_status()
        session_id = resp.json()["session"]["id"]

        with open(resume_path, "rb") as fh:
            resp = requests.post(
                _api(base_url, f"/sessions/{session_id}/documents"),
                files={"file": (resume_path.name, fh, "text/plain")},
                timeout=60,
            )
        resp.raise_for_status()
        document_id = resp.json()["document"]["id"]

        deadline = time.monotonic() + timeout
        status = "pending"
        while time.monotonic() < deadline:
            resp = requests.get(_api(base_url, f"/documents/{document_id}"), timeout=30)
            resp.raise_for_status()
            doc = resp.json()["document"]
            status = doc["status"]
            if status == "complete":
                break
            if status == "error":
                print(f"  {fixture_id}: extraction failed — {doc.get('error_message')}")
                return False
            time.sleep(poll_interval)
        else:
            print(f"  {fixture_id}: timed out after {timeout:.0f}s (status: {status})")
            return False

        resp = requests.get(_api(base_url, f"/documents/{document_id}/entities"), timeout=30)
        resp.raise_for_status()
        entities = resp.json()["entities"]

        out_path = output_dir / f"{fixture_id}.json"
        out_path.write_text(json.dumps(entities, indent=2))
        print(f"  {fixture_id}: extraction complete -> {out_path}")
        return True
    finally:
        if session_id and not keep_sessions:
            try:
                requests.delete(_api(base_url, f"/sessions/{session_id}"), timeout=30)
            except requests.RequestException:
                print(f"  {fixture_id}: warning — could not delete session {session_id}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--base-url", default="http://localhost:5000",
                        help="Backend base URL (default: http://localhost:5000)")
    parser.add_argument("--fixture", action="append", dest="fixtures",
                        help="Fixture id to evaluate (repeatable; default: all in manifest)")
    parser.add_argument("--mode", choices=MODES, default="raw",
                        help="Gold labels to score against (default: raw)")
    parser.add_argument("--timeout", type=float, default=180,
                        help="Seconds to wait for each extraction (default: 180)")
    parser.add_argument("--poll-interval", type=float, default=2,
                        help="Seconds between status polls (default: 2)")
    parser.add_argument("--keep-sessions", action="store_true",
                        help="Do not delete the backend sessions created for the run")
    parser.add_argument("--collect-only", action="store_true",
                        help="Collect extraction outputs but skip scoring")
    args = parser.parse_args()

    # Connectivity check before creating anything
    try:
        requests.get(_api(args.base_url, "/sessions"), timeout=10).raise_for_status()
    except requests.RequestException as e:
        print(f"Backend not reachable at {args.base_url}: {e}")
        print("Start it first (with an LLM API key in its environment).")
        return 2

    manifest_ids = [f["id"] for f in load_manifest()["fixtures"]]
    fixture_ids = args.fixtures or manifest_ids
    unknown = sorted(set(fixture_ids) - set(manifest_ids))
    if unknown:
        print(f"Unknown fixture id(s): {', '.join(unknown)}")
        return 2

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = LIVE_RUNS_DIR / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Live extraction eval — {len(fixture_ids)} fixture(s) via {args.base_url}")
    print(f"Outputs: {output_dir}\n")

    succeeded = 0
    for fixture_id in fixture_ids:
        if evaluate_fixture(args.base_url, fixture_id, output_dir,
                            args.timeout, args.poll_interval, args.keep_sessions):
            succeeded += 1

    print(f"\nCollected {succeeded}/{len(fixture_ids)} extraction outputs.")
    if not succeeded:
        return 1
    if args.collect_only:
        print(f"Score later with: python evaluation/run_eval.py --all "
              f"--extracted-dir {output_dir}")
        return 0

    results = run_batch(mode=args.mode, extracted_dir=output_dir)
    print()
    print(format_batch_report(results))
    print(f"\nRe-score anytime: python evaluation/run_eval.py --all "
          f"--mode {args.mode} --extracted-dir {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
