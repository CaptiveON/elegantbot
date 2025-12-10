"""
Formula Extractor

Detects and parses formulas and calculation patterns from UK tax documents.
Converts to StructuredFormula format for precise calculation execution.

Key Features:
- Detects calculation patterns in text
- Extracts variables and their types
- Identifies formula context (what tax this calculates)
- Links to related tables (tax rates, thresholds)

Example Formulas in UK Tax Documents:
- Corporation tax marginal relief: 3/200 × (£250,000 - P) × (TTP/P)
- Income tax calculation: (Income - Personal Allowance) × Rate
- VAT calculation: Net amount × VAT rate
- Penalty calculation: Tax due × penalty rate × days late
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import re
import logging

from .base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


@dataclass
class ExtractedFormula:
    """
    Represents a formula extracted from document text.
    """
    # === Identification ===
    formula_name: str
    formula_type: str  # Maps to FormulaType enum
    
    # === Formula Content ===
    formula_text: str          # Human-readable: "Tax = Income × Rate"
    formula_description: str   # Explanation of what it calculates
    
    # === Variables ===
    variables: Dict[str, Dict[str, Any]]  # {name: {type, description, example}}
    
    # === Logic (for execution) ===
    formula_logic: Dict[str, Any]  # Structured representation
    
    # === References ===
    tables_used: List[str] = field(default_factory=list)     # Related table names
    source_section: Optional[str] = None
    
    # === Temporal ===
    tax_year: Optional[str] = None
    
    # === Context ===
    context_text: str = ""  # Surrounding text for RAG
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "formula_name": self.formula_name,
            "formula_type": self.formula_type,
            "formula_text": self.formula_text,
            "formula_description": self.formula_description,
            "variables": self.variables,
            "formula_logic": self.formula_logic,
            "tables_used": self.tables_used,
            "tax_year": self.tax_year,
            "context_text": self.context_text,
        }


class FormulaExtractor(BaseExtractor):
    """
    Extracts calculation formulas from tax document text.
    
    Strategy:
    1. Find calculation indicator patterns (equals, multiply, etc.)
    2. Extract formula components
    3. Identify variables and their types
    4. Classify formula type
    5. Build structured logic representation
    
    Usage:
        extractor = FormulaExtractor()
        result = extractor.extract(html_content, text_content, source_url)
        
        for formula in result.items:
            print(f"Found: {formula.formula_name}")
            print(f"  Formula: {formula.formula_text}")
            print(f"  Variables: {formula.variables}")
    """
    
    # =========================================================================
    # FORMULA DETECTION PATTERNS
    # =========================================================================
    
    # Main calculation indicators
    CALCULATION_PATTERNS = [
        # Explicit formula statements
        re.compile(
            r'(?:the\s+)?(?:calculation|formula|equation)\s+is[:\s]+(.{20,200})',
            re.IGNORECASE
        ),
        # "calculated as/by"
        re.compile(
            r'(?:is\s+)?calculated\s+(?:as|by)[:\s]+(.{20,200})',
            re.IGNORECASE
        ),
        # Mathematical notation with equals
        re.compile(
            r'([A-Z][a-zA-Z\s]+)\s*=\s*([^.]+(?:×|x|\*|/|÷|\+|-)[^.]+)',
            re.IGNORECASE
        ),
        # Fraction patterns like 3/200
        re.compile(
            r'(\d+/\d+)\s*[×x\*]\s*\(([^)]+)\)',
            re.IGNORECASE
        ),
    ]
    
    # Specific formula types
    MARGINAL_RELIEF_PATTERN = re.compile(
        r'(?:marginal\s+relief|small\s+profits\s+rate).{0,50}(3/200|\d+/\d+).{0,100}',
        re.IGNORECASE | re.DOTALL
    )
    
    TAX_CALCULATION_PATTERN = re.compile(
        r'(?:tax\s+(?:due|payable|liability)|income\s+tax|corporation\s+tax).{0,30}(?:=|is\s+calculated).{0,150}',
        re.IGNORECASE | re.DOTALL
    )
    
    PENALTY_CALCULATION_PATTERN = re.compile(
        r'(?:penalty|surcharge).{0,30}(?:=|is\s+calculated|amounts?\s+to).{0,150}',
        re.IGNORECASE | re.DOTALL
    )
    
    VAT_CALCULATION_PATTERN = re.compile(
        r'(?:vat\s+(?:due|payable|amount)).{0,30}(?:=|is\s+calculated).{0,150}',
        re.IGNORECASE | re.DOTALL
    )
    
    RELIEF_CALCULATION_PATTERN = re.compile(
        r'(?:relief|allowance|deduction).{0,30}(?:=|is\s+calculated).{0,150}',
        re.IGNORECASE | re.DOTALL
    )
    
    # Variable patterns
    VARIABLE_PATTERNS = {
        'income': re.compile(r'\b(?:income|earnings?|profits?|turnover)\b', re.I),
        'rate': re.compile(r'\b(?:rate|percentage|%)\b', re.I),
        'threshold': re.compile(r'\b(?:threshold|limit|allowance)\b', re.I),
        'period': re.compile(r'\b(?:days?|months?|years?|period)\b', re.I),
        'amount': re.compile(r'\b(?:amount|sum|total|value)\b', re.I),
    }
    
    # Mathematical operators
    OPERATORS = {
        '×': 'multiply',
        'x': 'multiply',
        '*': 'multiply',
        '/': 'divide',
        '÷': 'divide',
        '+': 'add',
        '-': 'subtract',
    }
    
    def __init__(self):
        super().__init__()
    
    def extract(
        self,
        html_content: Optional[str],
        text_content: str,
        source_url: str,
        **kwargs
    ) -> ExtractionResult[ExtractedFormula]:
        """
        Extract formulas from document text.
        """
        result = ExtractionResult[ExtractedFormula](source_url=source_url)
        
        if not text_content:
            return result
        
        tax_year = kwargs.get('tax_year') or self.extract_tax_year(text_content)
        
        try:
            # Extract different formula types
            formulas = []
            
            # Check for specific formula types
            if self.MARGINAL_RELIEF_PATTERN.search(text_content):
                formula = self._extract_marginal_relief(text_content, tax_year)
                if formula:
                    formulas.append(formula)
            
            if self.TAX_CALCULATION_PATTERN.search(text_content):
                formula = self._extract_tax_calculation(text_content, tax_year)
                if formula:
                    formulas.append(formula)
            
            if self.PENALTY_CALCULATION_PATTERN.search(text_content):
                formula = self._extract_penalty_calculation(text_content, tax_year)
                if formula:
                    formulas.append(formula)
            
            if self.VAT_CALCULATION_PATTERN.search(text_content):
                formula = self._extract_vat_calculation(text_content, tax_year)
                if formula:
                    formulas.append(formula)
            
            # Generic formula extraction
            for pattern in self.CALCULATION_PATTERNS:
                for match in pattern.finditer(text_content):
                    formula = self._parse_generic_formula(
                        match.group(0), 
                        text_content,
                        match.start(),
                        tax_year
                    )
                    if formula and not self._is_duplicate(formula, formulas):
                        formulas.append(formula)
            
            result.items = formulas
            logger.info(f"Extracted {len(formulas)} formulas from {source_url}")
            
        except Exception as e:
            result.add_error(f"Formula extraction failed: {str(e)}")
        
        return result
    
    def _is_duplicate(
        self, 
        new_formula: ExtractedFormula, 
        existing: List[ExtractedFormula]
    ) -> bool:
        """Check if formula is a duplicate."""
        for f in existing:
            if f.formula_name == new_formula.formula_name:
                return True
            if f.formula_text == new_formula.formula_text:
                return True
        return False
    
    def _extract_marginal_relief(
        self, 
        text: str, 
        tax_year: Optional[str]
    ) -> Optional[ExtractedFormula]:
        """
        Extract corporation tax marginal relief formula.
        
        Standard formula: 3/200 × (UL - P) × (TTP/P)
        Where:
        - UL = Upper limit (£250,000)
        - P = Augmented profits
        - TTP = Taxable total profits
        """
        match = self.MARGINAL_RELIEF_PATTERN.search(text)
        if not match:
            return None
        
        context_start = max(0, match.start() - 200)
        context_end = min(len(text), match.end() + 200)
        context = text[context_start:context_end]
        
        # Extract the fraction (usually 3/200)
        fraction_match = re.search(r'(\d+)/(\d+)', match.group(0))
        fraction = "3/200" if not fraction_match else f"{fraction_match.group(1)}/{fraction_match.group(2)}"
        
        # Standard upper limit
        upper_limit = 250000
        ul_match = re.search(r'£([\d,]+)\s*(?:upper\s+limit)?', context)
        if ul_match:
            try:
                upper_limit = int(ul_match.group(1).replace(',', ''))
            except ValueError:
                pass
        
        return ExtractedFormula(
            formula_name="Corporation Tax Marginal Relief",
            formula_type="marginal_relief",
            formula_text=f"Marginal Relief = {fraction} × (£{upper_limit:,} - Augmented Profits) × (Taxable Profits / Augmented Profits)",
            formula_description="Calculates the marginal relief for corporation tax when profits fall between the small profits rate and main rate thresholds",
            variables={
                "augmented_profits": {
                    "type": "currency_gbp",
                    "description": "Company's augmented profits (profits + dividends from non-group companies)",
                    "symbol": "P"
                },
                "taxable_profits": {
                    "type": "currency_gbp",
                    "description": "Taxable total profits of the company",
                    "symbol": "TTP"
                },
                "upper_limit": {
                    "type": "currency_gbp",
                    "description": "Upper profits limit",
                    "default_value": upper_limit,
                    "symbol": "UL"
                },
                "fraction": {
                    "type": "fraction",
                    "description": "Marginal relief fraction",
                    "default_value": fraction
                }
            },
            formula_logic={
                "type": "marginal_relief",
                "steps": [
                    {"operation": "subtract", "operands": ["upper_limit", "augmented_profits"], "result": "excess"},
                    {"operation": "divide", "operands": ["taxable_profits", "augmented_profits"], "result": "ratio"},
                    {"operation": "multiply", "operands": ["excess", "ratio"], "result": "product"},
                    {"operation": "multiply", "operands": ["product", fraction], "result": "relief"}
                ]
            },
            tables_used=["Corporation Tax Rates"],
            tax_year=tax_year,
            context_text=context
        )
    
    def _extract_tax_calculation(
        self, 
        text: str, 
        tax_year: Optional[str]
    ) -> Optional[ExtractedFormula]:
        """Extract generic tax calculation formula."""
        match = self.TAX_CALCULATION_PATTERN.search(text)
        if not match:
            return None
        
        context_start = max(0, match.start() - 100)
        context_end = min(len(text), match.end() + 100)
        context = text[context_start:context_end]
        
        # Determine if income tax or corporation tax
        is_income_tax = 'income tax' in context.lower()
        is_corp_tax = 'corporation tax' in context.lower()
        
        if is_income_tax:
            return ExtractedFormula(
                formula_name="Income Tax Calculation",
                formula_type="tax_calculation",
                formula_text="Income Tax = (Taxable Income - Personal Allowance) × Tax Rate",
                formula_description="Calculates income tax by applying the appropriate tax rate to taxable income after deducting the personal allowance",
                variables={
                    "taxable_income": {
                        "type": "currency_gbp",
                        "description": "Total taxable income from all sources"
                    },
                    "personal_allowance": {
                        "type": "currency_gbp",
                        "description": "Tax-free personal allowance",
                        "default_value": 12570
                    },
                    "tax_rate": {
                        "type": "percentage",
                        "description": "Applicable tax rate based on income band"
                    }
                },
                formula_logic={
                    "type": "banded_calculation",
                    "uses_table": "income_tax_rates"
                },
                tables_used=["Income Tax Rates"],
                tax_year=tax_year,
                context_text=context
            )
        elif is_corp_tax:
            return ExtractedFormula(
                formula_name="Corporation Tax Calculation",
                formula_type="tax_calculation",
                formula_text="Corporation Tax = Taxable Profits × Corporation Tax Rate",
                formula_description="Calculates corporation tax on company profits",
                variables={
                    "taxable_profits": {
                        "type": "currency_gbp",
                        "description": "Company's taxable profits"
                    },
                    "tax_rate": {
                        "type": "percentage",
                        "description": "Corporation tax rate (main rate or small profits rate)"
                    }
                },
                formula_logic={
                    "type": "simple_multiplication",
                    "may_require_marginal_relief": True
                },
                tables_used=["Corporation Tax Rates"],
                tax_year=tax_year,
                context_text=context
            )
        
        return None
    
    def _extract_penalty_calculation(
        self, 
        text: str, 
        tax_year: Optional[str]
    ) -> Optional[ExtractedFormula]:
        """Extract penalty calculation formula."""
        match = self.PENALTY_CALCULATION_PATTERN.search(text)
        if not match:
            return None
        
        context_start = max(0, match.start() - 100)
        context_end = min(len(text), match.end() + 100)
        context = text[context_start:context_end]
        
        return ExtractedFormula(
            formula_name="Penalty Calculation",
            formula_type="penalty_calculation",
            formula_text="Penalty = Base Penalty + (Daily Penalty × Days Late)",
            formula_description="Calculates late filing or payment penalties",
            variables={
                "base_penalty": {
                    "type": "currency_gbp",
                    "description": "Fixed penalty for being late"
                },
                "daily_penalty": {
                    "type": "currency_gbp",
                    "description": "Additional daily penalty (if applicable)"
                },
                "days_late": {
                    "type": "number",
                    "description": "Number of days past deadline"
                }
            },
            formula_logic={
                "type": "penalty_tiered",
                "uses_table": "penalty_schedule"
            },
            tables_used=["Penalty Schedule"],
            tax_year=tax_year,
            context_text=context
        )
    
    def _extract_vat_calculation(
        self, 
        text: str, 
        tax_year: Optional[str]
    ) -> Optional[ExtractedFormula]:
        """Extract VAT calculation formula."""
        match = self.VAT_CALCULATION_PATTERN.search(text)
        if not match:
            return None
        
        context_start = max(0, match.start() - 100)
        context_end = min(len(text), match.end() + 100)
        context = text[context_start:context_end]
        
        return ExtractedFormula(
            formula_name="VAT Calculation",
            formula_type="vat_calculation",
            formula_text="VAT = Net Amount × VAT Rate",
            formula_description="Calculates VAT on goods or services",
            variables={
                "net_amount": {
                    "type": "currency_gbp",
                    "description": "Net value excluding VAT"
                },
                "vat_rate": {
                    "type": "percentage",
                    "description": "VAT rate (standard 20%, reduced 5%, or zero 0%)",
                    "default_value": 20
                }
            },
            formula_logic={
                "type": "simple_multiplication",
                "default_rate": 20
            },
            tables_used=["VAT Rates"],
            tax_year=tax_year,
            context_text=context
        )
    
    def _parse_generic_formula(
        self, 
        formula_text: str, 
        full_text: str,
        position: int,
        tax_year: Optional[str]
    ) -> Optional[ExtractedFormula]:
        """Parse a generic formula pattern."""
        # Skip if too short or too long
        if len(formula_text) < 10 or len(formula_text) > 300:
            return None
        
        # Get context
        context_start = max(0, position - 100)
        context_end = min(len(full_text), position + len(formula_text) + 100)
        context = full_text[context_start:context_end]
        
        # Try to identify formula name from context
        formula_name = "Calculation"
        name_patterns = [
            r'(?:to\s+)?calculate\s+(?:the\s+)?([a-z]+(?:\s+[a-z]+){0,2})',
            r'([a-z]+(?:\s+[a-z]+){0,2})\s+(?:is\s+)?calculated',
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, context, re.I)
            if match:
                formula_name = match.group(1).title()
                break
        
        # Extract variables mentioned
        variables = {}
        for var_name, pattern in self.VARIABLE_PATTERNS.items():
            if pattern.search(formula_text):
                variables[var_name] = {
                    "type": "unknown",
                    "description": f"Variable: {var_name}"
                }
        
        return ExtractedFormula(
            formula_name=formula_name,
            formula_type="other",
            formula_text=self.clean_text(formula_text),
            formula_description=f"Calculation found in document",
            variables=variables,
            formula_logic={"type": "generic", "raw_text": formula_text},
            tax_year=tax_year,
            context_text=context
        )
    
    def has_formulas(self, text: str) -> bool:
        """Quick check if text likely contains formulas."""
        formula_indicators = [
            r'calculated\s+(?:as|by)',
            r'=\s*[^=]',  # equals sign not doubled
            r'\d+/\d+\s*[×x\*]',  # fraction times something
            r'formula',
            r'multiply|divide|subtract|add',
        ]
        
        return any(re.search(p, text, re.I) for p in formula_indicators)
