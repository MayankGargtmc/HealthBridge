from django.contrib import admin
from .models import Document, ProcessingLog


class ProcessingLogInline(admin.TabularInline):
    model = ProcessingLog
    extra = 0
    readonly_fields = ['step', 'status', 'message', 'api_used', 'created_at']
    can_delete = False


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['original_filename', 'document_type', 'processing_status', 'created_at']
    list_filter = ['document_type', 'processing_status', 'created_at']
    search_fields = ['original_filename', 'hospital_clinic_name']
    readonly_fields = ['id', 'file_size', 'file_type', 'created_at', 'updated_at', 'processed_at']
    inlines = [ProcessingLogInline]
    
    fieldsets = (
        ('File Info', {
            'fields': ('id', 'file', 'original_filename', 'document_type', 'file_type', 'file_size')
        }),
        ('Processing', {
            'fields': ('processing_status', 'processing_error', 'raw_extracted_text', 'structured_data')
        }),
        ('Metadata', {
            'fields': ('uploaded_by', 'hospital_clinic_name', 'source_location')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'processed_at')
        }),
    )
