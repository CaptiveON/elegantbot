"""
Structured Content CRUD Operations

Database operations for all structured content models:
- Tables, Formulas, Decision Trees, Deadlines, Examples, Contacts, Condition Lists
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.models.structured_content import (
    StructuredTable,
    StructuredFormula,
    StructuredDecisionTree,
    StructuredDeadline,
    StructuredExample,
    StructuredContact,
    StructuredConditionList,
    TableType,
    FormulaType,
    DecisionCategory,
    DeadlineType,
    ExampleCategory,
    ConditionLogic
)

from app.schema.structured_content import (
    StructuredTableCreate,
    StructuredTableUpdate,
    StructuredFormulaCreate,
    StructuredFormulaUpdate,
    StructuredDecisionTreeCreate,
    StructuredDecisionTreeUpdate,
    StructuredDeadlineCreate,
    StructuredDeadlineUpdate,
    StructuredExampleCreate,
    StructuredExampleUpdate,
    StructuredContactCreate,
    StructuredContactUpdate,
    StructuredConditionListCreate,
    StructuredConditionListUpdate,
    StructuredContentStats
)


# =============================================================================
# STRUCTURED TABLE CRUD
# =============================================================================

def create_table(db: Session, table_data: StructuredTableCreate) -> StructuredTable:
    """Create a new structured table."""
    table = StructuredTable(
        chunk_id=table_data.chunk_id,
        document_id=table_data.document_id,
        table_type=table_data.table_type,
        table_name=table_data.table_name,
        table_description=table_data.table_description,
        headers=table_data.headers,
        rows=table_data.rows,
        column_types=table_data.column_types,
        column_descriptions=table_data.column_descriptions,
        tax_year=table_data.tax_year,
        effective_from=table_data.effective_from,
        effective_until=table_data.effective_until,
        lookup_keys=table_data.lookup_keys,
        value_columns=table_data.value_columns,
        source_url=table_data.source_url,
        citable_reference=table_data.citable_reference
    )
    
    db.add(table)
    db.commit()
    db.refresh(table)
    return table


def get_table(db: Session, table_id: str) -> Optional[StructuredTable]:
    """Get a table by ID."""
    return db.query(StructuredTable).filter(StructuredTable.id == table_id).first()


def get_tables_by_chunk(db: Session, chunk_id: str) -> List[StructuredTable]:
    """Get all tables for a chunk."""
    return db.query(StructuredTable).filter(StructuredTable.chunk_id == chunk_id).all()


def get_tables_by_document(db: Session, document_id: str) -> List[StructuredTable]:
    """Get all tables for a document."""
    return db.query(StructuredTable).filter(StructuredTable.document_id == document_id).all()


def get_tables_by_type(
    db: Session,
    table_type: TableType,
    tax_year: Optional[str] = None,
    limit: int = 100
) -> List[StructuredTable]:
    """Get tables by type, optionally filtered by tax year."""
    query = db.query(StructuredTable).filter(StructuredTable.table_type == table_type)
    
    if tax_year:
        query = query.filter(StructuredTable.tax_year == tax_year)
    
    return query.limit(limit).all()


def get_current_table(
    db: Session,
    table_type: TableType,
    table_name_contains: Optional[str] = None
) -> Optional[StructuredTable]:
    """Get the most current table of a given type."""
    query = db.query(StructuredTable).filter(StructuredTable.table_type == table_type)
    
    if table_name_contains:
        query = query.filter(StructuredTable.table_name.ilike(f"%{table_name_contains}%"))
    
    # Order by effective_from descending, then by created_at
    query = query.order_by(
        StructuredTable.effective_from.desc().nullslast(),
        StructuredTable.created_at.desc()
    )
    
    return query.first()


def update_table(
    db: Session,
    table_id: str,
    update_data: StructuredTableUpdate
) -> Optional[StructuredTable]:
    """Update a structured table."""
    table = get_table(db, table_id)
    if not table:
        return None
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(table, field, value)
    
    table.updated_at = datetime.now()
    db.commit()
    db.refresh(table)
    return table


def delete_table(db: Session, table_id: str) -> bool:
    """Delete a structured table."""
    table = get_table(db, table_id)
    if not table:
        return False
    
    db.delete(table)
    db.commit()
    return True


def lookup_table_value(
    db: Session,
    table_id: str,
    lookup_column: str,
    lookup_value: Any,
    return_column: str
) -> Optional[Any]:
    """Look up a value in a table."""
    table = get_table(db, table_id)
    if not table:
        return None
    
    return table.lookup_value(lookup_column, lookup_value, return_column)


def lookup_table_range(
    db: Session,
    table_id: str,
    value: float,
    min_column: str,
    max_column: str,
    return_column: str
) -> Optional[Any]:
    """Look up a value using range matching."""
    table = get_table(db, table_id)
    if not table:
        return None
    
    return table.lookup_range(value, min_column, max_column, return_column)


# =============================================================================
# STRUCTURED FORMULA CRUD
# =============================================================================

def create_formula(db: Session, formula_data: StructuredFormulaCreate) -> StructuredFormula:
    """Create a new structured formula."""
    formula = StructuredFormula(
        chunk_id=formula_data.chunk_id,
        document_id=formula_data.document_id,
        formula_type=formula_data.formula_type,
        formula_name=formula_data.formula_name,
        formula_description=formula_data.formula_description,
        formula_text=formula_data.formula_text,
        variables=formula_data.variables,
        formula_logic=formula_data.formula_logic,
        tables_used=formula_data.tables_used,
        tax_year=formula_data.tax_year,
        effective_from=formula_data.effective_from,
        effective_until=formula_data.effective_until,
        source_url=formula_data.source_url,
        citable_reference=formula_data.citable_reference
    )
    
    db.add(formula)
    db.commit()
    db.refresh(formula)
    return formula


def get_formula(db: Session, formula_id: str) -> Optional[StructuredFormula]:
    """Get a formula by ID."""
    return db.query(StructuredFormula).filter(StructuredFormula.id == formula_id).first()


def get_formulas_by_chunk(db: Session, chunk_id: str) -> List[StructuredFormula]:
    """Get all formulas for a chunk."""
    return db.query(StructuredFormula).filter(StructuredFormula.chunk_id == chunk_id).all()


def get_formulas_by_type(
    db: Session,
    formula_type: FormulaType,
    tax_year: Optional[str] = None,
    limit: int = 100
) -> List[StructuredFormula]:
    """Get formulas by type."""
    query = db.query(StructuredFormula).filter(StructuredFormula.formula_type == formula_type)
    
    if tax_year:
        query = query.filter(StructuredFormula.tax_year == tax_year)
    
    return query.limit(limit).all()


def get_formula_by_name(
    db: Session,
    name_contains: str,
    tax_year: Optional[str] = None
) -> Optional[StructuredFormula]:
    """Find a formula by name."""
    query = db.query(StructuredFormula).filter(
        StructuredFormula.formula_name.ilike(f"%{name_contains}%")
    )
    
    if tax_year:
        query = query.filter(StructuredFormula.tax_year == tax_year)
    
    return query.first()


def update_formula(
    db: Session,
    formula_id: str,
    update_data: StructuredFormulaUpdate
) -> Optional[StructuredFormula]:
    """Update a structured formula."""
    formula = get_formula(db, formula_id)
    if not formula:
        return None
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(formula, field, value)
    
    formula.updated_at = datetime.now()
    db.commit()
    db.refresh(formula)
    return formula


def delete_formula(db: Session, formula_id: str) -> bool:
    """Delete a structured formula."""
    formula = get_formula(db, formula_id)
    if not formula:
        return False
    
    db.delete(formula)
    db.commit()
    return True


# =============================================================================
# STRUCTURED DECISION TREE CRUD
# =============================================================================

def create_decision_tree(db: Session, tree_data: StructuredDecisionTreeCreate) -> StructuredDecisionTree:
    """Create a new decision tree."""
    tree = StructuredDecisionTree(
        chunk_id=tree_data.chunk_id,
        document_id=tree_data.document_id,
        tree_category=tree_data.tree_category,
        tree_name=tree_data.tree_name,
        tree_description=tree_data.tree_description,
        tax_types=tree_data.tax_types,
        entry_node_id=tree_data.entry_node_id,
        nodes=tree_data.nodes,
        possible_outcomes=tree_data.possible_outcomes,
        tax_year=tree_data.tax_year,
        effective_from=tree_data.effective_from,
        effective_until=tree_data.effective_until,
        source_url=tree_data.source_url,
        citable_reference=tree_data.citable_reference
    )
    
    db.add(tree)
    db.commit()
    db.refresh(tree)
    return tree


def get_decision_tree(db: Session, tree_id: str) -> Optional[StructuredDecisionTree]:
    """Get a decision tree by ID."""
    return db.query(StructuredDecisionTree).filter(StructuredDecisionTree.id == tree_id).first()


def get_decision_trees_by_category(
    db: Session,
    category: DecisionCategory,
    tax_type: Optional[str] = None,
    limit: int = 100
) -> List[StructuredDecisionTree]:
    """Get decision trees by category."""
    query = db.query(StructuredDecisionTree).filter(
        StructuredDecisionTree.tree_category == category
    )
    
    if tax_type:
        query = query.filter(StructuredDecisionTree.tax_types.contains([tax_type]))
    
    return query.limit(limit).all()


def get_decision_tree_by_name(
    db: Session,
    name_contains: str
) -> Optional[StructuredDecisionTree]:
    """Find a decision tree by name."""
    return db.query(StructuredDecisionTree).filter(
        StructuredDecisionTree.tree_name.ilike(f"%{name_contains}%")
    ).first()


def update_decision_tree(
    db: Session,
    tree_id: str,
    update_data: StructuredDecisionTreeUpdate
) -> Optional[StructuredDecisionTree]:
    """Update a decision tree."""
    tree = get_decision_tree(db, tree_id)
    if not tree:
        return None
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(tree, field, value)
    
    tree.updated_at = datetime.now()
    db.commit()
    db.refresh(tree)
    return tree


def delete_decision_tree(db: Session, tree_id: str) -> bool:
    """Delete a decision tree."""
    tree = get_decision_tree(db, tree_id)
    if not tree:
        return False
    
    db.delete(tree)
    db.commit()
    return True


# =============================================================================
# STRUCTURED DEADLINE CRUD
# =============================================================================

def create_deadline(db: Session, deadline_data: StructuredDeadlineCreate) -> StructuredDeadline:
    """Create a new structured deadline."""
    deadline = StructuredDeadline(
        chunk_id=deadline_data.chunk_id,
        document_id=deadline_data.document_id,
        deadline_type=deadline_data.deadline_type,
        deadline_name=deadline_data.deadline_name,
        deadline_description=deadline_data.deadline_description,
        tax_category=deadline_data.tax_category,
        frequency=deadline_data.frequency,
        deadline_rule=deadline_data.deadline_rule,
        examples=deadline_data.examples,
        penalty_reference_id=deadline_data.penalty_reference_id,
        suggested_reminder_days=deadline_data.suggested_reminder_days,
        tax_year=deadline_data.tax_year,
        effective_from=deadline_data.effective_from,
        effective_until=deadline_data.effective_until,
        source_url=deadline_data.source_url,
        citable_reference=deadline_data.citable_reference
    )
    
    db.add(deadline)
    db.commit()
    db.refresh(deadline)
    return deadline


def get_deadline(db: Session, deadline_id: str) -> Optional[StructuredDeadline]:
    """Get a deadline by ID."""
    return db.query(StructuredDeadline).filter(StructuredDeadline.id == deadline_id).first()


def get_deadlines_by_category(
    db: Session,
    tax_category: str,
    deadline_type: Optional[DeadlineType] = None,
    limit: int = 100
) -> List[StructuredDeadline]:
    """Get deadlines by tax category."""
    query = db.query(StructuredDeadline).filter(
        StructuredDeadline.tax_category == tax_category
    )
    
    if deadline_type:
        query = query.filter(StructuredDeadline.deadline_type == deadline_type)
    
    return query.limit(limit).all()


def get_deadlines_by_type(
    db: Session,
    deadline_type: DeadlineType,
    limit: int = 100
) -> List[StructuredDeadline]:
    """Get all deadlines of a specific type."""
    return db.query(StructuredDeadline).filter(
        StructuredDeadline.deadline_type == deadline_type
    ).limit(limit).all()


def update_deadline(
    db: Session,
    deadline_id: str,
    update_data: StructuredDeadlineUpdate
) -> Optional[StructuredDeadline]:
    """Update a structured deadline."""
    deadline = get_deadline(db, deadline_id)
    if not deadline:
        return None
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(deadline, field, value)
    
    deadline.updated_at = datetime.now()
    db.commit()
    db.refresh(deadline)
    return deadline


def delete_deadline(db: Session, deadline_id: str) -> bool:
    """Delete a structured deadline."""
    deadline = get_deadline(db, deadline_id)
    if not deadline:
        return False
    
    db.delete(deadline)
    db.commit()
    return True


# =============================================================================
# STRUCTURED EXAMPLE CRUD
# =============================================================================

def create_example(db: Session, example_data: StructuredExampleCreate) -> StructuredExample:
    """Create a new structured example."""
    example = StructuredExample(
        chunk_id=example_data.chunk_id,
        document_id=example_data.document_id,
        example_category=example_data.example_category,
        example_name=example_data.example_name,
        example_description=example_data.example_description,
        scenario=example_data.scenario,
        steps=example_data.steps,
        final_result=example_data.final_result,
        formulas_used=example_data.formulas_used,
        tables_used=example_data.tables_used,
        tax_year=example_data.tax_year,
        source_url=example_data.source_url,
        citable_reference=example_data.citable_reference
    )
    
    db.add(example)
    db.commit()
    db.refresh(example)
    return example


def get_example(db: Session, example_id: str) -> Optional[StructuredExample]:
    """Get an example by ID."""
    return db.query(StructuredExample).filter(StructuredExample.id == example_id).first()


def get_examples_by_category(
    db: Session,
    category: ExampleCategory,
    tax_year: Optional[str] = None,
    limit: int = 100
) -> List[StructuredExample]:
    """Get examples by category."""
    query = db.query(StructuredExample).filter(
        StructuredExample.example_category == category
    )
    
    if tax_year:
        query = query.filter(StructuredExample.tax_year == tax_year)
    
    return query.limit(limit).all()


def update_example(
    db: Session,
    example_id: str,
    update_data: StructuredExampleUpdate
) -> Optional[StructuredExample]:
    """Update a structured example."""
    example = get_example(db, example_id)
    if not example:
        return None
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(example, field, value)
    
    example.updated_at = datetime.now()
    db.commit()
    db.refresh(example)
    return example


def delete_example(db: Session, example_id: str) -> bool:
    """Delete a structured example."""
    example = get_example(db, example_id)
    if not example:
        return False
    
    db.delete(example)
    db.commit()
    return True


# =============================================================================
# STRUCTURED CONTACT CRUD
# =============================================================================

def create_contact(db: Session, contact_data: StructuredContactCreate) -> StructuredContact:
    """Create a new structured contact."""
    contact = StructuredContact(
        chunk_id=contact_data.chunk_id,
        document_id=contact_data.document_id,
        service_name=contact_data.service_name,
        department=contact_data.department,
        service_description=contact_data.service_description,
        tax_categories=contact_data.tax_categories,
        contact_methods=contact_data.contact_methods,
        online_services=contact_data.online_services,
        postal_address=contact_data.postal_address,
        last_verified=contact_data.last_verified,
        source_url=contact_data.source_url,
        citable_reference=contact_data.citable_reference
    )
    
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def get_contact(db: Session, contact_id: str) -> Optional[StructuredContact]:
    """Get a contact by ID."""
    return db.query(StructuredContact).filter(StructuredContact.id == contact_id).first()


def get_contacts_by_category(
    db: Session,
    tax_category: str,
    limit: int = 100
) -> List[StructuredContact]:
    """Get contacts for a tax category."""
    return db.query(StructuredContact).filter(
        StructuredContact.tax_categories.contains([tax_category])
    ).limit(limit).all()


def get_contact_by_service(
    db: Session,
    service_name_contains: str
) -> Optional[StructuredContact]:
    """Find a contact by service name."""
    return db.query(StructuredContact).filter(
        StructuredContact.service_name.ilike(f"%{service_name_contains}%")
    ).first()


def update_contact(
    db: Session,
    contact_id: str,
    update_data: StructuredContactUpdate
) -> Optional[StructuredContact]:
    """Update a structured contact."""
    contact = get_contact(db, contact_id)
    if not contact:
        return None
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(contact, field, value)
    
    contact.updated_at = datetime.now()
    db.commit()
    db.refresh(contact)
    return contact


def delete_contact(db: Session, contact_id: str) -> bool:
    """Delete a structured contact."""
    contact = get_contact(db, contact_id)
    if not contact:
        return False
    
    db.delete(contact)
    db.commit()
    return True


# =============================================================================
# STRUCTURED CONDITION LIST CRUD
# =============================================================================

def create_condition_list(db: Session, condition_data: StructuredConditionListCreate) -> StructuredConditionList:
    """Create a new condition list."""
    condition_list = StructuredConditionList(
        chunk_id=condition_data.chunk_id,
        document_id=condition_data.document_id,
        condition_name=condition_data.condition_name,
        condition_type=condition_data.condition_type,
        condition_description=condition_data.condition_description,
        tax_types=condition_data.tax_types,
        logical_operator=condition_data.logical_operator,
        conditions=condition_data.conditions,
        outcome_if_met=condition_data.outcome_if_met,
        outcome_if_not_met=condition_data.outcome_if_not_met,
        related_decision_tree_id=condition_data.related_decision_tree_id,
        tax_year=condition_data.tax_year,
        effective_from=condition_data.effective_from,
        effective_until=condition_data.effective_until,
        source_url=condition_data.source_url,
        citable_reference=condition_data.citable_reference
    )
    
    db.add(condition_list)
    db.commit()
    db.refresh(condition_list)
    return condition_list


def get_condition_list(db: Session, condition_id: str) -> Optional[StructuredConditionList]:
    """Get a condition list by ID."""
    return db.query(StructuredConditionList).filter(
        StructuredConditionList.id == condition_id
    ).first()


def get_condition_lists_by_type(
    db: Session,
    condition_type: str,
    tax_type: Optional[str] = None,
    limit: int = 100
) -> List[StructuredConditionList]:
    """Get condition lists by type."""
    query = db.query(StructuredConditionList).filter(
        StructuredConditionList.condition_type == condition_type
    )
    
    if tax_type:
        query = query.filter(StructuredConditionList.tax_types.contains([tax_type]))
    
    return query.limit(limit).all()


def update_condition_list(
    db: Session,
    condition_id: str,
    update_data: StructuredConditionListUpdate
) -> Optional[StructuredConditionList]:
    """Update a condition list."""
    condition_list = get_condition_list(db, condition_id)
    if not condition_list:
        return None
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(condition_list, field, value)
    
    condition_list.updated_at = datetime.now()
    db.commit()
    db.refresh(condition_list)
    return condition_list


def delete_condition_list(db: Session, condition_id: str) -> bool:
    """Delete a condition list."""
    condition_list = get_condition_list(db, condition_id)
    if not condition_list:
        return False
    
    db.delete(condition_list)
    db.commit()
    return True


# =============================================================================
# AGGREGATE OPERATIONS
# =============================================================================

def get_structured_content_for_chunk(db: Session, chunk_id: str) -> Dict[str, List]:
    """Get all structured content linked to a chunk."""
    return {
        "tables": get_tables_by_chunk(db, chunk_id),
        "formulas": db.query(StructuredFormula).filter(
            StructuredFormula.chunk_id == chunk_id
        ).all(),
        "decision_trees": db.query(StructuredDecisionTree).filter(
            StructuredDecisionTree.chunk_id == chunk_id
        ).all(),
        "deadlines": db.query(StructuredDeadline).filter(
            StructuredDeadline.chunk_id == chunk_id
        ).all(),
        "examples": db.query(StructuredExample).filter(
            StructuredExample.chunk_id == chunk_id
        ).all(),
        "contacts": db.query(StructuredContact).filter(
            StructuredContact.chunk_id == chunk_id
        ).all(),
        "condition_lists": db.query(StructuredConditionList).filter(
            StructuredConditionList.chunk_id == chunk_id
        ).all()
    }


def delete_structured_content_for_chunk(db: Session, chunk_id: str) -> Dict[str, int]:
    """Delete all structured content for a chunk. Returns counts."""
    counts = {}
    
    counts["tables"] = db.query(StructuredTable).filter(
        StructuredTable.chunk_id == chunk_id
    ).delete()
    
    counts["formulas"] = db.query(StructuredFormula).filter(
        StructuredFormula.chunk_id == chunk_id
    ).delete()
    
    counts["decision_trees"] = db.query(StructuredDecisionTree).filter(
        StructuredDecisionTree.chunk_id == chunk_id
    ).delete()
    
    counts["deadlines"] = db.query(StructuredDeadline).filter(
        StructuredDeadline.chunk_id == chunk_id
    ).delete()
    
    counts["examples"] = db.query(StructuredExample).filter(
        StructuredExample.chunk_id == chunk_id
    ).delete()
    
    counts["contacts"] = db.query(StructuredContact).filter(
        StructuredContact.chunk_id == chunk_id
    ).delete()
    
    counts["condition_lists"] = db.query(StructuredConditionList).filter(
        StructuredConditionList.chunk_id == chunk_id
    ).delete()
    
    db.commit()
    return counts


def get_structured_content_stats(db: Session) -> StructuredContentStats:
    """Get statistics about all structured content."""
    # Total counts
    total_tables = db.query(func.count(StructuredTable.id)).scalar() or 0
    total_formulas = db.query(func.count(StructuredFormula.id)).scalar() or 0
    total_decision_trees = db.query(func.count(StructuredDecisionTree.id)).scalar() or 0
    total_deadlines = db.query(func.count(StructuredDeadline.id)).scalar() or 0
    total_examples = db.query(func.count(StructuredExample.id)).scalar() or 0
    total_contacts = db.query(func.count(StructuredContact.id)).scalar() or 0
    total_condition_lists = db.query(func.count(StructuredConditionList.id)).scalar() or 0
    
    # Tables by type
    tables_by_type = dict(
        db.query(StructuredTable.table_type, func.count(StructuredTable.id))
        .group_by(StructuredTable.table_type)
        .all()
    )
    tables_by_type = {k.value if k else "unknown": v for k, v in tables_by_type.items()}
    
    # Formulas by type
    formulas_by_type = dict(
        db.query(StructuredFormula.formula_type, func.count(StructuredFormula.id))
        .group_by(StructuredFormula.formula_type)
        .all()
    )
    formulas_by_type = {k.value if k else "unknown": v for k, v in formulas_by_type.items()}
    
    # Decision trees by category
    trees_by_category = dict(
        db.query(StructuredDecisionTree.tree_category, func.count(StructuredDecisionTree.id))
        .group_by(StructuredDecisionTree.tree_category)
        .all()
    )
    trees_by_category = {k.value if k else "unknown": v for k, v in trees_by_category.items()}
    
    # Deadlines by type
    deadlines_by_type = dict(
        db.query(StructuredDeadline.deadline_type, func.count(StructuredDeadline.id))
        .group_by(StructuredDeadline.deadline_type)
        .all()
    )
    deadlines_by_type = {k.value if k else "unknown": v for k, v in deadlines_by_type.items()}
    
    # Examples by category
    examples_by_category = dict(
        db.query(StructuredExample.example_category, func.count(StructuredExample.id))
        .group_by(StructuredExample.example_category)
        .all()
    )
    examples_by_category = {k.value if k else "unknown": v for k, v in examples_by_category.items()}
    
    return StructuredContentStats(
        total_tables=total_tables,
        total_formulas=total_formulas,
        total_decision_trees=total_decision_trees,
        total_deadlines=total_deadlines,
        total_examples=total_examples,
        total_contacts=total_contacts,
        total_condition_lists=total_condition_lists,
        tables_by_type=tables_by_type,
        formulas_by_type=formulas_by_type,
        decision_trees_by_category=trees_by_category,
        deadlines_by_type=deadlines_by_type,
        examples_by_category=examples_by_category
    )


# =============================================================================
# FUNCTION ALIASES FOR PIPELINE COMPATIBILITY
# =============================================================================

# Table aliases
create_structured_table = create_table
get_structured_table = get_table
update_structured_table = update_table
delete_structured_table = delete_table

# Formula aliases
create_structured_formula = create_formula
get_structured_formula = get_formula
update_structured_formula = update_formula
delete_structured_formula = delete_formula

# Decision Tree aliases
create_structured_decision_tree = create_decision_tree
get_structured_decision_tree = get_decision_tree
update_structured_decision_tree = update_decision_tree
delete_structured_decision_tree = delete_decision_tree

# Deadline aliases
create_structured_deadline = create_deadline
get_structured_deadline = get_deadline
update_structured_deadline = update_deadline
delete_structured_deadline = delete_deadline

# Example aliases
create_structured_example = create_example
get_structured_example = get_example
update_structured_example = update_example
delete_structured_example = delete_example

# Contact aliases
create_structured_contact = create_contact
get_structured_contact = get_contact
update_structured_contact = update_contact
delete_structured_contact = delete_contact

# Condition List aliases
create_structured_condition_list = create_condition_list
get_structured_condition_list = get_condition_list
update_structured_condition_list = update_condition_list
delete_structured_condition_list = delete_condition_list
