from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count, Q
from django.db.models.functions import Coalesce

from apps.documents.models import Document
from apps.patients.models import Patient, Disease, PatientDisease


class DashboardView(APIView):
    """Main dashboard statistics."""
    
    def get(self, request):
        # Document stats
        total_documents = Document.objects.count()
        processed_documents = Document.objects.filter(processing_status='completed').count()
        pending_documents = Document.objects.filter(processing_status='pending').count()
        failed_documents = Document.objects.filter(processing_status='failed').count()
        
        # Patient stats
        total_patients = Patient.objects.count()
        patients_with_phone = Patient.objects.exclude(phone_number__isnull=True).exclude(phone_number='').count()
        
        # Disease stats
        total_diseases = Disease.objects.count()
        total_diagnoses = PatientDisease.objects.count()
        
        # Gender distribution
        gender_distribution = list(
            Patient.objects.values('gender')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        
        # Top diseases
        top_diseases = list(
            Disease.objects.annotate(patient_count=Count('patients'))
            .order_by('-patient_count')[:10]
            .values('id', 'name', 'patient_count')
        )
        
        # Recent activity
        recent_documents = list(
            Document.objects.order_by('-created_at')[:5]
            .values('id', 'original_filename', 'processing_status', 'created_at')
        )
        
        return Response({
            'documents': {
                'total': total_documents,
                'processed': processed_documents,
                'pending': pending_documents,
                'failed': failed_documents,
            },
            'patients': {
                'total': total_patients,
                'with_contact': patients_with_phone,
            },
            'diseases': {
                'unique_diseases': total_diseases,
                'total_diagnoses': total_diagnoses,
            },
            'gender_distribution': gender_distribution,
            'top_diseases': top_diseases,
            'recent_documents': recent_documents,
        })


class DiseaseAnalyticsView(APIView):
    """Disease-level analytics."""
    
    def get(self, request):
        disease_id = request.query_params.get('disease_id')
        
        if disease_id:
            # Specific disease analytics
            try:
                disease = Disease.objects.get(id=disease_id)
            except Disease.DoesNotExist:
                return Response({'error': 'Disease not found'}, status=404)
            
            patients = Patient.objects.filter(diseases=disease)
            
            # Age group distribution for this disease
            age_groups = self._get_age_group_distribution(patients)
            
            # Gender distribution for this disease
            gender_dist = list(
                patients.values('gender')
                .annotate(count=Count('id'))
            )
            
            # Location distribution for this disease
            location_dist = list(
                patients.exclude(location='')
                .values('location')
                .annotate(count=Count('id'))
                .order_by('-count')[:10]
            )
            
            return Response({
                'disease': {
                    'id': str(disease.id),
                    'name': disease.name,
                    'category': disease.category,
                },
                'total_patients': patients.count(),
                'age_groups': age_groups,
                'gender_distribution': gender_dist,
                'location_distribution': location_dist,
            })
        
        # All diseases overview
        diseases = Disease.objects.annotate(
            patient_count=Count('patients')
        ).order_by('-patient_count')
        
        result = []
        for disease in diseases:
            patients = Patient.objects.filter(diseases=disease)
            result.append({
                'id': str(disease.id),
                'name': disease.name,
                'category': disease.category,
                'patient_count': disease.patient_count,
                'age_groups': self._get_age_group_distribution(patients),
            })
        
        return Response(result)
    
    def _get_age_group_distribution(self, queryset):
        """Calculate age group distribution."""
        age_groups = {
            '0-17': queryset.filter(age__gte=0, age__lte=17).count(),
            '18-29': queryset.filter(age__gte=18, age__lte=29).count(),
            '30-44': queryset.filter(age__gte=30, age__lte=44).count(),
            '45-59': queryset.filter(age__gte=45, age__lte=59).count(),
            '60+': queryset.filter(age__gte=60).count(),
            'Unknown': queryset.filter(age__isnull=True).count(),
        }
        return [{'age_group': k, 'count': v} for k, v in age_groups.items() if v > 0]


class LocationAnalyticsView(APIView):
    """Location-based analytics."""
    
    def get(self, request):
        # State-level distribution
        state_distribution = list(
            Patient.objects.exclude(state='')
            .values('state')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        
        # City-level distribution
        city_distribution = list(
            Patient.objects.exclude(city='')
            .values('city', 'state')
            .annotate(count=Count('id'))
            .order_by('-count')[:20]
        )
        
        # Hospital/Clinic distribution
        hospital_distribution = list(
            Patient.objects.exclude(hospital_clinic='')
            .values('hospital_clinic')
            .annotate(count=Count('id'))
            .order_by('-count')[:20]
        )
        
        # Location (general) distribution
        location_distribution = list(
            Patient.objects.exclude(location='')
            .values('location')
            .annotate(count=Count('id'))
            .order_by('-count')[:20]
        )
        
        return Response({
            'by_state': state_distribution,
            'by_city': city_distribution,
            'by_hospital': hospital_distribution,
            'by_location': location_distribution,
        })


class AgeAnalyticsView(APIView):
    """Age-based analytics."""
    
    def get(self, request):
        # Overall age distribution
        age_groups = self._get_age_groups()
        
        # Age distribution by disease
        diseases = Disease.objects.annotate(patient_count=Count('patients')).filter(patient_count__gt=0)
        
        disease_age_data = []
        for disease in diseases[:10]:  # Top 10 diseases
            patients = Patient.objects.filter(diseases=disease)
            disease_age_data.append({
                'disease': disease.name,
                'age_groups': {
                    '0-17': patients.filter(age__gte=0, age__lte=17).count(),
                    '18-29': patients.filter(age__gte=18, age__lte=29).count(),
                    '30-44': patients.filter(age__gte=30, age__lte=44).count(),
                    '45-59': patients.filter(age__gte=45, age__lte=59).count(),
                    '60+': patients.filter(age__gte=60).count(),
                }
            })
        
        # Age distribution by gender
        gender_age_data = {}
        for gender in ['male', 'female', 'other']:
            patients = Patient.objects.filter(gender=gender)
            gender_age_data[gender] = {
                '0-17': patients.filter(age__gte=0, age__lte=17).count(),
                '18-29': patients.filter(age__gte=18, age__lte=29).count(),
                '30-44': patients.filter(age__gte=30, age__lte=44).count(),
                '45-59': patients.filter(age__gte=45, age__lte=59).count(),
                '60+': patients.filter(age__gte=60).count(),
            }
        
        return Response({
            'overall': age_groups,
            'by_disease': disease_age_data,
            'by_gender': gender_age_data,
        })
    
    def _get_age_groups(self):
        """Get overall age group distribution."""
        return [
            {'age_group': '0-17', 'count': Patient.objects.filter(age__gte=0, age__lte=17).count()},
            {'age_group': '18-29', 'count': Patient.objects.filter(age__gte=18, age__lte=29).count()},
            {'age_group': '30-44', 'count': Patient.objects.filter(age__gte=30, age__lte=44).count()},
            {'age_group': '45-59', 'count': Patient.objects.filter(age__gte=45, age__lte=59).count()},
            {'age_group': '60+', 'count': Patient.objects.filter(age__gte=60).count()},
            {'age_group': 'Unknown', 'count': Patient.objects.filter(age__isnull=True).count()},
        ]
