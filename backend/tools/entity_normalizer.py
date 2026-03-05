#!/usr/bin/env python3
"""
entity_normalizer.py — Entity Resolution for Resume Explorer JSON-LD Exports
=============================================================================

PURPOSE:
  Resume Explorer extracts entities from resume PDFs, but when processing
  multiple resume variants (or even a single one), naming inconsistencies
  creep in:
    - "GA4" vs "Google Analytics 4" vs "Google Analytics"
    - "machine learning" vs "Machine Learning"
    - "GUI%20development" vs "GUI development" (URL encoding artifacts)

  These duplicates degrade the knowledge graph: queries miss connections,
  the graph_analyzer.py pipeline reports false skill gaps, and the user-
  facing visualization shows confusing duplicate nodes.

  This script normalizes entities BEFORE downstream analysis, producing
  a clean JSON-LD where each real-world concept appears exactly once.

APPROACH:
  Three-phase normalization, from cheapest to most expensive:

  Phase 1 — DETERMINISTIC (free, instant)
    URL-decode all technology names ("GUI%20development" → "GUI development")
    Deduplicate exact case-insensitive matches ("wiki" → "Wiki")

  Phase 2 — ESCO-ANCHORED (free, instant)
    Any two entities sharing the same ESCO URI are definitionally identical.
    Merge them immediately. This leverages the semantic web infrastructure
    Resume Explorer already built — it's free normalization.

  Phase 3 — LLM BATCH (costs ~$0.01–0.05, takes seconds)
    Send all remaining entities to an LLM in a single structured call per
    entity type. The LLM sees the full context simultaneously, catching
    semantic aliases that fuzzy string matching would miss entirely
    (e.g., "GA4" vs "Google Analytics 4" scores ~0.35 on SequenceMatcher).

    WHY NOT FUZZY MATCHING?
    The podcast project (GraphRAG with Podcasts) used fuzzy matching with
    a 0.85 SequenceMatcher threshold because it had 720 concepts — making
    O(n²) LLM pairwise comparisons prohibitively expensive (~259K calls).
    Resume graphs have 20–50 entities. At that scale, a single batch LLM
    call is cheaper, faster, and far more accurate than threshold tuning.

PIPELINE POSITION:
  Resume Explorer export (JSON-LD)
    → entity_normalizer.py  ← YOU ARE HERE
    → normalized JSON-LD
    → graph_analyzer.py
    → insight documents
    → ChromaDB

USAGE:
  python entity_normalizer.py --input resume-graph.jsonld --output normalized.jsonld
  python entity_normalizer.py --input resume-graph.jsonld --output normalized.jsonld --dry-run
  python entity_normalizer.py --input resume-graph.jsonld --output normalized.jsonld --provider openai

DESIGN DECISIONS (with rationale):
  - Typed batch LLM calls (1 call per entity type, not pairwise comparisons)
    because resume-scale entity counts make batch feasible and far more accurate
  - ESCO anchoring before LLM because it's free and definitive
  - URL decoding as a separate deterministic phase because it's a data quality
    bug, not a semantic ambiguity — no reason to burn LLM tokens on it
  - altLabel preservation (from podcast project's SKOS patterns) so retrieval
    can match on ANY variant name after normalization
  - Writes a normalization report alongside the output for transparency

PORTED FROM:
  The merge logic, SKOS vocabulary, and altLabel preservation patterns come
  from the GraphRAG with Podcasts concept normalization pipeline. What changed:
  fuzzy+threshold → batch LLM (different scale, different optimal strategy).
"""

import json
import argparse
import sys
import os
from urllib.parse import unquote
from datetime import datetime
from collections import defaultdict
from typing import Any

# ─── CONSTANTS ────────────────────────────────────────────────

# JSON-LD namespace prefixes used by Resume Explorer
RE = "http://resumeexplorer.org/ontology#"
SCHEMA = "http://schema.org/"
SKOS = "http://www.w3.org/2004/02/skos/core#"
ESCO_TYPE = "http://data.europa.eu/esco/Skill"
RE_RESOURCE = "http://resumeexplorer.org/resource/"


# ─── PHASE 1: DETERMINISTIC CLEANUP ──────────────────────────

def url_decode_value(value: str) -> str:
    """
    Fix URL-encoding artifacts in technology names.

    Resume Explorer sometimes stores technology names as URI fragments,
    which means spaces become %20, etc. This is a data quality issue,
    not a semantic ambiguity.

    "GUI%20development" → "GUI development"
    "eye%20tracking"    → "eye tracking"
    "Lean%20Six-Sigma"  → "Lean Six-Sigma"
    """
    return unquote(value)


def normalize_case_key(label: str) -> str:
    """
    Generate a case-insensitive grouping key.

    Used to detect trivial case variants like "wiki" / "Wiki" / "WIKI".
    We strip whitespace and lowercase for comparison, but preserve the
    original labels for canonical selection.
    """
    return label.strip().lower()


# ─── DATA EXTRACTION ─────────────────────────────────────────

def extract_entity_value(field_list: list, key: str = "@value") -> str | None:
    """
    Safely pull a scalar value from JSON-LD's verbose value format.

    JSON-LD wraps values like: [{"@value": "Python"}]
    This helper handles the unwrapping and returns None if missing.
    """
    if not field_list:
        return None
    for item in field_list:
        if isinstance(item, dict) and key in item:
            return item[key]
        if isinstance(item, str):
            return item
    return None


def extract_all_values(field_list: list, key: str = "@value") -> list[str]:
    """Extract ALL values from a JSON-LD field list (not just the first)."""
    results = []
    for item in field_list:
        if isinstance(item, dict):
            val = item.get(key)
            if val is not None:
                results.append(str(val))
        elif isinstance(item, str):
            results.append(item)
    return results


def extract_entities(data: list[dict]) -> dict:
    """
    Parse the JSON-LD export into a structured inventory of all entities.

    Returns a dict with:
      - skills: {entity_id: {label, esco_uri, category, ...}}
      - technologies: {raw_label: [list of (job_id, original_form) tuples]}
      - jobs: {entity_id: {title, technologies: [...]}}
      - person: {entity_id: {name, skills: [...], jobs: [...]}}

    This separation by type is critical for Phase 3 — we never compare
    skills against organizations, which eliminates false positives and
    reduces the LLM's cognitive load.
    """
    skills = {}
    technologies = defaultdict(list)  # decoded_label → [(job_id, original_form)]
    jobs = {}
    person = None

    for entity in data:
        entity_type = entity.get("@type", [])
        entity_id = entity.get("@id", "")

        # ── Person ──
        if f"{SCHEMA}Person" in entity_type:
            person = {
                "id": entity_id,
                "name": extract_entity_value(entity.get(f"{SCHEMA}name", [])),
                "skill_ids": [
                    ref["@id"] for ref in entity.get(f"{RE}hasSkill", [])
                    if isinstance(ref, dict) and "@id" in ref
                ],
                "job_ids": [
                    ref["@id"] for ref in entity.get(f"{RE}hasJob", [])
                    if isinstance(ref, dict) and "@id" in ref
                ],
            }

        # ── Skills (typed ESCO entities with prefLabels) ──
        elif ESCO_TYPE in entity_type:
            label = extract_entity_value(entity.get(f"{SKOS}prefLabel", []))
            esco_uri = None
            for match in entity.get(f"{SKOS}exactMatch", []):
                if isinstance(match, dict) and "@id" in match:
                    esco_uri = match["@id"]

            skills[entity_id] = {
                "label": label,
                "esco_uri": esco_uri,
                "category": extract_entity_value(entity.get(f"{RE}skillCategory", [])),
                "proficiency": extract_entity_value(entity.get(f"{RE}proficiencyLevel", [])),
            }

        # ── Jobs (contain usedTechnology references) ──
        elif f"{SCHEMA}JobPosting" in entity_type:
            title = extract_entity_value(entity.get(f"{SCHEMA}title", []))

            # Extract technology references — both @id and @value forms
            raw_techs = entity.get(f"{RE}usedTechnology", [])
            tech_labels = set()
            for ref in raw_techs:
                if isinstance(ref, dict):
                    if "@value" in ref:
                        tech_labels.add(ref["@value"])
                    elif "@id" in ref:
                        # Extract name from URI: .../resource/Python → Python
                        name = ref["@id"].split("/")[-1]
                        tech_labels.add(name)

            jobs[entity_id] = {
                "title": title,
                "raw_technologies": tech_labels,
            }

            # Index each technology back to its source job
            for label in tech_labels:
                decoded = url_decode_value(label)
                technologies[decoded].append((entity_id, label))

    return {
        "skills": skills,
        "technologies": technologies,
        "jobs": jobs,
        "person": person,
    }


# ─── PHASE 2: ESCO-ANCHORED MERGE ────────────────────────────

def find_esco_groups(skills: dict) -> list[list[str]]:
    """
    Group skills that share the same ESCO URI.

    If two skill entities both have skos:exactMatch pointing to the same
    ESCO concept, they are definitionally the same skill — no LLM needed.

    This is free normalization from the semantic web infrastructure.
    In practice, this catches duplicates introduced by uploading multiple
    resume variants where the same skill got extracted with a new UUID
    each time but linked to the same ESCO concept.

    Returns: list of groups, where each group is [entity_id, entity_id, ...]
    """
    esco_to_ids = defaultdict(list)
    for entity_id, info in skills.items():
        if info["esco_uri"]:
            esco_to_ids[info["esco_uri"]].append(entity_id)

    # Only return groups with 2+ members (actual duplicates)
    return [ids for ids in esco_to_ids.values() if len(ids) > 1]


# ─── PHASE 3: LLM BATCH NORMALIZATION ────────────────────────

def build_normalization_prompt(labels: list[str], entity_type: str) -> str:
    """
    Construct the prompt for batch entity resolution.

    Design decisions in this prompt:
    - We show ALL labels at once so the LLM sees the full context
      (unlike pairwise comparison, which loses global context)
    - We ask for JSON output with explicit schema for reliable parsing
    - We instruct the LLM to be conservative: only group things that
      genuinely refer to the same concept (false merges are worse than
      residual duplicates, because merges lose information)
    - We ask for a canonical_label selection, preferring the most
      formal/complete form

    At resume scale (~20-50 entities), this is a single LLM call.
    """
    return f"""You are an entity resolution expert. Below is a list of {entity_type} names 
extracted from resume documents. Some of these refer to the same real-world concept 
but are written differently (abbreviations, case variants, alternative names).

TASK: Identify groups of names that refer to the SAME concept. 
Be CONSERVATIVE — only group things you are confident are the same.
Leave unique items as singleton groups.

For each group, pick the most formal/complete name as the canonical label.

ENTITY LIST:
{chr(10).join(f'  - "{label}"' for label in sorted(labels))}

Respond with ONLY valid JSON, no markdown fences, no explanation:
{{
  "groups": [
    {{
      "canonical": "the best/most complete name",
      "members": ["name1", "name2", "name3"],
      "reasoning": "brief explanation of why these are the same"
    }}
  ]
}}

Include ALL names — even unique ones should appear as single-member groups.
"""


def call_llm_for_normalization(
    labels: list[str],
    entity_type: str,
    provider: str = "anthropic"
) -> list[dict]:
    """
    Send a batch normalization request to the LLM.

    Returns a list of group dicts:
      [{"canonical": str, "members": [str, ...], "reasoning": str}, ...]

    Provider options:
      - "anthropic": Uses Claude via the Anthropic API
      - "openai": Uses GPT via the OpenAI API
      - "mock": Returns a trivial identity mapping (for testing/dry-run)

    The mock provider is essential for testing the pipeline without
    burning API tokens. It also serves as the fallback if the LLM
    call fails, ensuring the pipeline never crashes — it just produces
    less-normalized output (same graceful degradation pattern as
    Resume Explorer's dual-library PDF extraction).
    """
    if provider == "mock":
        # Identity mapping — each label is its own group
        return [
            {"canonical": label, "members": [label], "reasoning": "mock mode"}
            for label in labels
        ]

    prompt = build_normalization_prompt(labels, entity_type)

    if provider == "anthropic":
        try:
            import anthropic
            client = anthropic.Anthropic()
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text
        except Exception as e:
            print(f"  [WARN] Anthropic API call failed: {e}")
            print(f"  [WARN] Falling back to mock normalization")
            return call_llm_for_normalization(labels, entity_type, "mock")

    elif provider == "openai":
        try:
            import openai
            client = openai.OpenAI()
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
            )
            raw = response.choices[0].message.content
        except Exception as e:
            print(f"  [WARN] OpenAI API call failed: {e}")
            print(f"  [WARN] Falling back to mock normalization")
            return call_llm_for_normalization(labels, entity_type, "mock")

    else:
        raise ValueError(f"Unknown provider: {provider}")

    # Parse the LLM response
    # Strip markdown fences if the LLM added them despite instructions
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]  # drop first line
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    try:
        result = json.loads(raw)
        return result.get("groups", [])
    except json.JSONDecodeError as e:
        print(f"  [WARN] Failed to parse LLM response: {e}")
        print(f"  [WARN] Raw response: {raw[:300]}")
        return call_llm_for_normalization(labels, entity_type, "mock")


# ─── MERGE ENGINE ─────────────────────────────────────────────
#
# Ported from GraphRAG with Podcasts normalization pipeline.
# Core pattern: pick canonical label, collect all variants as altLabels,
# preserve all provenance. Adapted for JSON-LD rewriting.

def build_normalization_map(
    skills: dict,
    technologies: dict,
    provider: str = "anthropic",
) -> dict:
    """
    Execute the full three-phase normalization and return a mapping.

    Returns:
      {
        "label_map": {original_label: canonical_label, ...},
        "groups": [{"canonical": str, "members": [...], ...}, ...],
        "report": {statistics and decisions for transparency}
      }

    The label_map is the key output — it tells the JSON-LD rewriter
    what to rename. Every original label maps to either itself (no
    change needed) or a canonical form.
    """
    report = {
        "timestamp": datetime.now().isoformat(),
        "provider": provider,
        "phases": {},
    }

    # ── Collect ALL unique labels across both skills and technologies ──
    #
    # Skills have prefLabels (e.g., "Google Analytics 4")
    # Technologies have raw strings from jobs (e.g., "GA4", "Google Analytics")
    # We need to normalize ACROSS these two namespaces — that's the core
    # entity resolution challenge.

    skill_labels = {info["label"] for info in skills.values() if info["label"]}
    tech_labels = set(technologies.keys())
    all_labels = skill_labels | tech_labels

    print(f"  Found {len(skill_labels)} skill labels, {len(tech_labels)} technology labels")
    print(f"  Total unique labels before normalization: {len(all_labels)}")

    # ── Phase 1: Deterministic case-insensitive dedup ──
    #
    # Group labels that differ only by case. Pick the most "formal" form
    # as canonical (prefer Title Case or the form that appears as a
    # declared skill, since those are more carefully curated).

    case_groups = defaultdict(list)
    for label in all_labels:
        case_groups[normalize_case_key(label)].append(label)

    phase1_merges = {}
    for key, variants in case_groups.items():
        if len(variants) > 1:
            # Prefer the variant that's a declared skill (more curated)
            # Otherwise prefer Title Case, otherwise longest
            canonical = None
            for v in variants:
                if v in skill_labels:
                    canonical = v
                    break
            if not canonical:
                # Pick the most "formal" looking one (Title Case > lowercase > UPPER)
                canonical = sorted(variants, key=lambda x: (
                    not x[0].isupper(),  # prefer capitalized
                    -len(x),             # prefer longer
                ))[0]

            for v in variants:
                if v != canonical:
                    phase1_merges[v] = canonical

    report["phases"]["deterministic"] = {
        "merges": len(phase1_merges),
        "examples": dict(list(phase1_merges.items())[:5]),
    }
    print(f"  Phase 1 (deterministic): {len(phase1_merges)} case/encoding merges")

    # Apply Phase 1 merges to get the working label set
    remaining_labels = set()
    for label in all_labels:
        remaining_labels.add(phase1_merges.get(label, label))

    # ── Phase 2: ESCO-anchored merge ──
    #
    # If two labels are associated with skills that share an ESCO URI,
    # they're the same concept. This is free and definitive.

    esco_groups = find_esco_groups(skills)
    phase2_merges = {}
    for group in esco_groups:
        labels_in_group = [skills[eid]["label"] for eid in group if skills[eid]["label"]]
        if len(labels_in_group) > 1:
            canonical = labels_in_group[0]
            for label in labels_in_group[1:]:
                phase2_merges[label] = canonical

    report["phases"]["esco_anchored"] = {
        "merges": len(phase2_merges),
        "examples": dict(list(phase2_merges.items())[:5]),
    }
    print(f"  Phase 2 (ESCO-anchored): {len(phase2_merges)} merges")

    for old, new in phase2_merges.items():
        remaining_labels.discard(old)

    # ── Phase 3: LLM batch normalization ──
    #
    # Send all remaining labels to the LLM in one call. At resume scale
    # (20-50 labels), this is a single API call costing < $0.05.
    #
    # The LLM sees the full label set simultaneously, which means it can
    # catch semantic aliases like "GA4" ↔ "Google Analytics 4" that would
    # score ~0.35 on SequenceMatcher — far below any useful fuzzy threshold.

    remaining_list = sorted(remaining_labels)
    print(f"  Phase 3 (LLM batch): sending {len(remaining_list)} labels to {provider}...")

    llm_groups = call_llm_for_normalization(
        remaining_list,
        entity_type="skills and technologies from a professional resume",
        provider=provider,
    )

    phase3_merges = {}
    group_details = []
    for group in llm_groups:
        canonical = group.get("canonical", "")
        members = group.get("members", [])
        reasoning = group.get("reasoning", "")

        if len(members) > 1:
            group_details.append({
                "canonical": canonical,
                "merged": [m for m in members if m != canonical],
                "reasoning": reasoning,
            })
            for member in members:
                if member != canonical:
                    phase3_merges[member] = canonical

    report["phases"]["llm_batch"] = {
        "merges": len(phase3_merges),
        "groups": group_details,
    }
    print(f"  Phase 3 (LLM batch): {len(phase3_merges)} semantic merges")
    for g in group_details:
        print(f"    {g['merged']} → \"{g['canonical']}\"  ({g['reasoning']})")

    # ── Combine all phases into a single label map ──
    #
    # Chain the mappings: Phase 1 feeds into Phase 2 feeds into Phase 3.
    # If "machine learning" → "Machine Learning" (Phase 1) and then
    # "Machine Learning" → "ML" (Phase 3), the final map should send
    # "machine learning" → "ML".

    label_map = {}

    # Start with all original labels mapping to themselves
    for label in all_labels:
        label_map[label] = label

    # Apply Phase 1
    for old, new in phase1_merges.items():
        label_map[old] = new

    # Apply Phase 2 (on top of Phase 1 results)
    for old, new in phase2_merges.items():
        for k, v in label_map.items():
            if v == old:
                label_map[k] = new

    # Apply Phase 3 (on top of Phase 1+2 results)
    for old, new in phase3_merges.items():
        for k, v in label_map.items():
            if v == old:
                label_map[k] = new

    # Filter to only entries that actually changed
    changes_only = {k: v for k, v in label_map.items() if k != v}

    total_merges = len(changes_only)
    final_unique = len(set(label_map.values()))
    report["summary"] = {
        "original_labels": len(all_labels),
        "final_unique_labels": final_unique,
        "total_merges": total_merges,
        "reduction_pct": round((1 - final_unique / len(all_labels)) * 100, 1) if all_labels else 0,
    }

    print(f"\n  SUMMARY: {len(all_labels)} labels → {final_unique} unique ({total_merges} merges)")

    return {
        "label_map": label_map,
        "groups": group_details,
        "report": report,
    }


# ─── JSON-LD REWRITER ────────────────────────────────────────

def rewrite_jsonld(
    data: list[dict],
    label_map: dict,
) -> list[dict]:
    """
    Apply the normalization map to the JSON-LD, rewriting entity labels
    and technology references in-place.

    What gets rewritten:
    1. Skill prefLabels — updated to canonical form
    2. Job usedTechnology @value entries — updated to canonical form
    3. Job usedTechnology @id entries — URI fragment updated to match

    What does NOT get rewritten:
    - Entity @id URIs for skills (these are UUIDs, stable by design)
    - ESCO URIs (external identifiers, never touch these)
    - Job titles, person names, org names (not in scope for this normalizer)

    The rewriter also adds skos:altLabel entries to preserve all variant
    names — ported from the podcast normalization's altLabel preservation
    pattern. This ensures retrieval can still match on any variant.
    """
    # Build a reverse map: canonical → set of all original forms
    canonical_to_variants = defaultdict(set)
    for original, canonical in label_map.items():
        if original != canonical:
            canonical_to_variants[canonical].add(original)

    # Deep copy to avoid mutating the input
    output = json.loads(json.dumps(data))

    for entity in output:
        entity_type = entity.get("@type", [])

        # ── Rewrite Skill prefLabels ──
        if ESCO_TYPE in entity_type:
            pref_labels = entity.get(f"{SKOS}prefLabel", [])
            for i, item in enumerate(pref_labels):
                if isinstance(item, dict) and "@value" in item:
                    old_label = item["@value"]
                    new_label = label_map.get(old_label, old_label)
                    if old_label != new_label:
                        pref_labels[i]["@value"] = new_label

                        # Add altLabels for the variant names
                        # (preserves retrieval on original forms)
                        alt_labels = entity.get(f"{SKOS}altLabel", [])
                        variants = canonical_to_variants.get(new_label, set())
                        for variant in variants:
                            alt_entry = {"@value": variant}
                            if alt_entry not in alt_labels:
                                alt_labels.append(alt_entry)
                        if alt_labels:
                            entity[f"{SKOS}altLabel"] = alt_labels

        # ── Rewrite Job usedTechnology references ──
        elif f"{SCHEMA}JobPosting" in entity_type:
            tech_refs = entity.get(f"{RE}usedTechnology", [])
            seen_values = set()   # track to deduplicate after normalization
            seen_ids = set()
            cleaned_refs = []

            for ref in tech_refs:
                if isinstance(ref, dict):
                    if "@value" in ref:
                        old_label = url_decode_value(ref["@value"])
                        new_label = label_map.get(old_label, old_label)
                        if new_label not in seen_values:
                            seen_values.add(new_label)
                            cleaned_refs.append({"@value": new_label})

                    elif "@id" in ref:
                        old_name = url_decode_value(ref["@id"].split("/")[-1])
                        new_name = label_map.get(old_name, old_name)
                        new_id = f"{RE_RESOURCE}{new_name}"
                        if new_id not in seen_ids:
                            seen_ids.add(new_id)
                            cleaned_refs.append({"@id": new_id})

            entity[f"{RE}usedTechnology"] = cleaned_refs

    return output


# ─── MAIN ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Normalize entities in Resume Explorer JSON-LD exports",
        epilog="Produces a clean JSON-LD where each concept appears exactly once.",
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to the JSON-LD file exported from Resume Explorer",
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Path to write the normalized JSON-LD",
    )
    parser.add_argument(
        "--provider", "-p",
        choices=["anthropic", "openai", "mock"],
        default="mock",
        help=(
            "LLM provider for Phase 3 semantic normalization. "
            "'mock' skips the LLM call (useful for testing). "
            "Default: mock"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing any files",
    )
    parser.add_argument(
        "--report", "-r",
        help="Path to write the normalization report (JSON). Default: <output>.report.json",
    )
    args = parser.parse_args()

    # ── Load ──
    print(f"\nEntity Normalizer for Resume Explorer")
    print(f"{'=' * 40}")
    print(f"  Input:    {args.input}")
    print(f"  Output:   {args.output}")
    print(f"  Provider: {args.provider}")
    print()

    with open(args.input, "r") as f:
        data = json.load(f)

    if not isinstance(data, list):
        print("[ERROR] Expected a JSON array at top level. Is this a Resume Explorer export?")
        sys.exit(1)

    print(f"  Loaded {len(data)} entities from {args.input}")

    # ── Extract ──
    entities = extract_entities(data)
    print(f"  Parsed: {len(entities['skills'])} skills, "
          f"{len(entities['technologies'])} technologies, "
          f"{len(entities['jobs'])} jobs")
    print()

    # ── Normalize ──
    print("Running normalization...")
    result = build_normalization_map(
        skills=entities["skills"],
        technologies=entities["technologies"],
        provider=args.provider,
    )

    # ── Show changes ──
    changes = {k: v for k, v in result["label_map"].items() if k != v}
    if changes:
        print(f"\nLabel changes:")
        for old, new in sorted(changes.items()):
            print(f'  "{old}" → "{new}"')
    else:
        print("\nNo changes needed — all labels are already normalized.")

    if args.dry_run:
        print("\n[DRY RUN] No files written.")
        return

    # ── Rewrite ──
    print(f"\nRewriting JSON-LD...")
    normalized = rewrite_jsonld(data, result["label_map"])

    with open(args.output, "w") as f:
        json.dump(normalized, f, indent=2, ensure_ascii=False)
    print(f"  Written: {args.output}")

    # ── Report ──
    report_path = args.report or f"{args.output}.report.json"
    with open(report_path, "w") as f:
        json.dump(result["report"], f, indent=2, ensure_ascii=False)
    print(f"  Report:  {report_path}")

    print(f"\nDone. Normalized JSON-LD ready for graph_analyzer.py")


if __name__ == "__main__":
    main()
