"""
ChunkReference Model - Cross-reference tracking between document chunks.

This model stores the reference graph that enables automatic context expansion
during retrieval. When one legal section references another (e.g., "see VATREG02150
for definition"), we store that relationship here.

The reference graph allows us to:
1. Automatically fetch related chunks during retrieval
2. Ensure LLM has complete context for accurate answers
3. Generate comprehensive citations that include referenced sources

Example:
    VATREG02200 says "taxable turnover (see VATREG02150 for definition)"
    - source_chunk_id = VATREG02200's chunk ID
    - target_chunk_id = VATREG02150's chunk ID
    - reference_type = "definition"
    - reference_strength = "required"
"""

from sqlalchemy import Column, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.database import Base


class ReferenceType(str, enum.Enum):
    """Type of cross-reference relationship."""
    
    DEFINITION = "definition"           # "X means..." or "as defined in..."
    SEE_ALSO = "see_also"              # "see section X" or "refer to X"
    SUBJECT_TO = "subject_to"          # "subject to provisions in X"
    EXCEPTION = "exception"            # "except as provided in X"
    PENALTY = "penalty"                # References to penalty sections
    TIME_LIMIT = "time_limit"          # References to deadline sections
    THRESHOLD = "threshold"            # References to threshold/limit sections
    PROCEDURE = "procedure"            # "follow the procedure in X"
    LEGISLATION = "legislation"        # References to Acts/Regulations
    EXAMPLE = "example"                # "for examples, see X"
    SUPERSEDES = "supersedes"          # "this replaces X"
    AMENDED_BY = "amended_by"          # "as amended by X"


class ReferenceStrength(str, enum.Enum):
    """How important is this reference for understanding the source chunk."""
    
    REQUIRED = "required"       # Must fetch - contains essential definition/context
    RECOMMENDED = "recommended" # Should fetch - adds helpful context
    OPTIONAL = "optional"       # Can fetch - supplementary information


class ChunkReference(Base):
    """
    Stores cross-reference relationships between document chunks.
    
    This creates a directed graph where:
    - source_chunk_id = the chunk containing the reference text
    - target_chunk_id = the chunk being referenced
    
    The graph enables automatic context expansion during retrieval:
    1. User asks about VAT registration threshold
    2. System retrieves VATREG02200 (threshold section)
    3. System sees VATREG02200 references VATREG02150 (definition)
    4. System automatically fetches VATREG02150 for complete context
    5. LLM can now accurately define "taxable turnover" in its response
    """
    
    __tablename__ = "chunk_references"
    
    # === PRIMARY KEY ===
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # === RELATIONSHIP ENDPOINTS ===
    source_chunk_id = Column(
        String, 
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="The chunk that contains the reference"
    )
    target_chunk_id = Column(
        String,
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=True,  # Nullable because target might not be ingested yet
        index=True,
        comment="The chunk being referenced (null if unresolved)"
    )
    
    # === REFERENCE DETAILS ===
    reference_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of reference: definition, see_also, subject_to, etc."
    )
    reference_strength = Column(
        String(20),
        nullable=False,
        default=ReferenceStrength.RECOMMENDED.value,
        comment="Importance: required, recommended, optional"
    )
    
    # === REFERENCE TEXT ===
    reference_text = Column(
        String(200),
        nullable=False,
        comment="The reference as it appears in source: 'VATREG02150' or 'Section 3.4'"
    )
    reference_context = Column(
        Text,
        nullable=True,
        comment="Surrounding text explaining the reference: 'see VATREG02150 for definition of taxable turnover'"
    )
    
    # === RESOLUTION STATUS ===
    is_resolved = Column(
        Boolean,
        default=False,
        comment="True if target_chunk_id has been successfully linked"
    )
    target_section_id = Column(
        String(100),
        nullable=True,
        index=True,
        comment="Target section ID for resolution: 'VATREG02150' - used to resolve later"
    )
    
    # === TIMESTAMPS ===
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # === RELATIONSHIPS ===
    source_chunk = relationship(
        "DocumentChunk",
        foreign_keys=[source_chunk_id],
        backref="outgoing_references"
    )
    target_chunk = relationship(
        "DocumentChunk",
        foreign_keys=[target_chunk_id],
        backref="incoming_references"
    )
    
    def __repr__(self) -> str:
        return (
            f"<ChunkReference(source={self.source_chunk_id[:8]}..., "
            f"target={self.target_section_id}, type={self.reference_type}, "
            f"resolved={self.is_resolved})>"
        )