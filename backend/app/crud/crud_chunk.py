"""
Chunk CRUD Operations

Database operations for DocumentChunk model.

Updated for Phase 1.1: Added support for precise citation fields
(section_id, citable_reference) and cross-reference tracking fields.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.models.chunk import DocumentChunk, TopicPrimary, ContentType, ServiceCategory
from app.schema.chunk import ChunkCreate, ChunkUpdate


def create_chunk(db: Session, chunk_data: ChunkCreate) -> DocumentChunk:
    """Create a new document chunk"""
    chunk = DocumentChunk(
        document_id=chunk_data.document_id,
        content=chunk_data.content,
        chunk_summary=chunk_data.chunk_summary,
        
        # Source attribution
        source_url=chunk_data.source_url,
        source_authority=chunk_data.source_authority,
        section_title=chunk_data.section_title,
        heading_path=chunk_data.heading_path,
        
        # Precise citation fields
        section_id=chunk_data.section_id,
        paragraph_number=chunk_data.paragraph_number,
        citable_reference=chunk_data.citable_reference,
        
        # Classification
        topic_primary=chunk_data.topic_primary,
        topic_secondary=chunk_data.topic_secondary,
        business_types=chunk_data.business_types,
        content_type=chunk_data.content_type,
        service_category=chunk_data.service_category,
        reliability_tier=chunk_data.reliability_tier,
        
        # Temporal
        publication_date=chunk_data.publication_date,
        last_updated=chunk_data.last_updated,
        effective_from=chunk_data.effective_from,
        tax_year=chunk_data.tax_year,
        
        # Retrieval hints
        threshold_values=chunk_data.threshold_values,
        threshold_type=chunk_data.threshold_type,
        keywords=chunk_data.keywords,
        form_references=chunk_data.form_references,
        deadlines_mentioned=chunk_data.deadlines_mentioned,
        applies_to_tax_years=chunk_data.applies_to_tax_years,
        
        # Cross-reference tracking
        defined_terms_used=chunk_data.defined_terms_used,
        defined_terms_provided=chunk_data.defined_terms_provided,
        has_outgoing_references=chunk_data.has_outgoing_references,
        has_incoming_references=chunk_data.has_incoming_references,
        
        # Structured content flags
        contains_table=chunk_data.contains_table,
        contains_formula=chunk_data.contains_formula,
        contains_decision_tree=chunk_data.contains_decision_tree,
        contains_deadline=chunk_data.contains_deadline,
        contains_example=chunk_data.contains_example,
        contains_contact=chunk_data.contains_contact,
        contains_condition_list=chunk_data.contains_condition_list,
        structured_content_types=chunk_data.structured_content_types,
        
        # Compliance flags
        requires_professional_advice=chunk_data.requires_professional_advice,
        deadline_sensitive=chunk_data.deadline_sensitive,
        penalty_relevant=chunk_data.penalty_relevant,
        
        # Position
        chunk_index=chunk_data.chunk_index,
        total_chunks_in_doc=chunk_data.total_chunks_in_doc,
        char_start=chunk_data.char_start,
        char_end=chunk_data.char_end
    )
    
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    
    return chunk


def create_chunks_batch(db: Session, chunks_data: List[ChunkCreate]) -> List[DocumentChunk]:
    """Create multiple chunks in a batch (more efficient)"""
    chunks = []
    for chunk_data in chunks_data:
        chunk = DocumentChunk(
            document_id=chunk_data.document_id,
            content=chunk_data.content,
            chunk_summary=chunk_data.chunk_summary,
            
            # Source attribution
            source_url=chunk_data.source_url,
            source_authority=chunk_data.source_authority,
            section_title=chunk_data.section_title,
            heading_path=chunk_data.heading_path,
            
            # Precise citation fields
            section_id=chunk_data.section_id,
            paragraph_number=chunk_data.paragraph_number,
            citable_reference=chunk_data.citable_reference,
            
            # Classification
            topic_primary=chunk_data.topic_primary,
            topic_secondary=chunk_data.topic_secondary,
            business_types=chunk_data.business_types,
            content_type=chunk_data.content_type,
            service_category=chunk_data.service_category,
            reliability_tier=chunk_data.reliability_tier,
            
            # Temporal
            publication_date=chunk_data.publication_date,
            last_updated=chunk_data.last_updated,
            effective_from=chunk_data.effective_from,
            tax_year=chunk_data.tax_year,
            
            # Retrieval hints
            threshold_values=chunk_data.threshold_values,
            threshold_type=chunk_data.threshold_type,
            keywords=chunk_data.keywords,
            form_references=chunk_data.form_references,
            deadlines_mentioned=chunk_data.deadlines_mentioned,
            applies_to_tax_years=chunk_data.applies_to_tax_years,
            
            # Cross-reference tracking
            defined_terms_used=chunk_data.defined_terms_used,
            defined_terms_provided=chunk_data.defined_terms_provided,
            has_outgoing_references=chunk_data.has_outgoing_references,
            has_incoming_references=chunk_data.has_incoming_references,
            
            # Structured content flags
            contains_table=chunk_data.contains_table,
            contains_formula=chunk_data.contains_formula,
            contains_decision_tree=chunk_data.contains_decision_tree,
            contains_deadline=chunk_data.contains_deadline,
            contains_example=chunk_data.contains_example,
            contains_contact=chunk_data.contains_contact,
            contains_condition_list=chunk_data.contains_condition_list,
            structured_content_types=chunk_data.structured_content_types,
            
            # Compliance flags
            requires_professional_advice=chunk_data.requires_professional_advice,
            deadline_sensitive=chunk_data.deadline_sensitive,
            penalty_relevant=chunk_data.penalty_relevant,
            
            # Position
            chunk_index=chunk_data.chunk_index,
            total_chunks_in_doc=chunk_data.total_chunks_in_doc,
            char_start=chunk_data.char_start,
            char_end=chunk_data.char_end
        )
        chunks.append(chunk)
    
    db.add_all(chunks)
    db.commit()
    
    for chunk in chunks:
        db.refresh(chunk)
    
    return chunks


def get_chunk(db: Session, chunk_id: str) -> Optional[DocumentChunk]:
    """Get a chunk by ID"""
    return db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first()


def get_chunk_by_pinecone_id(db: Session, pinecone_id: str) -> Optional[DocumentChunk]:
    """Get a chunk by its Pinecone ID"""
    return db.query(DocumentChunk).filter(DocumentChunk.pinecone_id == pinecone_id).first()


def get_chunk_by_section_id(db: Session, section_id: str) -> Optional[DocumentChunk]:
    """Get a chunk by its section ID (e.g., 'VATREG02200')"""
    return db.query(DocumentChunk).filter(DocumentChunk.section_id == section_id).first()


def get_chunks_by_section_ids(db: Session, section_ids: List[str]) -> List[DocumentChunk]:
    """Get multiple chunks by section IDs"""
    return db.query(DocumentChunk).filter(
        DocumentChunk.section_id.in_(section_ids)
    ).all()


def get_chunks_by_document(
    db: Session,
    document_id: str,
    skip: int = 0,
    limit: int = 100
) -> List[DocumentChunk]:
    """Get all chunks for a document"""
    return db.query(DocumentChunk).filter(
        DocumentChunk.document_id == document_id
    ).order_by(DocumentChunk.chunk_index).offset(skip).limit(limit).all()


def count_chunks_by_document(db: Session, document_id: str) -> int:
    """Count chunks for a document"""
    return db.query(func.count(DocumentChunk.id)).filter(
        DocumentChunk.document_id == document_id
    ).scalar()


def get_chunks_by_topic(
    db: Session,
    topic: TopicPrimary,
    skip: int = 0,
    limit: int = 100
) -> List[DocumentChunk]:
    """Get chunks by primary topic"""
    return db.query(DocumentChunk).filter(
        DocumentChunk.topic_primary == topic
    ).offset(skip).limit(limit).all()


def get_chunks_without_embeddings(
    db: Session,
    limit: int = 100
) -> List[DocumentChunk]:
    """Get chunks that haven't been embedded yet"""
    return db.query(DocumentChunk).filter(
        DocumentChunk.pinecone_id.is_(None)
    ).limit(limit).all()


def get_chunks_with_outgoing_references(
    db: Session,
    limit: int = 100
) -> List[DocumentChunk]:
    """Get chunks that have outgoing references"""
    return db.query(DocumentChunk).filter(
        DocumentChunk.has_outgoing_references == True
    ).limit(limit).all()


def get_chunks_with_incoming_references(
    db: Session,
    limit: int = 100
) -> List[DocumentChunk]:
    """Get chunks that are referenced by other chunks"""
    return db.query(DocumentChunk).filter(
        DocumentChunk.has_incoming_references == True
    ).limit(limit).all()


def get_chunks_providing_term(
    db: Session,
    term: str
) -> List[DocumentChunk]:
    """Find chunks that define a specific term"""
    return db.query(DocumentChunk).filter(
        DocumentChunk.defined_terms_provided.contains([term])
    ).all()


def update_chunk(
    db: Session,
    chunk_id: str,
    chunk_data: ChunkUpdate
) -> Optional[DocumentChunk]:
    """Update a chunk"""
    chunk = get_chunk(db, chunk_id)
    if not chunk:
        return None
    
    update_data = chunk_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(chunk, field, value)
    
    chunk.updated_at = datetime.now()
    db.commit()
    db.refresh(chunk)
    
    return chunk


def update_chunk_embedding(
    db: Session,
    chunk_id: str,
    pinecone_id: str,
    embedding_model: str
) -> Optional[DocumentChunk]:
    """Update chunk with embedding information"""
    chunk = get_chunk(db, chunk_id)
    if not chunk:
        return None
    
    chunk.pinecone_id = pinecone_id
    chunk.embedding_model = embedding_model
    chunk.embedded_at = datetime.now()
    chunk.updated_at = datetime.now()
    
    db.commit()
    db.refresh(chunk)
    
    return chunk


def update_chunk_reference_flags(
    db: Session,
    chunk_id: str,
    has_outgoing: Optional[bool] = None,
    has_incoming: Optional[bool] = None
) -> Optional[DocumentChunk]:
    """Update chunk's reference tracking flags"""
    chunk = get_chunk(db, chunk_id)
    if not chunk:
        return None
    
    if has_outgoing is not None:
        chunk.has_outgoing_references = has_outgoing
    if has_incoming is not None:
        chunk.has_incoming_references = has_incoming
    
    chunk.updated_at = datetime.now()
    db.commit()
    db.refresh(chunk)
    
    return chunk


def update_chunks_embedding_batch(
    db: Session,
    chunk_updates: List[Dict[str, str]]
) -> int:
    """
    Batch update chunks with embedding information.
    chunk_updates: List of {"chunk_id": str, "pinecone_id": str, "embedding_model": str}
    Returns count of updated chunks.
    """
    updated_count = 0
    now = datetime.now()
    
    for update in chunk_updates:
        chunk = get_chunk(db, update["chunk_id"])
        if chunk:
            chunk.pinecone_id = update["pinecone_id"]
            chunk.embedding_model = update["embedding_model"]
            chunk.embedded_at = now
            chunk.updated_at = now
            updated_count += 1
    
    db.commit()
    return updated_count


def delete_chunk(db: Session, chunk_id: str) -> bool:
    """Delete a chunk"""
    chunk = get_chunk(db, chunk_id)
    if not chunk:
        return False
    
    db.delete(chunk)
    db.commit()
    
    return True


def delete_chunks_by_document(db: Session, document_id: str) -> int:
    """Delete all chunks for a document. Returns count deleted."""
    result = db.query(DocumentChunk).filter(
        DocumentChunk.document_id == document_id
    ).delete()
    db.commit()
    
    return result


def get_chunks_for_citation(db: Session, chunk_ids: List[str]) -> List[DocumentChunk]:
    """Get multiple chunks by IDs (for building citations)"""
    return db.query(DocumentChunk).filter(
        DocumentChunk.id.in_(chunk_ids)
    ).all()


def get_chunk_stats(db: Session) -> Dict[str, Any]:
    """Get statistics about chunks"""
    total = db.query(func.count(DocumentChunk.id)).scalar()
    embedded = db.query(func.count(DocumentChunk.id)).filter(
        DocumentChunk.pinecone_id.isnot(None)
    ).scalar()
    
    # With references
    with_outgoing = db.query(func.count(DocumentChunk.id)).filter(
        DocumentChunk.has_outgoing_references == True
    ).scalar()
    
    with_incoming = db.query(func.count(DocumentChunk.id)).filter(
        DocumentChunk.has_incoming_references == True
    ).scalar()
    
    # With structured content
    with_tables = db.query(func.count(DocumentChunk.id)).filter(
        DocumentChunk.contains_table == True
    ).scalar()
    
    with_formulas = db.query(func.count(DocumentChunk.id)).filter(
        DocumentChunk.contains_formula == True
    ).scalar()
    
    with_decision_trees = db.query(func.count(DocumentChunk.id)).filter(
        DocumentChunk.contains_decision_tree == True
    ).scalar()
    
    with_deadlines = db.query(func.count(DocumentChunk.id)).filter(
        DocumentChunk.contains_deadline == True
    ).scalar()
    
    with_examples = db.query(func.count(DocumentChunk.id)).filter(
        DocumentChunk.contains_example == True
    ).scalar()
    
    with_contacts = db.query(func.count(DocumentChunk.id)).filter(
        DocumentChunk.contains_contact == True
    ).scalar()
    
    # By topic
    by_topic = dict(
        db.query(DocumentChunk.topic_primary, func.count(DocumentChunk.id))
        .group_by(DocumentChunk.topic_primary)
        .all()
    )
    
    # By content type
    by_content_type = dict(
        db.query(DocumentChunk.content_type, func.count(DocumentChunk.id))
        .group_by(DocumentChunk.content_type)
        .all()
    )
    
    # By service category
    by_service_category = dict(
        db.query(DocumentChunk.service_category, func.count(DocumentChunk.id))
        .group_by(DocumentChunk.service_category)
        .all()
    )
    
    return {
        "total_chunks": total,
        "embedded_chunks": embedded,
        "pending_embedding": total - embedded,
        "with_outgoing_references": with_outgoing,
        "with_incoming_references": with_incoming,
        "with_tables": with_tables,
        "with_formulas": with_formulas,
        "with_decision_trees": with_decision_trees,
        "with_deadlines": with_deadlines,
        "with_examples": with_examples,
        "with_contacts": with_contacts,
        "by_topic": {k.value if k else "unknown": v for k, v in by_topic.items()},
        "by_content_type": {k.value if k else "unknown": v for k, v in by_content_type.items()},
        "by_service_category": {k.value if k else "unknown": v for k, v in by_service_category.items()}
    }


# === STRUCTURED CONTENT QUERIES ===

def get_chunks_with_tables(
    db: Session,
    topic: Optional[TopicPrimary] = None,
    limit: int = 100
) -> List[DocumentChunk]:
    """Get chunks that contain tables."""
    query = db.query(DocumentChunk).filter(DocumentChunk.contains_table == True)
    
    if topic:
        query = query.filter(DocumentChunk.topic_primary == topic)
    
    return query.limit(limit).all()


def get_chunks_with_formulas(
    db: Session,
    topic: Optional[TopicPrimary] = None,
    limit: int = 100
) -> List[DocumentChunk]:
    """Get chunks that contain formulas."""
    query = db.query(DocumentChunk).filter(DocumentChunk.contains_formula == True)
    
    if topic:
        query = query.filter(DocumentChunk.topic_primary == topic)
    
    return query.limit(limit).all()


def get_chunks_with_decision_trees(
    db: Session,
    topic: Optional[TopicPrimary] = None,
    limit: int = 100
) -> List[DocumentChunk]:
    """Get chunks that contain decision trees."""
    query = db.query(DocumentChunk).filter(DocumentChunk.contains_decision_tree == True)
    
    if topic:
        query = query.filter(DocumentChunk.topic_primary == topic)
    
    return query.limit(limit).all()


def get_chunks_with_deadlines(
    db: Session,
    tax_category: Optional[str] = None,
    limit: int = 100
) -> List[DocumentChunk]:
    """Get chunks that contain deadline information."""
    query = db.query(DocumentChunk).filter(DocumentChunk.contains_deadline == True)
    
    # Note: tax_category filtering would need to be done via structured_content_types
    # or by joining with StructuredDeadline table
    
    return query.limit(limit).all()


def get_chunks_with_contacts(
    db: Session,
    limit: int = 100
) -> List[DocumentChunk]:
    """Get chunks that contain contact information."""
    return db.query(DocumentChunk).filter(
        DocumentChunk.contains_contact == True
    ).limit(limit).all()


def get_chunks_with_examples(
    db: Session,
    topic: Optional[TopicPrimary] = None,
    limit: int = 100
) -> List[DocumentChunk]:
    """Get chunks that contain worked examples."""
    query = db.query(DocumentChunk).filter(DocumentChunk.contains_example == True)
    
    if topic:
        query = query.filter(DocumentChunk.topic_primary == topic)
    
    return query.limit(limit).all()


def update_chunk_structured_content_flags(
    db: Session,
    chunk_id: str,
    contains_table: Optional[bool] = None,
    contains_formula: Optional[bool] = None,
    contains_decision_tree: Optional[bool] = None,
    contains_deadline: Optional[bool] = None,
    contains_example: Optional[bool] = None,
    contains_contact: Optional[bool] = None,
    contains_condition_list: Optional[bool] = None,
    structured_content_types: Optional[List[str]] = None
) -> Optional[DocumentChunk]:
    """Update chunk's structured content flags."""
    chunk = get_chunk(db, chunk_id)
    if not chunk:
        return None
    
    if contains_table is not None:
        chunk.contains_table = contains_table
    if contains_formula is not None:
        chunk.contains_formula = contains_formula
    if contains_decision_tree is not None:
        chunk.contains_decision_tree = contains_decision_tree
    if contains_deadline is not None:
        chunk.contains_deadline = contains_deadline
    if contains_example is not None:
        chunk.contains_example = contains_example
    if contains_contact is not None:
        chunk.contains_contact = contains_contact
    if contains_condition_list is not None:
        chunk.contains_condition_list = contains_condition_list
    if structured_content_types is not None:
        chunk.structured_content_types = structured_content_types
    
    chunk.updated_at = datetime.now()
    db.commit()
    db.refresh(chunk)
    
    return chunk
