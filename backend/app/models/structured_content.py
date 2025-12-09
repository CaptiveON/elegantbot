"""
Structured Content Models

Models for storing structured content extracted from UK tax documents:
- Tables (tax rates, penalties, thresholds)
- Formulas (tax calculations)
- Decision Trees (eligibility checks, requirements)
- Deadlines (filing dates, payment dates)
- Examples (worked calculations)
- Contacts (HMRC helplines, addresses)
- Condition Lists (legal requirements)

These enable precise data extraction and validation beyond free-text RAG retrieval.
"""

from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean, ForeignKey, Enum as SQLEnum, Numeric
from sqlalchemy.orm import relationship, backref
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import uuid
from enum import StrEnum
from app.database import Base


# =============================================================================
# ENUMS
# =============================================================================

class TableType(StrEnum):
    """Types of tables found in tax documents."""
    TAX_RATES = "tax_rates"               # Income tax, corporation tax bands
    VAT_RATES = "vat_rates"               # VAT rate categories
    THRESHOLDS = "thresholds"             # Registration thresholds, limits
    PENALTIES = "penalties"               # Penalty schedules
    DEADLINES = "deadlines"               # Filing/payment deadline tables
    ALLOWANCES = "allowances"             # Personal allowance, capital allowances
    NI_RATES = "ni_rates"                 # National Insurance rates
    NI_THRESHOLDS = "ni_thresholds"       # NI thresholds
    MILEAGE_RATES = "mileage_rates"       # Approved mileage rates
    BENEFIT_RATES = "benefit_rates"       # Benefit in kind rates
    COMPARISON = "comparison"             # Feature comparisons
    OTHER = "other"


class FormulaType(StrEnum):
    """Types of formulas found in tax documents."""
    TAX_CALCULATION = "tax_calculation"           # Basic tax calculation
    MARGINAL_RELIEF = "marginal_relief"           # Marginal relief calculations
    PENALTY_CALCULATION = "penalty_calculation"   # Penalty amount calculations
    ALLOWANCE_CALCULATION = "allowance_calculation"
    THRESHOLD_TEST = "threshold_test"             # Testing against thresholds
    RELIEF_CALCULATION = "relief_calculation"     # Tax relief calculations
    NI_CALCULATION = "ni_calculation"             # National Insurance
    VAT_CALCULATION = "vat_calculation"           # VAT calculations
    INTEREST_CALCULATION = "interest_calculation" # Interest on late payment
    PRORATION = "proration"                       # Prorating for partial periods


class DecisionCategory(StrEnum):
    """Categories of decision trees."""
    REGISTRATION = "registration"         # Do I need to register for X?
    ELIGIBILITY = "eligibility"           # Am I eligible for X?
    FILING = "filing"                     # Do I need to file X?
    PAYMENT = "payment"                   # Do I need to pay X?
    EXEMPTION = "exemption"               # Am I exempt from X?
    SCHEME_CHOICE = "scheme_choice"       # Which scheme should I use?
    PENALTY_CHECK = "penalty_check"       # Will I get a penalty?


class DeadlineType(StrEnum):
    """Types of tax deadlines."""
    FILING = "filing"                     # Return submission deadline
    PAYMENT = "payment"                   # Tax payment deadline
    REGISTRATION = "registration"         # Registration deadline
    NOTIFICATION = "notification"         # Notification deadline
    APPEAL = "appeal"                     # Appeal deadline
    CLAIM = "claim"                       # Claim deadline (e.g., for refunds)
    ELECTION = "election"                 # Election deadline


class DeadlineFrequency(StrEnum):
    """How often a deadline recurs."""
    ANNUAL = "annual"                     # Once per tax year
    QUARTERLY = "quarterly"               # Four times per year
    MONTHLY = "monthly"                   # Every month
    ONE_TIME = "one_time"                 # Single occurrence
    EVENT_BASED = "event_based"           # Triggered by an event


class ContactType(StrEnum):
    """Types of contact methods."""
    PHONE = "phone"
    PHONE_INTERNATIONAL = "phone_international"
    TEXTPHONE = "textphone"
    EMAIL = "email"
    POST = "post"
    ONLINE_FORM = "online_form"
    WEBCHAT = "webchat"


class ExampleCategory(StrEnum):
    """Categories of worked examples."""
    INCOME_TAX = "income_tax"
    CORPORATION_TAX = "corporation_tax"
    VAT = "vat"
    NATIONAL_INSURANCE = "national_insurance"
    CAPITAL_GAINS = "capital_gains"
    PAYE = "paye"
    SELF_ASSESSMENT = "self_assessment"
    PENALTY = "penalty"
    RELIEF = "relief"


class ConditionLogic(StrEnum):
    """Logical operators for condition lists."""
    AND = "AND"           # All conditions must be met
    OR = "OR"             # Any condition must be met
    AND_NOT = "AND_NOT"   # All conditions except
    SEQUENTIAL = "SEQUENTIAL"  # Conditions checked in order


# =============================================================================
# STRUCTURED TABLE MODEL
# =============================================================================

class StructuredTable(Base):
    """
    Stores tables from tax documents in structured format.
    
    Enables precise data extraction and validation.
    Example: Income tax bands, VAT rates, penalty schedules.
    """
    __tablename__ = "structured_tables"
    
    # === PRIMARY KEY ===
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # === LINKS TO SOURCE ===
    chunk_id = Column(String, ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String, ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # === TABLE IDENTIFICATION ===
    table_type = Column(SQLEnum(TableType), nullable=False, index=True)
    table_name = Column(String(200), nullable=False)  # "Income Tax Rates 2024-25"
    table_description = Column(Text, nullable=True)
    
    # === STRUCTURED DATA ===
    headers = Column(JSONB, nullable=False)
    # ["Band", "Taxable Income From", "Taxable Income To", "Rate"]
    
    rows = Column(JSONB, nullable=False)
    # [{"band": "Basic", "income_from": 12571, "income_to": 50270, "rate": 20}, ...]
    
    column_types = Column(JSONB, nullable=True)
    # {"band": "text", "income_from": "currency_gbp", "rate": "percentage"}
    
    column_descriptions = Column(JSONB, nullable=True)
    # {"band": "Tax band name", "rate": "Tax rate as percentage"}
    
    # === TEMPORAL VALIDITY ===
    tax_year = Column(String(20), nullable=True, index=True)  # "2024-25"
    effective_from = Column(DateTime, nullable=True)
    effective_until = Column(DateTime, nullable=True)
    
    # === QUERY HELPERS ===
    lookup_keys = Column(JSONB, nullable=True)
    # Which columns can be used as lookup keys: ["income_from", "income_to"]
    
    value_columns = Column(JSONB, nullable=True)
    # Which columns contain the answer values: ["rate"]
    
    # === SOURCE ATTRIBUTION ===
    source_url = Column(String, nullable=False)
    citable_reference = Column(String(500), nullable=True)
    
    # === TIMESTAMPS ===
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # === RELATIONSHIPS ===
    chunk = relationship("DocumentChunk", back_populates="tables")
    document = relationship("SourceDocument",back_populates="tables")
    
    def __repr__(self):
        return f"<StructuredTable(id={self.id[:8]}, type={self.table_type}, name={self.table_name})>"
    
    def lookup_value(self, lookup_column: str, lookup_value, return_column: str):
        """
        Simple lookup: find row where lookup_column matches lookup_value,
        return value from return_column.
        """
        for row in self.rows:
            if row.get(lookup_column) == lookup_value:
                return row.get(return_column)
        return None
    
    def lookup_range(self, value: float, min_column: str, max_column: str, return_column: str):
        """
        Range lookup: find row where min_column <= value <= max_column,
        return value from return_column.
        Useful for tax bands.
        """
        for row in self.rows:
            min_val = row.get(min_column)
            max_val = row.get(max_column)
            
            # Handle None/null for unlimited upper bound
            if min_val is not None and value >= min_val:
                if max_val is None or value <= max_val:
                    return row.get(return_column)
        
        return None


# =============================================================================
# STRUCTURED FORMULA MODEL
# =============================================================================

class StructuredFormula(Base):
    """
    Stores tax formulas in structured, executable format.
    
    Enables precise calculations and validation.
    Example: Corporation tax marginal relief calculation.
    """
    __tablename__ = "structured_formulas"
    
    # === PRIMARY KEY ===
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # === LINKS TO SOURCE ===
    chunk_id = Column(String, ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String, ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # === FORMULA IDENTIFICATION ===
    formula_type = Column(SQLEnum(FormulaType), nullable=False, index=True)
    formula_name = Column(String(200), nullable=False)  # "Corporation Tax Marginal Relief"
    formula_description = Column(Text, nullable=True)
    
    # === HUMAN-READABLE VERSION ===
    formula_text = Column(Text, nullable=False)
    # "Tax = Profits × Rate" or "Marginal Relief = (Upper - Profits) × Fraction"
    
    # === VARIABLES ===
    variables = Column(JSONB, nullable=False)
    # {
    #   "taxable_profits": {"type": "currency_gbp", "description": "Taxable profits"},
    #   "upper_limit": {"type": "currency_gbp", "value": 250000, "description": "Upper threshold"}
    # }
    
    # === FORMULA LOGIC ===
    formula_logic = Column(JSONB, nullable=False)
    # {
    #   "type": "conditional",
    #   "conditions": [
    #     {"if": "profits <= 50000", "then": {"calculation": "profits * 0.19"}},
    #     {"if": "profits >= 250000", "then": {"calculation": "profits * 0.25"}},
    #     {"if": "profits > 50000 AND profits < 250000", "then": {...}}
    #   ]
    # }
    
    # === LINKED TABLES ===
    tables_used = Column(JSONB, nullable=True)
    # ["income_tax_bands_2024", "personal_allowance_2024"]
    
    # === TEMPORAL VALIDITY ===
    tax_year = Column(String(20), nullable=True, index=True)
    effective_from = Column(DateTime, nullable=True)
    effective_until = Column(DateTime, nullable=True)
    
    # === SOURCE ATTRIBUTION ===
    source_url = Column(String, nullable=False)
    citable_reference = Column(String(500), nullable=True)
    
    # === TIMESTAMPS ===
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # === RELATIONSHIPS ===
    chunk = relationship("DocumentChunk", back_populates="formulas")
    document = relationship("SourceDocument",back_populates="formulas")
    
    def __repr__(self):
        return f"<StructuredFormula(id={self.id[:8]}, type={self.formula_type}, name={self.formula_name})>"


# =============================================================================
# STRUCTURED DECISION TREE MODEL
# =============================================================================

class StructuredDecisionTree(Base):
    """
    Stores decision trees/flowcharts for eligibility and requirements.
    
    Enables structured "Do I need to...?" type queries.
    Example: VAT registration requirement flowchart.
    """
    __tablename__ = "structured_decision_trees"
    
    # === PRIMARY KEY ===
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # === LINKS TO SOURCE ===
    chunk_id = Column(String, ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String, ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # === TREE IDENTIFICATION ===
    tree_category = Column(SQLEnum(DecisionCategory), nullable=False, index=True)
    tree_name = Column(String(200), nullable=False)  # "VAT Registration Requirement"
    tree_description = Column(Text, nullable=True)
    
    # Relevant tax types
    tax_types = Column(JSONB, nullable=True)  # ["VAT", "PAYE"]
    
    # === TREE STRUCTURE ===
    entry_node_id = Column(String(50), nullable=False)  # Starting point
    
    nodes = Column(JSONB, nullable=False)
    # [
    #   {
    #     "id": "node_1",
    #     "type": "question",
    #     "text": "Is your taxable turnover over £90,000?",
    #     "variable": "turnover_12m",
    #     "condition": {"operator": ">", "value": 90000},
    #     "yes_next": "node_2",
    #     "no_next": "node_3"
    #   },
    #   {
    #     "id": "node_2",
    #     "type": "outcome",
    #     "result": "must_register",
    #     "text": "You MUST register for VAT within 30 days",
    #     "severity": "mandatory",
    #     "action_required": true,
    #     "deadline_reference": "vat_registration_deadline"
    #   }
    # ]
    
    # === OUTCOMES SUMMARY ===
    possible_outcomes = Column(JSONB, nullable=True)
    # ["must_register", "must_register_immediate", "optional", "exempt"]
    
    # === TEMPORAL VALIDITY ===
    tax_year = Column(String(20), nullable=True, index=True)
    effective_from = Column(DateTime, nullable=True)
    effective_until = Column(DateTime, nullable=True)
    
    # === SOURCE ATTRIBUTION ===
    source_url = Column(String, nullable=False)
    citable_reference = Column(String(500), nullable=True)
    
    # === TIMESTAMPS ===
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # === RELATIONSHIPS ===
    chunk = relationship("DocumentChunk", back_populates="decisiontrees")
    document = relationship("SourceDocument",back_populates="decisiontrees")
    
    def __repr__(self):
        return f"<StructuredDecisionTree(id={self.id[:8]}, category={self.tree_category}, name={self.tree_name})>"
    
    def get_node(self, node_id: str) -> dict:
        """Get a specific node by ID."""
        for node in self.nodes:
            if node.get("id") == node_id:
                return node
        return None
    
    def get_entry_node(self) -> dict:
        """Get the entry/starting node."""
        return self.get_node(self.entry_node_id)


# =============================================================================
# STRUCTURED DEADLINE MODEL
# =============================================================================

class StructuredDeadline(Base):
    """
    Stores tax deadlines with calculation logic.
    
    Enables precise deadline calculations and reminders.
    Example: Self Assessment filing deadline (31 January).
    """
    __tablename__ = "structured_deadlines"
    
    # === PRIMARY KEY ===
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # === LINKS TO SOURCE ===
    chunk_id = Column(String, ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String, ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # === DEADLINE IDENTIFICATION ===
    deadline_type = Column(SQLEnum(DeadlineType), nullable=False, index=True)
    deadline_name = Column(String(200), nullable=False)  # "Self Assessment Online Filing"
    deadline_description = Column(Text, nullable=True)
    
    # Relevant tax category
    tax_category = Column(String(50), nullable=False, index=True)  # "self_assessment", "vat", "paye"
    
    # === DEADLINE RULE ===
    frequency = Column(SQLEnum(DeadlineFrequency), nullable=False)
    
    deadline_rule = Column(JSONB, nullable=False)
    # {
    #   "type": "fixed_annual",
    #   "month": 1,
    #   "day": 31,
    #   "relative_to": "tax_year_end",
    #   "description": "31 January following the end of the tax year"
    # }
    # OR
    # {
    #   "type": "relative",
    #   "days_after": 30,
    #   "relative_to": "event",
    #   "event": "exceeding_vat_threshold",
    #   "description": "30 days after end of month when threshold exceeded"
    # }
    
    # === EXAMPLES ===
    examples = Column(JSONB, nullable=True)
    # [
    #   {"tax_year": "2023-24", "deadline_date": "2025-01-31"},
    #   {"tax_year": "2024-25", "deadline_date": "2026-01-31"}
    # ]
    
    # === PENALTY LINK ===
    penalty_reference_id = Column(String, nullable=True)
    # Links to penalty table or formula for missing this deadline
    
    # === REMINDERS ===
    suggested_reminder_days = Column(JSONB, nullable=True)
    # [30, 14, 7, 1] - days before deadline to remind
    
    # === TEMPORAL VALIDITY ===
    tax_year = Column(String(20), nullable=True, index=True)
    effective_from = Column(DateTime, nullable=True)
    effective_until = Column(DateTime, nullable=True)
    
    # === SOURCE ATTRIBUTION ===
    source_url = Column(String, nullable=False)
    citable_reference = Column(String(500), nullable=True)
    
    # === TIMESTAMPS ===
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # === RELATIONSHIPS ===
    chunk = relationship("DocumentChunk", back_populates="deadlines")
    document = relationship("SourceDocument",back_populates="deadlines")
    
    def __repr__(self):
        return f"<StructuredDeadline(id={self.id[:8]}, type={self.deadline_type}, name={self.deadline_name})>"


# =============================================================================
# STRUCTURED EXAMPLE MODEL
# =============================================================================

class StructuredExample(Base):
    """
    Stores worked examples with linked formulas and rules.
    
    Enables step-by-step calculation explanations.
    Example: "Sarah earns £55,000 - calculate her income tax"
    """
    __tablename__ = "structured_examples"
    
    # === PRIMARY KEY ===
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # === LINKS TO SOURCE ===
    chunk_id = Column(String, ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String, ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # === EXAMPLE IDENTIFICATION ===
    example_category = Column(SQLEnum(ExampleCategory), nullable=False, index=True)
    example_name = Column(String(200), nullable=False)  # "Income Tax Calculation - Basic Rate Taxpayer"
    example_description = Column(Text, nullable=True)
    
    # === SCENARIO ===
    scenario = Column(JSONB, nullable=False)
    # {
    #   "person": "Sarah",
    #   "income": 55000,
    #   "tax_year": "2024-25",
    #   "employment_status": "employed",
    #   "other_income": 0
    # }
    
    # === STEP-BY-STEP CALCULATION ===
    steps = Column(JSONB, nullable=False)
    # [
    #   {
    #     "step": 1,
    #     "title": "Deduct Personal Allowance",
    #     "description": "Subtract the tax-free personal allowance",
    #     "calculation": "55000 - 12570",
    #     "result": 42430,
    #     "result_label": "Taxable income"
    #   },
    #   {
    #     "step": 2,
    #     "title": "Calculate Basic Rate Tax",
    #     "description": "First £37,700 of taxable income at 20%",
    #     "calculation": "37700 * 0.20",
    #     "result": 7540,
    #     "result_label": "Basic rate tax"
    #   }
    # ]
    
    # === FINAL RESULT ===
    final_result = Column(JSONB, nullable=False)
    # {
    #   "value": 9432,
    #   "label": "Total income tax",
    #   "formatted": "£9,432"
    # }
    
    # === LINKS TO FORMULAS/TABLES USED ===
    formulas_used = Column(JSONB, nullable=True)
    # ["income_tax_calculation"]
    
    tables_used = Column(JSONB, nullable=True)
    # ["income_tax_bands_2024", "personal_allowance_2024"]
    
    # === TEMPORAL VALIDITY ===
    tax_year = Column(String(20), nullable=True, index=True)
    
    # === SOURCE ATTRIBUTION ===
    source_url = Column(String, nullable=False)
    citable_reference = Column(String(500), nullable=True)
    
    # === TIMESTAMPS ===
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # === RELATIONSHIPS ===
    chunk = relationship("DocumentChunk", back_populates="examples")
    document = relationship("SourceDocument",back_populates="examples")
    
    def __repr__(self):
        return f"<StructuredExample(id={self.id[:8]}, category={self.example_category}, name={self.example_name})>"


# =============================================================================
# STRUCTURED CONTACT MODEL
# =============================================================================

class StructuredContact(Base):
    """
    Stores HMRC and other official contact information.
    
    Enables accurate service navigation.
    Example: Self Assessment helpline phone number and hours.
    """
    __tablename__ = "structured_contacts"
    
    # === PRIMARY KEY ===
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # === LINKS TO SOURCE ===
    chunk_id = Column(String, ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String, ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # === CONTACT IDENTIFICATION ===
    service_name = Column(String(200), nullable=False)  # "Self Assessment Helpline"
    department = Column(String(100), nullable=True)     # "HMRC"
    service_description = Column(Text, nullable=True)
    
    # Relevant tax categories
    tax_categories = Column(JSONB, nullable=True)  # ["self_assessment", "income_tax"]
    
    # === CONTACT METHODS ===
    contact_methods = Column(JSONB, nullable=False)
    # [
    #   {
    #     "type": "phone",
    #     "value": "0300 200 3310",
    #     "hours": "Monday to Friday, 8am to 6pm",
    #     "notes": "Closed on bank holidays"
    #   },
    #   {
    #     "type": "phone_international",
    #     "value": "+44 161 931 9070",
    #     "hours": "Monday to Friday, 8am to 6pm UK time"
    #   },
    #   {
    #     "type": "textphone",
    #     "value": "0300 200 3319"
    #   }
    # ]
    
    # === ONLINE SERVICES ===
    online_services = Column(JSONB, nullable=True)
    # [
    #   {
    #     "name": "Personal Tax Account",
    #     "url": "https://www.gov.uk/personal-tax-account",
    #     "description": "View and manage your tax online"
    #   }
    # ]
    
    # === POSTAL ADDRESS ===
    postal_address = Column(JSONB, nullable=True)
    # {
    #   "lines": ["Self Assessment", "HM Revenue and Customs", "BX9 1AS"],
    #   "country": "United Kingdom"
    # }
    
    # === VERIFICATION ===
    last_verified = Column(DateTime, nullable=True)
    
    # === SOURCE ATTRIBUTION ===
    source_url = Column(String, nullable=False)
    citable_reference = Column(String(500), nullable=True)
    
    # === TIMESTAMPS ===
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # === RELATIONSHIPS ===
    chunk = relationship("DocumentChunk", back_populates="contacts")
    document = relationship("SourceDocument",back_populates="contacts")
    
    def __repr__(self):
        return f"<StructuredContact(id={self.id[:8]}, service={self.service_name})>"
    
    def get_phone(self) -> str:
        """Get primary phone number."""
        for method in self.contact_methods:
            if method.get("type") == "phone":
                return method.get("value")
        return None


# =============================================================================
# STRUCTURED CONDITION LIST MODEL
# =============================================================================

class StructuredConditionList(Base):
    """
    Stores legal condition lists with logical relationships.
    
    Enables structured evaluation of legal requirements.
    Example: VAT registration conditions (a), (b), (c).
    """
    __tablename__ = "structured_condition_lists"
    
    # === PRIMARY KEY ===
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # === LINKS TO SOURCE ===
    chunk_id = Column(String, ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String, ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # === CONDITION LIST IDENTIFICATION ===
    condition_name = Column(String(200), nullable=False)  # "VAT Registration Requirements"
    condition_type = Column(String(50), nullable=False, index=True)  # "requirement", "eligibility", "exemption"
    condition_description = Column(Text, nullable=True)
    
    # Relevant tax types
    tax_types = Column(JSONB, nullable=True)  # ["VAT"]
    
    # === LOGICAL OPERATOR ===
    logical_operator = Column(SQLEnum(ConditionLogic), nullable=False)
    # AND = all conditions must be met
    # OR = any condition must be met
    
    # === CONDITIONS ===
    conditions = Column(JSONB, nullable=False)
    # [
    #   {
    #     "id": "a",
    #     "text": "your taxable turnover exceeds £90,000 in any 12-month period",
    #     "variable": "turnover_12m",
    #     "operator": ">",
    #     "threshold": 90000,
    #     "threshold_type": "currency_gbp"
    #   },
    #   {
    #     "id": "b",
    #     "text": "you expect your taxable turnover to exceed £90,000 in the next 30 days alone",
    #     "variable": "expected_turnover_30d",
    #     "operator": ">",
    #     "threshold": 90000,
    #     "threshold_type": "currency_gbp"
    #   },
    #   {
    #     "id": "c",
    #     "text": "you take over a VAT-registered business as a going concern",
    #     "variable": "takeover_vat_business",
    #     "operator": "==",
    #     "threshold": true,
    #     "threshold_type": "boolean"
    #   }
    # ]
    
    # === OUTCOMES ===
    outcome_if_met = Column(Text, nullable=False)
    # "You must register for VAT"
    
    outcome_if_not_met = Column(Text, nullable=True)
    # "You may register voluntarily"
    
    # === RELATED CONTENT ===
    related_decision_tree_id = Column(String, nullable=True)
    # Link to a decision tree that uses these conditions
    
    # === TEMPORAL VALIDITY ===
    tax_year = Column(String(20), nullable=True, index=True)
    effective_from = Column(DateTime, nullable=True)
    effective_until = Column(DateTime, nullable=True)
    
    # === SOURCE ATTRIBUTION ===
    source_url = Column(String, nullable=False)
    citable_reference = Column(String(500), nullable=True)
    
    # === TIMESTAMPS ===
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # === RELATIONSHIPS ===
    chunk = relationship("DocumentChunk",back_populates="condition_lists")
    document = relationship("SourceDocument",back_populates="condition_lists")
    
    def __repr__(self):
        return f"<StructuredConditionList(id={self.id[:8]}, name={self.condition_name}, logic={self.logical_operator})>"
