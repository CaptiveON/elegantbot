"""
Phase 2 Document Ingestion - Comprehensive Test Suite

Tests all Phase 2 components without requiring a database connection:
1. Legal Chunker - Structure-aware chunking with citations
2. Table Extractor - HTML table detection and parsing
3. Formula Extractor - Tax calculation formulas
4. Deadline Extractor - Filing/payment deadlines
5. Contact Extractor - HMRC contact information
6. Condition Extractor - Legal condition lists
7. Example Extractor - Worked examples
8. Reference Detector - Cross-references
9. Metadata Extractor - Thresholds, tax years, forms

Run with: python -m pytest test_phase2_extractors.py -v
Or: python test_phase2_extractors.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from datetime import datetime


def test_legal_chunker():
    """Test the Legal Chunker with UK tax document patterns."""
    print("\n" + "="*70)
    print("TEST: Legal Chunker")
    print("="*70)
    
    from app.services.ingestion.legal_chunker import (
        LegalChunker, LegalChunkingConfig, LegalContentType
    )
    from app.services.ingestion.content_parser import ContentParser, ParsedDocument, ContentSection
    
    # Create chunker
    config = LegalChunkingConfig(
        min_chunk_size=100,
        max_chunk_size=2000,
        target_chunk_size=1000,
        preserve_condition_lists=True,
        extract_hmrc_section_ids=True,
        generate_citable_reference=True,
    )
    chunker = LegalChunker(config)
    
    # Test 1: HMRC section ID extraction
    print("\n1. Testing HMRC section ID extraction...")
    test_text = """
    ## VAT Registration Requirements
    
    According to VATREG02200, you must register for VAT if your taxable turnover 
    exceeds £90,000 in any 12-month period.
    
    See also CTM01500 for corporation tax implications and BIM45000 for business 
    income considerations.
    """
    
    section = ContentSection(
        heading="VAT Registration Requirements",
        level=2,
        content=test_text,
        heading_path="VAT Guide > VAT Registration Requirements"
    )
    
    parsed_doc = ParsedDocument(
        title="VAT Registration Guide",
        full_text=test_text,
        sections=[section],
        headings=[{"text": "VAT Registration Requirements", "level": 2, "tag": "h2"}],
        word_count=len(test_text.split()),
        has_content=True
    )
    
    chunks = chunker.chunk_document(parsed_doc, "https://www.gov.uk/vat-registration", "VAT Registration Guide")
    
    assert len(chunks) > 0, "Should create at least one chunk"
    print(f"   ✓ Created {len(chunks)} chunk(s)")
    
    first_chunk = chunks[0]
    assert first_chunk.section_id == "VATREG02200", f"Should extract VATREG02200, got {first_chunk.section_id}"
    print(f"   ✓ Extracted HMRC section ID: {first_chunk.section_id}")
    
    # Check cross-references
    refs = first_chunk.cross_references
    assert "CTM01500" in refs, f"Should find CTM01500 in cross-refs, got {refs}"
    assert "BIM45000" in refs, f"Should find BIM45000 in cross-refs, got {refs}"
    print(f"   ✓ Detected cross-references: {refs}")
    
    # Check citable reference
    assert first_chunk.citable_reference is not None, "Should generate citable reference"
    print(f"   ✓ Generated citation: {first_chunk.citable_reference}")
    
    # Test 2: Condition list detection
    print("\n2. Testing condition list detection...")
    condition_text = """
    ## When to Register for VAT
    
    You must register for VAT if any of the following apply:
    (a) your taxable turnover in the last 12 months exceeds £90,000
    (b) you expect your taxable turnover to exceed £90,000 in the next 30 days
    (c) you take over a VAT-registered business
    
    You can also register voluntarily if your turnover is below the threshold.
    """
    
    parsed_doc2 = ParsedDocument(
        title="VAT Registration",
        full_text=condition_text,
        sections=[ContentSection(
            heading="When to Register for VAT",
            level=2,
            content=condition_text,
            heading_path="VAT Registration"
        )],
        headings=[],
        word_count=len(condition_text.split()),
        has_content=True
    )
    
    chunks2 = chunker.chunk_document(parsed_doc2, "https://gov.uk/vat", "VAT Registration")
    
    assert any(c.contains_condition_list for c in chunks2), "Should detect condition list"
    print(f"   ✓ Detected condition list in chunk")
    
    # Test 3: Content type detection
    print("\n3. Testing content type detection...")
    assert chunker._detect_content_type("'Taxable turnover' means the total value of...") == LegalContentType.DEFINITION
    assert chunker._detect_content_type("The deadline for filing is 31 January") == LegalContentType.DEADLINE
    print(f"   ✓ Content type detection working")
    
    # Test 4: Chunk statistics
    print("\n4. Testing chunk statistics...")
    stats = chunker.get_chunk_stats(chunks)
    assert stats['count'] > 0
    assert stats['with_section_ids'] > 0
    print(f"   ✓ Stats: {stats['count']} chunks, {stats['with_section_ids']} with section IDs")
    
    print("\n✅ Legal Chunker tests PASSED")
    return True


def test_table_extractor():
    """Test the Table Extractor."""
    print("\n" + "="*70)
    print("TEST: Table Extractor")
    print("="*70)
    
    from app.services.ingestion.extractors.table_extractor import TableExtractor
    
    extractor = TableExtractor()
    
    # Test HTML with tax rate table
    html = """
    <h2>Income Tax Rates 2024-25</h2>
    <table>
        <thead>
            <tr>
                <th>Band</th>
                <th>Taxable Income</th>
                <th>Tax Rate</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Personal Allowance</td>
                <td>Up to £12,570</td>
                <td>0%</td>
            </tr>
            <tr>
                <td>Basic rate</td>
                <td>£12,571 to £50,270</td>
                <td>20%</td>
            </tr>
            <tr>
                <td>Higher rate</td>
                <td>£50,271 to £125,140</td>
                <td>40%</td>
            </tr>
            <tr>
                <td>Additional rate</td>
                <td>Over £125,140</td>
                <td>45%</td>
            </tr>
        </tbody>
    </table>
    """
    
    text_content = "Income Tax Rates 2024-25. The tax rates for the 2024-25 tax year."
    
    # Test 1: Table detection
    print("\n1. Testing table detection...")
    assert extractor.has_tables(html), "Should detect tables in HTML"
    print("   ✓ Table detected in HTML")
    
    # Test 2: Table extraction
    print("\n2. Testing table extraction...")
    result = extractor.extract(html, text_content, "https://gov.uk/tax-rates", tax_year="2024-25")
    
    assert result.has_items, "Should extract at least one table"
    table = result.items[0]
    print(f"   ✓ Extracted table: {table.table_name}")
    
    # Test 3: Table structure
    print("\n3. Testing table structure...")
    assert len(table.headers) == 3, f"Should have 3 headers, got {len(table.headers)}"
    assert len(table.rows) == 4, f"Should have 4 rows, got {len(table.rows)}"
    print(f"   ✓ Headers: {table.headers}")
    print(f"   ✓ Rows: {len(table.rows)}")
    
    # Test 4: Table classification
    print("\n4. Testing table classification...")
    assert table.table_type == "tax_rates", f"Should classify as tax_rates, got {table.table_type}"
    print(f"   ✓ Classified as: {table.table_type}")
    
    # Test 5: Tax year extraction
    print("\n5. Testing tax year extraction...")
    assert table.tax_year == "2024-25", f"Should have tax year 2024-25, got {table.tax_year}"
    print(f"   ✓ Tax year: {table.tax_year}")
    
    # Test 6: Readable text generation
    print("\n6. Testing readable text generation...")
    assert len(table.readable_text) > 0, "Should generate readable text"
    print(f"   ✓ Generated readable text ({len(table.readable_text)} chars)")
    
    print("\n✅ Table Extractor tests PASSED")
    return True


def test_formula_extractor():
    """Test the Formula Extractor."""
    print("\n" + "="*70)
    print("TEST: Formula Extractor")
    print("="*70)
    
    from app.services.ingestion.extractors.formula_extractor import FormulaExtractor
    
    extractor = FormulaExtractor()
    
    # Test text with marginal relief formula
    text = """
    Corporation Tax Marginal Relief
    
    If your company's profits are between £50,000 and £250,000, you may be entitled
    to marginal relief. The marginal relief is calculated as:
    
    3/200 × (£250,000 - Augmented Profits) × (Taxable Profits / Augmented Profits)
    
    This reduces your corporation tax liability from the main rate.
    """
    
    # Test 1: Formula detection
    print("\n1. Testing formula detection...")
    assert extractor.has_formulas(text), "Should detect formulas in text"
    print("   ✓ Formula detected in text")
    
    # Test 2: Formula extraction
    print("\n2. Testing formula extraction...")
    result = extractor.extract(None, text, "https://gov.uk/corporation-tax-rates", tax_year="2024-25")
    
    assert result.has_items, "Should extract at least one formula"
    formula = result.items[0]
    print(f"   ✓ Extracted formula: {formula.formula_name}")
    
    # Test 3: Formula type
    print("\n3. Testing formula type...")
    assert formula.formula_type == "marginal_relief", f"Should be marginal_relief, got {formula.formula_type}"
    print(f"   ✓ Formula type: {formula.formula_type}")
    
    # Test 4: Variables
    print("\n4. Testing variable extraction...")
    assert len(formula.variables) > 0, "Should extract variables"
    print(f"   ✓ Variables: {list(formula.variables.keys())}")
    
    # Test 5: Formula logic
    print("\n5. Testing formula logic...")
    assert formula.formula_logic is not None, "Should have formula logic"
    print(f"   ✓ Formula logic type: {formula.formula_logic.get('type')}")
    
    print("\n✅ Formula Extractor tests PASSED")
    return True


def test_deadline_extractor():
    """Test the Deadline Extractor."""
    print("\n" + "="*70)
    print("TEST: Deadline Extractor")
    print("="*70)
    
    from app.services.ingestion.extractors.deadline_extractor import DeadlineExtractor
    
    extractor = DeadlineExtractor()
    
    text = """
    Self Assessment Deadlines
    
    The deadline for submitting your online Self Assessment tax return is 
    31 January following the end of the tax year.
    
    If you file a paper return, the deadline is 31 October.
    
    You must also pay any tax owed by 31 January, otherwise you may face a penalty.
    """
    
    # Test 1: Deadline detection
    print("\n1. Testing deadline detection...")
    assert extractor.has_deadlines(text), "Should detect deadlines in text"
    print("   ✓ Deadlines detected in text")
    
    # Test 2: Deadline extraction
    print("\n2. Testing deadline extraction...")
    result = extractor.extract(None, text, "https://gov.uk/self-assessment-tax-returns")
    
    assert result.has_items, "Should extract deadlines"
    print(f"   ✓ Extracted {len(result.items)} deadline(s)")
    
    # Test 3: Known deadline detection
    print("\n3. Testing known deadline detection...")
    deadline_names = [d.deadline_name for d in result.items]
    assert any("31 January" in str(d.deadline_rule) or "Self Assessment" in d.deadline_name for d in result.items)
    print(f"   ✓ Found deadlines: {deadline_names}")
    
    print("\n✅ Deadline Extractor tests PASSED")
    return True


def test_contact_extractor():
    """Test the Contact Extractor."""
    print("\n" + "="*70)
    print("TEST: Contact Extractor")
    print("="*70)
    
    from app.services.ingestion.extractors.contact_extractor import ContactExtractor
    
    extractor = ContactExtractor()
    
    text = """
    Contact HMRC
    
    For Self Assessment queries, contact the Self Assessment helpline:
    Telephone: 0300 200 3310
    Opening hours: 8am to 6pm, Monday to Friday
    
    For VAT queries:
    Telephone: 0300 200 3700
    """
    
    # Test 1: Contact detection
    print("\n1. Testing contact detection...")
    assert extractor.has_contacts(text), "Should detect contacts in text"
    print("   ✓ Contacts detected in text")
    
    # Test 2: Contact extraction
    print("\n2. Testing contact extraction...")
    result = extractor.extract(None, text, "https://gov.uk/contact-hmrc")
    
    assert result.has_items, "Should extract contacts"
    contact = result.items[0]
    print(f"   ✓ Extracted contact: {contact.service_name}")
    
    # Test 3: Phone number extraction
    print("\n3. Testing phone number extraction...")
    phones = [m for m in contact.contact_methods if m.get('type') == 'phone']
    assert len(phones) > 0, "Should extract phone numbers"
    print(f"   ✓ Phone numbers: {[p.get('value') for p in phones]}")
    
    print("\n✅ Contact Extractor tests PASSED")
    return True


def test_condition_extractor():
    """Test the Condition Extractor."""
    print("\n" + "="*70)
    print("TEST: Condition Extractor")
    print("="*70)
    
    from app.services.ingestion.extractors.condition_extractor import ConditionExtractor
    
    extractor = ConditionExtractor()
    
    text = """
    You must register for VAT if any of the following apply:
    (a) your taxable turnover in the last 12 months exceeds £90,000
    (b) you expect your turnover to exceed £90,000 in the next 30 days alone
    (c) you take over a VAT-registered business as a going concern
    
    This is mandatory - you cannot choose not to register if these conditions apply.
    """
    
    # Test 1: Condition list detection
    print("\n1. Testing condition list detection...")
    assert extractor.has_condition_lists(text), "Should detect condition lists"
    print("   ✓ Condition list detected")
    
    # Test 2: Condition extraction
    print("\n2. Testing condition extraction...")
    result = extractor.extract(None, text, "https://gov.uk/vat-registration")
    
    assert result.has_items, "Should extract condition lists"
    condition_list = result.items[0]
    print(f"   ✓ Extracted: {condition_list.condition_name}")
    
    # Test 3: Condition items
    print("\n3. Testing condition items...")
    assert len(condition_list.conditions) >= 3, f"Should have 3+ conditions, got {len(condition_list.conditions)}"
    print(f"   ✓ Conditions: {len(condition_list.conditions)}")
    for c in condition_list.conditions:
        print(f"      ({c['id']}) {c['text'][:50]}...")
    
    # Test 4: Logical operator
    print("\n4. Testing logical operator...")
    assert condition_list.logical_operator in ["AND", "OR"], f"Should have valid operator, got {condition_list.logical_operator}"
    print(f"   ✓ Logical operator: {condition_list.logical_operator}")
    
    print("\n✅ Condition Extractor tests PASSED")
    return True


def test_example_extractor():
    """Test the Example Extractor."""
    print("\n" + "="*70)
    print("TEST: Example Extractor")
    print("="*70)
    
    from app.services.ingestion.extractors.example_extractor import ExampleExtractor
    
    extractor = ExampleExtractor()
    
    text = """
    Example: Sarah earns £55,000 in the 2024-25 tax year.
    
    Step 1: Deduct the personal allowance
    £55,000 - £12,570 = £42,430 taxable income
    
    Step 2: Calculate tax at basic rate (£12,571 to £50,270)
    £37,700 × 20% = £7,540
    
    Step 3: Calculate tax at higher rate
    £4,730 × 40% = £1,892
    
    Total tax due: £9,432
    """
    
    # Test 1: Example detection
    print("\n1. Testing example detection...")
    assert extractor.has_examples(text), "Should detect examples"
    print("   ✓ Example detected")
    
    # Test 2: Example extraction
    print("\n2. Testing example extraction...")
    result = extractor.extract(None, text, "https://gov.uk/income-tax-rates", tax_year="2024-25")
    
    assert result.has_items, "Should extract examples"
    example = result.items[0]
    print(f"   ✓ Extracted: {example.example_name}")
    
    # Test 3: Scenario extraction
    print("\n3. Testing scenario extraction...")
    assert example.scenario is not None, "Should extract scenario"
    print(f"   ✓ Scenario: {example.scenario}")
    
    # Test 4: Steps extraction
    print("\n4. Testing steps extraction...")
    if example.steps:
        print(f"   ✓ Steps: {len(example.steps)}")
    else:
        print(f"   ⚠ No explicit steps extracted (may be in full_text)")
    
    # Test 5: Category
    print("\n5. Testing category...")
    print(f"   ✓ Category: {example.example_category}")
    
    print("\n✅ Example Extractor tests PASSED")
    return True


def test_reference_detector():
    """Test the Reference Detector."""
    print("\n" + "="*70)
    print("TEST: Reference Detector")
    print("="*70)
    
    from app.services.ingestion.extractors.reference_detector import ReferenceDetector
    
    detector = ReferenceDetector()
    
    text = """
    VAT Registration Requirements
    
    For detailed guidance, see VATREG02200 in the HMRC VAT Manual.
    
    The relevant legislation is the Value Added Tax Act 1994, section 3.
    
    See also CTM01500 for corporation tax implications.
    
    As explained in section 3.2 above, the threshold applies to taxable turnover.
    """
    
    html = """
    <p>For more information, see <a href="/guidance/vat-registration">VAT registration guidance</a>.</p>
    """
    
    # Test 1: Reference detection
    print("\n1. Testing reference detection...")
    assert detector.has_references(text), "Should detect references"
    print("   ✓ References detected")
    
    # Test 2: Reference extraction
    print("\n2. Testing reference extraction...")
    result = detector.extract(html, text, "https://gov.uk/vat")
    
    assert result.has_items, "Should extract references"
    print(f"   ✓ Extracted {len(result.items)} reference(s)")
    
    # Test 3: HMRC manual references
    print("\n3. Testing HMRC manual references...")
    hmrc_refs = [r for r in result.items if r.reference_type == 'hmrc_manual']
    assert len(hmrc_refs) >= 2, f"Should find 2+ HMRC refs, got {len(hmrc_refs)}"
    ref_texts = [r.reference_text for r in hmrc_refs]
    print(f"   ✓ HMRC refs: {ref_texts}")
    
    # Test 4: Legislation references
    print("\n4. Testing legislation references...")
    leg_refs = [r for r in result.items if r.reference_type == 'legislation']
    print(f"   ✓ Legislation refs: {[r.reference_text for r in leg_refs]}")
    
    # Test 5: Section references
    print("\n5. Testing section references...")
    sec_refs = [r for r in result.items if r.reference_type == 'section']
    print(f"   ✓ Section refs: {[r.reference_text for r in sec_refs]}")
    
    print("\n✅ Reference Detector tests PASSED")
    return True


def test_metadata_extractor():
    """Test the Metadata Extractor."""
    print("\n" + "="*70)
    print("TEST: Metadata Extractor")
    print("="*70)
    
    from app.services.ingestion.extractors.metadata_extractor import MetadataExtractor
    
    extractor = MetadataExtractor()
    
    text = """
    VAT Registration Guide 2024-25
    
    The VAT registration threshold is £90,000. If your taxable turnover exceeds 
    this threshold, you must register for VAT.
    
    For sole traders, the personal allowance is £12,570 for the 2024-25 tax year.
    
    You'll need to complete form VAT1 to register for VAT. For Self Assessment,
    use form SA100.
    
    The deadline for registration is 31 January following the tax year.
    """
    
    # Test 1: Threshold extraction
    print("\n1. Testing threshold extraction...")
    result = extractor.extract(None, text, "https://gov.uk/vat-registration")
    
    assert result.has_items, "Should extract metadata"
    metadata = result.items[0]
    
    assert len(metadata.thresholds) > 0, "Should extract thresholds"
    threshold_values = [t['value'] for t in metadata.thresholds]
    print(f"   ✓ Thresholds: {threshold_values}")
    
    # Test 2: Tax year extraction
    print("\n2. Testing tax year extraction...")
    assert "2024-25" in metadata.tax_years, f"Should find 2024-25, got {metadata.tax_years}"
    print(f"   ✓ Tax years: {metadata.tax_years}")
    
    # Test 3: Form extraction
    print("\n3. Testing form extraction...")
    form_codes = [f['code'] for f in metadata.forms]
    assert "VAT1" in form_codes, f"Should find VAT1, got {form_codes}"
    assert "SA100" in form_codes, f"Should find SA100, got {form_codes}"
    print(f"   ✓ Forms: {form_codes}")
    
    # Test 4: Key date extraction
    print("\n4. Testing key date extraction...")
    assert len(metadata.key_dates) > 0, "Should extract key dates"
    print(f"   ✓ Key dates: {[(d['day'], d['month']) for d in metadata.key_dates]}")
    
    # Test 5: Topic classification
    print("\n5. Testing topic classification...")
    assert len(metadata.topics) > 0, "Should classify topics"
    print(f"   ✓ Topics: {metadata.topics}")
    
    # Test 6: Business type identification
    print("\n6. Testing business type identification...")
    assert len(metadata.business_types) > 0, "Should identify business types"
    print(f"   ✓ Business types: {metadata.business_types}")
    
    # Test 7: Keyword extraction
    print("\n7. Testing keyword extraction...")
    assert len(metadata.keywords) > 0, "Should extract keywords"
    print(f"   ✓ Keywords: {metadata.keywords[:10]}...")  # First 10
    
    print("\n✅ Metadata Extractor tests PASSED")
    return True


def test_integration():
    """Test integration of all extractors."""
    print("\n" + "="*70)
    print("TEST: Integration - All Extractors Together")
    print("="*70)
    
    from app.services.ingestion.legal_chunker import LegalChunker, LegalChunkingConfig
    from app.services.ingestion.content_parser import ContentParser
    from app.services.ingestion.extractors import (
        TableExtractor, FormulaExtractor, DeadlineExtractor,
        ContactExtractor, ConditionExtractor, ExampleExtractor,
        ReferenceDetector, MetadataExtractor
    )
    
    # Comprehensive test document
    html = """
    <h1>VAT Registration Guide</h1>
    
    <h2>When to Register</h2>
    <p>You must register for VAT if any of the following apply:</p>
    <p>(a) your taxable turnover exceeds £90,000 in 12 months</p>
    <p>(b) you expect turnover to exceed £90,000 in the next 30 days</p>
    
    <h2>VAT Rates 2024-25</h2>
    <table>
        <thead>
            <tr><th>Type</th><th>Rate</th></tr>
        </thead>
        <tbody>
            <tr><td>Standard rate</td><td>20%</td></tr>
            <tr><td>Reduced rate</td><td>5%</td></tr>
            <tr><td>Zero rate</td><td>0%</td></tr>
        </tbody>
    </table>
    
    <h2>Example Calculation</h2>
    <p>Example: Sarah sells goods worth £10,000 at standard rate.</p>
    <p>VAT = £10,000 × 20% = £2,000</p>
    
    <h2>Deadlines</h2>
    <p>The deadline for VAT registration is within 30 days of exceeding the threshold.</p>
    <p>For more information, see VATREG02200 in the HMRC manual.</p>
    
    <h2>Contact</h2>
    <p>VAT Helpline: 0300 200 3700</p>
    """
    
    # Initialize all components
    parser = ContentParser()
    chunker = LegalChunker()
    table_extractor = TableExtractor()
    formula_extractor = FormulaExtractor()
    deadline_extractor = DeadlineExtractor()
    contact_extractor = ContactExtractor()
    condition_extractor = ConditionExtractor()
    example_extractor = ExampleExtractor()
    reference_detector = ReferenceDetector()
    metadata_extractor = MetadataExtractor()
    
    # Parse document
    print("\n1. Parsing document...")
    parsed = parser.parse(html, "VAT Registration Guide")
    print(f"   ✓ Parsed: {parsed.word_count} words, {len(parsed.sections)} sections")
    
    # Chunk document
    print("\n2. Chunking document...")
    chunks = chunker.chunk_document(parsed, "https://gov.uk/vat-registration", "VAT Registration Guide")
    print(f"   ✓ Created {len(chunks)} chunks")
    
    # Run all extractors
    print("\n3. Running extractors...")
    text_content = parsed.full_text
    source_url = "https://gov.uk/vat-registration"
    
    results = {
        'tables': table_extractor.extract(html, text_content, source_url),
        'formulas': formula_extractor.extract(html, text_content, source_url),
        'deadlines': deadline_extractor.extract(html, text_content, source_url),
        'contacts': contact_extractor.extract(html, text_content, source_url),
        'conditions': condition_extractor.extract(html, text_content, source_url),
        'examples': example_extractor.extract(html, text_content, source_url),
        'references': reference_detector.extract(html, text_content, source_url),
        'metadata': metadata_extractor.extract(html, text_content, source_url),
    }
    
    # Print summary
    print("\n4. Extraction Summary:")
    for name, result in results.items():
        count = len(result.items) if result.items else 0
        status = "✓" if count > 0 else "○"
        print(f"   {status} {name}: {count} item(s)")
    
    # Verify at least some content was extracted
    total_items = sum(len(r.items) for r in results.values())
    assert total_items > 5, f"Should extract at least 5 items total, got {total_items}"
    
    print(f"\n   Total items extracted: {total_items}")
    print("\n✅ Integration test PASSED")
    return True


def run_all_tests():
    """Run all Phase 2 tests."""
    print("\n" + "="*70)
    print("PHASE 2 DOCUMENT INGESTION - TEST SUITE")
    print("="*70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("Legal Chunker", test_legal_chunker),
        ("Table Extractor", test_table_extractor),
        ("Formula Extractor", test_formula_extractor),
        ("Deadline Extractor", test_deadline_extractor),
        ("Contact Extractor", test_contact_extractor),
        ("Condition Extractor", test_condition_extractor),
        ("Example Extractor", test_example_extractor),
        ("Reference Detector", test_reference_detector),
        ("Metadata Extractor", test_metadata_extractor),
        ("Integration", test_integration),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ {name} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ {name} ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    # Final summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 ALL PHASE 2 TESTS PASSED! 🎉")
        print("\nPhase 2 Document Ingestion is ready for integration.")
        return True
    else:
        print(f"\n⚠️ {failed} test(s) failed. Please review the errors above.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
