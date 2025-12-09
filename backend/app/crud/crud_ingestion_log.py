"""
Ingestion Log CRUD Operations

Database operations for IngestionLog model.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.models.ingestion_log import IngestionLog, IngestionRunStatus


def create_ingestion_log(
    db: Session,
    source_type: str,
    run_name: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> IngestionLog:
    """Create a new ingestion log entry"""
    log = IngestionLog(
        source_type=source_type,
        run_name=run_name,
        config=config,
        status=IngestionRunStatus.STARTED,
        started_at=datetime.now()
    )
    
    db.add(log)
    db.commit()
    db.refresh(log)
    
    return log


def get_ingestion_log(db: Session, log_id: str) -> Optional[IngestionLog]:
    """Get an ingestion log by ID"""
    return db.query(IngestionLog).filter(IngestionLog.id == log_id).first()


def get_ingestion_logs(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    source_type: Optional[str] = None,
    status: Optional[IngestionRunStatus] = None
) -> List[IngestionLog]:
    """Get ingestion logs with optional filtering"""
    query = db.query(IngestionLog)
    
    if source_type:
        query = query.filter(IngestionLog.source_type == source_type)
    if status:
        query = query.filter(IngestionLog.status == status)
    
    return query.order_by(IngestionLog.started_at.desc()).offset(skip).limit(limit).all()


def update_ingestion_log_status(
    db: Session,
    log_id: str,
    status: IngestionRunStatus,
    error_message: Optional[str] = None
) -> Optional[IngestionLog]:
    """Update ingestion log status"""
    log = get_ingestion_log(db, log_id)
    if not log:
        return None
    
    log.status = status
    if status in [IngestionRunStatus.COMPLETED, IngestionRunStatus.COMPLETED_WITH_ERRORS, IngestionRunStatus.FAILED]:
        log.completed_at = datetime.now()
    
    if error_message:
        log.add_error(error_message)
    
    log.updated_at = datetime.now()
    db.commit()
    db.refresh(log)
    
    return log


def update_ingestion_log_stats(
    db: Session,
    log_id: str,
    documents_found: Optional[int] = None,
    documents_processed: Optional[int] = None,
    documents_created: Optional[int] = None,
    documents_updated: Optional[int] = None,
    documents_skipped: Optional[int] = None,
    documents_failed: Optional[int] = None,
    chunks_created: Optional[int] = None,
    chunks_embedded: Optional[int] = None,
    total_tokens_used: Optional[int] = None,
    estimated_cost_usd: Optional[str] = None
) -> Optional[IngestionLog]:
    """Update ingestion log statistics"""
    log = get_ingestion_log(db, log_id)
    if not log:
        return None
    
    if documents_found is not None:
        log.documents_found = documents_found
    if documents_processed is not None:
        log.documents_processed = documents_processed
    if documents_created is not None:
        log.documents_created = documents_created
    if documents_updated is not None:
        log.documents_updated = documents_updated
    if documents_skipped is not None:
        log.documents_skipped = documents_skipped
    if documents_failed is not None:
        log.documents_failed = documents_failed
    if chunks_created is not None:
        log.chunks_created = chunks_created
    if chunks_embedded is not None:
        log.chunks_embedded = chunks_embedded
    if total_tokens_used is not None:
        log.total_tokens_used = total_tokens_used
    if estimated_cost_usd is not None:
        log.estimated_cost_usd = estimated_cost_usd
    
    log.updated_at = datetime.now()
    db.commit()
    db.refresh(log)
    
    return log


def increment_ingestion_stats(
    db: Session,
    log_id: str,
    documents_processed: int = 0,
    documents_created: int = 0,
    documents_updated: int = 0,
    documents_skipped: int = 0,
    documents_failed: int = 0,
    chunks_created: int = 0,
    chunks_embedded: int = 0,
    tokens_used: int = 0
) -> Optional[IngestionLog]:
    """Increment ingestion statistics (for progress tracking)"""
    log = get_ingestion_log(db, log_id)
    if not log:
        return None
    
    log.documents_processed += documents_processed
    log.documents_created += documents_created
    log.documents_updated += documents_updated
    log.documents_skipped += documents_skipped
    log.documents_failed += documents_failed
    log.chunks_created += chunks_created
    log.chunks_embedded += chunks_embedded
    log.total_tokens_used += tokens_used
    
    log.updated_at = datetime.now()
    db.commit()
    db.refresh(log)
    
    return log


def add_ingestion_error(
    db: Session,
    log_id: str,
    error_message: str,
    document_url: Optional[str] = None
) -> Optional[IngestionLog]:
    """Add an error to the ingestion log"""
    log = get_ingestion_log(db, log_id)
    if not log:
        return None
    
    log.add_error(error_message, document_url)
    log.updated_at = datetime.now()
    db.commit()
    db.refresh(log)
    
    return log


def add_ingestion_warning(
    db: Session,
    log_id: str,
    warning_message: str,
    document_url: Optional[str] = None
) -> Optional[IngestionLog]:
    """Add a warning to the ingestion log"""
    log = get_ingestion_log(db, log_id)
    if not log:
        return None
    
    log.add_warning(warning_message, document_url)
    log.updated_at = datetime.now()
    db.commit()
    db.refresh(log)
    
    return log


def get_latest_successful_ingestion(
    db: Session,
    source_type: str
) -> Optional[IngestionLog]:
    """Get the most recent successful ingestion for a source type"""
    return db.query(IngestionLog).filter(
        IngestionLog.source_type == source_type,
        IngestionLog.status.in_([IngestionRunStatus.COMPLETED, IngestionRunStatus.COMPLETED_WITH_ERRORS])
    ).order_by(IngestionLog.completed_at.desc()).first()