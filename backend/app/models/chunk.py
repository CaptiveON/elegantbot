"""
DocumentChunk Model

Stores individual chunks of documents with full metadata for:
- Retrieval filtering in Pinecone
- Audit trail and precise citation
- Compliance tracking
- Cross-reference handling

Updated for Phase 1.1: Added precise citation fields (section_id, citable_reference)
and cross-reference tracking (defined_terms_used/provided, reference flags).
"""

from sqlalchemy import Column, String, DateTime, Integer, Text, Float, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import uuid
import enum
from app.database import Base


class TopicPrimary(str, enum.Enum):
    """Primary tax/guidance topics"""
    VAT = "VAT"
    CORPORATION_TAX = "Corporation_Tax"
    INCOME_TAX = "Income_Tax"
    PAYE = "PAYE"
    NATIONAL_INSURANCE = "National_Insurance"
    CAPITAL_GAINS = "Capital_Gains"
    INHERITANCE_TAX = "Inheritance_Tax"
    MTD = "MTD"  # Making Tax Digital
    COMPANY_FILING = "Company_Filing"
    RD_TAX_CREDITS = "RD_Tax_Credits"
    HMRC_SERVICE = "HMRC_Service"  # Contact, appeals, processes
    SELF_ASSESSMENT = "Self_Assessment"
    OTHER = "Other"


class ContentType(str, enum.Enum):
    """Type of content in the chunk"""
    FACTUAL = "factual"
    PROCEDURAL = "procedural"
    EXPLANATORY = "explanatory"
    DEFINITION = "definition"  # Added for chunks that define terms
    EXAMPLE = "example"
    WARNING = "warning"
    DEADLINE = "deadline"
    CONTACT_INFO = "contact_info"
    PROCESS = "process"
    THRESHOLD = "threshold"  # Added for threshold/limit content
    PENALTY = "penalty"  # Added for penalty-related content


class ServiceCategory(str, enum.Enum):
    """HMRC service categories for guidance navigation"""
    HMRC_CONTACT = "hmrc_contact"
    HMRC_PROCESS = "hmrc_process"
    HMRC_APPEAL = "hmrc_appeal"
    HMRC_ACCOUNT = "hmrc_account"
    NONE = "none"  # Pure tax compliance content


class DocumentChunk(Base):
    """
    Individual chunk with full metadata for retrieval and audit.
    
    Metadata is stored both here (PostgreSQL) and in Pinecone for filtering.
    Chunks are split at legal/structural boundaries (sections, clauses, paragraphs)
    rather than arbitrary token limits for precise citation and complete context.
    """
    __tablename__ = "document_chunks"
    
    # === PRIMARY KEY ===
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # === FOREIGN KEY TO SOURCE DOCUMENT ===
    document_id = Column(String, ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # === CHUNK CONTENT ===
    content = Column(Text, nullable=False)
    chunk_summary = Column(Text, nullable=True)  # LLM-generated summary
    
    # === SOURCE ATTRIBUTION (denormalized for fast access) ===
    source_url = Column(String, nullable=False)
    source_authority = Column(String, nullable=False)
    section_title = Column(String, nullable=True)
    heading_path = Column(String, nullable=True)  # e.g., "VAT Guide > Registration > Thresholds"
    
    # === PRECISE CITATION FIELDS (for legal/clause-level chunking) ===
    section_id = Column(
        String(100), nullable=True, index=True,
        comment="Section identifier e.g., 'VATREG02200' or '3.2'"
    )
    paragraph_number = Column(
        String(50), nullable=True,
        comment="Paragraph within section e.g., 'Para 1', 'Clause (a)'"
    )
    citable_reference = Column(
        String(500), nullable=True,
        comment="Full human-readable citation e.g., 'HMRC VAT Registration Manual, VATREG02200, Para 1'"
    )
    
    # === CLASSIFICATION METADATA ===
    topic_primary = Column(SQLEnum(TopicPrimary), nullable=False)
    topic_secondary = Column(JSONB, nullable=True, default=list)  # Array of secondary topics
    business_types = Column(JSONB, nullable=True, default=list)  # ["sole_trader", "limited_company", etc.]
    content_type = Column(SQLEnum(ContentType), nullable=False)
    service_category = Column(SQLEnum(ServiceCategory), default=ServiceCategory.NONE)
    reliability_tier = Column(Integer, nullable=False)
    
    # === TEMPORAL METADATA (inherited from document) ===
    publication_date = Column(DateTime, nullable=True)
    last_updated = Column(DateTime, nullable=True)
    effective_from = Column(DateTime, nullable=True)
    tax_year = Column(String, nullable=True)
    
    # === RETRIEVAL HINTS (extracted by rule-based processing) ===
    threshold_values = Column(JSONB, nullable=True, default=list)  # [90000, 85000, etc.]
    threshold_type = Column(String, nullable=True)  # "vat_registration", "mtd_threshold", etc.
    keywords = Column(JSONB, nullable=True, default=list)  # For hybrid search
    form_references = Column(JSONB, nullable=True, default=list)  # ["SA100", "CT600", etc.]
    deadlines_mentioned = Column(JSONB, nullable=True, default=list)  # Extracted deadline dates
    applies_to_tax_years = Column(JSONB, nullable=True, default=list)  # ["2024-25", "2025-26"]
    
    # === CROSS-REFERENCE TRACKING ===
    defined_terms_used = Column(
        JSONB, nullable=True, default=list,
        comment="Terms used in this chunk that are defined elsewhere e.g., ['taxable turnover', 'input tax']"
    )
    defined_terms_provided = Column(
        JSONB, nullable=True, default=list,
        comment="Terms that this chunk defines e.g., ['taxable turnover']"
    )
    has_outgoing_references = Column(
        Boolean, default=False,
        comment="True if this chunk references other chunks"
    )
    has_incoming_references = Column(
        Boolean, default=False,
        comment="True if other chunks reference this chunk"
    )
    
    # === STRUCTURED CONTENT LINKING ===
    contains_table = Column(
        Boolean, default=False,
        comment="True if this chunk contains a structured table"
    )
    contains_formula = Column(
        Boolean, default=False,
        comment="True if this chunk contains a calculation formula"
    )
    contains_decision_tree = Column(
        Boolean, default=False,
        comment="True if this chunk contains a decision tree/flowchart"
    )
    contains_deadline = Column(
        Boolean, default=False,
        comment="True if this chunk contains structured deadline info"
    )
    contains_example = Column(
        Boolean, default=False,
        comment="True if this chunk contains a worked example"
    )
    contains_contact = Column(
        Boolean, default=False,
        comment="True if this chunk contains contact information"
    )
    contains_condition_list = Column(
        Boolean, default=False,
        comment="True if this chunk contains a legal condition list"
    )
    structured_content_types = Column(
        JSONB, nullable=True, default=list,
        comment="List of structured content types in this chunk: ['table', 'formula', etc.]"
    )
    
    # === COMPLIANCE FLAGS ===
    requires_professional_advice = Column(Boolean, default=False)
    deadline_sensitive = Column(Boolean, default=False)
    penalty_relevant = Column(Boolean, default=False)
    
    # === CHUNK POSITION (for context and ordering) ===
    chunk_index = Column(Integer, nullable=False)
    total_chunks_in_doc = Column(Integer, nullable=False)
    char_start = Column(Integer, nullable=True)
    char_end = Column(Integer, nullable=True)
    
    # === VECTOR STORE TRACKING ===
    pinecone_id = Column(String, nullable=True, unique=True)  # ID in Pinecone
    embedding_model = Column(String, nullable=True)
    embedded_at = Column(DateTime, nullable=True)
    
    # === STANDARD TIMESTAMPS ===
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # === RELATIONSHIPS ===
    document = relationship("SourceDocument", back_populates="chunks")
    
    condition_lists = relationship("StructuredConditionList",back_populates="chunk",cascade="all, delete-orphan")
    contacts = relationship("StructuredContact",back_populates="chunk", cascade="all, delete-orphan")
    examples = relationship("StructuredExample",back_populates="chunk", cascade="all, delete-orphan")
    deadlines = relationship("StructuredDeadline",back_populates="chunk", cascade="all, delete-orphan")
    decisiontrees = relationship("StructuredDecisionTree",back_populates="chunk", cascade="all, delete-orphan")
    formulas = relationship("StructuredFormula",back_populates="chunk", cascade="all, delete-orphan")
    tables = relationship("StructuredTable",back_populates="chunk", cascade="all, delete-orphan")
   
    
    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, section_id={self.section_id}, topic={self.topic_primary})>"
    
    def to_pinecone_metadata(self) -> dict:
        """
        Convert chunk metadata to Pinecone-compatible format.
        Pinecone has limits on metadata size and types.
        """
        metadata = {
            # Source attribution
            "document_id": self.document_id,
            "source_url": self.source_url,
            "source_authority": self.source_authority,
            "section_title": self.section_title or "",
            "heading_path": self.heading_path or "",
            
            # Precise citation fields
            "section_id": self.section_id or "",
            "paragraph_number": self.paragraph_number or "",
            "citable_reference": self.citable_reference or "",
            
            # Classification
            "topic_primary": self.topic_primary.value if self.topic_primary else "Other",
            "topic_secondary": self.topic_secondary or [],
            "business_types": self.business_types or [],
            "content_type": self.content_type.value if self.content_type else "factual",
            "service_category": self.service_category.value if self.service_category else "none",
            "reliability_tier": self.reliability_tier,
            
            # Temporal
            "tax_year": self.tax_year or "",
            "publication_date": self.publication_date.isoformat() if self.publication_date else "",
            
            # Retrieval hints
            "threshold_values": self.threshold_values or [],
            "keywords": self.keywords or [],
            "form_references": self.form_references or [],
            "applies_to_tax_years": self.applies_to_tax_years or [],
            
            # Cross-reference flags (useful for retrieval expansion)
            "has_outgoing_references": self.has_outgoing_references,
            "has_incoming_references": self.has_incoming_references,
            
            # Structured content flags (useful for precise data retrieval)
            "contains_table": self.contains_table,
            "contains_formula": self.contains_formula,
            "contains_decision_tree": self.contains_decision_tree,
            "contains_deadline": self.contains_deadline,
            "contains_example": self.contains_example,
            "contains_contact": self.contains_contact,
            "structured_content_types": self.structured_content_types or [],
            
            # Compliance flags
            "requires_professional_advice": self.requires_professional_advice,
            "deadline_sensitive": self.deadline_sensitive,
            "penalty_relevant": self.penalty_relevant,
            
            # Position
            "chunk_index": self.chunk_index
        }
        
        # Remove empty values to save space in Pinecone
        return {k: v for k, v in metadata.items() if v is not None and v != "" and v != []}
