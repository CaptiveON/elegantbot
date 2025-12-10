"""
Base Extractor

Abstract base class for all structured content extractors.
Provides common interface and utilities.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, TypeVar, Generic
from datetime import datetime
import re
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class ExtractionResult(Generic[T]):
    """
    Generic result container for extraction operations.
    
    Contains the extracted items plus metadata about the extraction.
    """
    items: List[T] = field(default_factory=list)
    extraction_timestamp: datetime = field(default_factory=datetime.now)
    source_url: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @property
    def count(self) -> int:
        return len(self.items)
    
    @property
    def has_items(self) -> bool:
        return len(self.items) > 0
    
    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    def add_error(self, error: str) -> None:
        self.errors.append(error)
        logger.error(f"Extraction error: {error}")
    
    def add_warning(self, warning: str) -> None:
        self.warnings.append(warning)
        logger.warning(f"Extraction warning: {warning}")


class BaseExtractor(ABC):
    """
    Abstract base class for structured content extractors.
    
    All extractors should inherit from this class and implement
    the extract() method.
    
    Common utilities provided:
    - Text cleaning
    - Pattern matching helpers
    - Monetary amount parsing
    - Date parsing
    """
    
    # Common patterns used across extractors
    GBP_PATTERN = re.compile(r'£(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)')
    PERCENTAGE_PATTERN = re.compile(r'(\d+(?:\.\d+)?)\s*%')
    DATE_PATTERN = re.compile(
        r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s*(\d{4})?',
        re.IGNORECASE
    )
    TAX_YEAR_PATTERN = re.compile(r'(\d{4})[/-](\d{2,4})')
    
    # HMRC form references
    FORM_PATTERN = re.compile(r'\b(SA\d{2,3}[A-Z]?|CT\d{3}|VAT\d{1,3}|P\d{2}[A-Z]?|P60|P45|P11D)\b', re.IGNORECASE)
    
    def __init__(self):
        """Initialize the base extractor."""
        pass
    
    @abstractmethod
    def extract(
        self, 
        html_content: Optional[str],
        text_content: str,
        source_url: str,
        **kwargs
    ) -> ExtractionResult:
        """
        Extract structured content from document.
        
        Args:
            html_content: Raw HTML (may be None for text-only extraction)
            text_content: Cleaned text content
            source_url: URL of the source document
            **kwargs: Additional extractor-specific parameters
        
        Returns:
            ExtractionResult containing extracted items
        """
        pass
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def parse_gbp_amount(self, text: str) -> Optional[float]:
        """
        Parse a GBP monetary amount from text.
        
        Handles formats like: £1,234.56, £90,000, £12570
        Returns the numeric value or None if not found.
        """
        match = self.GBP_PATTERN.search(text)
        if match:
            amount_str = match.group(1).replace(',', '')
            try:
                return float(amount_str)
            except ValueError:
                return None
        return None
    
    def parse_all_gbp_amounts(self, text: str) -> List[float]:
        """Extract all GBP amounts from text."""
        amounts = []
        for match in self.GBP_PATTERN.finditer(text):
            amount_str = match.group(1).replace(',', '')
            try:
                amounts.append(float(amount_str))
            except ValueError:
                continue
        return amounts
    
    def parse_percentage(self, text: str) -> Optional[float]:
        """Parse a percentage from text."""
        match = self.PERCENTAGE_PATTERN.search(text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None
    
    def parse_all_percentages(self, text: str) -> List[float]:
        """Extract all percentages from text."""
        percentages = []
        for match in self.PERCENTAGE_PATTERN.finditer(text):
            try:
                percentages.append(float(match.group(1)))
            except ValueError:
                continue
        return percentages
    
    def extract_tax_year(self, text: str) -> Optional[str]:
        """
        Extract tax year from text.
        
        Handles formats like: 2024-25, 2024/25, 2024-2025
        Returns normalized format: "2024-25"
        """
        match = self.TAX_YEAR_PATTERN.search(text)
        if match:
            year1 = match.group(1)
            year2 = match.group(2)
            
            # Normalize to YY format
            if len(year2) == 4:
                year2 = year2[2:]
            
            return f"{year1}-{year2}"
        return None
    
    def extract_forms(self, text: str) -> List[str]:
        """Extract HMRC form references from text."""
        forms = []
        for match in self.FORM_PATTERN.finditer(text):
            forms.append(match.group(1).upper())
        return list(set(forms))
    
    def parse_date(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Parse a date from text.
        
        Returns dict with day, month, year (year may be None).
        """
        match = self.DATE_PATTERN.search(text)
        if match:
            return {
                "day": int(match.group(1)),
                "month": match.group(2).capitalize(),
                "year": int(match.group(3)) if match.group(3) else None
            }
        return None
    
    def find_pattern_with_context(
        self, 
        text: str, 
        pattern: re.Pattern, 
        context_chars: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Find all matches of a pattern with surrounding context.
        
        Returns list of dicts with match text and context.
        """
        results = []
        for match in pattern.finditer(text):
            start = max(0, match.start() - context_chars)
            end = min(len(text), match.end() + context_chars)
            
            results.append({
                "match": match.group(),
                "groups": match.groups(),
                "start": match.start(),
                "end": match.end(),
                "context_before": text[start:match.start()],
                "context_after": text[match.end():end],
                "full_context": text[start:end]
            })
        
        return results
    
    def infer_column_type(self, values: List[str]) -> str:
        """
        Infer the data type of a column from sample values.
        
        Returns one of: currency_gbp, percentage, number, date, text
        """
        if not values:
            return "text"
        
        # Sample up to 10 values
        sample = values[:10]
        
        # Count type matches
        currency_count = sum(1 for v in sample if self.GBP_PATTERN.search(str(v)))
        percentage_count = sum(1 for v in sample if self.PERCENTAGE_PATTERN.search(str(v)))
        number_count = sum(1 for v in sample if re.match(r'^[\d,]+(?:\.\d+)?$', str(v).strip()))
        
        total = len(sample)
        
        if currency_count > total * 0.5:
            return "currency_gbp"
        elif percentage_count > total * 0.5:
            return "percentage"
        elif number_count > total * 0.5:
            return "number"
        else:
            return "text"
