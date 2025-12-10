"""
GOV.UK Content API Client

Fetches official UK government content from the GOV.UK Content API.
This covers both general guidance (gov.uk/vat-registration) and 
HMRC technical manuals (gov.uk/hmrc-internal-manuals/vat-guide).

API Documentation: https://content-api.publishing.service.gov.uk/

Key Concepts:
- Every GOV.UK page has a corresponding API endpoint
- API returns structured JSON with metadata + HTML content
- HMRC manuals are nested (manual → sections → subsections)
"""

import requests
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin, urlparse
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class GovUKDocument:
    """
    Represents a document fetched from GOV.UK API.
    
    Think of this as a "standardized envelope" — regardless of whether
    the source is a simple guidance page or a complex HMRC manual,
    we convert it to this consistent format.
    """
    url: str
    base_path: str  # e.g., "/vat-registration"
    title: str
    description: Optional[str]
    body_html: str  # The main content (still HTML at this stage)
    
    # Metadata from API
    document_type: str  # e.g., "guide", "manual_section", "detailed_guide"
    schema_name: str  # GOV.UK's internal schema classification
    
    # Temporal data (critical for audit)
    first_published: Optional[datetime]
    last_updated: Optional[datetime]
    
    # Structure/hierarchy
    breadcrumbs: List[Dict[str, str]]  # [{title: "VAT", path: "/vat"}, ...]
    parent_title: Optional[str]
    parent_path: Optional[str]
    
    # For HMRC manuals - child sections to crawl
    child_sections: List[Dict[str, str]]  # [{title: "...", path: "..."}, ...]
    
    # Raw API response (for debugging/audit)
    raw_response: Dict[str, Any]


class GovUKContentAPIError(Exception):
    """Raised when GOV.UK API returns an error"""
    pass


class GovUKClient:
    """
    Client for fetching content from GOV.UK Content API.
    
    Analogy: This is like a librarian who knows exactly how to find
    and retrieve any book (document) from the government library (GOV.UK).
    You give them a book ID (URL path), they return the full book with
    all its metadata.
    
    Usage:
        client = GovUKClient()
        doc = client.fetch_document("/vat-registration")
        print(doc.title, doc.body_html)
    """
    
    BASE_URL = "https://www.gov.uk"
    API_BASE = "https://www.gov.uk/api/content"
    
    # Rate limiting: GOV.UK asks for reasonable usage
    # We'll be polite and wait between requests
    REQUEST_DELAY_SECONDS = 0.5
    
    def __init__(self, timeout: int = 30):
        """
        Initialize the GOV.UK client.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "UKSMETaxComplianceBot/1.0 (Educational/Research)",
            "Accept": "application/json"
        })
        self._last_request_time = 0
    
    def _rate_limit(self):
        """Ensure we don't overwhelm GOV.UK servers"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.REQUEST_DELAY_SECONDS:
            time.sleep(self.REQUEST_DELAY_SECONDS - elapsed)
        self._last_request_time = time.time()
    
    def _normalize_path(self, path_or_url: str) -> str:
        """
        Convert full URL or path to just the path portion.
        
        Examples:
            "https://www.gov.uk/vat-registration" → "/vat-registration"
            "/vat-registration" → "/vat-registration"
            "vat-registration" → "/vat-registration"
        """
        if path_or_url.startswith("http"):
            parsed = urlparse(path_or_url)
            path = parsed.path
        else:
            path = path_or_url
        
        if not path.startswith("/"):
            path = "/" + path
        
        return path
    
    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO datetime string from API"""
        if not date_str:
            return None
        try:
            # GOV.UK uses ISO format: "2024-03-15T09:30:00+00:00"
            # Remove timezone for simplicity (all GOV.UK times are UK)
            clean = date_str.replace("+00:00", "").replace("Z", "")
            if "T" in clean:
                return datetime.fromisoformat(clean)
            return datetime.fromisoformat(clean + "T00:00:00")
        except (ValueError, TypeError):
            logger.warning(f"Could not parse date: {date_str}")
            return None
    
    def _extract_breadcrumbs(self, data: Dict) -> List[Dict[str, str]]:
        """
        Extract navigation breadcrumbs from API response.
        
        Breadcrumbs show document hierarchy:
        Home > Business and self-employed > VAT > VAT Registration
        
        This helps us understand document context and relationships.
        """
        breadcrumbs = []
        
        # Try links.ordered_related_items first (newer API format)
        links = data.get("links", {})
        
        # Check for parent taxons (topic hierarchy)
        taxons = links.get("taxons", [])
        if taxons:
            for taxon in taxons:
                breadcrumbs.append({
                    "title": taxon.get("title", ""),
                    "path": taxon.get("base_path", "")
                })
        
        # Check for parent (direct parent document)
        parents = links.get("parent", [])
        if parents:
            for parent in parents:
                breadcrumbs.append({
                    "title": parent.get("title", ""),
                    "path": parent.get("base_path", "")
                })
        
        return breadcrumbs
    
    def _extract_child_sections(self, data: Dict) -> List[Dict[str, str]]:
        """
        Extract child sections for HMRC manuals.
        
        HMRC manuals are hierarchical:
        VAT Manual (top) → Sections → Subsections → Individual guidance
        
        We need to crawl all levels to get complete coverage.
        """
        children = []
        links = data.get("links", {})
        
        # For manuals - "children" contains subsections
        for child in links.get("children", []):
            children.append({
                "title": child.get("title", ""),
                "path": child.get("base_path", ""),
                "document_type": child.get("document_type", "")
            })
        
        # For some structures - "child_taxons"
        for child in links.get("child_taxons", []):
            children.append({
                "title": child.get("title", ""),
                "path": child.get("base_path", ""),
                "document_type": child.get("document_type", "")
            })
        
        return children
    
    def _extract_body_html(self, data: Dict) -> str:
        """
        Extract the main body content from API response.
        
        GOV.UK has different content structures depending on document type:
        - "body" field for simple pages
        - "parts" array for multi-part guides
        - "details.body" for some formats
        
        We handle all variations and combine into single HTML string.
        """
        details = data.get("details", {})
        
        # Case 1: Simple body field
        body = details.get("body", "")
        if body:
            return body
        
        # Case 2: Multi-part guide (like /vat-registration which has multiple tabs)
        parts = details.get("parts", [])
        if parts:
            html_parts = []
            for part in parts:
                part_title = part.get("title", "")
                part_body = part.get("body", "")
                if part_title:
                    html_parts.append(f"<h2>{part_title}</h2>")
                if part_body:
                    html_parts.append(part_body)
            return "\n".join(html_parts)
        
        # Case 3: Introduction + body (some manual sections)
        intro = details.get("introduction", "")
        main_body = details.get("body", "")
        if intro or main_body:
            parts = []
            if intro:
                parts.append(intro)
            if main_body:
                parts.append(main_body)
            return "\n".join(parts)
        
        # Case 4: child_section_groups (for manual overview pages)
        groups = details.get("child_section_groups", [])
        if groups:
            html_parts = []
            for group in groups:
                group_title = group.get("title", "")
                if group_title:
                    html_parts.append(f"<h2>{group_title}</h2>")
                child_sections = group.get("child_sections", [])
                if child_sections:
                    html_parts.append("<ul>")
                    for section in child_sections:
                        title = section.get("title", "")
                        path = section.get("base_path", "")
                        html_parts.append(f'<li><a href="{path}">{title}</a></li>')
                    html_parts.append("</ul>")
            return "\n".join(html_parts)
        
        # Fallback: return empty (will be caught by parser)
        logger.warning(f"No body content found for: {data.get('base_path', 'unknown')}")
        return ""
    
    def fetch_document(self, path_or_url: str) -> GovUKDocument:
        """
        Fetch a single document from GOV.UK API.
        
        Args:
            path_or_url: Either full URL or path like "/vat-registration"
        
        Returns:
            GovUKDocument with all extracted metadata and content
        
        Raises:
            GovUKContentAPIError: If API returns error or document not found
        
        Example:
            doc = client.fetch_document("/vat-registration")
            # doc.title = "Register for VAT"
            # doc.body_html = "<p>You must register...</p>"
        """
        path = self._normalize_path(path_or_url)
        api_url = f"{self.API_BASE}{path}"
        
        logger.info(f"Fetching: {api_url}")
        self._rate_limit()
        
        try:
            response = self.session.get(api_url, timeout=self.timeout)
            
            if response.status_code == 404:
                raise GovUKContentAPIError(f"Document not found: {path}")
            
            if response.status_code != 200:
                raise GovUKContentAPIError(
                    f"API error {response.status_code}: {response.text[:200]}"
                )
            
            data = response.json()
            
        except requests.RequestException as e:
            raise GovUKContentAPIError(f"Request failed: {e}")
        
        # Extract all fields
        links = data.get("links", {})
        parent = links.get("parent", [{}])[0] if links.get("parent") else {}
        
        return GovUKDocument(
            url=f"{self.BASE_URL}{path}",
            base_path=path,
            title=data.get("title", "Untitled"),
            description=data.get("description"),
            body_html=self._extract_body_html(data),
            document_type=data.get("document_type", "unknown"),
            schema_name=data.get("schema_name", "unknown"),
            first_published=self._parse_datetime(data.get("first_published_at")),
            last_updated=self._parse_datetime(data.get("public_updated_at")),
            breadcrumbs=self._extract_breadcrumbs(data),
            parent_title=parent.get("title"),
            parent_path=parent.get("base_path"),
            child_sections=self._extract_child_sections(data),
            raw_response=data
        )
    
    def fetch_hmrc_manual(self, manual_path: str, max_sections: Optional[int] = None) -> List[GovUKDocument]:
        """
        Fetch an entire HMRC manual with all its sections.
        
        HMRC manuals are hierarchical:
        /hmrc-internal-manuals/vat-guide (top-level)
        └── /hmrc-internal-manuals/vat-guide/vat1-1 (section)
            └── /hmrc-internal-manuals/vat-guide/vat1-1-1 (subsection)
        
        This method crawls the entire structure.
        
        Args:
            manual_path: Path to manual like "/hmrc-internal-manuals/vat-guide"
            max_sections: Limit number of sections (for testing)
        
        Returns:
            List of all documents in the manual
        """
        documents = []
        visited = set()
        to_visit = [manual_path]
        
        while to_visit:
            if max_sections and len(documents) >= max_sections:
                logger.info(f"Reached max_sections limit: {max_sections}")
                break
            
            current_path = to_visit.pop(0)
            
            if current_path in visited:
                continue
            visited.add(current_path)
            
            try:
                doc = self.fetch_document(current_path)
                documents.append(doc)
                
                # Add child sections to crawl
                for child in doc.child_sections:
                    child_path = child.get("path", "")
                    if child_path and child_path not in visited:
                        to_visit.append(child_path)
                
                logger.info(f"Fetched: {doc.title} ({len(documents)} total)")
                
            except GovUKContentAPIError as e:
                logger.error(f"Failed to fetch {current_path}: {e}")
                continue
        
        return documents
    
    def get_tax_guidance_urls(self) -> List[str]:
        """
        Returns a curated list of essential UK SME tax guidance URLs.
        
        This is our "seed list" — the core documents every UK SME needs.
        We start here and can expand based on related links.
        
        Organized by topic for clarity.
        """
        return [
            # === VAT ===
            "/vat-registration",
            "/vat-rates",
            "/vat-businesses",
            "/vat-returns",
            "/vat-record-keeping",
            "/vat-flat-rate-scheme",
            "/vat-cash-accounting-scheme",
            "/vat-annual-accounting-scheme",
            "/charge-reclaim-record-vat",
            "/pay-vat",
            "/vat-corrections",
            "/vat-registration-thresholds",
            
            # === Corporation Tax ===
            "/corporation-tax",
            "/corporation-tax-rates",
            "/prepare-file-annual-accounts-for-limited-company",
            "/company-tax-returns",
            "/pay-corporation-tax",
            "/corporation-tax-accounting-periods-and-டுe-dates",
            "/hmrc-internal-manuals/company-taxation-manual",
            
            # === Self Assessment / Income Tax ===
            "/self-assessment-tax-returns",
            "/register-for-self-assessment",
            "/understand-self-assessment-bill",
            "/pay-self-assessment-tax-bill",
            "/self-assessment-tax-return-forms",
            "/income-tax-rates",
            "/personal-allowances",
            "/tax-on-dividends",
            
            # === PAYE / Employers ===
            "/paye-for-employers",
            "/register-employer",
            "/running-payroll",
            "/payroll-annual-reporting",
            "/pay-paye-tax",
            "/employee-tax-codes",
            "/national-minimum-wage-rates",
            
            # === National Insurance ===
            "/national-insurance",
            "/national-insurance-rates-letters",
            "/self-employed-national-insurance-rates",
            "/national-insurance-classes",
            
            # === Making Tax Digital ===
            "/making-tax-digital-software",
            "/check-if-youre-eligible-for-making-tax-digital-for-income-tax",
            
            # === HMRC Services (Guidance Navigation) ===
            "/contact-hmrc",
            "/government/organisations/hm-revenue-customs/contact",
            "/sign-in-hmrc-online-services",
            "/personal-tax-account",
            "/tax-appeals",
            "/complain-about-hmrc",
            "/get-help-hmrc-extra-support",
            "/dealing-hmrc-additional-needs",
            
            # === Business Records & Compliance ===
            "/keeping-your-pay-tax-records",
            "/self-employed-records",
            "/running-a-limited-company",
            "/set-up-sole-trader",
            "/set-up-limited-company",
            "/set-up-business-partnership",
            
            # === R&D Tax Credits ===
            "/guidance/corporation-tax-research-and-development-rd-relief",
            "/hmrc-internal-manuals/corporate-intangibles-research-and-development-manual",
        ]
    
    def get_hmrc_manual_urls(self) -> List[str]:
        """
        Returns list of key HMRC technical manuals for SME tax compliance.
        
        These are the detailed manuals that accountants use.
        More technical than general guidance, but essential for accuracy.
        """
        return [
            "/hmrc-internal-manuals/vat-guide",  # Core VAT guidance
            "/hmrc-internal-manuals/vat-registration",  # VAT registration details
            "/hmrc-internal-manuals/company-taxation-manual",  # Corporation Tax
            "/hmrc-internal-manuals/business-income-manual",  # Self-employed income
            "/hmrc-internal-manuals/employment-income-manual",  # PAYE
            "/hmrc-internal-manuals/corporate-intangibles-research-and-development-manual",  # R&D
            "/hmrc-internal-manuals/self-assessment-manual",  # Self Assessment
        ]
