##  Where Edge Types Come From

This document describes the custom classification scheme for EDGE TYPES that I created for this application. 

The edge types are categories assigned by the code to organize relationships. They're a custom organizational scheme designed to make the graph easier to understand visually by semantically grouping relationships that have similar meanings. The result should be a sense of "understanding" the structure of a resume at-a-glance.

Here's what happens:

### 1. The System Creates Relationships

When a resume is processed, the system **creates connections (edges) between entities**. For example:
- "Person `hasSkill` Python"
- "Person `hasJob` Software Engineer"
- "Job `hiringOrganization` Google"


### 2. The Code Categorizes Each Relationship

There's a function called _classify_edge() that looks at each relationship and assigns it to one of these buckets:

🟢 OWNERSHIP - "Person owns/has something"
- hasJob, hasSkill, hasCertification, alumniOf
- Example: You have a skill in Python, you have a job title

🔵 ORGANIZATIONAL - "Connections to organizations"
- hiringOrganization, recognizedBy
- Example: This job is at Google, this degree is from MIT

🟣 USAGE - "Something was used/applied"
- usedSkill, usedTechnology
- Example: You used Python in this project, you used Docker in this job

🟠 HIERARCHICAL - "Taxonomy/hierarchy relationships"
- broader, narrower, related (from SKOS vocabulary)
- Example: "Machine Learning" is broader than "Neural Networks"

⚫ TYPING - "What type of thing is this?"
- rdf:type
- Example: This entity is a "Person", this entity is a "Skill"

⚪ OTHER - "Everything else that doesn't fit above"


In: `/backend/resume_explorer/graph/networkx_adapter.py:366-381`

```
def _classify_edge(self, pred: URIRef) -> str:
    """
    Classify edge type for visualization styling.
    
    Custom classification scheme for Resume Explorer:
    - ownership: Person possesses/has something (hasJob, hasSkill, etc.)
    - organizational: Connections to organizations
    - usage: Application/use of skills or technology
    - hierarchical: Taxonomy relationships (SKOS)
    - typing: RDF type declarations
    - other: Uncategorized relationships
    """
```

---

#### In Summary- 

The edge types are hand-coded classifications based on the relationship vocabulary. When the system sees `hasSkill`, it automatically tags it as *"ownership"*. When it sees `hiringOrganization`, it tags it as *"organizational"*.

It's like having a filing system where every document (relationship) gets sorted into one of 6 folders (edge types) based on its content: OWNERSHIP, ORGANIZATIONAL, USAGE, HIERARCHICAL, TYPING, OTHER.

The classification is purely for visualization purposes ("for styling"):
  - Line 383-393: Maps edge types to colors
  - Line 395-401: Maps edge types to line widths

 Why These Categories?

  These categories were chosen to:
  - Visually distinguish different types of relationships in the graph (different colors)
  - Semantically group relationships that have similar meanings
  - Help understandabilit of the resume at a glance