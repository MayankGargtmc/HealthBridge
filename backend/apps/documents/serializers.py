from rest_framework import serializers
from .models import Document, ProcessingLog


class ProcessingLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessingLog
        fields = ['id', 'step', 'status', 'message', 'api_used', 'created_at']


class DocumentSerializer(serializers.ModelSerializer):
    processing_logs = ProcessingLogSerializer(many=True, read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'file', 'file_url', 'original_filename', 'document_type',
            'file_type', 'file_size', 'processing_status', 'processing_error',
            'raw_extracted_text', 'structured_data', 'uploaded_by',
            'hospital_clinic_name', 'source_location', 'created_at',
            'updated_at', 'processed_at', 'processing_logs'
        ]
        read_only_fields = [
            'id', 'file_type', 'file_size', 'processing_status',
            'processing_error', 'raw_extracted_text', 'structured_data',
            'created_at', 'updated_at', 'processed_at'
        ]
    
    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class DocumentUploadSerializer(serializers.ModelSerializer):
    """Simplified serializer for document upload."""
    
    class Meta:
        model = Document
        fields = [
            'file', 'document_type', 'hospital_clinic_name', 
            'source_location', 'uploaded_by'
        ]
    
    def create(self, validated_data):
        file = validated_data.get('file')
        validated_data['original_filename'] = file.name
        validated_data['file_type'] = file.content_type
        validated_data['file_size'] = file.size
        return super().create(validated_data)


class BulkUploadSerializer(serializers.Serializer):
    """Serializer for bulk document upload."""
    
    files = serializers.ListField(
        child=serializers.FileField(),
        allow_empty=False
    )
    document_type = serializers.ChoiceField(
        choices=Document.DOCUMENT_TYPES,
        default='other'
    )
    hospital_clinic_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    source_location = serializers.CharField(max_length=255, required=False, allow_blank=True)
