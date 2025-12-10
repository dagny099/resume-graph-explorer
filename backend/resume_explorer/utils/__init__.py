"""
Resume Explorer Utilities Module

Exports logger and document processing utilities.
"""

from .logger import logger
from .document_processor import DocumentProcessor

__all__ = [
    'logger',
    'DocumentProcessor'
]
