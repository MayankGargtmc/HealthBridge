"""
Gemini Service - Free AI for processing images/documents and text.
Uses Google Gemini 1.5 Flash (free tier: 15 RPM, 1500 RPD).
"""

import logging
import base64
import json
from typing import Any, Dict, Optional
from django.conf import settings

from .base import BaseProcessingService, ProcessingResult, ProcessingStatus

logger = logging.getLogger(__name__)


class GeminiService(BaseProcessingService):
    """
    Service using Google Gemini for image and text processing.
    Free tier: 15 requests/minute, 1500 requests/day
    """
    
    service_name = "gemini"
    
    def __init__(self):
        self.api_key = getattr(settings, 'GEMINI_API_KEY', '')
        self.model = "gemini-2.5-flash"  # Free, fast, supports vision
    
    def is_available(self) -> bool:
        """Check if Gemini API key is configured."""
        return bool(self.api_key)
    
    def process(self, content: Any, content_type: str, **kwargs) -> ProcessingResult:
        """
        Process content using Gemini.
        """
        if not self.is_available():
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                error_message="Gemini API key not configured",
                service_used=self.service_name
            )
        
        document_type = kwargs.get('document_type', 'medical_document')
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            
            if content_type == 'text':
                return self._process_text(content, document_type)
            else:
                return self._process_image(content, content_type, document_type)
                
        except Exception as e:
            logger.error(f"[Gemini] Error: {str(e)}")
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                error_message=str(e),
                service_used=self.service_name
            )
    
    def _process_text(self, text: str, document_type: str) -> ProcessingResult:
        """Process text using Gemini."""
        import google.generativeai as genai
        
        model = genai.GenerativeModel(self.model)
        prompt = self._get_prompt(document_type)
        
        logger.info(f"[Gemini] Processing text, length: {len(text)} chars")
        
        response = model.generate_content(
            f"{prompt}\n\nExtract medical information from this clinical text:\n\n{text}"
        )
        
        result = self._parse_response(response.text)
        
        logger.info(f"[Gemini] Text processing complete")
        
        return ProcessingResult(
            status=ProcessingStatus.SUCCESS,
            raw_response=result,
            extracted_data=self._normalize_response(result),
            service_used=self.service_name,
            confidence_score=0.8
        )
    
    def _process_image(self, content: Any, content_type: str, document_type: str) -> ProcessingResult:
        """Process image using Gemini Vision."""
        import google.generativeai as genai
        from PIL import Image
        import io
        
        model = genai.GenerativeModel(self.model)
        
        # Handle base64 encoded content
        if isinstance(content, str):
            # Already base64 encoded - decode it
            image_data = base64.b64decode(content)
        else:
            image_data = content
        
        # Convert to PIL Image (Gemini works better with PIL)
        try:
            image = Image.open(io.BytesIO(image_data))
            # Convert to RGB if necessary (handles RGBA, grayscale, etc.)
            if image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')
        except Exception as e:
            logger.error(f"[Gemini] Failed to open image: {e}")
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                error_message=f"Invalid image format: {e}",
                service_used=self.service_name
            )
        
        prompt = self._get_prompt(document_type)
        
        if document_type == 'prescription':
            prompt += "\n\nThis is a medical prescription (may be handwritten). Extract all patient info, diagnoses, and medications."
        elif document_type == 'lab_report':
            prompt += "\n\nThis is a lab report. Extract patient info, test names, values, and identify abnormal results."
        
        logger.info(f"[Gemini] Processing image, size: {image.size}, mode: {image.mode}")
        
        # Pass PIL image directly to Gemini
        response = model.generate_content([prompt, image])
        
        result = self._parse_response(response.text)
        
        logger.info(f"[Gemini] Image processing complete, response : {response}, result : {result}")
        
        return ProcessingResult(
            status=ProcessingStatus.SUCCESS,
            raw_response=result,
            extracted_data=self._normalize_response(result),
            service_used=self.service_name,
            confidence_score=0.75
        )
    
    def _get_mime_type(self, content_type: str) -> str:
        """Get MIME type for image."""
        mapping = {
            'image/jpeg': 'image/jpeg',
            'image/jpg': 'image/jpeg',
            'image/png': 'image/png',
            'image/webp': 'image/webp',
            'image/base64': 'image/jpeg',  # Default for base64
            'application/pdf': 'application/pdf',
        }
        return mapping.get(content_type.lower(), 'image/jpeg')
    
    def _get_prompt(self, document_type: str) -> str:
        """Get extraction prompt."""
        return """You are a medical data extraction assistant. Extract structured information from the medical document.

Extract:
1. Patient demographics (name, age, gender, phone, address)
2. Diseases/Diagnoses - MOST IMPORTANT - expand all abbreviations:
   - DM → Diabetes Mellitus
   - HTN → Hypertension
   - CAD → Coronary Artery Disease
   - CKD → Chronic Kidney Disease
   - COPD → Chronic Obstructive Pulmonary Disease
   - TB → Tuberculosis
3. Symptoms
4. Medications with dosage
5. Lab results
6. Vitals
7. Hospital/Doctor info

Return ONLY valid JSON in this exact format (no markdown, no extra text):
{
    "patient": {
        "name": "string or null",
        "age": 45,
        "gender": "male/female/other",
        "phone": "string or null",
        "address": "string or null"
    },
    "diseases": [
        {"name": "Full Disease Name", "severity": "mild/moderate/severe or null"}
    ],
    "symptoms": ["symptom1", "symptom2"],
    "medications": [
        {"name": "Drug Name", "dosage": "string", "frequency": "string"}
    ],
    "lab_results": [
        {"test": "Test Name", "value": "string", "unit": "string"}
    ],
    "vitals": {
        "blood_pressure": "string or null",
        "pulse": "string or null"
    },
    "facility": {
        "hospital_name": "string or null",
        "doctor_name": "string or null"
    }
}"""

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Gemini response to JSON."""
        try:
            # Try direct JSON parse
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code block
            import re
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # Try to find JSON object in text
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass
            
            logger.warning(f"[Gemini] Could not parse JSON from response: {response_text[:200]}")
            return {}
    
    def _normalize_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Gemini response to standard format."""
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
            age = patient.get('age')
            if isinstance(age, str):
                import re
                match = re.search(r'(\d+)', age)
                age = int(match.group(1)) if match else None
            
            normalized["patient"] = {
                "name": patient.get('name'),
                "age": age,
                "gender": self._normalize_gender(patient.get('gender')),
                "phone": patient.get('phone'),
                "address": patient.get('address'),
            }
        
        # Diseases
        diseases = response.get('diseases', [])
        for disease in diseases:
            if isinstance(disease, str):
                normalized["diseases"].append({"name": disease})
            elif isinstance(disease, dict):
                normalized["diseases"].append({
                    "name": disease.get('name', ''),
                    "icd_code": disease.get('icd_code'),
                    "severity": disease.get('severity')
                })
        
        # Copy other fields
        normalized["symptoms"] = response.get('symptoms', [])
        normalized["medications"] = response.get('medications', [])
        normalized["lab_results"] = response.get('lab_results', [])
        normalized["vitals"] = response.get('vitals', {})
        normalized["facility"] = response.get('facility', {})
        
        return normalized
    
    def _normalize_gender(self, gender: Any) -> Optional[str]:
        """Normalize gender."""
        if not gender:
            return None
        gender = str(gender).lower().strip()
        if gender in ['m', 'male', 'man']:
            return 'male'
        elif gender in ['f', 'female', 'woman']:
            return 'female'
        return 'other' if gender else None
