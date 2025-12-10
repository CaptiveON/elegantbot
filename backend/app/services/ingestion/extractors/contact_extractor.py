"""
Contact Extractor

Extracts HMRC contact information from UK tax documents.
Converts to StructuredContact format.

Key Features:
- Extracts phone numbers (UK and international)
- Extracts email addresses
- Extracts opening hours
- Identifies which service/department
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import re
import logging

from .base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


@dataclass
class ExtractedContact:
    """Represents contact information extracted from document."""
    
    service_name: str
    department: Optional[str] = None
    
    # Contact methods
    contact_methods: List[Dict[str, Any]] = field(default_factory=list)
    # [{"type": "phone", "value": "0300 200 3310", "hours": "8am-6pm Mon-Fri"}]
    
    # Online services
    online_services: List[Dict[str, str]] = field(default_factory=list)
    # [{"name": "HMRC Online", "url": "https://..."}]
    
    # Postal address
    postal_address: Optional[str] = None
    
    # Context
    description: str = ""
    service_category: Optional[str] = None  # vat, self_assessment, paye, etc.
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_name": self.service_name,
            "department": self.department,
            "contact_methods": self.contact_methods,
            "online_services": self.online_services,
            "postal_address": self.postal_address,
            "description": self.description,
            "service_category": self.service_category,
        }


class ContactExtractor(BaseExtractor):
    """
    Extracts HMRC contact information from documents.
    """
    
    # UK phone patterns
    PHONE_PATTERNS = [
        re.compile(r'(0\d{2,4}[\s.-]?\d{3}[\s.-]?\d{4})', re.I),  # 0300 200 3310
        re.compile(r'(\+44[\s.-]?\d{2,4}[\s.-]?\d{3}[\s.-]?\d{4})', re.I),  # +44 format
    ]
    
    # Email pattern
    EMAIL_PATTERN = re.compile(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})')
    
    # Hours pattern
    HOURS_PATTERN = re.compile(
        r'(\d{1,2}(?::\d{2})?(?:am|pm)?[\s-]+(?:to|-)[\s-]+\d{1,2}(?::\d{2})?(?:am|pm)?)',
        re.I
    )
    
    # Days pattern
    DAYS_PATTERN = re.compile(
        r'((?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)[\s-]+(?:to|-)[\s-]+(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday))',
        re.I
    )
    
    # Known HMRC helplines
    KNOWN_HELPLINES = {
        '0300 200 3310': {'name': 'Self Assessment Helpline', 'category': 'self_assessment'},
        '0300 200 3700': {'name': 'VAT Helpline', 'category': 'vat'},
        '0300 200 3200': {'name': 'Corporation Tax Helpline', 'category': 'corporation_tax'},
        '0300 200 3500': {'name': 'National Insurance Helpline', 'category': 'national_insurance'},
        '0300 200 3300': {'name': 'Employer Helpline', 'category': 'paye'},
        '0300 200 3600': {'name': 'Tax Credits Helpline', 'category': 'tax_credits'},
    }
    
    # Contact section indicators
    CONTACT_INDICATORS = [
        r'\bcontact\s+(?:us|hmrc)',
        r'\bhelpline\b',
        r'\btelephone\b',
        r'\bcall\s+(?:us|hmrc)',
        r'\bget\s+help\b',
        r'\bphone\s+number\b',
    ]
    
    def __init__(self):
        super().__init__()
    
    def extract(
        self,
        html_content: Optional[str],
        text_content: str,
        source_url: str,
        **kwargs
    ) -> ExtractionResult[ExtractedContact]:
        """Extract contact information from document."""
        result = ExtractionResult[ExtractedContact](source_url=source_url)
        
        if not text_content:
            return result
        
        try:
            # Find contact sections
            contact_sections = self._find_contact_sections(text_content)
            
            if contact_sections:
                for section in contact_sections:
                    contact = self._extract_contact_from_section(section)
                    if contact:
                        result.items.append(contact)
            else:
                # Try to extract from full text
                contact = self._extract_contact_from_section(text_content)
                if contact:
                    result.items.append(contact)
            
            logger.info(f"Extracted {len(result.items)} contacts from {source_url}")
            
        except Exception as e:
            result.add_error(f"Contact extraction failed: {str(e)}")
        
        return result
    
    def _find_contact_sections(self, text: str) -> List[str]:
        """Find sections of text that contain contact information."""
        sections = []
        
        for indicator in self.CONTACT_INDICATORS:
            for match in re.finditer(indicator, text, re.I):
                # Extract surrounding context (up to 500 chars after)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 500)
                sections.append(text[start:end])
        
        return sections
    
    def _extract_contact_from_section(self, text: str) -> Optional[ExtractedContact]:
        """Extract contact info from a section of text."""
        contact_methods = []
        
        # Extract phone numbers
        for pattern in self.PHONE_PATTERNS:
            for match in pattern.finditer(text):
                phone = self._normalize_phone(match.group(1))
                
                # Check if known helpline
                known_info = self.KNOWN_HELPLINES.get(phone, {})
                
                # Find hours near this phone number
                hours = self._find_hours_near(text, match.start())
                
                contact_methods.append({
                    "type": "phone",
                    "value": phone,
                    "hours": hours,
                    "name": known_info.get('name'),
                })
        
        # Extract emails
        for match in self.EMAIL_PATTERN.finditer(text):
            email = match.group(1)
            if 'gov.uk' in email or 'hmrc' in email.lower():
                contact_methods.append({
                    "type": "email",
                    "value": email,
                })
        
        if not contact_methods:
            return None
        
        # Determine service name
        service_name = "HMRC Contact"
        service_category = None
        
        for phone_info in contact_methods:
            if phone_info.get("type") == "phone":
                phone = phone_info.get("value", "")
                known = self.KNOWN_HELPLINES.get(phone, {})
                if known.get("name"):
                    service_name = known["name"]
                    service_category = known.get("category")
                    break
        
        return ExtractedContact(
            service_name=service_name,
            contact_methods=contact_methods,
            service_category=service_category,
            description=text[:200] + "..." if len(text) > 200 else text,
        )
    
    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number format."""
        # Remove spaces, dots, dashes
        clean = re.sub(r'[\s.\-]', '', phone)
        
        # Format as 0300 200 3310
        if clean.startswith('0') and len(clean) == 11:
            return f"{clean[:4]} {clean[4:7]} {clean[7:]}"
        
        return phone
    
    def _find_hours_near(self, text: str, position: int) -> Optional[str]:
        """Find opening hours near a position in text."""
        # Search in surrounding text
        start = max(0, position - 100)
        end = min(len(text), position + 200)
        context = text[start:end]
        
        # Look for hours pattern
        hours_match = self.HOURS_PATTERN.search(context)
        days_match = self.DAYS_PATTERN.search(context)
        
        parts = []
        if hours_match:
            parts.append(hours_match.group(1))
        if days_match:
            parts.append(days_match.group(1))
        
        return ', '.join(parts) if parts else None
    
    def has_contacts(self, text: str) -> bool:
        """Quick check if text contains contact information."""
        # Check for phone numbers
        for pattern in self.PHONE_PATTERNS:
            if pattern.search(text):
                return True
        
        # Check for contact indicators
        return any(re.search(p, text, re.I) for p in self.CONTACT_INDICATORS)
