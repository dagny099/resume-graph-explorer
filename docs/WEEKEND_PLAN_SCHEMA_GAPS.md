# Weekend Plan: Close the Schema Documentation Gaps

**Estimated total time: 8–10 hours of focused work**
**Goal:** Make the docs match the code, replace placeholder ESCO URIs with real
ones, and add Technology + Project model classes so the vocabulary definitions
aren't dangling.

---

## Pre-flight Checklist

- [ ] Pull latest from `main` and merge into your working branch
- [ ] Confirm dev environment works: `cd backend && pip install -e ".[dev]"` (or equivalent)
- [ ] Run existing tests to establish baseline: `pytest backend/tests/`
- [ ] Skim the new [Schema at a Glance](SCHEMA_AT_A_GLANCE.md) doc to orient yourself

---

## Task 1: Replace Placeholder ESCO URIs with Real Ones
**~2–3 hours** | Priority: HIGH

The `ESCO_SKILLS` and `ESCO_OCCUPATIONS` dicts in `vocabularies.py` contain
fabricated UUIDs. This task replaces them with real URIs from the ESCO taxonomy.

### Background & Resources

- **ESCO Service Platform (search UI):**
  https://esco.ec.europa.eu/en/classification/skill_main
  Use this to manually search and verify skill/occupation URIs.

- **ESCO REST API docs:**
  https://esco.ec.europa.eu/en/use-esco/developer-resources
  The API lets you search programmatically. Key endpoints:
  - Search skills: `GET https://ec.europa.eu/esco/api/search?text=python&type=skill&language=en`
  - Search occupations: `GET https://ec.europa.eu/esco/api/search?text=data+scientist&type=occupation&language=en`
  - Get concept by URI: `GET https://ec.europa.eu/esco/api/resource/skill?uri=<full_uri>`

- **ESCO bulk download (CSV/JSONLD):**
  https://esco.ec.europa.eu/en/use-esco/download
  If you prefer offline lookup, download the full classification (~200MB).
  The skills CSV has columns: `conceptUri`, `preferredLabel`, `description`.

### Step-by-Step

- [ ] **1a.** Open the ESCO search UI or API. For each skill in `ESCO_SKILLS`,
  search by name and record the real concept URI. The skills to look up:

  | Key in code | Search term | Real URI |
  |-------------|------------|----------|
  | `python` | "Python (computer programming)" | (already `c3b1499e...` — verify) |
  | `javascript` | "JavaScript (computer programming)" | |
  | `java` | "Java (computer programming)" | |
  | `sql` | "SQL" | |
  | `r` | "R (programming language)" | |
  | `machine_learning` | "machine learning" | |
  | `data_analysis` | "data analysis" | |
  | `statistical_analysis` | "statistical analysis" | |
  | `data_visualization` | "data visualisation" (note: ESCO uses British spelling) | |
  | `aws` | "Amazon Web Services" | |
  | `azure` | "Microsoft Azure" | |
  | `docker` | "Docker" | |
  | `kubernetes` | "Kubernetes" | |
  | `leadership` | "show leadership" OR "lead others" | |
  | `communication` | "communicate" OR "communication" | |
  | `problem_solving` | "solve problems" OR "problem solving" | |
  | `teamwork` | "work in teams" OR "teamwork" | |

  **Tip:** ESCO skill names are often verb phrases ("use Python", "apply
  machine learning") rather than nouns. You may need to try a few search
  terms. The URI will look like:
  `http://data.europa.eu/esco/skill/<real-uuid>`

- [ ] **1b.** Look up the 5 occupations in `ESCO_OCCUPATIONS`:

  | Key in code | Search term |
  |-------------|------------|
  | `data_scientist` | "data scientist" |
  | `software_engineer` | "software developer" (ESCO's preferred term) |
  | `data_analyst` | "data analyst" |
  | `machine_learning_engineer` | "machine learning engineer" |
  | `research_scientist` | "research scientist" |

  Occupation URIs look like:
  `http://data.europa.eu/esco/occupation/<real-uuid>`

- [ ] **1c.** Update `backend/resume_explorer/graph/vocabularies.py`:
  - Replace every fabricated UUID in `ESCO_SKILLS` with the real URI
  - Replace every fabricated UUID in `ESCO_OCCUPATIONS` with the real URI
  - Add a comment block at the top of each dict noting the date verified
    and the ESCO version (e.g., "ESCO v1.2, verified March 2026")

- [ ] **1d.** Update documentation:
  - `docs/SKOS_SCHEMA.md`: Remove the "Caveat: Placeholder URIs" callout,
    or change it to note the ESCO version and verification date
  - `docs/SCHEMA_AT_A_GLANCE.md`: Update the "Known Limitations" section —
    remove item #1 about placeholder URIs

- [ ] **1e.** Run tests: `pytest backend/tests/test_models.py -v`
  (Skills auto-link to ESCO URIs on init — make sure this still works)

### How to verify you're done
- Every URI in `ESCO_SKILLS` and `ESCO_OCCUPATIONS` should resolve when you
  visit it in a browser (e.g., paste into
  `https://ec.europa.eu/esco/api/resource/skill?uri=<uri>&language=en`)
- No "placeholder" warnings remain in the docs

---

## Task 2: Document Defined-but-Unused Vocabulary Terms
**~45 minutes** | Priority: MEDIUM

You decided to keep the unused terms (`worksFor`, `employedBy`, etc.) for
future use. This task ensures code and docs are explicit about their status.

### Step-by-Step

- [ ] **2a.** Add inline comments in `vocabularies.py` `RelationType` class.
  For each unused term, add a comment like:
  ```python
  # Defined for future use — not currently emitted by the graph builder
  WORKS_AT = SCHEMA.worksFor
  ```

  The terms to annotate:
  - `WORKS_AT` (worksFor)
  - `EMPLOYED_BY` (employedBy)
  - `HOLDS_POSITION` (holdsPosition)
  - `REQUIRES_SKILL` (schema:skills)
  - `HAS_DEGREE` (hasCredential)
  - `KNOWS_TECHNOLOGY` (knowsTechnology)
  - `DURATION` (schema:duration)

- [ ] **2b.** Similarly annotate `EntityType` for types without models:
  ```python
  # Defined — model class added in Task 3 below (or note if still pending)
  TECHNOLOGY = RE.Technology
  PROJECT = RE.Project
  ```
  *(Update this comment after Task 3 is done.)*

- [ ] **2c.** Verify `docs/SKOS_SCHEMA.md` — the "Active vs. Defined" markers
  from the earlier commit should already be correct. Do a quick read-through
  to confirm nothing was missed.

### How to verify you're done
- `grep -n "Defined" backend/resume_explorer/graph/vocabularies.py` shows
  comments on all 7 unused RelationType terms and 2 EntityType terms

---

## Task 3: Create Technology and Project Model Classes
**~3–4 hours** | Priority: MEDIUM-HIGH

`EntityType.TECHNOLOGY` and `EntityType.PROJECT` exist in the vocabulary but
have no Python model class, no graph builder support, and no SHACL shapes.

### Step-by-Step

#### 3A: Technology Model

- [ ] **3a-i.** Create `backend/resume_explorer/models/technology.py`

  Follow the pattern of the other models. Suggested properties:
  ```
  Technology(SKOSEntity):
      name: str              # e.g., "Docker", "PostgreSQL"
      category: str          # e.g., "DevOps", "Database", "Framework"
      version: str           # optional, e.g., "3.11" for Python
      url: str               # optional, official docs/homepage URL
  ```

  Implement `to_rdf()` following the same pattern as `Skill`:
  - `RDF.type` → `EntityType.TECHNOLOGY`
  - `schema:name` → name
  - `RE.technologyCategory` → category (new custom property)
  - `schema:version` → version
  - `schema:url` → url

  Implement `to_dict()` following the same pattern.

- [ ] **3a-ii.** Update `rdf_graph_builder.py`:
  - Add `add_technology()` method with deduplication by normalized name
    (same pattern as `add_skill()`)
  - Add `_tech_cache` and `_tech_id_to_uri` dicts to `__init__`
  - Update `add_job()` to emit `re:usedTechnology` as IRI references
    to Technology entities instead of literal strings
  - Add Technology to `build_from_entities()` signature and processing
    (add technologies before jobs, like skills)

- [ ] **3a-iii.** Update `networkx_adapter.py`:
  - Add `'technology'` to `ENTITY_COLORS` (suggest `'#B39DDB'` — light purple)
  - Add `'technology'` to `ENTITY_SHAPES` (suggest `'triangle'`)
  - Add `EntityType.TECHNOLOGY: 'technology'` to `_get_entity_type()` type_map

#### 3B: Project Model

- [ ] **3b-i.** Create `backend/resume_explorer/models/project.py`

  Suggested properties:
  ```
  Project(SKOSEntity):
      name: str              # Project name
      description: str       # What the project does
      url: str               # optional, e.g., GitHub URL
      start_date: date       # optional
      end_date: date         # optional
      skills_used: List[str] # Skill entity IDs
      technologies_used: List[str]  # Technology entity IDs
  ```

  Implement `to_rdf()`:
  - `RDF.type` → `EntityType.PROJECT`
  - `schema:name` → name
  - `schema:description` → description
  - `schema:url` → url
  - `schema:startDate` → start_date
  - `schema:endDate` → end_date
  - `RE.usedSkill` → each skill (IRI)
  - `RE.usedTechnology` → each technology (IRI)

- [ ] **3b-ii.** Add `add_project()` to `rdf_graph_builder.py` with
  deduplication by name. Add to `build_from_entities()`.

- [ ] **3b-iii.** Update `networkx_adapter.py`:
  - Add `'project'` to `ENTITY_COLORS` (suggest `'#CE93D8'` — medium purple)
  - Add `'project'` to `ENTITY_SHAPES` (suggest `'box'`)
  - Add `EntityType.PROJECT: 'project'` to type_map

#### 3C: Wire Everything Up

- [ ] **3c-i.** Update `backend/resume_explorer/models/__init__.py`:
  ```python
  from .technology import Technology
  from .project import Project
  # Add to __all__
  ```

- [ ] **3c-ii.** Update the `TYPE_CHECKING` imports in `rdf_graph_builder.py`:
  ```python
  from ..models import Person, Job, Skill, Education, Certification, Organization, Technology, Project
  ```

- [ ] **3c-iii.** Add new relationship types to `vocabularies.py` if needed:
  - `RE.hasProject` (Person → Project) — add to `RelationType`
  - `RE.technologyCategory` — add to `RelationType` or as standalone
  - Consider adding `RE.usedInProject` (Job → Project) if relevant

- [ ] **3c-iv.** Add SHACL shapes for Technology and Project to
  `resume.lenient.shapes.ttl`:
  ```turtle
  re:TechnologyShape
    a sh:NodeShape ;
    sh:targetClass re:Technology ;
    sh:property [
      sh:path schema:name ;
      sh:minCount 1 ;
      sh:datatype xsd:string ;
      sh:message "Technology should have schema:name (string)." ;
    ] .

  re:ProjectShape
    a sh:NodeShape ;
    sh:targetClass re:Project ;
    sh:property [
      sh:path schema:name ;
      sh:minCount 1 ;
      sh:datatype xsd:string ;
      sh:message "Project should have schema:name (string)." ;
    ] .
  ```

#### 3D: Tests

- [ ] **3d-i.** Add tests to `backend/tests/test_models.py`:
  - Test Technology creation, to_rdf(), to_dict()
  - Test Project creation, to_rdf(), to_dict()

- [ ] **3d-ii.** Add tests to `backend/tests/test_graph.py`:
  - Test `add_technology()` and deduplication
  - Test `add_project()` and deduplication
  - Test that `add_job()` now emits `usedTechnology` as IRIs

- [ ] **3d-iii.** Run full test suite: `pytest backend/tests/ -v`

### How to verify you're done
- `python -c "from resume_explorer.models import Technology, Project; print('OK')"` works
- Tests pass
- `EntityType.TECHNOLOGY` and `EntityType.PROJECT` are no longer "orphaned"

---

## Task 4: Update All Documentation to Reflect Changes
**~1–1.5 hours** | Priority: HIGH (do this last)

### Step-by-Step

- [ ] **4a.** Update `docs/SCHEMA_AT_A_GLANCE.md`:
  - Add Technology and Project to the "6 Entity Types" section (now 8)
  - Update the entity table with their properties
  - Add any new relationships (hasProject, etc.) to the relationships section
  - Update the ASCII diagrams if the new entities change the graph shape
  - Update "Known Limitations" — remove resolved items, note any new caveats
  - Update the Big Picture ASCII art to show Technology as a node connected
    to Job (instead of "stored as literal string")

- [ ] **4b.** Update `docs/SKOS_SCHEMA.md`:
  - Add Technology entity section under "Entity Types"
  - Add Project entity section under "Entity Types"
  - Add any new relationship types (hasProject, technologyCategory)
  - Mark `re:usedTechnology` as now emitting IRIs (if Task 3 changed this)
  - Remove/update the placeholder ESCO URI caveat (if Task 1 is done)
  - Bump version to 1.2

- [ ] **4c.** Update `docs/EDGE_TYPE_CLASSIFICATION.md`:
  - If new edge types were introduced (e.g., hasProject), add them to the
    classification and note which bucket they fall into

- [ ] **4d.** Update `vocabularies.py` `EntityType` comments:
  - Remove "Defined — no model class" annotations added in Task 2

- [ ] **4e.** Final review: read through all three docs start-to-finish.
  Check for:
  - Broken cross-references
  - Stale "placeholder" or "defined-only" notes
  - Entity/relationship counts that no longer match

### How to verify you're done
- Every entity type in `vocabularies.py` has: a model class, graph builder
  support, a SHACL shape, and a docs section
- Every "Active" relationship in `SKOS_SCHEMA.md` is actually emitted by
  `rdf_graph_builder.py`
- No "placeholder" warnings remain unless they're genuinely still placeholders
- A fresh reader of Schema at a Glance can understand the schema without
  needing to read code

---

## Suggested Order of Operations

```
Saturday morning:   Task 1 (ESCO URIs) — independent, needs web access
Saturday afternoon: Task 2 (vocab annotations) — quick win
Sunday morning:     Task 3 (Technology + Project models) — biggest task
Sunday afternoon:   Task 4 (docs update) — ties everything together
```

Tasks 1 and 2 are independent and can be done in either order.
Task 3 should come before Task 4 since the docs update reflects code changes.

---

## Quick Reference: Files You'll Touch

| File | Tasks |
|------|-------|
| `backend/resume_explorer/graph/vocabularies.py` | 1c, 2a, 2b, 3c-iii |
| `backend/resume_explorer/models/technology.py` | 3a-i (new) |
| `backend/resume_explorer/models/project.py` | 3b-i (new) |
| `backend/resume_explorer/models/__init__.py` | 3c-i |
| `backend/resume_explorer/graph/rdf_graph_builder.py` | 3a-ii, 3b-ii, 3c-ii |
| `backend/resume_explorer/graph/networkx_adapter.py` | 3a-iii, 3b-iii |
| `backend/resume_explorer/graph/shapes/resume.lenient.shapes.ttl` | 3c-iv |
| `backend/tests/test_models.py` | 3d-i |
| `backend/tests/test_graph.py` | 3d-ii |
| `docs/SCHEMA_AT_A_GLANCE.md` | 1d, 4a |
| `docs/SKOS_SCHEMA.md` | 1d, 2c, 4b |
| `docs/EDGE_TYPE_CLASSIFICATION.md` | 4c |
