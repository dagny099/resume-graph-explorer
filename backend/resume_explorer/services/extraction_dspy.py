"""
DSPy-based Resume Extraction Module

Experimental extraction pipeline using DSPy for structured entity extraction.
Provides advanced reasoning patterns and graceful fallback to simple prompts.
"""

import dspy
from typing import Dict, List, Optional, Any
import json
from dataclasses import asdict

from ..models import Person, Job, Skill, Education, Certification, Organization
from ..utils.logger import logger


class ExtractResumeEntities(dspy.Signature):
    """
    Extract structured entities from resume text following SKOS schema.

    Uses hybrid vocabulary (ESCO + schema.org + custom RE namespace).
    Make sure organization IDs are stable and reused between the
    organizations list and any jobs/education that reference them.
    """

    resume_text: str = dspy.InputField(
        desc="Full resume text including contact info, work history, education, skills"
    )

    person: dict = dspy.OutputField(
        desc="Person entity following schema:Person format with name, email, phone, location, summary"
    )

    jobs: list = dspy.OutputField(
        desc="List of job positions (schema:JobPosting) with title, company, dates, location, description, skills_used. organization_id MUST point to an id from the organizations list; prefer ids like org-{kebab-case-company-name} and reuse them across all jobs."
    )

    skills: list = dspy.OutputField(
        desc="List of skills (esco:Skill) with label, category (Technical/Soft/Domain), proficiency_level, years_experience"
    )

    education: list = dspy.OutputField(
        desc="List of education records (schema:EducationalOccupationalCredential) with degree_type, field_of_study, institution, dates, gpa. institution_id MUST reuse an id from the organizations list (use org-{kebab-case-institution-name})."
    )

    certifications: list = dspy.OutputField(
        desc="List of certifications (RE:Certification) with name, issuing_organization, issue_date, expiration_date, credential_id"
    )

    organizations: list = dspy.OutputField(
        desc="List of organizations (schema:Organization) mentioned - companies, institutions with name, org_type, location, website. Provide a stable id for each (org-{kebab-case-name}) and ensure jobs/education reference these ids."
    )

    reasoning: str = dspy.OutputField(
        desc="Explanation of extraction decisions, ambiguities resolved, and confidence assessments"
    )


class ExtractSkillHierarchy(dspy.Signature):
    """
    Build SKOS hierarchical relationships for extracted skills.

    Creates broader/narrower/related concept relationships.
    """

    skills: list = dspy.InputField(
        desc="List of extracted skill labels"
    )

    skill_hierarchy: dict = dspy.OutputField(
        desc="Dictionary mapping skill labels to their broader_concepts, narrower_concepts, and related_concepts"
    )

    esco_mappings: dict = dspy.OutputField(
        desc="Dictionary mapping skill labels to ESCO skill URIs where applicable"
    )


class ResumeExtractionModule(dspy.Module):
    """
    DSPy module for resume entity extraction with reasoning.

    Uses Chain of Thought for structured extraction and hierarchical reasoning.
    """

    def __init__(self):
        super().__init__()
        self.extract_entities = dspy.ChainOfThought(ExtractResumeEntities)
        self.extract_hierarchy = dspy.ChainOfThought(ExtractSkillHierarchy)

    def forward(self, resume_text: str) -> Dict[str, Any]:
        """
        Extract entities from resume with reasoning.

        Args:
            resume_text: Full resume text

        Returns:
            Dictionary with extracted entities and reasoning
        """
        logger.info("Starting DSPy resume extraction")

        # Step 1: Extract base entities
        extraction_result = self.extract_entities(resume_text=resume_text)

        # Step 2: Build skill hierarchy
        skills = extraction_result.skills
        if skills:
            skill_labels = [s.get('label', s.get('name', '')) for s in skills if isinstance(s, dict)]
            if skill_labels:
                hierarchy_result = self.extract_hierarchy(skills=skill_labels)

                # Enrich skills with hierarchy and ESCO mappings
                for skill in skills:
                    if isinstance(skill, dict):
                        skill_label = skill.get('label', skill.get('name', ''))
                        if skill_label in hierarchy_result.skill_hierarchy:
                            skill.update(hierarchy_result.skill_hierarchy[skill_label])
                        if skill_label in hierarchy_result.esco_mappings:
                            skill['skos_uri'] = hierarchy_result.esco_mappings[skill_label]

        return {
            'person': extraction_result.person,
            'jobs': extraction_result.jobs,
            'skills': skills,
            'education': extraction_result.education,
            'certifications': extraction_result.certifications,
            'organizations': extraction_result.organizations,
            'reasoning': extraction_result.reasoning,
        }


class SimplifiedExtractor:
    """
    Fallback extraction using simple prompts without DSPy.

    Used when DSPy is disabled or unavailable.
    """

    EXTRACTION_PROMPT = """You are a resume parser that extracts structured information.

Organization ID rules:
- Build the organizations array first.
- For every organization, set an id using "org-{{kebab-case-organization-name}}". Example: "OpenAI" -> "org-openai".
- Use those exact ids in jobs.organization_id and education.institution_id. Never invent ids that are not present in the organizations array.
- Do NOT use template strings like org-{{uuid}} or org-{{uuid1}}. If no name is available, fall back to a short, unique id such as org-company-1.

Extract the following entities from the resume:

1. PERSON: Name, email, phone, location, professional summary
2. JOBS: For each position, extract:
   - Job title
   - Company name
   - Start date and end date (YYYY-MM-DD format, or null if not specified, use "Present" for current)
   - Location
   - Description/responsibilities
   - Skills and technologies mentioned (as list of strings)
   - Achievements (as list of strings)

3. EDUCATION: For each degree:
   - Degree type (PhD, MS, BS, etc.)
   - Field of study
   - Institution name
   - Start date and end date (YYYY-MM-DD format)
   - GPA (if mentioned)

4. CERTIFICATIONS: For each certification:
   - Name
   - Issuing organization
   - Issue date
   - Expiration date (if applicable)
   - Credential ID (if provided)

5. SKILLS: All mentioned skills categorized as:
   - Technical skills (programming, tools, frameworks)
   - Domain skills (data science, machine learning, etc.)
   - Soft skills (leadership, communication, etc.)

   For each skill include:
   - label (skill name)
   - category (Technical, Soft, or Domain)
   - proficiency_level (if mentioned: Expert, Intermediate, Beginner)
   - years_experience (if mentioned)

6. ORGANIZATIONS: List all companies and institutions mentioned with:
   - name
   - org_type (Company, University, Non-profit, etc.)
   - location (if mentioned)
   - website (if mentioned)

Return ONLY valid JSON following this exact schema:
{{
  "person": {{
    "name": "...",
    "email": "...",
    "phone": "...",
    "location": "...",
    "summary": "..."
  }},
  "jobs": [
    {{
      "title": "...",
      "organization_id": "org-openai",
      "start_date": "YYYY-MM-DD",
      "end_date": "YYYY-MM-DD or null",
      "is_current": false,
      "location": "...",
      "description": "...",
      "skills_used": ["skill1", "skill2"],
      "technologies_used": ["tech1", "tech2"],
      "achievements": ["achievement1"]
    }}
  ],
  "skills": [
    {{
      "label": "Python",
      "category": "Technical",
      "proficiency_level": "Expert",
      "years_experience": 5.0
    }}
  ],
  "education": [
    {{
      "degree_type": "PhD",
      "field_of_study": "...",
      "institution_id": "org-mit",
      "start_date": "YYYY-MM-DD",
      "end_date": "YYYY-MM-DD",
      "gpa": 3.9
    }}
  ],
  "certifications": [
    {{
      "name": "...",
      "issuing_organization": "...",
      "issue_date": "YYYY-MM-DD",
      "expiration_date": "YYYY-MM-DD or null",
      "credential_id": "..."
    }}
  ],
  "organizations": [
    {{
      "id": "org-openai",
      "name": "OpenAI",
      "org_type": "Company",
      "location": "San Francisco, CA",
      "website": "https://openai.com"
    }}
  ]
}}

Resume text:
---
{resume_text}
---

Return ONLY the JSON, no additional text."""

    def __init__(self, llm_backend):
        """
        Initialize simplified extractor.

        Args:
            llm_backend: LLMBackend instance for generation
        """
        self.llm_backend = llm_backend

    def extract(self, resume_text: str) -> Dict[str, Any]:
        """
        Extract entities using simple prompt.

        Args:
            resume_text: Full resume text

        Returns:
            Dictionary with extracted entities
        """
        logger.info("Starting simplified extraction (non-DSPy)")

        prompt = self.EXTRACTION_PROMPT.format(resume_text=resume_text)

        try:
            response = self.llm_backend.generate(
                prompt=prompt,
                temperature=0.1,  # Low temperature for structured output
                max_tokens=4000
            )

            # Parse JSON response
            # Remove markdown code blocks if present
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]

            result = json.loads(response.strip())

            logger.info(f"Simplified extraction complete: {len(result.get('jobs', []))} jobs, "
                       f"{len(result.get('skills', []))} skills")

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"LLM response: {response[:500]}...")

            # Return empty structure
            return {
                'person': {},
                'jobs': [],
                'skills': [],
                'education': [],
                'certifications': [],
                'organizations': []
            }
        except Exception as e:
            logger.error(f"Extraction error: {e}")
            raise


def create_extraction_pipeline(llm_backend, use_dspy: bool = True) -> Any:
    """
    Factory function to create extraction pipeline.

    Args:
        llm_backend: LLMBackend instance
        use_dspy: Whether to use DSPy module (default True)

    Returns:
        ResumeExtractionModule or SimplifiedExtractor
    """
    if use_dspy:
        try:
            # Configure DSPy with LLM backend
            from .llm_client import DSPyLMAdapter
            dspy_lm = DSPyLMAdapter(backend=llm_backend)
            dspy.settings.configure(lm=dspy_lm)

            logger.info("Using DSPy extraction pipeline")
            return ResumeExtractionModule()

        except Exception as e:
            logger.warning(f"DSPy initialization failed, falling back to simplified extractor: {e}")
            return SimplifiedExtractor(llm_backend)
    else:
        logger.info("Using simplified extraction pipeline")
        return SimplifiedExtractor(llm_backend)


__all__ = [
    'ExtractResumeEntities',
    'ExtractSkillHierarchy',
    'ResumeExtractionModule',
    'SimplifiedExtractor',
    'create_extraction_pipeline',
]
