"""
graph_analyzer.py — Graph-to-NL Analysis Pipeline for Digital Twin

Loads a Resume Explorer JSON-LD export, runs a battery of structural
analyses, and serializes each result as a natural language document
optimized for RAG retrieval in ChromaDB.

Usage:
  python graph_analyzer.py --input resume-graph.jsonld --output graph_insights/
  python graph_analyzer.py --input resume-graph.jsonld --output graph_insights/ --embed

Architecture:
  Each analyzer follows the pattern:
    1. LOAD     → Parse JSON-LD into Python objects (shared across all analyzers)
    2. COMPUTE  → Run analysis (pure Python / NetworkX)
    3. SERIALIZE → Convert to retrievable natural language
    4. METADATA → Attach tags, query hints, provenance

  The COMPUTE/SERIALIZE separation is deliberate:
    - You can re-serialize without re-computing (tune retrieval quality)
    - You can test compute and serialize independently
    - You can version serialization templates separately from analysis logic

Design principle for serialization:
  Each output document should read like a mini-briefing an analyst wrote,
  NOT like a data dump. Use language someone would SEARCH with. Provide
  interpretation, not just facts. Include semantic hooks for multiple
  query phrasings.
"""

import json
import argparse
import sys
import urllib.parse
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC, abstractmethod
from typing import Optional

# ─── Optional ESCO Lookup ─────────────────────────────────────────
# esco_lookup.py lives in the same tools/ directory as this script.
# Add the directory to sys.path so it's importable whether this module
# is run directly or loaded via importlib.util.spec_from_file_location().
_TOOLS_DIR = str(Path(__file__).resolve().parent)
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

try:
    from esco_lookup import ESCOLookup as _ESCOLookup
    _ESCO_AVAILABLE = True
except ImportError:
    _ESCO_AVAILABLE = False


# ─── URI Constants ────────────────────────────────────────────────

RE = "http://resumeexplorer.org/ontology#"
SCHEMA = "http://schema.org/"
SKOS = "http://www.w3.org/2004/02/skos/core#"
ESCO_SKILL = "http://data.europa.eu/esco/Skill"


# ─── JSON-LD Helpers ──────────────────────────────────────────────
# (Tested against actual Resume Explorer export format)

def _get_val(node: dict, prop: str) -> Optional[str]:
    """Get first value from a JSON-LD property."""
    vals = node.get(prop, [])
    if not vals:
        return None
    v = vals[0]
    return v.get("@value", v.get("@id"))


def _get_vals(node: dict, prop: str) -> list:
    """Get all values from a JSON-LD property."""
    return [v.get("@value", v.get("@id", "")) for v in node.get(prop, [])]


def _parse_job(node: dict) -> dict:
    """Parse a schema:JobPosting node into a plain dict."""
    return {
        "id": node["@id"],
        "title": _get_val(node, SCHEMA + "title"),
        "description": _get_val(node, SCHEMA + "description"),
        "start": _get_val(node, SCHEMA + "startDate"),
        "end": _get_val(node, SCHEMA + "endDate"),
        "org_id": _get_val(node, SCHEMA + "hiringOrganization"),
        "techs_used": [
            v for v in _get_vals(node, RE + "usedTechnology")
            if not v.startswith("http")
        ],
        "tech_refs": [
            v for v in _get_vals(node, RE + "usedTechnology")
            if v.startswith("http")
        ],
        "achievements": _get_vals(node, RE + "achievement"),
        "is_current": any(
            v.get("@value") is True
            for v in node.get(RE + "isCurrent", [])
        ),
    }


def _parse_skill(node: dict) -> dict:
    """Parse an esco:Skill node into a plain dict."""
    return {
        "id": node["@id"],
        "label": _get_val(node, SKOS + "prefLabel"),
        "category": _get_val(node, RE + "skillCategory"),
        "proficiency": _get_val(node, RE + "proficiencyLevel"),
        "years": _get_val(node, RE + "yearsExperience"),
        "esco_match": _get_val(node, SKOS + "exactMatch"),
        "broader": _get_vals(node, SKOS + "broader"),
        "narrower": _get_vals(node, SKOS + "narrower"),
    }


# ─── Data Models ──────────────────────────────────────────────────

@dataclass
class AnalysisDocument:
    """Output of a single graph analysis, ready for embedding."""
    analysis_type: str
    title: str
    content: str          # The NL document — this gets embedded
    metadata: dict = field(default_factory=dict)

    def to_markdown(self) -> str:
        """Serialize as markdown file with YAML frontmatter."""
        lines = ["---"]
        lines.append(f"analysis_type: {self.analysis_type}")
        lines.append(f"title: \"{self.title}\"")

        for k, v in self.metadata.items():
            if isinstance(v, list):
                lines.append(f"{k}:")
                for item in v:
                    lines.append(f"  - \"{item}\"")
            elif not isinstance(v, dict):
                lines.append(f"{k}: {v}")

        lines.append("---")
        lines.append("")
        lines.append(f"# {self.title}")
        lines.append("")
        lines.append(self.content)
        return "\n".join(lines)

    def to_chromadb_entry(self) -> dict:
        """Format for ChromaDB collection.add()."""
        # Flatten metadata for ChromaDB (it only accepts str/int/float/bool)
        flat_meta = {
            "analysis_type": self.analysis_type,
            "title": self.title,
            "source_file": self.metadata.get("source_file", ""),
            "person_name": self.metadata.get("person_name", ""),
            "analysis_date": self.metadata.get("analysis_date", ""),
            "source": "graph_analysis",  # distinguishes from text chunks
        }
        return {
            "id": f"graph_{self.analysis_type}",
            "document": self.content,
            "metadata": flat_meta,
        }


@dataclass
class ResumeGraph:
    """Parsed representation of a Resume Explorer JSON-LD export."""
    person_name: str = "Unknown"
    source_document: str = "Unknown"
    jobs: list = field(default_factory=list)
    skills: list = field(default_factory=list)
    education_ids: list = field(default_factory=list)
    certification_ids: list = field(default_factory=list)
    organization_ids: list = field(default_factory=list)
    raw_entities: list = field(default_factory=list)
    _person_node: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_jsonld(cls, path: str) -> "ResumeGraph":
        """Parse JSON-LD export into structured Python objects."""
        with open(path) as f:
            data = json.load(f)

        graph = cls(raw_entities=data)

        for node in data:
            types = node.get("@type", [])

            if SCHEMA + "Person" in types:
                graph._person_node = node
                graph.person_name = (
                    _get_val(node, SKOS + "prefLabel")
                    or _get_val(node, SCHEMA + "name")
                    or "Unknown"
                )
                graph.source_document = _get_val(node, RE + "sourceDocument") or "Unknown"
                graph.education_ids = _get_vals(node, SCHEMA + "alumniOf")
                graph.certification_ids = _get_vals(node, RE + "hasCertification")

            elif SCHEMA + "JobPosting" in types:
                graph.jobs.append(_parse_job(node))

            elif ESCO_SKILL in types:
                graph.skills.append(_parse_skill(node))

            elif SCHEMA + "Organization" in types:
                graph.organization_ids.append(node["@id"])

        # Sort jobs chronologically
        graph.jobs.sort(key=lambda j: j.get("start") or "0000")

        # Resolve tech references to skill labels.
        # usedTechnology triples are stored as URI references in the JSON-LD
        # (e.g. http://resumeexplorer.org/resource/{uuid}), not as string literals.
        # They land in tech_refs (filtered by startswith("http")) while techs_used
        # catches only literal strings. Build a label lookup and resolve both cases.
        skill_by_id = {}
        for s in graph.skills:
            if s["label"]:
                skill_by_id[s["id"]] = s["label"]           # full URI key
                skill_by_id[s["id"].split("/")[-1]] = s["label"]  # bare UUID key

        for job in graph.jobs:
            resolved = []
            # Resolve URI references (new export format)
            for ref in job.get("tech_refs", []):
                label = skill_by_id.get(ref) or skill_by_id.get(ref.split("/")[-1])
                if label:
                    resolved.append(label)
            # Replace any bare UUID strings in techs_used (old export format)
            real_techs = []
            for tech in job.get("techs_used", []):
                label = skill_by_id.get(tech)
                real_techs.append(label if label else tech)
            job["techs_used"] = real_techs + resolved

        return graph


# ─── Base Analyzer ────────────────────────────────────────────────

class GraphAnalyzer(ABC):
    """
    Base class for all graph analyses.

    Subclasses implement:
      - compute(graph) → dict of structured results
      - serialize(results, graph) → str of natural language

    The base class handles metadata, packaging, and the run() pipeline.
    """

    analysis_type: str = "base"
    title: str = "Base Analysis"
    tags: list = []
    query_hints: list = []

    def run(self, graph: ResumeGraph) -> AnalysisDocument:
        """Full pipeline: compute → serialize → package."""
        results = self.compute(graph)
        content = self.serialize(results, graph)

        return AnalysisDocument(
            analysis_type=self.analysis_type,
            title=self.title,
            content=content,
            metadata={
                "source_file": graph.source_document,
                "person_name": graph.person_name,
                "analysis_date": datetime.now().isoformat()[:10],
                "tags": self.tags,
                "query_hints": self.query_hints,
                "entity_count": len(graph.raw_entities),
                "job_count": len(graph.jobs),
                "skill_count": len(graph.skills),
            },
        )

    @abstractmethod
    def compute(self, graph: ResumeGraph) -> dict:
        """Run the analysis. Return structured data."""
        ...

    @abstractmethod
    def serialize(self, results: dict, graph: ResumeGraph) -> str:
        """
        Convert structured results to natural language.

        THIS IS THE ART. The text you produce here determines what
        questions will successfully retrieve this document from ChromaDB.

        Principles:
          1. Use language someone would SEARCH with
          2. Provide interpretation, not just data
          3. Include semantic hooks for multiple query phrasings
          4. Write as a coherent briefing, not a data dump
          5. Front-load the most important finding
        """
        ...


# ═══════════════════════════════════════════════════════════════════
# CONCRETE ANALYZERS
# ═══════════════════════════════════════════════════════════════════


# ─── ESCO-Backed Skill Grouper ────────────────────────────────────
# Groups skills by their ESCO broader concept using the ESCO REST API.
# Results are cached to disk (backend/data/esco/skill_cache.json) so
# repeat analysis runs are instant even with many skills.

def _group_skills_by_esco(skills: list, verbose: bool = False) -> tuple[dict, list]:
    """
    Look up all skills via ESCO REST API and group by broader concept.

    Returns:
        esco_groups: dict of {broader_label → [skill_dicts]}
                     (only for skills that matched ESCO)
        unmatched:   list of skill dicts with no ESCO match
                     (vendor-specific tools, niche terms, emerging tech)

    Falls back to (empty dict, all_skills) if esco_lookup is unavailable
    or the network is unreachable.
    """
    if not _ESCO_AVAILABLE:
        return {}, list(skills)

    labels = [s["label"] for s in skills if s.get("label")]
    try:
        esco = _ESCOLookup()
        results = esco.lookup_batch(labels, verbose=verbose)
    except Exception:
        return {}, list(skills)

    esco_groups: dict = {}
    unmatched = []
    for skill in skills:
        label = skill.get("label")
        if not label:
            unmatched.append(skill)
            continue
        match = results.get(label)
        if match and match.get("broader_label"):
            broader = match["broader_label"]
            esco_groups.setdefault(broader, []).append({
                **skill,
                "_esco_uri": match.get("uri"),
                "_esco_preferred": match.get("preferred_label"),
            })
        else:
            unmatched.append(skill)

    return esco_groups, unmatched


class SkillGapAnalyzer(GraphAnalyzer):
    """Compares declared skills (hasSkill) against used technologies (usedTechnology)."""

    analysis_type = "skill_gap"
    title = "Hidden Skills — Claimed vs. Used Analysis"
    tags = ["skills", "gaps", "hidden", "undersold", "capabilities", "resume"]
    query_hints = [
        "what skills am I missing",
        "hidden skills",
        "undersold capabilities",
        "what am I not claiming",
        "skills not on my resume",
        "what should I add to my resume",
        "unused skills",
        "skills I don't list",
    ]

    def compute(self, graph: ResumeGraph) -> dict:
        claimed = {s["label"].lower(): s for s in graph.skills}

        used_in_jobs = {}
        for job in graph.jobs:
            for tech in job.get("techs_used", []):
                key = tech.lower()
                used_in_jobs.setdefault(key, {"tech": tech, "roles": []})
                used_in_jobs[key]["roles"].append({
                    "title": job["title"],
                    "start": job.get("start", "?"),
                    "end": job.get("end", "present"),
                })

        overlap = []
        claimed_not_used = []
        for key, skill in claimed.items():
            if key in used_in_jobs:
                overlap.append(skill["label"])
            else:
                claimed_not_used.append(skill)

        used_not_claimed = []
        for key, info in used_in_jobs.items():
            if key not in claimed:
                used_not_claimed.append(info)

        return {
            "claimed_count": len(claimed),
            "used_count": len(used_in_jobs),
            "overlap_count": len(overlap),
            "overlap": overlap,
            "claimed_not_used": claimed_not_used,
            "used_not_claimed": used_not_claimed,
        }

    def serialize(self, results: dict, graph: ResumeGraph) -> str:
        name = graph.person_name.split()[0]
        lines = []

        overlap_str = ", ".join(results["overlap"]) if results["overlap"] else "none"
        lines.append(
            f"{name}'s resume declares **{results['claimed_count']} skills**, "
            f"but job history references **{results['used_count']} distinct technologies** "
            f"— with only **{results['overlap_count']}** appearing in both lists "
            f"({overlap_str}). "
            f"This reveals a gap between professional identity and documented experience."
        )
        lines.append("")

        if results["used_not_claimed"]:
            lines.append("## Undersold Capabilities")
            lines.append("")
            lines.append(
                f"Technologies {name} has hands-on experience with but doesn't claim as skills. "
                "They may represent expertise taken for granted, or capabilities deliberately "
                "dropped from the current professional identity."
            )
            lines.append("")

            by_role: dict = {}
            for item in results["used_not_claimed"]:
                for role in item["roles"]:
                    key = f"{role['title']} ({role['start']}–{role['end']})"
                    by_role.setdefault(key, []).append(item["tech"])

            for role_str, techs in by_role.items():
                lines.append(f"**{role_str}**")
                for tech in techs:
                    lines.append(f"- {tech}")
                lines.append("")

        if results["claimed_not_used"]:
            lines.append("## Ungrounded Claims")
            lines.append("")
            lines.append(
                "Skills declared on the resume but never linked to a specific role. "
                "They may be cross-cutting competencies used everywhere, soft skills, "
                "or areas that need stronger grounding in concrete job descriptions."
            )
            lines.append("")
            for skill in results["claimed_not_used"]:
                cat = skill.get("category", "?")
                prof = skill.get("proficiency", "unrated")
                lines.append(f"- **{skill['label']}** — {cat}, {prof}")

        return "\n".join(lines)


class CareerTopologyAnalyzer(GraphAnalyzer):
    """Finds bridge technologies, isolated clusters, and connectivity between roles."""

    analysis_type = "career_topology"
    title = "Career Topology — What Connects Different Roles"
    tags = ["topology", "bridges", "connections", "continuity", "career thread"]
    query_hints = [
        "what connects my roles",
        "career through-line",
        "bridge skills",
        "how are my jobs related",
        "career continuity",
        "what ties my experience together",
    ]

    def compute(self, graph: ResumeGraph) -> dict:
        tech_roles = {}
        for job in graph.jobs:
            for tech in job.get("techs_used", []):
                key = tech.lower()
                tech_roles.setdefault(key, {"tech": tech, "roles": []})
                tech_roles[key]["roles"].append(job["title"])

        bridges = {
            k: v for k, v in tech_roles.items() if len(v["roles"]) > 1
        }
        islands = {
            k: v for k, v in tech_roles.items() if len(v["roles"]) == 1
        }

        # Cluster roles by shared technology
        role_connections = {}
        for job in graph.jobs:
            title = job["title"]
            role_connections[title] = set()
            for tech in job.get("techs_used", []):
                for other_job in graph.jobs:
                    if other_job["title"] != title:
                        other_techs = [t.lower() for t in other_job.get("techs_used", [])]
                        if tech.lower() in other_techs:
                            role_connections[title].add(other_job["title"])

        isolated_roles = [
            r for r, connections in role_connections.items()
            if len(connections) == 0
        ]

        return {
            "bridges": bridges,
            "islands": islands,
            "total_techs": len(tech_roles),
            "job_count": len(graph.jobs),
            "role_connections": {r: list(c) for r, c in role_connections.items()},
            "isolated_roles": isolated_roles,
        }

    def serialize(self, results: dict, graph: ResumeGraph) -> str:
        name = graph.person_name.split()[0]
        lines = []

        bridge_count = len(results["bridges"])
        if bridge_count == 0:
            lines.append(
                f"Across **{results['job_count']} roles** and **{results['total_techs']} technologies**, "
                f"{name}'s career graph has **no bridge technologies** — no single technology "
                f"appears in more than one role. Each career chapter used an entirely different toolkit."
            )
        elif bridge_count <= 2:
            bridge_names = [v["tech"] for v in results["bridges"].values()]
            lines.append(
                f"Out of **{results['total_techs']} technologies** used across "
                f"**{results['job_count']} roles**, only **{bridge_count}** "
                f"({', '.join(bridge_names)}) appear in more than one job. "
                f"Career continuity is **not** at the tooling level — each transition "
                f"involved a near-complete technology stack change."
            )
        else:
            bridge_names = [v["tech"] for v in results["bridges"].values()]
            lines.append(
                f"{name}'s career shows **{bridge_count} bridge technologies** "
                f"({', '.join(bridge_names)}) connecting roles across "
                f"**{results['job_count']} positions**."
            )
        lines.append("")

        if results["bridges"]:
            lines.append("## Bridge Technologies")
            lines.append("")
            lines.append("Technologies appearing in multiple roles — the connective tissue of the career:")
            lines.append("")
            for key, info in results["bridges"].items():
                roles_str = " and ".join(info["roles"])
                lines.append(f"- **{info['tech']}** — connects: {roles_str}")
            lines.append("")

        if results["isolated_roles"]:
            lines.append("## Isolated Roles")
            lines.append("")
            lines.append("Roles with no shared technology with any other position:")
            lines.append("")
            for role in results["isolated_roles"]:
                lines.append(f"- {role}")
            lines.append("")
            lines.append(
                f"**The implication:** {name}'s value proposition is methodological and analytical, "
                f"not tool-specific. The career demonstrates adaptability — picking up whatever tools "
                f"each domain requires rather than building identity around a single technology stack."
            )

        return "\n".join(lines)


class TechEvolutionAnalyzer(GraphAnalyzer):
    """Chronological technology timeline showing how the toolkit changed over time."""

    analysis_type = "tech_evolution"
    title = "Technology Evolution — How the Toolkit Changed Over Time"
    tags = ["timeline", "evolution", "tools", "technology", "progression"]
    query_hints = [
        "how have my tools changed",
        "technology timeline",
        "tech stack history",
        "what tools have I used",
        "career progression technology",
    ]

    def compute(self, graph: ResumeGraph) -> dict:
        timeline = []
        for job in graph.jobs:  # already sorted chronologically
            timeline.append({
                "title": job["title"],
                "period": f"{job.get('start', '?')} – {job.get('end', 'present')}",
                "techs": job.get("techs_used", []),
                "is_current": job.get("is_current", False),
                "achievements": job.get("achievements", []),
            })

        # Track what was gained and lost at each transition
        transitions = []
        for i in range(1, len(timeline)):
            prev_techs = set(t.lower() for t in timeline[i - 1]["techs"])
            curr_techs = set(t.lower() for t in timeline[i]["techs"])
            transitions.append({
                "from_role": timeline[i - 1]["title"],
                "to_role": timeline[i]["title"],
                "gained": curr_techs - prev_techs,
                "lost": prev_techs - curr_techs,
                "retained": prev_techs & curr_techs,
            })

        return {"timeline": timeline, "transitions": transitions}

    def serialize(self, results: dict, graph: ResumeGraph) -> str:
        name = graph.person_name.split()[0]
        lines = []

        lines.append(
            f"{name}'s technology toolkit has evolved across **{len(results['timeline'])} roles**, "
            f"with major shifts at each career transition."
        )
        lines.append("")

        lines.append("## Chronological Technology Timeline")
        lines.append("")
        for entry in results["timeline"]:
            current_marker = " ← **CURRENT**" if entry["is_current"] else ""
            techs_str = ", ".join(entry["techs"]) if entry["techs"] else "*(no technologies listed)*"
            lines.append(f"### {entry['title']} ({entry['period']}){current_marker}")
            lines.append(f"**Tools:** {techs_str}")
            if entry["achievements"]:
                lines.append("")
                for a in entry["achievements"]:
                    lines.append(f"- {a}")
            lines.append("")

        if results["transitions"]:
            lines.append("## Transition Analysis")
            lines.append("")
            for t in results["transitions"]:
                lines.append(f"**{t['from_role']} → {t['to_role']}**")
                if t["retained"]:
                    lines.append(f"- *Retained:* {', '.join(sorted(t['retained']))}")
                if t["gained"]:
                    lines.append(f"- *Gained:* {', '.join(sorted(t['gained']))}")
                if t["lost"]:
                    lines.append(f"- *Dropped:* {', '.join(sorted(t['lost']))}")
                lines.append("")

        return "\n".join(lines)


class HierarchyMapAnalyzer(GraphAnalyzer):
    """Maps SKOS broader/narrower relationships and identifies flat vs. deep skill areas."""

    analysis_type = "hierarchy_map"
    title = "Skill Hierarchy — SKOS Taxonomy Structure"
    tags = ["hierarchy", "taxonomy", "SKOS", "skill relationships", "broader", "narrower"]
    query_hints = [
        "how do my skills relate",
        "skill hierarchy",
        "skill taxonomy",
        "skill categories",
        "what falls under what",
    ]

    def compute(self, graph: ResumeGraph) -> dict:
        # Check for explicit SKOS hierarchy already in the graph
        with_hierarchy = [s for s in graph.skills if s["broader"] or s["narrower"]]
        orphans = [s for s in graph.skills if not s["broader"] and not s["narrower"]]

        # Category grouping from extraction metadata (always available)
        by_category: dict = {}
        for skill in graph.skills:
            cat = skill.get("category") or "Uncategorized"
            by_category.setdefault(cat, []).append(skill)

        # ESCO-backed grouping: look up each skill and group by ESCO broader concept.
        # Uses REST API with disk cache — fast on repeat runs, slow (~0.1s/skill) on first run.
        esco_groups, unmatched = _group_skills_by_esco(graph.skills)

        return {
            "hierarchical_skills": with_hierarchy,
            "orphan_skills": orphans,
            "total_skills": len(graph.skills),
            "hierarchy_count": len(with_hierarchy),
            "by_category": by_category,
            "esco_groups": esco_groups,
            "esco_unmatched": unmatched,
            "esco_matched_count": len(graph.skills) - len(unmatched),
            "esco_available": _ESCO_AVAILABLE,
        }

    def serialize(self, results: dict, graph: ResumeGraph) -> str:
        name = graph.person_name.split()[0]
        lines = []

        total = results["total_skills"]
        matched = results["esco_matched_count"]
        pct = (matched * 100 // total) if total else 0

        if results["esco_available"]:
            lines.append(
                f"{name}'s graph contains **{total} skills**. "
                f"**{matched} ({pct}%)** matched to ESCO skill categories, "
                f"enabling standardized grouping by the European Skills/Competences taxonomy. "
                f"The remaining **{len(results['esco_unmatched'])}** are vendor-specific tools, "
                f"niche platforms, or emerging technologies not yet in the ESCO taxonomy."
            )
        else:
            lines.append(
                f"{name}'s graph contains **{total} skills**. "
                f"ESCO lookup unavailable (install esco_lookup or check network access)."
            )
        lines.append("")

        if results["hierarchy_count"] > 0:
            lines.append("## Explicit SKOS Hierarchy")
            lines.append("")

            def _decode_uri(uri: str) -> str:
                """Extract and URL-decode the last path segment of a URI."""
                segment = uri.split("/")[-1]
                return urllib.parse.unquote(segment).replace("_", " ")

            for s in results["hierarchical_skills"]:
                if s["narrower"]:
                    narrows = [_decode_uri(n) for n in s["narrower"]]
                    lines.append(f"- **{s['label']}** → includes: {', '.join(narrows)}")
                if s["broader"]:
                    broaders = [_decode_uri(b) for b in s["broader"]]
                    lines.append(f"- **{s['label']}** → falls under: {', '.join(broaders)}")
            lines.append("")

        if results["esco_groups"]:
            lines.append("## Skills by ESCO Category")
            lines.append("")
            lines.append(
                "Each group below is a real ESCO broader concept — "
                "not a keyword pattern, but a node in the European skill taxonomy:"
            )
            lines.append("")
            for broader_label, skills in sorted(results["esco_groups"].items()):
                lines.append(f"**{broader_label}** ({len(skills)} skill{'s' if len(skills) != 1 else ''})")
                lines.append("")
                for s in skills:
                    lines.append(f"- {s['label']}")
                lines.append("")

        if results["esco_unmatched"]:
            lines.append("## Domain-Specific & Uncategorized Skills")
            lines.append("")
            lines.append(
                "These skills have no direct match in the ESCO taxonomy. "
                "They are often vendor-specific products (AWS, Salesforce), "
                "emerging tools (LangChain, Databricks), or domain jargon "
                "that ESCO hasn't yet incorporated:"
            )
            lines.append("")
            for s in results["esco_unmatched"]:
                cat = s.get("category", "")
                cat_note = f" *({cat})*" if cat and cat.lower() != "uncategorized" else ""
                lines.append(f"- {s['label']}{cat_note}")
            lines.append("")

        if results["by_category"]:
            lines.append("## By Extraction Category")
            lines.append("")
            lines.append(
                "Categories assigned during resume extraction — "
                "complements the ESCO grouping above:"
            )
            lines.append("")
            for cat, skills in sorted(results["by_category"].items()):
                labels = ", ".join(s["label"] for s in skills)
                lines.append(f"**{cat}** ({len(skills)} skill{'s' if len(skills) != 1 else ''}): {labels}")
                lines.append("")

        return "\n".join(lines)


class ESCOCoverageAnalyzer(GraphAnalyzer):
    """Reports which skills are linked to ESCO URIs and which are string-only."""

    analysis_type = "esco_coverage"
    title = "ESCO Interoperability — Global Skill Identifiability"
    tags = ["ESCO", "interoperability", "linked data", "semantic web", "global skills"]
    query_hints = [
        "interoperability",
        "ESCO skills",
        "globally identifiable",
        "linked data coverage",
        "semantic web skills",
        "how portable is my profile",
    ]

    def compute(self, graph: ResumeGraph) -> dict:
        linked = [s for s in graph.skills if s["esco_match"]]
        unlinked = [s for s in graph.skills if not s["esco_match"]]
        pct = (len(linked) / len(graph.skills) * 100) if graph.skills else 0

        return {
            "linked": linked,
            "unlinked": unlinked,
            "total": len(graph.skills),
            "coverage_pct": round(pct),
        }

    def serialize(self, results: dict, graph: ResumeGraph) -> str:
        name = graph.person_name.split()[0]
        lines = []

        lines.append(
            f"**{results['coverage_pct']}%** of {name}'s skills "
            f"(**{len(results['linked'])}/{results['total']}**) are linked to "
            f"ESCO (European Skills/Competences/Occupations) URIs — making "
            f"them globally identifiable across any ESCO-aligned system."
        )
        lines.append("")

        if results["linked"]:
            lines.append("## Globally Identifiable Skills (ESCO-linked)")
            lines.append("")
            for s in results["linked"]:
                lines.append(f"- **{s['label']}**")
            lines.append("")

        if results["unlinked"]:
            lines.append("## String-Only Skills (not globally identifiable)")
            lines.append("")
            for s in results["unlinked"]:
                lines.append(f"- {s['label']} *({s.get('category', '?')})*")
            lines.append("")
            lines.append(
                f"**Pattern:** {name}'s foundational and well-known skills are globally identifiable, "
                f"but specialized differentiating skills (domain tools, niche platforms) are string-only. "
                f"In a cross-system search, someone looking for specific expertise would only find "
                f"this profile through exact string matching — not semantic discovery."
            )

        return "\n".join(lines)


class RoleProgressionAnalyzer(GraphAnalyzer):
    """Analyzes career arc, title evolution, and organizational trajectory."""

    analysis_type = "role_progression"
    title = "Role Progression — Career Arc and Trajectory"
    tags = ["career", "progression", "trajectory", "roles", "arc", "timeline"]
    query_hints = [
        "career path",
        "role history",
        "career trajectory",
        "job progression",
        "career arc",
        "what has Dagny done",
        "work history",
        "professional experience",
    ]

    def compute(self, graph: ResumeGraph) -> dict:
        roles = []
        for job in graph.jobs:
            roles.append({
                "title": job["title"],
                "start": job.get("start"),
                "end": job.get("end", "present"),
                "is_current": job.get("is_current", False),
                "org_id": job.get("org_id"),
                "achievements": job.get("achievements", []),
                "tech_count": len(job.get("techs_used", [])),
            })

        # Detect title patterns
        titles = [r["title"] for r in roles]
        unique_titles = set(titles)
        repeated_titles = [t for t in unique_titles if titles.count(t) > 1]

        # Detect org reuse
        org_ids = [r["org_id"] for r in roles if r["org_id"]]
        org_counts = {}
        for oid in org_ids:
            org_counts[oid] = org_counts.get(oid, 0) + 1
        repeated_orgs = {k: v for k, v in org_counts.items() if v > 1}

        return {
            "roles": roles,
            "total_roles": len(roles),
            "unique_titles": len(unique_titles),
            "repeated_titles": repeated_titles,
            "repeated_orgs": repeated_orgs,
        }

    def serialize(self, results: dict, graph: ResumeGraph) -> str:
        name = graph.person_name.split()[0]
        lines = []

        first = results["roles"][0] if results["roles"] else None

        lines.append(
            f"{name}'s career spans **{results['total_roles']} roles** "
            f"from **{first['start'] or '?'}** to present, "
            f"with **{results['unique_titles']} distinct titles**."
        )
        lines.append("")

        lines.append("## Career Timeline")
        lines.append("")
        for r in results["roles"]:
            current = " ← **CURRENT**" if r["is_current"] else ""
            period = f"{r['start'] or '?'} – {r['end']}"
            lines.append(f"### {r['title']} ({period}){current}")
            if r["achievements"]:
                for a in r["achievements"][:2]:
                    lines.append(f"- {a}")
            lines.append("")

        if results["repeated_titles"]:
            lines.append("## Recurring Titles")
            lines.append("")
            for t in results["repeated_titles"]:
                lines.append(
                    f"- **'{t}'** appears multiple times — suggesting either "
                    f"a return to a familiar role type or consistent professional identity."
                )
            lines.append("")

        if results["repeated_orgs"]:
            lines.append("## Organizational Loyalty")
            lines.append("")
            lines.append(
                f"**{len(results['repeated_orgs'])} organization(s)** appear in multiple roles — "
                f"indicating return engagements or long-term client relationships."
            )

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# PIPELINE RUNNER
# ═══════════════════════════════════════════════════════════════════

ANALYZER_BATTERY = [
    SkillGapAnalyzer(),
    CareerTopologyAnalyzer(),
    TechEvolutionAnalyzer(),
    HierarchyMapAnalyzer(),
    ESCOCoverageAnalyzer(),
    RoleProgressionAnalyzer(),
]


def run_pipeline(input_path: str, output_dir: str) -> list[AnalysisDocument]:
    """Full pipeline: load → analyze → serialize → save as markdown."""

    # 1. Load and parse
    graph = ResumeGraph.from_jsonld(input_path)
    print(f"✓ Loaded graph: {graph.person_name}")
    print(f"  Source: {graph.source_document}")
    print(f"  {len(graph.jobs)} jobs, {len(graph.skills)} skills, "
          f"{len(graph.raw_entities)} total entities")
    print()

    # 2. Run all analyses
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    documents = []
    for analyzer in ANALYZER_BATTERY:
        try:
            doc = analyzer.run(graph)
            documents.append(doc)

            # 3. Save as markdown
            md_path = output_path / f"{doc.analysis_type}.md"
            md_path.write_text(doc.to_markdown())
            print(f"  ✓ {doc.title}")
            print(f"    → {md_path} ({len(doc.content)} chars)")
        except Exception as e:
            print(f"  ✗ {analyzer.analysis_type}: {e}")

    print(f"\n✓ Generated {len(documents)} insight documents in {output_dir}")
    return documents


def embed_documents(documents: list[AnalysisDocument], collection_name: str = "digital_twin"):
    """
    Embed analysis documents into ChromaDB.

    This is a minimal integration — adapt to match your existing
    ChromaDB setup in the Digital Twin app.
    """
    try:
        import chromadb
    except ImportError:
        print("chromadb not installed — skipping embedding step")
        print("Run: pip install chromadb")
        return

    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_or_create_collection(name=collection_name)

    for doc in documents:
        entry = doc.to_chromadb_entry()
        collection.upsert(
            ids=[entry["id"]],
            documents=[entry["document"]],
            metadatas=[entry["metadata"]],
        )
        print(f"  ✓ Embedded: {entry['id']}")

    print(f"\n✓ Embedded {len(documents)} documents into '{collection_name}'")


# ═══════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analyze Resume Explorer graph export and generate NL insight documents"
    )
    parser.add_argument("--input", required=True, help="Path to JSON-LD export")
    parser.add_argument("--output", default="graph_insights/", help="Output directory for markdown files")
    parser.add_argument("--embed", action="store_true", help="Also embed into ChromaDB")
    parser.add_argument("--collection", default="digital_twin", help="ChromaDB collection name")
    args = parser.parse_args()

    docs = run_pipeline(args.input, args.output)

    if args.embed:
        embed_documents(docs, args.collection)
