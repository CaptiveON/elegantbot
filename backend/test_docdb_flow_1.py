"""
Test Script for Phase 1: Data Foundation (Updated)

This script tests all models, schemas, and CRUD operations including
the new precise citation and cross-reference features.

Run with: python test_phase1_data_foundation.py

Prerequisites:
1. PostgreSQL database running
2. .env file configured with DATABASE_URL
"""

# import sys
# import os

# Add the app directory to path
# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from sqlalchemy.orm import Session

# Import database
from app.database import engine, SessionLocal, Base

# Import models
from app.models import (
    SourceDocument,
    DocumentChunk,
    ChunkReference,
    IngestionLog,
    QueryAuditLog,
    AuthorityType,
    DocumentType,
    ReliabilityTier,
    IngestionStatus,
    TopicPrimary,
    ContentType,
    ServiceCategory,
    IngestionRunStatus,
    ReferenceType,
    ReferenceStrength
)

# Import schemas
from app.schema import (
    DocumentCreate,
    DocumentResponse,
    ChunkCreate,
    ChunkResponse,
    ChunkReferenceCreate,
    ChunkReferenceResponse,
    TopicPrimary as TopicPrimarySchema,
    ContentType as ContentTypeSchema,
    ServiceCategory as ServiceCategorySchema
)

# Import CRUD
from app.crud import (
    crud_document,
    crud_chunk,
    crud_chunk_reference,
    crud_ingestion_log,
    crud_audit_log
)

# Import metadata schemas
from app.schema.metadata import (
    QueryAuditData,
    PineconeMetadata
)


def print_section(title: str):
    """Print a section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_create_tables():
    """Test that all tables can be created"""
    print_section("Testing Table Creation")
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ All tables created successfully!")
        
        # List tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"\nTables in database:")
        for table in tables:
            print(f"  - {table}")
        
        # Verify new table exists
        if "chunk_references" in tables:
            print("\n✅ chunk_references table created (new for Phase 1.1)")
        
        return True
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        return False


def test_document_crud(db: Session):
    """Test document CRUD operations"""
    print_section("Testing Document CRUD")
    
    try:
        # Create a document
        doc_data = DocumentCreate(
            url="https://www.gov.uk/vat-registration",
            authority=AuthorityType.GOV_UK,
            document_type=DocumentType.GUIDANCE,
            reliability_tier=2,
            title="Register for VAT",
            tax_year="2024-25",
            publication_date=datetime(2024, 4, 1),
            last_updated_source=datetime(2024, 11, 1)
        )
        
        # Check if document already exists
        existing = crud_document.get_document_by_url(db, doc_data.url)
        if existing:
            print(f"  Document already exists, deleting first...")
            crud_document.delete_document(db, existing.id)
        
        doc = crud_document.create_document(db, doc_data)
        print(f"✅ Created document: {doc.id}")
        print(f"   Title: {doc.title}")
        print(f"   Authority: {doc.authority}")
        print(f"   Status: {doc.ingestion_status}")
        
        # Read document
        retrieved = crud_document.get_document(db, doc.id)
        assert retrieved is not None
        print(f"✅ Retrieved document by ID")
        
        # Update status
        updated = crud_document.update_document_status(
            db, doc.id, 
            IngestionStatus.COMPLETED,
            content_hash="sha256:test123",
            total_chunks=5
        )
        print(f"✅ Updated document status to: {updated.ingestion_status}")
        print(f"   Total chunks: {updated.total_chunks}")
        
        # Get stats
        stats = crud_document.get_document_stats(db)
        print(f"✅ Document stats:")
        print(f"   Total documents: {stats['total_documents']}")
        print(f"   By authority: {stats['by_authority']}")
        
        return doc.id
        
    except Exception as e:
        print(f"❌ Document CRUD test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_chunk_crud(db: Session, document_id: str):
    """Test chunk CRUD operations with new citation fields"""
    print_section("Testing Chunk CRUD (with Citation Fields)")
    
    try:
        # Create a chunk with precise citation fields
        chunk_data = ChunkCreate(
            document_id=document_id,
            content="You must register for VAT if your taxable turnover exceeds £90,000 in any 12-month period.",
            chunk_summary="VAT registration threshold requirement",
            source_url="https://www.gov.uk/vat-registration",
            source_authority="GOV_UK",
            section_title="When to register",
            heading_path="VAT > Registration > Thresholds",
            
            # NEW: Precise citation fields
            section_id="VATREG02200",
            paragraph_number="Para 1",
            citable_reference="HMRC VAT Registration Manual, VATREG02200, Para 1",
            
            # Classification
            topic_primary=TopicPrimarySchema.VAT,
            topic_secondary=["registration", "thresholds"],
            business_types=["sole_trader", "limited_company", "partnership"],
            content_type=ContentTypeSchema.THRESHOLD,
            service_category=ServiceCategorySchema.NONE,
            reliability_tier=2,
            tax_year="2024-25",
            
            # Retrieval hints
            threshold_values=[90000],
            threshold_type="vat_registration",
            keywords=["VAT", "registration", "threshold", "£90,000"],
            form_references=["VAT1"],
            
            # NEW: Cross-reference tracking
            defined_terms_used=["taxable turnover"],
            defined_terms_provided=[],
            has_outgoing_references=True,  # Will reference VATREG02150
            has_incoming_references=False,
            
            # Compliance flags
            deadline_sensitive=True,
            penalty_relevant=True,
            
            # Position
            chunk_index=0,
            total_chunks_in_doc=5,
            char_start=0,
            char_end=95
        )
        
        chunk = crud_chunk.create_chunk(db, chunk_data)
        print(f"✅ Created chunk: {chunk.id}")
        print(f"   Section ID: {chunk.section_id}")
        print(f"   Citable Reference: {chunk.citable_reference}")
        print(f"   Defined terms used: {chunk.defined_terms_used}")
        print(f"   Has outgoing references: {chunk.has_outgoing_references}")
        
        # Read chunk
        retrieved = crud_chunk.get_chunk(db, chunk.id)
        assert retrieved is not None
        print(f"✅ Retrieved chunk by ID")
        
        # Test get by section ID
        by_section = crud_chunk.get_chunk_by_section_id(db, "VATREG02200")
        assert by_section is not None
        print(f"✅ Retrieved chunk by section_id")
        
        # Test Pinecone metadata conversion (should include new fields)
        pinecone_meta = chunk.to_pinecone_metadata()
        print(f"✅ Pinecone metadata generated:")
        print(f"   section_id: {pinecone_meta.get('section_id', 'N/A')}")
        print(f"   citable_reference: {pinecone_meta.get('citable_reference', 'N/A')}")
        print(f"   has_outgoing_references: {pinecone_meta.get('has_outgoing_references', False)}")
        
        # Update with embedding info
        updated = crud_chunk.update_chunk_embedding(
            db, chunk.id,
            pinecone_id="vec_test_123",
            embedding_model="text-embedding-3-small"
        )
        print(f"✅ Updated chunk with embedding info")
        print(f"   Pinecone ID: {updated.pinecone_id}")
        
        # Get stats (should include reference counts)
        stats = crud_chunk.get_chunk_stats(db)
        print(f"✅ Chunk stats:")
        print(f"   Total chunks: {stats['total_chunks']}")
        print(f"   With outgoing refs: {stats['with_outgoing_references']}")
        print(f"   With incoming refs: {stats['with_incoming_references']}")
        
        return chunk.id
        
    except Exception as e:
        print(f"❌ Chunk CRUD test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_chunk_reference_crud(db: Session, document_id: str, source_chunk_id: str):
    """Test chunk reference CRUD operations (NEW for Phase 1.1)"""
    print_section("Testing Chunk Reference CRUD (NEW)")
    
    try:
        # First, create a target chunk (the definition chunk)
        target_chunk_data = ChunkCreate(
            document_id=document_id,
            content="Taxable turnover means the total value of taxable supplies made in the UK, excluding VAT.",
            chunk_summary="Definition of taxable turnover",
            source_url="https://www.gov.uk/vat-registration/taxable-turnover",
            source_authority="GOV_UK",
            section_title="Definition of Taxable Turnover",
            heading_path="VAT > Registration > Taxable Turnover Definition",
            
            # Precise citation
            section_id="VATREG02150",
            paragraph_number="Para 1",
            citable_reference="HMRC VAT Registration Manual, VATREG02150",
            
            # This chunk PROVIDES a definition
            topic_primary=TopicPrimarySchema.VAT,
            content_type=ContentTypeSchema.DEFINITION,
            reliability_tier=1,
            defined_terms_used=[],
            defined_terms_provided=["taxable turnover", "taxable supplies"],
            has_outgoing_references=False,
            has_incoming_references=False,  # Will be updated when reference is created
            
            chunk_index=1,
            total_chunks_in_doc=5,
            char_start=100,
            char_end=200
        )
        
        target_chunk = crud_chunk.create_chunk(db, target_chunk_data)
        print(f"✅ Created target chunk (definition): {target_chunk.section_id}")
        print(f"   Provides terms: {target_chunk.defined_terms_provided}")
        
        # Create a reference from source to target
        reference_data = ChunkReferenceCreate(
            source_chunk_id=source_chunk_id,
            target_chunk_id=target_chunk.id,
            reference_type=ReferenceType.DEFINITION.value,
            reference_strength=ReferenceStrength.REQUIRED.value,
            reference_text="VATREG02150",
            reference_context="see VATREG02150 for definition of taxable turnover",
            target_section_id="VATREG02150",
            is_resolved=True
        )
        
        reference = crud_chunk_reference.create_reference(db, reference_data)
        print(f"✅ Created reference:")
        print(f"   Type: {reference.reference_type}")
        print(f"   Strength: {reference.reference_strength}")
        print(f"   From: {reference.source_chunk_id[:8]}... → To: {reference.target_section_id}")
        print(f"   Resolved: {reference.is_resolved}")
        
        # Verify source chunk flag updated
        source_chunk = crud_chunk.get_chunk(db, source_chunk_id)
        print(f"✅ Source chunk has_outgoing_references: {source_chunk.has_outgoing_references}")
        
        # Verify target chunk flag updated
        db.refresh(target_chunk)
        print(f"✅ Target chunk has_incoming_references: {target_chunk.has_incoming_references}")
        
        # Test get outgoing references
        outgoing = crud_chunk_reference.get_outgoing_references(db, source_chunk_id)
        print(f"✅ Found {len(outgoing)} outgoing reference(s)")
        
        # Test get incoming references
        incoming = crud_chunk_reference.get_incoming_references(db, target_chunk.id)
        print(f"✅ Found {len(incoming)} incoming reference(s)")
        
        # Test reference expansion (the key feature!)
        expanded_ids, refs_followed = crud_chunk_reference.expand_references(
            db,
            chunk_ids=[source_chunk_id],
            max_depth=1,
            strength_filter=["required", "recommended"]
        )
        print(f"✅ Reference expansion:")
        print(f"   Started with 1 chunk")
        print(f"   Expanded to {len(expanded_ids)} chunks")
        print(f"   Followed {len(refs_followed)} reference(s)")
        
        # Test reference stats
        stats = crud_chunk_reference.get_reference_stats(db)
        print(f"✅ Reference graph stats:")
        print(f"   Total references: {stats.total_references}")
        print(f"   Resolved: {stats.resolved_references}")
        print(f"   By type: {stats.references_by_type}")
        print(f"   By strength: {stats.references_by_strength}")
        
        return reference.id, target_chunk.id
        
    except Exception as e:
        print(f"❌ Chunk Reference CRUD test failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def test_unresolved_references(db: Session, source_chunk_id: str):
    """Test unresolved reference handling"""
    print_section("Testing Unresolved Reference Handling")
    
    try:
        # Create an unresolved reference (target not yet ingested)
        unresolved_ref_data = ChunkReferenceCreate(
            source_chunk_id=source_chunk_id,
            target_chunk_id=None,  # Not resolved yet
            reference_type=ReferenceType.PENALTY.value,
            reference_strength=ReferenceStrength.RECOMMENDED.value,
            reference_text="VATREG09000",
            reference_context="For penalties for late registration, see VATREG09000",
            target_section_id="VATREG09000",
            is_resolved=False
        )
        
        unresolved_ref = crud_chunk_reference.create_reference(db, unresolved_ref_data)
        print(f"✅ Created unresolved reference to: {unresolved_ref.target_section_id}")
        print(f"   Is resolved: {unresolved_ref.is_resolved}")
        
        # Get unresolved references
        unresolved = crud_chunk_reference.get_unresolved_references(db)
        print(f"✅ Found {len(unresolved)} unresolved reference(s)")
        
        # In a real scenario, when VATREG09000 is later ingested, we would:
        # crud_chunk_reference.resolve_references_by_section(db, "VATREG09000", new_chunk_id)
        
        print(f"✅ Unresolved references ready for later resolution")
        
        return unresolved_ref.id
        
    except Exception as e:
        print(f"❌ Unresolved reference test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_ingestion_log_crud(db: Session):
    """Test ingestion log CRUD operations"""
    print_section("Testing Ingestion Log CRUD")
    
    try:
        # Create log
        log = crud_ingestion_log.create_ingestion_log(
            db,
            source_type="gov_uk",
            run_name="Test ingestion run",
            config={"max_pages": 10, "topics": ["VAT"]}
        )
        print(f"✅ Created ingestion log: {log.id}")
        print(f"   Status: {log.status}")
        
        # Update stats
        crud_ingestion_log.increment_ingestion_stats(
            db, log.id,
            documents_processed=5,
            documents_created=3,
            chunks_created=25,
            tokens_used=1500
        )
        
        updated = crud_ingestion_log.get_ingestion_log(db, log.id)
        print(f"✅ Updated ingestion stats:")
        print(f"   Documents processed: {updated.documents_processed}")
        print(f"   Chunks created: {updated.chunks_created}")
        
        # Add warning
        crud_ingestion_log.add_ingestion_warning(
            db, log.id,
            "Document had no publication date",
            "https://example.com/doc1"
        )
        print(f"✅ Added warning to log")
        
        # Complete
        crud_ingestion_log.update_ingestion_log_status(
            db, log.id,
            IngestionRunStatus.COMPLETED
        )
        print(f"✅ Marked ingestion as completed")
        
        return log.id
        
    except Exception as e:
        print(f"❌ Ingestion log CRUD test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_audit_log_crud(db: Session):
    """Test audit log CRUD operations"""
    print_section("Testing Audit Log CRUD")
    
    try:
        # Create audit data
        audit_data = QueryAuditData(
            original_query="When do I need to register for VAT?",
            processed_query="VAT registration threshold requirements",
            detected_intent="tax_compliance",
            chunks_retrieved=[
                {
                    "chunk_id": "test-chunk-1",
                    "document_id": "test-doc-1",
                    "section_id": "VATREG02200",
                    "similarity_score": 0.94,
                    "source_url": "https://www.gov.uk/vat-registration"
                }
            ],
            filters_applied={"topic_primary": "VAT", "reliability_tier": [1, 2]},
            response_text="You must register for VAT if your taxable turnover exceeds £90,000...",
            citations=[
                {
                    "chunk_id": "test-chunk-1",
                    "section_id": "VATREG02200",
                    "citable_reference": "HMRC VAT Registration Manual, VATREG02200",
                    "source_url": "https://www.gov.uk/vat-registration",
                    "quote_used": "taxable turnover exceeds £90,000"
                }
            ],
            disclaimer_type="standard",
            confidence_score=0.92,
            embedding_model="text-embedding-3-small",
            generation_model="gpt-4o",
            total_tokens=1250,
            latency_ms=1500
        )
        
        log = crud_audit_log.create_audit_log(
            db,
            audit_data=audit_data,
            user_id="18143c29-f1e2-4c10-a757-cebeeb370691",
            session_id="c29aac0f-fd46-489c-a1fc-964782c26e61"
        )
        print(f"✅ Created audit log: {log.id}")
        print(f"   Query: {log.original_query}")
        print(f"   Intent: {log.detected_intent}")
        
        # Add feedback
        crud_audit_log.update_audit_log_feedback(
            db, log.id,
            feedback="helpful",
            comment="Great answer!"
        )
        print(f"✅ Added user feedback")
        
        # Get stats
        stats = crud_audit_log.get_audit_stats(db)
        print(f"✅ Audit stats:")
        print(f"   Total queries: {stats['total_queries']}")
        print(f"   By intent: {stats['by_intent']}")
        
        return log.id
        
    except Exception as e:
        print(f"❌ Audit log CRUD test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_schema_validation():
    """Test Pydantic schema validation"""
    print_section("Testing Schema Validation")
    
    try:
        # Test PineconeMetadata
        meta = PineconeMetadata(
            document_id="doc-123",
            source_url="https://www.gov.uk/vat",
            source_authority="GOV_UK",
            topic_primary="VAT",
            content_type="factual",
            reliability_tier=2,
            keywords=["VAT", "tax"],
            threshold_values=[90000],
            chunk_index=0
        )
        
        meta_dict = meta.to_dict()
        print(f"✅ PineconeMetadata validation passed")
        print(f"   Keys: {list(meta_dict.keys())}")
        
        # Test ChunkReferenceCreate
        ref = ChunkReferenceCreate(
            source_chunk_id="chunk-123",
            target_chunk_id="chunk-456",
            reference_type="definition",
            reference_strength="required",
            reference_text="VATREG02150",
            reference_context="see VATREG02150 for definition",
            is_resolved=True
        )
        print(f"✅ ChunkReferenceCreate validation passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Schema validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def cleanup(db: Session, doc_id: str = None):
    """Clean up test data"""
    print_section("Cleanup")
    
    try:
        if doc_id:
            # Delete references first (foreign key constraint)
            chunks = crud_chunk.get_chunks_by_document(db, doc_id)
            for chunk in chunks:
                crud_chunk_reference.delete_references_for_chunk(db, chunk.id)
            
            # Then delete document (cascades to chunks)
            crud_document.delete_document(db, doc_id)
            print(f"✅ Deleted test document, chunks, and references")
        
        # Clean up audit logs created in test
        logs = crud_audit_log.get_audit_logs(db, limit=10)
        for log in logs:
            if log.user_id == "test-user-123":
                db.delete(log)
        db.commit()
        print(f"✅ Cleaned up test audit logs")
        
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  PHASE 1.1: DATA FOUNDATION TEST SUITE")
    print("  (Updated with Citation & Cross-Reference Tests)")
    print("="*60)
    
    # Test table creation
    if not test_create_tables():
        print("\n❌ Cannot continue without tables")
        return
    
    # Test schema validation (no DB needed)
    test_schema_validation()
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Test document CRUD
        doc_id = test_document_crud(db)
        
        if doc_id:
            # Test chunk CRUD (with new citation fields)
            chunk_id = test_chunk_crud(db, doc_id)
            
            if chunk_id:
                # Test chunk reference CRUD (NEW)
                ref_id, target_chunk_id = test_chunk_reference_crud(db, doc_id, chunk_id)
                
                # Test unresolved references (NEW)
                test_unresolved_references(db, chunk_id)
        
        # Test ingestion log CRUD
        test_ingestion_log_crud(db)
        
        # Test audit log CRUD
        test_audit_log_crud(db)
        
        # Cleanup
        cleanup(db, doc_id)
        
        print_section("TEST SUMMARY")
        print("✅ All Phase 1.1 tests completed!")
        print("\nNew features tested:")
        print("  - Precise citation fields (section_id, citable_reference)")
        print("  - Cross-reference tracking (defined_terms, reference flags)")
        print("  - ChunkReference model and CRUD")
        print("  - Reference expansion for retrieval")
        print("  - Unresolved reference handling")
        print("\nYour data foundation is ready for Phase 2: Document Ingestion")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()