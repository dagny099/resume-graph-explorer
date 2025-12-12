# Interoperability Roadmap: Enrichment, Recommendations, and Semantic Search

## Objectives
- Enrich résumé graph nodes with external linked data (e.g., Wikidata, DBpedia) to add context for universities, companies, skills, and locations.
- Build graph-based recommendation pipelines that leverage enrichment to suggest roles, learning paths, and collaborators.
- Enable semantic search that blends embeddings with graph structure for precise, intent-aware answers.

## Milestone order (why this order)
1. **Link Open Data enrichment** — Establish clean identifiers and enriched context first; both recommendations and embeddings benefit from richer, normalized entities.

2. **Semantic search / embeddings** — Build unified text/graph representations that leverage enrichment; reusable for recommendations.

3. **Graph-based recommendations** — Use enriched graph + embeddings for hybrid signals; ship curated, interpretable queries and APIs.

## Recommended Order of Milestones
0. PREP MILESTONE: **Foundations & Data Quality**
   - Normalize entity identifiers (URI scheme, stable IDs) and ensure exports include IRIs.
   - Add lightweight SHACL validation to guarantee consistent labels, types, and temporal properties.
   - Rationale: Reliable identifiers and shape validation prevent downstream enrichment/recommendation drift.

1. MILESTONE 1: **Linked Open Data (LOD) Enrichment** Pipeline
  - **Rationale**: Improves entity disambiguation, boosts search recall, and provides richer attributes for downstream ranking.

   - **Phase 1a: Entity alignment**
     - Start with Wikidata (broad coverage) and DBpedia (stable URIs) for universities, companies, and skills.
     - Implement deterministic matching first (exact name + country/industry filters), then add fuzzy matching when needed.
     - Store external IDs as `owl:sameAs`/`skos:exactMatch` and cache lookups.
   - **Phase 1b: Attribute enrichment**
     - Pull high-value properties: organization type, headquarters location, industry (NAICS/ISIC), enrollment size, founding dates, aliases.
     - Use named graphs or provenance triples to tag data source and retrieval timestamp.
   - **Phase 1c: Quality controls**
     - Add SHACL shapes to validate enriched fields and flag conflicts (e.g., multiple industries).
     - Build a diff report for manual review before merging new triples.

2. MILESTONE 2: **Semantic Search & Embeddings**
  - **Rationale**: Enrichment boosts embedding quality and improves query recall; hybrid search keeps precision high. 
   - **Phase 2a: Corpus generation**
     - Convert nodes/edges into text snippets (include enriched labels and provenance) and index in a hybrid engine (e.g., OpenSearch kNN + BM25, Weaviate, or Vespa).
   - **Phase 2b: Hybrid retrieval**
     - Combine embedding similarity with graph filters (e.g., skills within a timeframe, projects in a given industry).
     - Provide SPARQL-to-text bridging for questions the embedding layer misses.
   - **Phase 2c: Answer grounding**
     - Return supporting triples/paths with each result to maintain explainability.
   - Rationale: Hybrid retrieval balances flexibility (semantic) with precision (graph constraints).

3. MILESTONE 3: **Graph-Based Recommendations**
  - **Rationale**: Recommendations become explainable by leveraging explicit graph paths and enriched attributes. 
   - **Phase 3a: Feature graph construction**
     - Create derived relations ("skill co-usage", "role progression", "project similarity") from the enriched graph.
     - Materialize key aggregates (skill frequency, recency) to speed up queries.
   - **Phase 3b: Rule- & path-based recommenders**
     - Implement SPARQL/Cypher templates for: suggested next roles, skills to deepen, courses/certs tied to gaps.
     - Use enrichment (e.g., industry or academic rankings) to prioritize results.
   - **Phase 3c: Feedback & evaluation**
     - Add lightweight feedback signals (accepted/ignored) and offline evaluation using held-out roles.

## Implementation Notes and Trade-offs
- **Source selection**: Wikidata offers breadth and multilingual labels; DBpedia is stable but less current. Mix both and prefer sources with clear licensing. For niche skills, consider IEEE/ACM taxonomies or schema.org `Course` metadata from MOOCs.
- **Matching strategy**: Deterministic rules are easy to maintain and document; fuzzy matching improves coverage but raises risk of false positives—gate via confidence scores and manual review queues.
- **Storage**: Keep enrichment in named graphs to separate canonical résumé data from external facts; simplifies rollback and provenance tracking.
- **Performance vs. freshness**: Caching enrichment results speeds pipelines but can go stale; schedule periodic revalidation for high-change entities (companies) and slower cycles for universities.
- **Explainability**: Prioritize recommendation and search outputs that cite the specific triples and sources used; this reduces user trust issues compared to opaque embeddings-only approaches.
- **Documentation-first approach**: Document entity matching rules, data sources, and validation shapes in versioned docs/tests; this keeps the system maintainable as sources or schemas evolve.

## Quick Start Checklist (per milestone)
- **Foundations**: Define URI scheme; add SHACL shapes for Person, Organization, Role, Skill; enable shape validation in CI.
- **LOD Enrichment**: Build a script/notebook for entity alignment against Wikidata/DBpedia with exportable match reports; store matches as `owl:sameAs`.
- **Recommendations**: Ship a handful of SPARQL/Cypher templates and example outputs; add evaluation notebook with simple precision/recall on historical roles.
- **Semantic Search**: Generate snippet corpus, index in chosen vector+BM25 backend, expose a query API that returns both text hits and the supporting triples.

## Future Extensions
- Add geospatial queries (e.g., skills by region) using GeoSPARQL or PostGIS.
- Integrate SHACL rules with CI to block regressions in enrichment or recommendations.
- Offer a public SPARQL endpoint or GraphQL wrapper backed by the enriched graph for downstream apps.
- Docs & reproducibility: Provide one-command scripts for enrichment, embedding, and recommender evaluation; keep examples small and copy-pasteable for maintainers.


