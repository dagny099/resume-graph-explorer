"""
esco_lookup.py — ESCO REST API client with persistent disk cache

Provides label → {uri, preferred_label, broader_uri, broader_label} lookup
for skills using the ESCO v1.2.1 REST API (no download required, no auth).

Cache: results stored in backend/data/esco/skill_cache.json so repeat
analysis runs are instant. API is only called on first encounter of each
label.

Usage:
    from esco_lookup import ESCOLookup
    esco = ESCOLookup()
    result = esco.lookup("Python")
    # → {"uri": "...", "preferred_label": "Python (computer programming)",
    #     "broader_uri": "...", "broader_label": "computer programming"}
    result = esco.lookup("AWS")
    # → None  (vendor-specific, not in ESCO taxonomy)

Fallback: if the ESCO API is unreachable, returns None silently. The
HierarchyMapAnalyzer treats unmatched skills as "Uncategorized".
"""

import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

ESCO_API_BASE = "https://ec.europa.eu/esco/api"

# Cache lives next to the backend data directory.
# Resolved relative to this file's location so it works regardless of cwd.
_DEFAULT_CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "esco" / "skill_cache.json"


class ESCOLookup:
    """
    ESCO REST API client with persistent disk cache.

    Thread-safety: not thread-safe. For the offline pipeline scripts this
    is fine (single-threaded). Do not share an instance across threads.
    """

    def __init__(self, cache_path: Path = None):
        self._cache_path = Path(cache_path) if cache_path else _DEFAULT_CACHE_PATH
        self._skills: dict = {}    # normalized_label → result dict or None
        self._concepts: dict = {}  # esco_uri → english preferred label
        self._loaded = False

    # ─── Cache I/O ────────────────────────────────────────────────────────────

    def _load(self):
        if self._loaded:
            return
        self._loaded = True
        if not self._cache_path.exists():
            return
        try:
            with open(self._cache_path) as f:
                data = json.load(f)
            self._skills = data.get("skills", {})
            self._concepts = data.get("concepts", {})
        except Exception:
            pass  # corrupt cache → start fresh

    def _save(self):
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._cache_path, "w") as f:
            json.dump({"skills": self._skills, "concepts": self._concepts}, f, indent=2)

    # ─── HTTP helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _fetch(url: str) -> dict:
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "ResumeExplorer/1.0 (+https://github.com/dagny099/resume-graph-explorer)",
            },
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read())

    # ─── Concept label resolution ──────────────────────────────────────────────

    def _resolve_concept(self, uri: str) -> str | None:
        """
        Return English preferredLabel for an ESCO concept URI.

        Works for both skill URIs (resource/skill) and ISCED-F concept URIs.
        Cached to avoid repeat lookups for commonly shared broader concepts.
        """
        if uri in self._concepts:
            return self._concepts[uri]
        # Try skill endpoint first, then concept endpoint (for ISCED-F URIs)
        for endpoint in ("resource/skill", "resource/concept"):
            try:
                params = urllib.parse.urlencode({"uri": uri, "language": "en"})
                data = self._fetch(f"{ESCO_API_BASE}/{endpoint}?{params}")
                labels = data.get("preferredLabel", {})
                label = labels.get("en") or labels.get("en-us")
                if label:
                    self._concepts[uri] = label
                    return label
            except Exception:
                continue
        self._concepts[uri] = None
        return None

    # ─── API search ───────────────────────────────────────────────────────────

    @staticmethod
    def _match_score(label_lower: str, title: str) -> int:
        """
        Return a match quality score (higher = better).
        0 = no match (reject).

        Scoring:
          3 — hit title starts with label (e.g. "Python" → "Python (computer programming)")
          2 — label is a substring of hit title
          1 — first word of label matches first word of hit title
          0 — no match
        """
        if not label_lower or len(label_lower) < 2:
            return 0
        if title.startswith(label_lower):
            return 3
        if label_lower in title:
            return 2
        label_words = label_lower.split()
        title_words = title.split()
        if label_words and title_words and label_words[0] == title_words[0]:
            return 1
        return 0

    def _search(self, label: str) -> dict | None:
        """
        Query ESCO /search for the best-matching skill.

        Broader concept resolution strategy:
          1. Use broaderSkill[0] if available → most specific grouping
          2. Fall back to broaderHierarchyConcept[0] → ESCO pillar-level grouping
          3. If neither → matched skill has no broader context; treat as unmatched
             (grouping by an overly-generic category adds noise, not value)

        Returns {uri, preferred_label, broader_uri, broader_label} or None.
        """
        try:
            params = urllib.parse.urlencode({
                "text": label,
                "type": "skill",
                "language": "en",
                "limit": 5,
                "full": "false",
            })
            data = self._fetch(f"{ESCO_API_BASE}/search?{params}")
            results = data.get("_embedded", {}).get("results", [])
            if not results:
                return None

            label_lower = label.lower()

            # Pick best-scoring hit
            best = None
            best_score = 0
            for hit in results:
                title = hit.get("title", "").lower()
                score = self._match_score(label_lower, title)
                if score > best_score:
                    best = hit
                    best_score = score

            if not best or best_score == 0:
                return None

            skill_uri = best.get("uri")

            # Broader concept: prefer direct parent, fall back to hierarchy pillar
            broader_uri = None
            broader_label = None

            direct_broader = best.get("broaderSkill", [])
            if direct_broader:
                broader_uri = direct_broader[0]
                broader_label = self._resolve_concept(broader_uri)
            else:
                # Fall back to ESCO hierarchy concept (pillar-level grouping)
                hier = best.get("broaderHierarchyConcept", [])
                if hier:
                    broader_uri = hier[0]
                    broader_label = self._resolve_concept(broader_uri)

            preferred_label = best.get("title", label)

            # Filter out circular/unhelpful broader labels.
            # A broader label is circular when it shares most of its words with
            # the search label — indicating ESCO just wrapped the same concept
            # in a verb phrase (e.g. "data analysis" → "perform data analysis").
            # We compare against the search label (not preferred_label, which
            # may legitimately embed the broader category in parentheses).
            if broader_label:
                bl_words = set(broader_label.lower().split())
                sl_words = set(label.lower().split())
                if bl_words and sl_words:
                    overlap_ratio = len(bl_words & sl_words) / max(len(bl_words), len(sl_words))
                    if overlap_ratio >= 0.6:
                        broader_label = None
                        broader_uri = None

            return {
                "uri": skill_uri,
                "preferred_label": preferred_label,
                "broader_uri": broader_uri,
                "broader_label": broader_label,
            }
        except Exception:
            return None

    # ─── Public API ───────────────────────────────────────────────────────────

    @staticmethod
    def _key(label: str) -> str:
        return label.lower().strip()

    def lookup(self, label: str) -> dict | None:
        """
        Look up a single skill label.

        Returns dict with keys {uri, preferred_label, broader_uri, broader_label},
        or None if no ESCO match was found (network errors also return None).
        Results are cached to disk after first lookup.
        """
        self._load()
        key = self._key(label)
        if key in self._skills:
            return self._skills[key]
        result = self._search(label)
        self._skills[key] = result
        self._save()
        return result

    def lookup_batch(self, labels: list, verbose: bool = False) -> dict:
        """
        Look up multiple skill labels.

        Returns {label: result_or_None}.
        Cache hits are free; uncached labels are queried with 100ms delay
        between calls to be polite to the ESCO API.
        """
        self._load()
        results = {}
        dirty = False
        for label in labels:
            if not label:
                results[label] = None
                continue
            key = self._key(label)
            if key in self._skills:
                results[label] = self._skills[key]
            else:
                if verbose:
                    print(f"  ESCO: {label!r} ...", end=" ", flush=True)
                result = self._search(label)
                if verbose:
                    cat = result.get("broader_label") if result else None
                    print(cat or "(no match)")
                self._skills[key] = result
                results[label] = result
                dirty = True
                time.sleep(0.1)
        if dirty:
            self._save()
        return results

    def cache_stats(self) -> dict:
        """Return cache hit statistics (useful for debugging)."""
        self._load()
        matched = sum(1 for v in self._skills.values() if v is not None)
        return {
            "total_cached": len(self._skills),
            "matched": matched,
            "unmatched": len(self._skills) - matched,
            "concept_labels_cached": len(self._concepts),
            "cache_path": str(self._cache_path),
        }
