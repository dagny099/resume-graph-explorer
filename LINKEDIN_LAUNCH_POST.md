# LinkedIn Launch Post — Final

*Publish after the blog post is live. Replace the two `[LINK]` placeholders. Post text below the rule is paste-ready.*

---

I've spent my career at the intersection of how people represent knowledge and how machines can work with it. Recently I built something that sits exactly on that line, and I want to share it.

**Resume Graph Explorer** takes an ordinary resume and redraws it as a knowledge graph — an interactive map of jobs, skills, organizations, education, and how they connect. LLMs do the reading; open semantic-web standards (SKOS, schema.org, ESCO) give the result a durable, inspectable structure; and an analysis pipeline reads the graph's *shape* to surface things the page-form resume hides.

Some of what the graph sees that the document can't say:

— The skill that structurally bridges your career chapters often isn't the one you list first.
— Some skills you claim have no evidence attached; some skills you've clearly used never made the list.
— Whole toolkits from earlier chapters vanish from current resumes but remain visible in the history.

The part I find most interesting is the last mile: the pipeline writes its structural findings as short natural-language documents, built to serve as memory for AI assistants. Instead of an AI retrieving arbitrary chunks of biography text, it retrieves conclusions grounded in verified structure. Ask a structural question, get a structural answer.

That's the real thesis, and the resume is just a friendly test case for it: AI systems become more useful — and much easier to trust — when they're connected to explicit, inspectable knowledge rather than only loose text.

It's a working research-grade system, not a product: honest about its evaluation coverage, its validation scope, and what's still experimental.

I wrote up the full story — including what happened when I ran my own resume through it: [LINK: blog post]

Code, live demo, and design docs: [LINK: repo]

If you work on knowledge graphs, LLM extraction, AI evaluation, or making organizational knowledge AI-ready, I'd genuinely value your reactions — especially the critical ones.

---

## Posting notes

- **First comment:** put the repo link in a first comment as well — LinkedIn deprioritizes posts with external links; some people put *all* links in the first comment and say "links in comments." Consider testing that variant.
- **Image:** attach one annotated graph screenshot (the same one used in the blog post). Posts with a strong visual outperform text-only for this kind of announcement.
- **Hashtags (3–5 max, if used):** #KnowledgeGraphs #SemanticWeb #LLM #AIEvaluation
- **Timing:** Tue–Thu morning (US) generally performs best for professional/technical content.
- **Engagement plan:** reply substantively to early comments within the first two hours; the critical/technical comments are the ones to engage most visibly — they validate the "honest about scope" positioning.
