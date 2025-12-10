"""
Structured Content Extractors

This package contains extractors for detecting and parsing structured content
from UK tax documents:

- TableExtractor: Detects and parses HTML tables into StructuredTable records
- FormulaExtractor: Detects formulas and calculation patterns
- DeadlineExtractor: Extracts deadline information
- ContactExtractor: Extracts HMRC contact information
- ConditionExtractor: Parses legal condition lists
- ExampleExtractor: Detects worked examples
- ReferenceDetector: Detects cross-references between documents
- MetadataExtractor: Extracts metadata (thresholds, tax years, forms)

Each extractor follows a common interface:
    extractor = TableExtractor()
    results = extractor.extract(html_content, text_content)

Results can then be converted to database records using the corresponding CRUD operations.
"""

from .base import BaseExtractor, ExtractionResult
from .table_extractor import TableExtractor, ExtractedTable
from .formula_extractor import FormulaExtractor, ExtractedFormula
from .deadline_extractor import DeadlineExtractor, ExtractedDeadline
from .contact_extractor import ContactExtractor, ExtractedContact
from .condition_extractor import ConditionExtractor, ExtractedConditionList
from .example_extractor import ExampleExtractor, ExtractedExample
from .reference_detector import ReferenceDetector, DetectedReference
from .metadata_extractor import MetadataExtractor, ExtractedMetadata

__all__ = [
    # Base
    "BaseExtractor",
    "ExtractionResult",
    
    # Extractors
    "TableExtractor",
    "ExtractedTable",
    "FormulaExtractor", 
    "ExtractedFormula",
    "DeadlineExtractor",
    "ExtractedDeadline",
    "ContactExtractor",
    "ExtractedContact",
    "ConditionExtractor",
    "ExtractedConditionList",
    "ExampleExtractor",
    "ExtractedExample",
    "ReferenceDetector",
    "DetectedReference",
    "MetadataExtractor",
    "ExtractedMetadata",
]
