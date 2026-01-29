from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction

from .models import Document, ProcessingLog
from .serializers import DocumentSerializer, DocumentUploadSerializer, BulkUploadSerializer
from .services import DocumentProcessingService

import logging

logger = logging.getLogger(__name__)


class DocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing document uploads and processing.
    """
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['document_type', 'processing_status']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return DocumentUploadSerializer
        if self.action == 'bulk_upload':
            return BulkUploadSerializer
        return DocumentSerializer
    
    def create(self, request, *args, **kwargs):
        """Upload a single document."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = serializer.save()
        
        # Process document asynchronously (or sync for hackathon)
        process_now = request.query_params.get('process', 'false').lower() == 'true'
        if process_now:
            try:
                service = DocumentProcessingService()
                service.process_document(document)
            except Exception as e:
                logger.error(f"Error processing document: {e}")
        
        # Refresh and return full serializer
        document.refresh_from_db()
        output_serializer = DocumentSerializer(document, context={'request': request})
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def bulk_upload(self, request):
        """Upload multiple documents at once."""
        serializer = BulkUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        files = serializer.validated_data['files']
        document_type = serializer.validated_data.get('document_type', 'other')
        hospital_clinic_name = serializer.validated_data.get('hospital_clinic_name', '')
        source_location = serializer.validated_data.get('source_location', '')
        
        documents = []
        with transaction.atomic():
            for file in files:
                doc = Document.objects.create(
                    file=file,
                    original_filename=file.name,
                    document_type=document_type,
                    file_type=file.content_type,
                    file_size=file.size,
                    hospital_clinic_name=hospital_clinic_name,
                    source_location=source_location,
                )
                documents.append(doc)
        
        output_serializer = DocumentSerializer(
            documents, many=True, context={'request': request}
        )
        return Response({
            'message': f'Successfully uploaded {len(documents)} documents',
            'documents': output_serializer.data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Manually trigger processing for a document."""
        document = self.get_object()
        
        if document.processing_status == 'processing':
            return Response(
                {'error': 'Document is already being processed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            service = DocumentProcessingService()
            result = service.process_document(document)
            
            document.refresh_from_db()
            serializer = DocumentSerializer(document, context={'request': request})
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error processing document {pk}: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def process_all_pending(self, request):
        """Process all pending documents."""
        pending_docs = Document.objects.filter(processing_status='pending')
        
        service = DocumentProcessingService()
        results = {
            'processed': 0,
            'failed': 0,
            'errors': []
        }
        
        for doc in pending_docs:
            try:
                service.process_document(doc)
                results['processed'] += 1
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'document_id': str(doc.id),
                    'error': str(e)
                })
        
        return Response(results)
