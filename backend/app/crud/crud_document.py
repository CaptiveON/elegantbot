from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models.document import SourceDocument, IngestionStatus, AuthorityType, DocumentType
from app.schema.document import DocumentCreate, DocumentUpdate


def create_document(db: Session, document_data: DocumentCreate) -> SourceDocument:
    
    document = SourceDocument(
        url=document_data.url,
        authority=document_data.authority,
        document_type=document_data.document_type,
        reliability_tier=document_data.reliability_tier,
        title=document_data.title,
        parent_document=document_data.parent_document,
        section_hierarchy=document_data.section_hierarchy,
        publication_date=document_data.publication_date,
        last_updated_source=document_data.last_updated_source,
        effective_from=document_data.effective_from,
        effective_until=document_data.effective_until,
        tax_year=document_data.tax_year,
        ingestion_status=IngestionStatus.PENDING
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    return document


def get_document(db: Session, document_id: str) -> Optional[SourceDocument]:
    
    return db.query(SourceDocument).filter(SourceDocument.id == document_id).first()


def get_document_by_url(db: Session, url: str) -> Optional[SourceDocument]:

    return db.query(SourceDocument).filter(SourceDocument.url == url).first()


def get_documents(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    authority: Optional[AuthorityType] = None,
    document_type: Optional[DocumentType] = None,
    status: Optional[IngestionStatus] = None
) -> List[SourceDocument]:
    """Get documents with optional filtering and pagination"""
    query = db.query(SourceDocument)
    
    if authority:
        query = query.filter(SourceDocument.authority == authority)
    if document_type:
        query = query.filter(SourceDocument.document_type == document_type)
    if status:
        query = query.filter(SourceDocument.ingestion_status == status)
    
    return query.order_by(SourceDocument.created_at.desc()).offset(skip).limit(limit).all()


def count_documents(
    db: Session,
    authority: Optional[AuthorityType] = None,
    document_type: Optional[DocumentType] = None,
    status: Optional[IngestionStatus] = None
) -> int:
    
    query = db.query(func.count(SourceDocument.id))
    
    if authority:
        query = query.filter(SourceDocument.authority == authority)
    if document_type:
        query = query.filter(SourceDocument.document_type == document_type)
    if status:
        query = query.filter(SourceDocument.ingestion_status == status)
    
    return query.scalar()


def update_document(
    db: Session,
    document_id: str,
    document_data: DocumentUpdate
) -> Optional[SourceDocument]:
    """Update a document"""
    document = get_document(db, document_id)
    if not document:
        return None
    
    update_data = document_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(document, field, value)
    
    document.updated_at = datetime.now()
    db.commit()
    db.refresh(document)
    
    return document


def update_document_status(
    db: Session,
    document_id: str,
    status: IngestionStatus,
    content_hash: Optional[str] = None,
    total_chunks: Optional[int] = None
) -> Optional[SourceDocument]:
    """Update document ingestion status"""
    document = get_document(db, document_id)
    if not document:
        return None
    
    document.ingestion_status = status
    if status == IngestionStatus.COMPLETED:
        document.ingested_at = datetime.now()
    if content_hash:
        document.content_hash = content_hash
    if total_chunks is not None:
        document.total_chunks = total_chunks
    
    document.updated_at = datetime.now()
    db.commit()
    db.refresh(document)
    
    return document


def update_document_verified(db: Session, document_id: str) -> Optional[SourceDocument]:
    """Mark document as verified (content checked and still current)"""
    document = get_document(db, document_id)
    if not document:
        return None
    
    document.last_verified_at = datetime.now()
    document.updated_at = datetime.now()
    db.commit()
    db.refresh(document)
    
    return document


def delete_document(db: Session, document_id: str) -> bool:
    """Delete a document and its chunks (cascade)"""
    document = get_document(db, document_id)
    if not document:
        return False
    
    db.delete(document)
    db.commit()
    
    return True


def get_documents_needing_verification(
    db: Session,
    days_since_verified: int = 7,
    limit: int = 100
) -> List[SourceDocument]:
    """Get documents that haven't been verified recently"""
    from datetime import timedelta
    
    cutoff_date = datetime.now() - timedelta(days=days_since_verified)
    
    return db.query(SourceDocument).filter(
        SourceDocument.ingestion_status == IngestionStatus.COMPLETED,
        (SourceDocument.last_verified_at < cutoff_date) | (SourceDocument.last_verified_at.is_(None))
    ).limit(limit).all()


def get_document_stats(db: Session) -> Dict[str, Any]:
    """Get statistics about documents"""
    total = db.query(func.count(SourceDocument.id)).scalar()
    total_chunks = db.query(func.sum(SourceDocument.total_chunks)).scalar() or 0
    
    # By authority
    by_authority = dict(
        db.query(SourceDocument.authority, func.count(SourceDocument.id))
        .group_by(SourceDocument.authority)
        .all()
    )
    
    # By status
    by_status = dict(
        db.query(SourceDocument.ingestion_status, func.count(SourceDocument.id))
        .group_by(SourceDocument.ingestion_status)
        .all()
    )
    
    # Last ingestion
    last_ingestion = db.query(func.max(SourceDocument.ingested_at)).scalar()
    
    return {
        "total_documents": total,
        "total_chunks": total_chunks,
        "by_authority": {k.value if k else "unknown": v for k, v in by_authority.items()},
        "by_status": {k.value if k else "unknown": v for k, v in by_status.items()},
        "last_ingestion": last_ingestion
    }