"""
Main Processing Pipeline - Orchestrates document processing.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .classifier import DocumentClassifier, DocumentType, ContentCategory
from .services import (
    ProcessingResult,
    ProcessingStatus,
    EkaScribeService,
    EkaLabReportService,
    OpenAIService,
    DirectParserService,
)

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result from the processing pipeline."""
    success: bool
    document_type: str
    content_category: str
    extracted_data: Dict[str, Any]
    services_tried: List[str]
    service_used: str
    error_message: Optional[str] = None
    raw_responses: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "document_type": self.document_type,
            "content_category": self.content_category,
            "extracted_data": self.extracted_data,
            "services_tried": self.services_tried,
            "service_used": self.service_used,
            "error_message": self.error_message,
        }


class ProcessingPipeline:
    """
    Main pipeline for processing medical documents.
    Handles classification, service selection, and fallbacks.
    """
    
    # Processing chain - services to try for each document type
    PROCESSING_CHAIN = {
        DocumentType.LAB_REPORT: [
            ('eka_lab_report', EkaLabReportService),
            ('openai', OpenAIService),
        ],
        DocumentType.PRESCRIPTION: [
            ('openai', OpenAIService),  # Primary for handwritten
        ],
        DocumentType.CLINICAL_TEXT: [
            ('eka_scribe', EkaScribeService),  # Primary for text
            ('openai', OpenAIService),  # Fallback
        ],
        DocumentType.STRUCTURED_DATA: [
            ('direct_parser', DirectParserService),
        ],
        DocumentType.UNKNOWN: [
            ('openai', OpenAIService),  # Let OpenAI figure it out
        ],
    }
    
    def __init__(self):
        self.classifier = DocumentClassifier()
        
        # Initialize services
        self.services = {
            'eka_scribe': EkaScribeService(),
            'eka_lab_report': EkaLabReportService(),
            'openai': OpenAIService(),
            'direct_parser': DirectParserService(),
        }
    
    def process(
        self,
        content: Any,
        content_type: str,
        filename: Optional[str] = None,
        user_hint: Optional[str] = None,
        **kwargs
    ) -> PipelineResult:
        """
        Process a document through the pipeline.
        
        Args:
            content: File content (bytes) or text (str)
            filename: Original filename (optional)
            content_type: MIME type
            user_hint: User's hint about document type (e.g., 'lab_report', 'prescription')
            **kwargs: Additional parameters for services
            
        Returns:
            PipelineResult with extracted data
        """
        logger.info(f"[Pipeline] Processing: {filename}, type: {content_type}")
        
        # Step 1: Classify document
        doc_type, content_category = self.classifier.classify(
            filename=filename,
            content_type=content_type,
            content=content if isinstance(content, bytes) else content.encode() if isinstance(content, str) else None,
            user_hint=user_hint
        )
        
        logger.info(f"[Pipeline] Classified as: {doc_type.value}, {content_category.value}")
        
        # Step 2: Get processing chain for this document type
        chain = self.PROCESSING_CHAIN.get(doc_type, self.PROCESSING_CHAIN[DocumentType.UNKNOWN])
        
        # Step 3: Try each service in the chain
        services_tried = []
        errors = []
        raw_responses = {}
        
        for service_name, service_class in chain:
            service = self.services.get(service_name)
            
            if not service:
                logger.warning(f"[Pipeline] Service not found: {service_name}")
                continue
            
            if not service.is_available():
                logger.info(f"[Pipeline] Service not available: {service_name}")
                continue
            
            services_tried.append(service_name)
            logger.info(f"[Pipeline] Trying service: {service_name}")
            
            try:
                # Prepare content for service
                service_content = self._prepare_content(content, content_category, service_name)
                service_content_type = self._get_service_content_type(content_type, content_category)
                
                # Add document type hint for OpenAI
                service_kwargs = {**kwargs}
                if service_name == 'openai':
                    service_kwargs['document_type'] = doc_type.value
                
                # Process
                result = service.process(service_content, service_content_type, **service_kwargs)
                raw_responses[service_name] = result.raw_response
                
                if result.status == ProcessingStatus.SUCCESS:
                    logger.info(f"[Pipeline] Success with {service_name}")
                    
                    return PipelineResult(
                        success=True,
                        document_type=doc_type.value,
                        content_category=content_category.value,
                        extracted_data=result.extracted_data,
                        services_tried=services_tried,
                        service_used=service_name,
                        raw_responses=raw_responses,
                    )
                else:
                    errors.append(f"{service_name}: {result.error_message}")
                    logger.warning(f"[Pipeline] Failed with {service_name}: {result.error_message}")
                    
            except Exception as e:
                errors.append(f"{service_name}: {str(e)}")
                logger.error(f"[Pipeline] Exception with {service_name}: {str(e)}")
        
        # All services failed
        logger.error(f"[Pipeline] All services failed for {filename}")
        
        return PipelineResult(
            success=False,
            document_type=doc_type.value,
            content_category=content_category.value,
            extracted_data={},
            services_tried=services_tried,
            service_used="",
            error_message="; ".join(errors) if errors else "No available services",
            raw_responses=raw_responses,
        )
    
    def process_text(self, text: str, **kwargs) -> PipelineResult:
        """
        Convenience method for processing plain text (clinical notes, transcripts).
        
        Args:
            text: Clinical text to process
            **kwargs: Additional parameters
            
        Returns:
            PipelineResult
        """
        return self.process(
            content=text,
            filename="clinical_text.txt",
            content_type="text/plain",
            user_hint="clinical_text",
            **kwargs
        )
    
    def process_batch(
        self,
        content: bytes,
        filename: str,
        content_type: str,
        **kwargs
    ) -> PipelineResult:
        """
        Process batch data (CSV/JSON).
        
        Args:
            content: File content as bytes
            filename: Original filename
            content_type: MIME type (text/csv or application/json)
            **kwargs: Additional parameters (e.g., column_mapping)
            
        Returns:
            PipelineResult with list of records
        """
        return self.process(
            content=content,
            filename=filename,
            content_type=content_type,
            user_hint="structured_data",
            **kwargs
        )
    
    def _prepare_content(self, content: Any, category: ContentCategory, service_name: str) -> Any:
        """Prepare content for a specific service."""
        # EkaScribe expects text string
        if service_name == 'eka_scribe':
            if isinstance(content, bytes):
                return content.decode('utf-8', errors='ignore')
            return str(content)
        
        # Other services expect bytes for files, text for text category
        if category == ContentCategory.TEXT:
            if isinstance(content, bytes):
                return content.decode('utf-8', errors='ignore')
            return str(content)
        
        # Return bytes for binary content
        if isinstance(content, str):
            return content.encode('utf-8')
        return content
    
    def _get_service_content_type(self, original_type: str, category: ContentCategory) -> str:
        """Get content type for service."""
        if category == ContentCategory.TEXT:
            return 'text'
        return original_type
    
    def get_available_services(self) -> Dict[str, bool]:
        """Get availability status of all services."""
        return {
            name: service.is_available()
            for name, service in self.services.items()
        }


# Singleton instance for easy access
_pipeline_instance = None


def get_pipeline() -> ProcessingPipeline:
    """Get or create the pipeline singleton."""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = ProcessingPipeline()
    return _pipeline_instance
