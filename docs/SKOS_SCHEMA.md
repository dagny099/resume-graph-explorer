# SKOS Schema Documentation - Resume Explorer

**Version**: 1.0
**Date**: December 8, 2025
**Status**: Stable

## Overview

Resume Explorer uses a **hybrid SKOS-compliant vocabulary** combining:
- **SKOS Core** - Base concept organization system
- **ESCO** - European Skills, Competences, Qualifications and Occupations
- **schema.org** - Common structured data vocabularies
- **Custom RE namespace** - Resume-specific properties

This approach maximizes **semantic web interoperability** while allowing project-specific extensions.

---

## Namespaces

### Standard Vocabularies

| Prefix | URI | Purpose |
|--------|-----|---------|
| `skos` | `http://www.w3.org/2004/02/skos/core#` | Concept organization, hierarchies |
| `schema` | `http://schema.org/` | Person, Organization, Job, Education |
| `esco` | `http://data.europa.eu/esco/` | Skills, occupations, qualifications |
| `dcterms` | `http://purl.org/dc/terms/` | Metadata properties |

### Custom Vocabularies

| Prefix | URI | Purpose |
|--------|-----|---------|
| `re` | `http://resumeexplorer.org/ontology#` | Custom classes and properties |
| `resume` | `http://resumeexplorer.org/resource/` | Individual entity instances |

---

## Entity Types (RDF Classes)

### Core Entities

#### Person (`schema:Person`)
Represents the resume owner.

**Properties**:
- `schema:name` - Full name
- `schema:email` - Email address
- `schema:telephone` - Phone number
- `schema:address` - Geographic location
- `schema:description` - Professional summary

**Relationships**:
- `re:hasJob` → `Job`
- `re:hasSkill` → `Skill`
- `schema:alumniOf` → `Education`
- `re:hasCertification` → `Certification`

#### Job (`schema:JobPosting`)
Represents a job position.

**Properties**:
- `schema:title` - Job title
- `schema:hiringOrganization` → `Organization`
- `schema:jobLocation` - Location
- `schema:description` - Responsibilities
- `schema:startDate` - Employment start date
- `schema:endDate` - Employment end date (or null if current)
- `re:isCurrent` - Boolean flag for current position

**Relationships**:
- `re:usedSkill` → `Skill`
- `re:usedTechnology` → `Technology`
- `re:achievement` - Literal achievement descriptions

#### Skill (`esco:Skill`)
Represents a skill or competency.

**Properties**:
- `skos:prefLabel` - Skill name
- `skos:definition` - Skill description
- `skos:exactMatch` - Link to ESCO skill URI
- `re:skillCategory` - Category (Technical, Soft, Domain)
- `re:proficiencyLevel` - Proficiency (Expert, Intermediate, Beginner)
- `re:yearsExperience` - Years of experience

**SKOS Hierarchy**:
- `skos:broader` → Parent category (e.g., Python → Programming Languages)
- `skos:narrower` → Subcategories
- `skos:related` → Related skills

**Example ESCO Mapping**:
```turtle
resume:skill-abc123 a esco:Skill ;
    skos:prefLabel "Python Programming" ;
    skos:exactMatch <http://data.europa.eu/esco/skill/c3b1499e...> ;
    skos:broader resume:skill-programming ;
    skos:related resume:skill-data-science .
```

#### Education (`schema:EducationalOccupationalCredential`)
Represents educational credentials.

**Properties**:
- `schema:credentialCategory` - Degree type (PhD, MS, BS, etc.)
- `schema:educationalCredentialAwarded` - Field of study
- `schema:recognizedBy` → `Organization` (institution)
- `schema:availableAtOrFrom` - Location
- `schema:startDate` - Program start date
- `schema:endDate` - Graduation date
- `re:isCurrent` - Currently enrolled
- `re:gpa` - Grade point average

#### Certification (`re:Certification`)
Custom entity for professional certifications.

**Properties**:
- `schema:name` - Certification name
- `re:issuingOrganization` - Issuing body
- `re:issueDate` - Issue date
- `re:expirationDate` - Expiration date (if applicable)
- `re:credentialId` - Credential/certificate ID
- `re:credentialUrl` - Verification URL
- `re:isActive` - Active status
- `re:isExpired` - Expired status

#### Organization (`schema:Organization`)
Represents companies, institutions, etc.

**Properties**:
- `schema:name` - Organization name
- `schema:address` - Primary location
- `schema:url` - Website
- `schema:description` - Description
- `re:organizationType` - Type (Company, University, etc.)
- `re:industry` - Industry sector

---

## Relationship Types (RDF Properties)

### Employment Relationships
- `schema:worksFor` - Person works for Organization
- `re:employedBy` - Employment relationship
- `re:holdsPosition` - Holds job position

### Skill Relationships
- `re:hasSkill` - Person has skill
- `re:usedSkill` - Skill used in job
- `schema:skills` - Job requires skill

### Education Relationships
- `schema:alumniOf` - Person is alumni of institution
- `schema:hasCredential` - Person has educational credential
- `re:hasCertification` - Person has certification

### Technology Relationships
- `re:usedTechnology` - Technology used in job
- `re:knowsTechnology` - Person knows technology

### SKOS Hierarchical Relationships
- `skos:broader` - Broader concept
- `skos:narrower` - Narrower concept
- `skos:related` - Related concept
- `skos:exactMatch` - Exact match to external vocabulary

### Temporal Relationships
- `schema:startDate` - Start date (jobs, education)
- `schema:endDate` - End date
- `schema:duration` - Duration

---

## ESCO Integration

### ESCO Skill Taxonomy

ESCO provides standardized URIs for skills used across Europe. Resume Explorer maps extracted skills to ESCO concepts when possible.

**Example ESCO Skills**:
```python
{
    "python": "http://data.europa.eu/esco/skill/c3b1499e-77e4-42e8-be6f-676e9f1b7c91",
    "machine_learning": "http://data.europa.eu/esco/skill/f8b1b3e4-92c5-4e8a-8c5e-7c5e8b1b3e4e",
    "data_analysis": "http://data.europa.eu/esco/skill/g8b1b3e4-92c5-4e8a-8c5e-7c5e8b1b3e4f",
}
```

### ESCO Occupation Taxonomy

**Example ESCO Occupations**:
```python
{
    "data_scientist": "http://data.europa.eu/esco/occupation/8b1b3e4a-92c5-4e8a-8c5e-7c5e8b1b3e4q",
    "software_engineer": "http://data.europa.eu/esco/occupation/9b1b3e4a-92c5-4e8a-8c5e-7c5e8b1b3e4r",
}
```

### Skill Hierarchy

Skills are organized hierarchically following ESCO classification:

```
Technical Skills
├── Programming Languages
│   ├── Python
│   ├── JavaScript
│   ├── Java
│   └── SQL
├── Data Science
│   ├── Machine Learning
│   ├── Data Analysis
│   ├── Statistical Analysis
│   └── Data Visualization
└── Cloud Infrastructure
    ├── AWS
    ├── Azure
    ├── Docker
    └── Kubernetes
```

---

## Provenance & Metadata

All entities track provenance:

- `re:confidence` (xsd:float) - Extraction confidence (0.0-1.0)
- `re:sourceDocument` (xsd:string) - Source filename
- `re:createdAt` (xsd:dateTime) - Creation timestamp

**Example**:
```turtle
resume:skill-abc123
    re:confidence 0.95 ;
    re:sourceDocument "resume.pdf" ;
    re:createdAt "2025-12-08T10:30:00Z" .
```

---

## RDF Export Formats

Resume Explorer supports three RDF serialization formats:

### 1. Turtle (.ttl)
Human-readable, compact syntax.

```turtle
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix schema: <http://schema.org/> .
@prefix resume: <http://resumeexplorer.org/resource/> .

resume:person-123 a schema:Person ;
    schema:name "Barbara Hidalgo-Sotelo" ;
    schema:email "barbs@example.com" ;
    re:hasSkill resume:skill-python .

resume:skill-python a esco:Skill ;
    skos:prefLabel "Python Programming" ;
    skos:broader resume:skill-programming ;
    re:proficiencyLevel "Expert" .
```

### 2. RDF/XML (.rdf)
Standard XML-based RDF syntax.

```xml
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:schema="http://schema.org/"
         xmlns:resume="http://resumeexplorer.org/resource/">
  <schema:Person rdf:about="http://resumeexplorer.org/resource/person-123">
    <schema:name>Barbara Hidalgo-Sotelo</schema:name>
    <schema:email>barbs@example.com</schema:email>
  </schema:Person>
</rdf:RDF>
```

### 3. JSON-LD (.jsonld)
JSON-based RDF, compatible with web APIs.

```json
{
  "@context": {
    "schema": "http://schema.org/",
    "resume": "http://resumeexplorer.org/resource/"
  },
  "@id": "resume:person-123",
  "@type": "schema:Person",
  "schema:name": "Barbara Hidalgo-Sotelo",
  "schema:email": "barbs@example.com"
}
```

---

## SPARQL Query Examples

Once the graph is built, you can query using SPARQL:

### Find all skills used in data science jobs
```sparql
PREFIX schema: <http://schema.org/>
PREFIX re: <http://resumeexplorer.org/ontology#>
PREFIX resume: <http://resumeexplorer.org/resource/>

SELECT DISTINCT ?skill ?skillLabel
WHERE {
    ?job a schema:JobPosting ;
         schema:title ?title ;
         re:usedSkill ?skill .
    ?skill skos:prefLabel ?skillLabel .
    FILTER (CONTAINS(LCASE(?title), "data scientist"))
}
```

### Find skill gaps (skills mentioned in jobs but not in person's skill list)
```sparql
PREFIX schema: <http://schema.org/>
PREFIX re: <http://resumeexplorer.org/ontology#>

SELECT DISTINCT ?skill
WHERE {
    ?job re:usedSkill ?skill .
    FILTER NOT EXISTS {
        ?person re:hasSkill ?skill .
    }
}
```

---

## Vocabulary Versioning

**Current Version**: 1.0
**Backward Compatibility**: Guaranteed for minor versions (1.x)
**Breaking Changes**: Major version increments (2.0, 3.0, etc.)

---

## References

- **SKOS**: [W3C SKOS Recommendation](https://www.w3.org/TR/skos-reference/)
- **ESCO**: [European Commission ESCO Portal](https://esco.ec.europa.eu/)
- **schema.org**: [schema.org Vocabulary](https://schema.org/)
- **RDF**: [W3C RDF 1.1 Specification](https://www.w3.org/TR/rdf11-concepts/)

---

## Contact & Contributions

For questions or contributions to the vocabulary:
- GitHub Issues: [Resume Explorer Issues](https://github.com/yourusername/resume_explorer/issues)
- Email: maintainer@resumeexplorer.org

---

*Last Updated: December 8, 2025*
*License: CC BY 4.0*
