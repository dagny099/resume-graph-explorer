# Schema at a Glance

**What this document is:** A plain-language walkthrough of how Resume Explorer
turns a resume into a knowledge graph. Start here before diving into the formal
[SKOS Schema Reference](SKOS_SCHEMA.md).

---

## The Big Picture

Resume Explorer reads a resume (PDF, DOCX, or plain text), extracts structured
information, and builds a **knowledge graph** — a network of **entities** (nodes)
connected by **relationships** (edges).

```
                           ┌─────────────┐
                      ┌────│   Person    │────┐
                      │    └──────┬──────┘    │
                      │           │           │
                 has skill     has job    alumni of
                      │           │           │
                      v           v           v
                 ┌─────────┐ ┌─────────┐ ┌───────────┐
                 │  Skill  │ │   Job   │ │ Education │
                 └────┬────┘ └────┬────┘ └─────┬─────┘
                      │           │             │
                  broader    works at      recognized by
                      │           │             │
                      v           v             v
                 ┌─────────┐ ┌──────────────┐   │
                 │  Skill  │ │ Organization │<──┘
                 │(parent) │ └──────────────┘
                 └─────────┘
```

That's the core. A **Person** sits at the center, connected outward to their
**Jobs**, **Skills**, **Education**, and **Certifications**. Jobs and Education
link further out to **Organizations** (companies, universities). Skills can
form hierarchies (e.g., "Python" is narrower than "Programming Languages").

---

## The 6 Entity Types (Nodes)

Every node in the graph is one of these six types. Each gets a distinct color
and shape in the visualization.

```
  ◇ Person          (Red, diamond)      The resume owner
  ▭ Job             (Teal, box)         A position/role held
  ◯ Skill           (Blue, ellipse)     A skill or competency
  ▭ Education       (Green, box)        A degree or credential
  ◯ Certification   (Yellow, ellipse)   A professional certification
  ▭ Organization    (Orange, box)       A company, university, or issuer
```

### What each entity carries

| Entity | Key Properties | Where It Comes From |
|--------|---------------|---------------------|
| **Person** | name, email, phone, location, summary | Resume header/contact section |
| **Job** | title, start/end dates, location, description, achievements | Work experience section |
| **Skill** | category, proficiency level, years of experience | Skills section + skills mentioned in jobs |
| **Education** | degree type, field of study, GPA, start/end dates | Education section |
| **Certification** | name, issuing org, issue/expiration dates, credential ID/URL | Certifications section |
| **Organization** | name, type (Company/University), industry, location, website | Inferred from jobs & education |

Every entity also carries **provenance metadata**: a confidence score (0.0–1.0),
the source document filename, and a creation timestamp.

---

## The Relationships (Edges)

Edges connect entities. They fall into a few natural groups:

### Person → everything else ("I have / I did")

```
  Person ──has job──────────> Job
  Person ──has skill─────────> Skill
  Person ──alumni of─────────> Education
  Person ──has certification─> Certification
```

### Job → its context ("This job involved...")

```
  Job ──works at──────> Organization    (who employed you)
  Job ──uses skill────> Skill           (skills applied in this role)
  Job ──uses tech─────> Technology*     (technologies used)
```

### Education → its institution

```
  Education ──recognized by──> Organization   (the university/school)
```

### Skill → skill hierarchy (SKOS taxonomy)

```
  Skill ──broader──> Skill    ("Python" → "Programming Languages")
  Skill ──narrower─> Skill    ("Programming Languages" → "Python")
  Skill ──related──> Skill    ("Python" → "Data Science")
```

*\*Technology is stored as a literal string on the edge, not as a separate node,
in the current implementation.*

### Edge visualization

Edges are color-coded by category for visual clarity:

| Category | Color | Width | What it connects |
|----------|-------|-------|------------------|
| **Ownership** | Green | thick | Person → Job, Skill, Certification, Education |
| **Organizational** | Blue | medium | Job/Education → Organization |
| **Usage** | Purple | medium | Job → Skill, Job → Technology |
| **Hierarchical** | Orange | thin | Skill → Skill (SKOS broader/narrower/related) |

---

## How It Maps to Standards

Resume Explorer doesn't invent its own vocabulary from scratch. It leans on
three established standards and extends them where needed:

```
  ┌─────────────────────────────────────────────────────────┐
  │                    Resume Explorer Schema                │
  │                                                         │
  │  ┌───────────────┐  ┌──────────┐  ┌──────────────────┐ │
  │  │  schema.org   │  │   SKOS   │  │      ESCO        │ │
  │  │               │  │          │  │                  │ │
  │  │ Person        │  │ broader  │  │ Skill URIs       │ │
  │  │ Organization  │  │ narrower │  │ Occupation URIs  │ │
  │  │ JobPosting    │  │ related  │  │ Skill categories │ │
  │  │ Education     │  │ prefLabel│  │                  │ │
  │  │ Credential    │  │          │  │                  │ │
  │  └───────────────┘  └──────────┘  └──────────────────┘ │
  │                                                         │
  │  ┌─────────────────────────────────────────────────┐   │
  │  │  re: (custom namespace)                          │   │
  │  │  resumeexplorer.org/ontology#                    │   │
  │  │                                                  │   │
  │  │  hasJob, hasSkill, usedSkill, usedTechnology,   │   │
  │  │  hasCertification, skillCategory,               │   │
  │  │  proficiencyLevel, yearsExperience,             │   │
  │  │  confidence, sourceDocument, isCurrent, ...     │   │
  │  └─────────────────────────────────────────────────┘   │
  └─────────────────────────────────────────────────────────┘
```

| Standard | What it provides | Namespace prefix |
|----------|-----------------|------------------|
| **schema.org** | Entity types (Person, Organization, JobPosting, EducationalOccupationalCredential) and common properties (name, email, title, startDate, etc.) | `schema:` |
| **SKOS** | Concept organization — hierarchies (broader/narrower), labels (prefLabel), and cross-vocabulary linking (exactMatch) | `skos:` |
| **ESCO** | European taxonomy of skills and occupations. Skills are linked to ESCO URIs when a match is found. | `esco:` |
| **RE (custom)** | Resume-specific relationships and properties that don't exist in the above standards | `re:` |

---

## A Concrete Example

Here's what a single resume might produce, rendered as a simplified graph:

```
                              ◇ Barbara Hidalgo-Sotelo
                             /    |        |         \
                          has    has     alumni     has
                          job   skill     of      certification
                          /       |        |           \
                    ▭ Sr. Data  ◯ Python  ▭ PhD       ◯ AWS Solutions
                      Scientist    |      Neuroscience   Architect
                         |       broader      |
                      works at     |     recognized by
                         |         v          |
                    ▭ Acme Corp  ◯ Programming  ▭ UCLA
                                  Languages
```

As RDF triples (Turtle syntax), part of this looks like:

```turtle
resume:person-abc a schema:Person ;
    schema:name "Barbara Hidalgo-Sotelo" ;
    re:hasJob resume:job-xyz ;
    re:hasSkill resume:skill-python .

resume:skill-python a esco:Skill ;
    skos:prefLabel "Python" ;
    skos:broader resume:skill-programming ;
    re:proficiencyLevel "Expert" ;
    re:confidence 0.95 .

resume:job-xyz a schema:JobPosting ;
    schema:title "Sr. Data Scientist" ;
    schema:hiringOrganization resume:org-acme ;
    re:usedSkill resume:skill-python .
```

---

## Validation (SHACL Shapes)

The graph is validated using **SHACL** (Shapes Constraint Language) to catch
structural problems. The project uses a **lenient** validation philosophy:

- **Violations** (errors): Real interoperability breakers — e.g., a Person
  with no `schema:name`, a Job with no `schema:title`, a Skill with no
  `skos:prefLabel`.
- **Warnings** (quality nudges): Things that work but could be better — e.g.,
  missing dates, missing proficiency levels, organizations without
  human-readable labels.

See: `backend/.../graph/shapes/resume.lenient.shapes.ttl`

---

## Key Files

If you want to understand or modify the schema, these are the files to look at,
in priority order:

| File | What it does |
|------|-------------|
| `backend/resume_explorer/graph/vocabularies.py` | **Source of truth.** Defines all namespaces, entity types, relationship types, and ESCO mappings. |
| `backend/resume_explorer/models/*.py` | Entity classes (Person, Job, Skill, etc.) with their properties and `to_rdf()` serialization. |
| `backend/resume_explorer/graph/rdf_graph_builder.py` | Assembles entities into a complete RDF graph with deduplication. |
| `backend/resume_explorer/graph/shapes/resume.lenient.shapes.ttl` | SHACL validation constraints. |
| `backend/resume_explorer/graph/networkx_adapter.py` | Converts RDF to Vis.js visualization JSON (node colors, edge styling). |
| `docs/SKOS_SCHEMA.md` | Formal vocabulary reference (entity properties, relationship types, RDF examples). |
| `docs/EDGE_TYPE_CLASSIFICATION.md` | How edges are grouped and colored for visualization. |

---

## Known Limitations & Caveats

1. **Placeholder ESCO URIs.** Most ESCO skill/occupation URIs in
   `vocabularies.py` are fabricated UUIDs for development purposes (e.g.,
   `c8b1b3e4-92c5-...`). Only the Python skill URI
   (`c3b1499e-77e4-42e8-be6f-676e9f1b7c91`) appears to be a real ESCO
   identifier. In production, these should be resolved against the actual
   ESCO API or taxonomy download.

2. **Defined-but-unused vocabulary terms.** `vocabularies.py` defines several
   relationship types that are never emitted by the graph builder:
   `worksFor`, `employedBy`, `holdsPosition`, `skills` (as REQUIRES_SKILL),
   `hasCredential`, `knowsTechnology`, `duration`. These exist for potential
   future use but are not part of the active schema today. See the
   [Active vs. Defined Relationships](#) section in `SKOS_SCHEMA.md` for
   details.

3. **Technology as literal.** `re:usedTechnology` values are stored as literal
   strings, not as IRI references to a Technology entity — even though
   `EntityType.TECHNOLOGY` is defined. The SHACL shapes flag this as a
   warning.

4. **Entity types without models.** `EntityType.TECHNOLOGY` and
   `EntityType.PROJECT` are defined in vocabularies but have no corresponding
   Python model class or graph builder support.

---

*See also: [SKOS Schema Reference](SKOS_SCHEMA.md) | [Edge Type Classification](EDGE_TYPE_CLASSIFICATION.md)*
