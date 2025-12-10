"""
Document Ingestion Services (Phase 2)

This package provides the complete pipeline for ingesting UK tax guidance
from GOV.UK and HMRC into our RAG system with enhanced structured content extraction.

Core Components:
- GovUKClient: Fetches documents from GOV.UK Content API
- ContentParser: Cleans HTML and extracts structured text
- SemanticChunker: Basic document chunking
- LegalChunker: Legal-aware chunking with citation generation (Phase 2)

Extractors (Phase 2):
- TableExtractor: Extracts structured tables (tax rates, penalties, etc.)
- FormulaExtractor: Extracts calculation formulas
- DeadlineExtractor: Extracts deadline information
- ContactExtractor: Extracts HMRC contact information
- ConditionExtractor: Extracts legal condition lists
- ExampleExtractor: Extracts worked examples
- ReferenceDetector: Detects cross-references
- MetadataExtractor: Extracts thresholds, tax years, forms, keywords

Pipelines:
- IngestionPipeline: Basic ingestion (Phase 1)
- EnhancedIngestionPipeline: Full extraction pipeline (Phase 2)

Quick Start (Phase 2):
    from app.services.ingestion import EnhancedIngestionPipeline
    from app.db.session import get_db
    
    db = next(get_db())
    pipeline = EnhancedIngestionPipeline(db)
    
    # Ingest with full extraction
    result = pipeline.ingest_url("/vat-registration")
    print(f"Created {result.chunks_created} chunks, {result.tables_extracted} tables")
"""

# Core components
from .gov_uk_client import (
    GovUKClient,
    GovUKDocument,
    GovUKContentAPIError
)

from .content_parser import (
    ContentParser,
    ParsedDocument,
    ContentSection
)

from .chunker import (
    SemanticChunker,
    Chunk,
    ChunkingConfig
)

# Legal-aware chunker (Phase 2)
from .legal_chunker import (
    LegalChunker,
    LegalChunk,
    LegalChunkingConfig,
    LegalContentType
)

# Extractors (Phase 2)
from .extractors import (
    BaseExtractor,
    ExtractionResult,
    TableExtractor,
    ExtractedTable,
    FormulaExtractor,
    ExtractedFormula,
    DeadlineExtractor,
    ExtractedDeadline,
    ContactExtractor,
    ExtractedContact,
    ConditionExtractor,
    ExtractedConditionList,
    ExampleExtractor,
    ExtractedExample,
    ReferenceDetector,
    DetectedReference,
    MetadataExtractor,
    ExtractedMetadata,
)

# Basic Pipeline (Phase 1)
from .pipeline import (
    IngestionPipeline,
    IngestionMode,
    PipelineConfig,
    PipelineResult,
    IngestionResult
)

# Enhanced Pipeline (Phase 2)
from .enhanced_pipeline import (
    EnhancedIngestionPipeline,
    EnhancedPipelineConfig,
    EnhancedPipelineResult,
    EnhancedIngestionResult,
)

__all__ = [
    # === Core Components ===
    "GovUKClient",
    "GovUKDocument", 
    "GovUKContentAPIError",
    "ContentParser",
    "ParsedDocument",
    "ContentSection",
    
    # === Basic Chunker ===
    "SemanticChunker",
    "Chunk",
    "ChunkingConfig",
    
    # === Legal Chunker (Phase 2) ===
    "LegalChunker",
    "LegalChunk",
    "LegalChunkingConfig",
    "LegalContentType",
    
    # === Extractors (Phase 2) ===
    "BaseExtractor",
    "ExtractionResult",
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
    
    # === Basic Pipeline (Phase 1) ===
    "IngestionPipeline",
    "IngestionMode",
    "PipelineConfig",
    "PipelineResult",
    "IngestionResult",
    
    # === Enhanced Pipeline (Phase 2) ===
    "EnhancedIngestionPipeline",
    "EnhancedPipelineConfig",
    "EnhancedPipelineResult",
    "EnhancedIngestionResult",
]
