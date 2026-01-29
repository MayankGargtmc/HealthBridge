from django.db import models
import uuid


class Document(models.Model):
    """Model to store uploaded medical documents."""
    
    DOCUMENT_TYPES = [
        ('handwritten', 'Handwritten Prescription'),
        ('printed_lab', 'Printed Lab Report'),
        ('clinical_db', 'Clinical Database Export'),
        ('other', 'Other'),
    ]
    
    PROCESSING_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to='documents/%Y/%m/%d/')
    original_filename = models.CharField(max_length=255)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default='other')
    file_type = models.CharField(max_length=50, blank=True)  # pdf, jpg, png, etc.
    file_size = models.PositiveIntegerField(default=0)  # in bytes
    
    # Processing info
    processing_status = models.CharField(max_length=20, choices=PROCESSING_STATUS, default='pending')
    processing_error = models.TextField(blank=True)
    raw_extracted_text = models.TextField(blank=True)  # Raw OCR output
    structured_data = models.JSONField(default=dict, blank=True)  # Parsed structured data
    
    # Metadata
    uploaded_by = models.CharField(max_length=255, blank=True)  # For future auth
    hospital_clinic_name = models.CharField(max_length=255, blank=True)
    source_location = models.CharField(max_length=255, blank=True)  # Where this document came from
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'
    
    def __str__(self):
        return f"{self.original_filename} ({self.get_document_type_display()})"


class ProcessingLog(models.Model):
    """Log of processing attempts for debugging."""
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='processing_logs')
    step = models.CharField(max_length=100)
    status = models.CharField(max_length=20)
    message = models.TextField(blank=True)
    api_used = models.CharField(max_length=50, blank=True)  # eka, openai, etc.
    response_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.document.original_filename} - {self.step}"
