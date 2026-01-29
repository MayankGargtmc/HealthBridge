"""
Service for processing medical documents using Eka Care API and OpenAI fallback.
"""

import logging
import base64
import httpx
from django.conf import settings
from django.utils import timezone
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class EkaAPIService:
    """Service to interact with Eka Care API for lab report processing."""
    
    def __init__(self):
        self.api_key = settings.EKA_API_KEY
        self.base_url = settings.EKA_API_BASE_URL
        self.timeout = 60.0
    
    async def process_lab_report(self, file_content: bytes, file_type: str) -> Dict[str, Any]:
        """
        Process a lab report using Eka Care API.
        
        API Reference: https://developer.eka.care/api-reference/general-tools/medical/lab-report/introduction
        """
        if not self.api_key:
            raise ValueError("EKA_API_KEY is not configured")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        # Encode file to base64
        file_base64 = base64.b64encode(file_content).decode('utf-8')
        
        payload = {
            "file": file_base64,
            "file_type": file_type,
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/v1/lab-report/extract",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
    
    def process_lab_report_sync(self, file_content: bytes, file_type: str) -> Dict[str, Any]:
        """Synchronous version of process_lab_report."""
        if not self.api_key:
            raise ValueError("EKA_API_KEY is not configured")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        file_base64 = base64.b64encode(file_content).decode('utf-8')
        
        payload = {
            "file": file_base64,
            "file_type": file_type,
        }
        
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/v1/lab-report/extract",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()


class OpenAIService:
    """Fallback service using OpenAI for document processing."""
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
    
    def process_document(self, file_content: bytes, file_type: str, document_type: str) -> Dict[str, Any]:
        """
        Process a medical document using OpenAI's vision API.
        """
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured")
        
        import openai
        client = openai.OpenAI(api_key=self.api_key)
        
        # Encode file to base64
        file_base64 = base64.b64encode(file_content).decode('utf-8')
        
        # Determine media type
        media_type = "image/jpeg"
        if "pdf" in file_type.lower():
            media_type = "application/pdf"
        elif "png" in file_type.lower():
            media_type = "image/png"
        
        prompt = """Analyze this medical document and extract the following information in JSON format:
        {
            "patient_info": {
                "name": "",
                "age": null,
                "gender": "",
                "phone": "",
                "address": ""
            },
            "medical_info": {
                "diseases": [],  // List of diagnosed diseases/conditions
                "symptoms": [],
                "medications": [],
                "test_results": []  // Lab test results if any
            },
            "facility_info": {
                "hospital_name": "",
                "doctor_name": "",
                "date": ""
            }
        }
        
        Important notes:
        - Expand medical abbreviations (e.g., 'DM' -> 'Diabetes Mellitus', 'HTN' -> 'Hypertension')
        - Extract all diseases mentioned
        - If information is not available, use null or empty string
        - For age, extract as integer if possible
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
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
        
        import json
        return json.loads(response.choices[0].message.content)


class DocumentProcessingService:
    """Main service for processing documents."""
    
    def __init__(self):
        self.eka_service = EkaAPIService()
        self.openai_service = OpenAIService()
    
    def process_document(self, document) -> Dict[str, Any]:
        """
        Process a document and extract structured data.
        Uses Eka API as primary and OpenAI as fallback.
        """
        from .models import ProcessingLog
        
        document.processing_status = 'processing'
        document.save()
        
        try:
            # Read file content
            file_content = document.file.read()
            file_type = document.file_type
            
            result = None
            api_used = None
            
            # Try Eka API first for lab reports
            if document.document_type == 'printed_lab' and settings.EKA_API_KEY:
                try:
                    logger.info(f"Processing document {document.id} with Eka API")
                    result = self.eka_service.process_lab_report_sync(file_content, file_type)
                    api_used = 'eka'
                    
                    ProcessingLog.objects.create(
                        document=document,
                        step='eka_api_extraction',
                        status='success',
                        api_used='eka',
                        response_data=result
                    )
                except Exception as e:
                    logger.warning(f"Eka API failed for document {document.id}: {e}")
                    ProcessingLog.objects.create(
                        document=document,
                        step='eka_api_extraction',
                        status='failed',
                        message=str(e),
                        api_used='eka'
                    )
            
            # Fallback to OpenAI
            if result is None and settings.OPENAI_API_KEY:
                try:
                    logger.info(f"Processing document {document.id} with OpenAI")
                    result = self.openai_service.process_document(
                        file_content, 
                        file_type,
                        document.document_type
                    )
                    api_used = 'openai'
                    
                    ProcessingLog.objects.create(
                        document=document,
                        step='openai_extraction',
                        status='success',
                        api_used='openai',
                        response_data=result
                    )
                except Exception as e:
                    logger.error(f"OpenAI failed for document {document.id}: {e}")
                    ProcessingLog.objects.create(
                        document=document,
                        step='openai_extraction',
                        status='failed',
                        message=str(e),
                        api_used='openai'
                    )
            
            if result is None:
                raise Exception("All processing methods failed")
            
            # Update document with results
            document.structured_data = result
            document.processing_status = 'completed'
            document.processed_at = timezone.now()
            document.save()
            
            # Create patient records from extracted data
            self._create_patient_records(document, result, api_used)
            
            return result
            
        except Exception as e:
            logger.error(f"Document processing failed for {document.id}: {e}")
            document.processing_status = 'failed'
            document.processing_error = str(e)
            document.save()
            raise
    
    def _create_patient_records(self, document, extracted_data: Dict[str, Any], api_used: str):
        """Create patient records from extracted data."""
        from apps.patients.models import Patient, Disease, PatientDisease
        
        patient_info = extracted_data.get('patient_info', {})
        medical_info = extracted_data.get('medical_info', {})
        facility_info = extracted_data.get('facility_info', {})
        
        # Skip if no patient info
        if not patient_info.get('name'):
            logger.warning(f"No patient name found in document {document.id}")
            return
        
        # Create or update patient
        patient, created = Patient.objects.update_or_create(
            name=patient_info.get('name', '').strip(),
            phone_number=patient_info.get('phone', '').strip() or None,
            defaults={
                'age': patient_info.get('age'),
                'gender': self._normalize_gender(patient_info.get('gender', '')),
                'address': patient_info.get('address', ''),
                'hospital_clinic': facility_info.get('hospital_name', '') or document.hospital_clinic_name,
                'location': document.source_location,
                'source_document': document,
            }
        )
        
        # Add diseases
        diseases = medical_info.get('diseases', [])
        for disease_name in diseases:
            if disease_name:
                disease, _ = Disease.objects.get_or_create(
                    name=disease_name.strip().title()
                )
                PatientDisease.objects.get_or_create(
                    patient=patient,
                    disease=disease,
                    defaults={
                        'source_document': document,
                        'diagnosis_date': facility_info.get('date'),
                    }
                )
        
        logger.info(f"Created/updated patient {patient.id} with {len(diseases)} diseases")
    
    def _normalize_gender(self, gender: str) -> str:
        """Normalize gender value."""
        if not gender:
            return 'unknown'
        gender = gender.lower().strip()
        if gender in ['m', 'male', 'man']:
            return 'male'
        elif gender in ['f', 'female', 'woman']:
            return 'female'
        return 'other'
