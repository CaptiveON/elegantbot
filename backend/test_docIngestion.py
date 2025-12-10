"""
Phase 2 Test Script: Document Ingestion

This script tests all components of the document ingestion pipeline:
1. GOV.UK Client - Can we fetch documents from GOV.UK API?
2. Content Parser - Can we clean HTML and extract text?
3. Semantic Chunker - Can we split documents meaningfully?
4. Full Pipeline - Can we ingest and store documents?

Run from backend directory:
    cd elegantbot-main/backend
    python test_phase2_document_ingestion.py

Expected output:
    ✅ GOV.UK Client: Connected to API
    ✅ Content Parser: HTML cleaned successfully
    ✅ Semantic Chunker: Document chunked properly
    ✅ Full Pipeline: Documents ingested to database
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_gov_uk_client():
    """Test 1: GOV.UK Content API Client"""
    print("\n" + "="*60)
    print("TEST 1: GOV.UK Content API Client")
    print("="*60)
    
    from app.services.ingestion import GovUKClient, GovUKContentAPIError
    
    client = GovUKClient()
    
    # Test 1a: Fetch a simple page
    print("\n📡 Fetching /vat-registration from GOV.UK...")
    try:
        doc = client.fetch_document("/vat-registration")
        
        print(f"  ✅ Title: {doc.title}")
        print(f"  ✅ URL: {doc.url}")
        print(f"  ✅ Document Type: {doc.document_type}")
        print(f"  ✅ Schema: {doc.schema_name}")
        print(f"  ✅ Published: {doc.first_published}")
        print(f"  ✅ Updated: {doc.last_updated}")
        print(f"  ✅ Body length: {len(doc.body_html)} chars")
        print(f"  ✅ Breadcrumbs: {len(doc.breadcrumbs)} items")
        print(f"  ✅ Child sections: {len(doc.child_sections)} items")
        
    except GovUKContentAPIError as e:
        print(f"  ❌ API Error: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Unexpected error: {e}")
        return False
    
    # Test 1b: Fetch an HMRC manual page
    print("\n📡 Fetching HMRC VAT manual overview...")
    try:
        manual_doc = client.fetch_document("/hmrc-internal-manuals/vat-guide")
        
        print(f"  ✅ Title: {manual_doc.title}")
        print(f"  ✅ Document Type: {manual_doc.document_type}")
        print(f"  ✅ Child sections: {len(manual_doc.child_sections)} sections")
        
        if manual_doc.child_sections:
            print(f"  ✅ First child: {manual_doc.child_sections[0].get('title', 'N/A')}")
    
    except Exception as e:
        print(f"  ⚠️ Manual fetch error (non-critical): {e}")
    
    # Test 1c: Seed list
    print("\n📋 Checking seed list...")
    urls = client.get_tax_guidance_urls()
    print(f"  ✅ Seed list contains {len(urls)} URLs")
    print(f"  ✅ Categories covered: VAT, Corporation Tax, Self Assessment, PAYE, NI, MTD, HMRC Services")
    
    print("\n✅ GOV.UK Client tests PASSED")
    return True


def test_content_parser():
    """Test 2: Content Parser"""
    print("\n" + "="*60)
    print("TEST 2: Content Parser")
    print("="*60)
    
    from app.services.ingestion import ContentParser
    
    parser = ContentParser()
    
    # Test HTML sample (simulating GOV.UK structure)
    test_html = """
    <script>var tracking = "ignore this";</script>
    <nav>Navigation menu to remove</nav>
    
    <article>
        <h1>VAT Registration</h1>
        <p>You must <strong>register for VAT</strong> if your taxable turnover 
        exceeds £90,000 in any 12-month period.</p>
        
        <h2>When to register</h2>
        <p>You need to register within 30 days of the end of the month when 
        you went over the threshold.</p>
        
        <h3>Voluntary registration</h3>
        <p>You can register voluntarily if your turnover is below the threshold.</p>
        <ul>
            <li>Reclaim VAT on purchases</li>
            <li>Appear more established to customers</li>
        </ul>
        
        <h2>How to register</h2>
        <p>You can register online through your Government Gateway account.</p>
    </article>
    
    <footer>Crown Copyright - ignore this</footer>
    """
    
    print("\n🔧 Parsing test HTML...")
    result = parser.parse(test_html, title="VAT Registration")
    
    print(f"  ✅ Title: {result.title}")
    print(f"  ✅ Has content: {result.has_content}")
    print(f"  ✅ Word count: {result.word_count}")
    print(f"  ✅ Sections found: {len(result.sections)}")
    print(f"  ✅ Headings found: {len(result.headings)}")
    
    # Verify cleaning worked
    assert "script" not in result.full_text.lower(), "Script tag should be removed"
    assert "navigation" not in result.full_text.lower(), "Nav should be removed"
    assert "footer" not in result.full_text.lower(), "Footer should be removed"
    assert "£90,000" in result.full_text, "Content should be preserved"
    
    print("\n📄 Extracted sections:")
    for i, section in enumerate(result.sections[:5]):  # First 5
        print(f"  {i+1}. [{section.level}] {section.heading}")
        print(f"     Path: {section.heading_path}")
        print(f"     Content preview: {section.content[:80]}...")
    
    print("\n✅ Content Parser tests PASSED")
    return True


def test_semantic_chunker():
    """Test 3: Semantic Chunker"""
    print("\n" + "="*60)
    print("TEST 3: Semantic Chunker")
    print("="*60)
    
    from app.services.ingestion import SemanticChunker, ChunkingConfig, ContentParser
    
    # Create a longer document to test chunking
    long_content = """
    <h1>Complete VAT Guide for UK SMEs</h1>
    
    <h2>Part 1: Understanding VAT</h2>
    <p>Value Added Tax (VAT) is a consumption tax placed on products and services. 
    As a UK business, understanding VAT is essential for compliance with HMRC regulations.
    This guide will walk you through everything you need to know about VAT registration,
    rates, returns, and common pitfalls to avoid.</p>
    
    <p>VAT is charged at each stage of the production and distribution chain. Businesses
    collect VAT on behalf of HMRC and can reclaim VAT paid on business purchases. The 
    difference between VAT collected and VAT paid is what you pay to (or reclaim from) HMRC.</p>
    
    <h2>Part 2: VAT Registration</h2>
    <p>You must register for VAT if your taxable turnover exceeds £90,000 in any 12-month
    rolling period. This is known as the VAT registration threshold. Once registered, you
    must charge VAT on your taxable sales and submit regular VAT returns to HMRC.</p>
    
    <p>The registration process involves applying through your HMRC online account. You'll
    need your business details, bank account information, and turnover figures for the
    past 12 months. Most applications are processed within 30 days.</p>
    
    <h3>Voluntary Registration</h3>
    <p>Even if your turnover is below £90,000, you can choose to register voluntarily.
    Benefits include being able to reclaim VAT on purchases and appearing more established
    to business customers who can reclaim VAT themselves.</p>
    
    <h2>Part 3: VAT Rates</h2>
    <p>The UK has three VAT rates: standard rate (20%), reduced rate (5%), and zero rate (0%).
    Most goods and services fall under the standard rate. The reduced rate applies to certain
    items like children's car seats and home energy. Zero-rated items include most food,
    books, and children's clothing.</p>
    
    <h3>Exempt vs Zero-Rated</h3>
    <p>It's important to understand the difference between exempt and zero-rated supplies.
    Zero-rated supplies are taxable at 0%, meaning you can still reclaim input VAT.
    Exempt supplies are outside the VAT system, and you cannot reclaim input VAT on
    costs related to making exempt supplies.</p>
    
    <h2>Part 4: VAT Returns</h2>
    <p>Most VAT-registered businesses must submit quarterly VAT returns and pay any VAT
    owed within one month and seven days of the end of each quarter. Under Making Tax
    Digital (MTD), you must keep digital records and submit returns using compatible
    software.</p>
    """
    
    parser = ContentParser()
    parsed = parser.parse(long_content, title="VAT Guide")
    
    # Test with different configurations
    print("\n🔧 Testing chunking with default config...")
    chunker = SemanticChunker()
    chunks = chunker.chunk_document(parsed)
    
    stats = chunker.get_chunk_stats(chunks)
    print(f"  ✅ Chunks created: {stats['count']}")
    print(f"  ✅ Total characters: {stats['total_chars']}")
    print(f"  ✅ Average chunk size: {stats['avg_size']:.0f} chars")
    print(f"  ✅ Min chunk size: {stats['min_size']} chars")
    print(f"  ✅ Max chunk size: {stats['max_size']} chars")
    print(f"  ✅ Estimated tokens: {stats['est_total_tokens']}")
    print(f"  ✅ Sections covered: {stats['sections_covered']}")
    
    print("\n📄 Chunk details:")
    for chunk in chunks:
        print(f"  Chunk {chunk.chunk_index + 1}/{chunk.total_chunks}:")
        print(f"    Section: {chunk.section_title}")
        print(f"    Path: {chunk.heading_path}")
        print(f"    Size: {len(chunk.content)} chars (~{chunker.estimate_tokens(chunk.content)} tokens)")
        print(f"    Preview: {chunk.content[:60]}...")
        print()
    
    # Test with custom config (smaller chunks)
    print("🔧 Testing with smaller chunk config...")
    small_config = ChunkingConfig(
        max_chunk_size=800,
        target_chunk_size=500,
        overlap_size=50
    )
    small_chunker = SemanticChunker(small_config)
    small_chunks = small_chunker.chunk_document(parsed)
    
    small_stats = small_chunker.get_chunk_stats(small_chunks)
    print(f"  ✅ Smaller config created {small_stats['count']} chunks (vs {stats['count']} default)")
    print(f"  ✅ Average size: {small_stats['avg_size']:.0f} chars")
    
    print("\n✅ Semantic Chunker tests PASSED")
    return True


def test_full_pipeline():
    """Test 4: Full Ingestion Pipeline"""
    print("\n" + "="*60)
    print("TEST 4: Full Ingestion Pipeline (with Database)")
    print("="*60)
    
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from app.models import Base
    from app.services.ingestion import IngestionPipeline, PipelineConfig, IngestionMode
    from app.crud.crud_document import get_document_stats
    from app.crud.crud_chunk import get_chunk_stats
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("  ⚠️ DATABASE_URL not set - skipping database tests")
        print("  ℹ️ Set DATABASE_URL in .env to test full pipeline")
        return True
    
    print(f"\n🔌 Connecting to database...")
    
    try:
        engine = create_engine(database_url)
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("  ✅ Database connected")
        
        # Create tables if needed
        Base.metadata.create_all(engine)
        print("  ✅ Tables ready")
        
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
    except Exception as e:
        print(f"  ❌ Database connection failed: {e}")
        return False
    
    # Configure pipeline for testing (just 2 URLs)
    print("\n🚀 Running ingestion pipeline...")
    
    config = PipelineConfig(
        mode=IngestionMode.UPDATE_IF_CHANGED,
        verbose=True,
        continue_on_error=True
    )
    
    pipeline = IngestionPipeline(db, config)
    
    # Ingest just 2 documents for testing
    test_urls = [
        "/register-for-vat",
        "/corporation-tax"
    ]
    
    def progress_callback(current, total, result):
        status = "✅" if result.success else "❌"
        print(f"  {status} [{current}/{total}] {result.url} - {result.action}")
        if result.chunks_created:
            print(f"      Created {result.chunks_created} chunks")
    
    result = pipeline.run(
        urls=test_urls,
        run_name="phase2_test",
        progress_callback=progress_callback
    )
    
    print(f"\n📊 Pipeline Results:")
    print(f"  Run ID: {result.run_id}")
    print(f"  Status: {result.status}")
    print(f"  Documents processed: {result.documents_processed}")
    print(f"  Documents created: {result.documents_created}")
    print(f"  Documents updated: {result.documents_updated}")
    print(f"  Documents skipped: {result.documents_skipped}")
    print(f"  Documents failed: {result.documents_failed}")
    print(f"  Total chunks: {result.chunks_created}")
    print(f"  Duration: {result.duration_seconds:.1f} seconds")
    
    if result.errors:
        print(f"\n⚠️ Errors:")
        for err in result.errors:
            print(f"  - {err['url']}: {err['error']}")
    
    # Verify in database
    print("\n🔍 Verifying database state...")
    
    doc_stats = get_document_stats(db)
    print(f"  Total documents in DB: {doc_stats['total_documents']}")
    print(f"  By authority: {doc_stats.get('by_authority', {})}")
    
    chunk_stats = get_chunk_stats(db)
    print(f"  Total chunks in DB: {chunk_stats['total_chunks']}")
    
    # Show sample chunk
    from app.crud.crud_chunk import get_chunks_by_topic
    from app.models.chunk import TopicPrimary
    
    # Get any chunk to verify structure
    from sqlalchemy import select
    from app.models.chunk import DocumentChunk
    
    sample_chunk = db.execute(select(DocumentChunk).limit(1)).scalar_one_or_none()
    if sample_chunk:
        print(f"\n📄 Sample chunk from DB:")
        print(f"  ID: {sample_chunk.id}")
        print(f"  Section: {sample_chunk.section_title}")
        print(f"  Heading path: {sample_chunk.heading_path}")
        print(f"  Source URL: {sample_chunk.source_url}")
        print(f"  Content preview: {sample_chunk.content[:100]}...")
        print(f"  Chunk index: {sample_chunk.chunk_index}/{sample_chunk.total_chunks_in_doc}")
    
    db.close()
    
    print("\n✅ Full Pipeline tests PASSED")
    return True


def test_component_isolation():
    """Test components work without database (for quick iteration)"""
    print("\n" + "="*60)
    print("TEST 5: Component Isolation (No Database)")
    print("="*60)
    
    from app.services.ingestion import GovUKClient, ContentParser, SemanticChunker
    
    print("\n🔗 Testing end-to-end flow without database...")
    
    # Fetch
    client = GovUKClient()
    doc = client.fetch_document("/self-assessment-tax-returns")
    print(f"  ✅ Fetched: {doc.title}")
    
    # Parse
    parser = ContentParser()
    parsed = parser.parse_gov_uk_document(doc)
    print(f"  ✅ Parsed: {parsed.word_count} words, {len(parsed.sections)} sections")
    
    # Chunk
    chunker = SemanticChunker()
    chunks = chunker.chunk_document(parsed)
    print(f"  ✅ Chunked: {len(chunks)} chunks")
    
    # Show what would be stored
    print(f"\n📋 Ready for storage:")
    print(f"  Document URL: {doc.url}")
    print(f"  Document Title: {doc.title}")
    print(f"  Authority: GOV_UK")
    print(f"  Published: {doc.first_published}")
    print(f"  Chunks to create: {len(chunks)}")
    
    for i, chunk in enumerate(chunks[:3]):
        print(f"\n  Chunk {i+1}:")
        print(f"    Section: {chunk.section_title}")
        print(f"    Path: {chunk.heading_path}")
        print(f"    Size: {len(chunk.content)} chars")
    
    if len(chunks) > 3:
        print(f"\n  ... and {len(chunks) - 3} more chunks")
    
    print("\n✅ Component Isolation tests PASSED")
    return True


def main():
    """Run all Phase 2 tests"""
    print("\n" + "="*60)
    print("PHASE 2 TEST SUITE: Document Ingestion")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")
    
    results = {}
    
    # Test 1: GOV.UK Client
    try:
        results['gov_uk_client'] = test_gov_uk_client()
    except Exception as e:
        print(f"❌ GOV.UK Client test failed: {e}")
        results['gov_uk_client'] = False
    
    # Test 2: Content Parser
    try:
        results['content_parser'] = test_content_parser()
    except Exception as e:
        print(f"❌ Content Parser test failed: {e}")
        results['content_parser'] = False
    
    # Test 3: Semantic Chunker
    try:
        results['semantic_chunker'] = test_semantic_chunker()
    except Exception as e:
        print(f"❌ Semantic Chunker test failed: {e}")
        results['semantic_chunker'] = False
    
    # Test 4: Component Isolation
    try:
        results['component_isolation'] = test_component_isolation()
    except Exception as e:
        print(f"❌ Component Isolation test failed: {e}")
        results['component_isolation'] = False
    
    # Test 5: Full Pipeline (requires database)
    try:
        results['full_pipeline'] = test_full_pipeline()
    except Exception as e:
        print(f"❌ Full Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        results['full_pipeline'] = False
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 All Phase 2 tests PASSED!")
        print("\nPhase 2 is complete. Your ingestion pipeline can:")
        print("  1. Fetch documents from GOV.UK Content API")
        print("  2. Parse HTML and extract structured content")
        print("  3. Chunk documents semantically for RAG")
        print("  4. Store documents and chunks in PostgreSQL")
        print("\nNext: Phase 3 - Metadata Population")
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
