
# SourceDocument

# This is metadata of source documents ingested from GOV.UK/HMRC Manuals etc...
# A record for each document before chunking.

from sqlalchemy import Column, String, Integer, Text, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import StrEnum, IntEnum
import uuid
from app.database import Base

class AuthorityType(StrEnum):
    # Types of Authorities
    GOV_UK = "GOV_UK"
    HMRC_MANUAL = "HMRC_MANUAL"
    UK_LEGISLATION = "UK_LEGISLATION"
    COMPANIES_HOUSE = "COMPANIES_HOUSE"
    ACAS = "ACAS"
    OTHER_OFFICIAL = "OTHER_OFFICIAL"
    
class DocumentType(StrEnum):
    # Types of Documents
    GUIDANCE = "guidance"
    MANUAL = "manual"
    LEGISLATION = "legislation"
    FORM_INSTRUCTIONS = "form_instructions"
    SERVICE_INFO = "service_info"
    CONTACT_INFO = "contact_info"
    NEWS = "NEWS"
    
class ReliabilityTier(IntEnum):
    # Reliability tiers for source documents
    # Tier 1: Primary legislation, official HMRC manuals
    # Tier 2: GOV.UK guidance, official forms
    # Tier 3: Professional body guidance (ICAEW, CIOT)
    TIER_1 = 1
    TIER_2 = 2
    TIER_3 = 3
    
class IngestionStatus(StrEnum):
    # Document Ingestion Status
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    
class SourceDocument(Base):
    # Master record for each document to be referred
    # conataining complete metadata for audit compliance
    __tablename__ = "source_documents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # source identification
    url = Column(String, unique=True, nullable=False, index=True)
    authority = Column(SQLEnum(AuthorityType),nullable=False)
    document_type = Column(SQLEnum(DocumentType), nullable=False)
    reliability_tier = Column(SQLEnum(ReliabilityTier), nullable=False, default=2)
    
    # Document Metadata
    title = Column(String, nullable=False)
    parent_document = Column(String, nullable=True) #For Hierarical Documents
    section_hierarchy = Column(Text, nullable=True)
    
    # Metadata for audit compliance
    publication_date = Column(DateTime, nullable=True)
    last_updated_source = Column(DateTime, nullable=True)
    effective_from = Column(DateTime, nullable=True)
    effective_until = Column(DateTime, nullable=True)
    tax_year = Column(String, nullable=True)
    
    # Ingestion tracking
    ingestion_status = Column(SQLEnum(IngestionStatus), default=IngestionStatus.PENDING)
    ingested_at = Column(DateTime, nullable=True)
    last_verified_at = Column(DateTime, nullable=True)
    
    # Content integrity
    content_hash = Column(String, nullable=True)  # SHA256 hash for change detection
    raw_content_path = Column(String, nullable=True)  # S3 path for raw HTML backup
    
    # Number of chunks divided into
    total_chunks = Column(Integer, default=0)
    
    # Standard Timestamp - Document Uploaded First
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationship to Chunks
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    # Relation to StructuredConditionLists
    condition_lists = relationship("StructuredConditionList",back_populates="document", cascade="all, delete-orphan")
    contacts = relationship("StructuredContact",back_populates="document", cascade="all, delete-orphan")
    examples = relationship("StructuredExample",back_populates="document", cascade="all, delete-orphan")
    deadlines = relationship("StructuredDeadline",back_populates="document", cascade="all, delete-orphan")
    decisiontrees = relationship("StructuredDecisionTree",back_populates="document", cascade="all, delete-orphan")
    formulas = relationship("StructuredFormula",back_populates="document", cascade="all, delete-orphan")
    tables = relationship("StructuredTable",back_populates="document",cascade="all, delete-orphan")
    
    # Overrided Representation of SourceDocument Object for logging
    def __repr__(self):
        return f"<SourceDocument(id = {self.id}, title = {self.title}, authority = {self.authority}, source = {self.url})>"
    
    
    
    
    # Handle redirection of api URLs to automatically
    # going to the new URL and grab data