# Records every query and response for compliance and audit purposes.

from sqlalchemy import Column, String, DateTime, Integer, Text, Float, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import uuid
from app.database import Base


class QueryAuditLog(Base):
    # Complete audit trail for every tax assistant query.
    # Stores the full context: query, retrieval, response, and citations.
    
    __tablename__ = "query_audit_logs"
    
    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # User context (nullable for anonymous queries if allowed)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    session_id = Column(String, nullable=True, index=True)
    
    # Timestamps
    timestamp = Column(DateTime, default=datetime.now, index=True)
    
    # Query information
    original_query = Column(Text, nullable=False)
    processed_query = Column(Text, nullable=True)  # After preprocessing
    detected_intent = Column(String, nullable=True)  # "tax_compliance", "hmrc_service", etc.
    
    # Retrieval information
    chunks_retrieved = Column(JSONB, nullable=True)  # List of retrieved chunk info
    # Example structure:
    # [
    #   {
    #     "chunk_id": "uuid",
    #     "document_id": "uuid",
    #     "similarity_score": 0.94,
    #     "rerank_score": 0.97,
    #     "source_url": "https://...",
    #     "source_authority": "GOV_UK"
    #   }
    # ]
    
    filters_applied = Column(JSONB, nullable=True)  # Filters used in retrieval
    # Example: {"topic_primary": "VAT", "reliability_tier": [1, 2]}
    
    # Response information
    response_text = Column(Text, nullable=False)
    citations = Column(JSONB, nullable=True)  # Citations in the response
    # Example structure:
    # [
    #   {
    #     "chunk_id": "uuid",
    #     "source_url": "https://...",
    #     "source_title": "VAT Registration Guide",
    #     "quote_used": "You must register if..."
    #   }
    # ]
    
    disclaimer_type = Column(String, nullable=True)  # "standard", "professional_advice", etc.
    confidence_score = Column(Float, nullable=True)  # Model's confidence
    
    # Model information
    embedding_model = Column(String, nullable=True)
    generation_model = Column(String, nullable=True)
    prompt_template_version = Column(String, nullable=True)
    
    # Performance metrics
    total_tokens = Column(Integer, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    
    # Cost tracking
    estimated_cost_usd = Column(String, nullable=True)
    
    # Feedback (for future improvement)
    user_feedback = Column(String, nullable=True)  # "helpful", "not_helpful", etc.
    feedback_comment = Column(Text, nullable=True)
    
    # Standard timestamps
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<QueryAuditLog(id={self.id}, intent={self.detected_intent}, timestamp={self.timestamp})>"