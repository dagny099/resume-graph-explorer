"""
Resume Explorer Services Module

Exports LLM client, extraction pipeline, and related services.
"""

from .llm_client import (
    LLMBackend,
    ClaudeBackend,
    OpenAIBackend,
    OllamaBackend,
    LLMClient,
    create_llm_client,
    DSPyLMAdapter
)

from .extraction_dspy import (
    ExtractResumeEntities,
    ExtractSkillHierarchy,
    ResumeExtractionModule,
    SimplifiedExtractor,
    create_extraction_pipeline
)

from .resume_extractor import (
    ResumeExtractor,
    ExtractionEvent
)

from .entity_normalizer import (
    EntityNormalizer
)

__all__ = [
    # LLM backends
    'LLMBackend',
    'ClaudeBackend',
    'OpenAIBackend',
    'OllamaBackend',
    'LLMClient',
    'create_llm_client',
    'DSPyLMAdapter',

    # DSPy extraction
    'ExtractResumeEntities',
    'ExtractSkillHierarchy',
    'ResumeExtractionModule',
    'SimplifiedExtractor',
    'create_extraction_pipeline',

    # Resume extractor
    'ResumeExtractor',
    'ExtractionEvent',

    # Entity normalizer
    'EntityNormalizer'
]
