"""
Eka Lab Report Service - For processing lab report images/PDFs.
Extracts patient demographics and test results.

API Reference: 
- Upload: https://developer.eka.care/api-reference/general-tools/medical/lab-report/upload-report
- Get Result: https://developer.eka.care/api-reference/general-tools/medical/lab-report/parsed-report-result
"""

import logging
import base64
import time
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
    
    API Reference:
    - Upload: POST https://api.eka.care/mr/api/v2/docs?dt=lr&task=smart
    - Get Result: GET https://api.eka.care/mr/api/v1/docs/{document_id}/result
    
    2-Step Flow:
    1. POST /mr/api/v2/docs - Upload file, get document_id
    2. GET /mr/api/v1/docs/{document_id}/result - Poll for parsed results
    """
    
    service_name = "eka_lab_report"
    
    def __init__(self):
        self.api_key = getattr(settings, 'EKA_API_KEY', '')
        self.base_url = getattr(settings, 'EKA_API_BASE_URL', 'https://api.eka.care')
        self.timeout = 90.0
        self.poll_interval = 3  # seconds between polling (processing takes 1-4 mins)
        self.max_polls = 80  # max attempts (4 minutes total)
    
    def is_available(self) -> bool:
        """Check if Eka API key is configured."""
        return bool(self.api_key)
    
    def process(self, content: Any, content_type: str, **kwargs) -> ProcessingResult:
        """
        Process a lab report/prescription using Eka Care API.
        
        Args:
            content: File content as bytes or base64 string
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
            # Handle content - could be bytes or base64 string
            if isinstance(content, bytes):
                file_bytes = content
            elif isinstance(content, str):
                # Try base64 decode
                file_bytes = base64.b64decode(content)
            else:
                file_bytes = content
            
            logger.info(f"[EkaLab] File bytes length: {len(file_bytes)}, first 20 bytes: {file_bytes[:20]}")
            
            # Step 1: Upload the file
            request_id = self._upload_file(file_bytes, content_type)
            
            if not request_id:
                return ProcessingResult(
                    status=ProcessingStatus.FAILED,
                    error_message="Failed to upload file - no request_id returned",
                    service_used=self.service_name
                )
            
            logger.info(f"[EkaLab] Uploaded file, request_id: {request_id}")
            
            # Step 2: Poll for results
            result = self._poll_for_result(request_id)
            
            if not result:
                return ProcessingResult(
                    status=ProcessingStatus.FAILED,
                    error_message="Timed out waiting for processing result",
                    service_used=self.service_name
                )
            
            logger.info(f"[EkaLab] Successfully got parsed result", extra={"result": result})
            
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
            logger.error(f"[EkaLab] HTTP error: {e.response.status_code} - {e.response.text[:200]}")
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
    
    def _upload_file(self, file_bytes: bytes, content_type: str) -> Optional[str]:
        """
        Step 1: Upload file to Eka API.
        POST /mr/api/v2/docs?task=smart
        
        Returns: document_id for polling
        """
        import io
        
        # Detect actual file type from magic bytes
        detected_type = self._detect_file_type(file_bytes)
        if detected_type:
            ext, mime_type = detected_type
        else:
            # Fallback to content type
            clean_content_type = content_type.split(';')[0].strip().lower()
            type_mapping = {
                'application/pdf': ('pdf', 'application/pdf'),
                'image/jpeg': ('jpg', 'image/jpeg'),
                'image/jpg': ('jpg', 'image/jpeg'),
                'image/png': ('png', 'image/png'),
                'image/base64': ('png', 'image/png'),
            }
            ext, mime_type = type_mapping.get(clean_content_type, ('png', 'image/png'))
        
        filename = f"document.{ext}"
        
        logger.info(f"[EkaLab] Uploading: {filename}, mime: {mime_type}, size: {len(file_bytes)} bytes")
        logger.info(f"[EkaLab] First 20 bytes (hex): {file_bytes[:20].hex()}")
        
        # Use requests library - match exactly how curl works
        import requests
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        
        # Create file tuple with mime type (like curl does)
        files = {
            'file': (filename, file_bytes, mime_type)
        }
        
        params = {
            'task': 'smart'
        }
        
        response = requests.post(
            f"{self.base_url}/mr/api/v2/docs",
            headers=headers,
            files=files,
            params=params,
            timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()
        
        document_id = data.get('document_id')
        
        logger.info(f"[EkaLab] Upload response: {data}")
        
        return document_id
    
    def _detect_file_type(self, file_bytes: bytes) -> Optional[tuple]:
        """Detect file type from magic bytes."""
        if len(file_bytes) < 8:
            return None
        
        # Check magic bytes - be very explicit about PNG detection
        # PNG: 89 50 4E 47 0D 0A 1A 0A
        if file_bytes[:8] == b'\x89PNG\r\n\x1a\n':
            logger.info(f"[EkaLab] Detected PNG from magic bytes")
            return ('png', 'image/png')
        # JPEG: FF D8 FF
        elif file_bytes[:3] == b'\xff\xd8\xff':
            logger.info(f"[EkaLab] Detected JPEG from magic bytes")
            return ('jpg', 'image/jpeg')
        # PDF: %PDF
        elif file_bytes[:4] == b'%PDF':
            logger.info(f"[EkaLab] Detected PDF from magic bytes")
            return ('pdf', 'application/pdf')
        elif file_bytes[:4] == b'GIF8':
            logger.info(f"[EkaLab] Detected GIF from magic bytes")
            return ('gif', 'image/gif')
        elif len(file_bytes) >= 12 and file_bytes[:4] == b'RIFF' and file_bytes[8:12] == b'WEBP':
            logger.info(f"[EkaLab] Detected WEBP from magic bytes")
            return ('webp', 'image/webp')
        
        logger.warning(f"[EkaLab] Could not detect file type from magic bytes: {file_bytes[:10]}")
        return None
    
    def _poll_for_result(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Step 2: Poll for parsed result.
        GET /mr/api/v1/docs/{document_id}/result
        
        Status values: queued, inprogress, completed, deleted, error
        
        Returns: Parsed result or None if timeout
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        
        for attempt in range(self.max_polls):
            logger.info(f"[EkaLab] Polling for result, attempt {attempt + 1}/{self.max_polls}")
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.base_url}/mr/api/v1/docs/{document_id}/result",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check status: queued, inprogress, completed, deleted, error
                    status = data.get('status', '').lower()
                    
                    if status == 'completed':
                        logger.info(f"[EkaLab] Processing completed!")
                        return data
                    elif status == 'error':
                        error = data.get('error', [])
                        logger.error(f"[EkaLab] Processing error: {error}")
                        return None
                    elif status == 'deleted':
                        logger.error(f"[EkaLab] Document was deleted")
                        return None
                    elif status in ['queued', 'inprogress']:
                        # Still processing, continue polling
                        logger.info(f"[EkaLab] Status: {status}, waiting...")
                        time.sleep(self.poll_interval)
                        continue
                    else:
                        # Unknown status, check if we have data anyway
                        if data.get('data'):
                            return data
                        time.sleep(self.poll_interval)
                        continue
                        
                elif response.status_code == 202:
                    # Still processing
                    time.sleep(self.poll_interval)
                    continue
                elif response.status_code == 404:
                    # Not ready yet
                    time.sleep(self.poll_interval)
                    continue
                else:
                    response.raise_for_status()
            
            time.sleep(self.poll_interval)
        
        logger.error(f"[EkaLab] Timeout waiting for result")
        return None
    
    def _parse_response(self, response: Dict[str, Any], infer_diseases: bool = True) -> Dict[str, Any]:
        """
        Parse Eka API response - handles both lab reports and prescriptions.
        
        Prescription Response:
        {
            "status": "completed",
            "data": {
                "document_classification": "prescription",
                "output": {
                    "medications": [...],
                    "meta": {"source_display_name": "..."},
                    "pii": {
                        "<s3_path>": [
                            {
                                "PageNum": 1,
                                "DocumentDate": 1352399400,
                                "Patient": {"Name": "...", "Age": {...}, "Gender": "..."},
                                "Report": {"Doctor": "...", "Facility": "..."}
                            }
                        ]
                    }
                }
            }
        }
        
        Lab Report Response:
        {
            "status": "completed",
            "data": {
                "output": {
                    "data": [...],  // lab tests
                    "pii": {...}
                }
            }
        }
        """
        extracted = {
            "patient": {},
            "diseases": [],
            "symptoms": [],
            "medications": [],
            "lab_results": [],
            "vitals": {},
            "facility": {},
            "document_type": None
        }
        
        # Get the output data
        data = response.get('data', {}) or {}
        output = data.get('output', {}) or {}
        
        # Document classification
        doc_classification = data.get('document_classification')
        extracted["document_type"] = doc_classification
        
        logger.info(f"[EkaLab] Parsing response, doc_type: {doc_classification}")
        
        # Parse PII (patient info) - handles both formats
        pii = output.get('pii', {}) or {}
        self._parse_pii(pii, extracted)
        
        # Parse meta info
        meta = output.get('meta', {}) or {}
        if meta:
            source_name = meta.get('source_display_name', '')
            if source_name and not extracted.get('facility', {}).get('hospital_name'):
                # Parse "Dr. Name | Facility" format
                if '|' in source_name:
                    parts = source_name.split('|')
                    doctor = parts[0].strip()
                    facility = parts[1].strip() if len(parts) > 1 else ''
                    extracted["facility"] = {
                        "hospital_name": facility,
                        "doctor_name": doctor,
                    }
        
        # Parse medications (for prescriptions)
        medications = output.get('medications', []) or []
        for med in medications:
            if isinstance(med, dict):
                med_name = med.get('name', '')
                frequency = med.get('frequency', {}) or {}
                linked = med.get('linked', {}) or {}
                duration = med.get('duration', {}) or {}
                
                medication_entry = {
                    "name": med_name,
                    "dosage": frequency.get('custom') or frequency.get('type'),
                    "frequency": frequency.get('custom') or frequency.get('type'),
                    "duration": duration.get('custom') or duration.get('days'),
                    "timing": med.get('timing'),
                    "eka_id": linked.get('eka_id') if linked else None,
                    "confidence": linked.get('confidence') if linked else None,
                }
                extracted["medications"].append(medication_entry)
        
        # Parse diagnosis (diseases)
        diagnoses = output.get('diagnosis', []) or []
        for diag in diagnoses:
            if isinstance(diag, dict):
                diag_name = diag.get('name', '')
                linked = diag.get('linked', {}) or {}
                
                disease_entry = {
                    "name": diag_name,
                    "icd_code": None,
                    "snomed_code": linked.get('snomedct_code') if linked else None,
                    "eka_id": linked.get('eka_id') if linked else None,
                    "confidence": linked.get('confidence') if linked else None,
                    "severity": None,
                    "source": "Extracted from document"
                }
                extracted["diseases"].append(disease_entry)
        
        # Parse symptoms
        symptoms = output.get('symptoms', []) or []
        for symptom in symptoms:
            if isinstance(symptom, dict):
                symptom_name = symptom.get('name', '')
                linked = symptom.get('linked', {}) or {}
                
                symptom_entry = {
                    "name": symptom_name,
                    "snomed_code": linked.get('snomedct_code') if linked else None,
                    "eka_id": linked.get('eka_id') if linked else None,
                    "confidence": linked.get('confidence') if linked else None,
                }
                extracted["symptoms"].append(symptom_entry)
        
        # Parse lab vitals (BP, Weight, Height, etc.)
        lab_vitals = output.get('labVitals', []) or []
        for vital in lab_vitals:
            if isinstance(vital, dict):
                vital_name = vital.get('name', '').lower()
                vital_value = vital.get('value')
                vital_unit = vital.get('unit')
                linked = vital.get('linked', {}) or {}
                
                # Map to standard vital names
                if 'bp' in vital_name or 'blood pressure' in vital_name:
                    extracted["vitals"]["blood_pressure"] = vital_value
                elif 'weight' in vital_name:
                    extracted["vitals"]["weight"] = f"{vital_value} {vital_unit}" if vital_unit else vital_value
                elif 'height' in vital_name:
                    extracted["vitals"]["height"] = f"{vital_value} {vital_unit}" if vital_unit else vital_value
                elif 'temp' in vital_name:
                    extracted["vitals"]["temperature"] = f"{vital_value} {vital_unit}" if vital_unit else vital_value
                elif 'pulse' in vital_name or 'heart rate' in vital_name:
                    extracted["vitals"]["pulse"] = vital_value
                elif 'spo2' in vital_name or 'oxygen' in vital_name:
                    extracted["vitals"]["spo2"] = vital_value
                else:
                    # Store other vitals with original name
                    extracted["vitals"][vital_name] = f"{vital_value} {vital_unit}" if vital_unit else vital_value
        
        # Parse advice
        advice_list = output.get('advice', []) or []
        advice_texts = []
        for advice in advice_list:
            if isinstance(advice, dict):
                advice_text = advice.get('text', '')
                if advice_text:
                    advice_texts.append(advice_text)
        if advice_texts:
            extracted["advice"] = advice_texts
        
        # Parse followup
        followup = output.get('followup', {}) or {}
        if followup:
            followup_date = followup.get('date')
            if followup_date:
                extracted["followup_date"] = followup_date
        
        # Parse medical history / examinations
        medical_history = output.get('medicalHistory', {}) or {}
        examinations = medical_history.get('examinations', []) or []
        if examinations:
            extracted["examinations"] = []
            for exam in examinations:
                if isinstance(exam, dict):
                    exam_name = exam.get('name', '')
                    if exam_name:
                        extracted["examinations"].append({"name": exam_name})
        
        # Parse lab results (for lab reports)
        tests = output.get('data', []) or []
        abnormal_values = []
        
        for test in tests:
            if isinstance(test, dict):
                test_name = test.get('test_name', '')
                test_eka_id = test.get('test_eka_id')
                loinc_id = test.get('loinc_id')
                confidence = test.get('confidence', 0)
                
                # Get test data (non-normalized or normalized)
                test_data = test.get('data', {}) or {}
                normalised_data = test.get('normalised_data', {}) or {}
                
                # Prefer normalized data if available
                value = normalised_data.get('value') or test_data.get('value')
                unit = normalised_data.get('unit') or test_data.get('unit') or test_data.get('unit_processed')
                normal_range = (
                    normalised_data.get('normal_range_eka') or
                    normalised_data.get('normal_range_report') or
                    test_data.get('normal_range_eka') or
                    test_data.get('normal_range_report') or
                    test_data.get('display_range')
                )
                
                # Determine if abnormal
                is_abnormal = self._check_if_abnormal(test_name, value, str(normal_range) if normal_range else '')
                
                lab_result = {
                    "test": test_name,
                    "test_eka_id": test_eka_id,
                    "loinc_id": loinc_id,
                    "value": value,
                    "unit": unit,
                    "normal_range": normal_range,
                    "is_abnormal": is_abnormal,
                    "confidence": confidence,
                }
                extracted["lab_results"].append(lab_result)
                
                # Track abnormal values for disease inference
                if is_abnormal:
                    abnormal_values.append({
                        "test": test_name,
                        "value": value,
                        "is_high": self._is_high_value(test_name, value, str(normal_range) if normal_range else '')
                    })
        
        # Infer diseases from abnormal lab values
        if infer_diseases and abnormal_values:
            inferred_diseases = self._infer_diseases(abnormal_values)
            extracted["diseases"].extend(inferred_diseases)
        
        logger.info(f"[EkaLab] Parsed: patient={extracted.get('patient')}, diseases={len(extracted.get('diseases', []))}, symptoms={len(extracted.get('symptoms', []))}, meds={len(extracted.get('medications', []))}, vitals={extracted.get('vitals')}, labs={len(extracted.get('lab_results', []))}")
        
        return extracted
    
    def _parse_pii(self, pii: Dict[str, Any], extracted: Dict[str, Any]) -> None:
        """Parse PII data from response - handles both list and dict formats."""
        if not pii:
            return
        
        for file_path, pages_data in pii.items():
            # Handle list format (prescriptions): [{PageNum, Patient, Report}, ...]
            if isinstance(pages_data, list):
                for page_data in pages_data:
                    if isinstance(page_data, dict):
                        self._extract_patient_from_page(page_data, extracted)
                        break  # Use first page with data
                break  # Use first file
            
            # Handle dict format (lab reports): {page_num: {Name, Age, ...}}
            elif isinstance(pages_data, dict):
                for page_num, page_data in pages_data.items():
                    if isinstance(page_data, dict):
                        self._extract_patient_from_page(page_data, extracted)
                        break
                break
    
    def _extract_patient_from_page(self, page_data: Dict[str, Any], extracted: Dict[str, Any]) -> None:
        """Extract patient and facility info from a page data dict."""
        # Try Patient nested object first (prescription format)
        patient_obj = page_data.get('Patient', {}) or {}
        if patient_obj:
            name = patient_obj.get('Name')
            age_data = patient_obj.get('Age', {}) or {}
            gender = patient_obj.get('Gender')
        else:
            # Fall back to flat format (lab report format)
            name = page_data.get('Name')
            age_data = page_data.get('Age', {}) or {}
            gender = page_data.get('Gender')
        
        # Parse age
        age = None
        if isinstance(age_data, dict):
            age = age_data.get('Years') or age_data.get('years')
        elif isinstance(age_data, (int, float)):
            age = int(age_data)
        elif isinstance(age_data, str):
            age = self._parse_age(age_data)
        
        if name or age or gender:
            extracted["patient"] = {
                "name": name,
                "age": age,
                "gender": self._normalize_gender(gender) if gender else None,
            }
        
        # Try Report nested object first (prescription format)
        # Try Report nested object first (prescription format)
        report_obj = page_data.get('Report', {}) or {}
        if report_obj:
            facility = report_obj.get('Facility')
            doctor = report_obj.get('Doctor')
            doc_date = page_data.get('DocumentDate')
        else:
            # Fall back to flat format
            facility = page_data.get('Facility')
            doctor = page_data.get('Doctor')
            doc_date = page_data.get('DocumentDate')
        
        if facility or doctor:
            extracted["facility"] = {
                "hospital_name": facility,
                "doctor_name": doctor,
                "visit_date": doc_date,
            }
    
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
