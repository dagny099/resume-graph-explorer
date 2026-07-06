# Graph Analysis Pipeline — Architecture & Roadmap

**"The Digital Twin as a Natural Language Interface to Your Knowledge Graph"**

---

## What This Is

Resume Explorer builds a SKOS-compliant knowledge graph from your resume. That graph contains structural information — connections between roles, skills, and time periods — that flat text chunking completely misses. This pipeline extracts those structural insights and serializes them as natural language documents that a RAG-based "Digital Twin" chatbot can retrieve and narrate.

The result: instead of a Digital Twin that only knows what you wrote in your bio, you get one that can answer structurally-grounded questions like:

- *"What skills are you underselling?"* → answered from a pre-computed claimed-vs-used gap analysis
- *"What connects your different roles?"* → answered from a career topology analysis showing bridge technologies
- *"How has your toolkit changed over time?"* → answered from a chronological tech evolution document

---

## Why This Approach (the design decisions)

### Why pre-compute instead of querying the graph live?

The fastest path to graph-aware answers requires no new infrastructure. The Digital Twin already has a ChromaDB collection and an embedding pipeline. If you convert graph analysis results into well-written natural language documents and add them to that collection, you get graph-aware retrieval for free — same retrieval engine, better content.

This is Phase 1. Phase 2 (described below) adds live graph queries on top, but Phase 1 is independently valuable and ships in 1–2 days.

### Why natural language, not JSON?

ChromaDB embeds text. A JSON object like `{"claimed_not_used": ["SQL", "PowerBI"]}` embeds differently from a sentence like *"SQL and PowerBI are skills Dagny has listed but never documented using in a specific role — they're ungrounded claims."* The second version is semantically close to the queries someone would actually ask.

This is not obvious. The rule: **the text you serialize determines what questions will find it**. Each analysis document is written as a mini-briefing an analyst might write — not a data dump, but an interpretation with semantic hooks for multiple query phrasings. See `backend/tools/graph_analyzer.py` docstring for the full principle.

### Why standalone scripts, not part of the deployed app?

These scripts operate on *exported* data, not live session data. They require LLM API keys the deployed app doesn't need. They produce files for a different downstream system (the Digital Twin). Keeping them in `backend/tools/` means the deployed app stays lean, these tools can evolve independently, and you can re-run them with different parameters without touching the app.

### Why a separate `entity_normalizer.py` before `graph_analyzer.py`?

The graph analysis is only as good as the entity resolution. When Resume Explorer extracts "GA4" from one resume variant and "Google Analytics 4" from another, the gap analysis incorrectly reports these as two different technologies. The normalizer runs three phases — deterministic (URL decoding, case), ESCO-anchored (shared URI = same concept), and LLM batch (semantic aliases) — before analysis, so the structural findings are accurate.

---

## What the Analysis Reveals (concrete example)

Running `graph_analyzer.py` against a real resume export surfaced findings that were invisible on the flat resume:

**Skill Gap (claimed vs. used)**
The resume declared 11 skills, but job history referenced 19 distinct technologies — with only 2 overlapping. Seven declared skills never appeared in any role. Fifteen used technologies weren't in the skill list at all, including an entire cognitive science / human factors toolkit from earlier career stages (eye tracking, GSR, facial expression analysis, Matlab, signal processing) that had been dropped from professional identity.

**Career Topology**
Out of 19 technologies used across 6 roles, only 1 appeared in more than one job: Python. Every other technology was isolated to a single role. This means the career's continuity lives in *how* the person thinks, not *which tools* they use — each career chapter used an entirely different stack. The graph makes this visible; a flat resume obscures it.

**Ghost Nodes (structural integrity)**
Organizations were referenced (org-001 through org-005) but never materialized as entities in the export. Five certifications existed as references but not as full nodes. These were perfect illustrations of why entity resolution matters — and they had a concrete root cause: the RDF export route only serialized person/jobs/skills, dropping education, certifications, and organizations.

**Update (July 2026):** that root cause is fixed. All export/graph/analysis paths now share one graph-building code path (`resume_explorer/graph/session_graph.py`), so exports carry all six entity types. A semantic integrity validator (`resume_explorer/graph/graph_validator.py`, surfaced at `GET /api/sessions/:id/graph/validate`) now detects this class of problem — dangling references, missing labels, entity types lost between extraction and graph — before you trust an export. It's a pragmatic checker, not full SHACL validation.

These aren't hypothetical examples. They were found in a real export in under 30 seconds of runtime. The value: the graph contains structure you didn't know was there until you analyzed it.

---

## The 3-Phase Roadmap

This pipeline is "Avenue 3" — the third major architectural avenue for Resume Explorer, after graph building (Avenue 1) and the interactive visualization (Avenue 2). Each phase is independently demoable.

### Phase 1: Graph → Pre-Computed Insight Documents (DONE)

**Status:** Implemented — accessible both via CLI (`backend/tools/`) and the in-app UI.

**In-app access:** The web app exposes Phase 1 directly through the Analysis Pipeline sidebar panel. Click **▶ Analyze Graph** (Step 1) to run all 6 analyses without leaving the browser, then view results in the **Insights** tab. Click **▶ Generate Narratives** (Step 2) to run synthesis. No CLI or file management required. See `backend/resume_explorer/services/pipeline_service.py` for the in-app wrapper.

**What it does:** Run a battery of 6 structural analyses on the JSON-LD export. Convert each result to a natural language document. Optionally embed into ChromaDB alongside existing Digital Twin content.

**The 6 analyses:**

| Analysis | Output file | Answers |
|----------|-------------|---------|
| Skill Gap | `skill_gap.md` | "What skills am I underselling / hiding?" |
| Career Topology | `career_topology.md` | "What connects my different roles?" |
| Tech Evolution | `tech_evolution.md` | "How has my toolkit changed?" |
| SKOS Hierarchy Map | `hierarchy_map.md` | "How do my skills relate to each other?" |
| ESCO Coverage | `esco_coverage.md` | "How interoperable is my profile?" |
| Role Progression | `role_progression.md` | "What's my career arc?" |

**How to run:** See [`backend/tools/tools-README.md`](../backend/tools/tools-README.md).

**The demo moment:** Someone asks the Digital Twin "What hidden skills does Dagny have?" and it retrieves the pre-computed gap analysis showing the vanished cognitive science toolkit. The answer is grounded in graph structure, not just text similarity.

**Why this is Phase 1 (not Phase 2):** No new infrastructure. No function calling. No query translation. Just better content in the existing RAG pipeline, running against a well-understood system. This gives you a working baseline to compare against when you add live queries in Phase 2.

---

### Phase 2: Live Graph Query Tools for the LLM (PLANNED)

**Status:** Planned. See `New Plans/avenue-3-implementation-plan.jsx` for the detailed spec.

**What it does:** Instead of pre-computing all possible insights, give the LLM a toolkit of graph query functions it can call at runtime. When someone asks a question the pre-computed documents don't fully cover, the LLM decides which function to invoke, gets structured results, and narrates them.

**The key insight:** You don't need NL-to-SPARQL translation. You need a small set of well-designed Python functions that wrap common graph traversals, exposed to the LLM as tools.

**Planned tools (8–12 total):**

```python
find_skills_for_role(role_title: str) → List[Skill]
find_roles_for_skill(skill_name: str) → List[Role]
find_skill_gaps(claimed_vs_used: bool) → GapReport
find_bridge_skills() → List[BridgeSkill]
find_career_timeline() → List[TimelineEntry]
find_skill_hierarchy(skill_name: str) → HierarchyTree
find_similar_roles(role_title: str) → List[SimilarRole]
compute_skill_centrality() → RankedList[Skill]
```

**Architecture:**

```
User: "What skills am I underselling?"
              ↓
Digital Twin (LLM)
  sees available tools → decides to call find_skill_gaps()
              ↓
graph_tools.py
  loads graph from JSON-LD
  runs NetworkX traversal
  returns structured results: {claimed_not_used: [...], used_not_claimed: [...]}
              ↓
Digital Twin (LLM)
  narrates: "Great question — your graph shows 15 technologies you've used
  in roles that aren't in your skill list, including your entire cognitive
  science toolkit from your research years..."
```

**Implementation plan:** `graph_tools.py` module + thin Flask endpoint or direct function calls + system prompt engineering to teach the LLM when and how to use each tool.

**The demo moment:** Someone asks a question the Digital Twin has never seen before. It picks the right graph tool, runs a live query, and narrates a structurally-grounded answer. This is the "wait, show me that again" moment that Phase 1 can't deliver for novel questions.

**Why Phase 2 after Phase 1:** Pre-computed insights answer questions you anticipated. Live tools answer questions you didn't anticipate. Phase 1 gives you a working baseline to validate that the graph content is valuable before investing in the function-calling infrastructure.

---

### Phase 3: Hybrid RAG + Graph Tools + Conversation (NORTH STAR)

**Status:** Planned.

**What it does:** The Digital Twin uses BOTH traditional RAG (for biographical context, project narratives, your voice) AND graph tools (for structural career queries) in the same conversation. The LLM decides which source to consult based on the question.

```
"Tell me about Dagny's philosophy on explainability"
    → RAG retrieval from biosketch

"What skills back that up structurally?"
    → graph tool call (find_skills_for_role + find_career_timeline)

"How does that connect to the Resume Explorer project?"
    → both: graph structure + project README
```

**What makes it the north star:** This is the version where the Digital Twin isn't just a chatbot with your bio — it's a reasoning agent over a professional knowledge graph. It's also the architecture that demonstrates hybrid retrieval combining unstructured and structured knowledge, which is directly relevant to how enterprise AI systems handle knowledge management at scale.

**Key components:**
- Router logic in the system prompt that teaches the LLM when to use RAG vs. graph tools vs. both
- Blended responses that cite both sources
- Conversation memory so multi-turn graph exploration works ("now show me just the healthcare roles" → filters previous result)
- A "show your work" mode where the Twin can explain which tool it used and why

---

## Architecture Spectrum

```
PHASE 1                PHASE 2               PHASE 3
Graph → Text          LLM → Tools           RAG + Graph
Pre-computed          Live queries          Hybrid reasoning
─────────────────────────────────────────────────────────
Simpler / faster      More powerful         Maximum capability
Ships in 1-2 days     Ships in 3-5 days     Polish layer
```

Each phase is independently demoable. Phase 1 is live. Phases 2 and 3 are the roadmap.

---

## File Map

| File | What it is | Purpose |
|------|-----------|---------|
| `backend/tools/entity_normalizer.py` | Offline CLI script | Fix naming inconsistencies before analysis |
| `backend/tools/graph_analyzer.py` | Offline CLI script | 6 structural analyses → 6 markdown docs |
| `backend/tools/narrative_synthesizer.py` | Offline CLI script | LLM synthesis of all 6 analyses |
| `backend/tools/tools-README.md` | Operational guide | How to run the CLI pipeline |
| `backend/resume_explorer/services/pipeline_service.py` | In-app service | Wraps the tools for use within the Flask API + WebSocket progress |
| `backend/resume_explorer/api/routes.py` | API routes | 6 pipeline endpoints (`/pipeline/analyze`, `/pipeline/synthesize`, etc.) |
| `frontend/src/components/AnalysisPipelinePanel.jsx` | React component | Sidebar buttons: Analyze Graph + Generate Narratives |
| `frontend/src/components/InsightsViewer.jsx` | React component | Insights tab: 6 tabbed analysis docs rendered as markdown |
| `frontend/src/components/NarrativeViewer.jsx` | React component | Narratives tab: Conservative + Exploratory with download |
| `docs/GRAPH_ANALYSIS_PIPELINE.md` | This file | Why it was built and where it's going |
| `New Plans/avenue-3-implementation-plan.jsx` | Planning artifact | Detailed Phase 2+3 spec |
| `New Plans/resume-explorer-graph-analysis.jsx` | Planning artifact | The specific findings that motivated Phase 1 |
| `New Plans/phase-1-architecture.jsx` | Planning artifact | Deep dive on NL serialization design |
| `New Plans/langgraph-foundation-guide.jsx` | Planning artifact | LangGraph approach for Phase 2 agent |

---

## Normalization Architecture Note (for developers)

Two separate normalizers exist in this codebase. They solve different problems at different pipeline stages — they are complementary, not redundant.

| | `services/entity_normalizer.py` | `tools/entity_normalizer.py` |
|---|---|---|
| **When** | Live, during upload | Offline, after export |
| **Input** | Python dict objects (pre-RDF) | Exported JSON-LD |
| **Primary job** | Prevent duplicate entity *nodes* across multi-resume uploads | Reconcile Skill prefLabels against `usedTechnology` strings for analysis accuracy |
| **Trigger** | Automatic when session has 2+ documents | User-invoked with explicit provider |
| **altLabel support** | No | Yes — preserves variant names in graph |

The live normalizer handles: `"ML"` + `"Machine Learning"` from two different resumes → one canonical Skill node. The tools normalizer handles: `"ML"` in a job's technology list + `"Machine Learning"` as the declared skill *within a single export* — a cross-namespace inconsistency invisible to the live normalizer.

**Option B is now implemented.** The live normalizer now handles cross-namespace reconciliation (skill prefLabels vs. job `usedTechnology` strings), annotates the LLM prompt with `[declared skill]` / `[used in job]` type hints so it can confidently merge aliases, and writes merged variant names as `skos:altLabel` triples on the canonical Skill node. Phase 1 (deterministic) and Phase 2 (ESCO) now run for all sessions including single-resume; Phase 3 (LLM) runs only when 2+ documents are present OR `NORMALIZE_SINGLE_RESUME=true` is set. This makes the tools normalizer an optional audit step rather than a required pre-processing step for clean skill gap analysis.

See the docstrings in both files for the full architectural rationale.

---

## Graph Cache Freshness (for developers)

`PipelineService` caches the session graph at `sessions/{id}/graph.jsonld` so
that graph analysis and narrative synthesis don't rebuild it on every call. That
file is derived entirely from each completed document's extracted-entities JSON
(`sessions/{id}/extracted/{doc_id}.json`).

`_ensure_jsonld()` reuses the cache **only when it is fresh**: it rebuilds
whenever any completed document's extracted-entities file is newer than
`graph.jsonld` (see `_cache_is_fresh()`). This prevents the stale-analysis bug
where running analysis, then uploading or re-extracting another document in the
same session, would silently reuse the old graph. The `/graph`, `/export`,
`/stats`, and `/graph/validate` routes never cache — they call
`build_session_graph()` fresh — so only the analysis path needed this guard.

Regression coverage: `backend/tests/test_pipeline_cache.py`. Full write-up:
[`HANDOFF_GRAPH_CACHE_FIX.md`](HANDOFF_GRAPH_CACHE_FIX.md).

---

## Relationship to the Interoperability Roadmap

The graph analysis pipeline is complementary to (not a replacement for) the interoperability milestones in [`Roadmap-Interoperability_2025-12-11.md`](Roadmap-Interoperability_2025-12-11.md):

- **Milestone 0 (SHACL validation)** makes ghost nodes (org and certification references that don't resolve) detectable before analysis. The ghost node finding in Phase 1 is a concrete argument for why Milestone 0 matters.
- **Milestone 1 (LOD Enrichment)** would materialize the org nodes that are currently ghost references, enabling queries like "show me all my healthcare-sector roles."
- **Milestone 2 (Semantic Search / Embeddings)** is directly served by Phase 1 — the 6 insight documents *are* the corpus for embedding. The retrieval quality work described in that milestone applies here.

The analysis pipeline runs against whatever the current graph contains. Its findings improve as the graph's data quality improves.
