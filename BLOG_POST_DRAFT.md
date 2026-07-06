# What a Resume Can't Say

*Turning professional self-description into a knowledge graph — and why the shape of a career matters more than the page it's printed on.*

> **Draft for personal blog / portfolio site.**
> Placeholders marked `[SCREENSHOT: …]` and `[LINK: …]` need real assets before publishing.
> Target length as drafted: ~1,400 words. Cut candidates are marked at the end.

---

Every resume is a compression artifact.

Someone takes ten or twenty or thirty years of work and squeezes it onto a page or two. In the process they make hundreds of small decisions — what to keep, what to cut, which verbs sound right, what order tells the best story. Most of those decisions are unconscious. And the resume that comes out the other end is a genuinely strange document: a linear, self-authored narrative about a thing — a career — that isn't linear at all.

I'm a cognitive scientist by training, and resumes fascinate me as artifacts of self-description. So I did the thing you do with a fascination and an engineering habit: I built a system to un-compress one. It's called **Resume Graph Explorer**, and this post is about what happened when I pointed it at real resumes — including my own.

## The experiment

The system does something simple to describe and fussy to build: it reads a resume, uses a large language model to extract the entities in it — jobs, skills, organizations, degrees, certifications — and then assembles those entities into a knowledge graph built on open semantic-web standards (SKOS for concepts, schema.org for entity types, ESCO for skill taxonomy).

Instead of a page of bullet points, you get a network. You're a node at the center. Your jobs connect to you. Your skills connect to the jobs where you actually used them. Organizations, education, and certifications hang off the structure where they belong. Every connection is a piece of the professional story made explicit and inspectable.

[SCREENSHOT: interactive graph view of a full resume — annotate the person node, one job cluster, and one skill connected to multiple jobs]

The document doesn't change. The *representation* does. And representation, it turns out, is most of the game.

## The moment it got interesting

Reading a resume, you process one line at a time: this job, then that job, then a skills list at the bottom. Whatever connections exist between them live in the reader's head — if they get made at all.

The graph makes them explicit, and the first time I saw a full career rendered as a network, three things jumped out that the page had been hiding in plain sight.

**The connector skill wasn't the one listed first.** Careers have bridge skills — the capabilities that structurally link one chapter to the next. On paper, a skills section is an undifferentiated list; SQL and Python and "stakeholder communication" all get the same font. In the graph, one of them is visibly load-bearing: it's the node with edges into the analytics chapter *and* the research chapter *and* the consulting chapter. That's not a judgment call. It's topology.

**Whole toolkits had vanished from the story but not from the history.** Resumes get pruned as careers move on — reasonably so. But the pruning is one-directional: skills disappear from the current document while remaining fully present in the job history it summarizes. My own cognitive science toolkit had mostly been trimmed out of my consulting-era resume. The graph still saw it, sitting in the earlier chapters, connected to methods I use every week under different names.

**Some claims had no evidence attached — and some evidence had no claim.** This was the finding I kept coming back to, so it gets its own section.

## Claimed versus evidenced

A resume actually contains two different kinds of skill statements, and the flat format makes them look identical.

There are **claimed skills**: the ones in the skills section, asserted directly. And there are **evidenced skills**: the ones attached to actual work — "built the ETL pipeline in Python," "administered the Postgres cluster." In the graph, these are structurally different. A claimed skill connects to the person. An evidenced skill connects to a *job*, which connects to the person. The evidence relationship is explicit.

Which means you can run the comparison — and the comparison is where resumes get honest:

- **Claimed but not evidenced.** Skills sitting in the list with no job attached to them anywhere in the graph. Sometimes that's legitimate (a skill from coursework, a genuine capability that never made it into a bullet point). Sometimes it's aspiration wearing the costume of experience. Either way, it's exactly the gap a sharp interviewer finds — and better to find it yourself first.

[SCREENSHOT: skill-gap analysis output — a claimed skill with no job edges next to an evidenced skill with three, annotated]

- **Evidenced but not claimed.** The reverse case is more interesting, because it's pure undersell: skills demonstrably present in the work history that never made the skills list. These are capabilities the person *has*, *used*, and *forgot to say they have*. Nearly every resume I ran through the system had several.

No human reader performs this audit reliably, because it requires holding the entire document in mind at once and checking every claim against every bullet point. It's tedious for a person and trivial for a graph. That asymmetry — things that are invisible in linear text and obvious in structure — is the whole reason the project exists.

## Why this matters beyond resumes

Here's where the toy problem stops being a toy.

The standard way to make documents "AI-ready" right now is: chop the text into chunks, embed the chunks, and let the AI retrieve whichever chunks look relevant to a question. For lookup questions — *when did she work at X?* — that's fine. The answer is sitting in some chunk.

But ask a structural question — *what skill connects the different phases of this career? which claims lack evidence? how did the toolkit evolve?* — and chunk retrieval quietly fails. Not with an error; with a fluent guess. No chunk contains the answer, because the answer lives in the relationships *between* chunks, and those relationships were never written down anywhere. The retrieval system can't find what was never made explicit.

Resume Graph Explorer takes the other path, and the order of operations is the point:

1. **Extract the structure** (LLM entity extraction into a standards-based graph),
2. **check it** (entity normalization, plus a validation pass that catches dangling references, missing labels, and near-duplicate entities),
3. **analyze its shape** (bridge skills, claimed-vs-evidenced gaps, technology evolution, role progression),
4. and only *then* **generate the text an AI remembers** — short natural-language insight documents, each one a conclusion grounded in verified structure, written to be embedded and retrieved.

An AI assistant built on those documents — a career "Digital Twin," say — answers the structural question correctly not because the language model is clever, but because the structural work was actually done, upstream, where it can be inspected. Ask a structural question, get a structural answer. And when the answer is wrong, you can find out *where* it went wrong, because every step of the chain is readable: the triple, the validation report, the analysis document.

That's my broader thesis, and the resume is just its friendliest possible test case: **AI systems become more useful — and much easier to trust — when they're connected to explicit, inspectable knowledge structures rather than only loose text.** Every organization currently pointing an LLM at its document pile is choosing, knowingly or not, between these two paths.

## What it is and isn't

In the interest of practicing the inspectability I'm preaching: this is a working research-grade system, not a product. Single-resume analysis works well end to end; multi-resume sessions work with a known cosmetic issue. The evaluation harness — fixtures, gold labels, precision/recall per entity type — is real but early; it measures extraction output against synthetic fixtures and doesn't yet constitute a benchmark of the extractors across real-world resume diversity. The validation endpoint runs a pragmatic set of integrity checks, not full SHACL validation. About half of extracted skills find a match in the ESCO taxonomy, which is roughly what ESCO's scope predicts for modern technical stacks.

The code, the design docs, and the honest status pages are all in the repo: [LINK: repo]. There's a live demo at [LINK: demo].

## Try it on yourself

If you have a resume lying around — and you do — it's worth twenty minutes to see your own career as a shape instead of a story. You already know what you did. The graph might tell you how it connects.

---

**Possible cuts if trimming for length:** the second paragraph of "The experiment" (standards detail — the technical audience will hit the repo anyway); the parenthetical examples in "Claimed but not evidenced."

**SEO/metadata suggestions:**
- Title tag: *What a Resume Can't Say: Turning Careers into Knowledge Graphs*
- Description: *I built a system that turns resumes into semantic knowledge graphs. Here's what career structure reveals that the page hides — and why it matters for trustworthy AI.*
- Tags: knowledge graphs, LLM extraction, semantic web, RAG, AI evaluation, digital twin
