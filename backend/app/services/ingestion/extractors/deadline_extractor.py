"""
Deadline Extractor

Extracts deadline information from UK tax documents.
Converts to StructuredDeadline format.

Key Features:
- Identifies filing deadlines, payment deadlines, registration deadlines
- Extracts date rules (fixed dates, relative dates)
- Links to associated penalties
- Handles recurring vs one-time deadlines
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import re
import logging

from .base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


@dataclass
class ExtractedDeadline:
    """Represents a deadline extracted from document."""
    
    deadline_name: str
    deadline_type: str  # filing, payment, registration, etc.
    tax_category: str   # self_assessment, vat, corporation_tax, etc.
    
    # Date information
    frequency: str      # annual, quarterly, monthly, one_time, event_based
    deadline_rule: Dict[str, Any]  # {type: "fixed", month: 1, day: 31}
    
    # Context
    description: str
    applies_to: List[str] = field(default_factory=list)  # Who this applies to
    
    # Consequences
    penalty_description: Optional[str] = None
    
    # Temporal
    tax_year: Optional[str] = None
    
    # Suggested reminder
    suggested_reminder_days: int = 14
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "deadline_name": self.deadline_name,
            "deadline_type": self.deadline_type,
            "tax_category": self.tax_category,
            "frequency": self.frequency,
            "deadline_rule": self.deadline_rule,
            "description": self.description,
            "applies_to": self.applies_to,
            "penalty_description": self.penalty_description,
            "tax_year": self.tax_year,
            "suggested_reminder_days": self.suggested_reminder_days,
        }


class DeadlineExtractor(BaseExtractor):
    """
    Extracts deadline information from tax documents.
    """
    
    # Known UK tax deadlines
    KNOWN_DEADLINES = {
        "31 january": {
            "name": "Self Assessment Tax Return and Payment",
            "type": "filing",
            "category": "self_assessment",
            "frequency": "annual",
            "applies_to": ["self_employed", "landlord", "high_earner"],
        },
        "5 april": {
            "name": "Tax Year End",
            "type": "notification",
            "category": "general",
            "frequency": "annual",
        },
        "6 april": {
            "name": "New Tax Year Start",
            "type": "notification",
            "category": "general",
            "frequency": "annual",
        },
        "31 july": {
            "name": "Second Payment on Account",
            "type": "payment",
            "category": "self_assessment",
            "frequency": "annual",
        },
        "31 october": {
            "name": "Paper Self Assessment Deadline",
            "type": "filing",
            "category": "self_assessment",
            "frequency": "annual",
        },
        "19 april": {
            "name": "PAYE Year End Returns",
            "type": "filing",
            "category": "paye",
            "frequency": "annual",
        },
    }
    
    # Deadline patterns
    DEADLINE_PATTERNS = [
        re.compile(
            r'(?:deadline|due\s+(?:date|by)|must\s+be\s+(?:filed|submitted|paid)\s+by)[:\s]+(\d{1,2}\s+[A-Za-z]+)',
            re.I
        ),
        re.compile(
            r'by\s+(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December))',
            re.I
        ),
        re.compile(
            r'within\s+(\d+)\s+(days?|months?|weeks?)\s+(?:of|after|from)',
            re.I
        ),
    ]
    
    MONTH_MAP = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12
    }
    
    def __init__(self):
        super().__init__()
    
    def extract(
        self,
        html_content: Optional[str],
        text_content: str,
        source_url: str,
        **kwargs
    ) -> ExtractionResult[ExtractedDeadline]:
        """Extract deadlines from document."""
        result = ExtractionResult[ExtractedDeadline](source_url=source_url)
        
        if not text_content:
            return result
        
        tax_year = kwargs.get('tax_year') or self.extract_tax_year(text_content)
        text_lower = text_content.lower()
        
        try:
            # Check for known deadlines
            for date_key, info in self.KNOWN_DEADLINES.items():
                if date_key in text_lower:
                    deadline = self._create_known_deadline(date_key, info, text_content, tax_year)
                    result.items.append(deadline)
            
            # Extract relative deadlines
            for pattern in self.DEADLINE_PATTERNS[2:]:  # within X days patterns
                for match in pattern.finditer(text_content):
                    deadline = self._create_relative_deadline(match, text_content, tax_year)
                    if deadline:
                        result.items.append(deadline)
            
            logger.info(f"Extracted {len(result.items)} deadlines from {source_url}")
            
        except Exception as e:
            result.add_error(f"Deadline extraction failed: {str(e)}")
        
        return result
    
    def _create_known_deadline(
        self, 
        date_key: str, 
        info: Dict,
        text: str,
        tax_year: Optional[str]
    ) -> ExtractedDeadline:
        """Create deadline from known deadline info."""
        parts = date_key.split()
        day = int(parts[0])
        month = self.MONTH_MAP[parts[1]]
        
        # Find penalty information nearby
        penalty_desc = self._find_penalty_context(text, date_key)
        
        return ExtractedDeadline(
            deadline_name=info["name"],
            deadline_type=info["type"],
            tax_category=info["category"],
            frequency=info.get("frequency", "annual"),
            deadline_rule={
                "type": "fixed",
                "day": day,
                "month": month,
            },
            description=f"{info['name']} deadline is {day} {parts[1].capitalize()}",
            applies_to=info.get("applies_to", []),
            penalty_description=penalty_desc,
            tax_year=tax_year,
            suggested_reminder_days=30 if info["type"] == "filing" else 14,
        )
    
    def _create_relative_deadline(
        self, 
        match: re.Match,
        text: str,
        tax_year: Optional[str]
    ) -> Optional[ExtractedDeadline]:
        """Create deadline from relative pattern (within X days)."""
        try:
            number = int(match.group(1))
            unit = match.group(2).lower().rstrip('s')  # days -> day
            
            # Get context to understand what this deadline is for
            context_start = max(0, match.start() - 150)
            context = text[context_start:match.end() + 50]
            
            # Try to identify the deadline type
            deadline_type = "notification"
            if 'file' in context.lower() or 'submit' in context.lower():
                deadline_type = "filing"
            elif 'pay' in context.lower():
                deadline_type = "payment"
            elif 'register' in context.lower():
                deadline_type = "registration"
            elif 'appeal' in context.lower():
                deadline_type = "appeal"
            
            return ExtractedDeadline(
                deadline_name=f"Within {number} {unit}s deadline",
                deadline_type=deadline_type,
                tax_category="general",
                frequency="event_based",
                deadline_rule={
                    "type": "relative",
                    "value": number,
                    "unit": unit,
                },
                description=f"Must be completed within {number} {unit}(s)",
                tax_year=tax_year,
                suggested_reminder_days=min(number // 2, 14),
            )
        except (ValueError, IndexError):
            return None
    
    def _find_penalty_context(self, text: str, date_key: str) -> Optional[str]:
        """Find penalty information near a deadline."""
        idx = text.lower().find(date_key)
        if idx == -1:
            return None
        
        # Search nearby text for penalty info
        context = text[max(0, idx - 200):idx + 300]
        
        penalty_patterns = [
            r'penalty\s+of\s+£[\d,]+',
            r'£[\d,]+\s+penalty',
            r'late\s+filing\s+penalty',
            r'interest\s+will\s+be\s+charged',
        ]
        
        for pattern in penalty_patterns:
            match = re.search(pattern, context, re.I)
            if match:
                return match.group(0)
        
        return None
    
    def has_deadlines(self, text: str) -> bool:
        """Quick check if text contains deadline information."""
        indicators = [
            r'\b(?:deadline|due\s+date)\b',
            r'must\s+be\s+(?:filed|submitted|paid)\s+by',
            r'within\s+\d+\s+(?:days?|months?)',
            r'\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)',
        ]
        return any(re.search(p, text, re.I) for p in indicators)
