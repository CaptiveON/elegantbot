"""
Content Parser

Cleans HTML from GOV.UK and extracts structured text content.
Preserves document hierarchy (headings) while removing noise.

Key Concepts:
- GOV.UK HTML is relatively clean but still has unnecessary elements
- We preserve heading structure for better chunking
- We convert to a structured format that captures both text and hierarchy

Analogy:
When you photocopy a textbook page, you want the content, not the
"Property of Library" stamps or the binding margin. This parser
does the same for HTML — keeps the educational content, removes
the website infrastructure.
"""

from bs4 import BeautifulSoup, NavigableString, Tag
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import re
import html
import logging

logger = logging.getLogger(__name__)


@dataclass
class ContentSection:
    """
    Represents a section of content with its heading hierarchy.
    
    A document becomes a list of these sections:
    [
        Section(heading="Overview", level=1, content="..."),
        Section(heading="Who needs to register", level=2, content="..."),
        ...
    ]
    
    This structure makes chunking much easier — we can split at
    section boundaries rather than arbitrary character counts.
    """
    heading: str
    level: int  # 1 = H1, 2 = H2, etc.
    content: str  # The text content under this heading
    heading_path: str  # Full path like "VAT Registration > Who needs to register"


@dataclass 
class ParsedDocument:
    """
    Result of parsing a GOV.UK document.
    
    Contains both the full cleaned text and the structured sections.
    The full text is useful for search, while sections help with chunking.
    """
    title: str
    full_text: str  # All content as plain text
    sections: List[ContentSection]  # Structured by headings
    headings: List[Dict[str, Any]]  # List of all headings with levels
    word_count: int
    has_content: bool


class ContentParser:
    """
    Parses and cleans HTML content from GOV.UK documents.
    
    Main responsibilities:
    1. Remove HTML noise (scripts, styles, navigation)
    2. Extract clean text while preserving structure
    3. Identify heading hierarchy for chunking
    4. Normalize whitespace and formatting
    
    Usage:
        parser = ContentParser()
        result = parser.parse(html_content, title="VAT Registration")
        print(result.full_text)
        for section in result.sections:
            print(f"{section.heading}: {len(section.content)} chars")
    """
    
    # HTML tags to completely remove (including their content)
    REMOVE_TAGS = [
        'script', 'style', 'nav', 'header', 'footer', 
        'aside', 'noscript', 'iframe', 'svg', 'form',
        'button', 'input', 'select', 'textarea'
    ]
    
    # Tags that represent structural breaks (insert newlines)
    BLOCK_TAGS = [
        'p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'li', 'tr', 'br', 'hr', 'blockquote', 'pre',
        'article', 'section', 'main'
    ]
    
    # Heading tags in order of importance
    HEADING_TAGS = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
    
    def __init__(self):
        """Initialize the parser"""
        pass
    
    def _remove_unwanted_tags(self, soup: BeautifulSoup) -> None:
        """Remove script, style, nav, and other non-content tags"""
        for tag_name in self.REMOVE_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()
        
        # Also remove comments
        for comment in soup.find_all(string=lambda t: isinstance(t, NavigableString) and t.strip().startswith('<!--')):
            comment.extract()
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text content.
        
        Steps:
        1. Decode HTML entities (&amp; → &)
        2. Normalize whitespace (multiple spaces → single space)
        3. Normalize line breaks
        4. Strip leading/trailing whitespace
        """
        if not text:
            return ""
        
        # Decode HTML entities
        text = html.unescape(text)
        
        # Replace multiple whitespace with single space
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Replace multiple newlines with double newline (paragraph break)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        # Final strip
        return text.strip()
    
    def _extract_text_with_structure(self, soup: BeautifulSoup) -> str:
        """
        Extract text while preserving structural information.
        
        Adds newlines after block elements to maintain readability.
        Preserves list structure by adding markers.
        """
        result = []
        
        def process_element(element, depth=0):
            if isinstance(element, NavigableString):
                text = str(element).strip()
                if text:
                    result.append(text)
            elif isinstance(element, Tag):
                tag_name = element.name.lower()
                
                # Skip removed tags
                if tag_name in self.REMOVE_TAGS:
                    return
                
                # Handle lists specially
                if tag_name == 'li':
                    result.append('\n• ')
                elif tag_name == 'ol':
                    pass  # Will handle numbered items differently if needed
                
                # Process children
                for child in element.children:
                    process_element(child, depth + 1)
                
                # Add newlines after block elements
                if tag_name in self.BLOCK_TAGS:
                    result.append('\n')
                
                # Extra newline after headings for visual separation
                if tag_name in self.HEADING_TAGS:
                    result.append('\n')
        
        process_element(soup)
        
        return self._clean_text(''.join(result))
    
    def _extract_headings(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract all headings with their levels and positions.
        
        Returns list like:
        [
            {"text": "VAT Registration", "level": 1, "tag": "h1"},
            {"text": "Who must register", "level": 2, "tag": "h2"},
            ...
        ]
        """
        headings = []
        
        for tag_name in self.HEADING_TAGS:
            for heading in soup.find_all(tag_name):
                text = self._clean_text(heading.get_text())
                if text:
                    level = int(tag_name[1])  # h1 → 1, h2 → 2, etc.
                    headings.append({
                        "text": text,
                        "level": level,
                        "tag": tag_name
                    })
        
        # Sort by position in document (BeautifulSoup maintains order)
        # This is already in document order from find_all
        return headings
    
    def _extract_sections(self, soup: BeautifulSoup, document_title: str) -> List[ContentSection]:
        """
        Extract content sections based on heading structure.
        
        This is the key method for enabling semantic chunking.
        Each section contains:
        - The heading text
        - The heading level (1-6)
        - All content until the next same-or-higher-level heading
        - The full heading path (for context)
        
        Example result:
        [
            Section("Overview", 2, "VAT is a tax on...", "VAT Registration > Overview"),
            Section("Who must register", 2, "You must register if...", "VAT Registration > Who must register")
        ]
        """
        sections = []
        current_path = [document_title]  # Stack for building heading paths
        
        # Get all elements in order
        all_elements = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'div', 'table'])
        
        current_heading = document_title
        current_level = 1
        current_content = []
        
        for element in all_elements:
            tag_name = element.name.lower()
            
            if tag_name in self.HEADING_TAGS:
                # Save previous section if it has content
                if current_content:
                    content_text = self._clean_text('\n'.join(current_content))
                    if content_text:
                        sections.append(ContentSection(
                            heading=current_heading,
                            level=current_level,
                            content=content_text,
                            heading_path=" > ".join(current_path)
                        ))
                
                # Start new section
                heading_text = self._clean_text(element.get_text())
                heading_level = int(tag_name[1])
                
                # Update heading path
                # Pop items from path until we're at parent level
                while len(current_path) > 1 and len(current_path) > heading_level:
                    current_path.pop()
                
                # Add new heading to path (unless it's the same as document title)
                if heading_text.lower() != document_title.lower():
                    if len(current_path) <= heading_level:
                        current_path.append(heading_text)
                    else:
                        current_path[-1] = heading_text
                
                current_heading = heading_text
                current_level = heading_level
                current_content = []
                
            else:
                # Add content to current section
                text = self._clean_text(element.get_text())
                if text:
                    current_content.append(text)
        
        # Don't forget the last section
        if current_content:
            content_text = self._clean_text('\n'.join(current_content))
            if content_text:
                sections.append(ContentSection(
                    heading=current_heading,
                    level=current_level,
                    content=content_text,
                    heading_path=" > ".join(current_path)
                ))
        
        return sections
    
    def parse(self, html_content: str, title: str = "Document") -> ParsedDocument:
        """
        Parse HTML content and extract structured text.
        
        Args:
            html_content: Raw HTML from GOV.UK
            title: Document title (used in heading paths)
        
        Returns:
            ParsedDocument with full text, sections, and metadata
        
        Example:
            parser = ContentParser()
            result = parser.parse("<h1>VAT</h1><p>VAT is...</p>", "VAT Guide")
            print(result.full_text)  # "VAT\n\nVAT is..."
            print(len(result.sections))  # Number of sections
        """
        if not html_content:
            return ParsedDocument(
                title=title,
                full_text="",
                sections=[],
                headings=[],
                word_count=0,
                has_content=False
            )
        
        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove unwanted elements
        self._remove_unwanted_tags(soup)
        
        # Extract full text
        full_text = self._extract_text_with_structure(soup)
        
        # Extract headings
        headings = self._extract_headings(soup)
        
        # Extract sections
        sections = self._extract_sections(soup, title)
        
        # If no sections were extracted, create one section with all content
        if not sections and full_text:
            sections = [ContentSection(
                heading=title,
                level=1,
                content=full_text,
                heading_path=title
            )]
        
        # Calculate word count
        word_count = len(full_text.split())
        
        return ParsedDocument(
            title=title,
            full_text=full_text,
            sections=sections,
            headings=headings,
            word_count=word_count,
            has_content=bool(full_text.strip())
        )
    
    def parse_gov_uk_document(self, gov_uk_doc) -> ParsedDocument:
        """
        Convenience method to parse a GovUKDocument directly.
        
        Args:
            gov_uk_doc: GovUKDocument from gov_uk_client
        
        Returns:
            ParsedDocument with extracted content
        """
        return self.parse(gov_uk_doc.body_html, gov_uk_doc.title)
