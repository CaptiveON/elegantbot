"""
Table Extractor

Detects and parses HTML tables from UK tax documents.
Converts to StructuredTable format for precise data extraction.

Key Features:
- Identifies table type based on headers (tax rates, penalties, etc.)
- Extracts structured row data with type inference
- Handles merged cells and complex table structures
- Generates readable text version for RAG chunking

Example Tables Found in UK Tax Documents:
- Income tax bands and rates
- VAT rate categories
- Penalty schedules (days late → penalty amount)
- National Insurance thresholds
- Filing deadline calendars
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup, Tag
import re
import logging

from .base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


@dataclass
class ExtractedTable:
    """
    Represents a table extracted from HTML.
    
    This intermediate format is converted to StructuredTable
    when stored in the database.
    """
    # === Structure ===
    headers: List[str]
    rows: List[Dict[str, Any]]
    
    # === Classification ===
    table_type: str  # Maps to TableType enum
    table_name: str
    table_description: Optional[str] = None
    
    # === Type Information ===
    column_types: Dict[str, str] = field(default_factory=dict)
    column_descriptions: Dict[str, str] = field(default_factory=dict)
    
    # === Query Helpers ===
    lookup_keys: List[str] = field(default_factory=list)
    value_columns: List[str] = field(default_factory=list)
    
    # === Temporal ===
    tax_year: Optional[str] = None
    
    # === Position in Document ===
    position_index: int = 0  # Which table in the document (0-indexed)
    
    # === Text Representation ===
    readable_text: str = ""  # Human-readable version for RAG
    
    # === Raw HTML (for debugging) ===
    raw_html: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            "headers": self.headers,
            "rows": self.rows,
            "table_type": self.table_type,
            "table_name": self.table_name,
            "table_description": self.table_description,
            "column_types": self.column_types,
            "column_descriptions": self.column_descriptions,
            "lookup_keys": self.lookup_keys,
            "value_columns": self.value_columns,
            "tax_year": self.tax_year,
            "readable_text": self.readable_text,
        }


class TableExtractor(BaseExtractor):
    """
    Extracts and classifies tables from HTML content.
    
    Strategy:
    1. Find all <table> elements in HTML
    2. Extract headers and data rows
    3. Classify table type based on header keywords
    4. Infer column data types
    5. Generate readable text representation
    
    Usage:
        extractor = TableExtractor()
        result = extractor.extract(html_content, text_content, source_url)
        
        for table in result.items:
            print(f"Found {table.table_type} table: {table.table_name}")
            print(f"  Columns: {table.headers}")
            print(f"  Rows: {len(table.rows)}")
    """
    
    # =========================================================================
    # TABLE TYPE CLASSIFICATION
    # =========================================================================
    
    # Keywords that identify table types
    TABLE_TYPE_KEYWORDS = {
        "tax_rates": [
            r'\brate\b', r'\bband\b', r'\btax\s+rate', r'\bincome\s+tax',
            r'\bcorporation\s+tax', r'\btaxable\s+income'
        ],
        "vat_rates": [
            r'\bvat\s+rate', r'\bstandard\s+rate', r'\breduced\s+rate',
            r'\bzero[- ]rated', r'\bexempt'
        ],
        "penalties": [
            r'\bpenalt', r'\bsurcharge', r'\bfine\b', r'\blate\s+filing',
            r'\blate\s+payment', r'\bdays?\s+late'
        ],
        "thresholds": [
            r'\bthreshold', r'\blimit\b', r'\bmaximum', r'\bminimum',
            r'\ballowance', r'\bexemption\s+limit'
        ],
        "deadlines": [
            r'\bdeadline', r'\bdue\s+date', r'\bfiling\s+date',
            r'\bpayment\s+date', r'\bsubmission'
        ],
        "ni_rates": [
            r'\bnational\s+insurance', r'\bni\s+rate', r'\bclass\s+[1-4]',
            r'\bnic\b', r'\bemployer.{0,10}ni'
        ],
        "ni_thresholds": [
            r'\bni\s+threshold', r'\bprimary\s+threshold',
            r'\bsecondary\s+threshold', r'\bupper\s+earnings'
        ],
        "allowances": [
            r'\bpersonal\s+allowance', r'\bcapital\s+allowance',
            r'\bannual\s+allowance', r'\btax.free'
        ],
        "mileage_rates": [
            r'\bmileage', r'\bapproved\s+mileage', r'\bbusiness\s+miles',
            r'\bpence\s+per\s+mile'
        ],
        "benefit_rates": [
            r'\bbenefit\s+in\s+kind', r'\bbik\b', r'\bcompany\s+car',
            r'\bp11d'
        ],
    }
    
    # Header keywords for identifying lookup/value columns
    LOOKUP_KEYWORDS = [
        r'\bfrom\b', r'\bover\b', r'\babove\b', r'\bband\b',
        r'\bcategory', r'\btype\b', r'\bclass\b', r'\bdays?'
    ]
    
    VALUE_KEYWORDS = [
        r'\brate\b', r'\bamount', r'\b%\b', r'\bpenalty',
        r'\btax\b', r'\bpayable', r'\bdue\b'
    ]
    
    def __init__(self):
        super().__init__()
    
    def extract(
        self,
        html_content: Optional[str],
        text_content: str,
        source_url: str,
        **kwargs
    ) -> ExtractionResult[ExtractedTable]:
        """
        Extract all tables from HTML content.
        
        Args:
            html_content: Raw HTML containing tables
            text_content: Cleaned text (used for context)
            source_url: URL for citation
            **kwargs: Optional tax_year parameter
        
        Returns:
            ExtractionResult containing ExtractedTable items
        """
        result = ExtractionResult[ExtractedTable](source_url=source_url)
        
        if not html_content:
            return result
        
        # Get tax year from context if not provided
        tax_year = kwargs.get('tax_year') or self.extract_tax_year(text_content)
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            tables = soup.find_all('table')
            
            for idx, table_elem in enumerate(tables):
                try:
                    extracted = self._extract_table(table_elem, idx, tax_year)
                    if extracted and extracted.rows:
                        result.items.append(extracted)
                except Exception as e:
                    result.add_warning(f"Failed to extract table {idx}: {str(e)}")
            
            logger.info(f"Extracted {len(result.items)} tables from {source_url}")
            
        except Exception as e:
            result.add_error(f"Table extraction failed: {str(e)}")
        
        return result
    
    def _extract_table(
        self, 
        table_elem: Tag, 
        position: int,
        tax_year: Optional[str]
    ) -> Optional[ExtractedTable]:
        """
        Extract a single table element.
        """
        # Get raw HTML for reference
        raw_html = str(table_elem)[:2000]  # Truncate very large tables
        
        # Extract headers
        headers = self._extract_headers(table_elem)
        if not headers:
            return None
        
        # Extract rows
        rows = self._extract_rows(table_elem, headers)
        if not rows:
            return None
        
        # Classify table type
        header_text = ' '.join(headers)
        table_type = self._classify_table_type(header_text, rows)
        
        # Infer column types
        column_types = self._infer_column_types(headers, rows)
        
        # Identify lookup and value columns
        lookup_keys = self._identify_lookup_columns(headers)
        value_columns = self._identify_value_columns(headers)
        
        # Generate table name
        table_name = self._generate_table_name(table_type, headers, tax_year)
        
        # Generate readable text
        readable_text = self._generate_readable_text(headers, rows, table_name)
        
        return ExtractedTable(
            headers=headers,
            rows=rows,
            table_type=table_type,
            table_name=table_name,
            column_types=column_types,
            lookup_keys=lookup_keys,
            value_columns=value_columns,
            tax_year=tax_year,
            position_index=position,
            readable_text=readable_text,
            raw_html=raw_html
        )
    
    def _extract_headers(self, table_elem: Tag) -> List[str]:
        """
        Extract column headers from table.
        
        Tries multiple strategies:
        1. <thead> > <tr> > <th>
        2. First <tr> with <th> elements
        3. First <tr> with <td> elements (treat as headers)
        """
        headers = []
        
        # Try thead first
        thead = table_elem.find('thead')
        if thead:
            header_row = thead.find('tr')
            if header_row:
                headers = [
                    self.clean_text(th.get_text())
                    for th in header_row.find_all(['th', 'td'])
                ]
        
        # Try first row with th elements
        if not headers:
            first_row = table_elem.find('tr')
            if first_row:
                th_cells = first_row.find_all('th')
                if th_cells:
                    headers = [self.clean_text(th.get_text()) for th in th_cells]
        
        # Last resort: treat first row as headers
        if not headers:
            first_row = table_elem.find('tr')
            if first_row:
                cells = first_row.find_all(['td', 'th'])
                # Only use if cells have text and aren't just numbers
                cell_texts = [self.clean_text(c.get_text()) for c in cells]
                if cell_texts and not all(re.match(r'^[\d,.%£]+$', t) for t in cell_texts if t):
                    headers = cell_texts
        
        # Normalize headers (remove empty, ensure unique)
        headers = [h or f"Column_{i}" for i, h in enumerate(headers)]
        headers = self._make_headers_unique(headers)
        
        return headers
    
    def _make_headers_unique(self, headers: List[str]) -> List[str]:
        """Ensure all header names are unique."""
        seen = {}
        unique = []
        for h in headers:
            if h in seen:
                seen[h] += 1
                unique.append(f"{h}_{seen[h]}")
            else:
                seen[h] = 0
                unique.append(h)
        return unique
    
    def _extract_rows(self, table_elem: Tag, headers: List[str]) -> List[Dict[str, Any]]:
        """
        Extract data rows from table.
        
        Handles:
        - Basic row extraction
        - Merged cells (colspan/rowspan)
        - Type conversion (numbers, percentages, currency)
        """
        rows = []
        
        # Find tbody or use table directly
        tbody = table_elem.find('tbody') or table_elem
        
        # Get all tr elements
        all_rows = tbody.find_all('tr')
        
        # Skip header row(s)
        data_rows = all_rows[1:] if all_rows else []
        
        # Also check if first row is in thead (already skipped)
        thead = table_elem.find('thead')
        if thead:
            data_rows = [r for r in all_rows if r.parent != thead]
        
        for tr in data_rows:
            cells = tr.find_all(['td', 'th'])
            
            if not cells:
                continue
            
            # Extract cell values
            values = [self._parse_cell_value(c) for c in cells]
            
            # Pad or truncate to match headers
            while len(values) < len(headers):
                values.append(None)
            values = values[:len(headers)]
            
            # Create row dict
            row = dict(zip(headers, values))
            
            # Skip rows that are all empty or all None
            if any(v is not None and v != '' for v in row.values()):
                rows.append(row)
        
        return rows
    
    def _parse_cell_value(self, cell: Tag) -> Any:
        """
        Parse a table cell value with type inference.
        
        Converts:
        - £1,234.56 → 1234.56 (float)
        - 20% → 20.0 (float, stored as percentage)
        - 1,000 → 1000 (int)
        - Other → string
        """
        text = self.clean_text(cell.get_text())
        
        if not text or text == '-' or text.lower() == 'n/a':
            return None
        
        # Try currency
        currency_match = self.GBP_PATTERN.search(text)
        if currency_match:
            amount_str = currency_match.group(1).replace(',', '')
            try:
                return float(amount_str)
            except ValueError:
                pass
        
        # Try percentage
        pct_match = self.PERCENTAGE_PATTERN.search(text)
        if pct_match:
            try:
                return float(pct_match.group(1))
            except ValueError:
                pass
        
        # Try plain number
        plain_num = re.sub(r'[,\s]', '', text)
        if re.match(r'^-?\d+(?:\.\d+)?$', plain_num):
            try:
                if '.' in plain_num:
                    return float(plain_num)
                return int(plain_num)
            except ValueError:
                pass
        
        return text
    
    def _classify_table_type(
        self, 
        header_text: str, 
        rows: List[Dict[str, Any]]
    ) -> str:
        """
        Classify the table type based on headers and content.
        """
        header_lower = header_text.lower()
        
        # Also check first few row values for context
        sample_values = []
        for row in rows[:3]:
            sample_values.extend(str(v).lower() for v in row.values() if v)
        sample_text = ' '.join(sample_values)
        combined_text = header_lower + ' ' + sample_text
        
        for table_type, patterns in self.TABLE_TYPE_KEYWORDS.items():
            for pattern in patterns:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    return table_type
        
        return "other"
    
    def _infer_column_types(
        self, 
        headers: List[str], 
        rows: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Infer data types for each column.
        """
        column_types = {}
        
        for header in headers:
            values = [str(row.get(header, '')) for row in rows if row.get(header) is not None]
            column_types[header] = self.infer_column_type(values)
        
        return column_types
    
    def _identify_lookup_columns(self, headers: List[str]) -> List[str]:
        """Identify which columns are suitable for lookups."""
        lookup_cols = []
        
        for header in headers:
            header_lower = header.lower()
            for pattern in self.LOOKUP_KEYWORDS:
                if re.search(pattern, header_lower):
                    lookup_cols.append(header)
                    break
        
        return lookup_cols
    
    def _identify_value_columns(self, headers: List[str]) -> List[str]:
        """Identify which columns contain the answer values."""
        value_cols = []
        
        for header in headers:
            header_lower = header.lower()
            for pattern in self.VALUE_KEYWORDS:
                if re.search(pattern, header_lower):
                    value_cols.append(header)
                    break
        
        return value_cols
    
    def _generate_table_name(
        self, 
        table_type: str, 
        headers: List[str],
        tax_year: Optional[str]
    ) -> str:
        """Generate a descriptive name for the table."""
        type_names = {
            "tax_rates": "Tax Rates",
            "vat_rates": "VAT Rates", 
            "penalties": "Penalty Schedule",
            "thresholds": "Thresholds",
            "deadlines": "Deadlines",
            "ni_rates": "National Insurance Rates",
            "ni_thresholds": "National Insurance Thresholds",
            "allowances": "Allowances",
            "mileage_rates": "Mileage Rates",
            "benefit_rates": "Benefit Rates",
            "other": "Data Table"
        }
        
        base_name = type_names.get(table_type, "Table")
        
        if tax_year:
            return f"{base_name} {tax_year}"
        
        return base_name
    
    def _generate_readable_text(
        self, 
        headers: List[str], 
        rows: List[Dict[str, Any]],
        table_name: str
    ) -> str:
        """
        Generate a human-readable text version of the table.
        
        This is included in chunks for RAG retrieval.
        
        Example output:
        "Income Tax Rates 2024-25:
        - Basic rate band (£12,571 to £50,270): 20%
        - Higher rate band (£50,271 to £125,140): 40%
        - Additional rate band (over £125,140): 45%"
        """
        lines = [f"{table_name}:"]
        
        for row in rows:
            # Try to create a natural language description
            parts = []
            for header, value in row.items():
                if value is not None and value != '':
                    # Format value appropriately
                    if isinstance(value, float):
                        # Check if it's a percentage or currency
                        if 'rate' in header.lower() or '%' in header:
                            parts.append(f"{header}: {value}%")
                        elif value >= 1000:
                            parts.append(f"{header}: £{value:,.0f}")
                        else:
                            parts.append(f"{header}: {value}")
                    else:
                        parts.append(f"{header}: {value}")
            
            if parts:
                lines.append(f"  • {', '.join(parts)}")
        
        return '\n'.join(lines)
    
    def has_tables(self, html_content: str) -> bool:
        """Quick check if HTML contains tables."""
        if not html_content:
            return False
        return '<table' in html_content.lower()
