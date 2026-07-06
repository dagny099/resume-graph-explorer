# Positioning: Resume Graph Explorer

*Two positioning deliverables — a technical brief and a plain-English portfolio narrative — for presenting Resume Graph Explorer to technical and public audiences.*

**Repo:** [github.com/dagny099/resume-graph-explorer](https://github.com/dagny099/resume-graph-explorer)

---

# Deliverable 1 — Technical Positioning Brief

**Audience:** AI engineers, data/knowledge architects, semantic web practitioners, technical hiring managers.

## 1. One-sentence technical description

> **Resume Graph Explorer converts resume documents into SKOS/schema.org-aligned RDF knowledge graphs via LLM extraction, then validates, visualizes, and structurally analyzes those graphs — producing both standards-compliant exports and natural-language insight documents designed for graph-aware RAG and Digital Twin memory.**

Shorter variant for constrained contexts:

> **An LLM-to-RDF pipeline that turns resumes into inspectable, standards-aligned knowledge graphs — and then asks the graph questions a resume can't answer.**

## 2. What problem it addresses

**Flat resumes hide structure.** A resume is a linear, self-authored narrative optimized for skimming. The relationships that actually matter — which skills are *evidenced* by which roles, which capabilities bridge career chapters, what has quietly dropped out of the story — are implicit at best.

**Ordinary resume parsers stop at field extraction.** ATS-style parsers map text to a fixed schema (name, title, dates) and discard the connective tissue. The output is a database row, not a knowledge structure. You can't ask a database row "what connects the first half of this career to the second half?"

**Text-only RAG inherits the flatness.** The default pattern for making documents "AI-ready" is: chunk the text, embed the chunks, retrieve by similarity. That works for lookup questions, but it can't answer structural questions — *claimed vs. evidenced skills*, *skill co-occurrence across roles*, *identity drift over time* — because the structure was never made explicit. Retrieval over chunks of a biography returns fragments of the story, not its shape.

Resume Graph Explorer treats the resume as a small, tractable instance of a much larger problem: **turning messy professional self-description into explicit, queryable, semantically grounded knowledge** — and doing it in a way you can inspect, validate, and evaluate.

## 3. What the system does

The pipeline, end to end:

```
resume upload (PDF / DOCX / TXT / MD)
  → text extraction (PyMuPDF primary, pdfplumber fallback)
  → LLM entity extraction (Claude / OpenAI / Ollama, provider-agnostic,
    with real-time WebSocket progress)
  → entity normalization (3-phase: deterministic → ESCO-anchored → LLM batch;
    merged aliases preserved as skos:altLabel)
  → RDF graph construction (single shared builder path; rdflib)
  → interactive visualization (React + Vis.js)
  → RDF export (Turtle, RDF/XML, JSON-LD — same complete content as the graph view)
  → semantic integrity validation (dangling refs, missing labels,
    near-duplicate skills, lost entity types)
  → structural graph analysis (6 analyses: skill gap, career topology,
    technology evolution, SKOS hierarchy, ESCO interoperability, role progression)
  → narrative synthesis (LLM cross-references the analyses into
    career-insight documents)
  → downstream use: embed insight documents as Digital Twin / RAG memory
```

Architecture notes that matter to a technical reader:

- **One graph builder path.** Export, visualization, stats, and analysis all consume the same graph construction code — so the RDF export is guaranteed to contain the same semantic content the user sees. No "the export is a lossy side product" problem.
- **Normalization is layered, not monolithic.** Dedup caches in the graph builder (case-insensitive skill labels, fuzzy org names, composite keys for jobs/education) act as first defense; a 3-phase normalizer handles the rest, and merged variants survive as `skos:altLabel` rather than being silently discarded.
- **ESCO alignment happens at analysis time** via the ESCO REST API with local caching — no taxonomy downloads, no auth. Roughly 50–60% of skills match; vendor-specific tools (AWS, Kubernetes) correctly return no match, which is a property of ESCO's scope, not a bug.
- **Session/document management** with file-based persistence supports multi-document sessions, with single-resume sessions as the recommended, best-validated path.

## 4. Why the graph matters

The RDF/SKOS/schema.org/ESCO stack isn't ornamental — each standard is doing a specific job:

- **Interoperability.** SKOS concepts, schema.org types (Person, Organization, JobPosting…), and ESCO skill URIs mean the output can be consumed by any RDF-aware tool, merged with other graphs, or queried with SPARQL — without a bespoke schema negotiation. The graph outlives the app that made it.
- **Inspectability.** Every extracted claim becomes a triple you can read. When the LLM gets something wrong, you can see *exactly* which assertion is wrong and where it came from — unlike an embedding, which fails opaquely.
- **Graph-aware retrieval.** The post-export analyses are structural queries over the graph — bridge skills, claimed-vs-evidenced gaps, chronological toolkit shifts — written out as natural-language documents. A RAG system retrieving those documents is retrieving *conclusions grounded in structure*, not fragments of prose.
- **Evidence structure.** The graph distinguishes a skill that is *listed* from a skill that is *attached to a job via usedTechnology*. That claimed-vs-evidenced distinction is the single most useful thing a graph representation adds over the source text, and it's invisible to a text chunker.
- **Entity relationships as first-class data.** Organizations, roles, skills, education, and certifications are linked entities with typed edges, not co-occurring strings.
- **Evaluation and validation as design commitments.** A validation endpoint checks graph integrity (errors vs. warnings, honestly scoped as "pragmatic checks, not SHACL"). An evaluation harness compares extraction output to gold labels with per-entity-type precision/recall/F1. Both are early, and both exist because an extraction pipeline you can't measure is a demo, not a system.

## 5. What makes it technically interesting

- **Semantic web ∘ LLM extraction, taken seriously on both sides.** Most LLM-extraction projects invent an ad-hoc JSON schema; most semantic web projects predate LLMs. This one uses LLMs for what they're good at (reading messy human text) and standards for what they're good at (making the result durable, mergeable, and queryable).
- **RDF export as product, not side effect.** The export is the point — validated, complete, and identical in content to what the UI shows, because everything shares one builder.
- **Graph integrity validation.** A dedicated endpoint that treats the graph as something that can be *wrong* — dangling references, label-less entities, near-duplicate skills that slipped past normalization — and reports it, separating structural errors from suspicious-but-legitimate warnings.
- **An evaluation harness for extraction quality.** Deterministic, offline, no API keys: fixtures, gold labels, and a comparator. It's a scaffold, not a benchmark — but it makes extraction quality a measurable property instead of a vibe.
- **Natural-language insight documents generated *from graph structure*.** The narrative synthesizer doesn't summarize the resume; it cross-references six structural analyses. This is a working example of the "graph → prose → embedding" pattern for giving RAG systems structured memory.
- **A knowledge-graph-to-RAG bridge you can actually run.** The full loop — extraction, normalization, validation, analysis, synthesis, embedding-ready output — exists in one repo at a scale a single reviewer can audit.
- **Enterprise knowledge-architecture patterns at portfolio scale.** Entity resolution, taxonomy alignment, canonical-label governance with alias preservation, validation gates, extraction evaluation: the same problems an enterprise knowledge platform faces, demonstrated end to end on a domain everyone understands.

## 6. What it does not claim

Stated plainly, because credibility is the product:

- **Not a production ATS** or a replacement for one. Single-resume sessions work well; multi-resume sessions are functional with a known cosmetic issue (orphaned node references).
- **Not a validated extraction benchmark.** The evaluation harness measures whatever extraction output you point it at, against synthetic fixtures. It does not yet establish the accuracy of the LLM extractors across real-world resume diversity.
- **Not full SHACL validation.** The integrity validator is a pragmatic, schema-tuned set of checks — useful, honest about scope, and explicitly not a substitute for formal shape validation.
- **DSPy integration is experimental** and disabled by default (`ENABLE_DSPY=false`); it has known threading issues in this deployment architecture and is documented as not production-validated.
- **ESCO coverage is partial by nature** (~50–60% match rates), and the fixtures are synthetic — real-world benchmark data is future work.
- **It is a research-grade portfolio system**, deployed and functional, best described as production-ready *for single-resume exploratory use* — no broader claim.

## 7. Why it matters for enterprise AI

The resume is the demo; the pattern is the point. Every enterprise trying to make its documents "AI-ready" faces the same choices this project makes explicit:

- **Knowledge quality is upstream of AI quality.** If extraction is unmeasured and entities unresolved, everything downstream — retrieval, reasoning, generation — inherits the noise. This project puts normalization, validation, and evaluation *inside* the pipeline rather than treating them as someone else's problem.
- **Traceability.** Triples with provenance beat embeddings when someone asks "why did the system say that?" — which, in regulated or high-stakes settings, someone always does.
- **Semantic interoperability** via open standards (SKOS, schema.org, ESCO) instead of another proprietary schema that dies with the vendor contract.
- **AI governance in practice.** An inspectable knowledge layer is what makes AI outputs auditable. You cannot govern what you cannot read.
- **A counterexample to "just chunk everything."** Chunk-and-embed is the right first move for many corpora — and a ceiling for structural questions. This project demonstrates the alternative: extract structure, validate it, analyze it, *then* generate the text you embed. The retrieval layer gets documents that already contain conclusions.
- **Evaluating extraction pipelines** is an unsolved habit in most organizations. A lightweight gold-label harness — even an early one — models the discipline.

## 8. Tagline options

Technical:

1. *From resume to RDF: LLM extraction with a semantic conscience.*
2. *LLM extraction in the front, knowledge graph in the back, evaluation throughout.*
3. *A working bridge between knowledge graphs and RAG — at a scale you can audit.*
4. *Structured, validated, exportable: what "AI-ready data" should actually mean.*

Elegant / conceptual:

5. *A resume says what you did. The graph shows how it connects.*
6. *Turning professional self-description into inspectable knowledge.*
7. *Your career has structure. Now you can see it.*
8. *What your resume knows but can't say.*

Thesis-forward:

9. *AI memory you can read.*
10. *Explicit knowledge structures make AI systems more trustworthy — here's a working example.*
11. *Beyond chunking: giving language models something structured to think with.*
12. *Knowledge graphs meet LLMs, and both are better for it.*

## 9. Suggested README intro

```markdown
# Resume Graph Explorer

**Turn a resume into a knowledge graph you can inspect, validate, query, and build on.**

Resume Graph Explorer extracts entities from resume documents using LLMs
(Claude, OpenAI, or local Ollama) and assembles them into an RDF knowledge
graph aligned with open standards — SKOS for concepts, schema.org for entity
types, ESCO for skill taxonomy. Explore the graph interactively, export it as
Turtle / RDF/XML / JSON-LD, check its semantic integrity via a validation
endpoint, and run a post-export analysis pipeline that turns graph structure
into natural-language career insights — documents designed to serve as
grounded memory for RAG systems and Digital Twins.

The deeper idea: a resume is a flat story, but a career has structure —
skills that bridge chapters, capabilities evidenced but never listed,
toolkits that drift over time. Making that structure explicit, in open
standards, is what makes it useful to both humans and AI systems.

**Status:** deployed and functional; production-ready for single-resume
sessions. The evaluation harness and validation checks are early and honest
about their scope. DSPy integration is experimental and off by default.
```

## 10. Suggested LinkedIn / portfolio blurb

> **Resume Graph Explorer** is a full-stack semantic web + AI system that turns resume documents into SKOS/schema.org-aligned RDF knowledge graphs. LLMs handle extraction; open standards make the result durable, mergeable, and inspectable. The system includes entity normalization with alias preservation, a graph-integrity validation endpoint, an early evaluation harness comparing extraction to gold labels, and a post-export pipeline that converts graph structure into natural-language insight documents — built to serve as grounded memory for RAG systems and Digital Twins. It's a portfolio-scale demonstration of a thesis I bring to consulting work: AI systems become more useful and more trustworthy when they're connected to explicit, inspectable knowledge structures rather than only loose text chunks.

---

# Deliverable 2 — Plain-English Portfolio Narrative

**Audience:** recruiters, collaborators, LinkedIn readers, intelligent non-specialists.

## 1. The simple explanation

Resume Graph Explorer is a web app that reads a resume and redraws it as a map.

Instead of a page of bullet points, you get an interactive network: you at the center, connected to your jobs, and your jobs connected to the skills you actually used in them, the organizations you worked for, your degrees and certifications. Every connection is a piece of your professional story made visible.

You can explore the map, download it in open data formats other tools understand, and run analyses that read the map's *shape* — which skills tie your career together, which chapters connect to which, what shows up in your history that your current resume no longer mentions.

## 2. Why I built it

Three reasons, braided together.

**Curiosity.** I'm a cognitive scientist by training. Resumes fascinate me as artifacts of self-description: a person compressing decades of work into one page, deciding — mostly unconsciously — what to keep, what to cut, and how to arrange it. I wanted to see what happens when you un-compress one.

**A professional thesis.** My consulting work centers on a claim: AI systems get more useful and more trustworthy when they're connected to explicit, inspectable knowledge — not just piles of text. That claim needs demonstrations, not just assertions. This is one.

**A portfolio artifact.** The project exercises, in one place, most of what I do professionally: LLM pipelines, knowledge graphs, semantic standards, entity resolution, evaluation, and turning structure back into human-readable insight.

## 3. The "aha" moment

A resume says what you did. A graph shows how the pieces relate.

Reading a resume, you process one line at a time: this job, then that job, then a skills list at the bottom. The connections live in the reader's head, if they get made at all.

The graph makes them explicit. The first time you see your own career as a network, you notice things the page was hiding: a skill quietly threading through four different jobs, a whole cluster from an earlier chapter that your current resume no longer mentions, a skill sitting in your skills list connected to nothing at all. The document didn't change — the representation did. And representation, it turns out, is most of the game.

## 4. What it can reveal

Concretely, the kinds of findings the analysis pipeline surfaces:

- **The connector skill isn't the one you'd guess.** You might list SQL first, but the graph shows Python is what links your analytics chapter to your research chapter to your consulting chapter — it's the bridge, structurally.
- **Skills that vanished from the story but not from the history.** Your cognitive science toolkit may have been trimmed from your current resume, but the graph still sees it in your job history — and can show where it connects to what you do now.
- **Claimed but not evidenced; evidenced but not claimed.** Some skills sit in your skills section with no job attached to them. Others appear in your actual work history but never made the skills list. Both gaps are worth knowing about before an interviewer finds them.
- **How your toolkit evolved.** Laid out chronologically, the graph shows technology eras of a career — what you adopted, what you kept, what you left behind.
- **Career shape.** Whether your path reads as one deepening lane, several bridged chapters, or a pivot — visible as topology, not just narrative.

## 5. Why this connects to AI

Here's the connection to the broader AI moment.

The standard way to give an AI system knowledge about documents is to chop the text into chunks and let the AI retrieve whichever chunks look relevant. For simple lookup, that works. But ask a structural question — *"what skill connects the different phases of this person's career?"* — and chunk retrieval fails, because no chunk contains the answer. The answer lives in the relationships *between* chunks, and those were never written down.

Resume Graph Explorer takes the other path: extract the structure first, check it for errors, analyze its shape, and then write the findings as short natural-language documents. An AI assistant — a career Digital Twin, say — that retrieves *those* documents is drawing on conclusions grounded in verified structure, not fragments of prose. It can answer the structural question because someone (the pipeline) actually did the structural work.

That's the thesis in miniature: **AI memory built on explicit, inspectable knowledge beats AI memory built on loose text — and you can check its work.**

## 6. Three versions of public copy

### 75-word version

Resume Graph Explorer turns a resume into an interactive knowledge graph. LLMs extract your jobs, skills, education, and organizations; open semantic-web standards (SKOS, schema.org, ESCO) link them into a structure you can explore, validate, and export. Analyses then read the graph's shape: which skills bridge your career chapters, what's claimed but not evidenced, what your history contains that your resume forgot. A working demonstration that explicit knowledge structures make AI systems more trustworthy.

### 150-word version

A resume says what you did. A graph can show how the pieces relate.

Resume Graph Explorer is a full-stack app that reads a resume, extracts its entities with LLMs, and assembles them into a knowledge graph built on open standards — SKOS, schema.org, and the ESCO skill taxonomy. You explore the graph interactively, export it in standard RDF formats, and run analyses that read its structure: the bridge skills connecting career chapters, skills claimed but never evidenced, capabilities buried in your history that your current resume no longer mentions.

The pipeline then writes those findings as natural-language insight documents — designed to serve as grounded memory for AI assistants and Digital Twins, so structural questions get structural answers instead of retrieved text fragments.

It's a portfolio project with a thesis: AI becomes more useful and more trustworthy when it's connected to explicit, inspectable knowledge — not just piles of text.

### 300-word version

Every resume is a compression artifact. A person takes decades of work and squeezes it onto a page or two, deciding — mostly unconsciously — what to keep, what to cut, and how to arrange it. What gets lost isn't just detail. It's structure: which skills actually thread through the whole career, which capabilities are evidenced by real work versus merely listed, which earlier chapters quietly disappeared from the current story.

Resume Graph Explorer is a full-stack application that un-compresses the resume. LLMs (Claude, OpenAI, or a local model) extract the entities — jobs, skills, organizations, education, certifications — and the system assembles them into a knowledge graph built on open semantic-web standards: SKOS for concepts, schema.org for entity types, ESCO for skill taxonomy. You explore the graph interactively, export it in standard RDF formats, and validate its integrity. Then an analysis pipeline reads the graph's shape and reports what it finds: bridge skills connecting career chapters, claimed-versus-evidenced gaps, how your toolkit evolved over time, how your roles progressed.

Finally, the pipeline writes those structural findings as natural-language documents — the kind an AI assistant or career "Digital Twin" can retrieve to answer questions with structurally grounded conclusions, rather than guessing from fragments of biography text.

That last step is the point. The dominant approach to making documents AI-ready is to chunk the text and hope retrieval finds the right pieces. This project demonstrates the alternative: extract explicit structure, check it, analyze it, and only then generate the text an AI remembers. The resume is a friendly, human-scale test case for a pattern that matters everywhere organizations are connecting AI to their knowledge.

Built by a cognitive scientist who thinks representation is most of the game — and that AI systems, like people, think better when their knowledge has structure.

## 7. LinkedIn launch post

> I've spent my career at the intersection of how people represent knowledge and how machines can work with it. Recently I built something that sits exactly on that line, and I want to share it.
>
> **Resume Graph Explorer** takes an ordinary resume and redraws it as a knowledge graph — an interactive map of jobs, skills, organizations, education, and how they connect. LLMs do the reading; open semantic-web standards (SKOS, schema.org, ESCO) give the result a durable, inspectable structure; and an analysis pipeline reads the graph's *shape* to surface things the page-form resume hides.
>
> Some of what the graph sees that the document can't say:
>
> — The skill that structurally bridges your career chapters often isn't the one you list first.
> — Some skills you claim have no evidence attached; some skills you've clearly used never made the list.
> — Whole toolkits from earlier chapters vanish from current resumes but remain visible in the history.
>
> The part I find most interesting is the last mile: the pipeline writes its structural findings as short natural-language documents, built to serve as memory for AI assistants. Instead of an AI retrieving arbitrary chunks of biography text, it retrieves conclusions grounded in verified structure. Ask a structural question, get a structural answer.
>
> That's the real thesis, and the resume is just a friendly test case for it: AI systems become more useful — and much easier to trust — when they're connected to explicit, inspectable knowledge rather than only loose text.
>
> It's a working research-grade system, not a product: honest about its evaluation coverage, its validation scope, and what's still experimental. The repo, the live demo, and the design docs are linked below. If you work on knowledge graphs, LLM extraction, AI evaluation, or making organizational knowledge AI-ready, I'd genuinely value your reactions — especially the critical ones.

## 8. Audience-specific angles

**AI/data hiring managers**
End-to-end LLM system engineering by one person: provider-agnostic extraction, entity resolution, standards-based modeling, a validation endpoint, an evaluation harness, real-time streaming UX, and a deployed full stack. The interesting signal isn't any single feature — it's that quality controls (normalization, validation, evaluation) are built into the pipeline, which is the discipline production AI teams need.

**Knowledge graph / semantic web people**
A genuine SKOS/schema.org/ESCO implementation where LLMs feed the graph instead of replacing it: `skos:altLabel` preservation through normalization, ESCO alignment via the REST API with honest coverage numbers, one shared builder path so exports are complete by construction, and integrity checks that treat the graph as something that can be wrong. Standards as working infrastructure, not decoration.

**AI governance people**
A small working model of auditable AI. Every extracted claim is a readable triple; a validation report separates structural errors from warnings; an evaluation harness makes extraction quality measurable; and the limits (early evals, partial ESCO coverage, experimental DSPy) are documented rather than glossed. The pattern — inspectable knowledge layer between LLM and downstream use — is the governance-relevant part.

**Recruiters**
A demonstration piece from a PhD cognitive scientist and AI consultant who ships: full-stack (Python/Flask + React), applied LLMs, semantic data standards, and evaluation practice, all in one deployed project. It also happens to be *about* resumes — it can show a candidate's career as a connected map, including strengths their own resume undersells.

**Nontechnical collaborators**
It turns a resume into an explorable map of a career — and the map notices things the page can't: the skill quietly connecting all your chapters, the expertise you stopped mentioning, the claims with no story behind them. Useful for anyone rethinking how they present decades of work.

**Future clients**
This is the "make our knowledge AI-ready" problem at demonstration scale. The same questions your organization faces — how do we extract structure from messy documents, resolve duplicate entities, validate quality, measure the pipeline, and feed AI systems knowledge we can audit? — are answered here end to end, in a domain simple enough to evaluate in an afternoon. It's the working argument behind my consulting approach: structure first, then AI.

---

# Closing Recommendations

## Top 5 strongest positioning lines

1. **"A resume says what you did. The graph shows how it connects."** — the whole project in twelve words; works for every audience.
2. **"AI systems become more useful and more trustworthy when they're connected to explicit, inspectable knowledge structures rather than only loose text chunks."** — the thesis; this is what makes the project *yours* and not just another LLM demo.
3. **"RDF export as product, not side effect."** — instantly credible to semantic web and data-architecture audiences; signals unusual seriousness about the knowledge layer.
4. **"Extract the structure, check it, analyze it — and only then generate the text an AI remembers."** — the cleanest statement of the graph-to-RAG pattern, and the most transferable to enterprise conversations.
5. **"Some skills you claim have no evidence attached; some skills you've used never made the list."** — the concrete, human hook; the moment nontechnical readers *get it*.

## Top 3 audiences to prioritize first

1. **Knowledge graph / semantic web practitioners.** They'll recognize the craft immediately (SKOS altLabels, ESCO alignment, single builder path), they're underserved with good LLM-era examples, and their endorsement transfers credibility to every other audience.
2. **AI/data hiring managers and technical leads.** The strongest career ROI: the project demonstrates exactly the pipeline-plus-evaluation discipline they're hiring for, in an auditable single-author codebase.
3. **Future consulting clients (via the governance/enterprise framing).** The thesis maps directly onto budgets: "AI-ready data," knowledge quality, and auditability. This audience converts interest into engagements — but they're best reached *after* the first two audiences have validated the work publicly.

## Recommended next public artifact

**First: the README rewrite** (using the intro in §9 of the brief). It's low-effort, and it's where every other artifact will send people — technical readers judge the project within thirty seconds of landing on the repo, and the current README leads with features rather than the thesis. Fix the landing zone before driving traffic to it.

**Then: one blog post** — *"What a resume can't say: turning self-description into a knowledge graph."* Structure: the aha moment (§3), one real annotated graph screenshot, the claimed-vs-evidenced finding, and the graph-to-RAG argument (§5). The blog post is the asset the LinkedIn launch post links to, the portfolio page excerpts, and future talks are built from — write it once, reuse it everywhere.

The LinkedIn post (§7) then launches both. A demo video and carousel are worthwhile later, once the written positioning has been tested against real reactions.

---

*Assumptions made: repo details (validation endpoint, evaluation harness scope, ESCO match rates, single builder path, DSPy status) were verified against the codebase and README as of July 2026. Claims about deployment status follow the repo's own qualification: production-ready for single-resume sessions, multi-resume functional with a known cosmetic issue.*
