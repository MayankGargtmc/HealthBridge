"""
API Views for Processing.
"""

import logging
import json
import base64
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.core.files.uploadedfile import InMemoryUploadedFile

from .serializers import (
    DocumentUploadSerializer,
    BatchUploadSerializer,
    TextProcessSerializer,
    ProcessingResultSerializer,
    BulkProcessingResultSerializer,
)
from .pipeline import ProcessingPipeline
from .normalizer import get_normalizer
from .classifier import DocumentType

logger = logging.getLogger(__name__)


class ProcessDocumentView(APIView):
    """
    Process a single document (PDF, image, or text).
    
    POST /api/process/document/
    """
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def post(self, request):
        serializer = DocumentUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        pipeline = ProcessingPipeline()
        normalizer = get_normalizer()
        
        try:
            # Determine input type
            if data.get('file'):
                file = data['file']
                file_name = file.name
                content_type = file.content_type
                file_content = file.read()
                
                logger.info(f"[ProcessDocument] Processing file: {file_name} ({content_type})")
                
                # Determine document type
                if data['document_type'] != 'auto':
                    doc_type = self._get_document_type(data['document_type'])
                else:
                    doc_type = None  # Let pipeline classify
                
                # Process based on content type
                if content_type in ['text/csv', 'application/json']:
                    # Batch data
                    result = pipeline.process_batch(
                        file_content.decode('utf-8'),
                        file_name,
                        content_type,
                    )
                elif content_type in ['image/jpeg', 'image/png', 'image/webp', 'image/gif']:
                    # Image file - pass raw bytes directly, let pipeline handle it
                    result = pipeline.process(
                        content=file_content,  # Raw bytes, not base64
                        content_type=content_type,  # Preserve original content type
                        filename=file_name,
                        document_type=doc_type,
                    )
                elif content_type == 'application/pdf':
                    # PDF file - pass raw bytes directly
                    result = pipeline.process(
                        content=file_content,  # Raw bytes, not base64
                        content_type=content_type,
                        filename=file_name,
                        document_type=doc_type,
                    )
                else:
                    # Try as text
                    try:
                        text_content = file_content.decode('utf-8')
                        result = pipeline.process_text(text_content, filename=file_name, document_type=doc_type)
                    except UnicodeDecodeError:
                        return Response({
                            'success': False,
                            'message': f'Unsupported file type: {content_type}',
                        }, status=status.HTTP_400_BAD_REQUEST)
            else:
                # Text input
                text = data.get('text', '')
                doc_type = self._get_document_type(data['document_type']) if data['document_type'] != 'auto' else None
                
                logger.info(f"[ProcessDocument] Processing text ({len(text)} chars)")
                result = pipeline.process_text(text, filename="clinical_text.txt", document_type=doc_type)
            
            # Check if processing was successful
            if not result.success:
                return Response({
                    'success': False,
                    'message': result.error_message or 'Processing failed',
                    'processing_method': result.service_used,
                }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
            
            # Normalize and save to database
            patients = normalizer.normalize_and_save(
                extracted_data=result.extracted_data,
                hospital_name=data.get('hospital_name', ''),
                location=data.get('location', ''),
            )
            
            # Prepare response
            diseases_found = self._collect_diseases(result.extracted_data)
            
            response_data = {
                'success': True,
                'message': f'Successfully processed document',
                'patients_created': len(patients),
                'diseases_found': diseases_found,
                'processing_method': result.service_used,
                'raw_data': result.raw_responses if request.query_params.get('include_raw') == 'true' else None,
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception(f"[ProcessDocument] Error processing document: {e}")
            return Response({
                'success': False,
                'message': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_document_type(self, type_str: str) -> DocumentType:
        """Convert string to DocumentType enum."""
        mapping = {
            'lab_report': DocumentType.LAB_REPORT,
            'prescription': DocumentType.PRESCRIPTION,
            'clinical_text': DocumentType.CLINICAL_TEXT,
            'structured_data': DocumentType.STRUCTURED_DATA,
        }
        return mapping.get(type_str, DocumentType.UNKNOWN)
    
    def _collect_diseases(self, data: dict) -> list:
        """Collect disease names from extracted data."""
        diseases = []
        
        # Direct diseases list
        if 'diseases' in data:
            for d in data['diseases']:
                if isinstance(d, str):
                    diseases.append(d)
                elif isinstance(d, dict) and 'name' in d:
                    diseases.append(d['name'])
        
        # From medical section
        if 'medical' in data and 'diseases' in data['medical']:
            for d in data['medical']['diseases']:
                if isinstance(d, str):
                    diseases.append(d)
                elif isinstance(d, dict) and 'name' in d:
                    diseases.append(d['name'])
        
        # From batch records
        if 'records' in data:
            for record in data['records']:
                if 'diseases' in record:
                    for d in record['diseases']:
                        if isinstance(d, str):
                            diseases.append(d)
                        elif isinstance(d, dict) and 'name' in d:
                            diseases.append(d['name'])
        
        return list(set(diseases))  # Deduplicate


class ProcessTextView(APIView):
    """
    Process clinical text directly.
    
    POST /api/process/text/
    """
    parser_classes = [JSONParser]
    
    def post(self, request):
        serializer = TextProcessSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        pipeline = ProcessingPipeline()
        normalizer = get_normalizer()
        
        try:
            # Process text - primarily for clinical notes
            result = pipeline.process_text(data['text'], filename="clinical_text.txt", document_type=DocumentType.CLINICAL_TEXT)
            
            if not result.success:
                return Response({
                    'success': False,
                    'message': result.error_message or 'Processing failed',
                }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
            
            # Normalize and save
            patients = normalizer.normalize_and_save(
                extracted_data=result.extracted_data,
                hospital_name=data.get('hospital_name', ''),
                location=data.get('location', ''),
            )
            
            # Collect diseases
            diseases = []
            if 'diseases' in result.extracted_data:
                for d in result.extracted_data['diseases']:
                    if isinstance(d, str):
                        diseases.append(d)
                    elif isinstance(d, dict):
                        diseases.append(d.get('name', ''))
            
            return Response({
                'success': True,
                'message': 'Text processed successfully',
                'patients_created': len(patients),
                'diseases_found': diseases,
                'processing_method': result.service_used,
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception(f"[ProcessText] Error: {e}")
            return Response({
                'success': False,
                'message': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProcessBatchView(APIView):
    """
    Process batch data (CSV/JSON file with multiple records).
    
    POST /api/process/batch/
    """
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        serializer = BatchUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        file = data['file']
        
        try:
            file_content = file.read().decode('utf-8')
            file_name = file.name
            content_type = file.content_type
            
            logger.info(f"[ProcessBatch] Processing batch file: {file_name}")
            
            pipeline = ProcessingPipeline()
            normalizer = get_normalizer()
            
            # Process batch
            result = pipeline.process_batch(file_content, file_name, content_type)
            
            if not result.success:
                return Response({
                    'success': False,
                    'message': result.error_message or 'Batch processing failed',
                    'total_records': 0,
                    'processed_count': 0,
                    'failed_count': 0,
                    'patients': [],
                    'errors': [result.error_message] if result.error_message else [],
                }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
            
            # Normalize and save
            patients = normalizer.normalize_and_save(
                extracted_data=result.data,
                hospital_name=data.get('hospital_name', ''),
                location=data.get('location', ''),
            )
            
            # Prepare patient summaries
            patient_summaries = []
            for patient in patients:
                diseases = list(patient.diseases.values_list('name', flat=True))
                patient_summaries.append({
                    'id': patient.id,
                    'name': patient.name,
                    'age': patient.age,
                    'gender': patient.gender,
                    'diseases': diseases,
                    'hospital': patient.hospital_clinic,
                })
            
            total_records = len(result.data.get('records', []))
            
            return Response({
                'success': True,
                'message': f'Batch processed successfully',
                'total_records': total_records,
                'processed_count': len(patients),
                'failed_count': total_records - len(patients),
                'patients': patient_summaries,
                'errors': [],
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception(f"[ProcessBatch] Error: {e}")
            return Response({
                'success': False,
                'message': str(e),
                'total_records': 0,
                'processed_count': 0,
                'failed_count': 0,
                'patients': [],
                'errors': [str(e)],
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProcessingStatusView(APIView):
    """
    Check if processing services are available.
    
    GET /api/process/status/
    """
    def get(self, request):
        from django.conf import settings
        
        services = {
            'eka_scribe': {
                'configured': bool(getattr(settings, 'EKASCRIBE_API_URL', '')),
            },
            'eka_lab_report': {
                'configured': bool(getattr(settings, 'EKA_API_KEY', '')),
            },
            'gemini': {
                'configured': bool(getattr(settings, 'GEMINI_API_KEY', '')),
                'note': 'FREE - 15 req/min, 1500 req/day',
            },
            'openai': {
                'configured': bool(getattr(settings, 'OPENAI_API_KEY', '')),
            },
            'direct_parser': {
                'configured': True,  # Always available
            },
        }
        
        return Response({
            'status': 'ok',
            'services': services,
        })
