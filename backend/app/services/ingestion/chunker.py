"""
Semantic Chunker

Splits documents into meaningful chunks for RAG retrieval.
Uses document structure (headings) rather than arbitrary character counts.

Key Concepts:

1. WHY CHUNKING MATTERS:
   LLMs have context limits, and retrieving entire documents is wasteful.
   We want to retrieve only the relevant pieces. But HOW we split matters:
   
   Bad:  "You must register for VAT if" | "your turnover exceeds £90,000"
   Good: "You must register for VAT if your turnover exceeds £90,000..."
   
   The first splits mid-sentence — neither chunk answers the full question.
   The second keeps the complete thought together.

2. SEMANTIC VS ARBITRARY CHUNKING:
   - Arbitrary: Split every N characters/tokens regardless of content
   - Semantic: Split at natural boundaries (headings, paragraphs, topics)
   
   We use semantic chunking because:
   - Each chunk is a complete thought
   - Better retrieval precision
   - Easier to cite sources accurately

3. OVERLAP:
   We include some overlap between chunks so that:
   - Context isn't lost at boundaries
   - Related information stays connected
   - Retrieval can catch edge cases

Analogy:
If you're helping someone study for an exam by making flashcards:
- Bad: Cut the textbook every 500 characters (mid-sentence, mid-concept)
- Good: One flashcard per concept, with enough context to be self-explanatory
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import re
import logging
from .content_parser import ContentSection, ParsedDocument

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """
    A single chunk of document content ready for embedding.
    
    Each chunk is designed to be:
    - Self-contained (can be understood without other chunks)
    - Appropriately sized for embedding models
    - Traceable back to source (section, position)
    """
    content: str
    
    # Position in document
    chunk_index: int
    total_chunks: int  # Set after all chunks created
    char_start: int
    char_end: int
    
    # Context from document structure
    section_title: str
    heading_path: str
    heading_level: int
    
    # For overlap tracking
    has_overlap_with_previous: bool = False
    overlap_text: str = ""  # The overlapping portion


@dataclass
class ChunkingConfig:
    """
    Configuration for the chunking process.
    
    These values are tuned for:
    - OpenAI text-embedding-3-small (8191 token limit)
    - UK tax guidance content structure
    - Optimal retrieval precision
    """
    # Target chunk size (in characters, roughly 4 chars = 1 token)
    min_chunk_size: int = 500  # Don't create tiny chunks
    max_chunk_size: int = 2000  # ~500 tokens, well under embedding limit
    target_chunk_size: int = 1200  # ~300 tokens, sweet spot for retrieval
    
    # Overlap between consecutive chunks (helps with context continuity)
    overlap_size: int = 100  # ~25 tokens of overlap
    
    # Respect document structure
    split_on_headings: bool = True  # Always start new chunk on heading
    keep_heading_with_content: bool = True  # Include heading text in chunk
    
    # Minimum content to create a chunk (avoid empty/tiny chunks)
    min_content_length: int = 50


class SemanticChunker:
    """
    Splits documents into meaningful chunks using document structure.
    
    Strategy:
    1. Use heading boundaries as primary split points
    2. If a section is too long, split at paragraph boundaries
    3. If still too long, split at sentence boundaries
    4. Never split mid-sentence if possible
    5. Add overlap between chunks for context continuity
    
    Usage:
        chunker = SemanticChunker()
        chunks = chunker.chunk_document(parsed_doc)
        for chunk in chunks:
            print(f"Chunk {chunk.chunk_index}: {len(chunk.content)} chars")
            print(f"  Section: {chunk.section_title}")
    """
    
    # Regex patterns for finding split points
    PARAGRAPH_PATTERN = re.compile(r'\n\n+')
    SENTENCE_PATTERN = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')
    
    def __init__(self, config: Optional[ChunkingConfig] = None):
        """
        Initialize chunker with configuration.
        
        Args:
            config: ChunkingConfig or None for defaults
        """
        self.config = config or ChunkingConfig()
    
    def _split_text_at_boundaries(
        self, 
        text: str, 
        max_size: int,
        boundaries: List[str] = None
    ) -> List[str]:
        """
        Split text at natural boundaries, respecting max_size.
        
        Tries boundaries in order:
        1. Paragraphs (double newline)
        2. Sentences (period + space + capital)
        3. Any whitespace (last resort)
        
        Args:
            text: Text to split
            max_size: Maximum size of each piece
            boundaries: Custom boundary patterns (optional)
        
        Returns:
            List of text pieces
        """
        if len(text) <= max_size:
            return [text]
        
        pieces = []
        remaining = text
        
        while remaining:
            if len(remaining) <= max_size:
                pieces.append(remaining)
                break
            
            # Find best split point within max_size
            split_point = max_size
            chunk_candidate = remaining[:max_size]
            
            # Try paragraph boundary first
            para_matches = list(self.PARAGRAPH_PATTERN.finditer(chunk_candidate))
            if para_matches:
                # Use last paragraph break within limit
                split_point = para_matches[-1].end()
            else:
                # Try sentence boundary
                sent_matches = list(self.SENTENCE_PATTERN.finditer(chunk_candidate))
                if sent_matches:
                    # Use last sentence break within limit
                    split_point = sent_matches[-1].end()
                else:
                    # Last resort: find last whitespace
                    last_space = chunk_candidate.rfind(' ')
                    if last_space > max_size // 2:  # Only if reasonable
                        split_point = last_space
            
            pieces.append(remaining[:split_point].strip())
            remaining = remaining[split_point:].strip()
        
        return [p for p in pieces if p]  # Remove empty pieces
    
    def _create_overlap(self, previous_chunk: str, overlap_size: int) -> str:
        """
        Extract overlap text from end of previous chunk.
        
        We want to include the last complete sentence(s) that fit
        within overlap_size, not arbitrary characters.
        
        Args:
            previous_chunk: Content of the previous chunk
            overlap_size: Target overlap size in characters
        
        Returns:
            Overlap text to prepend to next chunk
        """
        if not previous_chunk or overlap_size <= 0:
            return ""
        
        # Get last portion
        tail = previous_chunk[-overlap_size * 2:]  # Get extra for finding sentence boundary
        
        # Find sentence start (after period + space or at start)
        sentences = self.SENTENCE_PATTERN.split(tail)
        if sentences:
            # Take last sentence(s) that fit in overlap_size
            overlap_parts = []
            total_len = 0
            for sent in reversed(sentences):
                if total_len + len(sent) <= overlap_size:
                    overlap_parts.insert(0, sent)
                    total_len += len(sent)
                else:
                    break
            
            if overlap_parts:
                return ' '.join(overlap_parts).strip()
        
        # Fallback: just take last overlap_size characters at word boundary
        tail = previous_chunk[-overlap_size:]
        first_space = tail.find(' ')
        if first_space > 0:
            return tail[first_space:].strip()
        return tail.strip()
    
    def _chunk_section(
        self, 
        section: ContentSection,
        start_index: int
    ) -> List[Chunk]:
        """
        Chunk a single section, respecting size limits.
        
        Args:
            section: ContentSection from parser
            start_index: Starting chunk index
        
        Returns:
            List of Chunks from this section
        """
        chunks = []
        
        # Build full content with heading if configured
        if self.config.keep_heading_with_content and section.heading:
            full_content = f"## {section.heading}\n\n{section.content}"
        else:
            full_content = section.content
        
        # Skip if too short
        if len(full_content) < self.config.min_content_length:
            logger.debug(f"Skipping short section: {section.heading}")
            return []
        
        # Split if too long
        if len(full_content) <= self.config.max_chunk_size:
            # Section fits in one chunk
            chunks.append(Chunk(
                content=full_content,
                chunk_index=start_index,
                total_chunks=0,  # Set later
                char_start=0,
                char_end=len(full_content),
                section_title=section.heading,
                heading_path=section.heading_path,
                heading_level=section.level
            ))
        else:
            # Need to split section
            pieces = self._split_text_at_boundaries(
                full_content, 
                self.config.target_chunk_size
            )
            
            char_pos = 0
            for i, piece in enumerate(pieces):
                # Add overlap from previous chunk (within same section)
                overlap_text = ""
                if i > 0 and self.config.overlap_size > 0:
                    overlap_text = self._create_overlap(
                        pieces[i-1], 
                        self.config.overlap_size
                    )
                
                content = piece
                if overlap_text and not piece.startswith(overlap_text):
                    # Add overlap indicator for clarity
                    content = f"[...] {piece}"
                
                chunks.append(Chunk(
                    content=content,
                    chunk_index=start_index + i,
                    total_chunks=0,  # Set later
                    char_start=char_pos,
                    char_end=char_pos + len(piece),
                    section_title=section.heading,
                    heading_path=section.heading_path,
                    heading_level=section.level,
                    has_overlap_with_previous=(i > 0),
                    overlap_text=overlap_text
                ))
                char_pos += len(piece)
        
        return chunks
    
    def chunk_document(self, parsed_doc: ParsedDocument) -> List[Chunk]:
        """
        Chunk an entire parsed document.
        
        Args:
            parsed_doc: ParsedDocument from content_parser
        
        Returns:
            List of Chunks covering the entire document
        """
        all_chunks = []
        current_index = 0
        
        if not parsed_doc.sections:
            # No sections found — treat entire content as one section
            if parsed_doc.full_text:
                section = ContentSection(
                    heading=parsed_doc.title,
                    level=1,
                    content=parsed_doc.full_text,
                    heading_path=parsed_doc.title
                )
                all_chunks = self._chunk_section(section, 0)
        else:
            # Process each section
            for section in parsed_doc.sections:
                section_chunks = self._chunk_section(section, current_index)
                all_chunks.extend(section_chunks)
                current_index += len(section_chunks)
        
        # Set total_chunks on all chunks
        total = len(all_chunks)
        for chunk in all_chunks:
            chunk.total_chunks = total
        
        logger.info(f"Created {total} chunks from '{parsed_doc.title}'")
        return all_chunks
    
    def chunk_text(
        self, 
        text: str, 
        title: str = "Document",
        heading_path: str = None
    ) -> List[Chunk]:
        """
        Chunk raw text (without HTML parsing).
        
        Useful for already-cleaned content.
        
        Args:
            text: Plain text to chunk
            title: Title for the content
            heading_path: Optional heading path for context
        
        Returns:
            List of Chunks
        """
        section = ContentSection(
            heading=title,
            level=1,
            content=text,
            heading_path=heading_path or title
        )
        
        chunks = self._chunk_section(section, 0)
        total = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total
        
        return chunks
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Rule of thumb for English: ~4 characters per token.
        This is a rough estimate — actual tokenization varies.
        
        Args:
            text: Text to estimate
        
        Returns:
            Estimated token count
        """
        return len(text) // 4
    
    def get_chunk_stats(self, chunks: List[Chunk]) -> dict:
        """
        Get statistics about a list of chunks.
        
        Useful for tuning chunking parameters.
        
        Args:
            chunks: List of Chunks to analyze
        
        Returns:
            Dictionary with statistics
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
            "est_total_tokens": sum(self.estimate_tokens(c.content) for c in chunks),
            "est_avg_tokens": sum(self.estimate_tokens(c.content) for c in chunks) / len(chunks),
            "sections_covered": len(set(c.section_title for c in chunks)),
            "chunks_with_overlap": sum(1 for c in chunks if c.has_overlap_with_previous)
        }
