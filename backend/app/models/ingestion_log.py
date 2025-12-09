# Tracks ingestion pipeline runs for audit and monitoring.
# Records what was ingested, when, and any errors encountered.

from sqlalchemy import Column, String, DateTime, Integer, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import uuid
from enum import StrEnum
from app.database import Base


class IngestionRunStatus(StrEnum):
    # Status of an ingestion run
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"


class IngestionLog(Base):
    # Tracks each ingestion pipeline run.
    # Useful for debugging, monitoring, and audit compliance.
    
    __tablename__ = "ingestion_logs"
    
    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Run identification
    run_name = Column(String, nullable=True)  # Optional descriptive name
    source_type = Column(String, nullable=False)  # "gov_uk", "hmrc_manual", etc.
    
    # Status tracking
    status = Column(SQLEnum(IngestionRunStatus), default=IngestionRunStatus.STARTED)
    started_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)
    
    # Statistics
    documents_found = Column(Integer, default=0)
    documents_processed = Column(Integer, default=0)
    documents_created = Column(Integer, default=0)
    documents_updated = Column(Integer, default=0)
    documents_skipped = Column(Integer, default=0)
    documents_failed = Column(Integer, default=0)
    
    chunks_created = Column(Integer, default=0)
    chunks_embedded = Column(Integer, default=0)
    
    # Configuration used
    config = Column(JSONB, nullable=True)  # Store ingestion config for reproducibility
    
    # Errors and warnings
    errors = Column(JSONB, default=list)  # List of error messages
    warnings = Column(JSONB, default=list)  # List of warning messages
    
    # Cost tracking (for LLM calls)
    total_tokens_used = Column(Integer, default=0)
    estimated_cost_usd = Column(String, nullable=True)  # Store as string for precision
    
    # Standard timestamps
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<IngestionLog(id={self.id}, source={self.source_type}, status={self.status})>"
    
    def add_error(self, error_message: str, document_url: str = None):
        # Add an error to the log
        if self.errors is None:
            self.errors = []
        self.errors.append({
            "timestamp": datetime.now().isoformat(),
            "message": error_message,
            "document_url": document_url
        })
    
    def add_warning(self, warning_message: str, document_url: str = None):
        # Add a warning to the log
        if self.warnings is None:
            self.warnings = []
        self.warnings.append({
            "timestamp": datetime.now().isoformat(),
            "message": warning_message,
            "document_url": document_url
        })