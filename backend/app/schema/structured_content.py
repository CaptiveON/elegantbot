"""
Structured Content Schemas

Pydantic schemas for structured content validation and serialization:
- Tables, Formulas, Decision Trees, Deadlines, Examples, Contacts, Condition Lists
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum


# =============================================================================
# ENUMS (mirrored from models)
# =============================================================================

class TableType(str, Enum):
    TAX_RATES = "tax_rates"
    VAT_RATES = "vat_rates"
    THRESHOLDS = "thresholds"
    PENALTIES = "penalties"
    DEADLINES = "deadlines"
    ALLOWANCES = "allowances"
    NI_RATES = "ni_rates"
    NI_THRESHOLDS = "ni_thresholds"
    MILEAGE_RATES = "mileage_rates"
    BENEFIT_RATES = "benefit_rates"
    COMPARISON = "comparison"
    OTHER = "other"


class FormulaType(str, Enum):
    TAX_CALCULATION = "tax_calculation"
    MARGINAL_RELIEF = "marginal_relief"
    PENALTY_CALCULATION = "penalty_calculation"
    ALLOWANCE_CALCULATION = "allowance_calculation"
    THRESHOLD_TEST = "threshold_test"
    RELIEF_CALCULATION = "relief_calculation"
    NI_CALCULATION = "ni_calculation"
    VAT_CALCULATION = "vat_calculation"
    INTEREST_CALCULATION = "interest_calculation"
    PRORATION = "proration"


class DecisionCategory(str, Enum):
    REGISTRATION = "registration"
    ELIGIBILITY = "eligibility"
    FILING = "filing"
    PAYMENT = "payment"
    EXEMPTION = "exemption"
    SCHEME_CHOICE = "scheme_choice"
    PENALTY_CHECK = "penalty_check"


class DeadlineType(str, Enum):
    FILING = "filing"
    PAYMENT = "payment"
    REGISTRATION = "registration"
    NOTIFICATION = "notification"
    APPEAL = "appeal"
    CLAIM = "claim"
    ELECTION = "election"


class DeadlineFrequency(str, Enum):
    ANNUAL = "annual"
    QUARTERLY = "quarterly"
    MONTHLY = "monthly"
    ONE_TIME = "one_time"
    EVENT_BASED = "event_based"


class ContactType(str, Enum):
    PHONE = "phone"
    PHONE_INTERNATIONAL = "phone_international"
    TEXTPHONE = "textphone"
    EMAIL = "email"
    POST = "post"
    ONLINE_FORM = "online_form"
    WEBCHAT = "webchat"


class ExampleCategory(str, Enum):
    INCOME_TAX = "income_tax"
    CORPORATION_TAX = "corporation_tax"
    VAT = "vat"
    NATIONAL_INSURANCE = "national_insurance"
    CAPITAL_GAINS = "capital_gains"
    PAYE = "paye"
    SELF_ASSESSMENT = "self_assessment"
    PENALTY = "penalty"
    RELIEF = "relief"


class ConditionLogic(str, Enum):
    AND = "AND"
    OR = "OR"
    AND_NOT = "AND_NOT"
    SEQUENTIAL = "SEQUENTIAL"


# =============================================================================
# SHARED SUB-SCHEMAS
# =============================================================================

class ColumnDefinition(BaseModel):
    """Definition of a table column."""
    name: str
    type: str  # "text", "currency_gbp", "percentage", "integer", "date"
    description: Optional[str] = None


class TableRow(BaseModel):
    """A single row in a structured table."""
    data: Dict[str, Any]


class FormulaVariable(BaseModel):
    """A variable in a formula."""
    name: str
    type: str  # "currency_gbp", "percentage", "integer", "boolean"
    description: str
    default_value: Optional[Any] = None


class DecisionNode(BaseModel):
    """A node in a decision tree."""
    id: str
    type: str  # "question", "outcome", "calculation"
    text: str
    variable: Optional[str] = None
    condition: Optional[Dict[str, Any]] = None
    yes_next: Optional[str] = None
    no_next: Optional[str] = None
    result: Optional[str] = None
    severity: Optional[str] = None
    action_required: Optional[bool] = None


class ContactMethod(BaseModel):
    """A single contact method."""
    type: ContactType
    value: str
    hours: Optional[str] = None
    notes: Optional[str] = None


class ExampleStep(BaseModel):
    """A step in a worked example."""
    step: int
    title: str
    description: str
    calculation: str
    result: Union[int, float, str]
    result_label: str


class ConditionItem(BaseModel):
    """A single condition in a condition list."""
    id: str  # "a", "b", "c"
    text: str
    variable: Optional[str] = None
    operator: Optional[str] = None  # ">", "<", "==", ">=", "<="
    threshold: Optional[Any] = None
    threshold_type: Optional[str] = None


# =============================================================================
# STRUCTURED TABLE SCHEMAS
# =============================================================================

class StructuredTableCreate(BaseModel):
    """Schema for creating a structured table."""
    chunk_id: str
    document_id: str
    
    table_type: TableType
    table_name: str = Field(..., max_length=200)
    table_description: Optional[str] = None
    
    headers: List[str]
    rows: List[Dict[str, Any]]
    column_types: Optional[Dict[str, str]] = None
    column_descriptions: Optional[Dict[str, str]] = None
    
    tax_year: Optional[str] = None
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None
    
    lookup_keys: Optional[List[str]] = None
    value_columns: Optional[List[str]] = None
    
    source_url: str
    citable_reference: Optional[str] = None


class StructuredTableUpdate(BaseModel):
    """Schema for updating a structured table."""
    table_name: Optional[str] = None
    table_description: Optional[str] = None
    
    headers: Optional[List[str]] = None
    rows: Optional[List[Dict[str, Any]]] = None
    column_types: Optional[Dict[str, str]] = None
    
    tax_year: Optional[str] = None
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None
    
    citable_reference: Optional[str] = None


class StructuredTableResponse(BaseModel):
    """Schema for returning a structured table."""
    id: str
    chunk_id: str
    document_id: str
    
    table_type: TableType
    table_name: str
    table_description: Optional[str] = None
    
    headers: List[str]
    rows: List[Dict[str, Any]]
    column_types: Optional[Dict[str, str]] = None
    column_descriptions: Optional[Dict[str, str]] = None
    
    tax_year: Optional[str] = None
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None
    
    lookup_keys: Optional[List[str]] = None
    value_columns: Optional[List[str]] = None
    
    source_url: str
    citable_reference: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class TableLookupRequest(BaseModel):
    """Request to look up a value in a table."""
    table_id: str
    lookup_column: str
    lookup_value: Any
    return_column: str


class TableRangeLookupRequest(BaseModel):
    """Request to look up a value using range matching."""
    table_id: str
    value: float
    min_column: str
    max_column: str
    return_column: str


class TableLookupResponse(BaseModel):
    """Response from a table lookup."""
    table_id: str
    table_name: str
    lookup_value: Any
    result_column: str
    result_value: Any
    row_data: Dict[str, Any]
    citable_reference: Optional[str] = None


# =============================================================================
# STRUCTURED FORMULA SCHEMAS
# =============================================================================

class StructuredFormulaCreate(BaseModel):
    """Schema for creating a structured formula."""
    chunk_id: str
    document_id: str
    
    formula_type: FormulaType
    formula_name: str = Field(..., max_length=200)
    formula_description: Optional[str] = None
    
    formula_text: str
    variables: Dict[str, Dict[str, Any]]
    formula_logic: Dict[str, Any]
    
    tables_used: Optional[List[str]] = None
    
    tax_year: Optional[str] = None
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None
    
    source_url: str
    citable_reference: Optional[str] = None


class StructuredFormulaUpdate(BaseModel):
    """Schema for updating a structured formula."""
    formula_name: Optional[str] = None
    formula_description: Optional[str] = None
    formula_text: Optional[str] = None
    variables: Optional[Dict[str, Dict[str, Any]]] = None
    formula_logic: Optional[Dict[str, Any]] = None
    tables_used: Optional[List[str]] = None
    tax_year: Optional[str] = None
    citable_reference: Optional[str] = None


class StructuredFormulaResponse(BaseModel):
    """Schema for returning a structured formula."""
    id: str
    chunk_id: str
    document_id: str
    
    formula_type: FormulaType
    formula_name: str
    formula_description: Optional[str] = None
    
    formula_text: str
    variables: Dict[str, Dict[str, Any]]
    formula_logic: Dict[str, Any]
    
    tables_used: Optional[List[str]] = None
    
    tax_year: Optional[str] = None
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None
    
    source_url: str
    citable_reference: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


# =============================================================================
# STRUCTURED DECISION TREE SCHEMAS
# =============================================================================

class StructuredDecisionTreeCreate(BaseModel):
    """Schema for creating a structured decision tree."""
    chunk_id: str
    document_id: str
    
    tree_category: DecisionCategory
    tree_name: str = Field(..., max_length=200)
    tree_description: Optional[str] = None
    tax_types: Optional[List[str]] = None
    
    entry_node_id: str
    nodes: List[Dict[str, Any]]
    possible_outcomes: Optional[List[str]] = None
    
    tax_year: Optional[str] = None
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None
    
    source_url: str
    citable_reference: Optional[str] = None


class StructuredDecisionTreeUpdate(BaseModel):
    """Schema for updating a structured decision tree."""
    tree_name: Optional[str] = None
    tree_description: Optional[str] = None
    nodes: Optional[List[Dict[str, Any]]] = None
    possible_outcomes: Optional[List[str]] = None
    tax_year: Optional[str] = None
    citable_reference: Optional[str] = None


class StructuredDecisionTreeResponse(BaseModel):
    """Schema for returning a structured decision tree."""
    id: str
    chunk_id: str
    document_id: str
    
    tree_category: DecisionCategory
    tree_name: str
    tree_description: Optional[str] = None
    tax_types: Optional[List[str]] = None
    
    entry_node_id: str
    nodes: List[Dict[str, Any]]
    possible_outcomes: Optional[List[str]] = None
    
    tax_year: Optional[str] = None
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None
    
    source_url: str
    citable_reference: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class DecisionTreeTraversalRequest(BaseModel):
    """Request to traverse a decision tree."""
    tree_id: str
    answers: Dict[str, Any]  # {variable_name: value}


class DecisionTreeTraversalResponse(BaseModel):
    """Response from decision tree traversal."""
    tree_id: str
    tree_name: str
    path_taken: List[str]  # Node IDs visited
    final_outcome: str
    outcome_text: str
    action_required: bool
    severity: Optional[str] = None
    citable_reference: Optional[str] = None


# =============================================================================
# STRUCTURED DEADLINE SCHEMAS
# =============================================================================

class StructuredDeadlineCreate(BaseModel):
    """Schema for creating a structured deadline."""
    chunk_id: str
    document_id: str
    
    deadline_type: DeadlineType
    deadline_name: str = Field(..., max_length=200)
    deadline_description: Optional[str] = None
    tax_category: str
    
    frequency: DeadlineFrequency
    deadline_rule: Dict[str, Any]
    examples: Optional[List[Dict[str, Any]]] = None
    
    penalty_reference_id: Optional[str] = None
    suggested_reminder_days: Optional[List[int]] = None
    
    tax_year: Optional[str] = None
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None
    
    source_url: str
    citable_reference: Optional[str] = None


class StructuredDeadlineUpdate(BaseModel):
    """Schema for updating a structured deadline."""
    deadline_name: Optional[str] = None
    deadline_description: Optional[str] = None
    deadline_rule: Optional[Dict[str, Any]] = None
    examples: Optional[List[Dict[str, Any]]] = None
    penalty_reference_id: Optional[str] = None
    suggested_reminder_days: Optional[List[int]] = None
    tax_year: Optional[str] = None
    citable_reference: Optional[str] = None


class StructuredDeadlineResponse(BaseModel):
    """Schema for returning a structured deadline."""
    id: str
    chunk_id: str
    document_id: str
    
    deadline_type: DeadlineType
    deadline_name: str
    deadline_description: Optional[str] = None
    tax_category: str
    
    frequency: DeadlineFrequency
    deadline_rule: Dict[str, Any]
    examples: Optional[List[Dict[str, Any]]] = None
    
    penalty_reference_id: Optional[str] = None
    suggested_reminder_days: Optional[List[int]] = None
    
    tax_year: Optional[str] = None
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None
    
    source_url: str
    citable_reference: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class DeadlineCalculationRequest(BaseModel):
    """Request to calculate a specific deadline date."""
    deadline_id: str
    tax_year: Optional[str] = None
    event_date: Optional[datetime] = None


class DeadlineCalculationResponse(BaseModel):
    """Response with calculated deadline date."""
    deadline_id: str
    deadline_name: str
    calculated_date: datetime
    days_remaining: Optional[int] = None
    is_overdue: bool = False
    penalty_warning: Optional[str] = None
    citable_reference: Optional[str] = None


# =============================================================================
# STRUCTURED EXAMPLE SCHEMAS
# =============================================================================

class StructuredExampleCreate(BaseModel):
    """Schema for creating a structured example."""
    chunk_id: str
    document_id: str
    
    example_category: ExampleCategory
    example_name: str = Field(..., max_length=200)
    example_description: Optional[str] = None
    
    scenario: Dict[str, Any]
    steps: List[Dict[str, Any]]
    final_result: Dict[str, Any]
    
    formulas_used: Optional[List[str]] = None
    tables_used: Optional[List[str]] = None
    
    tax_year: Optional[str] = None
    
    source_url: str
    citable_reference: Optional[str] = None


class StructuredExampleUpdate(BaseModel):
    """Schema for updating a structured example."""
    example_name: Optional[str] = None
    example_description: Optional[str] = None
    scenario: Optional[Dict[str, Any]] = None
    steps: Optional[List[Dict[str, Any]]] = None
    final_result: Optional[Dict[str, Any]] = None
    formulas_used: Optional[List[str]] = None
    tables_used: Optional[List[str]] = None
    tax_year: Optional[str] = None
    citable_reference: Optional[str] = None


class StructuredExampleResponse(BaseModel):
    """Schema for returning a structured example."""
    id: str
    chunk_id: str
    document_id: str
    
    example_category: ExampleCategory
    example_name: str
    example_description: Optional[str] = None
    
    scenario: Dict[str, Any]
    steps: List[Dict[str, Any]]
    final_result: Dict[str, Any]
    
    formulas_used: Optional[List[str]] = None
    tables_used: Optional[List[str]] = None
    
    tax_year: Optional[str] = None
    
    source_url: str
    citable_reference: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


# =============================================================================
# STRUCTURED CONTACT SCHEMAS
# =============================================================================

class StructuredContactCreate(BaseModel):
    """Schema for creating a structured contact."""
    chunk_id: str
    document_id: str
    
    service_name: str = Field(..., max_length=200)
    department: Optional[str] = None
    service_description: Optional[str] = None
    tax_categories: Optional[List[str]] = None
    
    contact_methods: List[Dict[str, Any]]
    online_services: Optional[List[Dict[str, Any]]] = None
    postal_address: Optional[Dict[str, Any]] = None
    
    last_verified: Optional[datetime] = None
    
    source_url: str
    citable_reference: Optional[str] = None


class StructuredContactUpdate(BaseModel):
    """Schema for updating a structured contact."""
    service_name: Optional[str] = None
    department: Optional[str] = None
    service_description: Optional[str] = None
    contact_methods: Optional[List[Dict[str, Any]]] = None
    online_services: Optional[List[Dict[str, Any]]] = None
    postal_address: Optional[Dict[str, Any]] = None
    last_verified: Optional[datetime] = None
    citable_reference: Optional[str] = None


class StructuredContactResponse(BaseModel):
    """Schema for returning a structured contact."""
    id: str
    chunk_id: str
    document_id: str
    
    service_name: str
    department: Optional[str] = None
    service_description: Optional[str] = None
    tax_categories: Optional[List[str]] = None
    
    contact_methods: List[Dict[str, Any]]
    online_services: Optional[List[Dict[str, Any]]] = None
    postal_address: Optional[Dict[str, Any]] = None
    
    last_verified: Optional[datetime] = None
    
    source_url: str
    citable_reference: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


# =============================================================================
# STRUCTURED CONDITION LIST SCHEMAS
# =============================================================================

class StructuredConditionListCreate(BaseModel):
    """Schema for creating a structured condition list."""
    chunk_id: str
    document_id: str
    
    condition_name: str = Field(..., max_length=200)
    condition_type: str  # "requirement", "eligibility", "exemption"
    condition_description: Optional[str] = None
    tax_types: Optional[List[str]] = None
    
    logical_operator: ConditionLogic
    conditions: List[Dict[str, Any]]
    
    outcome_if_met: str
    outcome_if_not_met: Optional[str] = None
    
    related_decision_tree_id: Optional[str] = None
    
    tax_year: Optional[str] = None
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None
    
    source_url: str
    citable_reference: Optional[str] = None


class StructuredConditionListUpdate(BaseModel):
    """Schema for updating a structured condition list."""
    condition_name: Optional[str] = None
    condition_description: Optional[str] = None
    conditions: Optional[List[Dict[str, Any]]] = None
    outcome_if_met: Optional[str] = None
    outcome_if_not_met: Optional[str] = None
    tax_year: Optional[str] = None
    citable_reference: Optional[str] = None


class StructuredConditionListResponse(BaseModel):
    """Schema for returning a structured condition list."""
    id: str
    chunk_id: str
    document_id: str
    
    condition_name: str
    condition_type: str
    condition_description: Optional[str] = None
    tax_types: Optional[List[str]] = None
    
    logical_operator: ConditionLogic
    conditions: List[Dict[str, Any]]
    
    outcome_if_met: str
    outcome_if_not_met: Optional[str] = None
    
    related_decision_tree_id: Optional[str] = None
    
    tax_year: Optional[str] = None
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None
    
    source_url: str
    citable_reference: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class ConditionEvaluationRequest(BaseModel):
    """Request to evaluate conditions against provided values."""
    condition_list_id: str
    values: Dict[str, Any]  # {variable_name: value}


class ConditionEvaluationResponse(BaseModel):
    """Response from condition evaluation."""
    condition_list_id: str
    condition_name: str
    logical_operator: ConditionLogic
    conditions_met: List[str]  # IDs of conditions that were met
    conditions_not_met: List[str]
    overall_result: bool  # Whether the overall condition is satisfied
    outcome: str  # outcome_if_met or outcome_if_not_met
    citable_reference: Optional[str] = None


# =============================================================================
# AGGREGATE SCHEMAS
# =============================================================================

class StructuredContentSummary(BaseModel):
    """Summary of all structured content linked to a chunk."""
    chunk_id: str
    tables: List[str] = []  # Table IDs
    formulas: List[str] = []
    decision_trees: List[str] = []
    deadlines: List[str] = []
    examples: List[str] = []
    contacts: List[str] = []
    condition_lists: List[str] = []
    
    has_structured_content: bool = False


class StructuredContentStats(BaseModel):
    """Statistics about structured content in the system."""
    total_tables: int = 0
    total_formulas: int = 0
    total_decision_trees: int = 0
    total_deadlines: int = 0
    total_examples: int = 0
    total_contacts: int = 0
    total_condition_lists: int = 0
    
    tables_by_type: Dict[str, int] = {}
    formulas_by_type: Dict[str, int] = {}
    decision_trees_by_category: Dict[str, int] = {}
    deadlines_by_type: Dict[str, int] = {}
    examples_by_category: Dict[str, int] = {}
