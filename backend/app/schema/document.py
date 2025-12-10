# Pydantic schemas for SourceDocument validation and serialization.

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# Re-export enums for schema usage
class AuthorityType(str, Enum):
    GOV_UK = "GOV_UK"
    HMRC_MANUAL = "HMRC_MANUAL"
    UK_LEGISLATION = "UK_LEGISLATION"
    COMPANIES_HOUSE = "COMPANIES_HOUSE"
    ACAS = "ACAS"
    OTHER_OFFICIAL = "OTHER_OFFICIAL"


class DocumentType(str, Enum):
    GUIDANCE = "guidance"
    MANUAL = "manual"
    LEGISLATION = "legislation"
    FORM_INSTRUCTIONS = "form_instructions"
    SERVICE_INFO = "service_info"
    CONTACT_INFO = "contact_info"


class IngestionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Create Schemas
class DocumentCreate(BaseModel):
    # Schema for creating a new source document
    url: str
    authority: AuthorityType
    document_type: DocumentType
    reliability_tier: int = Field(ge=1, le=3, default=2)
    title: str
    parent_document: Optional[str] = None
    section_hierarchy: Optional[List[str]] = None  # JSON string
    publication_date: Optional[datetime] = None
    last_updated_source: Optional[datetime] = None
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None
    tax_year: Optional[str] = None


class DocumentUpdate(BaseModel):
    # Schema for updating a source document
    title: Optional[str] = None
    parent_document: Optional[str] = None
    section_hierarchy: Optional[List[str]] = None
    publication_date: Optional[datetime] = None
    last_updated_source: Optional[datetime] = None
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None
    tax_year: Optional[str] = None
    ingestion_status: Optional[IngestionStatus] = None
    content_hash: Optional[str] = None
    total_chunks: Optional[int] = None


class DocumentResponse(BaseModel):
    # Schema for document response
    id: str
    url: str
    authority: AuthorityType
    document_type: DocumentType
    reliability_tier: int
    title: str
    parent_document: Optional[str] = None
    section_hierarchy: Optional[str] = None
    publication_date: Optional[datetime] = None
    last_updated_source: Optional[datetime] = None
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None
    tax_year: Optional[str] = None
    ingestion_status: IngestionStatus
    ingested_at: Optional[datetime] = None
    last_verified_at: Optional[datetime] = None
    content_hash: Optional[str] = None
    total_chunks: int
    created_at: datetime
    updated_at: datetime
    
    model_config = {
        "from_attributes": True
    }


class DocumentSummary(BaseModel):
    # Lightweight document summary for listings
    id: str
    url: str
    title: str
    authority: AuthorityType
    document_type: DocumentType
    ingestion_status: IngestionStatus
    total_chunks: int
    last_updated_source: Optional[datetime] = None
    
    model_config = {
        "from_attributes": True
    }


class DocumentListResponse(BaseModel):
    # Response for listing documents with pagination
    total: int
    page: int
    page_size: int
    documents: List[DocumentSummary]


class DocumentStats(BaseModel):
    # Statistics about ingested documents
    total_documents: int
    total_chunks: int
    by_authority: dict  # {"GOV_UK": 50, "HMRC_MANUAL": 30, ...}
    by_status: dict  # {"completed": 70, "pending": 10, ...}
    by_topic: dict  # {"VAT": 25, "Corporation_Tax": 15, ...}
    last_ingestion: Optional[datetime] = None