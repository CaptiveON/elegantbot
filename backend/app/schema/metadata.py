# Comprehensive metadata structures used throughout the ingestion pipeline.
# These schemas define the complete metadata format for audit-friendly retrieval.

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class PopulatedMetadata(BaseModel):
    """
    Complete metadata structure for a chunk.
    This is the full schema populated by the metadata pipeline:
    1. Automated extraction (URLs, dates, structure)
    2. Rule-based extraction (thresholds, tax years, forms)
    3. LLM classification (topics, business types, complexity)
    """
    
    # Level 1: Source Document Metadata
    document_id: str
    source: "SourceMetadata"
    temporal: "TemporalMetadata"
    classification: "ClassificationData"
    audit: "AuditMetadata"
    
    # Level 2: Chunk-Specific Metadata
    chunk_position: "ChunkPositionData"
    retrieval_hints: "RetrievalHintsData"
    compliance_flags: "ComplianceFlagsData"
    chunk_summary: Optional[str] = None


class SourceMetadata(BaseModel):
    # Source attribution metadata
    url: str
    authority: str  # GOV_UK, HMRC_MANUAL, etc.
    authority_type: str  # government_official, professional_body, etc.
    document_title: str
    parent_document: Optional[str] = None
    section_title: Optional[str] = None
    section_hierarchy: List[str] = []
    heading_path: Optional[str] = None


class TemporalMetadata(BaseModel):
    # Temporal tracking metadata
    publication_date: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None
    tax_year: Optional[str] = None
    ingestion_timestamp: datetime
    last_verified: Optional[datetime] = None


class ClassificationData(BaseModel):
    # Classification metadata
    document_type: str  # guidance, manual, legislation, etc.
    topic_primary: str
    topic_secondary: List[str] = []
    business_types: List[str] = []
    content_type: str  # factual, procedural, explanatory, etc.
    service_category: Optional[str] = None
    reliability_tier: int = Field(ge=1, le=3)
    complexity_level: Optional[str] = None  # simple, moderate, complex


class AuditMetadata(BaseModel):
    # Audit trail metadata
    ingestion_method: str  # gov_uk_api, web_scrape, manual
    content_hash: str  # SHA256 hash
    raw_file_path: Optional[str] = None  # S3/storage path
    classification_model: Optional[str] = None  # Model used for LLM classification
    classification_timestamp: Optional[datetime] = None


class ChunkPositionData(BaseModel):
    # Chunk position within document
    index: int
    total_chunks: int
    char_start: Optional[int] = None
    char_end: Optional[int] = None


class RetrievalHintsData(BaseModel):
    # Data to improve retrieval accuracy
    threshold_values: List[int] = []
    threshold_type: Optional[str] = None
    keywords: List[str] = []
    form_references: List[str] = []
    deadlines_mentioned: List[str] = []
    applies_to_tax_years: List[str] = []


class ComplianceFlagsData(BaseModel):
    # Compliance-related flags
    requires_professional_advice: bool = False
    deadline_sensitive: bool = False
    penalty_relevant: bool = False


# Update forward references
PopulatedMetadata.model_rebuild()


class LLMClassificationResult(BaseModel):
    # Result from LLM classification
    topic_primary: str
    topic_secondary: List[str] = []
    business_types: List[str] = []
    content_type: str
    complexity_level: str = "moderate"
    requires_professional_advice: bool = False
    summary: str


class RuleBasedExtractionResult(BaseModel):
    # Result from rule-based extraction
    tax_years: List[str] = []
    threshold_values: List[int] = []
    threshold_type: Optional[str] = None
    form_references: List[str] = []
    deadlines_mentioned: List[str] = []
    penalty_relevant: bool = False
    deadline_sensitive: bool = False


class AutomatedExtractionResult(BaseModel):
    # Result from automated extraction
    url: str
    authority: str
    authority_type: str
    document_title: str
    publication_date: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    section_hierarchy: List[str] = []
    heading_path: Optional[str] = None
    content_hash: str
    reliability_tier: int


class PineconeMetadata(BaseModel):
    # Metadata format for Pinecone storage.
    # Optimized for filtering and within Pinecone's metadata limits.
    
    # Source (for citation)
    document_id: str
    source_url: str
    source_authority: str
    section_title: str = ""
    heading_path: str = ""
    
    # Classification (for filtering)
    topic_primary: str
    topic_secondary: List[str] = []
    business_types: List[str] = []
    content_type: str
    service_category: str = "none"
    reliability_tier: int
    
    # Temporal (for filtering)
    tax_year: str = ""
    publication_date: str = ""  # ISO format string
    
    # Retrieval hints (for filtering)
    threshold_values: List[int] = []
    keywords: List[str] = []
    form_references: List[str] = []
    applies_to_tax_years: List[str] = []
    
    # Compliance flags (for filtering)
    requires_professional_advice: bool = False
    deadline_sensitive: bool = False
    penalty_relevant: bool = False
    
    # Position
    chunk_index: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        # Convert to dictionary for Pinecone upsert
        return self.model_dump()


class QueryAuditData(BaseModel):
    # Complete audit data for a query-response pair.
    # Used to create QueryAuditLog records.
    
    # Query info
    original_query: str
    processed_query: Optional[str] = None
    detected_intent: Optional[str] = None
    
    # Retrieval info
    chunks_retrieved: List[Dict[str, Any]] = []
    filters_applied: Optional[Dict[str, Any]] = None
    
    # Response info
    response_text: str
    citations: List[Dict[str, Any]] = []
    disclaimer_type: Optional[str] = None
    confidence_score: Optional[float] = None
    
    # Model info
    embedding_model: Optional[str] = None
    generation_model: Optional[str] = None
    prompt_template_version: Optional[str] = None
    
    # Performance
    total_tokens: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    estimated_cost_usd: Optional[str] = None