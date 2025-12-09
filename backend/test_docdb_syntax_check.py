"""
Syntax Validation Test for Phase 1.2: Structured Content

This script validates that all code is syntactically correct and imports work.
It doesn't require a database connection.

Run with: python test_phase1_syntax_check.py
"""

import sys
import os

# Add the app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def print_section(title: str):
    """Print a section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_imports():
    """Test that all modules can be imported"""
    print_section("Testing Module Imports")
    
    errors = []
    
    # Test model imports
    try:
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
            DeadlineFrequency,
            ContactType,
            ExampleCategory,
            ConditionLogic
        )
        print("✅ Structured Content Models imported successfully")
    except Exception as e:
        errors.append(f"Models import: {e}")
        print(f"❌ Models import failed: {e}")
    
    # Test schema imports
    try:
        from app.schema.structured_content import (
            StructuredTableCreate,
            StructuredTableUpdate,
            StructuredTableResponse,
            StructuredFormulaCreate,
            StructuredFormulaResponse,
            StructuredDecisionTreeCreate,
            StructuredDecisionTreeResponse,
            StructuredDeadlineCreate,
            StructuredDeadlineResponse,
            StructuredExampleCreate,
            StructuredExampleResponse,
            StructuredContactCreate,
            StructuredContactResponse,
            StructuredConditionListCreate,
            StructuredConditionListResponse,
            StructuredContentStats
        )
        print("✅ Structured Content Schemas imported successfully")
    except Exception as e:
        errors.append(f"Schemas import: {e}")
        print(f"❌ Schemas import failed: {e}")
    
    # Test CRUD imports
    try:
        from app.crud.crud_structured_content import (
            create_table,
            get_table,
            get_tables_by_type,
            create_formula,
            get_formula,
            create_decision_tree,
            get_decision_tree,
            create_deadline,
            get_deadline,
            create_example,
            get_example,
            create_contact,
            get_contact,
            create_condition_list,
            get_condition_list,
            get_structured_content_stats
        )
        print("✅ Structured Content CRUD imported successfully")
    except Exception as e:
        errors.append(f"CRUD import: {e}")
        print(f"❌ CRUD import failed: {e}")
    
    # Test chunk model has new fields
    try:
        from app.models.chunk import DocumentChunk
        
        # Check for new attributes
        new_fields = [
            'contains_table',
            'contains_formula',
            'contains_decision_tree',
            'contains_deadline',
            'contains_example',
            'contains_contact',
            'contains_condition_list',
            'structured_content_types'
        ]
        
        for field in new_fields:
            if not hasattr(DocumentChunk, field):
                raise AttributeError(f"DocumentChunk missing field: {field}")
        
        print("✅ DocumentChunk has all new structured content fields")
    except Exception as e:
        errors.append(f"Chunk model check: {e}")
        print(f"❌ Chunk model check failed: {e}")
    
    # Test chunk schema has new fields
    try:
        from app.schema.chunk import ChunkCreate, ChunkResponse
        
        # Create test instance to verify fields exist
        chunk_fields = ChunkCreate.model_fields
        
        new_schema_fields = [
            'contains_table',
            'contains_formula',
            'contains_decision_tree',
            'contains_deadline',
            'contains_example',
            'contains_contact',
            'contains_condition_list',
            'structured_content_types'
        ]
        
        for field in new_schema_fields:
            if field not in chunk_fields:
                raise AttributeError(f"ChunkCreate missing field: {field}")
        
        print("✅ Chunk schemas have all new structured content fields")
    except Exception as e:
        errors.append(f"Chunk schema check: {e}")
        print(f"❌ Chunk schema check failed: {e}")
    
    return errors


def test_enum_values():
    """Test that all enums have expected values"""
    print_section("Testing Enum Values")
    
    errors = []
    
    try:
        from app.models.structured_content import TableType
        expected_table_types = [
            "tax_rates", "vat_rates", "thresholds", "penalties",
            "deadlines", "allowances", "ni_rates", "other"
        ]
        for t in expected_table_types:
            assert hasattr(TableType, t.upper()), f"Missing TableType.{t.upper()}"
        print(f"✅ TableType has {len(TableType)} values")
    except Exception as e:
        errors.append(f"TableType: {e}")
        print(f"❌ TableType check failed: {e}")
    
    try:
        from app.models.structured_content import FormulaType
        expected_formula_types = [
            "tax_calculation", "marginal_relief", "penalty_calculation"
        ]
        for t in expected_formula_types:
            assert hasattr(FormulaType, t.upper()), f"Missing FormulaType.{t.upper()}"
        print(f"✅ FormulaType has {len(FormulaType)} values")
    except Exception as e:
        errors.append(f"FormulaType: {e}")
        print(f"❌ FormulaType check failed: {e}")
    
    try:
        from app.models.structured_content import DecisionCategory
        expected_categories = ["registration", "eligibility", "filing", "payment"]
        for c in expected_categories:
            assert hasattr(DecisionCategory, c.upper()), f"Missing DecisionCategory.{c.upper()}"
        print(f"✅ DecisionCategory has {len(DecisionCategory)} values")
    except Exception as e:
        errors.append(f"DecisionCategory: {e}")
        print(f"❌ DecisionCategory check failed: {e}")
    
    try:
        from app.models.structured_content import DeadlineType, DeadlineFrequency
        print(f"✅ DeadlineType has {len(DeadlineType)} values")
        print(f"✅ DeadlineFrequency has {len(DeadlineFrequency)} values")
    except Exception as e:
        errors.append(f"Deadline enums: {e}")
        print(f"❌ Deadline enums check failed: {e}")
    
    try:
        from app.models.structured_content import ConditionLogic
        expected_logic = ["AND", "OR", "AND_NOT"]
        for l in expected_logic:
            assert hasattr(ConditionLogic, l), f"Missing ConditionLogic.{l}"
        print(f"✅ ConditionLogic has {len(ConditionLogic)} values")
    except Exception as e:
        errors.append(f"ConditionLogic: {e}")
        print(f"❌ ConditionLogic check failed: {e}")
    
    return errors


def test_schema_validation():
    """Test that schemas can be instantiated"""
    print_section("Testing Schema Instantiation")
    
    errors = []
    
    try:
        from app.schema.structured_content import StructuredTableCreate, TableType
        
        table = StructuredTableCreate(
            chunk_id="test-chunk-id",
            document_id="test-doc-id",
            table_type=TableType.TAX_RATES,
            table_name="Income Tax Rates 2024-25",
            headers=["Band", "Rate"],
            rows=[{"band": "Basic", "rate": 20}],
            source_url="https://gov.uk/test"
        )
        print("✅ StructuredTableCreate instantiation works")
    except Exception as e:
        errors.append(f"StructuredTableCreate: {e}")
        print(f"❌ StructuredTableCreate failed: {e}")
    
    try:
        from app.schema.structured_content import StructuredFormulaCreate, FormulaType
        
        formula = StructuredFormulaCreate(
            chunk_id="test-chunk-id",
            document_id="test-doc-id",
            formula_type=FormulaType.TAX_CALCULATION,
            formula_name="Tax Calculation",
            formula_text="Tax = Income * Rate",
            variables={"income": {"type": "currency"}},
            formula_logic={"type": "simple", "calculation": "income * rate"},
            source_url="https://gov.uk/test"
        )
        print("✅ StructuredFormulaCreate instantiation works")
    except Exception as e:
        errors.append(f"StructuredFormulaCreate: {e}")
        print(f"❌ StructuredFormulaCreate failed: {e}")
    
    try:
        from app.schema.structured_content import StructuredDecisionTreeCreate, DecisionCategory
        
        tree = StructuredDecisionTreeCreate(
            chunk_id="test-chunk-id",
            document_id="test-doc-id",
            tree_category=DecisionCategory.REGISTRATION,
            tree_name="VAT Registration Check",
            entry_node_id="node_1",
            nodes=[{"id": "node_1", "type": "question", "text": "Test?"}],
            source_url="https://gov.uk/test"
        )
        print("✅ StructuredDecisionTreeCreate instantiation works")
    except Exception as e:
        errors.append(f"StructuredDecisionTreeCreate: {e}")
        print(f"❌ StructuredDecisionTreeCreate failed: {e}")
    
    try:
        from app.schema.structured_content import StructuredDeadlineCreate, DeadlineType, DeadlineFrequency
        
        deadline = StructuredDeadlineCreate(
            chunk_id="test-chunk-id",
            document_id="test-doc-id",
            deadline_type=DeadlineType.FILING,
            deadline_name="SA Deadline",
            tax_category="self_assessment",
            frequency=DeadlineFrequency.ANNUAL,
            deadline_rule={"type": "fixed", "month": 1, "day": 31},
            source_url="https://gov.uk/test"
        )
        print("✅ StructuredDeadlineCreate instantiation works")
    except Exception as e:
        errors.append(f"StructuredDeadlineCreate: {e}")
        print(f"❌ StructuredDeadlineCreate failed: {e}")
    
    try:
        from app.schema.structured_content import StructuredExampleCreate, ExampleCategory
        
        example = StructuredExampleCreate(
            chunk_id="test-chunk-id",
            document_id="test-doc-id",
            example_category=ExampleCategory.INCOME_TAX,
            example_name="Tax Example",
            scenario={"income": 50000},
            steps=[{"step": 1, "calculation": "50000 * 0.2", "result": 10000}],
            final_result={"value": 10000, "label": "Tax"},
            source_url="https://gov.uk/test"
        )
        print("✅ StructuredExampleCreate instantiation works")
    except Exception as e:
        errors.append(f"StructuredExampleCreate: {e}")
        print(f"❌ StructuredExampleCreate failed: {e}")
    
    try:
        from app.schema.structured_content import StructuredContactCreate
        
        contact = StructuredContactCreate(
            chunk_id="test-chunk-id",
            document_id="test-doc-id",
            service_name="HMRC Helpline",
            contact_methods=[{"type": "phone", "value": "0300 200 3310"}],
            source_url="https://gov.uk/test"
        )
        print("✅ StructuredContactCreate instantiation works")
    except Exception as e:
        errors.append(f"StructuredContactCreate: {e}")
        print(f"❌ StructuredContactCreate failed: {e}")
    
    try:
        from app.schema.structured_content import StructuredConditionListCreate, ConditionLogic
        
        conditions = StructuredConditionListCreate(
            chunk_id="test-chunk-id",
            document_id="test-doc-id",
            condition_name="VAT Requirements",
            condition_type="requirement",
            logical_operator=ConditionLogic.OR,
            conditions=[{"id": "a", "text": "turnover > 90000"}],
            outcome_if_met="Must register",
            source_url="https://gov.uk/test"
        )
        print("✅ StructuredConditionListCreate instantiation works")
    except Exception as e:
        errors.append(f"StructuredConditionListCreate: {e}")
        print(f"❌ StructuredConditionListCreate failed: {e}")
    
    return errors


def test_model_table_names():
    """Test that models have correct table names"""
    print_section("Testing Model Table Names")
    
    errors = []
    
    expected_tables = {
        'StructuredTable': 'structured_tables',
        'StructuredFormula': 'structured_formulas',
        'StructuredDecisionTree': 'structured_decision_trees',
        'StructuredDeadline': 'structured_deadlines',
        'StructuredExample': 'structured_examples',
        'StructuredContact': 'structured_contacts',
        'StructuredConditionList': 'structured_condition_lists'
    }
    
    try:
        from app.models import structured_content
        
        for class_name, table_name in expected_tables.items():
            cls = getattr(structured_content, class_name)
            actual_table = cls.__tablename__
            if actual_table != table_name:
                raise ValueError(f"{class_name}.__tablename__ = '{actual_table}', expected '{table_name}'")
            print(f"✅ {class_name} → {table_name}")
        
    except Exception as e:
        errors.append(f"Table names: {e}")
        print(f"❌ Table names check failed: {e}")
    
    return errors


def test_exports():
    """Test that all exports are working"""
    print_section("Testing Package Exports")
    
    errors = []
    
    try:
        from app.models import (
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
            DeadlineFrequency,
            ContactType,
            ExampleCategory,
            ConditionLogic
        )
        print("✅ app.models exports all structured content")
    except ImportError as e:
        errors.append(f"models exports: {e}")
        print(f"❌ models exports failed: {e}")
    
    try:
        from app.schema import (
            StructuredTableCreate,
            StructuredTableResponse,
            StructuredFormulaCreate,
            StructuredFormulaResponse,
            StructuredDecisionTreeCreate,
            StructuredDecisionTreeResponse,
            StructuredDeadlineCreate,
            StructuredDeadlineResponse,
            StructuredExampleCreate,
            StructuredExampleResponse,
            StructuredContactCreate,
            StructuredContactResponse,
            StructuredConditionListCreate,
            StructuredConditionListResponse,
            StructuredContentStats
        )
        print("✅ app.schema exports all structured content schemas")
    except ImportError as e:
        errors.append(f"schema exports: {e}")
        print(f"❌ schema exports failed: {e}")
    
    try:
        from app.crud import crud_structured_content
        print("✅ app.crud exports crud_structured_content")
    except ImportError as e:
        errors.append(f"crud exports: {e}")
        print(f"❌ crud exports failed: {e}")
    
    return errors


def main():
    """Run all syntax validation tests"""
    print("\n" + "="*60)
    print("  PHASE 1.2: SYNTAX VALIDATION TEST SUITE")
    print("="*60)
    
    all_errors = []
    
    all_errors.extend(test_imports())
    all_errors.extend(test_enum_values())
    all_errors.extend(test_schema_validation())
    all_errors.extend(test_model_table_names())
    all_errors.extend(test_exports())
    
    print_section("TEST SUMMARY")
    
    if all_errors:
        print(f"❌ {len(all_errors)} error(s) found:")
        for err in all_errors:
            print(f"   - {err}")
        return 1
    else:
        print("✅ All Phase 1.2 syntax validation tests passed!")
        print("\nValidated:")
        print("  - All 7 structured content models")
        print("  - All Pydantic schemas (Create, Update, Response)")
        print("  - All CRUD functions")
        print("  - All enums and their values")
        print("  - Package exports")
        print("  - Chunk model/schema updates")
        print("\n⚠️  Note: Full database tests require PostgreSQL")
        print("    To run full tests, connect to a PostgreSQL database")
        return 0


if __name__ == "__main__":
    sys.exit(main())
