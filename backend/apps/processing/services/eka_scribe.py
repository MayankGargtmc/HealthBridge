"""
EkaScribe Service - For processing unstructured clinical text/transcripts.
PRIMARY service for extracting diseases and diagnoses.

API Endpoint: http://ekascribe.orbi.orbi/generate_eka_emr_template
"""

import logging
import httpx
from typing import Any, Dict, Optional
from django.conf import settings

from .base import BaseProcessingService, ProcessingResult, ProcessingStatus

logger = logging.getLogger(__name__)


class EkaScribeService(BaseProcessingService):
    """
    Service to process clinical notes/transcripts using EkaScribe API.
    This is the PRIMARY service for extracting diseases from clinical text.
    """
    
    service_name = "eka_scribe"
    
    def __init__(self):
        self.api_url = getattr(settings, 'EKASCRIBE_API_URL', 'http://ekascribe.orbi.orbi/generate_eka_emr_template')
        self.timeout = 60.0
    
    def is_available(self) -> bool:
        """EkaScribe doesn't require API key, so it's always available if URL is set."""
        return bool(self.api_url)
    
    def process(self, content: Any, content_type: str = "text", **kwargs) -> ProcessingResult:
        """
        Process clinical text/transcript using EkaScribe API.
        
        Args:
            content: Clinical text/transcript as string
            content_type: Should be "text" for this service
            **kwargs: 
                - model_type: "pro" or "basic" (default: "pro")
                - txn_id: Transaction ID for tracking (optional)
                
        Returns:
            ProcessingResult with extracted EMR data
        """
        if not isinstance(content, str) or not content.strip():
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                error_message="Content must be a non-empty string",
                service_used=self.service_name
            )
        
        model_type = kwargs.get('model_type', 'pro')
        txn_id = kwargs.get('txn_id', 'healthbridge')
        
        try:
            payload = {
                "transcript": content,
                "model_type": model_type,
                "txn_id": txn_id,
                "response_type": "json"
            }
            
            logger.info(f"[EkaScribe] Processing transcript, length: {len(content)} chars")
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    self.api_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                result = response.json()
            
            logger.info(f"[EkaScribe] Successfully processed transcript")
            
            # Extract structured data from response
            extracted_data = self._parse_response(result)
            
            return ProcessingResult(
                status=ProcessingStatus.SUCCESS,
                raw_response=result,
                extracted_data=extracted_data,
                service_used=self.service_name,
                confidence_score=0.85  # EkaScribe is generally reliable
            )
            
        except httpx.HTTPStatusError as e:
            logger.error(f"[EkaScribe] HTTP error: {e.response.status_code} - {e.response.text}")
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                error_message=f"HTTP {e.response.status_code}: {e.response.text[:200]}",
                service_used=self.service_name
            )
        except httpx.RequestError as e:
            logger.error(f"[EkaScribe] Request error: {str(e)}")
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                error_message=f"Request failed: {str(e)}",
                service_used=self.service_name
            )
        except Exception as e:
            logger.error(f"[EkaScribe] Unexpected error: {str(e)}")
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                error_message=str(e),
                service_used=self.service_name
            )
    
    def _parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse EkaScribe response and extract relevant fields.
        
        Expected response structure (based on EMR template):
        {
            "patient_info": {...},
            "chief_complaints": [...],
            "diagnosis": [...],
            "vitals": {...},
            "investigations": [...],
            "medications": [...],
            ...
        }
        """
        extracted = {
            "patient": {},
            "diseases": [],
            "symptoms": [],
            "medications": [],
            "lab_results": [],
            "vitals": {},
            "facility": {}
        }
        
        # Patient info
        patient_info = response.get('patient_info', {})
        if patient_info:
            extracted["patient"] = {
                "name": patient_info.get('name'),
                "age": self._parse_age(patient_info.get('age')),
                "gender": self._normalize_gender(patient_info.get('gender')),
                "phone": patient_info.get('phone') or patient_info.get('mobile'),
            }
        
        # Diagnoses/Diseases - PRIMARY DATA WE WANT
        diagnoses = response.get('diagnosis', []) or response.get('diagnoses', [])
        if isinstance(diagnoses, list):
            for diag in diagnoses:
                if isinstance(diag, str):
                    extracted["diseases"].append({
                        "name": diag.strip(),
                        "icd_code": None,
                        "severity": None
                    })
                elif isinstance(diag, dict):
                    extracted["diseases"].append({
                        "name": diag.get('name') or diag.get('diagnosis', ''),
                        "icd_code": diag.get('icd_code') or diag.get('code'),
                        "severity": diag.get('severity')
                    })
        
        # Also check for conditions/medical_history
        conditions = response.get('conditions', []) or response.get('medical_history', [])
        if isinstance(conditions, list):
            for cond in conditions:
                if isinstance(cond, str) and cond.strip():
                    # Avoid duplicates
                    existing_names = [d['name'].lower() for d in extracted["diseases"]]
                    if cond.strip().lower() not in existing_names:
                        extracted["diseases"].append({
                            "name": cond.strip(),
                            "icd_code": None,
                            "severity": None
                        })
        
        # Chief complaints / Symptoms
        complaints = response.get('chief_complaints', []) or response.get('complaints', [])
        if isinstance(complaints, list):
            for complaint in complaints:
                if isinstance(complaint, str):
                    extracted["symptoms"].append(complaint)
                elif isinstance(complaint, dict):
                    extracted["symptoms"].append(complaint.get('complaint', str(complaint)))
        
        # Vitals
        vitals = response.get('vitals', {})
        if vitals:
            extracted["vitals"] = {
                "blood_pressure": vitals.get('bp') or vitals.get('blood_pressure'),
                "pulse": vitals.get('pulse') or vitals.get('heart_rate'),
                "temperature": vitals.get('temperature'),
                "spo2": vitals.get('spo2') or vitals.get('oxygen_saturation'),
                "weight": vitals.get('weight'),
                "height": vitals.get('height'),
            }
        
        # Medications
        medications = response.get('medications', []) or response.get('prescriptions', [])
        if isinstance(medications, list):
            for med in medications:
                if isinstance(med, str):
                    extracted["medications"].append({"name": med})
                elif isinstance(med, dict):
                    extracted["medications"].append({
                        "name": med.get('name') or med.get('drug_name', ''),
                        "dosage": med.get('dosage') or med.get('dose'),
                        "frequency": med.get('frequency'),
                        "duration": med.get('duration'),
                    })
        
        # Lab results / Investigations
        investigations = response.get('investigations', []) or response.get('lab_results', [])
        if isinstance(investigations, list):
            for inv in investigations:
                if isinstance(inv, str):
                    extracted["lab_results"].append({"test": inv})
                elif isinstance(inv, dict):
                    extracted["lab_results"].append({
                        "test": inv.get('name') or inv.get('test_name', ''),
                        "value": inv.get('value') or inv.get('result'),
                        "unit": inv.get('unit'),
                        "date": inv.get('date'),
                    })
        
        return extracted
    
    def _parse_age(self, age_value: Any) -> Optional[int]:
        """Parse age from various formats."""
        if age_value is None:
            return None
        if isinstance(age_value, int):
            return age_value
        if isinstance(age_value, str):
            # Try to extract number from strings like "45 years", "45Y", etc.
            import re
            match = re.search(r'(\d+)', age_value)
            if match:
                return int(match.group(1))
        return None
    
    def _normalize_gender(self, gender: Any) -> Optional[str]:
        """Normalize gender to standard values."""
        if not gender:
            return None
        gender = str(gender).lower().strip()
        if gender in ['m', 'male', 'man']:
            return 'male'
        elif gender in ['f', 'female', 'woman']:
            return 'female'
        elif gender in ['o', 'other']:
            return 'other'
        return None
