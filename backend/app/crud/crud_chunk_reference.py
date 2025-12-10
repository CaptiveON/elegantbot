"""
Chunk Reference CRUD Operations

Database operations for ChunkReference model.

Handles:
1. Creating references during ingestion
2. Resolving references to actual chunk IDs
3. Querying reference graph for retrieval expansion
4. Statistics and maintenance operations
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from app.models.chunk import DocumentChunk
from app.models.chunk_reference import ChunkReference, ReferenceType, ReferenceStrength
from app.schema.chunk_reference import (
    ChunkReferenceCreate,
    ChunkReferenceUpdate,
    ReferenceStats
)


# === CREATE OPERATIONS ===

def create_reference(
    db: Session,
    reference_data: ChunkReferenceCreate
) -> ChunkReference:
    """Create a single chunk reference."""
    reference = ChunkReference(
        source_chunk_id=reference_data.source_chunk_id,
        target_chunk_id=reference_data.target_chunk_id,
        reference_type=reference_data.reference_type,
        reference_strength=reference_data.reference_strength,
        reference_text=reference_data.reference_text,
        reference_context=reference_data.reference_context,
        target_section_id=reference_data.target_section_id,
        is_resolved=reference_data.is_resolved
    )
    
    db.add(reference)
    db.commit()
    db.refresh(reference)
    
    # Update source chunk's has_outgoing_references flag
    source_chunk = db.query(DocumentChunk).filter(
        DocumentChunk.id == reference_data.source_chunk_id
    ).first()
    if source_chunk:
        source_chunk.has_outgoing_references = True
    
    # If resolved, update target chunk's has_incoming_references flag
    if reference_data.is_resolved and reference_data.target_chunk_id:
        target_chunk = db.query(DocumentChunk).filter(
            DocumentChunk.id == reference_data.target_chunk_id
        ).first()
        if target_chunk:
            target_chunk.has_incoming_references = True
    
    db.commit()
    return reference


def create_references_batch(
    db: Session,
    references: List[ChunkReferenceCreate]
) -> List[ChunkReference]:
    """Create multiple references in batch."""
    if not references:
        return []
    
    db_references = []
    for ref_data in references:
        reference = ChunkReference(
            source_chunk_id=ref_data.source_chunk_id,
            target_chunk_id=ref_data.target_chunk_id,
            reference_type=ref_data.reference_type,
            reference_strength=ref_data.reference_strength,
            reference_text=ref_data.reference_text,
            reference_context=ref_data.reference_context,
            target_section_id=ref_data.target_section_id,
            is_resolved=ref_data.is_resolved
        )
        db_references.append(reference)
    
    db.add_all(db_references)
    db.commit()
    
    # Update has_outgoing_references for all source chunks
    source_chunk_ids = list(set(ref.source_chunk_id for ref in references))
    db.query(DocumentChunk).filter(
        DocumentChunk.id.in_(source_chunk_ids)
    ).update({DocumentChunk.has_outgoing_references: True}, synchronize_session=False)
    
    # Update has_incoming_references for resolved target chunks
    resolved_target_ids = list(set(
        ref.target_chunk_id for ref in references 
        if ref.is_resolved and ref.target_chunk_id
    ))
    if resolved_target_ids:
        db.query(DocumentChunk).filter(
            DocumentChunk.id.in_(resolved_target_ids)
        ).update({DocumentChunk.has_incoming_references: True}, synchronize_session=False)
    
    db.commit()
    
    for ref in db_references:
        db.refresh(ref)
    
    return db_references


# === READ OPERATIONS ===

def get_reference(
    db: Session,
    reference_id: str
) -> Optional[ChunkReference]:
    """Get a reference by ID."""
    return db.query(ChunkReference).filter(ChunkReference.id == reference_id).first()


def get_outgoing_references(
    db: Session,
    chunk_id: str,
    strength_filter: Optional[List[str]] = None,
    resolved_only: bool = False
) -> List[ChunkReference]:
    """Get all references FROM a chunk (what this chunk references)."""
    query = db.query(ChunkReference).filter(ChunkReference.source_chunk_id == chunk_id)
    
    if strength_filter:
        query = query.filter(ChunkReference.reference_strength.in_(strength_filter))
    
    if resolved_only:
        query = query.filter(ChunkReference.is_resolved == True)
    
    return query.all()


def get_incoming_references(
    db: Session,
    chunk_id: str,
    strength_filter: Optional[List[str]] = None
) -> List[ChunkReference]:
    """Get all references TO a chunk (what references this chunk)."""
    query = db.query(ChunkReference).filter(
        and_(
            ChunkReference.target_chunk_id == chunk_id,
            ChunkReference.is_resolved == True
        )
    )
    
    if strength_filter:
        query = query.filter(ChunkReference.reference_strength.in_(strength_filter))
    
    return query.all()


def get_unresolved_references(
    db: Session,
    limit: int = 100
) -> List[ChunkReference]:
    """Get references that haven't been resolved to chunk IDs yet."""
    return db.query(ChunkReference).filter(
        ChunkReference.is_resolved == False
    ).limit(limit).all()


def get_references_by_target_section(
    db: Session,
    target_section_id: str
) -> List[ChunkReference]:
    """Find all unresolved references pointing to a section ID."""
    return db.query(ChunkReference).filter(
        and_(
            ChunkReference.target_section_id == target_section_id,
            ChunkReference.is_resolved == False
        )
    ).all()


def get_references_by_type(
    db: Session,
    reference_type: str,
    limit: int = 100
) -> List[ChunkReference]:
    """Get references by type."""
    return db.query(ChunkReference).filter(
        ChunkReference.reference_type == reference_type
    ).limit(limit).all()


# === GRAPH TRAVERSAL ===

def expand_references(
    db: Session,
    chunk_ids: List[str],
    max_depth: int = 1,
    strength_filter: Optional[List[str]] = None,
    max_total_chunks: int = 10
) -> Tuple[List[str], List[ChunkReference]]:
    """
    Expand from initial chunks following the reference graph.
    
    This is the key function for automatic context expansion during retrieval.
    When a user asks about VAT registration, we retrieve the relevant chunk,
    then automatically fetch any chunks it references (definitions, penalties, etc.)
    
    Args:
        db: Database session
        chunk_ids: Initial chunk IDs to expand from
        max_depth: How many hops to follow (1=direct refs, 2=refs of refs)
        strength_filter: Which reference strengths to include
        max_total_chunks: Maximum total chunks to return
    
    Returns:
        Tuple of (all_chunk_ids, references_followed)
    """
    if strength_filter is None:
        strength_filter = [ReferenceStrength.REQUIRED.value, ReferenceStrength.RECOMMENDED.value]
    
    all_chunk_ids = set(chunk_ids)
    all_references = []
    current_chunks = list(chunk_ids)
    
    for depth in range(max_depth):
        if len(all_chunk_ids) >= max_total_chunks:
            break
        
        # Get outgoing references from current chunks
        references = db.query(ChunkReference).filter(
            and_(
                ChunkReference.source_chunk_id.in_(current_chunks),
                ChunkReference.is_resolved == True,
                ChunkReference.reference_strength.in_(strength_filter)
            )
        ).all()
        
        # Collect new chunk IDs
        new_chunk_ids = []
        for ref in references:
            if ref.target_chunk_id and ref.target_chunk_id not in all_chunk_ids:
                new_chunk_ids.append(ref.target_chunk_id)
                all_chunk_ids.add(ref.target_chunk_id)
                all_references.append(ref)
                
                if len(all_chunk_ids) >= max_total_chunks:
                    break
        
        current_chunks = new_chunk_ids
        
        if not current_chunks:
            break
    
    return list(all_chunk_ids), all_references


def get_definition_chain(
    db: Session,
    chunk_id: str,
    max_depth: int = 2
) -> Tuple[List[str], List[ChunkReference]]:
    """
    Get all definition references from a chunk.
    
    Useful for ensuring we have all term definitions needed
    to accurately explain a concept.
    """
    return expand_references(
        db,
        chunk_ids=[chunk_id],
        max_depth=max_depth,
        strength_filter=[ReferenceStrength.REQUIRED.value],
        max_total_chunks=10
    )


# === UPDATE OPERATIONS ===

def resolve_reference(
    db: Session,
    reference_id: str,
    target_chunk_id: str
) -> Optional[ChunkReference]:
    """Resolve a reference by linking it to the target chunk."""
    reference = get_reference(db, reference_id)
    
    if not reference:
        return None
    
    reference.target_chunk_id = target_chunk_id
    reference.is_resolved = True
    reference.updated_at = datetime.now()
    
    # Update target chunk's has_incoming_references flag
    target_chunk = db.query(DocumentChunk).filter(
        DocumentChunk.id == target_chunk_id
    ).first()
    if target_chunk:
        target_chunk.has_incoming_references = True
    
    db.commit()
    db.refresh(reference)
    return reference


def resolve_references_by_section(
    db: Session,
    section_id: str,
    target_chunk_id: str
) -> int:
    """
    Resolve all references pointing to a section ID.
    
    Called when a new chunk is ingested - we check if any existing
    unresolved references point to this section and resolve them.
    """
    # Find all unresolved references to this section
    references = db.query(ChunkReference).filter(
        and_(
            ChunkReference.target_section_id == section_id,
            ChunkReference.is_resolved == False
        )
    ).all()
    
    resolved_count = 0
    for ref in references:
        ref.target_chunk_id = target_chunk_id
        ref.is_resolved = True
        ref.updated_at = datetime.now()
        resolved_count += 1
    
    # Update target chunk's has_incoming_references
    if resolved_count > 0:
        target_chunk = db.query(DocumentChunk).filter(
            DocumentChunk.id == target_chunk_id
        ).first()
        if target_chunk:
            target_chunk.has_incoming_references = True
    
    db.commit()
    return resolved_count


def update_reference(
    db: Session,
    reference_id: str,
    update_data: ChunkReferenceUpdate
) -> Optional[ChunkReference]:
    """Update a reference."""
    reference = get_reference(db, reference_id)
    
    if not reference:
        return None
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(reference, field, value)
    
    reference.updated_at = datetime.now()
    db.commit()
    db.refresh(reference)
    return reference


# === DELETE OPERATIONS ===

def delete_reference(
    db: Session,
    reference_id: str
) -> bool:
    """Delete a reference."""
    reference = get_reference(db, reference_id)
    
    if not reference:
        return False
    
    db.delete(reference)
    db.commit()
    return True


def delete_references_for_chunk(
    db: Session,
    chunk_id: str
) -> int:
    """Delete all references from or to a chunk."""
    # Count before deletion
    count = db.query(func.count(ChunkReference.id)).filter(
        or_(
            ChunkReference.source_chunk_id == chunk_id,
            ChunkReference.target_chunk_id == chunk_id
        )
    ).scalar()
    
    # Delete references
    db.query(ChunkReference).filter(
        or_(
            ChunkReference.source_chunk_id == chunk_id,
            ChunkReference.target_chunk_id == chunk_id
        )
    ).delete(synchronize_session=False)
    
    db.commit()
    return count or 0


# === STATISTICS ===

def get_reference_stats(db: Session) -> ReferenceStats:
    """Get statistics about the reference graph."""
    # Total and resolution counts
    total = db.query(func.count(ChunkReference.id)).scalar() or 0
    resolved = db.query(func.count(ChunkReference.id)).filter(
        ChunkReference.is_resolved == True
    ).scalar() or 0
    
    # Count by type
    type_result = db.query(
        ChunkReference.reference_type, 
        func.count(ChunkReference.id)
    ).group_by(ChunkReference.reference_type).all()
    by_type = {row[0]: row[1] for row in type_result}
    
    # Count by strength
    strength_result = db.query(
        ChunkReference.reference_strength, 
        func.count(ChunkReference.id)
    ).group_by(ChunkReference.reference_strength).all()
    by_strength = {row[0]: row[1] for row in strength_result}
    
    # Chunks with references
    with_outgoing = db.query(func.count(DocumentChunk.id)).filter(
        DocumentChunk.has_outgoing_references == True
    ).scalar() or 0
    
    with_incoming = db.query(func.count(DocumentChunk.id)).filter(
        DocumentChunk.has_incoming_references == True
    ).scalar() or 0
    
    return ReferenceStats(
        total_references=total,
        resolved_references=resolved,
        unresolved_references=total - resolved,
        references_by_type=by_type,
        references_by_strength=by_strength,
        chunks_with_outgoing=with_outgoing,
        chunks_with_incoming=with_incoming
    )


def get_most_referenced_chunks(
    db: Session,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Get chunks that are most frequently referenced."""
    results = db.query(
        ChunkReference.target_chunk_id,
        func.count(ChunkReference.id).label('reference_count')
    ).filter(
        ChunkReference.is_resolved == True
    ).group_by(
        ChunkReference.target_chunk_id
    ).order_by(
        func.count(ChunkReference.id).desc()
    ).limit(limit).all()
    
    return [
        {"chunk_id": row[0], "reference_count": row[1]}
        for row in results
    ]


# =============================================================================
# FUNCTION ALIASES FOR PIPELINE COMPATIBILITY  
# =============================================================================

create_chunk_reference = create_reference
get_chunk_reference = get_reference
update_chunk_reference = update_reference
delete_chunk_reference = delete_reference