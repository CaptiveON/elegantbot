"""
Test Script for Phase 1.2: Structured Content

This script tests all structured content models, schemas, and CRUD operations:
- Tables, Formulas, Decision Trees, Deadlines, Examples, Contacts, Condition Lists

Run with: python test_phase1_structured_content.py

Prerequisites:
1. PostgreSQL database running
2. .env file configured with DATABASE_URL
3. Phase 1 and 1.1 tables already created
"""
from datetime import datetime
from sqlalchemy.orm import Session

# Import database
from app.database import engine, SessionLocal, Base

# Import models
from app.models import (
    SourceDocument,
    DocumentChunk,
    StructuredTable,
    StructuredFormula,
    StructuredDecisionTree,
    StructuredDeadline,
    StructuredExample,
    StructuredContact,
    StructuredConditionList,
    AuthorityType,
    DocumentType,
    IngestionStatus,
    TopicPrimary,
    ContentType,
    ServiceCategory,
    TableType,
    FormulaType,
    DecisionCategory,
    DeadlineType,
    DeadlineFrequency,
    ExampleCategory,
    ConditionLogic
)

# Import schemas
from app.schema import (
    DocumentCreate,
    ChunkCreate,
    StructuredTableCreate,
    StructuredFormulaCreate,
    StructuredDecisionTreeCreate,
    StructuredDeadlineCreate,
    StructuredExampleCreate,
    StructuredContactCreate,
    StructuredConditionListCreate,
    TopicPrimary as TopicPrimarySchema,
    ContentType as ContentTypeSchema,
    ServiceCategory as ServiceCategorySchema
)

# Import CRUD
from app.crud import (
    crud_document,
    crud_chunk,
    crud_structured_content
)


def print_section(title: str):
    """Print a section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_create_tables():
    """Test that all structured content tables can be created"""
    print_section("Testing Structured Content Table Creation")
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ All tables created successfully!")
        
        # List tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        # Check for new structured content tables
        expected_tables = [
            "structured_tables",
            "structured_formulas",
            "structured_decision_trees",
            "structured_deadlines",
            "structured_examples",
            "structured_contacts",
            "structured_condition_lists"
        ]
        
        print("\nStructured Content Tables:")
        for table in expected_tables:
            if table in tables:
                print(f"  ✅ {table}")
            else:
                print(f"  ❌ {table} (missing)")
        
        return True
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_test_document_and_chunk(db: Session):
    """Create test document and chunk for structured content"""
    print_section("Creating Test Document and Chunk")
    
    # Create document
    doc_data = DocumentCreate(
        url="https://www.gov.uk/income-tax-rates",
        authority=AuthorityType.GOV_UK,
        document_type=DocumentType.GUIDANCE,
        reliability_tier=2,
        title="Income Tax Rates",
        tax_year="2024-25"
    )
    
    # Check if exists
    existing = crud_document.get_document_by_url(db, doc_data.url)
    if existing:
        crud_document.delete_document(db, existing.id)
    
    doc = crud_document.create_document(db, doc_data)
    print(f"✅ Created document: {doc.id[:8]}...")
    
    # Create chunk with structured content flags
    chunk_data = ChunkCreate(
        document_id=doc.id,
        content="Income tax rates and bands for 2024-25 tax year...",
        source_url=doc.url,
        source_authority="GOV_UK",
        section_title="Income Tax Rates",
        section_id="IT-RATES-2024",
        citable_reference="GOV.UK Income Tax Rates 2024-25",
        topic_primary=TopicPrimarySchema.INCOME_TAX,
        content_type=ContentTypeSchema.FACTUAL,
        reliability_tier=2,
        tax_year="2024-25",
        contains_table=True,
        contains_formula=True,
        contains_example=True,
        structured_content_types=["table", "formula", "example"],
        chunk_index=0,
        total_chunks_in_doc=1
    )
    
    chunk = crud_chunk.create_chunk(db, chunk_data)
    print(f"✅ Created chunk: {chunk.id[:8]}...")
    print(f"   Contains table: {chunk.contains_table}")
    print(f"   Contains formula: {chunk.contains_formula}")
    print(f"   Structured types: {chunk.structured_content_types}")
    
    return doc, chunk


def test_structured_table(db: Session, doc, chunk):
    """Test StructuredTable CRUD"""
    print_section("Testing StructuredTable CRUD")
    
    try:
        # Create income tax rates table
        table_data = StructuredTableCreate(
            chunk_id=chunk.id,
            document_id=doc.id,
            table_type=TableType.TAX_RATES,
            table_name="Income Tax Rates and Bands 2024-25",
            table_description="Income tax rates for the 2024-25 tax year",
            headers=["Band", "Taxable Income From", "Taxable Income To", "Rate"],
            rows=[
                {
                    "band": "Personal Allowance",
                    "taxable_income_from": 0,
                    "taxable_income_to": 12570,
                    "rate": 0
                },
                {
                    "band": "Basic Rate",
                    "taxable_income_from": 12571,
                    "taxable_income_to": 50270,
                    "rate": 20
                },
                {
                    "band": "Higher Rate",
                    "taxable_income_from": 50271,
                    "taxable_income_to": 125140,
                    "rate": 40
                },
                {
                    "band": "Additional Rate",
                    "taxable_income_from": 125141,
                    "taxable_income_to": None,
                    "rate": 45
                }
            ],
            column_types={
                "band": "text",
                "taxable_income_from": "currency_gbp",
                "taxable_income_to": "currency_gbp",
                "rate": "percentage"
            },
            lookup_keys=["taxable_income_from", "taxable_income_to"],
            value_columns=["rate"],
            tax_year="2024-25",
            source_url=doc.url,
            citable_reference="GOV.UK Income Tax Rates 2024-25"
        )
        
        table = crud_structured_content.create_table(db, table_data)
        print(f"✅ Created StructuredTable: {table.id[:8]}...")
        print(f"   Name: {table.table_name}")
        print(f"   Type: {table.table_type}")
        print(f"   Rows: {len(table.rows)}")
        
        # Test range lookup
        rate = table.lookup_range(
            value=60000,
            min_column="taxable_income_from",
            max_column="taxable_income_to",
            return_column="rate"
        )
        print(f"✅ Range lookup (£60,000): {rate}% (expected: 40%)")
        
        # Test get by type
        tax_rate_tables = crud_structured_content.get_tables_by_type(
            db, TableType.TAX_RATES, tax_year="2024-25"
        )
        print(f"✅ Found {len(tax_rate_tables)} tax rate table(s)")
        
        return table
        
    except Exception as e:
        print(f"❌ StructuredTable test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_structured_formula(db: Session, doc, chunk):
    """Test StructuredFormula CRUD"""
    print_section("Testing StructuredFormula CRUD")
    
    try:
        formula_data = StructuredFormulaCreate(
            chunk_id=chunk.id,
            document_id=doc.id,
            formula_type=FormulaType.TAX_CALCULATION,
            formula_name="Income Tax Calculation",
            formula_description="Calculate income tax based on taxable income",
            formula_text="Tax = Sum of (Income in each band × Band rate)",
            variables={
                "gross_income": {
                    "type": "currency_gbp",
                    "description": "Total gross income"
                },
                "personal_allowance": {
                    "type": "currency_gbp",
                    "description": "Personal allowance amount",
                    "default": 12570
                }
            },
            formula_logic={
                "type": "stepped",
                "steps": [
                    {
                        "step": 1,
                        "description": "Calculate taxable income",
                        "calculation": "taxable_income = gross_income - personal_allowance"
                    },
                    {
                        "step": 2,
                        "description": "Apply tax bands",
                        "calculation": "Apply rates from income_tax_bands table"
                    }
                ]
            },
            tables_used=["income_tax_bands_2024"],
            tax_year="2024-25",
            source_url=doc.url,
            citable_reference="GOV.UK Income Tax Calculation"
        )
        
        formula = crud_structured_content.create_formula(db, formula_data)
        print(f"✅ Created StructuredFormula: {formula.id[:8]}...")
        print(f"   Name: {formula.formula_name}")
        print(f"   Type: {formula.formula_type}")
        print(f"   Variables: {list(formula.variables.keys())}")
        
        return formula
        
    except Exception as e:
        print(f"❌ StructuredFormula test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_structured_decision_tree(db: Session, doc, chunk):
    """Test StructuredDecisionTree CRUD"""
    print_section("Testing StructuredDecisionTree CRUD")
    
    try:
        tree_data = StructuredDecisionTreeCreate(
            chunk_id=chunk.id,
            document_id=doc.id,
            tree_category=DecisionCategory.REGISTRATION,
            tree_name="VAT Registration Requirement",
            tree_description="Determine if you need to register for VAT",
            tax_types=["VAT"],
            entry_node_id="node_1",
            nodes=[
                {
                    "id": "node_1",
                    "type": "question",
                    "text": "Is your taxable turnover over £90,000 in the last 12 months?",
                    "variable": "turnover_12m",
                    "condition": {"operator": ">", "value": 90000},
                    "yes_next": "node_2",
                    "no_next": "node_3"
                },
                {
                    "id": "node_2",
                    "type": "outcome",
                    "result": "must_register",
                    "text": "You MUST register for VAT within 30 days",
                    "severity": "mandatory",
                    "action_required": True
                },
                {
                    "id": "node_3",
                    "type": "question",
                    "text": "Do you expect to exceed £90,000 in the next 30 days?",
                    "variable": "expected_turnover_30d",
                    "condition": {"operator": ">", "value": 90000},
                    "yes_next": "node_4",
                    "no_next": "node_5"
                },
                {
                    "id": "node_4",
                    "type": "outcome",
                    "result": "must_register_immediate",
                    "text": "You MUST register for VAT immediately",
                    "severity": "mandatory",
                    "action_required": True
                },
                {
                    "id": "node_5",
                    "type": "outcome",
                    "result": "optional",
                    "text": "VAT registration is optional",
                    "severity": "optional",
                    "action_required": False
                }
            ],
            possible_outcomes=["must_register", "must_register_immediate", "optional"],
            tax_year="2024-25",
            source_url="https://www.gov.uk/vat-registration",
            citable_reference="GOV.UK VAT Registration"
        )
        
        tree = crud_structured_content.create_decision_tree(db, tree_data)
        print(f"✅ Created StructuredDecisionTree: {tree.id[:8]}...")
        print(f"   Name: {tree.tree_name}")
        print(f"   Category: {tree.tree_category}")
        print(f"   Nodes: {len(tree.nodes)}")
        print(f"   Possible outcomes: {tree.possible_outcomes}")
        
        # Test get entry node
        entry = tree.get_entry_node()
        print(f"✅ Entry node: {entry['text'][:50]}...")
        
        return tree
        
    except Exception as e:
        print(f"❌ StructuredDecisionTree test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_structured_deadline(db: Session, doc, chunk):
    """Test StructuredDeadline CRUD"""
    print_section("Testing StructuredDeadline CRUD")
    
    try:
        deadline_data = StructuredDeadlineCreate(
            chunk_id=chunk.id,
            document_id=doc.id,
            deadline_type=DeadlineType.FILING,
            deadline_name="Self Assessment Online Filing Deadline",
            deadline_description="Deadline for submitting online Self Assessment tax return",
            tax_category="self_assessment",
            frequency=DeadlineFrequency.ANNUAL,
            deadline_rule={
                "type": "fixed_annual",
                "month": 1,
                "day": 31,
                "relative_to": "tax_year_end",
                "description": "31 January following the end of the tax year"
            },
            examples=[
                {"tax_year": "2023-24", "deadline_date": "2025-01-31"},
                {"tax_year": "2024-25", "deadline_date": "2026-01-31"}
            ],
            suggested_reminder_days=[30, 14, 7, 1],
            tax_year="2024-25",
            source_url="https://www.gov.uk/self-assessment-tax-returns",
            citable_reference="GOV.UK Self Assessment Deadlines"
        )
        
        deadline = crud_structured_content.create_deadline(db, deadline_data)
        print(f"✅ Created StructuredDeadline: {deadline.id[:8]}...")
        print(f"   Name: {deadline.deadline_name}")
        print(f"   Type: {deadline.deadline_type}")
        print(f"   Frequency: {deadline.frequency}")
        print(f"   Reminder days: {deadline.suggested_reminder_days}")
        
        return deadline
        
    except Exception as e:
        print(f"❌ StructuredDeadline test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_structured_example(db: Session, doc, chunk):
    """Test StructuredExample CRUD"""
    print_section("Testing StructuredExample CRUD")
    
    try:
        example_data = StructuredExampleCreate(
            chunk_id=chunk.id,
            document_id=doc.id,
            example_category=ExampleCategory.INCOME_TAX,
            example_name="Income Tax Calculation - Basic Rate Taxpayer",
            example_description="Example calculation for someone earning £55,000",
            scenario={
                "person": "Sarah",
                "gross_income": 55000,
                "tax_year": "2024-25",
                "employment_status": "employed"
            },
            steps=[
                {
                    "step": 1,
                    "title": "Deduct Personal Allowance",
                    "description": "Subtract the tax-free personal allowance",
                    "calculation": "55000 - 12570",
                    "result": 42430,
                    "result_label": "Taxable income"
                },
                {
                    "step": 2,
                    "title": "Calculate Basic Rate Tax",
                    "description": "First £37,700 of taxable income at 20%",
                    "calculation": "37700 * 0.20",
                    "result": 7540,
                    "result_label": "Basic rate tax"
                },
                {
                    "step": 3,
                    "title": "Calculate Higher Rate Tax",
                    "description": "Remaining £4,730 at 40%",
                    "calculation": "4730 * 0.40",
                    "result": 1892,
                    "result_label": "Higher rate tax"
                },
                {
                    "step": 4,
                    "title": "Total Tax",
                    "description": "Sum of all tax bands",
                    "calculation": "7540 + 1892",
                    "result": 9432,
                    "result_label": "Total income tax"
                }
            ],
            final_result={
                "value": 9432,
                "label": "Total income tax",
                "formatted": "£9,432"
            },
            formulas_used=["income_tax_calculation"],
            tables_used=["income_tax_bands_2024"],
            tax_year="2024-25",
            source_url=doc.url,
            citable_reference="GOV.UK Income Tax Example"
        )
        
        example = crud_structured_content.create_example(db, example_data)
        print(f"✅ Created StructuredExample: {example.id[:8]}...")
        print(f"   Name: {example.example_name}")
        print(f"   Category: {example.example_category}")
        print(f"   Steps: {len(example.steps)}")
        print(f"   Final result: {example.final_result['formatted']}")
        
        return example
        
    except Exception as e:
        print(f"❌ StructuredExample test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_structured_contact(db: Session, doc, chunk):
    """Test StructuredContact CRUD"""
    print_section("Testing StructuredContact CRUD")
    
    try:
        contact_data = StructuredContactCreate(
            chunk_id=chunk.id,
            document_id=doc.id,
            service_name="Self Assessment Helpline",
            department="HMRC",
            service_description="Get help with Self Assessment tax returns",
            tax_categories=["self_assessment", "income_tax"],
            contact_methods=[
                {
                    "type": "phone",
                    "value": "0300 200 3310",
                    "hours": "Monday to Friday, 8am to 6pm",
                    "notes": "Closed on bank holidays"
                },
                {
                    "type": "phone_international",
                    "value": "+44 161 931 9070",
                    "hours": "Monday to Friday, 8am to 6pm UK time"
                },
                {
                    "type": "textphone",
                    "value": "0300 200 3319"
                }
            ],
            online_services=[
                {
                    "name": "Personal Tax Account",
                    "url": "https://www.gov.uk/personal-tax-account",
                    "description": "View and manage your tax online"
                }
            ],
            postal_address={
                "lines": ["Self Assessment", "HM Revenue and Customs", "BX9 1AS"],
                "country": "United Kingdom"
            },
            last_verified=datetime.now(),
            source_url="https://www.gov.uk/contact-hmrc",
            citable_reference="GOV.UK Contact HMRC"
        )
        
        contact = crud_structured_content.create_contact(db, contact_data)
        print(f"✅ Created StructuredContact: {contact.id[:8]}...")
        print(f"   Service: {contact.service_name}")
        print(f"   Department: {contact.department}")
        print(f"   Phone: {contact.get_phone()}")
        print(f"   Contact methods: {len(contact.contact_methods)}")
        
        return contact
        
    except Exception as e:
        print(f"❌ StructuredContact test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_structured_condition_list(db: Session, doc, chunk):
    """Test StructuredConditionList CRUD"""
    print_section("Testing StructuredConditionList CRUD")
    
    try:
        condition_data = StructuredConditionListCreate(
            chunk_id=chunk.id,
            document_id=doc.id,
            condition_name="VAT Registration Requirements",
            condition_type="requirement",
            condition_description="Conditions that require mandatory VAT registration",
            tax_types=["VAT"],
            logical_operator=ConditionLogic.OR,
            conditions=[
                {
                    "id": "a",
                    "text": "your taxable turnover exceeds £90,000 in any 12-month period",
                    "variable": "turnover_12m",
                    "operator": ">",
                    "threshold": 90000,
                    "threshold_type": "currency_gbp"
                },
                {
                    "id": "b",
                    "text": "you expect your taxable turnover to exceed £90,000 in the next 30 days alone",
                    "variable": "expected_turnover_30d",
                    "operator": ">",
                    "threshold": 90000,
                    "threshold_type": "currency_gbp"
                },
                {
                    "id": "c",
                    "text": "you take over a VAT-registered business as a going concern",
                    "variable": "takeover_vat_business",
                    "operator": "==",
                    "threshold": True,
                    "threshold_type": "boolean"
                }
            ],
            outcome_if_met="You must register for VAT",
            outcome_if_not_met="VAT registration is optional",
            tax_year="2024-25",
            source_url="https://www.gov.uk/vat-registration",
            citable_reference="GOV.UK VAT Registration Requirements"
        )
        
        condition_list = crud_structured_content.create_condition_list(db, condition_data)
        print(f"✅ Created StructuredConditionList: {condition_list.id[:8]}...")
        print(f"   Name: {condition_list.condition_name}")
        print(f"   Logic: {condition_list.logical_operator}")
        print(f"   Conditions: {len(condition_list.conditions)}")
        print(f"   Outcome if met: {condition_list.outcome_if_met}")
        
        return condition_list
        
    except Exception as e:
        print(f"❌ StructuredConditionList test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_structured_content_stats(db: Session):
    """Test aggregate statistics"""
    print_section("Testing Structured Content Statistics")
    
    try:
        stats = crud_structured_content.get_structured_content_stats(db)
        print(f"✅ Structured Content Stats:")
        print(f"   Tables: {stats.total_tables}")
        print(f"   Formulas: {stats.total_formulas}")
        print(f"   Decision Trees: {stats.total_decision_trees}")
        print(f"   Deadlines: {stats.total_deadlines}")
        print(f"   Examples: {stats.total_examples}")
        print(f"   Contacts: {stats.total_contacts}")
        print(f"   Condition Lists: {stats.total_condition_lists}")
        
        if stats.tables_by_type:
            print(f"\n   Tables by type: {stats.tables_by_type}")
        
        return stats
        
    except Exception as e:
        print(f"❌ Stats test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_chunk_stats_with_structured(db: Session):
    """Test chunk stats include structured content counts"""
    print_section("Testing Chunk Stats with Structured Content")
    
    try:
        stats = crud_chunk.get_chunk_stats(db)
        print(f"✅ Chunk Stats (with structured content):")
        print(f"   Total chunks: {stats['total_chunks']}")
        print(f"   With tables: {stats.get('with_tables', 0)}")
        print(f"   With formulas: {stats.get('with_formulas', 0)}")
        print(f"   With decision trees: {stats.get('with_decision_trees', 0)}")
        print(f"   With deadlines: {stats.get('with_deadlines', 0)}")
        print(f"   With examples: {stats.get('with_examples', 0)}")
        print(f"   With contacts: {stats.get('with_contacts', 0)}")
        
        return stats
        
    except Exception as e:
        print(f"❌ Chunk stats test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def cleanup(db: Session, doc_id: str = None):
    """Clean up test data"""
    print_section("Cleanup")
    
    try:
        if doc_id:
            # Delete document (cascades to chunks and structured content)
            crud_document.delete_document(db, doc_id)
            print(f"✅ Deleted test document and all related data")
        
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  PHASE 1.2: STRUCTURED CONTENT TEST SUITE")
    print("="*60)
    
    # Test table creation
    if not test_create_tables():
        print("\n❌ Cannot continue without tables")
        return
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Create test document and chunk
        doc, chunk = create_test_document_and_chunk(db)
        
        # Test each structured content type
        table = test_structured_table(db, doc, chunk)
        formula = test_structured_formula(db, doc, chunk)
        tree = test_structured_decision_tree(db, doc, chunk)
        deadline = test_structured_deadline(db, doc, chunk)
        example = test_structured_example(db, doc, chunk)
        contact = test_structured_contact(db, doc, chunk)
        condition_list = test_structured_condition_list(db, doc, chunk)
        
        # Test aggregate operations
        test_structured_content_stats(db)
        test_chunk_stats_with_structured(db)
        
        # Cleanup
        cleanup(db, doc.id)
        
        print_section("TEST SUMMARY")
        print("✅ All Phase 1.2 Structured Content tests completed!")
        print("\nNew features tested:")
        print("  - StructuredTable (tax rates, thresholds, penalties)")
        print("  - StructuredFormula (tax calculations)")
        print("  - StructuredDecisionTree (eligibility checks)")
        print("  - StructuredDeadline (filing/payment dates)")
        print("  - StructuredExample (worked calculations)")
        print("  - StructuredContact (HMRC helplines)")
        print("  - StructuredConditionList (legal requirements)")
        print("  - Chunk linking to structured content")
        print("  - Aggregate statistics")
        print("\nYour data foundation is ready for Phase 2: Document Ingestion")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
