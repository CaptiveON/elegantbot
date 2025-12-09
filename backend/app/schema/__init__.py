"""
Schemas Package

Exports all Pydantic schemas for the UK Tax Compliance RAG system.
"""

# Original schemas
from .user import UserCreate, UserResponse
from .chat import (
    MessageCreate, 
    MessageResponse, 
    ChatResponse, 
    ChatSessionResponse, 
    ChatHistory, 
    ChatSessions
)
from .token import Token, TokenData

# Phase 1: Document schemas
from .document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentSummary,
    DocumentListResponse,
    DocumentStats
)

# Phase 1: Chunk schemas
from .chunk import (
    # Enums
    TopicPrimary,
    ContentType,
    ServiceCategory,
    
    # Sub-schemas
    SourceAttribution,
    TemporalMetadata,
    ClassificationMetadata,
    RetrievalHints,
    ComplianceFlags,
    ReferenceTracking,
    ChunkPosition,
    
    # Main schemas
    ChunkCreate,
    ChunkUpdate,
    ChunkResponse,
    ChunkSummaryResponse,
    ChunkSearchResult,
    ChunkListResponse,
    ChunkWithReferences
)

# Phase 1: Chunk Reference schemas
from .chunk_reference import (
    ReferenceType,
    ReferenceStrength,
    ChunkReferenceBase,
    ChunkReferenceCreate,
    ChunkReferenceUpdate,
    ChunkReferenceResponse,
    ChunkReferenceWithContext,
    ReferenceExpansionRequest,
    ReferenceExpansionResult,
    UnresolvedReference,
    ReferenceStats,
    ReferenceGraphSummary
)

# Phase 1: Metadata schemas
from .metadata import (
    QueryAuditData,
    PineconeMetadata,
    SourceMetadata,
    AuditMetadata,
    LLMClassificationResult,
    RuleBasedExtractionResult,
    AutomatedExtractionResult,
    PopulatedMetadata
)

# Phase 1.2: Structured Content schemas
from .structured_content import (
    # Enums
    TableType,
    FormulaType,
    DecisionCategory,
    DeadlineType,
    DeadlineFrequency,
    ContactType,
    ExampleCategory,
    ConditionLogic,
    
    # Table schemas
    StructuredTableCreate,
    StructuredTableUpdate,
    StructuredTableResponse,
    TableLookupRequest,
    TableRangeLookupRequest,
    TableLookupResponse,
    
    # Formula schemas
    StructuredFormulaCreate,
    StructuredFormulaUpdate,
    StructuredFormulaResponse,
    
    # Decision Tree schemas
    StructuredDecisionTreeCreate,
    StructuredDecisionTreeUpdate,
    StructuredDecisionTreeResponse,
    DecisionTreeTraversalRequest,
    DecisionTreeTraversalResponse,
    
    # Deadline schemas
    StructuredDeadlineCreate,
    StructuredDeadlineUpdate,
    StructuredDeadlineResponse,
    DeadlineCalculationRequest,
    DeadlineCalculationResponse,
    
    # Example schemas
    StructuredExampleCreate,
    StructuredExampleUpdate,
    StructuredExampleResponse,
    
    # Contact schemas
    StructuredContactCreate,
    StructuredContactUpdate,
    StructuredContactResponse,
    
    # Condition List schemas
    StructuredConditionListCreate,
    StructuredConditionListUpdate,
    StructuredConditionListResponse,
    ConditionEvaluationRequest,
    ConditionEvaluationResponse,
    
    # Aggregate schemas
    StructuredContentSummary,
    StructuredContentStats
)


__all__ = [
    # Original
    "UserCreate", 
    "UserResponse", 
    "MessageCreate", 
    "MessageResponse", 
    "ChatResponse", 
    "ChatSessionResponse", 
    "ChatHistory", 
    "ChatSessions",
    "Token",
    "TokenData",
    
    # Document
    "DocumentCreate",
    "DocumentUpdate",
    "DocumentResponse",
    "DocumentSummary",
    "DocumentListResponse",
    "DocumentStats",
    
    # Chunk enums
    "TopicPrimary",
    "ContentType",
    "ServiceCategory",
    
    # Chunk sub-schemas
    "SourceAttribution",
    "TemporalMetadata",
    "ClassificationMetadata",
    "RetrievalHints",
    "ComplianceFlags",
    "ReferenceTracking",
    "ChunkPosition",
    
    # Chunk main schemas
    "ChunkCreate",
    "ChunkUpdate",
    "ChunkResponse",
    "ChunkSummaryResponse",
    "ChunkSearchResult",
    "ChunkListResponse",
    "ChunkWithReferences",
    
    # Chunk Reference
    "ReferenceType",
    "ReferenceStrength",
    "ChunkReferenceBase",
    "ChunkReferenceCreate",
    "ChunkReferenceUpdate",
    "ChunkReferenceResponse",
    "ChunkReferenceWithContext",
    "ReferenceExpansionRequest",
    "ReferenceExpansionResult",
    "UnresolvedReference",
    "ReferenceStats",
    "ReferenceGraphSummary",
    
    # Metadata
    "QueryAuditData",
    "PineconeMetadata",
    "SourceMetadata",
    "AuditMetadata",
    "LLMClassificationResult",
    "RuleBasedExtractionResult",
    "AutomatedExtractionResult",
    "PopulatedMetadata",
    
    # Structured Content enums
    "TableType",
    "FormulaType",
    "DecisionCategory",
    "DeadlineType",
    "DeadlineFrequency",
    "ContactType",
    "ExampleCategory",
    "ConditionLogic",
    
    # Structured Content schemas
    "StructuredTableCreate",
    "StructuredTableUpdate",
    "StructuredTableResponse",
    "TableLookupRequest",
    "TableRangeLookupRequest",
    "TableLookupResponse",
    "StructuredFormulaCreate",
    "StructuredFormulaUpdate",
    "StructuredFormulaResponse",
    "StructuredDecisionTreeCreate",
    "StructuredDecisionTreeUpdate",
    "StructuredDecisionTreeResponse",
    "DecisionTreeTraversalRequest",
    "DecisionTreeTraversalResponse",
    "StructuredDeadlineCreate",
    "StructuredDeadlineUpdate",
    "StructuredDeadlineResponse",
    "DeadlineCalculationRequest",
    "DeadlineCalculationResponse",
    "StructuredExampleCreate",
    "StructuredExampleUpdate",
    "StructuredExampleResponse",
    "StructuredContactCreate",
    "StructuredContactUpdate",
    "StructuredContactResponse",
    "StructuredConditionListCreate",
    "StructuredConditionListUpdate",
    "StructuredConditionListResponse",
    "ConditionEvaluationRequest",
    "ConditionEvaluationResponse",
    "StructuredContentSummary",
    "StructuredContentStats",
]
