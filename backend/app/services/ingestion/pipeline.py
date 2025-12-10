"""
Document Ingestion Pipeline

Orchestrates the complete process of ingesting documents from GOV.UK
into our PostgreSQL database, ready for metadata population and embedding.

Pipeline Flow:
┌─────────────────────────────────────────────────────────────────────────┐
│                         INGESTION PIPELINE                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. INITIALIZE                                                          │
│     └── Create IngestionLog record to track this run                    │
│                                                                         │
│  2. FETCH URLS                                                          │
│     └── Get list of URLs to process (seed list or custom)               │
│                                                                         │
│  3. FOR EACH URL:                                                       │
│     ├── Check if already ingested (skip if unchanged)                   │
│     ├── Fetch from GOV.UK API                                           │
│     ├── Parse HTML → clean text + structure                             │
│     ├── Chunk semantically                                              │
│     ├── Create SourceDocument record                                    │
│     ├── Create DocumentChunk records                                    │
│     └── Update progress in IngestionLog                                 │
│                                                                         │
│  4. FINALIZE                                                            │
│     └── Update IngestionLog with final stats                            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

Key Design Decisions:
- Idempotent: Running twice won't create duplicates (uses content hash)
- Resumable: Failures don't lose progress (each doc committed separately)
- Observable: Full logging via IngestionLog table
- Configurable: Can process single URL, list, or full seed set
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime
from enum import Enum
import hashlib
import logging
import traceback
from uuid import UUID

from sqlalchemy.orm import Session

from .gov_uk_client import GovUKClient, GovUKDocument, GovUKContentAPIError
from .content_parser import ContentParser, ParsedDocument
from .chunker import SemanticChunker, Chunk, ChunkingConfig

# Import our models and CRUD
from app.models.document import SourceDocument, AuthorityType, DocumentType, ReliabilityTier, IngestionStatus
from app.models.chunk import DocumentChunk, TopicPrimary, ContentType, ServiceCategory
from app.models.ingestion_log import IngestionLog, IngestionRunStatus
from app.crud.crud_document import create_document, get_document_by_url, update_document, update_document_status
from app.crud.crud_chunk import create_chunks_batch, get_chunks_by_document
from app.crud.crud_ingestion_log import (
    create_ingestion_log, 
    update_ingestion_log_status,
    update_ingestion_log_stats,
    increment_ingestion_stats,
    add_ingestion_error,
    add_ingestion_warning
)
from app.schema.document import DocumentCreate, DocumentUpdate
from app.schema.chunk import ChunkCreate

logger = logging.getLogger(__name__)


class IngestionMode(str, Enum):
    """How to handle existing documents"""
    SKIP_EXISTING = "skip_existing"  # Skip if URL exists (fastest)
    UPDATE_IF_CHANGED = "update_if_changed"  # Re-ingest if content hash differs
    FORCE_UPDATE = "force_update"  # Always re-ingest (for schema changes)


@dataclass
class PipelineConfig:
    """
    Configuration for the ingestion pipeline.
    
    Adjust these based on your needs:
    - Testing: small batch_size, verbose logging
    - Production: larger batch_size, error-only logging
    """
    # Processing behavior
    mode: IngestionMode = IngestionMode.UPDATE_IF_CHANGED
    batch_size: int = 10  # Commit to DB every N documents
    
    # Error handling
    continue_on_error: bool = True  # Keep going if one doc fails
    max_errors: int = 50  # Stop if too many errors
    
    # Content filtering
    min_content_length: int = 100  # Skip documents with less content
    
    # Chunking config
    chunking_config: ChunkingConfig = field(default_factory=ChunkingConfig)
    
    # Logging
    verbose: bool = True


@dataclass
class IngestionResult:
    """Result of ingesting a single document"""
    url: str
    success: bool
    document_id: Optional[UUID] = None
    chunks_created: int = 0
    action: str = ""  # "created", "updated", "skipped", "failed"
    error: Optional[str] = None


@dataclass
class PipelineResult:
    """Final result of pipeline run"""
    run_id: UUID
    status: str
    documents_processed: int
    documents_created: int
    documents_updated: int
    documents_skipped: int
    documents_failed: int
    chunks_created: int
    errors: List[Dict[str, str]]
    duration_seconds: float


class IngestionPipeline:
    """
    Main pipeline for ingesting GOV.UK documents.
    
    This is the central coordinator that:
    1. Fetches documents from GOV.UK
    2. Parses and chunks them
    3. Stores in PostgreSQL
    4. Tracks progress in IngestionLog
    
    Usage:
        pipeline = IngestionPipeline(db_session)
        
        # Ingest specific URLs
        result = pipeline.run(urls=["/vat-registration", "/corporation-tax"])
        
        # Or use the seed list
        result = pipeline.run_seed_list()
        
        print(f"Created {result.documents_created} documents")
    """
    
    def __init__(
        self, 
        db: Session,
        config: Optional[PipelineConfig] = None
    ):
        """
        Initialize the pipeline.
        
        Args:
            db: SQLAlchemy database session
            config: Pipeline configuration (uses defaults if None)
        """
        self.db = db
        self.config = config or PipelineConfig()
        
        # Initialize components
        self.gov_uk_client = GovUKClient()
        self.parser = ContentParser()
        self.chunker = SemanticChunker(self.config.chunking_config)
        
        # Track current run
        self.current_log: Optional[IngestionLog] = None
        self._error_count = 0
    
    def _compute_content_hash(self, content: str) -> str:
        """
        Compute SHA-256 hash of content for change detection.
        
        We use this to know if a document has changed since last ingestion.
        If hash matches, content is identical → skip re-processing.
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _determine_authority(self, url: str, doc_type: str) -> AuthorityType:
        """
        Determine the authority type based on URL and document type.
        
        Authority hierarchy:
        1. HMRC_MANUAL - Technical manuals (highest authority for details)
        2. GOV_UK - Official guidance
        3. HMRC - General HMRC content
        4. LEGISLATION - Acts and regulations
        """
        url_lower = url.lower()
        
        if "hmrc-internal-manuals" in url_lower:
            return AuthorityType.HMRC_MANUAL
        elif "legislation.gov.uk" in url_lower:
            return AuthorityType.UK_LEGISLATION
        elif "hmrc" in url_lower or doc_type == "hmrc_manual_section":
            return AuthorityType.HMRC_MANUAL
        else:
            return AuthorityType.GOV_UK
    
    def _determine_document_type(self, schema_name: str, doc_type: str) -> DocumentType:
        """
        Map GOV.UK schema/document types to our DocumentType enum.
        """
        schema_lower = schema_name.lower()
        type_lower = doc_type.lower()
        
        if "manual" in type_lower:
            return DocumentType.MANUAL
        elif "guide" in schema_lower or "guide" in type_lower:
            return DocumentType.GUIDANCE
        elif "form" in type_lower:
            return DocumentType.FORM_INSTRUCTIONS
        elif "news" in type_lower or "announcement" in type_lower:
            return DocumentType.NEWS
        elif "detailed" in type_lower:
            return DocumentType.GUIDANCE
        else:
            return DocumentType.GUIDANCE  # Default
    
    def _determine_reliability_tier(self, authority: AuthorityType) -> ReliabilityTier:
        """
        Determine reliability tier based on authority.
        
        Tier 1: Primary legislation, HMRC manuals (most authoritative)
        Tier 2: GOV.UK official guidance
        Tier 3: Professional bodies, third parties
        """
        if authority in [AuthorityType.UK_LEGISLATION, AuthorityType.HMRC_MANUAL]:
            return ReliabilityTier.TIER_1
        elif authority in [AuthorityType.GOV_UK, AuthorityType.HMRC_MANUAL]:
            return ReliabilityTier.TIER_2
        else:
            return ReliabilityTier.TIER_3
    
    def _extract_section_hierarchy(self, breadcrumbs: List[Dict]) -> List[str]:
        """Extract section hierarchy from breadcrumbs"""
        return [b.get("title", "") for b in breadcrumbs if b.get("title")]
    
    def _should_process_document(
        self, 
        url: str, 
        content_hash: str
    ) -> tuple[bool, str, Optional[SourceDocument]]:
        """
        Determine if we should process this document.
        
        Returns:
            (should_process, reason, existing_doc)
        """
        existing = get_document_by_url(self.db, url)
        
        if not existing:
            return True, "new", None
        
        if self.config.mode == IngestionMode.SKIP_EXISTING:
            return False, "skip_existing", existing
        
        if self.config.mode == IngestionMode.UPDATE_IF_CHANGED:
            if existing.content_hash == content_hash:
                return False, "unchanged", existing
            return True, "content_changed", existing
        
        # FORCE_UPDATE
        return True, "force_update", existing
    
    def _create_document_record(
        self,
        gov_doc: GovUKDocument,
        parsed_doc: ParsedDocument,
        content_hash: str
    ) -> SourceDocument:
        """
        Create a SourceDocument record from fetched data.
        """
        authority = self._determine_authority(gov_doc.url, gov_doc.document_type)
        doc_type = self._determine_document_type(gov_doc.schema_name, gov_doc.document_type)
        reliability = self._determine_reliability_tier(authority)
        
        doc_create = DocumentCreate(
            url=gov_doc.url,
            authority=authority,
            document_type=doc_type,
            reliability_tier=reliability,
            title=gov_doc.title,
            parent_document=gov_doc.parent_title,
            section_hierarchy=self._extract_section_hierarchy(gov_doc.breadcrumbs),
            publication_date=gov_doc.first_published.date() if gov_doc.first_published else None,
            last_updated_source=gov_doc.last_updated,
            content_hash=content_hash
        )
        
        return create_document(self.db, doc_create)
    
    def _update_document_record(
        self,
        existing: SourceDocument,
        gov_doc: GovUKDocument,
        parsed_doc: ParsedDocument,
        content_hash: str
    ) -> SourceDocument:
        """
        Update an existing SourceDocument with new data.
        """
        doc_update = DocumentUpdate(
            title=gov_doc.title,
            parent_document=gov_doc.parent_title,
            section_hierarchy=self._extract_section_hierarchy(gov_doc.breadcrumbs),
            last_updated_source=gov_doc.last_updated,
            content_hash=content_hash,
            ingestion_status=IngestionStatus.PENDING
        )
        
        return update_document(self.db, existing.id, doc_update)
    
    def _create_chunk_records(
        self,
        document: SourceDocument,
        chunks: List[Chunk],
        gov_doc: GovUKDocument
    ) -> List[DocumentChunk]:
        """
        Create DocumentChunk records from chunked content.
        
        Note: Phase 2 only populates AUTOMATIC fields.
        LLM-derived fields (topic, business_type, etc.) are populated in Phase 3.
        """
        chunk_creates = []
        
        for chunk in chunks:
            chunk_create = ChunkCreate(
                document_id=document.id,
                content=chunk.content,
                
                # Source attribution (denormalized for fast citation)
                source_url=document.url,
                source_authority=document.authority,
                section_title=chunk.section_title,
                heading_path=chunk.heading_path,
                
                # Position tracking
                chunk_index=chunk.chunk_index,
                total_chunks_in_doc=chunk.total_chunks,
                char_start=chunk.char_start,
                char_end=chunk.char_end,
                
                # Inherited from document
                reliability_tier=document.reliability_tier,
                publication_date=document.publication_date,
                last_updated=gov_doc.last_updated,
                
                # === Fields populated in Phase 3 (Metadata Population) ===
                # topic_primary=None,  # LLM classification
                # topic_secondary=[],  # LLM classification
                # business_types=[],  # LLM classification
                # content_type=None,  # LLM classification
                # service_category=None,  # LLM classification
                # threshold_values=[],  # Rule-based extraction
                # keywords=[],  # Rule-based + LLM
                # form_references=[],  # Rule-based extraction
                # requires_professional_advice=False,  # LLM classification
            )
            chunk_creates.append(chunk_create)
        
        return create_chunks_batch(self.db, chunk_creates)
    
    def _delete_existing_chunks(self, document_id: UUID) -> int:
        """Delete all chunks for a document (before re-ingestion)"""
        existing_chunks = get_chunks_by_document(self.db, document_id)
        count = len(existing_chunks)
        for chunk in existing_chunks:
            self.db.delete(chunk)
        self.db.commit()
        return count
    
    def ingest_url(self, url: str) -> IngestionResult:
        """
        Ingest a single URL.
        
        This is the core method that processes one document through
        the entire pipeline: fetch → parse → chunk → store.
        
        Args:
            url: GOV.UK URL or path to ingest
        
        Returns:
            IngestionResult with success status and details
        """
        result = IngestionResult(url=url, success=False)
        
        try:
            # Step 1: Fetch from GOV.UK
            if self.config.verbose:
                logger.info(f"Fetching: {url}")
            
            gov_doc = self.gov_uk_client.fetch_document(url)
            
            # Step 2: Parse content
            parsed_doc = self.parser.parse_gov_uk_document(gov_doc)
            
            if not parsed_doc.has_content:
                result.action = "skipped"
                result.error = "No content found"
                if self.current_log:
                    add_ingestion_warning(
                        self.db, self.current_log.id,
                        f"No content: {url}"
                    )
                return result
            
            if parsed_doc.word_count < self.config.min_content_length // 5:  # ~5 chars per word
                result.action = "skipped"
                result.error = f"Content too short ({parsed_doc.word_count} words)"
                if self.current_log:
                    add_ingestion_warning(
                        self.db, self.current_log.id,
                        f"Content too short: {url} ({parsed_doc.word_count} words)"
                    )
                return result
            
            # Step 3: Compute content hash
            content_hash = self._compute_content_hash(parsed_doc.full_text)
            
            # Step 4: Check if should process
            should_process, reason, existing_doc = self._should_process_document(
                gov_doc.url, content_hash
            )
            
            if not should_process:
                result.success = True
                result.action = "skipped"
                result.document_id = existing_doc.id if existing_doc else None
                if self.config.verbose:
                    logger.info(f"Skipping {url}: {reason}")
                return result
            
            # Step 5: Chunk content
            chunks = self.chunker.chunk_document(parsed_doc)
            
            if not chunks:
                result.action = "skipped"
                result.error = "No chunks created"
                return result
            
            # Step 6: Create/Update database records
            if existing_doc:
                # Delete old chunks before creating new ones
                self._delete_existing_chunks(existing_doc.id)
                document = self._update_document_record(
                    existing_doc, gov_doc, parsed_doc, content_hash
                )
                result.action = "updated"
            else:
                document = self._create_document_record(
                    gov_doc, parsed_doc, content_hash
                )
                result.action = "created"
            
            # Step 7: Create chunk records
            created_chunks = self._create_chunk_records(document, chunks, gov_doc)
            
            # Step 8: Update document with chunk count
            document.total_chunks = len(created_chunks)
            document.ingestion_status = IngestionStatus.COMPLETED
            document.ingested_at = datetime.now()
            self.db.commit()
            
            # Success!
            result.success = True
            result.document_id = document.id
            result.chunks_created = len(created_chunks)
            
            if self.config.verbose:
                logger.info(
                    f"✓ {result.action.upper()}: {gov_doc.title} "
                    f"({len(created_chunks)} chunks)"
                )
            
        except GovUKContentAPIError as e:
            result.error = str(e)
            result.action = "failed"
            self._error_count += 1
            logger.error(f"API error for {url}: {e}")
            
            if self.current_log:
                add_ingestion_error(
                    self.db, self.current_log.id,
                    f"API error: {url}", str(e)
                )
        
        except Exception as e:
            result.error = str(e)
            result.action = "failed"
            self._error_count += 1
            logger.error(f"Error ingesting {url}: {e}")
            logger.debug(traceback.format_exc())
            
            if self.current_log:
                add_ingestion_error(
                    self.db, self.current_log.id,
                    f"Unexpected error: {url}", 
                    f"{type(e).__name__}: {str(e)}"
                )
        
        return result
    
    def run(
        self,
        urls: List[str],
        run_name: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, IngestionResult], None]] = None
    ) -> PipelineResult:
        """
        Run the ingestion pipeline for a list of URLs.
        
        Args:
            urls: List of GOV.UK URLs or paths to ingest
            run_name: Optional name for this run (for logging)
            progress_callback: Optional callback(current, total, result) for progress updates
        
        Returns:
            PipelineResult with final statistics
        """
        start_time = datetime.now()
        self._error_count = 0
        
        # Create ingestion log
        run_name = run_name or f"ingestion_{start_time.strftime('%Y%m%d_%H%M%S')}"
        self.current_log = create_ingestion_log(
            self.db,
            run_name=run_name,
            source_type="gov_uk_api",
            config={
                "mode": self.config.mode.value,
                "url_count": len(urls),
                "chunking_config": {
                    "min_chunk_size": self.config.chunking_config.min_chunk_size,
                    "max_chunk_size": self.config.chunking_config.max_chunk_size,
                    "target_chunk_size": self.config.chunking_config.target_chunk_size,
                    "overlap_size": self.config.chunking_config.overlap_size
                }
            }
        )
        
        # Update status to running
        update_ingestion_log_status(self.db, self.current_log.id, IngestionRunStatus.IN_PROGRESS)
        
        # Track results
        results = []
        docs_created = 0
        docs_updated = 0
        docs_skipped = 0
        docs_failed = 0
        total_chunks = 0
        
        # Process each URL
        for i, url in enumerate(urls):
            # Check if too many errors
            if self._error_count >= self.config.max_errors:
                logger.error(f"Too many errors ({self._error_count}), stopping")
                add_ingestion_error(
                    self.db, self.current_log.id,
                    "Pipeline stopped", f"Too many errors: {self._error_count}"
                )
                break
            
            # Process URL
            result = self.ingest_url(url)
            results.append(result)
            
            # Update counters
            if result.action == "created":
                docs_created += 1
                total_chunks += result.chunks_created
            elif result.action == "updated":
                docs_updated += 1
                total_chunks += result.chunks_created
            elif result.action == "skipped":
                docs_skipped += 1
            else:  # failed
                docs_failed += 1
            
            # Update log periodically
            if (i + 1) % self.config.batch_size == 0:
                update_ingestion_log_stats(
                    self.db, self.current_log.id,
                    documents_found=len(urls),
                    documents_processed=i + 1,
                    documents_created=docs_created,
                    documents_updated=docs_updated,
                    documents_skipped=docs_skipped,
                    documents_failed=docs_failed,
                    chunks_created=total_chunks
                )
            
            # Progress callback
            if progress_callback:
                progress_callback(i + 1, len(urls), result)
        
        # Finalize
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Final status
        final_status = IngestionRunStatus.COMPLETED
        if docs_failed > 0 and docs_failed == len(urls):
            final_status = IngestionRunStatus.FAILED
        elif docs_failed > 0:
            final_status = IngestionRunStatus.COMPLETED_WITH_ERRORS
        
        # Update log with final stats
        update_ingestion_log_stats(
            self.db, self.current_log.id,
            documents_found=len(urls),
            documents_processed=len(results),
            documents_created=docs_created,
            documents_updated=docs_updated,
            documents_skipped=docs_skipped,
            documents_failed=docs_failed,
            chunks_created=total_chunks
        )
        update_ingestion_log_status(self.db, self.current_log.id, final_status)
        
        # Build result
        errors = [
            {"url": r.url, "error": r.error}
            for r in results if r.error
        ]
        
        logger.info(
            f"Pipeline complete: {docs_created} created, {docs_updated} updated, "
            f"{docs_skipped} skipped, {docs_failed} failed "
            f"({total_chunks} total chunks) in {duration:.1f}s"
        )
        
        return PipelineResult(
            run_id=self.current_log.id,
            status=final_status.value,
            documents_processed=len(results),
            documents_created=docs_created,
            documents_updated=docs_updated,
            documents_skipped=docs_skipped,
            documents_failed=docs_failed,
            chunks_created=total_chunks,
            errors=errors,
            duration_seconds=duration
        )
    
    def run_seed_list(
        self,
        include_manuals: bool = False,
        max_manual_sections: int = 50,
        progress_callback: Optional[Callable] = None
    ) -> PipelineResult:
        """
        Run ingestion using the built-in seed list of essential UK tax URLs.
        
        This is the easiest way to get started — ingest all core guidance.
        
        Args:
            include_manuals: Whether to crawl HMRC technical manuals
            max_manual_sections: Limit manual sections (they're huge)
            progress_callback: Optional progress callback
        
        Returns:
            PipelineResult
        """
        urls = self.gov_uk_client.get_tax_guidance_urls()
        
        if include_manuals:
            # Add manual URLs but note these will need crawling
            manual_urls = self.gov_uk_client.get_hmrc_manual_urls()
            urls.extend(manual_urls)
        
        return self.run(
            urls=urls,
            run_name="seed_list_ingestion",
            progress_callback=progress_callback
        )
    
    def ingest_hmrc_manual(
        self,
        manual_path: str,
        max_sections: Optional[int] = None,
        progress_callback: Optional[Callable] = None
    ) -> PipelineResult:
        """
        Ingest an entire HMRC manual with all its sections.
        
        HMRC manuals are hierarchical and can have hundreds of sections.
        This method crawls the entire structure.
        
        Args:
            manual_path: Path like "/hmrc-internal-manuals/vat-guide"
            max_sections: Limit for testing (None = all sections)
            progress_callback: Optional progress callback
        
        Returns:
            PipelineResult
        """
        logger.info(f"Crawling HMRC manual: {manual_path}")
        
        # Fetch all documents in manual
        documents = self.gov_uk_client.fetch_hmrc_manual(
            manual_path, 
            max_sections=max_sections
        )
        
        # Extract URLs
        urls = [doc.url for doc in documents]
        
        logger.info(f"Found {len(urls)} sections in manual")
        
        return self.run(
            urls=urls,
            run_name=f"manual_{manual_path.split('/')[-1]}",
            progress_callback=progress_callback
        )
