"""
Audit Log CRUD Operations

Database operations for QueryAuditLog model.
Critical for compliance tracking and audit trails.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from app.models.audit_log import QueryAuditLog
from app.schema.metadata import QueryAuditData


def create_audit_log(
    db: Session,
    audit_data: QueryAuditData,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> QueryAuditLog:
    """Create a new audit log entry"""
    log = QueryAuditLog(
        user_id=user_id,
        session_id=session_id,
        
        # Query info
        original_query=audit_data.original_query,
        processed_query=audit_data.processed_query,
        detected_intent=audit_data.detected_intent,
        
        # Retrieval info
        chunks_retrieved=audit_data.chunks_retrieved,
        filters_applied=audit_data.filters_applied,
        
        # Response info
        response_text=audit_data.response_text,
        citations=audit_data.citations,
        disclaimer_type=audit_data.disclaimer_type,
        confidence_score=audit_data.confidence_score,
        
        # Model info
        embedding_model=audit_data.embedding_model,
        generation_model=audit_data.generation_model,
        prompt_template_version=audit_data.prompt_template_version,
        
        # Performance
        total_tokens=audit_data.total_tokens,
        prompt_tokens=audit_data.prompt_tokens,
        completion_tokens=audit_data.completion_tokens,
        latency_ms=audit_data.latency_ms,
        estimated_cost_usd=audit_data.estimated_cost_usd
    )
    
    db.add(log)
    db.commit()
    db.refresh(log)
    
    return log


def get_audit_log(db: Session, log_id: str) -> Optional[QueryAuditLog]:
    """Get an audit log by ID"""
    return db.query(QueryAuditLog).filter(QueryAuditLog.id == log_id).first()


def get_audit_logs(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    intent: Optional[str] = None
) -> List[QueryAuditLog]:
    """Get audit logs with filtering"""
    query = db.query(QueryAuditLog)
    
    if user_id:
        query = query.filter(QueryAuditLog.user_id == user_id)
    if session_id:
        query = query.filter(QueryAuditLog.session_id == session_id)
    if start_date:
        query = query.filter(QueryAuditLog.timestamp >= start_date)
    if end_date:
        query = query.filter(QueryAuditLog.timestamp <= end_date)
    if intent:
        query = query.filter(QueryAuditLog.detected_intent == intent)
    
    return query.order_by(QueryAuditLog.timestamp.desc()).offset(skip).limit(limit).all()


def count_audit_logs(
    db: Session,
    user_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> int:
    """Count audit logs with filtering"""
    query = db.query(func.count(QueryAuditLog.id))
    
    if user_id:
        query = query.filter(QueryAuditLog.user_id == user_id)
    if start_date:
        query = query.filter(QueryAuditLog.timestamp >= start_date)
    if end_date:
        query = query.filter(QueryAuditLog.timestamp <= end_date)
    
    return query.scalar()


def update_audit_log_feedback(
    db: Session,
    log_id: str,
    feedback: str,
    comment: Optional[str] = None
) -> Optional[QueryAuditLog]:
    """Update audit log with user feedback"""
    log = get_audit_log(db, log_id)
    if not log:
        return None
    
    log.user_feedback = feedback
    log.feedback_comment = comment
    
    db.commit()
    db.refresh(log)
    
    return log


def get_audit_trail_for_query(db: Session, query_text: str) -> List[QueryAuditLog]:
    """
    Get audit trail for similar queries.
    Useful for investigating patterns or issues.
    """
    return db.query(QueryAuditLog).filter(
        QueryAuditLog.original_query.ilike(f"%{query_text}%")
    ).order_by(QueryAuditLog.timestamp.desc()).limit(50).all()


def get_audit_trail_for_document(db: Session, document_id: str) -> List[QueryAuditLog]:
    """
    Get all queries that referenced a specific document.
    Useful for impact analysis when documents are updated.
    """
    # This searches the JSONB chunks_retrieved field
    return db.query(QueryAuditLog).filter(
        QueryAuditLog.chunks_retrieved.cast(str).ilike(f"%{document_id}%")
    ).order_by(QueryAuditLog.timestamp.desc()).all()


def get_audit_stats(
    db: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """Get audit statistics for reporting"""
    if not start_date:
        start_date = datetime.now() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now()
    
    base_query = db.query(QueryAuditLog).filter(
        QueryAuditLog.timestamp >= start_date,
        QueryAuditLog.timestamp <= end_date
    )
    
    total_queries = base_query.count()
    
    # By intent
    by_intent = dict(
        db.query(QueryAuditLog.detected_intent, func.count(QueryAuditLog.id))
        .filter(
            QueryAuditLog.timestamp >= start_date,
            QueryAuditLog.timestamp <= end_date
        )
        .group_by(QueryAuditLog.detected_intent)
        .all()
    )
    
    # Average latency
    avg_latency = db.query(func.avg(QueryAuditLog.latency_ms)).filter(
        QueryAuditLog.timestamp >= start_date,
        QueryAuditLog.timestamp <= end_date,
        QueryAuditLog.latency_ms.isnot(None)
    ).scalar()
    
    # Total tokens
    total_tokens = db.query(func.sum(QueryAuditLog.total_tokens)).filter(
        QueryAuditLog.timestamp >= start_date,
        QueryAuditLog.timestamp <= end_date
    ).scalar() or 0
    
    # Feedback distribution
    feedback_dist = dict(
        db.query(QueryAuditLog.user_feedback, func.count(QueryAuditLog.id))
        .filter(
            QueryAuditLog.timestamp >= start_date,
            QueryAuditLog.timestamp <= end_date,
            QueryAuditLog.user_feedback.isnot(None)
        )
        .group_by(QueryAuditLog.user_feedback)
        .all()
    )
    
    # Professional advice warnings issued
    prof_advice_count = db.query(func.count(QueryAuditLog.id)).filter(
        QueryAuditLog.timestamp >= start_date,
        QueryAuditLog.timestamp <= end_date,
        QueryAuditLog.disclaimer_type == "professional_advice"
    ).scalar()
    
    return {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        "total_queries": total_queries,
        "by_intent": {k or "unknown": v for k, v in by_intent.items()},
        "average_latency_ms": round(avg_latency, 2) if avg_latency else None,
        "total_tokens_used": total_tokens,
        "feedback_distribution": {k or "none": v for k, v in feedback_dist.items()},
        "professional_advice_warnings": prof_advice_count
    }


def export_audit_logs(
    db: Session,
    start_date: datetime,
    end_date: datetime,
    user_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Export audit logs for compliance reporting.
    Returns a list of dictionaries suitable for CSV/JSON export.
    """
    logs = get_audit_logs(
        db,
        skip=0,
        limit=10000,  # Reasonable limit for export
        user_id=user_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return [
        {
            "id": log.id,
            "timestamp": log.timestamp.isoformat(),
            "user_id": log.user_id,
            "query": log.original_query,
            "intent": log.detected_intent,
            "response_preview": log.response_text[:200] + "..." if len(log.response_text) > 200 else log.response_text,
            "citations_count": len(log.citations) if log.citations else 0,
            "disclaimer_type": log.disclaimer_type,
            "confidence_score": log.confidence_score,
            "latency_ms": log.latency_ms,
            "feedback": log.user_feedback
        }
        for log in logs
    ]