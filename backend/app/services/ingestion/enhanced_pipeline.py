"""
Enhanced Ingestion Pipeline (Phase 2)

Orchestrates the complete document ingestion process with full structured
content extraction. Builds on the basic pipeline with:

1. Legal-aware chunking (preserves condition lists, extracts citations)
2. Structured content extraction (tables, formulas, examples, etc.)
3. Cross-reference detection (HMRC manual refs, legislation)
4. Metadata extraction (thresholds, tax years, forms, keywords)

Usage:
    pipeline = EnhancedIngestionPipeline(db)
    result = pipeline.ingest_url("/vat-registration")
    
    print(f"Chunks: {result.chunks_created}")
    print(f"Tables: {result.tables_extracted}")
    print(f"Formulas: {result.formulas_extracted}")
    print(f"Cross-refs: {result.references_detected}")
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
import hashlib
import logging

from sqlalchemy.orm import Session

# Core components
from .gov_uk_client import GovUKClient, GovUKDocument, GovUKContentAPIError
from .content_parser import ContentParser, ParsedDocument
from .legal_chunker import LegalChunker, LegalChunk, LegalChunkingConfig

# Extractors
from .extractors import (
    TableExtractor,
    FormulaExtractor,
    DeadlineExtractor,
    ContactExtractor,
    ConditionExtractor,
    ExampleExtractor,
    ReferenceDetector,
    MetadataExtractor,
    ExtractedTable,
    ExtractedFormula,
    ExtractedDeadline,
    ExtractedContact,
    ExtractedConditionList,
    ExtractedExample,
    DetectedReference,
    ExtractedMetadata,
)

# Models and CRUD
from app.models.document import SourceDocument, AuthorityType, DocumentType, ReliabilityTier, IngestionStatus
from app.models.chunk import DocumentChunk, TopicPrimary, ContentType
from app.models.ingestion_log import IngestionLog, IngestionRunStatus
from app.models.structured_content import (
    StructuredTable, StructuredFormula, StructuredDeadline,
    StructuredContact, StructuredExample, StructuredConditionList,
    TableType, FormulaType, DeadlineType, DeadlineFrequency,
    ContactType, ExampleCategory, ConditionLogic
)
from app.models.chunk_reference import ChunkReference, ReferenceType

from app.crud.crud_document import create_document, get_document_by_url, update_document
from app.crud.crud_chunk import create_chunks_batch, get_chunks_by_document
from app.crud.crud_ingestion_log import (
    create_ingestion_log,
    update_ingestion_log_status,
    update_ingestion_log_stats,
    add_ingestion_error,
    add_ingestion_warning
)
from app.crud.crud_structured_content import (
    create_structured_table,
    create_structured_formula,
    create_structured_deadline,
    create_structured_contact,
    create_structured_example,
    create_structured_condition_list,
)
from app.crud.crud_chunk_reference import create_chunk_reference

from app.schema.document import DocumentCreate
from app.schema.chunk import ChunkCreate
from app.schema.structured_content import (
    StructuredTableCreate,
    StructuredFormulaCreate,
    StructuredDeadlineCreate,
    StructuredContactCreate,
    StructuredExampleCreate,
    StructuredConditionListCreate,
)
from app.schema.chunk_reference import ChunkReferenceCreate

logger = logging.getLogger(__name__)


@dataclass
class EnhancedPipelineConfig:
    """Configuration for the enhanced ingestion pipeline."""
    
    # Chunking configuration
    chunking_config: LegalChunkingConfig = field(default_factory=LegalChunkingConfig)
    
    # Extraction toggles
    extract_tables: bool = True
    extract_formulas: bool = True
    extract_deadlines: bool = True
    extract_contacts: bool = True
    extract_conditions: bool = True
    extract_examples: bool = True
    detect_references: bool = True
    extract_metadata: bool = True
    
    # Processing options
    continue_on_error: bool = True
    max_errors: int = 50
    min_content_length: int = 100
    
    # Logging
    verbose: bool = True


@dataclass
class EnhancedIngestionResult:
    """Result of ingesting a single document with enhanced extraction."""
    
    url: str
    success: bool
    document_id: Optional[UUID] = None
    action: str = ""  # created, updated, skipped, failed
    error: Optional[str] = None
    
    # Basic counts
    chunks_created: int = 0
    
    # Structured content counts
    tables_extracted: int = 0
    formulas_extracted: int = 0
    deadlines_extracted: int = 0
    contacts_extracted: int = 0
    conditions_extracted: int = 0
    examples_extracted: int = 0
    references_detected: int = 0
    
    # Metadata
    tax_years_found: List[str] = field(default_factory=list)
    forms_found: List[str] = field(default_factory=list)
    thresholds_found: int = 0


@dataclass
class EnhancedPipelineResult:
    """Final result of enhanced pipeline run."""
    
    run_id: UUID
    status: str
    
    # Document counts
    documents_processed: int = 0
    documents_created: int = 0
    documents_updated: int = 0
    documents_skipped: int = 0
    documents_failed: int = 0
    
    # Content counts
    chunks_created: int = 0
    tables_extracted: int = 0
    formulas_extracted: int = 0
    deadlines_extracted: int = 0
    contacts_extracted: int = 0
    conditions_extracted: int = 0
    examples_extracted: int = 0
    references_detected: int = 0
    
    # Timing
    duration_seconds: float = 0.0
    
    # Errors
    errors: List[Dict[str, str]] = field(default_factory=list)


class EnhancedIngestionPipeline:
    """
    Enhanced pipeline for ingesting GOV.UK documents with full structured
    content extraction.
    """
    
    def __init__(
        self,
        db: Session,
        config: Optional[EnhancedPipelineConfig] = None
    ):
        """
        Initialize the enhanced pipeline.
        
        Args:
            db: SQLAlchemy database session
            config: Pipeline configuration
        """
        self.db = db
        self.config = config or EnhancedPipelineConfig()
        
        # Core components
        self.gov_uk_client = GovUKClient()
        self.parser = ContentParser()
        self.chunker = LegalChunker(self.config.chunking_config)
        
        # Extractors
        self.table_extractor = TableExtractor()
        self.formula_extractor = FormulaExtractor()
        self.deadline_extractor = DeadlineExtractor()
        self.contact_extractor = ContactExtractor()
        self.condition_extractor = ConditionExtractor()
        self.example_extractor = ExampleExtractor()
        self.reference_detector = ReferenceDetector()
        self.metadata_extractor = MetadataExtractor()
        
        # Tracking
        self.current_log: Optional[IngestionLog] = None
        self._error_count = 0
    
    def _compute_content_hash(self, content: str) -> str:
        """Compute SHA-256 hash of content for change detection."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _determine_authority(self, url: str, doc_type: str) -> AuthorityType:
        """Determine the authority type based on URL and document type."""
        url_lower = url.lower()
        
        if "hmrc-internal-manuals" in url_lower:
            return AuthorityType.HMRC_MANUAL
        elif "legislation.gov.uk" in url_lower:
            return AuthorityType.LEGISLATION
        elif "hmrc" in url_lower or doc_type == "hmrc_manual_section":
            return AuthorityType.HMRC
        else:
            return AuthorityType.GOV_UK
    
    def _determine_document_type(self, schema_name: str, doc_type: str) -> DocumentType:
        """Map GOV.UK schema/document types to our DocumentType enum."""
        schema_lower = schema_name.lower()
        type_lower = doc_type.lower()
        
        if "manual" in type_lower:
            return DocumentType.MANUAL
        elif "guide" in schema_lower or "guide" in type_lower:
            return DocumentType.GUIDANCE
        elif "form" in type_lower:
            return DocumentType.FORM
        elif "news" in type_lower or "announcement" in type_lower:
            return DocumentType.NEWS
        else:
            return DocumentType.GUIDANCE
    
    def _determine_reliability_tier(self, authority: AuthorityType) -> ReliabilityTier:
        """Determine reliability tier based on authority."""
        if authority in [AuthorityType.LEGISLATION, AuthorityType.HMRC_MANUAL]:
            return ReliabilityTier.TIER_1
        elif authority in [AuthorityType.GOV_UK, AuthorityType.HMRC]:
            return ReliabilityTier.TIER_2
        else:
            return ReliabilityTier.TIER_3
    
    def _map_topic_to_enum(self, topic: str) -> Optional[TopicPrimary]:
        """Map extracted topic to TopicPrimary enum."""
        topic_map = {
            'vat': TopicPrimary.VAT,
            'income_tax': TopicPrimary.INCOME_TAX,
            'corporation_tax': TopicPrimary.CORPORATION_TAX,
            'self_assessment': TopicPrimary.SELF_ASSESSMENT,
            'national_insurance': TopicPrimary.NATIONAL_INSURANCE,
            'capital_gains': TopicPrimary.CAPITAL_GAINS,
            'paye': TopicPrimary.PAYE,
            'penalties': TopicPrimary.PENALTIES,
        }
        return topic_map.get(topic)
    
    def _map_table_type(self, type_str: str) -> TableType:
        """Map extracted table type string to TableType enum."""
        type_map = {
            'tax_rates': TableType.TAX_RATES,
            'vat_rates': TableType.VAT_RATES,
            'penalties': TableType.PENALTIES,
            'thresholds': TableType.THRESHOLDS,
            'deadlines': TableType.DEADLINES,
            'ni_rates': TableType.NI_RATES,
            'ni_thresholds': TableType.NI_THRESHOLDS,
            'allowances': TableType.ALLOWANCES,
            'mileage_rates': TableType.MILEAGE_RATES,
            'benefit_rates': TableType.BENEFIT_RATES,
        }
        return type_map.get(type_str, TableType.OTHER)
    
    def _map_formula_type(self, type_str: str) -> FormulaType:
        """Map extracted formula type to FormulaType enum."""
        type_map = {
            'marginal_relief': FormulaType.MARGINAL_RELIEF,
            'tax_calculation': FormulaType.TAX_CALCULATION,
            'penalty_calculation': FormulaType.PENALTY_CALCULATION,
            'vat_calculation': FormulaType.VAT_CALCULATION,
            'relief_calculation': FormulaType.RELIEF_CALCULATION,
        }
        return type_map.get(type_str, FormulaType.TAX_CALCULATION)
    
    def ingest_url(self, url: str) -> EnhancedIngestionResult:
        """
        Ingest a single URL with full enhanced extraction.
        
        Args:
            url: GOV.UK URL path (e.g., "/vat-registration")
        
        Returns:
            EnhancedIngestionResult with extraction counts
        """
        result = EnhancedIngestionResult(url=url, success=False)
        
        try:
            # Step 1: Fetch document
            logger.info(f"Fetching document: {url}")
            gov_uk_doc = self.gov_uk_client.fetch(url)
            
            if not gov_uk_doc.body_html:
                result.action = "skipped"
                result.error = "No content"
                return result
            
            # Step 2: Parse document (preserve HTML for table extraction)
            parsed_doc = self.parser.parse(gov_uk_doc.body_html, gov_uk_doc.title)
            
            if not parsed_doc.has_content or parsed_doc.word_count < 20:
                result.action = "skipped"
                result.error = "Insufficient content"
                return result
            
            # Extract document-level metadata first
            doc_metadata = self.metadata_extractor.extract(
                gov_uk_doc.body_html,
                parsed_doc.full_text,
                gov_uk_doc.url
            )
            metadata = doc_metadata.items[0] if doc_metadata.items else ExtractedMetadata()
            
            result.tax_years_found = metadata.tax_years
            result.forms_found = [f['code'] for f in metadata.forms]
            result.thresholds_found = len(metadata.thresholds)
            
            # Determine document properties
            authority = self._determine_authority(url, gov_uk_doc.document_type)
            doc_type = self._determine_document_type(gov_uk_doc.schema_name, gov_uk_doc.document_type)
            reliability = self._determine_reliability_tier(authority)
            content_hash = self._compute_content_hash(parsed_doc.full_text)
            
            # Primary topic from metadata
            primary_topic = None
            if metadata.topics:
                primary_topic = self._map_topic_to_enum(metadata.topics[0])
            
            # Step 3: Check if document exists
            existing_doc = get_document_by_url(self.db, gov_uk_doc.url)
            
            if existing_doc:
                if existing_doc.content_hash == content_hash:
                    result.action = "skipped"
                    result.success = True
                    result.document_id = existing_doc.id
                    return result
                
                # Document changed - would need to update
                result.action = "updated"
            else:
                result.action = "created"
            
            # Step 4: Create document record
            doc_create = DocumentCreate(
                url=gov_uk_doc.url,
                title=gov_uk_doc.title,
                description=gov_uk_doc.description,
                authority_type=authority,
                document_type=doc_type,
                reliability_tier=reliability,
                content_hash=content_hash,
                raw_content=gov_uk_doc.body_html,
                parsed_content=parsed_doc.full_text,
                word_count=parsed_doc.word_count,
                schema_name=gov_uk_doc.schema_name,
                locale=gov_uk_doc.locale,
                first_published_at=gov_uk_doc.first_published_at,
                public_updated_at=gov_uk_doc.public_updated_at,
                ingestion_status=IngestionStatus.COMPLETED,
            )
            
            document = create_document(self.db, doc_create)
            result.document_id = document.id
            
            # Step 5: Chunk with legal awareness
            chunks = self.chunker.chunk_document(
                parsed_doc,
                source_url=gov_uk_doc.url,
                document_title=gov_uk_doc.title
            )
            
            # Step 6: Create chunk records
            chunk_creates = []
            
            for chunk in chunks:
                # Extract chunk-level metadata
                chunk_metadata = self.metadata_extractor.extract_for_chunk(chunk.content)
                
                chunk_create = ChunkCreate(
                    document_id=str(document.id),
                    content=chunk.content,
                    chunk_index=chunk.chunk_index,
                    total_chunks=chunk.total_chunks,
                    char_start=chunk.char_start,
                    char_end=chunk.char_end,
                    section_title=chunk.section_title,
                    heading_path=chunk.heading_path,
                    heading_level=chunk.heading_level,
                    section_id=chunk.section_id,
                    paragraph_number=chunk.paragraph_number,
                    citable_reference=chunk.citable_reference,
                    content_type=ContentType.FACTUAL if chunk.content_type.value == 'general' else ContentType.PROCEDURAL,
                    topic_primary=primary_topic,
                    has_overlap_with_previous=chunk.has_overlap_with_previous,
                    contains_condition_list=chunk.contains_condition_list,
                    contains_table=chunk.contains_table_reference,
                    contains_deadline=chunk.contains_deadline,
                    contains_example=chunk.contains_example,
                    tax_years=chunk_metadata.tax_years,
                    forms_referenced=[f['code'] for f in chunk_metadata.forms],
                    keywords=chunk_metadata.keywords,
                )
                chunk_creates.append(chunk_create)
            
            # Batch create chunks
            created_chunks = create_chunks_batch(self.db, chunk_creates)
            result.chunks_created = len(created_chunks)
            
            # Step 7: Extract structured content
            first_chunk = created_chunks[0] if created_chunks else None
            tax_year = metadata.tax_years[0] if metadata.tax_years else None
            
            if first_chunk:
                # Tables
                if self.config.extract_tables and self.table_extractor.has_tables(gov_uk_doc.body_html):
                    table_result = self.table_extractor.extract(
                        gov_uk_doc.body_html, parsed_doc.full_text, gov_uk_doc.url, tax_year=tax_year
                    )
                    for table in table_result.items:
                        table_create = StructuredTableCreate(
                            chunk_id=str(first_chunk.id),
                            document_id=str(document.id),
                            table_type=self._map_table_type(table.table_type),
                            table_name=table.table_name,
                            headers=table.headers,
                            rows=table.rows,
                            column_types=table.column_types,
                            lookup_keys=table.lookup_keys,
                            value_columns=table.value_columns,
                            tax_year=table.tax_year,
                            source_url=gov_uk_doc.url,
                        )
                        create_structured_table(self.db, table_create)
                        result.tables_extracted += 1
                
                # Formulas
                if self.config.extract_formulas and self.formula_extractor.has_formulas(parsed_doc.full_text):
                    formula_result = self.formula_extractor.extract(
                        gov_uk_doc.body_html, parsed_doc.full_text, gov_uk_doc.url, tax_year=tax_year
                    )
                    for formula in formula_result.items:
                        formula_create = StructuredFormulaCreate(
                            chunk_id=str(first_chunk.id),
                            document_id=str(document.id),
                            formula_type=self._map_formula_type(formula.formula_type),
                            formula_name=formula.formula_name,
                            formula_text=formula.formula_text,
                            formula_description=formula.formula_description,
                            variables=formula.variables,
                            formula_logic=formula.formula_logic,
                            tax_year=formula.tax_year,
                            source_url=gov_uk_doc.url,
                        )
                        create_structured_formula(self.db, formula_create)
                        result.formulas_extracted += 1
                
                # Deadlines
                if self.config.extract_deadlines and self.deadline_extractor.has_deadlines(parsed_doc.full_text):
                    deadline_result = self.deadline_extractor.extract(
                        gov_uk_doc.body_html, parsed_doc.full_text, gov_uk_doc.url, tax_year=tax_year
                    )
                    for deadline in deadline_result.items:
                        deadline_create = StructuredDeadlineCreate(
                            chunk_id=str(first_chunk.id),
                            document_id=str(document.id),
                            deadline_type=DeadlineType.FILING,
                            deadline_name=deadline.deadline_name,
                            tax_category=deadline.tax_category,
                            frequency=DeadlineFrequency.ANNUAL,
                            deadline_rule=deadline.deadline_rule,
                            description=deadline.description,
                            applies_to=deadline.applies_to,
                            source_url=gov_uk_doc.url,
                        )
                        create_structured_deadline(self.db, deadline_create)
                        result.deadlines_extracted += 1
                
                # Contacts
                if self.config.extract_contacts and self.contact_extractor.has_contacts(parsed_doc.full_text):
                    contact_result = self.contact_extractor.extract(
                        gov_uk_doc.body_html, parsed_doc.full_text, gov_uk_doc.url
                    )
                    for contact in contact_result.items:
                        contact_create = StructuredContactCreate(
                            chunk_id=str(first_chunk.id),
                            document_id=str(document.id),
                            service_name=contact.service_name,
                            contact_methods=contact.contact_methods,
                            description=contact.description,
                            source_url=gov_uk_doc.url,
                        )
                        create_structured_contact(self.db, contact_create)
                        result.contacts_extracted += 1
                
                # Condition lists
                if self.config.extract_conditions and self.condition_extractor.has_condition_lists(parsed_doc.full_text):
                    condition_result = self.condition_extractor.extract(
                        gov_uk_doc.body_html, parsed_doc.full_text, gov_uk_doc.url
                    )
                    for condition_list in condition_result.items:
                        condition_create = StructuredConditionListCreate(
                            chunk_id=str(first_chunk.id),
                            document_id=str(document.id),
                            condition_name=condition_list.condition_name,
                            condition_type=condition_list.condition_type,
                            logical_operator=ConditionLogic.OR,
                            conditions=condition_list.conditions,
                            outcome_if_met=condition_list.outcome_if_met,
                            source_url=gov_uk_doc.url,
                        )
                        create_structured_condition_list(self.db, condition_create)
                        result.conditions_extracted += 1
                
                # Examples
                if self.config.extract_examples and self.example_extractor.has_examples(parsed_doc.full_text):
                    example_result = self.example_extractor.extract(
                        gov_uk_doc.body_html, parsed_doc.full_text, gov_uk_doc.url, tax_year=tax_year
                    )
                    for example in example_result.items:
                        example_create = StructuredExampleCreate(
                            chunk_id=str(first_chunk.id),
                            document_id=str(document.id),
                            example_category=ExampleCategory.INCOME_TAX,
                            example_name=example.example_name,
                            scenario=example.scenario,
                            scenario_description=example.scenario_description,
                            steps=example.steps,
                            final_result=example.final_result,
                            tax_year=example.tax_year,
                            source_url=gov_uk_doc.url,
                        )
                        create_structured_example(self.db, example_create)
                        result.examples_extracted += 1
                
                # Cross-references
                if self.config.detect_references and self.reference_detector.has_references(parsed_doc.full_text):
                    ref_result = self.reference_detector.extract(
                        gov_uk_doc.body_html, parsed_doc.full_text, gov_uk_doc.url
                    )
                    for ref in ref_result.items:
                        ref_type = ReferenceType.HMRC_MANUAL if ref.reference_type == 'hmrc_manual' else ReferenceType.SEE_ALSO
                        ref_create = ChunkReferenceCreate(
                            source_chunk_id=str(first_chunk.id),
                            reference_type=ref_type,
                            reference_text=ref.reference_text,
                            target_identifier=ref.target_normalized,
                            target_url=ref.target_url,
                            relationship_type=ref.relationship_type,
                            context_snippet=ref.context[:200] if ref.context else None,
                        )
                        create_chunk_reference(self.db, ref_create)
                        result.references_detected += 1
            
            result.success = True
            logger.info(
                f"Ingested {url}: {result.chunks_created} chunks, "
                f"{result.tables_extracted} tables, {result.formulas_extracted} formulas"
            )
            
        except GovUKContentAPIError as e:
            result.error = f"GOV.UK API error: {str(e)}"
            result.action = "failed"
            logger.error(f"Failed to fetch {url}: {e}")
            
        except Exception as e:
            result.error = f"Processing error: {str(e)}"
            result.action = "failed"
            logger.exception(f"Error processing {url}")
        
        return result
    
    def run(self, urls: List[str]) -> EnhancedPipelineResult:
        """
        Run the enhanced pipeline on a list of URLs.
        """
        start_time = datetime.now()
        
        log = create_ingestion_log(
            self.db,
            run_type="enhanced_batch",
            config={"urls": urls}
        )
        self.current_log = log
        
        result = EnhancedPipelineResult(run_id=log.id, status="running")
        
        try:
            for url in urls:
                if self._error_count >= self.config.max_errors:
                    break
                
                url_result = self.ingest_url(url)
                result.documents_processed += 1
                
                if url_result.success:
                    if url_result.action == "created":
                        result.documents_created += 1
                    elif url_result.action == "updated":
                        result.documents_updated += 1
                    elif url_result.action == "skipped":
                        result.documents_skipped += 1
                    
                    result.chunks_created += url_result.chunks_created
                    result.tables_extracted += url_result.tables_extracted
                    result.formulas_extracted += url_result.formulas_extracted
                    result.deadlines_extracted += url_result.deadlines_extracted
                    result.contacts_extracted += url_result.contacts_extracted
                    result.conditions_extracted += url_result.conditions_extracted
                    result.examples_extracted += url_result.examples_extracted
                    result.references_detected += url_result.references_detected
                else:
                    result.documents_failed += 1
                    self._error_count += 1
                    if url_result.error:
                        result.errors.append({"url": url, "error": url_result.error})
            
            result.status = "completed"
            
        except Exception as e:
            result.status = "failed"
            result.errors.append({"error": str(e)})
        
        result.duration_seconds = (datetime.now() - start_time).total_seconds()
        
        update_ingestion_log_status(
            self.db, log.id,
            IngestionRunStatus.COMPLETED if result.status == "completed" else IngestionRunStatus.FAILED
        )
        
        return result
