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
        all_entities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Normalize entities from multiple documents in a session.

        Args:
            all_entities: List of entity dicts from all documents in session
                Each dict should have: {person, jobs, skills, education, etc.}

        Returns:
            {
                "normalized_entities": List of normalized entity dicts,
                "label_map": {original: canonical} mapping,
                "report": {statistics and decisions}
            }
        """
        logger.info(f"Starting entity normalization with {self.provider} provider")

        # Extract all labels from all documents
        skill_labels = set()
        tech_labels = set()
        org_labels = set()
        degree_labels = set()
        skill_to_esco = {}  # skill_label -> esco_uri

        for entities in all_entities:
            # Collect skill labels
            for skill in entities.get("skills", []):
                label = skill.get("name") or skill.get("label")
                if label:
                    decoded_label = self._url_decode(label)
                    skill_labels.add(decoded_label)

                    # Track ESCO mappings
                    esco = skill.get("esco_uri")
                    if esco:
                        skill_to_esco[decoded_label] = esco

            # Collect technology labels from jobs
            for job in entities.get("jobs", []):
                for tech in job.get("technologies_used", []):
                    decoded = self._url_decode(tech)
                    tech_labels.add(decoded)

            # Collect organization labels
            for org in entities.get("organizations", []):
                name = org.get("name")
                if name:
                    decoded = self._url_decode(name)
                    org_labels.add(decoded)

            # Collect degree labels from education
            for edu in entities.get("education", []):
                degree = edu.get("degree")
                if degree:
                    decoded = self._url_decode(degree)
                    degree_labels.add(decoded)

        all_labels = skill_labels | tech_labels | org_labels | degree_labels
        logger.info(
            f"Found {len(skill_labels)} skill labels, "
            f"{len(tech_labels)} technology labels, "
            f"{len(org_labels)} organization labels, "
            f"{len(degree_labels)} degree labels "
            f"({len(all_labels)} unique total)"
        )

        # Phase 1: Deterministic normalization
        phase1_map = self._phase1_deterministic(all_labels)
        logger.info(f"Phase 1 (deterministic): {len(phase1_map)} merges")

        # Apply Phase 1
        remaining_labels = set()
        for label in all_labels:
            remaining_labels.add(phase1_map.get(label, label))

        # Phase 2: ESCO-anchored merge
        phase2_map = self._phase2_esco_anchored(remaining_labels, skill_to_esco)
        logger.info(f"Phase 2 (ESCO-anchored): {len(phase2_map)} merges")

        # Apply Phase 2
        for old, new in phase2_map.items():
            remaining_labels.discard(old)

        # Phase 3: LLM batch normalization
        phase3_map, groups = self._phase3_llm_batch(remaining_labels)
        logger.info(f"Phase 3 (LLM batch): {len(phase3_map)} merges")

        # Build final label map (chain all phases)
        label_map = self._build_final_map(all_labels, phase1_map, phase2_map, phase3_map)

        # Apply normalization to entities
        normalized_entities = self._apply_normalization(all_entities, label_map)

        # Build report
        report = {
            "provider": self.provider,
            "phases": {
                "deterministic": {"merges": len(phase1_map)},
                "esco_anchored": {"merges": len(phase2_map)},
                "llm_batch": {"merges": len(phase3_map), "groups": groups},
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
        """Build prompt for LLM batch normalization."""
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

    def _mock_normalization(self, labels: List[str]) -> tuple[Dict[str, str], List[Dict]]:
        """Mock provider: identity mapping (no actual normalization)."""
        return {}, []

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
        label_map: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Apply label_map to all entities."""
        normalized = []

        for entities in all_entities:
            normalized_doc = {}

            # Normalize person (pass through)
            if "person" in entities:
                normalized_doc["person"] = entities["person"]

            # Normalize skills
            normalized_skills = []
            for skill in entities.get("skills", []):
                skill_copy = skill.copy()
                old_label = skill_copy.get("name") or skill_copy.get("label")
                if old_label:
                    decoded = self._url_decode(old_label)
                    new_label = label_map.get(decoded, decoded)
                    if "name" in skill_copy:
                        skill_copy["name"] = new_label
                    if "label" in skill_copy:
                        skill_copy["label"] = new_label
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
