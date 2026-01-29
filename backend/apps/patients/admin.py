from django.contrib import admin
from .models import Patient, Disease, PatientDisease


class PatientDiseaseInline(admin.TabularInline):
    model = PatientDisease
    extra = 1
    autocomplete_fields = ['disease']


@admin.register(Disease)
class DiseaseAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'icd_code', 'patient_count']
    list_filter = ['category']
    search_fields = ['name', 'abbreviations']
    
    def patient_count(self, obj):
        return obj.patients.count()
    patient_count.short_description = 'Patients'


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['name', 'age', 'gender', 'phone_number', 'location', 'hospital_clinic', 'get_diseases']
    list_filter = ['gender', 'state', 'city', 'diseases']
    search_fields = ['name', 'phone_number', 'address']
    inlines = [PatientDiseaseInline]
    
    fieldsets = (
        ('Personal Info', {
            'fields': ('name', 'age', 'gender', 'phone_number', 'email')
        }),
        ('Location', {
            'fields': ('address', 'city', 'district', 'state', 'pincode', 'location')
        }),
        ('Medical', {
            'fields': ('hospital_clinic', 'doctor_name', 'economic_status', 'notes')
        }),
        ('Source', {
            'fields': ('source_document',),
            'classes': ('collapse',)
        }),
    )
    
    def get_diseases(self, obj):
        return ', '.join(obj.disease_list[:3])
    get_diseases.short_description = 'Diseases'
