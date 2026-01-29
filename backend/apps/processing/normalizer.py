"""
Data Normalizer - Converts extracted data to patient records.
"""

import logging
from typing import Dict, Any, List, Optional
from django.utils import timezone

logger = logging.getLogger(__name__)


class DataNormalizer:
    """
    Normalizes extracted data and creates/updates patient records.
    """
    
    def normalize_and_save(
        self,
        extracted_data: Dict[str, Any],
        source_document=None,
        hospital_name: str = "",
        location: str = "",
    ) -> List[Any]:
        """
        Normalize extracted data and save to database.
        
        Args:
            extracted_data: Data from processing pipeline
            source_document: Document model instance (optional)
            hospital_name: Default hospital name
            location: Default location
            
        Returns:
            List of created/updated Patient instances
        """
        from apps.patients.models import Patient, Disease, PatientDisease
        
        # Handle batch data (multiple records)
        if extracted_data.get('is_batch') and 'records' in extracted_data:
            records = extracted_data['records']
            logger.info(f"[Normalizer] Processing batch of {len(records)} records")
        else:
            records = [extracted_data]
        
        created_patients = []
        
        for record in records:
            patient = self._save_patient_record(
                record=record,
                source_document=source_document,
                default_hospital=hospital_name,
                default_location=location,
            )
            if patient:
                created_patients.append(patient)
        
        logger.info(f"[Normalizer] Created/updated {len(created_patients)} patients")
        return created_patients
    
    def _save_patient_record(
        self,
        record: Dict[str, Any],
        source_document=None,
        default_hospital: str = "",
        default_location: str = "",
    ) -> Optional[Any]:
        """Save a single patient record."""
        from apps.patients.models import Patient, Disease, PatientDisease
        
        # Extract patient info
        patient_info = record.get('patient', {})
        medical_info = record.get('medical', record)  # Support both nested and flat structure
        facility_info = record.get('facility', {})
        
        # Get patient name
        name = patient_info.get('name', '').strip() if patient_info else None
        
        if not name:
            logger.warning("[Normalizer] Skipping record without patient name")
            return None
        
        # Prepare patient data
        patient_data = {
            'age': patient_info.get('age'),
            'gender': self._normalize_gender(patient_info.get('gender')),
            'phone_number': self._clean_phone(patient_info.get('phone')),
            'email': patient_info.get('email'),
            'address': patient_info.get('address', ''),
            'city': patient_info.get('city', ''),
            'state': patient_info.get('state', ''),
            'pincode': patient_info.get('pincode', ''),
            'hospital_clinic': facility_info.get('hospital_name') or default_hospital,
            'doctor_name': facility_info.get('doctor_name', ''),
            'location': default_location,
        }
        
        # Remove None values
        patient_data = {k: v for k, v in patient_data.items() if v is not None}
        
        # Create or update patient
        # Use name + phone as unique identifier if phone exists
        phone = patient_data.get('phone_number')
        
        if phone:
            patient, created = Patient.objects.update_or_create(
                name__iexact=name,
                phone_number=phone,
                defaults={**patient_data, 'name': name}
            )
        else:
            # Without phone, just match by name (may create duplicates)
            patient, created = Patient.objects.get_or_create(
                name__iexact=name,
                defaults={**patient_data, 'name': name}
            )
            if not created:
                # Update existing patient with new data
                for key, value in patient_data.items():
                    if value:  # Only update non-empty values
                        setattr(patient, key, value)
                patient.save()
        
        # Set source document
        if source_document:
            patient.source_document = source_document
            patient.save()
        
        # Add diseases
        diseases = medical_info.get('diseases', []) if isinstance(medical_info, dict) else record.get('diseases', [])
        self._add_diseases(patient, diseases, source_document)
        
        logger.info(f"[Normalizer] {'Created' if created else 'Updated'} patient: {name}")
        return patient
    
    def _add_diseases(self, patient, diseases: List[Dict], source_document=None):
        """Add diseases to patient."""
        from apps.patients.models import Disease, PatientDisease
        
        for disease_data in diseases:
            if isinstance(disease_data, str):
                disease_name = disease_data.strip()
                icd_code = None
                severity = None
            elif isinstance(disease_data, dict):
                disease_name = disease_data.get('name', '').strip()
                icd_code = disease_data.get('icd_code')
                severity = disease_data.get('severity')
            else:
                continue
            
            if not disease_name:
                continue
            
            # Normalize disease name
            disease_name = self._normalize_disease_name(disease_name)
            
            # Get or create disease
            disease, _ = Disease.objects.get_or_create(
                name__iexact=disease_name,
                defaults={
                    'name': disease_name,
                    'icd_code': icd_code or '',
                }
            )
            
            # Update ICD code if we have it and disease doesn't
            if icd_code and not disease.icd_code:
                disease.icd_code = icd_code
                disease.save()
            
            # Link patient to disease
            PatientDisease.objects.get_or_create(
                patient=patient,
                disease=disease,
                defaults={
                    'severity': severity or '',
                    'source_document': source_document,
                }
            )
    
    def _normalize_gender(self, gender: Any) -> str:
        """Normalize gender to standard value."""
        if not gender:
            return 'unknown'
        gender = str(gender).lower().strip()
        if gender in ['m', 'male', 'man']:
            return 'male'
        elif gender in ['f', 'female', 'woman']:
            return 'female'
        elif gender in ['o', 'other']:
            return 'other'
        return 'unknown'
    
    def _clean_phone(self, phone: Any) -> Optional[str]:
        """Clean phone number."""
        if not phone:
            return None
        
        # Convert to string and remove common separators
        phone = str(phone).strip()
        phone = ''.join(c for c in phone if c.isdigit() or c == '+')
        
        # Return None if too short
        if len(phone) < 10:
            return None
        
        return phone
    
    def _normalize_disease_name(self, name: str) -> str:
        """Normalize disease name (expand abbreviations, proper case)."""
        name = name.strip()
        
        # Common abbreviation expansions
        abbreviations = {
            'dm': 'Diabetes Mellitus',
            'dm2': 'Type 2 Diabetes Mellitus',
            't2dm': 'Type 2 Diabetes Mellitus',
            'dm1': 'Type 1 Diabetes Mellitus',
            't1dm': 'Type 1 Diabetes Mellitus',
            'htn': 'Hypertension',
            'cad': 'Coronary Artery Disease',
            'ckd': 'Chronic Kidney Disease',
            'copd': 'Chronic Obstructive Pulmonary Disease',
            'mi': 'Myocardial Infarction',
            'chf': 'Congestive Heart Failure',
            'af': 'Atrial Fibrillation',
            'tb': 'Tuberculosis',
            'hiv': 'HIV/AIDS',
            'acs': 'Acute Coronary Syndrome',
            'cva': 'Cerebrovascular Accident',
            'dvt': 'Deep Vein Thrombosis',
            'pe': 'Pulmonary Embolism',
            'uti': 'Urinary Tract Infection',
            'gerd': 'Gastroesophageal Reflux Disease',
            'ibs': 'Irritable Bowel Syndrome',
            'ra': 'Rheumatoid Arthritis',
            'oa': 'Osteoarthritis',
            'hypothyroid': 'Hypothyroidism',
            'hyperthyroid': 'Hyperthyroidism',
        }
        
        # Check if it's a known abbreviation
        lower_name = name.lower()
        if lower_name in abbreviations:
            return abbreviations[lower_name]
        
        # Title case if all caps or all lower
        if name.isupper() or name.islower():
            return name.title()
        
        return name


# Singleton instance
_normalizer_instance = None


def get_normalizer() -> DataNormalizer:
    """Get or create normalizer singleton."""
    global _normalizer_instance
    if _normalizer_instance is None:
        _normalizer_instance = DataNormalizer()
    return _normalizer_instance
