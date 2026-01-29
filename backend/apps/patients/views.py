from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.http import HttpResponse
import pandas as pd
from io import BytesIO

from .models import Patient, Disease, PatientDisease
from .serializers import (
    PatientSerializer, 
    PatientListSerializer, 
    PatientExportSerializer,
    DiseaseSerializer
)


class DiseaseViewSet(viewsets.ModelViewSet):
    """ViewSet for managing diseases."""
    queryset = Disease.objects.all()
    serializer_class = DiseaseSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category']
    search_fields = ['name', 'abbreviations']


class PatientViewSet(viewsets.ModelViewSet):
    """ViewSet for managing patients."""
    queryset = Patient.objects.prefetch_related('diseases').all()
    serializer_class = PatientSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['gender', 'city', 'district', 'state', 'hospital_clinic']
    search_fields = ['name', 'phone_number', 'location']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PatientListSerializer
        return PatientSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by disease
        disease_id = self.request.query_params.get('disease')
        if disease_id:
            queryset = queryset.filter(diseases__id=disease_id)
        
        # Filter by disease name (partial match)
        disease_name = self.request.query_params.get('disease_name')
        if disease_name:
            queryset = queryset.filter(diseases__name__icontains=disease_name)
        
        # Filter by age range
        min_age = self.request.query_params.get('min_age')
        max_age = self.request.query_params.get('max_age')
        if min_age:
            queryset = queryset.filter(age__gte=int(min_age))
        if max_age:
            queryset = queryset.filter(age__lte=int(max_age))
        
        # Filter by age group
        age_group = self.request.query_params.get('age_group')
        if age_group:
            age_ranges = {
                '0-17': (0, 17),
                '18-29': (18, 29),
                '30-44': (30, 44),
                '45-59': (45, 59),
                '60+': (60, 200),
            }
            if age_group in age_ranges:
                min_a, max_a = age_ranges[age_group]
                queryset = queryset.filter(age__gte=min_a, age__lte=max_a)
        
        return queryset.distinct()
    
    @action(detail=False, methods=['get'])
    def export(self, request):
        """Export patients as CSV or Excel."""
        export_format = request.query_params.get('format', 'csv')
        
        # Get filtered queryset
        queryset = self.filter_queryset(self.get_queryset())
        serializer = PatientExportSerializer(queryset, many=True)
        
        # Create DataFrame
        df = pd.DataFrame(serializer.data)
        
        if df.empty:
            return Response(
                {'error': 'No patients to export'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Rename columns for export
        column_mapping = {
            'name': 'Patient Name',
            'age': 'Age',
            'age_group': 'Age Group',
            'gender': 'Gender',
            'phone_number': 'Phone Number',
            'email': 'Email',
            'address': 'Address',
            'city': 'City',
            'district': 'District',
            'state': 'State',
            'pincode': 'Pincode',
            'location': 'Location',
            'hospital_clinic': 'Hospital/Clinic',
            'doctor_name': 'Doctor Name',
            'diseases': 'Diseases',
            'economic_status': 'Economic Status',
            'created_at': 'Record Created'
        }
        df = df.rename(columns=column_mapping)
        
        if export_format == 'excel':
            # Export as Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Patients')
            output.seek(0)
            
            response = HttpResponse(
                output.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename=patients_export.xlsx'
            return response
        else:
            # Export as CSV
            csv_content = df.to_csv(index=False)
            response = HttpResponse(csv_content, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename=patients_export.csv'
            return response
    
    @action(detail=False, methods=['get'])
    def by_disease(self, request):
        """Get patients grouped by disease."""
        diseases = Disease.objects.all()
        result = []
        
        for disease in diseases:
            patients = Patient.objects.filter(diseases=disease)
            result.append({
                'disease': DiseaseSerializer(disease).data,
                'patient_count': patients.count(),
                'patients': PatientListSerializer(patients[:10], many=True).data  # Limit to 10
            })
        
        return Response(result)
