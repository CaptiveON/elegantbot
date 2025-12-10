"""
Metadata Extractor

Extracts structured metadata from UK tax documents:
- Monetary thresholds (£90,000 VAT registration)
- Tax years (2024-25)
- Form references (SA100, CT600)
- Key dates (31 January, 5 April)
- Keywords for hybrid search

This metadata enables:
- Precise threshold lookups ("What's the VAT registration threshold?")
- Tax year filtering
- Form identification
- Hybrid search (semantic + keyword)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
import re
import logging

from .base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


@dataclass
class ExtractedMetadata:
    """
    Metadata extracted from a document or chunk.
    """
    # Monetary thresholds
    thresholds: List[Dict[str, Any]] = field(default_factory=list)
    # [{"value": 90000, "context": "VAT registration", "type": "registration"}]
    
    # Tax years mentioned
    tax_years: List[str] = field(default_factory=list)
    # ["2024-25", "2023-24"]
    
    # Forms referenced
    forms: List[Dict[str, str]] = field(default_factory=list)
    # [{"code": "SA100", "name": "Self Assessment tax return"}]
    
    # Key dates
    key_dates: List[Dict[str, Any]] = field(default_factory=list)
    # [{"day": 31, "month": "January", "context": "Self Assessment deadline"}]
    
    # Keywords for hybrid search
    keywords: List[str] = field(default_factory=list)
    
    # Topic classification (rule-based)
    topics: List[str] = field(default_factory=list)
    
    # Business types this applies to
    business_types: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "thresholds": self.thresholds,
            "tax_years": self.tax_years,
            "forms": self.forms,
            "key_dates": self.key_dates,
            "keywords": self.keywords,
            "topics": self.topics,
            "business_types": self.business_types,
        }
    
    def merge(self, other: 'ExtractedMetadata') -> 'ExtractedMetadata':
        """Merge two metadata objects."""
        return ExtractedMetadata(
            thresholds=self.thresholds + other.thresholds,
            tax_years=list(set(self.tax_years + other.tax_years)),
            forms=self.forms + other.forms,
            key_dates=self.key_dates + other.key_dates,
            keywords=list(set(self.keywords + other.keywords)),
            topics=list(set(self.topics + other.topics)),
            business_types=list(set(self.business_types + other.business_types)),
        )


class MetadataExtractor(BaseExtractor):
    """
    Extracts structured metadata from UK tax documents.
    """
    
    # Known UK tax thresholds with context patterns
    THRESHOLD_PATTERNS = [
        # VAT registration
        (re.compile(r'(?:VAT\s+)?registration\s+threshold[:\s]+£?([\d,]+)', re.I), 'vat_registration'),
        (re.compile(r'(?:taxable\s+)?turnover\s+(?:exceeds?|over|more\s+than)\s+£([\d,]+)', re.I), 'vat_registration'),
        
        # Personal allowance
        (re.compile(r'personal\s+allowance[:\s]+£?([\d,]+)', re.I), 'personal_allowance'),
        (re.compile(r'tax[- ]free\s+allowance[:\s]+£?([\d,]+)', re.I), 'personal_allowance'),
        
        # Income tax bands
        (re.compile(r'basic\s+rate\s+(?:band|threshold)[:\s]+£?([\d,]+)', re.I), 'basic_rate_threshold'),
        (re.compile(r'higher\s+rate\s+(?:band|threshold)[:\s]+£?([\d,]+)', re.I), 'higher_rate_threshold'),
        (re.compile(r'additional\s+rate\s+(?:band|threshold)[:\s]+£?([\d,]+)', re.I), 'additional_rate_threshold'),
        
        # Corporation tax
        (re.compile(r'small\s+profits\s+(?:rate|threshold)[:\s]+£?([\d,]+)', re.I), 'small_profits_threshold'),
        (re.compile(r'(?:main\s+rate|upper)\s+(?:profits?\s+)?(?:limit|threshold)[:\s]+£?([\d,]+)', re.I), 'main_rate_threshold'),
        
        # NI thresholds
        (re.compile(r'primary\s+threshold[:\s]+£?([\d,]+)', re.I), 'ni_primary_threshold'),
        (re.compile(r'secondary\s+threshold[:\s]+£?([\d,]+)', re.I), 'ni_secondary_threshold'),
        (re.compile(r'upper\s+earnings\s+limit[:\s]+£?([\d,]+)', re.I), 'ni_upper_earnings'),
        
        # Generic threshold
        (re.compile(r'threshold\s+(?:of|is)\s+£([\d,]+)', re.I), 'threshold'),
        (re.compile(r'£([\d,]+)\s+threshold', re.I), 'threshold'),
    ]
    
    # Known forms
    KNOWN_FORMS = {
        'SA100': 'Self Assessment tax return (main form)',
        'SA102': 'Employment income',
        'SA103': 'Self-employment (short)',
        'SA103F': 'Self-employment (full)',
        'SA104': 'Partnership',
        'SA105': 'UK property income',
        'SA106': 'Foreign income',
        'SA108': 'Capital gains',
        'SA109': 'Residence and remittance',
        'CT600': 'Corporation Tax return',
        'CT600A': 'Losses, deficits and excess amounts',
        'CT600B': 'Controlled foreign companies',
        'VAT1': 'VAT registration application',
        'VAT2': 'VAT partnership details',
        'VAT100': 'VAT return',
        'P60': 'End of year certificate',
        'P45': 'Details of employee leaving work',
        'P11D': 'Expenses and benefits',
        'P11D(b)': 'Return of Class 1A NI contributions',
        'RTI': 'Real Time Information',
        'FPS': 'Full Payment Submission',
        'EPS': 'Employer Payment Summary',
    }
    
    # Form pattern
    FORM_PATTERN = re.compile(
        r'\b(SA\d{2,3}[A-Z]?|CT\d{3}[A-Z]?|VAT\d{1,3}|P\d{2}[A-Z]?|P60|P45|P11D(?:\(b\))?|RTI|FPS|EPS)\b',
        re.I
    )
    
    # Tax year pattern
    TAX_YEAR_PATTERN = re.compile(r'(\d{4})[/-](\d{2,4})')
    EXPLICIT_TAX_YEAR = re.compile(r'(?:tax\s+year|year)\s+(\d{4})[/-](\d{2,4})', re.I)
    
    # Date patterns
    DATE_PATTERNS = [
        re.compile(r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)', re.I),
    ]
    
    # Topic keywords
    TOPIC_KEYWORDS = {
        'vat': ['vat', 'value added tax', 'vat registration', 'vat return', 'vat rate'],
        'income_tax': ['income tax', 'paye', 'personal allowance', 'tax band', 'tax code'],
        'corporation_tax': ['corporation tax', 'company tax', 'ct600', 'marginal relief'],
        'self_assessment': ['self assessment', 'self-assessment', 'sa100', 'tax return'],
        'national_insurance': ['national insurance', 'ni contributions', 'class 1', 'class 2', 'class 4'],
        'capital_gains': ['capital gains', 'cgt', 'asset disposal', 'annual exempt amount'],
        'paye': ['paye', 'employer', 'payroll', 'real time information', 'rti'],
        'penalties': ['penalty', 'penalties', 'late filing', 'late payment', 'surcharge'],
        'tax_credits': ['tax credits', 'working tax credit', 'child tax credit'],
        'inheritance_tax': ['inheritance tax', 'iht', 'estate', 'nil rate band'],
    }
    
    # Business type keywords
    BUSINESS_TYPE_KEYWORDS = {
        'sole_trader': ['sole trader', 'self-employed', 'self employed', 'freelancer'],
        'limited_company': ['limited company', 'ltd', 'company director', 'corporation'],
        'partnership': ['partnership', 'partner', 'llp'],
        'contractor': ['contractor', 'ir35', 'off-payroll'],
        'landlord': ['landlord', 'property income', 'rental income', 'buy to let'],
        'employer': ['employer', 'employee', 'paye', 'payroll'],
    }
    
    def __init__(self):
        super().__init__()
    
    def extract(
        self,
        html_content: Optional[str],
        text_content: str,
        source_url: str,
        **kwargs
    ) -> ExtractionResult[ExtractedMetadata]:
        """Extract metadata from document."""
        result = ExtractionResult[ExtractedMetadata](source_url=source_url)
        
        if not text_content:
            result.items.append(ExtractedMetadata())
            return result
        
        try:
            metadata = ExtractedMetadata()
            
            # Extract thresholds
            metadata.thresholds = self._extract_thresholds(text_content)
            
            # Extract tax years
            metadata.tax_years = self._extract_tax_years(text_content)
            
            # Extract forms
            metadata.forms = self._extract_forms(text_content)
            
            # Extract key dates
            metadata.key_dates = self._extract_key_dates(text_content)
            
            # Extract keywords
            metadata.keywords = self._extract_keywords(text_content)
            
            # Classify topics
            metadata.topics = self._classify_topics(text_content)
            
            # Identify business types
            metadata.business_types = self._identify_business_types(text_content)
            
            result.items.append(metadata)
            logger.info(f"Extracted metadata: {len(metadata.thresholds)} thresholds, {len(metadata.forms)} forms")
            
        except Exception as e:
            result.add_error(f"Metadata extraction failed: {str(e)}")
            result.items.append(ExtractedMetadata())
        
        return result
    
    def _extract_thresholds(self, text: str) -> List[Dict[str, Any]]:
        """Extract monetary thresholds."""
        thresholds = []
        seen_values = set()
        
        for pattern, threshold_type in self.THRESHOLD_PATTERNS:
            for match in pattern.finditer(text):
                try:
                    value = int(match.group(1).replace(',', ''))
                    
                    # Skip duplicates
                    if value in seen_values:
                        continue
                    seen_values.add(value)
                    
                    # Get context
                    context_start = max(0, match.start() - 50)
                    context_end = min(len(text), match.end() + 50)
                    context = text[context_start:context_end]
                    
                    thresholds.append({
                        "value": value,
                        "type": threshold_type,
                        "context": context,
                        "formatted": f"£{value:,}"
                    })
                except ValueError:
                    continue
        
        return thresholds
    
    def _extract_tax_years(self, text: str) -> List[str]:
        """Extract tax years mentioned."""
        years = set()
        
        # Explicit tax year mentions first
        for match in self.EXPLICIT_TAX_YEAR.finditer(text):
            year1 = match.group(1)
            year2 = match.group(2)
            if len(year2) == 4:
                year2 = year2[2:]
            years.add(f"{year1}-{year2}")
        
        # General tax year pattern
        for match in self.TAX_YEAR_PATTERN.finditer(text):
            year1 = match.group(1)
            year2 = match.group(2)
            
            # Validate it looks like a tax year (not a date range)
            y1 = int(year1)
            y2 = int(year2) if len(year2) == 2 else int(year2) % 100
            
            # Tax year spans two calendar years (e.g., 2024-25)
            if y2 == (y1 + 1) % 100:
                if len(year2) == 4:
                    year2 = year2[2:]
                years.add(f"{year1}-{year2}")
        
        return sorted(list(years), reverse=True)
    
    def _extract_forms(self, text: str) -> List[Dict[str, str]]:
        """Extract form references."""
        forms = []
        seen = set()
        
        for match in self.FORM_PATTERN.finditer(text):
            form_code = match.group(1).upper()
            
            if form_code in seen:
                continue
            seen.add(form_code)
            
            forms.append({
                "code": form_code,
                "name": self.KNOWN_FORMS.get(form_code, "HMRC form"),
            })
        
        return forms
    
    def _extract_key_dates(self, text: str) -> List[Dict[str, Any]]:
        """Extract key dates (deadlines, etc.)."""
        dates = []
        seen = set()
        
        for pattern in self.DATE_PATTERNS:
            for match in pattern.finditer(text):
                day = int(match.group(1))
                month = match.group(2).capitalize()
                
                key = (day, month)
                if key in seen:
                    continue
                seen.add(key)
                
                # Get context to understand what the date is for
                context_start = max(0, match.start() - 100)
                context_end = min(len(text), match.end() + 50)
                context = text[context_start:context_end]
                
                # Determine date type from context
                date_type = self._classify_date_type(context)
                
                dates.append({
                    "day": day,
                    "month": month,
                    "context": context,
                    "type": date_type,
                })
        
        return dates
    
    def _classify_date_type(self, context: str) -> str:
        """Classify what type of date this is."""
        context_lower = context.lower()
        
        if any(w in context_lower for w in ['deadline', 'due', 'submit', 'file']):
            return 'deadline'
        elif any(w in context_lower for w in ['pay', 'payment']):
            return 'payment'
        elif any(w in context_lower for w in ['start', 'begin', 'commence']):
            return 'start_date'
        elif any(w in context_lower for w in ['end', 'finish', 'close']):
            return 'end_date'
        
        return 'date'
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords for hybrid search."""
        keywords = set()
        text_lower = text.lower()
        
        # Add topic keywords found
        for topic, topic_keywords in self.TOPIC_KEYWORDS.items():
            for keyword in topic_keywords:
                if keyword in text_lower:
                    keywords.add(keyword)
        
        # Add business type keywords
        for btype, btype_keywords in self.BUSINESS_TYPE_KEYWORDS.items():
            for keyword in btype_keywords:
                if keyword in text_lower:
                    keywords.add(keyword)
        
        # Add form codes
        for match in self.FORM_PATTERN.finditer(text):
            keywords.add(match.group(1).lower())
        
        return sorted(list(keywords))
    
    def _classify_topics(self, text: str) -> List[str]:
        """Classify document topics based on keywords."""
        topics = []
        text_lower = text.lower()
        
        for topic, keywords in self.TOPIC_KEYWORDS.items():
            # Count keyword matches
            matches = sum(1 for kw in keywords if kw in text_lower)
            if matches >= 2:  # Require at least 2 keyword matches
                topics.append(topic)
        
        return topics
    
    def _identify_business_types(self, text: str) -> List[str]:
        """Identify what business types this content applies to."""
        types = []
        text_lower = text.lower()
        
        for btype, keywords in self.BUSINESS_TYPE_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                types.append(btype)
        
        return types
    
    def extract_for_chunk(self, chunk_text: str) -> ExtractedMetadata:
        """
        Simplified extraction for individual chunks.
        
        Returns metadata directly rather than ExtractionResult.
        """
        result = self.extract(None, chunk_text, "")
        return result.items[0] if result.items else ExtractedMetadata()
