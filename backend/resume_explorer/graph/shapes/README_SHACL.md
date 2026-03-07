# SHACL Validation for Resume Explorer (Lenient Mode)

This folder contains SHACL "shapes" that validate exported RDF graphs (Turtle/RDF/XML/JSON-LD-as-RDF).

## What SHACL is (plain language)

- Your export file is a *graph* (nodes + relationships).
- SHACL is a *rule sheet* that checks whether the graph follows expectations.
- It answers: “Is this RDF usable by other tools, and is the structure reasonably clean?”

Think of it like:
- JSON Schema, but for RDF graphs
- or Pydantic validation, but for triples

## What “Lenient Mode” means

Lenient mode is designed to be hard to fail.
- It only flags serious issues as **Violations** if you choose to later.
- Most checks are **Warnings** (quality nudges).

This is ideal when you’re still iterating on the data model and extraction pipeline.

## What these checks are looking for

The shapes focus on what real users complain about:

### 1) Missing human-readable labels
If nodes have no `schema:name` / `skos:prefLabel` / `rdfs:label`, graph UIs become unreadable.

### 2) Literal strings where IRIs should be
Example: `re:usedTechnology "uuid-string"` is technically RDF, but it is less interoperable.
Tools and downstream graphs work best when relationships point to actual nodes (IRIs).

### 3) Datatypes that support querying
Dates should look like `xsd:date`, booleans like `xsd:boolean`, etc.
Otherwise SPARQL filters and analytics become fragile.

## Quick start: validate an export

### 1) Install dependencies
From your backend virtualenv (or system python):

pip install pyshacl rdflib

### 2) Run validation
From the repo root (or adjust paths):

pyshacl \
  -s backend/resume_explorer/graph/shapes/resume.lenient.shapes.ttl \
  -d path/to/your/export.ttl

### 3) Interpret results
- If the command exits cleanly: the file is structurally reasonable.
- If you see **Warnings**: the export is usable, but there are quality improvements you may want.
- If you see **Violations** (more common in strict mode): the export likely breaks interoperability expectations.

## What to do with the output

Treat the output as a checklist for improving exports:
- Add missing labels (schema:name / skos:prefLabel)
- Ensure relationship targets are IRIs (mint nodes instead of literals)
- Normalize datatypes (dates, booleans, numerics)

## Recommended workflow

1) Run lenient SHACL during development to catch obvious issues early
2) Once stable, add a strict SHACL file and run it in CI on sample exports
3) Optionally validate on export and produce a QA report alongside the RDF
