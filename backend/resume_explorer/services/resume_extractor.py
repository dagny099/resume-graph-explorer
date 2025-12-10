"""
Resume Extractor Service

Main service for extracting structured entities from resume documents.
Supports streaming progress via WebSocket and multiple LLM providers.
"""

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, date
import uuid
import asyncio

from .extraction_dspy import create_extraction_pipeline
from .llm_client import LLMClient
from ..models import Person, Job, Skill, Education, Certification, Organization
from ..utils.logger import logger


class ExtractionEvent:
    """Event types for extraction progress."""
    STARTED = 'extraction_started'
    PROGRESS = 'extraction_progress'
    ENTITY_EXTRACTED = 'entity_extracted'
    COMPLETE = 'extraction_complete'
    ERROR = 'extraction_error'


class ResumeExtractor:
    """
    Main service for resume entity extraction.

    Features:
    - Multi-provider LLM support (Claude, OpenAI, Ollama)
    - DSPy and simplified extraction pipelines
    - WebSocket streaming for real-time progress
    - Automatic entity object creation
    - Error handling and recovery
    """

    def __init__(
        self,
        llm_client: LLMClient,
        event_emitter: Optional[Callable] = None,
        use_dspy: bool = True
    ):
        """
        Initialize resume extractor.

        Args:
            llm_client: Configured LLM client
            event_emitter: Optional callback for WebSocket events
            use_dspy: Whether to use DSPy module (default True)
        """
        self.llm_client = llm_client
        self.event_emitter = event_emitter
        self.use_dspy = use_dspy

        # Create extraction pipeline
        self.pipeline = create_extraction_pipeline(
            llm_backend=llm_client.backend,
            use_dspy=use_dspy
        )

        logger.info(f"ResumeExtractor initialized with {llm_client.backend.__class__.__name__}")

    def _emit_event(self, event_name: str, data: Dict[str, Any]):
        """Emit event via WebSocket if emitter is configured."""
        if self.event_emitter:
            try:
                self.event_emitter(event_name, data)
            except Exception as e:
                logger.warning(f"Event emission failed: {e}")

    async def extract_entities_async(
        self,
        resume_text: str,
        filename: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract entities from resume with async WebSocket streaming.

        Args:
            resume_text: Full resume text
            filename: Original filename
            session_id: Optional session ID for tracking

        Returns:
            Dictionary with entity objects and metadata
        """
        document_id = str(uuid.uuid4())

        # Emit started event
        self._emit_event(ExtractionEvent.STARTED, {
            'document_id': document_id,
            'filename': filename,
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        })

        try:
            # Run extraction (potentially long-running)
            logger.info(f"Extracting entities from {filename}")

            # Call pipeline (DSPy or simplified)
            if hasattr(self.pipeline, 'forward'):
                # DSPy module
                raw_result = self.pipeline.forward(resume_text=resume_text)
            elif hasattr(self.pipeline, 'extract'):
                # Simplified extractor
                raw_result = self.pipeline.extract(resume_text=resume_text)
            else:
                raise ValueError(f"Invalid pipeline type: {type(self.pipeline)}")

            # Emit progress after extraction
            self._emit_event(ExtractionEvent.PROGRESS, {
                'document_id': document_id,
                'stage': 'extraction_complete',
                'progress': 50
            })

            # Convert raw JSON to entity objects
            logger.info("Converting extracted data to entity objects")
            entities = self._convert_to_entities(raw_result, filename)

            # Emit entity extracted events
            for entity_type, entity_list in entities.items():
                if entity_type != 'metadata' and isinstance(entity_list, list):
                    self._emit_event(ExtractionEvent.ENTITY_EXTRACTED, {
                        'document_id': document_id,
                        'entity_type': entity_type,
                        'count': len(entity_list)
                    })

            # Emit progress after conversion
            self._emit_event(ExtractionEvent.PROGRESS, {
                'document_id': document_id,
                'stage': 'conversion_complete',
                'progress': 100
            })

            # Emit completion event
            self._emit_event(ExtractionEvent.COMPLETE, {
                'document_id': document_id,
                'filename': filename,
                'session_id': session_id,
                'entity_count': sum(
                    len(v) for k, v in entities.items()
                    if k != 'metadata' and isinstance(v, list)
                ),
                'timestamp': datetime.now().isoformat()
            })

            logger.info(f"Extraction complete for {filename}: "
                       f"person={entities.get('person', {}).get('name', 'N/A')}, "
                       f"jobs={len(entities.get('jobs', []))}, "
                       f"skills={len(entities.get('skills', []))}")

            return entities

        except Exception as e:
            logger.error(f"Extraction failed for {filename}: {e}", exc_info=True)

            # Emit error event
            self._emit_event(ExtractionEvent.ERROR, {
                'document_id': document_id,
                'filename': filename,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })

            raise

    def extract_entities(
        self,
        resume_text: str,
        filename: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synchronous wrapper for extract_entities_async.

        Args:
            resume_text: Full resume text
            filename: Original filename
            session_id: Optional session ID

        Returns:
            Dictionary with entity objects and metadata
        """
        # Run async function in event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.extract_entities_async(resume_text, filename, session_id)
        )

    def _convert_to_entities(
        self,
        raw_result: Dict[str, Any],
        source_filename: str
    ) -> Dict[str, Any]:
        """
        Convert raw extraction result to entity objects.

        Args:
            raw_result: Dictionary from extraction pipeline
            source_filename: Source document filename

        Returns:
            Dictionary with entity objects
        """
        # Create ID mappings for relationships
        org_id_map = {}  # Map organization names to IDs

        # 1. Create Organizations first (needed for Job and Education relationships)
        organizations = []
        for org_data in raw_result.get('organizations', []):
            org = Organization(
                id=org_data.get('id', str(uuid.uuid4())),
                label=org_data.get('name', ''),
                name=org_data.get('name', ''),
                org_type=org_data.get('org_type'),
                location=org_data.get('location'),
                website=org_data.get('website'),
                description=org_data.get('description'),
                source_doc=source_filename,
                confidence=org_data.get('confidence', 1.0)
            )
            organizations.append(org)
            org_id_map[org.name] = org.id

        # 2. Create Skills (needed for Job relationships)
        skills = []
        skill_id_map = {}
        for skill_data in raw_result.get('skills', []):
            skill = Skill(
                id=str(uuid.uuid4()),
                label=skill_data.get('label', skill_data.get('name', '')),
                category=skill_data.get('category'),
                proficiency_level=skill_data.get('proficiency_level'),
                years_experience=skill_data.get('years_experience'),
                broader_concepts=skill_data.get('broader_concepts', []),
                narrower_concepts=skill_data.get('narrower_concepts', []),
                related_concepts=skill_data.get('related_concepts', []),
                skos_uri=skill_data.get('skos_uri'),
                source_doc=source_filename,
                confidence=skill_data.get('confidence', 1.0)
            )
            skills.append(skill)
            skill_id_map[skill.label] = skill.id

        # 3. Create Jobs
        jobs = []
        for job_data in raw_result.get('jobs', []):
            # Map organization name to ID
            org_id = job_data.get('organization_id', '')
            if not org_id and 'company' in job_data:
                org_id = org_id_map.get(job_data['company'], '')

            # Map skill names to IDs
            skills_used = []
            for skill_name in job_data.get('skills_used', []):
                if skill_name in skill_id_map:
                    skills_used.append(skill_id_map[skill_name])

            job = Job(
                id=str(uuid.uuid4()),
                label=job_data.get('title', ''),
                title=job_data.get('title', ''),
                organization_id=org_id,
                start_date=self._parse_date(job_data.get('start_date')),
                end_date=self._parse_date(job_data.get('end_date')),
                is_current=job_data.get('is_current', False),
                location=job_data.get('location'),
                description=job_data.get('description'),
                skills_used=skills_used,
                technologies_used=job_data.get('technologies_used', []),
                achievements=job_data.get('achievements', []),
                source_doc=source_filename,
                confidence=job_data.get('confidence', 1.0)
            )
            jobs.append(job)

        # 4. Create Education
        education_list = []
        for edu_data in raw_result.get('education', []):
            # Map institution name to ID
            inst_id = edu_data.get('institution_id', '')
            if not inst_id and 'institution' in edu_data:
                inst_id = org_id_map.get(edu_data['institution'], '')

            education = Education(
                id=str(uuid.uuid4()),
                label=f"{edu_data.get('degree_type', '')} in {edu_data.get('field_of_study', '')}",
                degree_type=edu_data.get('degree_type', ''),
                field_of_study=edu_data.get('field_of_study'),
                institution_id=inst_id,
                start_date=self._parse_date(edu_data.get('start_date')),
                end_date=self._parse_date(edu_data.get('end_date')),
                is_current=edu_data.get('is_current', False),
                gpa=edu_data.get('gpa'),
                source_doc=source_filename,
                confidence=edu_data.get('confidence', 1.0)
            )
            education_list.append(education)

        # 5. Create Certifications
        certifications = []
        for cert_data in raw_result.get('certifications', []):
            cert = Certification(
                id=str(uuid.uuid4()),
                label=cert_data.get('name', ''),
                name=cert_data.get('name', ''),
                issuing_organization=cert_data.get('issuing_organization'),
                issue_date=self._parse_date(cert_data.get('issue_date')),
                expiration_date=self._parse_date(cert_data.get('expiration_date')),
                credential_id=cert_data.get('credential_id'),
                credential_url=cert_data.get('credential_url'),
                is_active=cert_data.get('is_active', True),
                source_doc=source_filename,
                confidence=cert_data.get('confidence', 1.0)
            )
            certifications.append(cert)

        # 6. Create Person
        person_data = raw_result.get('person', {})
        person = Person(
            id=str(uuid.uuid4()),
            label=person_data.get('name', ''),
            name=person_data.get('name', ''),
            email=person_data.get('email'),
            phone=person_data.get('phone'),
            location=person_data.get('location'),
            summary=person_data.get('summary'),
            jobs=[job.id for job in jobs],
            skills=[skill.id for skill in skills],
            education=[edu.id for edu in education_list],
            certifications=[cert.id for cert in certifications],
            source_doc=source_filename,
            confidence=person_data.get('confidence', 1.0)
        )

        return {
            'person': person,
            'jobs': jobs,
            'skills': skills,
            'education': education_list,
            'certifications': certifications,
            'organizations': organizations,
            'metadata': {
                'source_filename': source_filename,
                'extraction_timestamp': datetime.now().isoformat(),
                'reasoning': raw_result.get('reasoning', ''),
                'use_dspy': self.use_dspy
            }
        }

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """
        Parse date string to date object.

        Args:
            date_str: Date string in YYYY-MM-DD format or None

        Returns:
            date object or None
        """
        if not date_str or date_str == 'null' or date_str.lower() == 'present':
            return None

        try:
            # Try parsing YYYY-MM-DD format
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            try:
                # Try YYYY-MM format
                return datetime.strptime(date_str, '%Y-%m').date()
            except ValueError:
                try:
                    # Try YYYY format
                    return datetime.strptime(date_str, '%Y').date()
                except ValueError:
                    logger.warning(f"Could not parse date: {date_str}")
                    return None


__all__ = ['ResumeExtractor', 'ExtractionEvent']
