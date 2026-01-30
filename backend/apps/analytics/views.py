from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count, Q, Avg
from django.db.models.functions import Coalesce, TruncDate, TruncWeek
from django.utils import timezone
from datetime import timedelta

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


class SurveillanceView(APIView):
    """
    Disease surveillance and epidemic detection.
    Similar to CDC's outbreak detection system.
    """
    
    def get(self, request):
        from .epidemic_detection import EpidemicDetector
        
        detector = EpidemicDetector()
        
        # Get query parameters for filtering
        days = int(request.query_params.get('days', 30))
        
        return Response({
            'alerts': detector.detect_spikes(lookback_days=7, baseline_days=days),
            'geographic_clusters': detector.detect_geographic_clusters(),
            'age_concentrations': detector.detect_age_group_concentration(),
        })


class DiseaseTrendsView(APIView):
    """
    Disease trends over time for epidemic tracking.
    """
    
    def get(self, request):
        days = int(request.query_params.get('days', 30))
        disease_id = request.query_params.get('disease_id')
        
        start_date = timezone.now() - timedelta(days=days)
        
        # Base queryset
        queryset = PatientDisease.objects.filter(created_at__gte=start_date)
        
        if disease_id:
            queryset = queryset.filter(disease_id=disease_id)
        
        # Daily trends
        daily_trends = list(
            queryset
            .annotate(date=TruncDate('created_at'))
            .values('date', 'disease__name')
            .annotate(count=Count('id'))
            .order_by('date')
        )
        
        # Organize by disease
        trends_by_disease = {}
        for item in daily_trends:
            disease_name = item['disease__name']
            if disease_name not in trends_by_disease:
                trends_by_disease[disease_name] = []
            trends_by_disease[disease_name].append({
                'date': item['date'].isoformat() if item['date'] else None,
                'count': item['count']
            })
        
        # Weekly aggregation for longer periods
        weekly_trends = []
        if days > 14:
            weekly_data = list(
                queryset
                .annotate(week=TruncWeek('created_at'))
                .values('week', 'disease__name')
                .annotate(count=Count('id'))
                .order_by('week')
            )
            
            for item in weekly_data:
                weekly_trends.append({
                    'week': item['week'].isoformat() if item['week'] else None,
                    'disease': item['disease__name'],
                    'count': item['count']
                })
        
        return Response({
            'period_days': days,
            'daily_trends': trends_by_disease,
            'weekly_trends': weekly_trends,
        })


class ComorbidityView(APIView):
    """
    Comorbidity analysis - which diseases occur together.
    """
    
    def get(self, request):
        from .epidemic_detection import EpidemicDetector
        
        detector = EpidemicDetector()
        comorbidities = detector.get_comorbidity_analysis()
        
        return Response({
            'comorbidities': comorbidities,
            'total_analyzed': Patient.objects.annotate(
                disease_count=Count('diseases')
            ).filter(disease_count__gte=2).count()
        })


class AdvancedFiltersView(APIView):
    """
    Advanced filtering and cross-tabulation.
    Allows filtering by multiple criteria simultaneously.
    """
    
    def get(self, request):
        # Get filter parameters
        diseases = request.query_params.getlist('disease')
        age_groups = request.query_params.getlist('age_group')
        genders = request.query_params.getlist('gender')
        locations = request.query_params.getlist('location')
        states = request.query_params.getlist('state')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        # Build queryset
        queryset = Patient.objects.all()
        
        # Apply filters
        if diseases:
            queryset = queryset.filter(diseases__name__in=diseases)
        
        if age_groups:
            age_q = Q()
            for ag in age_groups:
                if ag == '0-17':
                    age_q |= Q(age__gte=0, age__lte=17)
                elif ag == '18-29':
                    age_q |= Q(age__gte=18, age__lte=29)
                elif ag == '30-44':
                    age_q |= Q(age__gte=30, age__lte=44)
                elif ag == '45-59':
                    age_q |= Q(age__gte=45, age__lte=59)
                elif ag == '60+':
                    age_q |= Q(age__gte=60)
            queryset = queryset.filter(age_q)
        
        if genders:
            queryset = queryset.filter(gender__in=genders)
        
        if locations:
            queryset = queryset.filter(location__in=locations)
        
        if states:
            queryset = queryset.filter(state__in=states)
        
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        # Get distinct patients
        queryset = queryset.distinct()
        
        # Generate statistics
        total_count = queryset.count()
        
        # Disease breakdown
        disease_breakdown = list(
            queryset.values('diseases__name')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        
        # Age breakdown
        age_breakdown = [
            {'age_group': '0-17', 'count': queryset.filter(age__gte=0, age__lte=17).count()},
            {'age_group': '18-29', 'count': queryset.filter(age__gte=18, age__lte=29).count()},
            {'age_group': '30-44', 'count': queryset.filter(age__gte=30, age__lte=44).count()},
            {'age_group': '45-59', 'count': queryset.filter(age__gte=45, age__lte=59).count()},
            {'age_group': '60+', 'count': queryset.filter(age__gte=60).count()},
            {'age_group': 'Unknown', 'count': queryset.filter(age__isnull=True).count()},
        ]
        
        # Gender breakdown
        gender_breakdown = list(
            queryset.values('gender')
            .annotate(count=Count('id'))
        )
        
        # Location breakdown
        location_breakdown = list(
            queryset.exclude(location='')
            .values('location')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )
        
        return Response({
            'total_patients': total_count,
            'filters_applied': {
                'diseases': diseases,
                'age_groups': age_groups,
                'genders': genders,
                'locations': locations,
                'states': states,
                'date_from': date_from,
                'date_to': date_to,
            },
            'disease_breakdown': disease_breakdown,
            'age_breakdown': age_breakdown,
            'gender_breakdown': gender_breakdown,
            'location_breakdown': location_breakdown,
        })


class FilterOptionsView(APIView):
    """
    Get available filter options for the dashboard.
    """
    
    def get(self, request):
        # Available diseases
        diseases = list(
            Disease.objects.annotate(patient_count=Count('patients'))
            .filter(patient_count__gt=0)
            .values('id', 'name', 'patient_count')
            .order_by('-patient_count')
        )
        
        # Available locations
        locations = list(
            Patient.objects.exclude(location='')
            .values('location')
            .annotate(count=Count('id'))
            .order_by('-count')[:50]
        )
        
        # Available states
        states = list(
            Patient.objects.exclude(state='')
            .values('state')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        
        # Available cities
        cities = list(
            Patient.objects.exclude(city='')
            .values('city')
            .annotate(count=Count('id'))
            .order_by('-count')[:50]
        )
        
        # Hospitals
        hospitals = list(
            Patient.objects.exclude(hospital_clinic='')
            .values('hospital_clinic')
            .annotate(count=Count('id'))
            .order_by('-count')[:50]
        )
        
        return Response({
            'diseases': diseases,
            'locations': locations,
            'states': states,
            'cities': cities,
            'hospitals': hospitals,
            'age_groups': ['0-17', '18-29', '30-44', '45-59', '60+'],
            'genders': ['male', 'female', 'other', 'unknown'],
        })
