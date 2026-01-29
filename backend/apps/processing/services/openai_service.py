"""
OpenAI Service - Fallback for processing images/documents and text.
Uses GPT-4 Vision for images and GPT-4 for text.
"""

import logging
import base64
import json
from typing import Any, Dict, Optional
from django.conf import settings

from .base import BaseProcessingService, ProcessingResult, ProcessingStatus

logger = logging.getLogger(__name__)


class OpenAIService(BaseProcessingService):
    """
    Fallback service using OpenAI GPT-4 Vision for images and GPT-4 for text.
    """
    
    service_name = "openai"
    
    def __init__(self):
        self.api_key = getattr(settings, 'OPENAI_API_KEY', '')
        self.model_vision = "gpt-4o"  # GPT-4 with vision
        self.model_text = "gpt-4o"
        self.timeout = 120.0
    
    def is_available(self) -> bool:
        """Check if OpenAI API key is configured."""
        return bool(self.api_key)
    
    def process(self, content: Any, content_type: str, **kwargs) -> ProcessingResult:
        """
        Process content using OpenAI.
        
        Args:
            content: File bytes or text string
            content_type: 'text' for text, MIME type for images/PDFs
            **kwargs:
                - document_type: Type of document for better prompting
                
        Returns:
            ProcessingResult with extracted data
        """
        # log api key for debugging   
        logger.debug(f"OpenAI API Key: {self.api_key}")
        if not self.is_available():
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                error_message="OpenAI API key not configured",
                service_used=self.service_name
            )
        
        document_type = kwargs.get('document_type', 'medical_document')
        
        try:
            if content_type == 'text' or isinstance(content, str):
                return self._process_text(content, document_type)
            else:
                return self._process_image(content, content_type, document_type)
                
        except Exception as e:
            logger.error(f"[OpenAI] Error: {str(e)}")
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                error_message=str(e),
                service_used=self.service_name
            )
    
    def _process_text(self, text: str, document_type: str) -> ProcessingResult:
        """Process text using GPT-4."""
        import openai
        
        client = openai.OpenAI(api_key=self.api_key)
        
        prompt = self._get_text_prompt(document_type)
        
        logger.info(f"[OpenAI] Processing text, length: {len(text)} chars")
        
        response = client.chat.completions.create(
            model=self.model_text,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Extract medical information from this clinical text:\n\n{text}"}
            ],
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        logger.info(f"[OpenAI] Text processing complete")
        
        return ProcessingResult(
            status=ProcessingStatus.SUCCESS,
            raw_response=result,
            extracted_data=self._normalize_response(result),
            service_used=self.service_name,
            confidence_score=0.8
        )
    
    def _process_image(self, content: bytes, content_type: str, document_type: str) -> ProcessingResult:
        """Process image/PDF using GPT-4 Vision."""
        import openai
        
        client = openai.OpenAI(api_key=self.api_key)
        
        # Encode to base64
        file_base64 = base64.b64encode(content).decode('utf-8')
        
        # Determine media type
        media_type = self._get_media_type(content_type)
        
        prompt = self._get_vision_prompt(document_type)
        
        logger.info(f"[OpenAI] Processing image, type: {media_type}")
        
        response = client.chat.completions.create(
            model=self.model_vision,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{file_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        logger.info(f"[OpenAI] Image processing complete")
        
        return ProcessingResult(
            status=ProcessingStatus.SUCCESS,
            raw_response=result,
            extracted_data=self._normalize_response(result),
            service_used=self.service_name,
            confidence_score=0.75  # Vision slightly less confident
        )
    
    def _get_media_type(self, content_type: str) -> str:
        """Get proper media type for data URL."""
        mapping = {
            'application/pdf': 'application/pdf',
            'image/jpeg': 'image/jpeg',
            'image/jpg': 'image/jpeg',
            'image/png': 'image/png',
        }
        return mapping.get(content_type.lower(), 'image/jpeg')
    
    def _get_text_prompt(self, document_type: str) -> str:
        """Get system prompt for text processing."""
        return """You are a medical data extraction assistant. Extract structured information from clinical text.

Your task is to identify and extract:
1. Patient demographics (name, age, gender, phone, address)
2. Diseases/Diagnoses - THIS IS THE MOST IMPORTANT PART
3. Symptoms/Chief complaints
4. Medications
5. Lab results
6. Vitals
7. Hospital/Clinic information

IMPORTANT RULES:
- Expand ALL medical abbreviations:
  - DM → Diabetes Mellitus
  - HTN → Hypertension
  - CAD → Coronary Artery Disease
  - CKD → Chronic Kidney Disease
  - COPD → Chronic Obstructive Pulmonary Disease
  - MI → Myocardial Infarction
  - CHF → Congestive Heart Failure
  - TB → Tuberculosis
  - etc.
- Extract ALL diseases mentioned, even in medical history
- If age is mentioned as "45 Y" or "45 years", extract as integer 45
- Normalize gender to: male, female, or other

Return JSON in this exact format:
{
    "patient": {
        "name": "string or null",
        "age": "integer or null",
        "gender": "male/female/other or null",
        "phone": "string or null",
        "address": "string or null"
    },
    "diseases": [
        {"name": "Full Disease Name", "icd_code": null, "severity": "mild/moderate/severe or null"}
    ],
    "symptoms": ["symptom1", "symptom2"],
    "medications": [
        {"name": "Drug Name", "dosage": "string or null", "frequency": "string or null"}
    ],
    "lab_results": [
        {"test": "Test Name", "value": "string", "unit": "string or null"}
    ],
    "vitals": {
        "blood_pressure": "string or null",
        "pulse": "string or null",
        "temperature": "string or null"
    },
    "facility": {
        "hospital_name": "string or null",
        "doctor_name": "string or null",
        "visit_date": "string or null"
    }
}"""

    def _get_vision_prompt(self, document_type: str) -> str:
        """Get prompt for vision processing."""
        base_prompt = self._get_text_prompt(document_type)
        
        if document_type == 'prescription':
            extra = """
            
This is a medical prescription (may be handwritten). Pay special attention to:
- Patient name and details at the top
- Diagnosis/Chief complaint
- Medications with dosage
- Doctor's name and clinic
- Handwriting may be difficult - do your best to interpret"""
        elif document_type == 'lab_report':
            extra = """
            
This is a lab report. Pay special attention to:
- Patient demographics
- Test names and values
- Abnormal values (often marked with H/L or highlighted)
- Lab name and date"""
        else:
            extra = """
            
This is a medical document. Extract all visible patient and medical information."""
        
        return base_prompt + extra
    
    def _normalize_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize OpenAI response to our standard format."""
        normalized = {
            "patient": {},
            "diseases": [],
            "symptoms": [],
            "medications": [],
            "lab_results": [],
            "vitals": {},
            "facility": {}
        }
        
        # Patient
        patient = response.get('patient', {})
        if patient:
            normalized["patient"] = {
                "name": patient.get('name'),
                "age": patient.get('age') if isinstance(patient.get('age'), int) else self._parse_age(patient.get('age')),
                "gender": self._normalize_gender(patient.get('gender')),
                "phone": patient.get('phone'),
                "address": patient.get('address'),
            }
        
        # Diseases - ensure proper format
        diseases = response.get('diseases', [])
        for disease in diseases:
            if isinstance(disease, str):
                normalized["diseases"].append({
                    "name": disease,
                    "icd_code": None,
                    "severity": None
                })
            elif isinstance(disease, dict):
                normalized["diseases"].append({
                    "name": disease.get('name', ''),
                    "icd_code": disease.get('icd_code'),
                    "severity": disease.get('severity')
                })
        
        # Symptoms
        symptoms = response.get('symptoms', [])
        normalized["symptoms"] = [s for s in symptoms if isinstance(s, str)]
        
        # Medications
        medications = response.get('medications', [])
        for med in medications:
            if isinstance(med, str):
                normalized["medications"].append({"name": med})
            elif isinstance(med, dict):
                normalized["medications"].append({
                    "name": med.get('name', ''),
                    "dosage": med.get('dosage'),
                    "frequency": med.get('frequency'),
                })
        
        # Lab results
        lab_results = response.get('lab_results', [])
        for result in lab_results:
            if isinstance(result, dict):
                normalized["lab_results"].append({
                    "test": result.get('test', ''),
                    "value": result.get('value'),
                    "unit": result.get('unit'),
                })
        
        # Vitals
        normalized["vitals"] = response.get('vitals', {})
        
        # Facility
        facility = response.get('facility', {})
        if facility:
            normalized["facility"] = {
                "hospital_name": facility.get('hospital_name'),
                "doctor_name": facility.get('doctor_name'),
                "visit_date": facility.get('visit_date'),
            }
        
        return normalized
    
    def _parse_age(self, age_value: Any) -> Optional[int]:
        """Parse age from string."""
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
        """Normalize gender."""
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
