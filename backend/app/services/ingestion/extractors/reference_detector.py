"""
Reference Detector

Detects cross-references between documents and sections in UK tax content.
Used to build the cross-reference graph for context expansion during retrieval.

Key Features:
- HMRC manual references (VATREG02200, CTM01500)
- Section/paragraph references ("see section 3.2")
- Defined term references ("taxable turnover" as defined)
- Legislation references (Finance Act 2024)
- Internal GOV.UK links
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import re
import logging

from .base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


@dataclass
class DetectedReference:
    """Represents a cross-reference detected in text."""
    
    # Reference identification
    reference_type: str  # hmrc_manual, section, legislation, definition, internal_link
    reference_text: str  # The actual reference text (e.g., "VATREG02200")
    
    # Normalized target
    target_normalized: str  # Normalized form for matching
    target_url: Optional[str] = None  # Full URL if determinable
    
    # Context
    context: str = ""  # Surrounding text for understanding
    position: int = 0  # Position in source text
    
    # Relationship
    relationship_type: str = "references"  # references, defines, supersedes, etc.
    strength: str = "explicit"  # explicit, implicit, inferred
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "reference_type": self.reference_type,
            "reference_text": self.reference_text,
            "target_normalized": self.target_normalized,
            "target_url": self.target_url,
            "context": self.context,
            "position": self.position,
            "relationship_type": self.relationship_type,
            "strength": self.strength,
        }


class ReferenceDetector(BaseExtractor):
    """
    Detects cross-references in document text.
    
    Reference types detected:
    1. HMRC Manual References (VATREG02200)
    2. Section/Paragraph References (see section 3.2)
    3. Legislation References (Finance Act 2024, s.45)
    4. Definition References ("taxable turnover" as defined in...)
    5. Internal GOV.UK Links (/guidance/vat-registration)
    """
    
    # HMRC manual section patterns
    HMRC_MANUAL_PATTERNS = [
        # VAT manuals
        (re.compile(r'\b(VAT(?:REG|SC|TOS|INF|IT|NOT|POSS|FRS|REC|AOS|GEN|ADJ|PE|RA|SG|AM|DT|LAND|FIN|FS)\d{5})\b', re.I), 'vat_manual'),
        # Corporation Tax Manual
        (re.compile(r'\b(CTM\d{5})\b', re.I), 'ct_manual'),
        # Capital Gains Manual
        (re.compile(r'\b(CG\d{5})\b', re.I), 'cg_manual'),
        # Business Income Manual
        (re.compile(r'\b(BIM\d{5})\b', re.I), 'bim_manual'),
        # Employment Income Manual
        (re.compile(r'\b(EIM\d{5})\b', re.I), 'eim_manual'),
        # National Insurance Manual
        (re.compile(r'\b(NIM\d{5})\b', re.I), 'ni_manual'),
        # PAYE Manual
        (re.compile(r'\b(PAYE\d{5})\b', re.I), 'paye_manual'),
        # Compliance Handbook
        (re.compile(r'\b(CH\d{5})\b', re.I), 'compliance_handbook'),
        # Trusts Manual
        (re.compile(r'\b(TSEM\d{5})\b', re.I), 'trusts_manual'),
    ]
    
    # Section/paragraph reference patterns
    SECTION_PATTERNS = [
        (re.compile(r'(?:see|refer\s+to)\s+(?:section|paragraph|para\.?)\s+([\d.]+)', re.I), 'section_ref'),
        (re.compile(r'(?:as\s+(?:explained|described|set\s+out)\s+in)\s+(?:section|paragraph)\s+([\d.]+)', re.I), 'section_ref'),
        (re.compile(r'(?:section|paragraph|para\.?)\s+([\d.]+)\s+(?:above|below|explains?)', re.I), 'section_ref'),
    ]
    
    # Legislation patterns
    LEGISLATION_PATTERNS = [
        # UK Acts
        (re.compile(r'((?:Finance|Tax(?:es)?|VAT|Income\s+Tax|Corporation\s+Tax)\s+Act\s+\d{4})', re.I), 'uk_act'),
        # Section references in legislation
        (re.compile(r'(?:section|s\.?)\s*(\d+[A-Z]?)\s+(?:of\s+)?(?:the\s+)?(\w+\s+Act\s+\d{4})', re.I), 'act_section'),
        # SI references
        (re.compile(r'(?:SI|S\.I\.)\s*(\d{4}/\d+)', re.I), 'statutory_instrument'),
        # EU regulations (still referenced)
        (re.compile(r'(?:EU\s+)?(?:Regulation|Directive)\s+(\d+/\d+)', re.I), 'eu_regulation'),
    ]
    
    # Definition reference patterns
    DEFINITION_PATTERNS = [
        (re.compile(r'[\'"]([^\'\"]+)[\'"]\s+(?:as\s+defined|has\s+the\s+meaning|means)', re.I), 'definition'),
        (re.compile(r'(?:the\s+term\s+)?[\'"]([^\'\"]+)[\'"]\s+is\s+defined\s+in', re.I), 'definition'),
        (re.compile(r'(?:within\s+the\s+meaning\s+of)\s+([^,.]+)', re.I), 'definition'),
    ]
    
    # Internal GOV.UK link patterns
    GOVUK_LINK_PATTERNS = [
        (re.compile(r'(?:gov\.uk|GOV\.UK)(/[a-z0-9\-/]+)', re.I), 'govuk_link'),
        (re.compile(r'(?:see|visit|go\s+to)\s+(?:the\s+)?([a-z\-]+)\s+(?:page|guidance|section)\s+on\s+GOV\.UK', re.I), 'govuk_page'),
    ]
    
    # HMRC manual URL bases
    MANUAL_URL_BASES = {
        'vat_manual': 'https://www.gov.uk/hmrc-internal-manuals/vat-',
        'ct_manual': 'https://www.gov.uk/hmrc-internal-manuals/company-taxation-manual/',
        'cg_manual': 'https://www.gov.uk/hmrc-internal-manuals/capital-gains-manual/',
        'bim_manual': 'https://www.gov.uk/hmrc-internal-manuals/business-income-manual/',
        'eim_manual': 'https://www.gov.uk/hmrc-internal-manuals/employment-income-manual/',
        'ni_manual': 'https://www.gov.uk/hmrc-internal-manuals/national-insurance-manual/',
        'paye_manual': 'https://www.gov.uk/hmrc-internal-manuals/paye-manual/',
    }
    
    def __init__(self):
        super().__init__()
    
    def extract(
        self,
        html_content: Optional[str],
        text_content: str,
        source_url: str,
        **kwargs
    ) -> ExtractionResult[DetectedReference]:
        """Detect all cross-references in document."""
        result = ExtractionResult[DetectedReference](source_url=source_url)
        
        if not text_content:
            return result
        
        try:
            # Detect HMRC manual references
            result.items.extend(self._detect_hmrc_references(text_content))
            
            # Detect section references
            result.items.extend(self._detect_section_references(text_content))
            
            # Detect legislation references
            result.items.extend(self._detect_legislation_references(text_content))
            
            # Detect definition references
            result.items.extend(self._detect_definition_references(text_content))
            
            # Detect GOV.UK links
            if html_content:
                result.items.extend(self._detect_govuk_links(html_content, text_content))
            
            # Deduplicate
            result.items = self._deduplicate_references(result.items)
            
            logger.info(f"Detected {len(result.items)} references in {source_url}")
            
        except Exception as e:
            result.add_error(f"Reference detection failed: {str(e)}")
        
        return result
    
    def _detect_hmrc_references(self, text: str) -> List[DetectedReference]:
        """Detect HMRC manual references."""
        refs = []
        
        for pattern, manual_type in self.HMRC_MANUAL_PATTERNS:
            for match in pattern.finditer(text):
                ref_text = match.group(1).upper()
                
                # Get context
                context_start = max(0, match.start() - 50)
                context_end = min(len(text), match.end() + 50)
                context = text[context_start:context_end]
                
                # Determine relationship type from context
                relationship = self._infer_relationship(context)
                
                # Try to construct URL
                target_url = self._construct_manual_url(ref_text, manual_type)
                
                refs.append(DetectedReference(
                    reference_type='hmrc_manual',
                    reference_text=ref_text,
                    target_normalized=ref_text.lower(),
                    target_url=target_url,
                    context=context,
                    position=match.start(),
                    relationship_type=relationship,
                    strength='explicit',
                ))
        
        return refs
    
    def _detect_section_references(self, text: str) -> List[DetectedReference]:
        """Detect section/paragraph references."""
        refs = []
        
        for pattern, ref_type in self.SECTION_PATTERNS:
            for match in pattern.finditer(text):
                section_num = match.group(1)
                
                context_start = max(0, match.start() - 30)
                context_end = min(len(text), match.end() + 30)
                
                refs.append(DetectedReference(
                    reference_type='section',
                    reference_text=f"section {section_num}",
                    target_normalized=f"section_{section_num}",
                    context=text[context_start:context_end],
                    position=match.start(),
                    relationship_type='references',
                    strength='explicit',
                ))
        
        return refs
    
    def _detect_legislation_references(self, text: str) -> List[DetectedReference]:
        """Detect legislation references."""
        refs = []
        
        for pattern, ref_type in self.LEGISLATION_PATTERNS:
            for match in pattern.finditer(text):
                if ref_type == 'act_section' and match.lastindex >= 2:
                    ref_text = f"s.{match.group(1)} {match.group(2)}"
                    normalized = f"{match.group(2).lower().replace(' ', '_')}_s{match.group(1)}"
                else:
                    ref_text = match.group(1)
                    normalized = ref_text.lower().replace(' ', '_')
                
                context_start = max(0, match.start() - 30)
                context_end = min(len(text), match.end() + 30)
                
                refs.append(DetectedReference(
                    reference_type='legislation',
                    reference_text=ref_text,
                    target_normalized=normalized,
                    context=text[context_start:context_end],
                    position=match.start(),
                    relationship_type='cites',
                    strength='explicit',
                ))
        
        return refs
    
    def _detect_definition_references(self, text: str) -> List[DetectedReference]:
        """Detect references to defined terms."""
        refs = []
        
        for pattern, ref_type in self.DEFINITION_PATTERNS:
            for match in pattern.finditer(text):
                term = match.group(1)
                
                context_start = max(0, match.start() - 30)
                context_end = min(len(text), match.end() + 50)
                
                refs.append(DetectedReference(
                    reference_type='definition',
                    reference_text=term,
                    target_normalized=term.lower().replace(' ', '_'),
                    context=text[context_start:context_end],
                    position=match.start(),
                    relationship_type='defines',
                    strength='explicit',
                ))
        
        return refs
    
    def _detect_govuk_links(self, html: str, text: str) -> List[DetectedReference]:
        """Detect GOV.UK internal links from HTML."""
        refs = []
        
        # Parse HTML for actual links
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Check if internal GOV.UK link
            if href.startswith('/') or 'gov.uk' in href:
                # Normalize URL
                if href.startswith('/'):
                    full_url = f"https://www.gov.uk{href}"
                else:
                    full_url = href
                
                # Skip anchors and non-content links
                if '#' in href and href.index('#') == 0:
                    continue
                if any(skip in href for skip in ['/sign-in', '/register', '/search']):
                    continue
                
                link_text = self.clean_text(link.get_text())
                
                refs.append(DetectedReference(
                    reference_type='internal_link',
                    reference_text=link_text or href,
                    target_normalized=href.lower(),
                    target_url=full_url,
                    context=link_text,
                    relationship_type='links_to',
                    strength='explicit',
                ))
        
        return refs
    
    def _infer_relationship(self, context: str) -> str:
        """Infer the relationship type from context."""
        context_lower = context.lower()
        
        if any(w in context_lower for w in ['see', 'refer to', 'explained in']):
            return 'references'
        elif any(w in context_lower for w in ['supersedes', 'replaces', 'replaced by']):
            return 'supersedes'
        elif any(w in context_lower for w in ['defines', 'definition']):
            return 'defines'
        elif any(w in context_lower for w in ['example', 'such as']):
            return 'example_of'
        
        return 'references'
    
    def _construct_manual_url(self, ref: str, manual_type: str) -> Optional[str]:
        """Try to construct the URL for an HMRC manual reference."""
        base = self.MANUAL_URL_BASES.get(manual_type)
        if not base:
            return None
        
        # Extract manual section prefix and number
        # e.g., VATREG02200 -> vatreg02200
        return f"https://www.gov.uk/hmrc-internal-manuals/{ref.lower()}"
    
    def _deduplicate_references(self, refs: List[DetectedReference]) -> List[DetectedReference]:
        """Remove duplicate references."""
        seen = set()
        unique = []
        
        for ref in refs:
            key = (ref.reference_type, ref.target_normalized)
            if key not in seen:
                seen.add(key)
                unique.append(ref)
        
        return unique
    
    def has_references(self, text: str) -> bool:
        """Quick check if text contains cross-references."""
        # Check for any HMRC manual reference
        for pattern, _ in self.HMRC_MANUAL_PATTERNS:
            if pattern.search(text):
                return True
        
        # Check for section references
        if re.search(r'(?:see|refer\s+to)\s+(?:section|paragraph)', text, re.I):
            return True
        
        # Check for legislation
        if re.search(r'(?:Finance|Tax)\s+Act\s+\d{4}', text, re.I):
            return True
        
        return False
