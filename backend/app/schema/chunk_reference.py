"""
ChunkReference Schemas

Pydantic schemas for cross-reference operations including:
- Creating references during ingestion
- Resolving references to chunk IDs
- Querying the reference graph during retrieval
- Statistics and reporting
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# === ENUMS (mirrored from models) ===

class ReferenceType:
    """Reference type constants"""
    DEFINITION = "definition"
    SEE_ALSO = "see_also"
    SUBJECT_TO = "subject_to"
    EXCEPTION = "exception"
    PENALTY = "penalty"
    TIME_LIMIT = "time_limit"
    THRESHOLD = "threshold"
    PROCEDURE = "procedure"
    LEGISLATION = "legislation"
    EXAMPLE = "example"
    SUPERSEDES = "supersedes"
    AMENDED_BY = "amended_by"


class ReferenceStrength:
    """Reference strength constants"""
    REQUIRED = "required"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"


# === BASE SCHEMAS ===

class ChunkReferenceBase(BaseModel):
    """Base schema with common reference fields"""
    
    reference_type: str = Field(
        ...,
        description="Type: definition, see_also, subject_to, exception, penalty, etc."
    )
    reference_strength: str = Field(
        default="recommended",
        description="Importance: required, recommended, optional"
    )
    reference_text: str = Field(
        ...,
        max_length=200,
        description="The reference as it appears: 'VATREG02150' or 'Section 3.4'"
    )
    reference_context: Optional[str] = Field(
        None,
        description="Surrounding text: 'see VATREG02150 for definition of taxable turnover'"
    )
    target_section_id: Optional[str] = Field(
        None,
        description="Target section ID for later resolution: 'VATREG02150'"
    )


# === CREATE/UPDATE SCHEMAS ===

class ChunkReferenceCreate(ChunkReferenceBase):
    """Schema for creating a new chunk reference"""
    
    source_chunk_id: str = Field(..., description="The chunk containing the reference")
    target_chunk_id: Optional[str] = Field(
        None,
        description="The referenced chunk (null if not yet resolved)"
    )
    is_resolved: bool = Field(default=False)


class ChunkReferenceUpdate(BaseModel):
    """Schema for updating a chunk reference (mainly for resolution)"""
    
    target_chunk_id: Optional[str] = None
    is_resolved: Optional[bool] = None
    reference_strength: Optional[str] = None


# === RESPONSE SCHEMAS ===

class ChunkReferenceResponse(ChunkReferenceBase):
    """Schema for returning a chunk reference"""
    
    id: str
    source_chunk_id: str
    target_chunk_id: Optional[str]
    is_resolved: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = {
        "from_attributes": True
    }


class ChunkReferenceWithContext(ChunkReferenceResponse):
    """Reference with additional context from related chunks"""
    
    source_section_id: Optional[str] = Field(None, description="Section ID of source chunk")
    source_citable_reference: Optional[str] = Field(None, description="Citation of source")
    target_citable_reference: Optional[str] = Field(None, description="Citation of target")


# === GRAPH QUERY SCHEMAS ===

class ReferenceExpansionRequest(BaseModel):
    """Request to expand references for retrieval"""
    
    chunk_ids: List[str] = Field(..., description="Initial chunk IDs to expand from")
    max_depth: int = Field(
        default=1, 
        ge=1, 
        le=3, 
        description="How many hops to follow (1=direct refs, 2=refs of refs)"
    )
    include_strength: List[str] = Field(
        default=["required", "recommended"],
        description="Which reference strengths to include"
    )
    max_total_chunks: int = Field(
        default=10, 
        ge=1, 
        le=20,
        description="Maximum total chunks to return"
    )


class ReferenceExpansionResult(BaseModel):
    """Result of reference expansion"""
    
    primary_chunk_ids: List[str] = Field(..., description="Original query chunks")
    referenced_chunk_ids: List[str] = Field(..., description="Chunks found via references")
    reference_chain: List[ChunkReferenceResponse] = Field(
        default=[],
        description="The references that were followed"
    )
    total_chunks: int


class UnresolvedReference(BaseModel):
    """An unresolved reference that needs manual review or later resolution"""
    
    id: str
    source_chunk_id: str
    source_section_id: Optional[str] = None
    reference_text: str
    target_section_id: Optional[str] = None
    reference_context: Optional[str] = None
    
    model_config = {
        "from_attributes": True
    }


# === STATISTICS SCHEMAS ===

class ReferenceStats(BaseModel):
    """Statistics about the reference graph"""
    
    total_references: int
    resolved_references: int
    unresolved_references: int
    references_by_type: Dict[str, int] = {}
    references_by_strength: Dict[str, int] = {}
    chunks_with_outgoing: int
    chunks_with_incoming: int


class ReferenceGraphSummary(BaseModel):
    """Summary of the reference graph for a document or topic"""
    
    total_chunks: int
    chunks_with_references: int
    total_references: int
    most_referenced_chunks: List[Dict[str, Any]] = []  # [{chunk_id, section_id, incoming_count}]
    most_referencing_chunks: List[Dict[str, Any]] = []  # [{chunk_id, section_id, outgoing_count}]
