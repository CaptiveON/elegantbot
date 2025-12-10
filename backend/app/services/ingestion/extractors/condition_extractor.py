"""
Condition Extractor

Extracts legal condition lists from UK tax documents.
Converts to StructuredConditionList format.

Key Features:
- Identifies (a), (b), (c) style condition lists
- Determines logical operator (AND, OR)
- Extracts outcome if conditions are met
- Preserves legal language precisely
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import re
import logging

from .base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


@dataclass
class ExtractedConditionList:
    """Represents a condition list extracted from document."""
    
    condition_name: str
    condition_type: str  # requirement, eligibility, exemption, etc.
    
    # Logic
    logical_operator: str  # AND, OR, AND_NOT, SEQUENTIAL
    conditions: List[Dict[str, Any]]  # [{"id": "a", "text": "...", "variables": [...]}]
    
    # Outcome
    outcome_if_met: str
    outcome_if_not_met: Optional[str] = None
    
    # Context
    context_text: str = ""
    applies_to: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition_name": self.condition_name,
            "condition_type": self.condition_type,
            "logical_operator": self.logical_operator,
            "conditions": self.conditions,
            "outcome_if_met": self.outcome_if_met,
            "outcome_if_not_met": self.outcome_if_not_met,
            "context_text": self.context_text,
            "applies_to": self.applies_to,
        }


class ConditionExtractor(BaseExtractor):
    """
    Extracts condition lists from legal/tax documents.
    
    Handles patterns like:
    - "You must register if: (a) ..., (b) ..., or (c) ..."
    - "You're exempt if all of the following apply: ..."
    - "1. ..., 2. ..., 3. ..."
    """
    
    # Condition list start patterns
    CONDITION_START_PATTERNS = [
        # Must/should patterns
        (re.compile(
            r'you\s+(?:must|should|need\s+to)\s+([a-z]+(?:\s+[a-z]+){0,5})\s+if[:\s]+',
            re.I | re.DOTALL
        ), 'requirement', 'must'),
        
        # Can/cannot patterns  
        (re.compile(
            r'you\s+(?:can(?:not)?|cannot)\s+([a-z]+(?:\s+[a-z]+){0,5})\s+(?:if|unless)[:\s]+',
            re.I | re.DOTALL
        ), 'eligibility', 'can'),
        
        # Eligible if patterns
        (re.compile(
            r'(?:you\'?re?|you\s+are)\s+(?:only\s+)?(?:eligible|entitled)\s+(?:for\s+)?([a-z]+(?:\s+[a-z]+){0,3})?\s*if[:\s]+',
            re.I | re.DOTALL
        ), 'eligibility', 'eligible'),
        
        # Exempt if patterns
        (re.compile(
            r'(?:you\'?re?|you\s+are)\s+exempt\s+(?:from\s+)?([a-z]+(?:\s+[a-z]+){0,3})?\s*if[:\s]+',
            re.I | re.DOTALL
        ), 'exemption', 'exempt'),
        
        # "The following" patterns
        (re.compile(
            r'(?:if\s+)?(?:any|all)\s+of\s+the\s+following\s+(?:conditions?\s+)?apply[:\s]+',
            re.I | re.DOTALL
        ), 'requirement', 'following'),
    ]
    
    # Letter/number list patterns
    LETTER_ITEM_PATTERN = re.compile(r'^\s*\(([a-z])\)\s*(.+?)(?=^\s*\([a-z]\)|\Z)', re.MULTILINE | re.DOTALL)
    NUMBER_ITEM_PATTERN = re.compile(r'^\s*(\d+)\.\s*(.+?)(?=^\s*\d+\.|\Z)', re.MULTILINE | re.DOTALL)
    BULLET_ITEM_PATTERN = re.compile(r'^\s*[•\-\*]\s*(.+?)(?=^\s*[•\-\*]|\Z)', re.MULTILINE | re.DOTALL)
    
    # Logical operator patterns
    AND_INDICATORS = ['all of', 'each of', 'and', 'both']
    OR_INDICATORS = ['any of', 'one of', 'or', 'either']
    
    def __init__(self):
        super().__init__()
    
    def extract(
        self,
        html_content: Optional[str],
        text_content: str,
        source_url: str,
        **kwargs
    ) -> ExtractionResult[ExtractedConditionList]:
        """Extract condition lists from document."""
        result = ExtractionResult[ExtractedConditionList](source_url=source_url)
        
        if not text_content:
            return result
        
        try:
            for pattern, cond_type, name_hint in self.CONDITION_START_PATTERNS:
                for match in pattern.finditer(text_content):
                    condition_list = self._extract_condition_list(
                        match, text_content, cond_type, name_hint
                    )
                    if condition_list and len(condition_list.conditions) >= 2:
                        result.items.append(condition_list)
            
            logger.info(f"Extracted {len(result.items)} condition lists from {source_url}")
            
        except Exception as e:
            result.add_error(f"Condition extraction failed: {str(e)}")
        
        return result
    
    def _extract_condition_list(
        self,
        start_match: re.Match,
        full_text: str,
        cond_type: str,
        name_hint: str
    ) -> Optional[ExtractedConditionList]:
        """Extract a condition list starting from matched pattern."""
        
        # Get text after the pattern start
        start_pos = start_match.end()
        # Look for end of condition list (next paragraph break or section)
        remaining = full_text[start_pos:start_pos + 2000]
        
        # Find end of list
        end_patterns = [
            r'\n\n(?=[A-Z])',  # Double newline followed by capital
            r'\n##',  # New heading
            r'\n\d+\.',  # New numbered section (not part of list)
        ]
        
        end_pos = len(remaining)
        for pattern in end_patterns:
            match = re.search(pattern, remaining)
            if match and match.start() > 50:  # Minimum content
                end_pos = min(end_pos, match.start())
        
        list_text = remaining[:end_pos]
        
        # Extract conditions
        conditions = self._extract_conditions(list_text)
        
        if not conditions:
            return None
        
        # Determine logical operator
        intro_text = full_text[max(0, start_match.start() - 50):start_match.end()].lower()
        logical_op = self._determine_logical_operator(intro_text)
        
        # Generate name
        subject = start_match.group(1) if start_match.lastindex and start_match.group(1) else name_hint
        condition_name = f"{cond_type.replace('_', ' ').title()} conditions for {subject}"
        
        # Determine outcome
        outcome = self._determine_outcome(intro_text, cond_type)
        
        return ExtractedConditionList(
            condition_name=condition_name,
            condition_type=cond_type,
            logical_operator=logical_op,
            conditions=conditions,
            outcome_if_met=outcome,
            context_text=full_text[start_match.start():start_match.end() + len(list_text)],
        )
    
    def _extract_conditions(self, text: str) -> List[Dict[str, Any]]:
        """Extract individual conditions from list text."""
        conditions = []
        
        # Try letter pattern first (a), (b), (c)
        letter_matches = list(self.LETTER_ITEM_PATTERN.finditer(text))
        if letter_matches:
            for match in letter_matches:
                conditions.append({
                    "id": match.group(1),
                    "text": self.clean_text(match.group(2)),
                    "variables": self._extract_variables(match.group(2))
                })
            return conditions
        
        # Try number pattern 1., 2., 3.
        number_matches = list(self.NUMBER_ITEM_PATTERN.finditer(text))
        if number_matches:
            for match in number_matches:
                conditions.append({
                    "id": match.group(1),
                    "text": self.clean_text(match.group(2)),
                    "variables": self._extract_variables(match.group(2))
                })
            return conditions
        
        # Try bullet pattern
        bullet_matches = list(self.BULLET_ITEM_PATTERN.finditer(text))
        if bullet_matches:
            for i, match in enumerate(bullet_matches):
                conditions.append({
                    "id": chr(ord('a') + i),  # Convert to letter
                    "text": self.clean_text(match.group(1)),
                    "variables": self._extract_variables(match.group(1))
                })
            return conditions
        
        return conditions
    
    def _extract_variables(self, text: str) -> List[Dict[str, str]]:
        """Extract variables (thresholds, amounts) from condition text."""
        variables = []
        
        # Extract GBP amounts
        for match in self.GBP_PATTERN.finditer(text):
            variables.append({
                "type": "currency_gbp",
                "value": match.group(1),
                "context": text[max(0, match.start()-20):match.end()+20]
            })
        
        # Extract percentages
        for match in self.PERCENTAGE_PATTERN.finditer(text):
            variables.append({
                "type": "percentage",
                "value": match.group(1),
            })
        
        return variables
    
    def _determine_logical_operator(self, intro_text: str) -> str:
        """Determine if conditions are AND or OR."""
        intro_lower = intro_text.lower()
        
        for indicator in self.OR_INDICATORS:
            if indicator in intro_lower:
                return "OR"
        
        for indicator in self.AND_INDICATORS:
            if indicator in intro_lower:
                return "AND"
        
        # Default to OR for most tax requirements (any condition triggers)
        return "OR"
    
    def _determine_outcome(self, intro_text: str, cond_type: str) -> str:
        """Determine the outcome if conditions are met."""
        outcomes = {
            'requirement': 'You must comply with this requirement',
            'eligibility': 'You are eligible',
            'exemption': 'You are exempt',
        }
        
        # Try to extract specific outcome from text
        specific_patterns = [
            r'you\s+(?:must|should)\s+([a-z]+(?:\s+[a-z]+){0,3})',
            r'you\s+(?:can)\s+([a-z]+(?:\s+[a-z]+){0,3})',
        ]
        
        for pattern in specific_patterns:
            match = re.search(pattern, intro_text, re.I)
            if match:
                return f"You must {match.group(1)}"
        
        return outcomes.get(cond_type, 'Conditions apply')
    
    def has_condition_lists(self, text: str) -> bool:
        """Quick check if text contains condition lists."""
        # Check for (a), (b) pattern
        if re.search(r'\([a-c]\)', text):
            return True
        
        # Check for condition indicators
        indicators = [
            r'if\s+(?:any|all)\s+of\s+the\s+following',
            r'you\s+must\s+[a-z]+\s+if:',
            r'you\s+can\s+[a-z]+\s+if:',
        ]
        return any(re.search(p, text, re.I) for p in indicators)
