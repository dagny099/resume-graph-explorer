"""
Entity Normalization Service for Resume Explorer

Normalizes entity names across multiple resume documents to eliminate duplicates
and ensure consistent naming. Uses a three-phase approach:

1. DETERMINISTIC - Case-insensitive deduplication and URL decoding
2. ESCO-ANCHORED - Merge entities sharing the same ESCO URI
3. LLM BATCH - Semantic normalization using language models

Usage:
    normalizer = EntityNormalizer(provider="mock")  # or "anthropic", "openai"
    normalized_entities = normalizer.normalize_session_entities(all_entities)

─── ROLE IN THE NORMALIZATION ARCHITECTURE ────────────────────────────────────

This is the LIVE SESSION NORMALIZER. It runs automatically during upload
(triggered from routes.py:_maybe_normalize_session_entities), operating on
Python dict objects before they are serialized to RDF. Its job is to prevent
duplicate entity NODES in the knowledge graph when multiple resume variants
are uploaded to the same session.

Examples of what this handles:
  - "python" (resume A) and "Python" (resume B) → one canonical Skill node
  - "ML" (resume A) and "Machine Learning" (resume B) → one Skill node
  - "UT-Austin" (resume A) and "University of Texas at Austin" (resume B)
    → one Organization node (also backed by RDF builder fuzzy matching)

IMPORTANT — WHEN THIS RUNS:
  Currently triggered only when a session has 2+ completed documents
  (see routes.py). Single-resume sessions receive NO in-app normalization;
  they rely entirely on the RDF graph builder's own dedup caches
  (case-insensitive for skills, fuzzy-normalized for orgs).

─── COMPANION: backend/tools/entity_normalizer.py ─────────────────────────────

A separate normalizer exists for post-export offline use. It is NOT the same
job. The tools normalizer reconciles cross-namespace label inconsistencies
between Skill node prefLabels and usedTechnology free-text strings in job
records — a problem this service doesn't address because those two sets come
from separate LLM extraction paths and must be compared at the graph level.

  THIS FILE (services/entity_normalizer.py)
    Purpose:  prevent duplicate entity NODES across uploads
    When:     live, automatic, during upload
    Input:    Python dict objects (pre-RDF)
    Trigger:  session has 2+ completed documents

  backend/tools/entity_normalizer.py
    Purpose:  reconcile Skill prefLabels against usedTechnology strings
              for accurate skill_gap.md analysis; adds skos:altLabel entries
    When:     offline, manual, after JSON-LD export
    Input:    exported JSON-LD file
    Trigger:  user runs the script explicitly

Both normalizers use the same three-phase approach (deterministic → ESCO →
LLM batch), but they solve different problems at different pipeline stages.
────────────────────────────────────────────────────────────────────────────────
"""

from urllib.parse import unquote
from collections import defaultdict
from typing import Dict, List, Any, Optional
import json

from ..utils import logger


class EntityNormalizer:
    """Normalizes entity names across resume documents."""

    def __init__(self, provider: str = "mock", llm_client=None):
        """
        Initialize entity normalizer.

        Args:
            provider: LLM provider to use ("anthropic", "openai", "ollama", or "mock")
            llm_client: LLM client instance (required for anthropic/openai/ollama)
        """
        self.provider = provider
        self.llm_client = llm_client

        if provider in ("anthropic", "openai", "ollama") and not llm_client:
            logger.warning(
                f"EntityNormalizer: {provider} provider requested but no LLM client provided. "
                f"Falling back to mock provider."
            )
            self.provider = "mock"

    def normalize_session_entities(
        self,
        all_entities: List[Dict[str, Any]],
        run_llm_phase: bool = True,
    ) -> Dict[str, Any]:
        """
        Normalize entities from multiple documents in a session.

        Args:
            all_entities: List of entity dicts from all documents in session
                Each dict should have: {person, jobs, skills, education, etc.}
            run_llm_phase: Whether to run Phase 3 (LLM semantic normalization).
                Set to False for single-resume sessions where only cheap
                deterministic + ESCO phases are needed.

        Returns:
            {
                "normalized_entities": List of normalized entity dicts,
                "label_map": {original: canonical} mapping,
                "report": {statistics and decisions}
            }
        """
        logger.info(f"Starting entity normalization with {self.provider} provider")

        # Extract all labels from all documents, keeping type pools separate so
        # Phase 3 can send type-annotated prompts and avoid cross-type contamination
        # (e.g., "MS" as an org abbreviation should never merge with "MS" as a degree).
        declared_skill_labels: set = set()  # from skill entities (curated prefLabels)
        tech_labels: set = set()            # from job.technologies_used (free-text)
        org_labels: set = set()
        degree_labels: set = set()
        skill_to_esco: Dict[str, str] = {}  # skill_label -> esco_uri
        verified_labels: set = set()        # labels from user_verified entities — treated as anchors

        for entities in all_entities:
            for skill in entities.get("skills", []):
                label = skill.get("name") or skill.get("label")
                if label:
                    decoded_label = self._url_decode(label)
                    declared_skill_labels.add(decoded_label)
                    esco = skill.get("esco_uri")
                    if esco:
                        skill_to_esco[decoded_label] = esco
                    if skill.get("user_verified"):
                        verified_labels.add(decoded_label)

            for job in entities.get("jobs", []):
                for tech in job.get("technologies_used", []):
                    decoded = self._url_decode(tech)
                    tech_labels.add(decoded)

            for org in entities.get("organizations", []):
                name = org.get("name")
                if name:
                    decoded = self._url_decode(name)
                    org_labels.add(decoded)

            for edu in entities.get("education", []):
                degree = edu.get("degree")
                if degree:
                    decoded = self._url_decode(degree)
                    degree_labels.add(decoded)

        # Skills and technologies share the same real-world concept space, so they
        # are treated as a single pool for dedup. Orgs and degrees are separate pools.
        skill_tech_labels = declared_skill_labels | tech_labels
        all_labels = skill_tech_labels | org_labels | degree_labels

        logger.info(
            f"Found {len(declared_skill_labels)} declared skill labels, "
            f"{len(tech_labels)} technology labels, "
            f"{len(org_labels)} organization labels, "
            f"{len(degree_labels)} degree labels "
            f"({len(all_labels)} unique total)"
        )

        # Phase 1: Deterministic normalization — run per type pool to prevent
        # cross-type case merges (e.g., "MS" org vs "MS" degree stay separate).
        phase1_skill_tech = self._phase1_deterministic(skill_tech_labels)
        phase1_org = self._phase1_deterministic(org_labels)
        phase1_degree = self._phase1_deterministic(degree_labels)
        phase1_map = {**phase1_skill_tech, **phase1_org, **phase1_degree}
        logger.info(f"Phase 1 (deterministic): {len(phase1_map)} merges")

        # Apply Phase 1 per pool, preserving per-type membership for Phase 3
        def _apply_m(labels: set, m: dict) -> set:
            return {m.get(l, l) for l in labels}

        remaining_declared = _apply_m(declared_skill_labels, phase1_skill_tech)
        remaining_techs = _apply_m(tech_labels, phase1_skill_tech)
        remaining_skill_tech = remaining_declared | remaining_techs
        remaining_orgs = _apply_m(org_labels, phase1_org)
        remaining_degrees = _apply_m(degree_labels, phase1_degree)

        # Phase 2: ESCO-anchored merge (skill+tech pool only — ESCO URIs are for skills)
        phase2_map = self._phase2_esco_anchored(remaining_skill_tech, skill_to_esco)
        logger.info(f"Phase 2 (ESCO-anchored): {len(phase2_map)} merges")

        # Apply Phase 2 to skill+tech subsets
        remaining_declared = _apply_m(remaining_declared, phase2_map)
        remaining_techs = _apply_m(remaining_techs, phase2_map)

        # Phase 3: LLM — three separate calls, each with a type-specific prompt.
        # Separation prevents "ML" (tech) from being confused with "ML" (org abbrev).
        # The skill+tech prompt annotates which labels are declared vs used-in-job,
        # helping the LLM confidently merge "ML" [used] ↔ "Machine Learning" [declared].
        if run_llm_phase:
            phase3_skill_tech, groups_st = self._phase3_skill_tech_batch(
                remaining_declared, remaining_techs
            )
            phase3_org, groups_org = self._phase3_labeled_batch(
                sorted(remaining_orgs), "organization name"
            )
            phase3_degree, groups_deg = self._phase3_labeled_batch(
                sorted(remaining_degrees), "academic degree or field of study"
            )
            phase3_map = {**phase3_skill_tech, **phase3_org, **phase3_degree}
            groups = groups_st + groups_org + groups_deg
        else:
            phase3_map, groups = {}, []

        logger.info(f"Phase 3 (LLM batch): {len(phase3_map)} merges (ran={run_llm_phase})")

        # Build final label map (chain all phases)
        label_map = self._build_final_map(all_labels, phase1_map, phase2_map, phase3_map)

        # Protect verified labels: they are authoritative anchors and must not be remapped.
        # Other labels may already normalize TO them (the map is unchanged for those).
        for vl in verified_labels:
            label_map[vl] = vl

        # Apply normalization to entities; track alt_labels on skills whose labels changed
        normalized_entities = self._apply_normalization(
            all_entities, label_map, declared_skill_labels, verified_labels=verified_labels
        )

        # Build report
        report = {
            "provider": self.provider,
            "phases": {
                "deterministic": {"merges": len(phase1_map)},
                "esco_anchored": {"merges": len(phase2_map)},
                "llm_batch": {
                    "merges": len(phase3_map),
                    "groups": groups,
                    "ran": run_llm_phase,
                },
            },
            "summary": {
                "original_labels": len(all_labels),
                "final_unique_labels": len(set(label_map.values())),
                "total_merges": sum(1 for k, v in label_map.items() if k != v),
            },
        }

        logger.info(
            f"Normalization complete: {len(all_labels)} labels → "
            f"{report['summary']['final_unique_labels']} unique "
            f"({report['summary']['total_merges']} merges)"
        )

        return {
            "normalized_entities": normalized_entities,
            "label_map": label_map,
            "report": report,
        }

    # =========================================================================
    # Phase 1: Deterministic
    # =========================================================================

    def _url_decode(self, value: str) -> str:
        """Decode URL-encoded strings (e.g., 'GUI%20development' -> 'GUI development')."""
        return unquote(value)

    def _normalize_case_key(self, label: str) -> str:
        """Generate case-insensitive grouping key."""
        return label.strip().lower()

    def _phase1_deterministic(self, labels: set) -> Dict[str, str]:
        """
        Phase 1: Deterministic case-insensitive deduplication.

        Returns: {original_label: canonical_label}
        """
        case_groups = defaultdict(list)
        for label in labels:
            key = self._normalize_case_key(label)
            case_groups[key].append(label)

        merges = {}
        for key, variants in case_groups.items():
            if len(variants) > 1:
                # Prefer Title Case, then longest
                canonical = sorted(
                    variants,
                    key=lambda x: (not x[0].isupper(), -len(x))
                )[0]

                for v in variants:
                    if v != canonical:
                        merges[v] = canonical

        return merges

    # =========================================================================
    # Phase 2: ESCO-Anchored
    # =========================================================================

    def _phase2_esco_anchored(
        self,
        labels: set,
        skill_to_esco: Dict[str, str]
    ) -> Dict[str, str]:
        """
        Phase 2: Merge skills that share the same ESCO URI.

        Returns: {original_label: canonical_label}
        """
        esco_to_labels = defaultdict(list)
        for label in labels:
            esco = skill_to_esco.get(label)
            if esco:
                esco_to_labels[esco].append(label)

        merges = {}
        for esco_uri, labels_with_uri in esco_to_labels.items():
            if len(labels_with_uri) > 1:
                canonical = labels_with_uri[0]
                for label in labels_with_uri[1:]:
                    merges[label] = canonical

        return merges

    # =========================================================================
    # Phase 3: LLM Batch
    # =========================================================================

    def _phase3_llm_batch(self, labels: set) -> tuple[Dict[str, str], List[Dict]]:
        """
        Phase 3: LLM-based semantic normalization.

        Returns: (merges_map, group_details)
        """
        if not labels:
            return {}, []

        labels_list = sorted(labels)

        if self.provider == "mock":
            return self._mock_normalization(labels_list)
        elif self.provider == "anthropic":
            return self._anthropic_normalization(labels_list)
        elif self.provider == "openai":
            return self._openai_normalization(labels_list)
        elif self.provider == "ollama":
            return self._ollama_normalization(labels_list)
        else:
            logger.warning(f"Unknown provider {self.provider}, using mock")
            return self._mock_normalization(labels_list)

    def _build_normalization_prompt(self, labels: List[str]) -> str:
        """Build prompt for LLM batch normalization (legacy — mixed pool)."""
        return f"""You are an entity resolution expert. Below is a list of skills and technologies
extracted from resume documents. Some of these refer to the same real-world concept
but are written differently (abbreviations, case variants, alternative names).

TASK: Identify groups of names that refer to the SAME concept.
Be CONSERVATIVE — only group things you are confident are the same.
Leave unique items as singleton groups.

For each group, pick the most formal/complete name as the canonical label.

ENTITY LIST:
{chr(10).join(f'  - "{label}"' for label in labels)}

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

    def _build_skill_tech_prompt(
        self, declared_skills: set, tech_labels: set
    ) -> str:
        """
        Build a type-annotated prompt for the skill+tech pool.

        Annotating which labels are declared skills vs used-in-job technologies
        helps the LLM confidently merge e.g. "ML" [used] ↔ "Machine Learning" [declared]
        and prefer the more formal declared name as canonical.
        """
        items = (
            [f'  - "{l}" [declared skill]' for l in sorted(declared_skills)] +
            [f'  - "{l}" [used in job]' for l in sorted(tech_labels)]
        )
        return f"""You are an entity resolution expert reviewing a resume knowledge graph.
Below are skill/technology labels extracted from resume documents.
Labels marked [declared skill] come from the skills section (curated names).
Labels marked [used in job] come from job descriptions (free-text, may use abbreviations).

TASK: Identify groups that refer to the SAME real-world skill or technology.
Be CONSERVATIVE — only group things you are highly confident are the same concept.
When merging, PREFER the [declared skill] label as canonical (it is more authoritative).
Leave unique items as singleton groups.

ENTITY LIST:
{chr(10).join(items)}

Respond with ONLY valid JSON, no markdown fences, no explanation:
{{
  "groups": [
    {{
      "canonical": "the best/most complete name",
      "members": ["name1", "name2"],
      "reasoning": "brief explanation"
    }}
  ]
}}

Include ALL names — even unique ones should appear as single-member groups.
"""

    def _build_pool_prompt(self, labels: List[str], entity_type: str) -> str:
        """Build a prompt for a homogeneous entity pool (org names, degree names, etc.)."""
        return f"""You are an entity resolution expert reviewing a resume knowledge graph.
Below is a list of {entity_type}s extracted from resume documents.
Some may refer to the same real-world entity written differently
(abbreviations, punctuation variants, alternate official names).

TASK: Identify groups that refer to the SAME real-world {entity_type}.
Be CONSERVATIVE — only group things you are highly confident are the same.
Leave unique items as singleton groups.

ENTITY LIST:
{chr(10).join(f'  - "{label}"' for label in labels)}

Respond with ONLY valid JSON, no markdown fences, no explanation:
{{
  "groups": [
    {{
      "canonical": "the most complete/official name",
      "members": ["name1", "name2"],
      "reasoning": "brief explanation"
    }}
  ]
}}

Include ALL names — even unique ones should appear as single-member groups.
"""

    def _mock_normalization(self, labels: List[str]) -> tuple[Dict[str, str], List[Dict]]:
        """Mock provider: identity mapping (no actual normalization)."""
        return {}, []

    # =========================================================================
    # Phase 3: Type-pool helpers (used by normalize_session_entities)
    # =========================================================================

    def _call_llm(self, prompt: str, max_tokens: int = 2000) -> Optional[str]:
        """
        Call the configured LLM and return raw text. Returns None on failure.
        Centralizes provider dispatch so pool helpers stay DRY.
        """
        if self.provider == "mock":
            return None
        try:
            if self.provider == "anthropic":
                return self.llm_client.generate(prompt, max_tokens=max_tokens)
            elif self.provider == "openai":
                import openai
                client = openai.OpenAI()
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                )
                return response.choices[0].message.content
            elif self.provider == "ollama":
                return self.llm_client.generate(prompt, max_tokens=3000, temperature=0.1)
        except Exception as e:
            logger.error(f"LLM call failed ({self.provider}): {e}")
        return None

    def _phase3_skill_tech_batch(
        self, declared_skills: set, tech_labels: set
    ) -> tuple[Dict[str, str], List[Dict]]:
        """
        Phase 3 for the skill+tech pool.
        Uses a type-annotated prompt so the LLM knows which labels are curated
        skill names vs free-text job description strings.
        """
        if not declared_skills and not tech_labels:
            return {}, []
        if self.provider == "mock":
            return {}, []
        prompt = self._build_skill_tech_prompt(declared_skills, tech_labels)
        raw = self._call_llm(prompt)
        if raw:
            return self._parse_llm_response(raw)
        return {}, []

    def _phase3_labeled_batch(
        self, labels: List[str], entity_type: str
    ) -> tuple[Dict[str, str], List[Dict]]:
        """
        Phase 3 for a homogeneous entity pool (org names, degree names, etc.).
        Uses a type-specific prompt to avoid cross-type confusion.
        """
        if not labels:
            return {}, []
        if self.provider == "mock":
            return {}, []
        prompt = self._build_pool_prompt(labels, entity_type)
        raw = self._call_llm(prompt)
        if raw:
            return self._parse_llm_response(raw)
        return {}, []

    # =========================================================================
    # Phase 3: Per-provider implementations (legacy — used by _phase3_llm_batch)
    # =========================================================================

    def _anthropic_normalization(self, labels: List[str]) -> tuple[Dict[str, str], List[Dict]]:
        """Use Anthropic Claude for normalization."""
        try:
            prompt = self._build_normalization_prompt(labels)
            response = self.llm_client.generate(prompt, max_tokens=2000)
            return self._parse_llm_response(response)
        except Exception as e:
            logger.error(f"Anthropic normalization failed: {e}")
            return self._mock_normalization(labels)

    def _openai_normalization(self, labels: List[str]) -> tuple[Dict[str, str], List[Dict]]:
        """Use OpenAI for normalization."""
        try:
            import openai
            client = openai.OpenAI()
            prompt = self._build_normalization_prompt(labels)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
            )
            raw = response.choices[0].message.content
            return self._parse_llm_response(raw)
        except Exception as e:
            logger.error(f"OpenAI normalization failed: {e}")
            return self._mock_normalization(labels)

    def _ollama_normalization(self, labels: List[str]) -> tuple[Dict[str, str], List[Dict]]:
        """Use Ollama (local LLM) for normalization."""
        try:
            prompt = self._build_normalization_prompt(labels)
            # Use higher max_tokens for Ollama since it's local (no cost)
            raw = self.llm_client.generate(prompt, max_tokens=3000, temperature=0.1)
            return self._parse_llm_response(raw)
        except Exception as e:
            logger.error(f"Ollama normalization failed: {e}")
            logger.warning("Falling back to mock normalization")
            return self._mock_normalization(labels)

    def _parse_llm_response(self, raw: str) -> tuple[Dict[str, str], List[Dict]]:
        """Parse LLM JSON response into merges map and group details."""
        # Strip markdown fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

        try:
            result = json.loads(raw)
            groups = result.get("groups", [])

            merges = {}
            group_details = []

            for group in groups:
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
                            merges[member] = canonical

            return merges, group_details

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.error(f"Raw response: {raw[:300]}")
            return {}, []

    # =========================================================================
    # Final Map and Application
    # =========================================================================

    def _build_final_map(
        self,
        all_labels: set,
        phase1_map: Dict[str, str],
        phase2_map: Dict[str, str],
        phase3_map: Dict[str, str],
    ) -> Dict[str, str]:
        """Chain all phase mappings into final label map."""
        label_map = {}

        # Start with identity
        for label in all_labels:
            label_map[label] = label

        # Apply Phase 1
        for old, new in phase1_map.items():
            label_map[old] = new

        # Apply Phase 2 (on top of Phase 1)
        for old, new in phase2_map.items():
            for k, v in label_map.items():
                if v == old:
                    label_map[k] = new

        # Apply Phase 3 (on top of Phase 1+2)
        for old, new in phase3_map.items():
            for k, v in label_map.items():
                if v == old:
                    label_map[k] = new

        return label_map

    def _apply_normalization(
        self,
        all_entities: List[Dict[str, Any]],
        label_map: Dict[str, str],
        declared_skill_labels: Optional[set] = None,
        verified_labels: Optional[set] = None,
    ) -> List[Dict[str, Any]]:
        """
        Apply label_map to all entities.

        When a skill's label is remapped to a canonical (e.g. "ML" → "Machine Learning"),
        the original label is stored in skill["alt_labels"] so the RDF builder can write
        it as a skos:altLabel triple, keeping variant names discoverable in the graph.

        Entities with user_verified=True are skipped — their labels are authoritative
        and must not be overwritten by normalization.
        """
        normalized = []
        _verified = verified_labels or set()

        for entities in all_entities:
            normalized_doc = {}

            # Normalize person (pass through)
            if "person" in entities:
                normalized_doc["person"] = entities["person"]

            # Normalize skills, tracking alt_labels when the label changes
            normalized_skills = []
            for skill in entities.get("skills", []):
                skill_copy = skill.copy()
                # Skip user-curated entities — their label is authoritative
                if skill_copy.get("user_verified"):
                    normalized_skills.append(skill_copy)
                    continue
                old_label = skill_copy.get("name") or skill_copy.get("label")
                if old_label:
                    decoded = self._url_decode(old_label)
                    new_label = label_map.get(decoded, decoded)
                    if "name" in skill_copy:
                        skill_copy["name"] = new_label
                    if "label" in skill_copy:
                        skill_copy["label"] = new_label
                    # If the label was remapped, preserve the original as an alt_label
                    # so it ends up as skos:altLabel on the canonical Skill node in RDF.
                    if new_label != decoded:
                        alt_labels = list(skill_copy.get("alt_labels", []))
                        if decoded not in alt_labels:
                            alt_labels.append(decoded)
                        skill_copy["alt_labels"] = alt_labels
                normalized_skills.append(skill_copy)
            normalized_doc["skills"] = normalized_skills

            # Normalize jobs (technology lists)
            normalized_jobs = []
            for job in entities.get("jobs", []):
                job_copy = job.copy()
                old_techs = job_copy.get("technologies_used", [])
                new_techs = []
                seen = set()

                for tech in old_techs:
                    decoded = self._url_decode(tech)
                    normalized_tech = label_map.get(decoded, decoded)
                    if normalized_tech not in seen:
                        new_techs.append(normalized_tech)
                        seen.add(normalized_tech)

                job_copy["technologies_used"] = new_techs
                normalized_jobs.append(job_copy)
            normalized_doc["jobs"] = normalized_jobs

            # Normalize organizations
            normalized_orgs = []
            for org in entities.get("organizations", []):
                org_copy = org.copy()
                old_name = org_copy.get("name")
                if old_name:
                    decoded = self._url_decode(old_name)
                    new_name = label_map.get(decoded, decoded)
                    org_copy["name"] = new_name
                normalized_orgs.append(org_copy)
            normalized_doc["organizations"] = normalized_orgs

            # Normalize education (degree names)
            normalized_edu = []
            for edu in entities.get("education", []):
                edu_copy = edu.copy()
                old_degree = edu_copy.get("degree")
                if old_degree:
                    decoded = self._url_decode(old_degree)
                    new_degree = label_map.get(decoded, decoded)
                    edu_copy["degree"] = new_degree
                normalized_edu.append(edu_copy)
            normalized_doc["education"] = normalized_edu

            # Pass through certifications (no normalization needed yet)
            if "certifications" in entities:
                normalized_doc["certifications"] = entities["certifications"]

            normalized.append(normalized_doc)

        return normalized
