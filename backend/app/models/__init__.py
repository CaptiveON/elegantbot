"""
Models Package

Exports all SQLAlchemy models and enums for the UK Tax Compliance RAG system.
"""

from app.database import Base, engine

# Original models
from .user import User
from .chat import ChatSession, Message

# Phase 1: Data Foundation models
from .document import (
    SourceDocument,
    AuthorityType,
    DocumentType,
    ReliabilityTier,
    IngestionStatus
)

from .chunk import (
    DocumentChunk,
    TopicPrimary,
    ContentType,
    ServiceCategory
)

from .chunk_reference import (
    ChunkReference,
    ReferenceType,
    ReferenceStrength
)

from .ingestion_log import (
    IngestionLog,
    IngestionRunStatus
)

from .audit_log import QueryAuditLog

# Phase 1.2: Structured Content models
from .structured_content import (
    StructuredTable,
    StructuredFormula,
    StructuredDecisionTree,
    StructuredDeadline,
    StructuredExample,
    StructuredContact,
    StructuredConditionList,
    TableType,
    FormulaType,
    DecisionCategory,
    DeadlineType,
    DeadlineFrequency,
    ContactType,
    ExampleCategory,
    ConditionLogic
)


# Uncomment to recreate all tables (use with caution!)
# Base.metadata.drop_all(bind=engine)
# Base.metadata.create_all(bind=engine)


__all__ = [
    # Base
    "Base",
    "engine",
    
    # Original models
    "User",
    "ChatSession",
    "Message",
    
    # Document models
    "SourceDocument",
    "AuthorityType",
    "DocumentType",
    "ReliabilityTier",
    "IngestionStatus",
    
    # Chunk models
    "DocumentChunk",
    "TopicPrimary",
    "ContentType",
    "ServiceCategory",
    
    # Reference models
    "ChunkReference",
    "ReferenceType",
    "ReferenceStrength",
    
    # Ingestion models
    "IngestionLog",
    "IngestionRunStatus",
    
    # Audit models
    "QueryAuditLog",
    
    # Structured Content models
    "StructuredTable",
    "StructuredFormula",
    "StructuredDecisionTree",
    "StructuredDeadline",
    "StructuredExample",
    "StructuredContact",
    "StructuredConditionList",
    
    # Structured Content enums
    "TableType",
    "FormulaType",
    "DecisionCategory",
    "DeadlineType",
    "DeadlineFrequency",
    "ContactType",
    "ExampleCategory",
    "ConditionLogic",
]
