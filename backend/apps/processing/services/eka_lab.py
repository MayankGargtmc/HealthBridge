"""
Eka Lab Report Service - For processing lab report images/PDFs.
Extracts patient demographics and test results.

API Reference: https://developer.eka.care/api-reference/general-tools/medical/lab-report/introduction
"""

import logging
import base64
import httpx
from typing import Any, Dict, Optional
from django.conf import settings

from .base import BaseProcessingService, ProcessingResult, ProcessingStatus

logger = logging.getLogger(__name__)


# Mapping of abnormal lab values to potential diseases/conditions
LAB_VALUE_DISEASE_MAPPING = {
    'hba1c': {
        'high': [{'name': 'Diabetes Mellitus', 'threshold': 6.5}],
    },
    'fasting_glucose': {
        'high': [{'name': 'Diabetes Mellitus', 'threshold': 126}],
    },
    'blood_sugar': {
        'high': [{'name': 'Diabetes Mellitus', 'threshold': 200}],
    },
    'creatinine': {
        'high': [{'name': 'Chronic Kidney Disease', 'threshold': 1.3}],
    },
    'hemoglobin': {
        'low': [{'name': 'Anemia', 'threshold': 12}],
    },
    'tsh': {
        'high': [{'name': 'Hypothyroidism', 'threshold': 4.5}],
        'low': [{'name': 'Hyperthyroidism', 'threshold': 0.4}],
    },
    'cholesterol': {
        'high': [{'name': 'Hyperlipidemia', 'threshold': 200}],
    },
    'ldl': {
        'high': [{'name': 'Hyperlipidemia', 'threshold': 130}],
    },
    'triglycerides': {
        'high': [{'name': 'Hypertriglyceridemia', 'threshold': 150}],
    },
    'uric_acid': {
        'high': [{'name': 'Hyperuricemia', 'threshold': 7}],
    },
    'bilirubin': {
        'high': [{'name': 'Liver Disease', 'threshold': 1.2}],
    },
    'sgpt': {
        'high': [{'name': 'Liver Disease', 'threshold': 40}],
    },
    'sgot': {
        'high': [{'name': 'Liver Disease', 'threshold': 40}],
    },
}


class EkaLabReportService(BaseProcessingService):
    """
    Service to process lab reports using Eka Care Lab Report API.
    Extracts patient info, test results, and can infer diseases from abnormal values.
    """
    
    service_name = "eka_lab_report"
    
    def __init__(self):
        self.api_key = getattr(settings, 'EKA_API_KEY', '')
        self.base_url = getattr(settings, 'EKA_API_BASE_URL', 'https://api.eka.care')
        self.timeout = 90.0  # Lab report processing can take time
    
    def is_available(self) -> bool:
        """Check if Eka API key is configured."""
        return bool(self.api_key)
    
    def process(self, content: bytes, content_type: str, **kwargs) -> ProcessingResult:
        """
        Process a lab report file using Eka Care API.
        
        Args:
            content: File content as bytes
            content_type: MIME type (application/pdf, image/jpeg, image/png)
            **kwargs:
                - infer_diseases: Whether to infer diseases from abnormal values (default: True)
                
        Returns:
            ProcessingResult with extracted data
        """
        if not self.is_available():
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                error_message="Eka API key not configured",
                service_used=self.service_name
            )
        
        if not content:
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                error_message="No content provided",
                service_used=self.service_name
            )
        
        infer_diseases = kwargs.get('infer_diseases', True)
        
        try:
            # Encode file to base64
            file_base64 = base64.b64encode(content).decode('utf-8')
            
            # Determine file type for API
            file_type = self._get_file_type(content_type)
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            
            payload = {
                "file": file_base64,
                "file_type": file_type,
            }
            
            logger.info(f"[EkaLab] Processing lab report, type: {file_type}")
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/v1/lab-report/extract",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
            
            logger.info(f"[EkaLab] Successfully processed lab report")
            
            # Parse and extract data
            extracted_data = self._parse_response(result, infer_diseases)
            
            return ProcessingResult(
                status=ProcessingStatus.SUCCESS,
                raw_response=result,
                extracted_data=extracted_data,
                service_used=self.service_name,
                confidence_score=0.9
            )
            
        except httpx.HTTPStatusError as e:
            logger.error(f"[EkaLab] HTTP error: {e.response.status_code}")
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                error_message=f"HTTP {e.response.status_code}: {e.response.text[:200]}",
                service_used=self.service_name
            )
        except Exception as e:
            logger.error(f"[EkaLab] Error: {str(e)}")
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                error_message=str(e),
                service_used=self.service_name
            )
    
    def _get_file_type(self, content_type: str) -> str:
        """Map MIME type to Eka API file type."""
        mapping = {
            'application/pdf': 'pdf',
            'image/jpeg': 'jpeg',
            'image/jpg': 'jpeg',
            'image/png': 'png',
        }
        return mapping.get(content_type.lower(), 'pdf')
    
    def _parse_response(self, response: Dict[str, Any], infer_diseases: bool = True) -> Dict[str, Any]:
        """
        Parse Eka Lab Report API response.
        
        Expected response structure:
        {
            "patient": {"name": "", "age": "", "gender": "", ...},
            "tests": [{"name": "", "value": "", "unit": "", "normal_range": "", ...}],
            "lab_info": {"name": "", "date": "", ...}
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
        patient = response.get('patient', {})
        if patient:
            extracted["patient"] = {
                "name": patient.get('name'),
                "age": self._parse_age(patient.get('age')),
                "gender": self._normalize_gender(patient.get('gender')),
                "phone": patient.get('phone') or patient.get('mobile'),
                "address": patient.get('address'),
            }
        
        # Lab results
        tests = response.get('tests', []) or response.get('results', [])
        abnormal_values = []
        
        for test in tests:
            if isinstance(test, dict):
                test_name = test.get('name') or test.get('test_name', '')
                value = test.get('value') or test.get('result')
                unit = test.get('unit', '')
                normal_range = test.get('normal_range') or test.get('reference_range', '')
                is_abnormal = test.get('is_abnormal', False) or test.get('flag', '') in ['H', 'L', 'HIGH', 'LOW']
                
                lab_result = {
                    "test": test_name,
                    "value": value,
                    "unit": unit,
                    "normal_range": normal_range,
                    "is_abnormal": is_abnormal,
                }
                extracted["lab_results"].append(lab_result)
                
                # Track abnormal values for disease inference
                if is_abnormal or self._check_if_abnormal(test_name, value, normal_range):
                    abnormal_values.append({
                        "test": test_name,
                        "value": value,
                        "is_high": self._is_high_value(test_name, value, normal_range)
                    })
        
        # Infer diseases from abnormal lab values
        if infer_diseases and abnormal_values:
            inferred_diseases = self._infer_diseases(abnormal_values)
            extracted["diseases"].extend(inferred_diseases)
        
        # Lab/Facility info
        lab_info = response.get('lab_info', {}) or response.get('laboratory', {})
        if lab_info:
            extracted["facility"] = {
                "hospital_name": lab_info.get('name') or lab_info.get('lab_name'),
                "visit_date": lab_info.get('date') or lab_info.get('report_date'),
            }
        
        return extracted
    
    def _parse_age(self, age_value: Any) -> Optional[int]:
        """Parse age from various formats."""
        if age_value is None:
            return None
        if isinstance(age_value, int):
            return age_value
        if isinstance(age_value, str):
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
        return None
    
    def _check_if_abnormal(self, test_name: str, value: Any, normal_range: str) -> bool:
        """Check if a test value is abnormal based on normal range."""
        try:
            if not value or not normal_range:
                return False
            
            # Try to parse numeric value
            import re
            value_match = re.search(r'[\d.]+', str(value))
            if not value_match:
                return False
            
            numeric_value = float(value_match.group())
            
            # Parse range like "70-100" or "< 100" or "> 10"
            range_match = re.search(r'([\d.]+)\s*-\s*([\d.]+)', normal_range)
            if range_match:
                low = float(range_match.group(1))
                high = float(range_match.group(2))
                return numeric_value < low or numeric_value > high
            
            return False
        except:
            return False
    
    def _is_high_value(self, test_name: str, value: Any, normal_range: str) -> bool:
        """Determine if value is high (vs low)."""
        try:
            import re
            value_match = re.search(r'[\d.]+', str(value))
            if not value_match:
                return False
            
            numeric_value = float(value_match.group())
            
            range_match = re.search(r'([\d.]+)\s*-\s*([\d.]+)', normal_range)
            if range_match:
                high = float(range_match.group(2))
                return numeric_value > high
            
            return False
        except:
            return False
    
    def _infer_diseases(self, abnormal_values: list) -> list:
        """Infer possible diseases from abnormal lab values."""
        inferred = []
        seen_diseases = set()
        
        for abnormal in abnormal_values:
            test_name = abnormal['test'].lower().replace(' ', '_')
            is_high = abnormal.get('is_high', True)
            
            # Check our mapping
            for key, conditions in LAB_VALUE_DISEASE_MAPPING.items():
                if key in test_name:
                    direction = 'high' if is_high else 'low'
                    if direction in conditions:
                        for disease in conditions[direction]:
                            if disease['name'] not in seen_diseases:
                                inferred.append({
                                    "name": disease['name'],
                                    "icd_code": None,
                                    "severity": None,
                                    "source": f"Inferred from abnormal {abnormal['test']}"
                                })
                                seen_diseases.add(disease['name'])
        
        return inferred
