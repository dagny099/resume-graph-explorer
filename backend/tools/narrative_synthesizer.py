#!/usr/bin/env python3
"""
narrative_synthesizer.py — LLM-Narrated Career Synthesis
=========================================================

PURPOSE:
  The 6 structural analyses from graph_analyzer.py are individually accurate
  but generically narrated. Each analysis is an island — it doesn't know
  what the other 5 found. This script sends all 6 to an LLM and asks it
  to synthesize cross-cutting themes, producing personalized career
  narratives that feel insightful rather than templated.

  Produces TWO versions:
    Conservative — only claims directly supported by the analyses.
      Every observation must cite [source_analysis]. No speculation.
      Safe to embed in the Digital Twin's ChromaDB.

    Exploratory — allowed to infer, hypothesize, and suggest positioning.
      Still cites sources, but can connect dots the analyses don't
      explicitly draw. Intended for human review, not automated embedding.

WHY A SEPARATE SCRIPT (not a 7th analyzer in graph_analyzer.py):
  - graph_analyzer.py is fully deterministic. No LLM, no API keys,
    same input always produces same output. That property is valuable.
  - This script requires an LLM API key and produces non-deterministic
    output. Mixing it into the deterministic pipeline would compromise
    the whole pipeline's reproducibility guarantees.
  - Separation means you can re-run synthesis with different prompts
    or models without re-running the structural analyses.

PIPELINE POSITION:
  Resume Explorer export (.jsonld)
    → entity_normalizer.py      (deterministic + LLM)
    → graph_analyzer.py         (deterministic)
    → narrative_synthesizer.py  ← YOU ARE HERE (LLM-dependent)
    → embed into ChromaDB       (future)

USAGE:
  python narrative_synthesizer.py --input insights/ --output insights/
  python narrative_synthesizer.py --input insights/ --output insights/ --provider openai
  python narrative_synthesizer.py --input insights/ --output insights/ --model claude-opus-4-20250514

CONCERNS (read before embedding):
  1. RETRIEVAL COLLISION — If you embed both versions + the 6 structural
     analyses into ChromaDB, queries may retrieve overlapping documents.
     Recommendation: embed conservative only. Keep exploratory for human use.
  2. ERROR AMPLIFICATION — If the structural analyses contain errors
     (e.g., from missed entity normalization), the synthesis weaves those
     errors into a persuasive narrative. Always review structural reports first.
  3. NON-DETERMINISM — Same input produces different prose each run.
     Review before embedding. Treat output as a draft, not a fact.
  4. CAREER ADVICE — The exploratory version may suggest positioning
     strategies. It doesn't know your market, preferences, or constraints.
     Treat it as brainstorming, not an oracle.
"""

import json
import argparse
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional


# ─── CONSTANTS ────────────────────────────────────────────────

# The 6 structural analyses we expect to find (from graph_analyzer.py)
ANALYSIS_FILES = [
    "skill_gap.md",
    "career_topology.md",
    "tech_evolution.md",
    "hierarchy_map.md",
    "esco_coverage.md",
    "role_progression.md",
]


# ─── PROMPT ENGINEERING ───────────────────────────────────────
#
# Two prompts: conservative (grounded) and exploratory (inferential).
# Both receive the same 6 analyses as context. The difference is in
# what the LLM is permitted to do with that context.
#
# Design principle: the prompts explicitly require citation of source
# analyses using [brackets]. This creates an audit trail — every claim
# in the output can be traced back to a specific structural finding.

SYSTEM_PROMPT = """You are a career analyst synthesizing structural analyses 
of a person's career graph. You have been given 6 independent analyses, each 
derived from graph topology (not subjective assessment). Your job is to find 
cross-cutting themes and produce a personalized narrative.

CRITICAL RULES:
- Every observation MUST cite its source analysis in [brackets], e.g., 
  [skill_gap], [career_topology], [tech_evolution], [hierarchy_map], 
  [esco_coverage], [role_progression]
- When combining findings from multiple analyses, cite ALL relevant sources,
  e.g., [skill_gap + career_topology]
- Do NOT invent findings that aren't in the analyses
- Use the person's actual name, actual skills, actual role titles
- Write in second person ("you" / "your") addressing the person directly"""


CONSERVATIVE_PROMPT = """Synthesize these 6 career graph analyses into a 
cohesive narrative. You are writing the CONSERVATIVE version — every claim 
must be directly supported by the analyses provided.

RULES FOR THE CONSERVATIVE VERSION:
- State only what the analyses explicitly show
- Do not speculate about motivations, preferences, or future directions
- Do not give career advice
- When analyses could support multiple interpretations, state the ambiguity 
  rather than picking one
- Focus on: cross-cutting patterns visible only when analyses are combined,
  what specific combinations of findings reveal about this person's career
  structure, and any tensions or contradictions between analyses

FORMAT:
Write 3-5 themed sections (not one section per analysis). Each section should
draw from multiple analyses. Use descriptive headers that name the specific
pattern you're identifying, not generic headers like "Key Findings."

Begin with a 2-3 sentence overview that captures the most distinctive 
structural feature of this person's career graph.

Here are the 6 analyses:

{analyses}"""


EXPLORATORY_PROMPT = """Synthesize these 6 career graph analyses into a 
cohesive narrative. You are writing the EXPLORATORY version — you may infer, 
hypothesize, and suggest, but must still cite your reasoning.

RULES FOR THE EXPLORATORY VERSION:
- You may infer what specific combinations of findings suggest about 
  professional positioning, market differentiation, and career narrative
- You may hypothesize about why certain patterns exist (e.g., why skills 
  were dropped, why certain roles are isolated)
- You may suggest how specific findings could be leveraged in job searching,
  interviewing, or professional branding
- Mark inferences clearly: use phrases like "this suggests," "one 
  interpretation is," "this could indicate"
- Still cite source analyses for every observation — even speculative ones
  must be anchored in structural findings
- Think about what makes this person's career graph STRUCTURALLY UNUSUAL
  compared to a typical career. What would surprise a hiring manager?

FORMAT:
Write 4-6 themed sections. Each section should have a provocative header 
that names a specific insight, not a generic category. Include at least one 
section specifically about how structural findings could be leveraged for 
professional positioning.

Begin with a 2-3 sentence overview that captures what makes this person's 
career graph distinctive — not what's in it, but what's unusual about 
its STRUCTURE.

Here are the 6 analyses:

{analyses}"""


# ─── FILE I/O ─────────────────────────────────────────────────

def load_analyses(input_dir: Path) -> dict[str, str]:
    """
    Load all 6 structural analysis files from the input directory.

    Returns a dict mapping analysis name → full file content.
    Warns (but doesn't fail) if some analyses are missing — the
    synthesizer works with whatever subset is available.
    """
    analyses = {}
    missing = []

    for filename in ANALYSIS_FILES:
        filepath = input_dir / filename
        if filepath.exists():
            analyses[filename.replace(".md", "")] = filepath.read_text()
        else:
            missing.append(filename)

    if missing:
        print(f"  [WARN] Missing analyses: {', '.join(missing)}")
        print(f"  [WARN] Synthesis will proceed with {len(analyses)}/6 analyses")

    if not analyses:
        print(f"  [ERROR] No analysis files found in {input_dir}")
        print(f"  [ERROR] Run graph_analyzer.py first to generate them")
        sys.exit(1)

    return analyses


def format_analyses_for_prompt(analyses: dict[str, str]) -> str:
    """
    Format the analyses into a single string for the LLM prompt.

    Each analysis is wrapped in clear delimiters with its name,
    so the LLM can cite specific analyses by name.
    """
    sections = []
    for name, content in analyses.items():
        # Strip YAML front matter — the LLM doesn't need metadata tags
        parts = content.split("---")
        if len(parts) >= 3:
            # Content is after the second ---
            body = "---".join(parts[2:]).strip()
        else:
            body = content.strip()

        sections.append(f"═══ [{name}] ═══\n{body}")

    return "\n\n".join(sections)


# ─── LLM CALL ────────────────────────────────────────────────

def call_llm(
    system_prompt: str,
    user_prompt: str,
    provider: str = "anthropic",
    model: Optional[str] = None,
) -> str:
    """
    Send the synthesis request to the LLM.

    Uses the same provider abstraction pattern as entity_normalizer.py
    and Resume Explorer itself — never be architecturally dependent
    on a single provider.

    Returns the raw text response.
    """
    if provider == "anthropic":
        model = model or "claude-sonnet-4-20250514"
        try:
            import anthropic
            client = anthropic.Anthropic()
            response = client.messages.create(
                model=model,
                max_tokens=4000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return response.content[0].text
        except ImportError:
            print("  [ERROR] anthropic package not installed: pip install anthropic")
            sys.exit(1)
        except Exception as e:
            print(f"  [ERROR] Anthropic API call failed: {e}")
            sys.exit(1)

    elif provider == "openai":
        model = model or "gpt-4o"
        try:
            import openai
            client = openai.OpenAI()
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=4000,
            )
            return response.choices[0].message.content
        except ImportError:
            print("  [ERROR] openai package not installed: pip install openai")
            sys.exit(1)
        except Exception as e:
            print(f"  [ERROR] OpenAI API call failed: {e}")
            sys.exit(1)

    else:
        print(f"  [ERROR] Unknown provider: {provider}")
        print(f"  [ERROR] Use 'anthropic' or 'openai'")
        sys.exit(1)


# ─── OUTPUT GENERATION ────────────────────────────────────────

def build_front_matter(
    variant: str,
    person_name: str,
    source_analyses: list[str],
    provider: str,
    model: str,
) -> str:
    """
    Generate YAML front matter for the narrative document.

    Includes synthesis-specific metadata:
    - synthesis: true (flags this as LLM-interpreted, not structural)
    - variant: conservative|exploratory
    - source_analyses: which structural reports this was built from
    - provider/model: which LLM generated the narrative
    - generated_at: timestamp for versioning

    The synthesis flag is critical for downstream consumers. The Digital
    Twin's retrieval can filter on it (e.g., only retrieve synthesis
    documents when the query is about "career narrative" or "big picture",
    only retrieve structural documents for specific skill questions).
    """
    sources_yaml = "\n".join(f'  - "{s}"' for s in source_analyses)

    return f"""---
analysis_type: career_narrative
variant: {variant}
synthesis: true
title: "Career Narrative — {variant.title()} Synthesis"
person_name: {person_name}
generated_at: {datetime.now().isoformat()}
provider: {provider}
model: {model}
source_analyses:
{sources_yaml}
tags:
  - "narrative"
  - "synthesis"
  - "cross-cutting"
  - "career story"
  - "positioning"
query_hints:
  - "tell me about my career"
  - "what makes my background unique"
  - "career narrative"
  - "big picture"
  - "how does my experience fit together"
  - "what story does my career tell"
  - "professional positioning"
  - "career themes"
---"""


def extract_person_name(analyses: dict[str, str]) -> str:
    """
    Pull the person's name from any analysis's YAML front matter.

    Falls back to "the candidate" if not found — the narrative
    should still work without a name.
    """
    for content in analyses.values():
        for line in content.split("\n"):
            if line.strip().startswith("person_name:"):
                name = line.split(":", 1)[1].strip().strip('"')
                if name and name != "None":
                    return name
    return "the candidate"


# ─── MAIN ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate LLM-narrated career synthesis from structural analyses",
        epilog=(
            "Reads the 6 .md files from graph_analyzer.py and produces "
            "career_narrative_conservative.md and career_narrative_exploratory.md"
        ),
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Directory containing the 6 analysis .md files from graph_analyzer.py",
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Directory to write the narrative .md files",
    )
    parser.add_argument(
        "--provider", "-p",
        choices=["anthropic", "openai"],
        default="anthropic",
        help="LLM provider for narrative generation (default: anthropic)",
    )
    parser.add_argument(
        "--model", "-m",
        default=None,
        help=(
            "Specific model to use. Defaults: claude-sonnet-4-20250514 (anthropic), "
            "gpt-4o (openai). For deeper synthesis, try claude-opus-4-20250514."
        ),
    )
    parser.add_argument(
        "--conservative-only",
        action="store_true",
        help="Only generate the conservative version (faster, cheaper)",
    )
    parser.add_argument(
        "--exploratory-only",
        action="store_true",
        help="Only generate the exploratory version",
    )
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    effective_model = args.model or (
        "claude-sonnet-4-20250514" if args.provider == "anthropic" else "gpt-4o"
    )

    print(f"\nNarrative Synthesizer")
    print(f"{'=' * 40}")
    print(f"  Input:    {input_dir}")
    print(f"  Output:   {output_dir}")
    print(f"  Provider: {args.provider} ({effective_model})")
    print()

    # ── Load analyses ──
    print("Loading structural analyses...")
    analyses = load_analyses(input_dir)
    print(f"  Loaded {len(analyses)} analyses: {', '.join(analyses.keys())}")

    person_name = extract_person_name(analyses)
    print(f"  Person: {person_name}")
    print()

    # ── Format for prompt ──
    formatted = format_analyses_for_prompt(analyses)
    source_list = list(analyses.keys())

    # ── Generate variants ──
    variants_to_generate = []
    if args.exploratory_only:
        variants_to_generate = [("exploratory", EXPLORATORY_PROMPT)]
    elif args.conservative_only:
        variants_to_generate = [("conservative", CONSERVATIVE_PROMPT)]
    else:
        variants_to_generate = [
            ("conservative", CONSERVATIVE_PROMPT),
            ("exploratory", EXPLORATORY_PROMPT),
        ]

    for variant_name, prompt_template in variants_to_generate:
        print(f"Generating {variant_name} narrative...")
        print(f"  Sending {len(formatted)} chars to {args.provider}...")

        user_prompt = prompt_template.format(analyses=formatted)

        narrative = call_llm(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            provider=args.provider,
            model=args.model,
        )

        # ── Build output document ──
        front_matter = build_front_matter(
            variant=variant_name,
            person_name=person_name,
            source_analyses=source_list,
            provider=args.provider,
            model=effective_model,
        )

        full_document = f"{front_matter}\n\n{narrative}\n"

        # ── Write ──
        output_path = output_dir / f"career_narrative_{variant_name}.md"
        output_path.write_text(full_document)
        print(f"  ✓ Written: {output_path} ({len(narrative)} chars)")
        print()

    # ── Summary ──
    print(f"Done. Generated {len(variants_to_generate)} narrative(s) in {output_dir}/")
    print()
    print("NEXT STEPS:")
    print("  1. Read both versions and compare")
    print("  2. Check that every [bracketed] citation traces to a real finding")
    print("  3. For Digital Twin embedding: use the conservative version only")
    print("  4. For personal positioning/interview prep: the exploratory version")
    print()
    print("AUDIT: verify citations with:")
    print(f"  grep -o '\\[.*\\]' {output_dir}/career_narrative_conservative.md | sort | uniq -c")


if __name__ == "__main__":
    main()
