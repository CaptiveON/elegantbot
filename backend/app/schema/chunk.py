"""
Chunk Schemas

Pydantic schemas for DocumentChunk validation and serialization.

Updated for Phase 1.1: Added precise citation fields (section_id, citable_reference)
and cross-reference tracking (defined_terms_used/provided, reference flags).
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


# === ENUMS (mirrored from models for schema usage) ===

class TopicPrimary(str, Enum):
    VAT = "VAT"
    CORPORATION_TAX = "Corporation_Tax"
    INCOME_TAX = "Income_Tax"
    PAYE = "PAYE"
    NATIONAL_INSURANCE = "National_Insurance"
    CAPITAL_GAINS = "Capital_Gains"
    INHERITANCE_TAX = "Inheritance_Tax"
    MTD = "MTD"
    COMPANY_FILING = "Company_Filing"
    RD_TAX_CREDITS = "RD_Tax_Credits"
    HMRC_SERVICE = "HMRC_Service"
    SELF_ASSESSMENT = "Self_Assessment"
    OTHER = "Other"


class ContentType(str, Enum):
    FACTUAL = "factual"
    PROCEDURAL = "procedural"
    EXPLANATORY = "explanatory"
    DEFINITION = "definition"
    EXAMPLE = "example"
    WARNING = "warning"
    DEADLINE = "deadline"
    CONTACT_INFO = "contact_info"
    PROCESS = "process"
    THRESHOLD = "threshold"
    PENALTY = "penalty"


class ServiceCategory(str, Enum):
    HMRC_CONTACT = "hmrc_contact"
    HMRC_PROCESS = "hmrc_process"
    HMRC_APPEAL = "hmrc_appeal"
    HMRC_ACCOUNT = "hmrc_account"
    NONE = "none"


# === METADATA SUB-SCHEMAS ===

class SourceAttribution(BaseModel):
    """Source attribution for a chunk"""
    url: str
    authority: str
    section_title: Optional[str] = None
    heading_path: Optional[str] = None
    section_id: Optional[str] = None
    paragraph_number: Optional[str] = None
    citable_reference: Optional[str] = None


class TemporalMetadata(BaseModel):
    """Temporal metadata for a chunk"""
    publication_date: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    effective_from: Optional[datetime] = None
    tax_year: Optional[str] = None


class ClassificationMetadata(BaseModel):
    """Classification metadata for a chunk"""
    topic_primary: Optional[TopicPrimary] = None #LLM Populated
    topic_secondary: List[str] = []
    business_types: List[str] = []
    content_type: Optional[ContentType] = None #LLM Populated
    service_category: ServiceCategory = ServiceCategory.NONE
    reliability_tier: int = Field(ge=1, le=3)


class RetrievalHints(BaseModel):
    """Hints to improve retrieval accuracy"""
    threshold_values: List[int] = []
    threshold_type: Optional[str] = None
    keywords: List[str] = []
    form_references: List[str] = []
    deadlines_mentioned: List[str] = []
    applies_to_tax_years: List[str] = []


class ComplianceFlags(BaseModel):
    """Compliance-related flags"""
    requires_professional_advice: bool = False
    deadline_sensitive: bool = False
    penalty_relevant: bool = False


class ReferenceTracking(BaseModel):
    """Cross-reference tracking for a chunk"""
    defined_terms_used: List[str] = []
    defined_terms_provided: List[str] = []
    has_outgoing_references: bool = False
    has_incoming_references: bool = False


class ChunkPosition(BaseModel):
    """Position of chunk within document"""
    chunk_index: int
    total_chunks: int
    char_start: Optional[int] = None
    char_end: Optional[int] = None


# === CREATE/UPDATE/RESPONSE SCHEMAS ===

class ChunkCreate(BaseModel):
    """Schema for creating a new chunk"""
    document_id: str
    content: str
    chunk_summary: Optional[str] = None
    
    # Source attribution
    source_url: str
    source_authority: str
    section_title: Optional[str] = None
    heading_path: Optional[str] = None
    
    # Precise citation fields
    section_id: Optional[str] = Field(None, description="Section identifier e.g., 'VATREG02200'")
    paragraph_number: Optional[str] = Field(None, description="Paragraph within section")
    citable_reference: Optional[str] = Field(None, description="Full human-readable citation")
    
    # Classification
    topic_primary: Optional[TopicPrimary] = None #LLM Populated
    topic_secondary: List[str] = []
    business_types: List[str] = []
    content_type: Optional[ContentType] = None #LLM Populated
    service_category: ServiceCategory = ServiceCategory.NONE
    reliability_tier: int = Field(ge=1, le=3, default=2)
    
    # Temporal
    publication_date: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    effective_from: Optional[datetime] = None
    tax_year: Optional[str] = None
    
    # Retrieval hints
    threshold_values: List[int] = []
    threshold_type: Optional[str] = None
    keywords: List[str] = []
    form_references: List[str] = []
    deadlines_mentioned: List[str] = []
    applies_to_tax_years: List[str] = []
    
    # Cross-reference tracking
    defined_terms_used: List[str] = Field(default_factory=list)
    defined_terms_provided: List[str] = Field(default_factory=list)
    has_outgoing_references: bool = Field(default=False)
    has_incoming_references: bool = Field(default=False)
    
    # Structured content flags
    contains_table: bool = Field(default=False)
    contains_formula: bool = Field(default=False)
    contains_decision_tree: bool = Field(default=False)
    contains_deadline: bool = Field(default=False)
    contains_example: bool = Field(default=False)
    contains_contact: bool = Field(default=False)
    contains_condition_list: bool = Field(default=False)
    structured_content_types: List[str] = Field(default_factory=list)
    
    # Compliance flags
    requires_professional_advice: bool = False
    deadline_sensitive: bool = False
    penalty_relevant: bool = False
    
    # Position
    chunk_index: int
    total_chunks_in_doc: int
    char_start: Optional[int] = None
    char_end: Optional[int] = None


class ChunkUpdate(BaseModel):
    """Schema for updating a chunk"""
    chunk_summary: Optional[str] = None
    
    # Precise citation fields
    section_id: Optional[str] = None
    paragraph_number: Optional[str] = None
    citable_reference: Optional[str] = None
    
    # Classification
    topic_primary: Optional[TopicPrimary] = None
    topic_secondary: Optional[List[str]] = None
    business_types: Optional[List[str]] = None
    content_type: Optional[ContentType] = None
    service_category: Optional[ServiceCategory] = None
    
    # Retrieval hints
    keywords: Optional[List[str]] = None
    threshold_values: Optional[List[int]] = None
    threshold_type: Optional[str] = None
    form_references: Optional[List[str]] = None
    deadlines_mentioned: Optional[List[str]] = None
    applies_to_tax_years: Optional[List[str]] = None
    
    # Cross-reference tracking
    defined_terms_used: Optional[List[str]] = None
    defined_terms_provided: Optional[List[str]] = None
    has_outgoing_references: Optional[bool] = None
    has_incoming_references: Optional[bool] = None
    
    # Structured content flags
    contains_table: Optional[bool] = None
    contains_formula: Optional[bool] = None
    contains_decision_tree: Optional[bool] = None
    contains_deadline: Optional[bool] = None
    contains_example: Optional[bool] = None
    contains_contact: Optional[bool] = None
    contains_condition_list: Optional[bool] = None
    structured_content_types: Optional[List[str]] = None
    
    # Compliance flags
    requires_professional_advice: Optional[bool] = None
    deadline_sensitive: Optional[bool] = None
    penalty_relevant: Optional[bool] = None
    
    # Vector store
    pinecone_id: Optional[str] = None
    embedding_model: Optional[str] = None
    embedded_at: Optional[datetime] = None


class ChunkResponse(BaseModel):
    """Full chunk response"""
    id: str
    document_id: str
    content: str
    chunk_summary: Optional[str] = None
    
    # Source attribution
    source_url: str
    source_authority: str
    section_title: Optional[str] = None
    heading_path: Optional[str] = None
    
    # Precise citation fields
    section_id: Optional[str] = None
    paragraph_number: Optional[str] = None
    citable_reference: Optional[str] = None
    
    # Classification
    topic_primary: TopicPrimary
    topic_secondary: List[str] = []
    business_types: List[str] = []
    content_type: ContentType
    service_category: ServiceCategory
    reliability_tier: int
    
    # Temporal
    publication_date: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    effective_from: Optional[datetime] = None
    tax_year: Optional[str] = None
    
    # Retrieval hints
    threshold_values: List[int] = []
    keywords: List[str] = []
    form_references: List[str] = []
    applies_to_tax_years: List[str] = []
    
    # Cross-reference tracking
    defined_terms_used: List[str] = Field(default_factory=list)
    defined_terms_provided: List[str] = Field(default_factory=list)
    has_outgoing_references: bool = False
    has_incoming_references: bool = False
    
    # Structured content flags
    contains_table: bool = False
    contains_formula: bool = False
    contains_decision_tree: bool = False
    contains_deadline: bool = False
    contains_example: bool = False
    contains_contact: bool = False
    contains_condition_list: bool = False
    structured_content_types: List[str] = Field(default_factory=list)
    
    # Compliance flags
    requires_professional_advice: bool
    deadline_sensitive: bool
    penalty_relevant: bool
    
    # Position
    chunk_index: int
    total_chunks_in_doc: int
    
    # Vector store
    pinecone_id: Optional[str] = None
    embedded_at: Optional[datetime] = None
    
    created_at: datetime
    updated_at: datetime
    
    model_config = {
        "from_attributes": True
    }


class ChunkSummaryResponse(BaseModel):
    """Lightweight chunk summary for listings"""
    id: str
    document_id: str
    source_url: str
    section_id: Optional[str] = None
    section_title: Optional[str] = None
    topic_primary: TopicPrimary
    content_type: ContentType
    chunk_index: int
    has_embedding: bool
    has_outgoing_references: bool = False
    has_incoming_references: bool = False
    
    model_config = {
        "from_attributes": True
    }


class ChunkSearchResult(BaseModel):
    """Chunk returned from vector search with relevance scoring"""
    id: str
    content: str
    score: float  # Similarity score
    rerank_score: Optional[float] = None
    
    # Source for citation
    source_url: str
    source_authority: str
    section_title: Optional[str] = None
    heading_path: Optional[str] = None
    
    # Precise citation
    section_id: Optional[str] = None
    citable_reference: Optional[str] = None
    
    # Classification
    topic_primary: str
    content_type: str
    reliability_tier: int
    
    # Reference flags (for potential expansion)
    has_outgoing_references: bool = False
    
    # Compliance
    requires_professional_advice: bool


class ChunkListResponse(BaseModel):
    """Response for listing chunks with pagination"""
    total: int
    page: int
    page_size: int
    document_id: str
    chunks: List[ChunkSummaryResponse]


class ChunkWithReferences(BaseModel):
    """Chunk with its resolved references for complete context"""
    chunk: ChunkResponse
    outgoing_references: List["ChunkResponse"] = []
    reference_types: List[str] = []  # Type of each outgoing reference
