"""
Document and RAG System Exceptions

Custom exceptions for document ingestion and RAG operations.
"""

from fastapi import status
from app.exceptions.base import AppException


# === DOCUMENT EXCEPTIONS ===

class DocumentNotFoundException(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Document not found."


class DocumentAlreadyExistsException(AppException):
    status_code = status.HTTP_409_CONFLICT
    detail = "A document with this URL already exists."


# === CHUNK EXCEPTIONS ===

class ChunkNotFoundException(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Chunk not found."


# === REFERENCE EXCEPTIONS ===

class ChunkReferenceNotFoundException(AppException):
    """Raised when a chunk reference is not found."""
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Chunk reference not found."


class ReferenceResolutionException(AppException):
    """Raised when reference resolution fails."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "Failed to resolve reference."


class CircularReferenceException(AppException):
    """Raised when a circular reference is detected."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail = "Circular reference detected in document graph."


# === INGESTION EXCEPTIONS ===

class IngestionException(AppException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "An error occurred during document ingestion."


class IngestionLogNotFoundException(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Ingestion log not found."


class SourceFetchException(AppException):
    status_code = status.HTTP_502_BAD_GATEWAY
    detail = "Failed to fetch content from source."


# === METADATA EXCEPTIONS ===

class MetadataExtractionException(AppException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "Failed to extract metadata from document."


class ClassificationException(AppException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "Failed to classify document content."


class InvalidMetadataException(AppException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail = "Invalid or incomplete metadata."


# === VECTOR STORE EXCEPTIONS ===

class EmbeddingException(AppException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "Failed to generate embeddings."


class VectorStoreException(AppException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "Vector store operation failed."


# === RETRIEVAL EXCEPTIONS ===

class RetrievalException(AppException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "Failed to retrieve relevant documents."


class ReferenceExpansionException(AppException):
    """Raised when reference expansion during retrieval fails."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "Failed to expand references during retrieval."


# === GENERATION EXCEPTIONS ===

class GenerationException(AppException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "Failed to generate response."


# === AUDIT EXCEPTIONS ===

class AuditLogException(AppException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "Failed to create audit log entry."