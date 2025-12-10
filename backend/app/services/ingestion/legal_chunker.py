"""
Legal Document Chunker

Enhanced chunker specifically designed for UK tax and legal documents.
Preserves legal structure, extracts citation metadata, and maintains
document integrity for audit purposes.

Key Enhancements over Basic Chunker:
1. HMRC section ID extraction (VATREG02200, CTM01500)
2. Condition list preservation ((a), (b), (c) stay together)
3. Legal boundary detection (sections, clauses, definitions)
4. Variable chunk sizes based on content type
5. Citation metadata extraction (citable_reference)
6. Cross-reference pattern detection

Analogy:
A basic chunker is like cutting a book every 500 words.
A legal chunker is like a paralegal who knows to keep:
- Legal definitions with their terms
- Conditions (a), (b), (c) together
- Section headers with their content
- Cross-references intact
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple, Set
import re
import logging
from enum import StrEnum
from .content_parser import ContentSection, ParsedDocument

logger = logging.getLogger(__name__)


class LegalContentType(StrEnum):
    """Types of legal content that affect chunking strategy."""
    DEFINITION = "definition"           # Term definitions
    CONDITION_LIST = "condition_list"   # (a), (b), (c) requirements
    PROCEDURE = "procedure"             # Step-by-step instructions
    RATE_TABLE = "rate_table"           # Tax rates, thresholds
    DEADLINE = "deadline"               # Filing/payment dates
    EXAMPLE = "example"                 # Worked examples
    PENALTY = "penalty"                 # Penalty information
    CONTACT = "contact"                 # Contact information
    GENERAL = "general"                 # General guidance


@dataclass
class LegalChunkingConfig:
    """
    Configuration for legal document chunking.
    
    Tuned for UK tax guidance documents with specific handling
    for HMRC manual structure and legal content patterns.
    """
    # === Size limits (in characters, ~4 chars = 1 token) ===
    min_chunk_size: int = 200         # Minimum chunk size
    max_chunk_size: int = 3000        # Maximum chunk size (~750 tokens)
    target_chunk_size: int = 1500     # Target size (~375 tokens)
    
    # === Overlap ===
    overlap_size: int = 150           # Overlap between chunks
    
    # === Legal structure preservation ===
    preserve_condition_lists: bool = True    # Keep (a), (b), (c) together
    preserve_definitions: bool = True        # Keep term + definition together
    preserve_examples: bool = True           # Keep example scenarios together
    max_condition_list_size: int = 4000      # Max size before splitting condition list
    
    # === HMRC-specific ===
    extract_hmrc_section_ids: bool = True    # Extract VATREG02200-style IDs
    extract_paragraph_numbers: bool = True   # Extract paragraph numbers
    
    # === Citation generation ===
    generate_citable_reference: bool = True
    
    # === Content type detection ===
    detect_content_type: bool = True


@dataclass
class LegalChunk:
    """
    A chunk of legal document content with enhanced metadata.
    
    Extends the basic Chunk with legal-specific fields for
    precise citation and retrieval.
    """
    content: str
    
    # === Position ===
    chunk_index: int
    total_chunks: int
    char_start: int
    char_end: int
    
    # === Document structure ===
    section_title: str
    heading_path: str
    heading_level: int
    
    # === Legal-specific metadata ===
    section_id: Optional[str] = None           # HMRC ID like VATREG02200
    paragraph_number: Optional[str] = None      # Paragraph number if present
    citable_reference: Optional[str] = None     # Full citation string
    content_type: LegalContentType = LegalContentType.GENERAL
    
    # === Structural flags ===
    contains_condition_list: bool = False
    contains_definition: bool = False
    contains_example: bool = False
    contains_table_reference: bool = False
    contains_deadline: bool = False
    contains_penalty_info: bool = False
    contains_contact_info: bool = False
    
    # === Cross-references detected ===
    cross_references: List[str] = field(default_factory=list)  # ["VATREG02150", "see section 3.2"]
    
    # === Overlap ===
    has_overlap_with_previous: bool = False
    overlap_text: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "content": self.content,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "section_title": self.section_title,
            "heading_path": self.heading_path,
            "heading_level": self.heading_level,
            "section_id": self.section_id,
            "paragraph_number": self.paragraph_number,
            "citable_reference": self.citable_reference,
            "content_type": self.content_type.value if self.content_type else None,
            "contains_condition_list": self.contains_condition_list,
            "contains_definition": self.contains_definition,
            "contains_example": self.contains_example,
            "contains_table_reference": self.contains_table_reference,
            "contains_deadline": self.contains_deadline,
            "contains_penalty_info": self.contains_penalty_info,
            "contains_contact_info": self.contains_contact_info,
            "cross_references": self.cross_references,
            "has_overlap_with_previous": self.has_overlap_with_previous,
        }


class LegalChunker:
    """
    Legal-aware document chunker for UK tax guidance.
    
    Strategy:
    1. Detect legal structure patterns (definitions, conditions, etc.)
    2. Extract HMRC section IDs and paragraph numbers
    3. Keep legal units together (don't split condition lists)
    4. Generate precise citable references
    5. Detect cross-references for later linking
    
    Usage:
        chunker = LegalChunker()
        chunks = chunker.chunk_document(parsed_doc, source_url, document_title)
        
        for chunk in chunks:
            print(f"Chunk {chunk.chunk_index}: {chunk.citable_reference}")
            print(f"  Content type: {chunk.content_type}")
            print(f"  Cross-refs: {chunk.cross_references}")
    """
    
    # ==========================================================================
    # REGEX PATTERNS FOR LEGAL CONTENT DETECTION
    # ==========================================================================
    
    # HMRC manual section IDs
    HMRC_SECTION_PATTERNS = [
        re.compile(r'\b(VAT(?:REG|SC|TOS|INF|IT|NOT|POSS|FRS|REC|AOS|GEN|ADJ|PE|RA|SG|AM|DT|LAND|FIN|FS)\d{5})\b', re.I),
        re.compile(r'\b(CTM\d{5})\b', re.I),          # Corporation Tax Manual
        re.compile(r'\b(CG\d{5})\b', re.I),           # Capital Gains Manual
        re.compile(r'\b(BIM\d{5})\b', re.I),          # Business Income Manual
        re.compile(r'\b(EIM\d{5})\b', re.I),          # Employment Income Manual
        re.compile(r'\b(TSEM\d{5})\b', re.I),         # Trusts, Settlements Manual
        re.compile(r'\b(SAIM\d{5})\b', re.I),         # Savings and Investment Manual
        re.compile(r'\b(PIM\d{5})\b', re.I),          # Property Income Manual
        re.compile(r'\b(NIM\d{5})\b', re.I),          # National Insurance Manual
        re.compile(r'\b(PAYE\d{5})\b', re.I),         # PAYE Manual
        re.compile(r'\b(CH\d{5})\b', re.I),           # Compliance Handbook
    ]
    
    # Condition list patterns
    CONDITION_START_PATTERN = re.compile(
        r'(?:you\s+(?:must|should|can(?:not)?|need\s+to|will\s+need\s+to)|'
        r'(?:a\s+)?(?:person|business|company|trader)\s+(?:must|should|can)|'
        r'(?:this|the\s+following)\s+(?:applies?|conditions?)\s+(?:if|when|where)|'
        r'if\s+(?:any|all)\s+of\s+the\s+following|'
        r'you\'?re?\s+(?:required|obliged)\s+to)[^.]*:',
        re.IGNORECASE | re.MULTILINE
    )
    
    CONDITION_ITEM_PATTERN = re.compile(r'^\s*\(([a-z])\)\s*', re.MULTILINE)
    NUMBERED_LIST_PATTERN = re.compile(r'^\s*(\d+)\.\s+', re.MULTILINE)
    BULLET_LIST_PATTERN = re.compile(r'^\s*[•\-\*]\s+', re.MULTILINE)
    
    # Definition patterns
    DEFINITION_PATTERNS = [
        re.compile(r'[\'"]([^\'\"]+)[\'"]\s+(?:means|has\s+the\s+meaning|is\s+defined\s+as|refers?\s+to)', re.I),
        re.compile(r'\b(?:the\s+term\s+)?[\'"]([^\'\"]+)[\'"]\s+(?:means|is|includes)', re.I),
        re.compile(r'^([A-Z][a-z]+(?:\s+[a-z]+)*)\s*[-–]\s*(?:means|is|the)', re.MULTILINE),
    ]
    
    # Example patterns
    EXAMPLE_PATTERNS = [
        re.compile(r'\b(?:example|for\s+example|e\.g\.)\s*[:\-]', re.I),
        re.compile(r'\b(?:suppose|consider|imagine|let\'s\s+say)\b', re.I),
        re.compile(r'\b(?:Sarah|John|Mary|James|Company\s+[A-Z]|ABC\s+Ltd)\b'),  # Common example names
        re.compile(r'(?:earns?|has\s+(?:income|turnover|profit)\s+of)\s+£[\d,]+', re.I),
    ]
    
    # Deadline patterns
    DEADLINE_PATTERNS = [
        re.compile(r'\b(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December))\b', re.I),
        re.compile(r'\b(?:deadline|due\s+(?:date|by)|must\s+be\s+(?:filed|submitted|paid)\s+by)\b', re.I),
        re.compile(r'\b(?:within\s+\d+\s+(?:days?|months?|weeks?))\b', re.I),
    ]
    
    # Penalty patterns
    PENALTY_PATTERNS = [
        re.compile(r'\b(?:penalty|penalties|fine|fines|surcharge|interest)\b', re.I),
        re.compile(r'\b(?:late\s+(?:filing|payment|submission))\b', re.I),
        re.compile(r'(?:£\d+(?:,\d+)*)\s*(?:penalty|fine)', re.I),
    ]
    
    # Contact patterns
    CONTACT_PATTERNS = [
        re.compile(r'\b(?:telephone|phone|call|helpline|contact)\s*(?:number|line)?[:\s]+(?:0\d{2,4}\s*\d{3,4}\s*\d{3,4}|\+44)', re.I),
        re.compile(r'\b(?:email|e-mail)[:\s]+\S+@\S+\.\S+', re.I),
        re.compile(r'\b(?:write\s+to|post|address)[:\s]+', re.I),
    ]
    
    # Cross-reference patterns
    CROSS_REF_PATTERNS = [
        re.compile(r'\b(?:see|refer\s+to)\s+(?:section|paragraph|chapter)\s+([\d.]+)', re.I),
        re.compile(r'\b(?:as\s+(?:explained|described|set\s+out)\s+in)\s+(?:section|paragraph)\s+([\d.]+)', re.I),
    ]
    
    # Monetary amounts
    GBP_PATTERN = re.compile(r'£(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)')
    
    # Paragraph numbers
    PARAGRAPH_PATTERN = re.compile(r'^(?:Para(?:graph)?\.?\s*)?(\d+(?:\.\d+)*)', re.MULTILINE)
    
    def __init__(self, config: Optional[LegalChunkingConfig] = None):
        """
        Initialize the legal chunker.
        
        Args:
            config: LegalChunkingConfig or None for defaults
        """
        self.config = config or LegalChunkingConfig()
    
    # ==========================================================================
    # PATTERN DETECTION METHODS
    # ==========================================================================
    
    def _extract_hmrc_section_id(self, text: str) -> Optional[str]:
        """
        Extract HMRC manual section ID from text.
        
        Returns the first matched ID like VATREG02200, CTM01500, etc.
        """
        for pattern in self.HMRC_SECTION_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group(1).upper()
        return None
    
    def _extract_all_section_ids(self, text: str) -> List[str]:
        """Extract all HMRC section IDs from text (for cross-references)."""
        ids = []
        for pattern in self.HMRC_SECTION_PATTERNS:
            ids.extend(m.group(1).upper() for m in pattern.finditer(text))
        return list(set(ids))
    
    def _extract_paragraph_number(self, text: str) -> Optional[str]:
        """Extract paragraph number from text."""
        match = self.PARAGRAPH_PATTERN.search(text[:200])  # Check start of text
        if match:
            return match.group(1)
        return None
    
    def _detect_content_type(self, text: str) -> LegalContentType:
        """
        Detect the primary content type of the text.
        
        Returns the most likely content type based on pattern matching.
        """
        # Check patterns in priority order
        if any(p.search(text) for p in self.DEFINITION_PATTERNS):
            return LegalContentType.DEFINITION
        
        if self.CONDITION_START_PATTERN.search(text) and self.CONDITION_ITEM_PATTERN.search(text):
            return LegalContentType.CONDITION_LIST
        
        if any(p.search(text) for p in self.EXAMPLE_PATTERNS):
            return LegalContentType.EXAMPLE
        
        if any(p.search(text) for p in self.CONTACT_PATTERNS):
            return LegalContentType.CONTACT
        
        if any(p.search(text) for p in self.PENALTY_PATTERNS):
            return LegalContentType.PENALTY
        
        if any(p.search(text) for p in self.DEADLINE_PATTERNS):
            return LegalContentType.DEADLINE
        
        return LegalContentType.GENERAL
    
    def _detect_cross_references(self, text: str) -> List[str]:
        """
        Detect cross-references in text.
        
        Returns list of reference strings (HMRC IDs, section numbers, etc.)
        """
        refs = []
        
        # HMRC manual IDs
        refs.extend(self._extract_all_section_ids(text))
        
        # Section/paragraph references
        for pattern in self.CROSS_REF_PATTERNS:
            for match in pattern.finditer(text):
                refs.append(f"section {match.group(1)}")
        
        return list(set(refs))
    
    def _has_condition_list(self, text: str) -> bool:
        """Check if text contains a condition list."""
        has_start = bool(self.CONDITION_START_PATTERN.search(text))
        has_items = bool(self.CONDITION_ITEM_PATTERN.search(text))
        return has_start and has_items
    
    def _has_definition(self, text: str) -> bool:
        """Check if text contains a definition."""
        return any(p.search(text) for p in self.DEFINITION_PATTERNS)
    
    def _has_example(self, text: str) -> bool:
        """Check if text contains a worked example."""
        return any(p.search(text) for p in self.EXAMPLE_PATTERNS)
    
    def _has_deadline(self, text: str) -> bool:
        """Check if text contains deadline information."""
        return any(p.search(text) for p in self.DEADLINE_PATTERNS)
    
    def _has_penalty_info(self, text: str) -> bool:
        """Check if text contains penalty information."""
        return any(p.search(text) for p in self.PENALTY_PATTERNS)
    
    def _has_contact_info(self, text: str) -> bool:
        """Check if text contains contact information."""
        return any(p.search(text) for p in self.CONTACT_PATTERNS)
    
    def _has_table_reference(self, text: str) -> bool:
        """Check if text references a table."""
        table_patterns = [
            r'\b(?:see|refer\s+to)\s+(?:the\s+)?table\b',
            r'\btable\s+(?:below|above|following)\b',
            r'\bthe\s+following\s+table\b',
        ]
        return any(re.search(p, text, re.I) for p in table_patterns)
    
    # ==========================================================================
    # CITATION GENERATION
    # ==========================================================================
    
    def _generate_citable_reference(
        self,
        document_title: str,
        section_title: str,
        heading_path: str,
        section_id: Optional[str],
        paragraph_number: Optional[str],
        source_url: str
    ) -> str:
        """
        Generate a citable reference for legal documents.
        
        Format varies based on available metadata:
        - HMRC Manual: "HMRC VAT Manual, VATREG02200, Para 2.1"
        - GOV.UK: "GOV.UK, VAT Registration > Who must register"
        """
        parts = []
        
        # Determine source type
        if section_id:
            # HMRC manual reference
            manual_name = self._infer_manual_name(section_id)
            parts.append(f"HMRC {manual_name}")
            parts.append(section_id)
            if paragraph_number:
                parts.append(f"Para {paragraph_number}")
        else:
            # GOV.UK reference
            parts.append("GOV.UK")
            if heading_path and heading_path != document_title:
                parts.append(heading_path)
            elif section_title:
                parts.append(section_title)
            if paragraph_number:
                parts.append(f"Para {paragraph_number}")
        
        return ", ".join(parts)
    
    def _infer_manual_name(self, section_id: str) -> str:
        """Infer the manual name from section ID prefix."""
        prefix_map = {
            "VAT": "VAT Manual",
            "CTM": "Corporation Tax Manual",
            "CG": "Capital Gains Manual",
            "BIM": "Business Income Manual",
            "EIM": "Employment Income Manual",
            "TSEM": "Trusts Manual",
            "SAIM": "Savings Manual",
            "PIM": "Property Income Manual",
            "NIM": "National Insurance Manual",
            "PAYE": "PAYE Manual",
            "CH": "Compliance Handbook",
        }
        
        for prefix, name in prefix_map.items():
            if section_id.upper().startswith(prefix):
                return name
        return "Manual"
    
    # ==========================================================================
    # SPLITTING METHODS
    # ==========================================================================
    
    def _find_condition_list_boundaries(self, text: str) -> List[Tuple[int, int]]:
        """
        Find start and end positions of condition lists in text.
        
        Returns list of (start, end) tuples.
        """
        boundaries = []
        
        # Find condition list starts
        for match in self.CONDITION_START_PATTERN.finditer(text):
            start = match.start()
            
            # Find the end - look for next paragraph break after last (letter) item
            remaining = text[start:]
            items = list(self.CONDITION_ITEM_PATTERN.finditer(remaining))
            
            if items:
                # Find end of last item
                last_item_start = items[-1].end()
                
                # Look for double newline or next section
                end_search = remaining[last_item_start:]
                para_break = end_search.find('\n\n')
                
                if para_break != -1:
                    end = start + last_item_start + para_break
                else:
                    end = len(text)
                
                boundaries.append((start, min(end, len(text))))
        
        return boundaries
    
    def _split_preserving_lists(
        self, 
        text: str, 
        max_size: int
    ) -> List[str]:
        """
        Split text while preserving condition lists intact.
        
        If a condition list exceeds max_size, it gets its own chunk.
        """
        if len(text) <= max_size:
            return [text]
        
        pieces = []
        list_boundaries = self._find_condition_list_boundaries(text)
        
        if not list_boundaries:
            # No condition lists, use standard splitting
            return self._split_at_boundaries(text, max_size)
        
        # Process text with condition list awareness
        current_pos = 0
        current_chunk = []
        current_size = 0
        
        for list_start, list_end in list_boundaries:
            # Add text before the list
            before_list = text[current_pos:list_start].strip()
            if before_list:
                if current_size + len(before_list) > max_size and current_chunk:
                    pieces.append('\n'.join(current_chunk))
                    current_chunk = []
                    current_size = 0
                current_chunk.append(before_list)
                current_size += len(before_list)
            
            # Handle the condition list itself
            list_text = text[list_start:list_end].strip()
            
            if current_size + len(list_text) > max_size:
                # Save current chunk
                if current_chunk:
                    pieces.append('\n'.join(current_chunk))
                    current_chunk = []
                    current_size = 0
                
                # List might be too big for a single chunk
                if len(list_text) > self.config.max_condition_list_size:
                    # Split the list (last resort)
                    pieces.extend(self._split_at_boundaries(list_text, max_size))
                else:
                    # Keep list together even if over max_size
                    pieces.append(list_text)
            else:
                current_chunk.append(list_text)
                current_size += len(list_text)
            
            current_pos = list_end
        
        # Handle remaining text
        remaining = text[current_pos:].strip()
        if remaining:
            if current_size + len(remaining) > max_size and current_chunk:
                pieces.append('\n'.join(current_chunk))
                pieces.extend(self._split_at_boundaries(remaining, max_size))
            else:
                current_chunk.append(remaining)
                pieces.append('\n'.join(current_chunk))
        elif current_chunk:
            pieces.append('\n'.join(current_chunk))
        
        return [p for p in pieces if p.strip()]
    
    def _split_at_boundaries(
        self, 
        text: str, 
        max_size: int
    ) -> List[str]:
        """
        Split text at natural boundaries (paragraphs, sentences).
        """
        if len(text) <= max_size:
            return [text]
        
        pieces = []
        remaining = text
        
        # Patterns for split points (in priority order)
        para_pattern = re.compile(r'\n\n+')
        sentence_pattern = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')
        
        while remaining:
            if len(remaining) <= max_size:
                pieces.append(remaining)
                break
            
            chunk_candidate = remaining[:max_size]
            split_point = max_size
            
            # Try paragraph boundary
            para_matches = list(para_pattern.finditer(chunk_candidate))
            if para_matches:
                split_point = para_matches[-1].end()
            else:
                # Try sentence boundary
                sent_matches = list(sentence_pattern.finditer(chunk_candidate))
                if sent_matches:
                    split_point = sent_matches[-1].end()
                else:
                    # Last resort: find last space
                    last_space = chunk_candidate.rfind(' ')
                    if last_space > max_size // 2:
                        split_point = last_space
            
            pieces.append(remaining[:split_point].strip())
            remaining = remaining[split_point:].strip()
        
        return [p for p in pieces if p]
    
    # ==========================================================================
    # MAIN CHUNKING METHODS
    # ==========================================================================
    
    def _chunk_section(
        self,
        section: ContentSection,
        start_index: int,
        document_title: str,
        source_url: str
    ) -> List[LegalChunk]:
        """
        Chunk a single section with legal awareness.
        """
        chunks = []
        
        # Build full content
        full_content = f"## {section.heading}\n\n{section.content}" if section.heading else section.content
        
        # Skip if too short
        if len(full_content) < self.config.min_chunk_size:
            return []
        
        # Extract section-level metadata
        section_id = self._extract_hmrc_section_id(full_content) if self.config.extract_hmrc_section_ids else None
        
        # Determine splitting strategy based on content
        if self.config.preserve_condition_lists and self._has_condition_list(full_content):
            pieces = self._split_preserving_lists(full_content, self.config.max_chunk_size)
        else:
            pieces = self._split_at_boundaries(full_content, self.config.target_chunk_size)
        
        # Create chunks
        char_pos = 0
        for i, piece in enumerate(pieces):
            # Extract chunk-specific metadata
            paragraph_num = self._extract_paragraph_number(piece) if self.config.extract_paragraph_numbers else None
            
            # Generate citation
            citable_ref = None
            if self.config.generate_citable_reference:
                citable_ref = self._generate_citable_reference(
                    document_title=document_title,
                    section_title=section.heading,
                    heading_path=section.heading_path,
                    section_id=section_id,
                    paragraph_number=paragraph_num,
                    source_url=source_url
                )
            
            # Detect content characteristics
            content_type = self._detect_content_type(piece) if self.config.detect_content_type else LegalContentType.GENERAL
            cross_refs = self._detect_cross_references(piece)
            
            # Remove the section_id from cross_refs if it matches the section's own ID
            if section_id and section_id in cross_refs:
                cross_refs.remove(section_id)
            
            chunk = LegalChunk(
                content=piece,
                chunk_index=start_index + i,
                total_chunks=0,  # Set later
                char_start=char_pos,
                char_end=char_pos + len(piece),
                section_title=section.heading,
                heading_path=section.heading_path,
                heading_level=section.level,
                section_id=section_id,
                paragraph_number=paragraph_num,
                citable_reference=citable_ref,
                content_type=content_type,
                contains_condition_list=self._has_condition_list(piece),
                contains_definition=self._has_definition(piece),
                contains_example=self._has_example(piece),
                contains_table_reference=self._has_table_reference(piece),
                contains_deadline=self._has_deadline(piece),
                contains_penalty_info=self._has_penalty_info(piece),
                contains_contact_info=self._has_contact_info(piece),
                cross_references=cross_refs,
                has_overlap_with_previous=(i > 0),
            )
            
            chunks.append(chunk)
            char_pos += len(piece)
        
        return chunks
    
    def chunk_document(
        self,
        parsed_doc: ParsedDocument,
        source_url: str,
        document_title: Optional[str] = None
    ) -> List[LegalChunk]:
        """
        Chunk an entire parsed document with legal awareness.
        
        Args:
            parsed_doc: ParsedDocument from content_parser
            source_url: URL of the source document
            document_title: Override title (uses parsed_doc.title if None)
        
        Returns:
            List of LegalChunks with full metadata
        """
        title = document_title or parsed_doc.title
        all_chunks = []
        current_index = 0
        
        if not parsed_doc.sections:
            # No sections - treat entire content as one section
            if parsed_doc.full_text:
                section = ContentSection(
                    heading=title,
                    level=1,
                    content=parsed_doc.full_text,
                    heading_path=title
                )
                all_chunks = self._chunk_section(section, 0, title, source_url)
        else:
            # Process each section
            for section in parsed_doc.sections:
                section_chunks = self._chunk_section(
                    section, current_index, title, source_url
                )
                all_chunks.extend(section_chunks)
                current_index += len(section_chunks)
        
        # Set total_chunks on all chunks
        total = len(all_chunks)
        for chunk in all_chunks:
            chunk.total_chunks = total
        
        logger.info(f"Created {total} legal chunks from '{title}'")
        return all_chunks
    
    def chunk_text(
        self,
        text: str,
        source_url: str,
        title: str = "Document",
        heading_path: Optional[str] = None
    ) -> List[LegalChunk]:
        """
        Chunk raw text with legal awareness.
        
        Args:
            text: Plain text to chunk
            source_url: URL for citation
            title: Title for the content
            heading_path: Optional heading path
        
        Returns:
            List of LegalChunks
        """
        section = ContentSection(
            heading=title,
            level=1,
            content=text,
            heading_path=heading_path or title
        )
        
        chunks = self._chunk_section(section, 0, title, source_url)
        total = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total
        
        return chunks
    
    def get_chunk_stats(self, chunks: List[LegalChunk]) -> Dict[str, Any]:
        """
        Get detailed statistics about chunks.
        """
        if not chunks:
            return {"count": 0}
        
        sizes = [len(c.content) for c in chunks]
        
        return {
            "count": len(chunks),
            "total_chars": sum(sizes),
            "avg_size": sum(sizes) / len(sizes),
            "min_size": min(sizes),
            "max_size": max(sizes),
            "est_total_tokens": sum(len(c.content) // 4 for c in chunks),
            "sections_covered": len(set(c.section_title for c in chunks)),
            "with_section_ids": sum(1 for c in chunks if c.section_id),
            "with_condition_lists": sum(1 for c in chunks if c.contains_condition_list),
            "with_definitions": sum(1 for c in chunks if c.contains_definition),
            "with_examples": sum(1 for c in chunks if c.contains_example),
            "with_deadlines": sum(1 for c in chunks if c.contains_deadline),
            "with_penalties": sum(1 for c in chunks if c.contains_penalty_info),
            "with_contacts": sum(1 for c in chunks if c.contains_contact_info),
            "content_types": {
                ct.value: sum(1 for c in chunks if c.content_type == ct)
                for ct in LegalContentType
            },
            "total_cross_refs": sum(len(c.cross_references) for c in chunks),
        }
