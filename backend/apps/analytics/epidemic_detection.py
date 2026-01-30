"""
Epidemic Detection and Alert System
Similar to CDC's outbreak detection methodology
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from django.db.models import Count, Avg, F
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from django.utils import timezone

logger = logging.getLogger(__name__)


class EpidemicDetector:
    """
    Detects potential disease outbreaks and epidemics based on:
    1. Sudden increase in disease cases (spike detection)
    2. Geographic clustering (hotspot detection)
    3. Age group concentration
    4. Comparison with historical baseline
    """
    
    # Thresholds for alerts (lowered for better detection with limited data)
    SPIKE_THRESHOLD = 1.3  # 30% increase triggers warning
    CRITICAL_SPIKE_THRESHOLD = 1.5  # 50% increase triggers critical alert
    CLUSTER_MIN_CASES = 1  # Minimum cases to consider a cluster (lowered from 5)
    
    def __init__(self):
        from apps.patients.models import Patient, Disease, PatientDisease
        self.Patient = Patient
        self.Disease = Disease
        self.PatientDisease = PatientDisease
    
    def get_disease_trends(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get disease trends over time.
        Returns daily/weekly case counts for each disease.
        """
        start_date = timezone.now() - timedelta(days=days)
        
        # Get cases by disease and date
        trends = (
            self.PatientDisease.objects
            .filter(created_at__gte=start_date)
            .annotate(date=TruncDate('created_at'))
            .values('disease__name', 'date')
            .annotate(count=Count('id'))
            .order_by('disease__name', 'date')
        )
        
        # Organize by disease
        disease_trends = {}
        for item in trends:
            disease_name = item['disease__name']
            if disease_name not in disease_trends:
                disease_trends[disease_name] = []
            disease_trends[disease_name].append({
                'date': item['date'].isoformat() if item['date'] else None,
                'count': item['count']
            })
        
        return [
            {'disease': name, 'trend': data}
            for name, data in disease_trends.items()
        ]
    
    def detect_spikes(self, lookback_days: int = 7, baseline_days: int = 30) -> List[Dict[str, Any]]:
        """
        Detect sudden spikes in disease cases.
        Compares recent period to historical baseline.
        """
        now = timezone.now()
        recent_start = now - timedelta(days=lookback_days)
        baseline_start = now - timedelta(days=baseline_days)
        
        alerts = []
        
        diseases = self.Disease.objects.annotate(
            total_cases=Count('patients')
        ).filter(total_cases__gt=0)
        
        for disease in diseases:
            # Recent cases
            recent_cases = self.PatientDisease.objects.filter(
                disease=disease,
                created_at__gte=recent_start
            ).count()
            
            # Baseline average (excluding recent period)
            baseline_cases = self.PatientDisease.objects.filter(
                disease=disease,
                created_at__gte=baseline_start,
                created_at__lt=recent_start
            ).count()
            
            baseline_days_count = (baseline_days - lookback_days)
            baseline_avg = baseline_cases / baseline_days_count * lookback_days if baseline_days_count > 0 else 0
            
            if baseline_avg > 0:
                ratio = recent_cases / baseline_avg
                
                if ratio >= self.CRITICAL_SPIKE_THRESHOLD:
                    alerts.append({
                        'disease': disease.name,
                        'disease_id': str(disease.id),
                        'severity': 'critical',
                        'recent_cases': recent_cases,
                        'baseline_avg': round(baseline_avg, 1),
                        'increase_ratio': round(ratio, 2),
                        'message': f'{disease.name}: {recent_cases} cases in last {lookback_days} days '
                                   f'({round((ratio-1)*100)}% above normal)'
                    })
                elif ratio >= self.SPIKE_THRESHOLD:
                    alerts.append({
                        'disease': disease.name,
                        'disease_id': str(disease.id),
                        'severity': 'warning',
                        'recent_cases': recent_cases,
                        'baseline_avg': round(baseline_avg, 1),
                        'increase_ratio': round(ratio, 2),
                        'message': f'{disease.name}: elevated cases detected'
                    })
            elif recent_cases >= self.CLUSTER_MIN_CASES:
                # New disease emergence
                alerts.append({
                    'disease': disease.name,
                    'disease_id': str(disease.id),
                    'severity': 'warning',
                    'recent_cases': recent_cases,
                    'baseline_avg': 0,
                    'increase_ratio': None,
                    'message': f'{disease.name}: new disease emergence with {recent_cases} cases'
                })
        
        # Sort by severity and ratio
        alerts.sort(key=lambda x: (
            0 if x['severity'] == 'critical' else 1,
            -(x['increase_ratio'] or 0)
        ))
        
        return alerts
    
    def detect_geographic_clusters(self) -> List[Dict[str, Any]]:
        """
        Detect geographic clustering of diseases (hotspots).
        """
        clusters = []
        
        # By location
        location_clusters = (
            self.Patient.objects
            .exclude(location='')
            .values('location')
            .annotate(
                patient_count=Count('id'),
                disease_count=Count('diseases', distinct=True)
            )
            .filter(patient_count__gte=self.CLUSTER_MIN_CASES)
            .order_by('-patient_count')[:20]
        )
        
        for cluster in location_clusters:
            # Get diseases in this location
            diseases_in_location = list(
                self.Patient.objects
                .filter(location=cluster['location'])
                .values('diseases__name')
                .annotate(count=Count('id'))
                .order_by('-count')[:5]
            )
            
            clusters.append({
                'type': 'location',
                'location': cluster['location'],
                'patient_count': cluster['patient_count'],
                'disease_count': cluster['disease_count'],
                'top_diseases': [
                    {'name': d['diseases__name'], 'count': d['count']}
                    for d in diseases_in_location if d['diseases__name']
                ]
            })
        
        # By state
        state_clusters = (
            self.Patient.objects
            .exclude(state='')
            .values('state')
            .annotate(
                patient_count=Count('id'),
                disease_count=Count('diseases', distinct=True)
            )
            .filter(patient_count__gte=self.CLUSTER_MIN_CASES)
            .order_by('-patient_count')[:10]
        )
        
        for cluster in state_clusters:
            diseases_in_state = list(
                self.Patient.objects
                .filter(state=cluster['state'])
                .values('diseases__name')
                .annotate(count=Count('id'))
                .order_by('-count')[:5]
            )
            
            clusters.append({
                'type': 'state',
                'state': cluster['state'],
                'patient_count': cluster['patient_count'],
                'disease_count': cluster['disease_count'],
                'top_diseases': [
                    {'name': d['diseases__name'], 'count': d['count']}
                    for d in diseases_in_state if d['diseases__name']
                ]
            })
        
        return clusters
    
    def detect_age_group_concentration(self) -> List[Dict[str, Any]]:
        """
        Detect diseases concentrated in specific age groups.
        Useful for identifying pediatric outbreaks, geriatric issues, etc.
        """
        concentrations = []
        
        age_ranges = [
            ('0-17', 0, 17, 'Pediatric'),
            ('18-29', 18, 29, 'Young Adult'),
            ('30-44', 30, 44, 'Adult'),
            ('45-59', 45, 59, 'Middle Age'),
            ('60+', 60, 200, 'Elderly'),
        ]
        
        diseases = self.Disease.objects.annotate(
            total_patients=Count('patients')
        ).filter(total_patients__gte=1)  # Include diseases with any patients
        
        for disease in diseases:
            patients = self.Patient.objects.filter(diseases=disease)
            total = patients.count()
            
            if total < 1:
                continue
            
            age_distribution = {}
            for label, min_age, max_age, desc in age_ranges:
                count = patients.filter(age__gte=min_age, age__lte=max_age).count()
                age_distribution[label] = {
                    'count': count,
                    'percentage': round(count / total * 100, 1) if total > 0 else 0,
                    'description': desc
                }
            
            # Find dominant age group (>30% concentration for smaller datasets)
            for label, data in age_distribution.items():
                if data['percentage'] >= 30:
                    concentrations.append({
                        'disease': disease.name,
                        'disease_id': str(disease.id),
                        'dominant_age_group': label,
                        'concentration': data['percentage'],
                        'patient_count': data['count'],
                        'total_patients': total,
                        'description': f"{disease.name} primarily affects {data['description']} population",
                        'all_age_groups': age_distribution
                    })
                    break
        
        concentrations.sort(key=lambda x: -x['concentration'])
        return concentrations
    
    def get_comorbidity_analysis(self) -> List[Dict[str, Any]]:
        """
        Analyze disease co-occurrence patterns.
        Identifies common comorbidities.
        """
        from django.db.models import Q
        
        # Get patients with multiple diseases
        patients_with_comorbidities = (
            self.Patient.objects
            .annotate(disease_count=Count('diseases'))
            .filter(disease_count__gte=2)
        )
        
        # Count disease pairs
        pair_counts = {}
        for patient in patients_with_comorbidities:
            diseases = list(patient.diseases.values_list('name', flat=True))
            diseases.sort()  # Sort for consistent pairing
            
            for i in range(len(diseases)):
                for j in range(i + 1, len(diseases)):
                    pair = (diseases[i], diseases[j])
                    pair_counts[pair] = pair_counts.get(pair, 0) + 1
        
        # Convert to list and sort
        comorbidities = [
            {
                'disease_1': pair[0],
                'disease_2': pair[1],
                'co_occurrence_count': count,
            }
            for pair, count in pair_counts.items()
            if count >= 1  # Include all disease pairs (lowered from 2)
        ]
        
        comorbidities.sort(key=lambda x: -x['co_occurrence_count'])
        return comorbidities[:20]  # Top 20 comorbidities
    
    def get_full_surveillance_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive surveillance report.
        """
        return {
            'generated_at': timezone.now().isoformat(),
            'alerts': self.detect_spikes(),
            'geographic_clusters': self.detect_geographic_clusters(),
            'age_concentrations': self.detect_age_group_concentration(),
            'comorbidities': self.get_comorbidity_analysis(),
            'trends': self.get_disease_trends(days=30),
        }
