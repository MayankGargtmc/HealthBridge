"""
Serializers for Processing API.
"""

from rest_framework import serializers


class DocumentUploadSerializer(serializers.Serializer):
    """Serializer for document upload."""
    file = serializers.FileField(required=False)
    text = serializers.CharField(required=False, allow_blank=True)
    document_type = serializers.ChoiceField(
        choices=['auto', 'lab_report', 'prescription', 'clinical_text', 'structured_data'],
        default='auto',
    )
    hospital_name = serializers.CharField(required=False, allow_blank=True, default='')
    location = serializers.CharField(required=False, allow_blank=True, default='')
    
    def validate(self, attrs):
        if not attrs.get('file') and not attrs.get('text'):
            raise serializers.ValidationError(
                "Either 'file' or 'text' must be provided."
            )
        return attrs


class BatchUploadSerializer(serializers.Serializer):
    """Serializer for batch upload (CSV/JSON)."""
    file = serializers.FileField()
    hospital_name = serializers.CharField(required=False, allow_blank=True, default='')
    location = serializers.CharField(required=False, allow_blank=True, default='')


class TextProcessSerializer(serializers.Serializer):
    """Serializer for processing clinical text."""
    text = serializers.CharField()
    hospital_name = serializers.CharField(required=False, allow_blank=True, default='')
    location = serializers.CharField(required=False, allow_blank=True, default='')


class ProcessingResultSerializer(serializers.Serializer):
    """Serializer for processing results."""
    success = serializers.BooleanField()
    message = serializers.CharField()
    patients_created = serializers.IntegerField(default=0)
    patients_updated = serializers.IntegerField(default=0)
    diseases_found = serializers.ListField(child=serializers.CharField(), default=list)
    processing_method = serializers.CharField(default='')
    errors = serializers.ListField(child=serializers.CharField(), default=list)
    raw_data = serializers.DictField(required=False)


class PatientSummarySerializer(serializers.Serializer):
    """Quick patient summary serializer."""
    id = serializers.IntegerField()
    name = serializers.CharField()
    age = serializers.IntegerField(allow_null=True)
    gender = serializers.CharField()
    diseases = serializers.ListField(child=serializers.CharField())
    hospital = serializers.CharField(allow_blank=True)


class BulkProcessingResultSerializer(serializers.Serializer):
    """Serializer for bulk processing results."""
    success = serializers.BooleanField()
    total_records = serializers.IntegerField()
    processed = serializers.IntegerField()
    failed = serializers.IntegerField()
    patients = PatientSummarySerializer(many=True)
    errors = serializers.ListField(child=serializers.CharField())
