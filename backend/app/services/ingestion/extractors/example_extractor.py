"""
Example Extractor

Extracts worked examples from UK tax documents.
Converts to StructuredExample format.

Key Features:
- Identifies example scenarios
- Extracts calculation steps
- Links to formulas and tables used
- Preserves input values and final results
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import re
import logging

from .base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


@dataclass
class ExtractedExample:
    """Represents a worked example extracted from document."""
    
    example_name: str
    example_category: str  # income_tax, vat, corporation_tax, etc.
    
    # Scenario
    scenario: Dict[str, Any]  # Input values: {"income": 55000, "name": "Sarah"}
    scenario_description: str
    
    # Calculation steps
    steps: List[Dict[str, Any]]  # [{"step": 1, "description": "...", "calculation": "...", "result": 1000}]
    
    # Result
    final_result: Dict[str, Any]  # {"value": 8000, "label": "Tax Due"}
    
    # References
    formulas_used: List[str] = field(default_factory=list)
    tables_used: List[str] = field(default_factory=list)
    
    # Context
    full_text: str = ""
    tax_year: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "example_name": self.example_name,
            "example_category": self.example_category,
            "scenario": self.scenario,
            "scenario_description": self.scenario_description,
            "steps": self.steps,
            "final_result": self.final_result,
            "formulas_used": self.formulas_used,
            "tables_used": self.tables_used,
            "tax_year": self.tax_year,
        }


class ExampleExtractor(BaseExtractor):
    """
    Extracts worked examples from tax documents.
    
    Looks for patterns like:
    - "Example: Sarah earns £55,000..."
    - "For example, if your income is £40,000..."
    - Step-by-step calculations with amounts
    """
    
    # Example start patterns
    EXAMPLE_START_PATTERNS = [
        re.compile(r'\bexample[:\s]+([A-Z][a-z]+)', re.I),  # "Example: Sarah"
        re.compile(r'\bfor\s+example[,:\s]+', re.I),
        re.compile(r'\bsuppose\s+(?:that\s+)?', re.I),
        re.compile(r'\blet\'?s?\s+say\s+', re.I),
        re.compile(r'\bconsider\s+(?:the\s+)?(?:case|following|situation)', re.I),
    ]
    
    # Common example names
    EXAMPLE_NAMES = ['Sarah', 'John', 'Mary', 'James', 'Company A', 'ABC Ltd', 'XYZ Ltd']
    
    # Step patterns
    STEP_PATTERN = re.compile(
        r'(?:step\s+(\d+)[:\s]+|(\d+)\.\s+)(.+?)(?=step\s+\d+|^\d+\.|$)',
        re.I | re.MULTILINE | re.DOTALL
    )
    
    # Result patterns  
    RESULT_PATTERNS = [
        re.compile(r'(?:total|final|overall)\s+(?:tax|amount|sum)[:\s]+£([\d,]+)', re.I),
        re.compile(r'(?:tax\s+)?(?:due|payable|liability)[:\s]+£([\d,]+)', re.I),
        re.compile(r'=\s*£([\d,]+)', re.I),
    ]
    
    # Category patterns
    CATEGORY_PATTERNS = {
        'income_tax': [r'\bincome\s+tax\b', r'\bpaye\b', r'\bpersonal\s+allowance\b'],
        'corporation_tax': [r'\bcorporation\s+tax\b', r'\bcompany\s+(?:tax|profit)', r'\bmarginal\s+relief\b'],
        'vat': [r'\bvat\b', r'\bvalue\s+added\s+tax\b'],
        'capital_gains': [r'\bcapital\s+gains?\b', r'\bcgt\b', r'\basset\s+disposal\b'],
        'national_insurance': [r'\bnational\s+insurance\b', r'\bnic?\b', r'\bclass\s+[1-4]\b'],
        'self_assessment': [r'\bself[- ]assessment\b', r'\bsa\s+\d{3}\b'],
    }
    
    def __init__(self):
        super().__init__()
    
    def extract(
        self,
        html_content: Optional[str],
        text_content: str,
        source_url: str,
        **kwargs
    ) -> ExtractionResult[ExtractedExample]:
        """Extract worked examples from document."""
        result = ExtractionResult[ExtractedExample](source_url=source_url)
        
        if not text_content:
            return result
        
        tax_year = kwargs.get('tax_year') or self.extract_tax_year(text_content)
        
        try:
            # Find example sections
            for pattern in self.EXAMPLE_START_PATTERNS:
                for match in pattern.finditer(text_content):
                    example = self._extract_example(match, text_content, tax_year)
                    if example:
                        result.items.append(example)
            
            logger.info(f"Extracted {len(result.items)} examples from {source_url}")
            
        except Exception as e:
            result.add_error(f"Example extraction failed: {str(e)}")
        
        return result
    
    def _extract_example(
        self,
        start_match: re.Match,
        full_text: str,
        tax_year: Optional[str]
    ) -> Optional[ExtractedExample]:
        """Extract a single example."""
        
        # Get example text (up to 1500 chars or next section)
        start_pos = start_match.start()
        remaining = full_text[start_pos:start_pos + 1500]
        
        # Find end of example
        end_markers = [r'\n\n##', r'\n\nExample:', r'\n\nNote:']
        end_pos = len(remaining)
        for marker in end_markers:
            match = re.search(marker, remaining, re.I)
            if match and match.start() > 100:
                end_pos = min(end_pos, match.start())
        
        example_text = remaining[:end_pos]
        
        # Extract scenario
        scenario = self._extract_scenario(example_text)
        if not scenario:
            return None
        
        # Extract steps
        steps = self._extract_steps(example_text)
        
        # Extract final result
        final_result = self._extract_final_result(example_text)
        
        # Determine category
        category = self._determine_category(example_text)
        
        # Generate name
        example_name = self._generate_example_name(scenario, category)
        
        return ExtractedExample(
            example_name=example_name,
            example_category=category,
            scenario=scenario,
            scenario_description=self._generate_scenario_description(scenario),
            steps=steps,
            final_result=final_result,
            formulas_used=self._identify_formulas(example_text),
            tables_used=self._identify_tables(example_text),
            full_text=example_text,
            tax_year=tax_year,
        )
    
    def _extract_scenario(self, text: str) -> Dict[str, Any]:
        """Extract scenario/input values from example."""
        scenario = {}
        
        # Look for person name
        for name in self.EXAMPLE_NAMES:
            if name.lower() in text.lower():
                scenario['name'] = name
                break
        
        # Extract income/earnings
        income_patterns = [
            (r'(?:earns?|has\s+(?:income|salary)\s+of)\s+£([\d,]+)', 'income'),
            (r'(?:income|earnings?|salary)\s+(?:of\s+)?£([\d,]+)', 'income'),
            (r'(?:turnover|revenue)\s+(?:of\s+)?£([\d,]+)', 'turnover'),
            (r'(?:profits?)\s+(?:of\s+)?£([\d,]+)', 'profit'),
        ]
        
        for pattern, key in income_patterns:
            match = re.search(pattern, text, re.I)
            if match:
                try:
                    scenario[key] = int(match.group(1).replace(',', ''))
                except ValueError:
                    pass
        
        return scenario if scenario else None
    
    def _extract_steps(self, text: str) -> List[Dict[str, Any]]:
        """Extract calculation steps from example."""
        steps = []
        
        # Look for explicit steps
        for match in self.STEP_PATTERN.finditer(text):
            step_num = match.group(1) or match.group(2)
            step_text = self.clean_text(match.group(3))
            
            # Extract calculation and result
            calc_match = re.search(r'(£?[\d,]+(?:\s*[×x\*+\-/]\s*[\d,.%]+)+)', step_text)
            result_match = re.search(r'=\s*£?([\d,]+)', step_text)
            
            step = {
                "step": int(step_num),
                "description": step_text[:200],
            }
            
            if calc_match:
                step["calculation"] = calc_match.group(1)
            if result_match:
                try:
                    step["result"] = float(result_match.group(1).replace(',', ''))
                except ValueError:
                    pass
            
            steps.append(step)
        
        return steps
    
    def _extract_final_result(self, text: str) -> Dict[str, Any]:
        """Extract the final result of the example."""
        for pattern in self.RESULT_PATTERNS:
            match = pattern.search(text)
            if match:
                try:
                    value = float(match.group(1).replace(',', ''))
                    return {
                        "value": value,
                        "label": "Tax Due",
                        "formatted": f"£{value:,.2f}"
                    }
                except ValueError:
                    pass
        
        return {"value": None, "label": "Result not extracted"}
    
    def _determine_category(self, text: str) -> str:
        """Determine the category of the example."""
        text_lower = text.lower()
        
        for category, patterns in self.CATEGORY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return category
        
        return 'general'
    
    def _generate_example_name(self, scenario: Dict, category: str) -> str:
        """Generate a descriptive name for the example."""
        parts = []
        
        if 'name' in scenario:
            parts.append(scenario['name'])
        
        if 'income' in scenario:
            parts.append(f"£{scenario['income']:,} income")
        elif 'profit' in scenario:
            parts.append(f"£{scenario['profit']:,} profit")
        elif 'turnover' in scenario:
            parts.append(f"£{scenario['turnover']:,} turnover")
        
        category_names = {
            'income_tax': 'Income Tax',
            'corporation_tax': 'Corporation Tax',
            'vat': 'VAT',
            'capital_gains': 'Capital Gains Tax',
            'national_insurance': 'National Insurance',
        }
        
        if parts:
            return f"{' - '.join(parts)} - {category_names.get(category, 'Tax')} Example"
        return f"{category_names.get(category, 'Tax')} Calculation Example"
    
    def _generate_scenario_description(self, scenario: Dict) -> str:
        """Generate a human-readable scenario description."""
        parts = []
        
        if 'name' in scenario:
            parts.append(scenario['name'])
        
        if 'income' in scenario:
            parts.append(f"has income of £{scenario['income']:,}")
        
        if parts:
            return ' '.join(parts)
        return "Example calculation"
    
    def _identify_formulas(self, text: str) -> List[str]:
        """Identify formulas used in the example."""
        formulas = []
        
        formula_indicators = {
            'marginal relief': 'Marginal Relief Formula',
            'personal allowance': 'Personal Allowance Calculation',
            'tax band': 'Tax Band Calculation',
        }
        
        text_lower = text.lower()
        for indicator, formula_name in formula_indicators.items():
            if indicator in text_lower:
                formulas.append(formula_name)
        
        return formulas
    
    def _identify_tables(self, text: str) -> List[str]:
        """Identify tables referenced in the example."""
        tables = []
        
        table_indicators = {
            'tax rate': 'Tax Rates',
            'tax band': 'Tax Bands',
            'threshold': 'Thresholds',
        }
        
        text_lower = text.lower()
        for indicator, table_name in table_indicators.items():
            if indicator in text_lower:
                tables.append(table_name)
        
        return tables
    
    def has_examples(self, text: str) -> bool:
        """Quick check if text contains examples."""
        return any(pattern.search(text) for pattern in self.EXAMPLE_START_PATTERNS)
