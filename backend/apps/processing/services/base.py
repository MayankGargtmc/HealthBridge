"""
Base service class for all processing services.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ProcessingStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"  # Some data extracted but not all


@dataclass
class ProcessingResult:
    """Standardized result from any processing service."""
    status: ProcessingStatus
    raw_response: Dict[str, Any] = field(default_factory=dict)
    extracted_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    service_used: str = ""
    confidence_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "raw_response": self.raw_response,
            "extracted_data": self.extracted_data,
            "error_message": self.error_message,
            "service_used": self.service_used,
            "confidence_score": self.confidence_score,
        }


@dataclass
class StandardizedPatientData:
    """
    Standardized patient data structure that all normalizers output.
    This is what gets saved to our database.
    """
    # Patient Demographics
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None  # male, female, other, unknown
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    
    # Medical Info
    diseases: list = field(default_factory=list)  # [{"name": str, "icd_code": str, "severity": str}]
    symptoms: list = field(default_factory=list)
    medications: list = field(default_factory=list)
    lab_results: list = field(default_factory=list)
    vitals: Dict[str, Any] = field(default_factory=dict)
    
    # Facility Info
    hospital_name: Optional[str] = None
    doctor_name: Optional[str] = None
    visit_date: Optional[str] = None
    
    # Metadata
    source_type: str = ""  # lab_report, prescription, clinical_notes, etc.
    extraction_confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "patient": {
                "name": self.name,
                "age": self.age,
                "gender": self.gender,
                "phone": self.phone,
                "email": self.email,
                "address": self.address,
                "city": self.city,
                "state": self.state,
                "pincode": self.pincode,
            },
            "medical": {
                "diseases": self.diseases,
                "symptoms": self.symptoms,
                "medications": self.medications,
                "lab_results": self.lab_results,
                "vitals": self.vitals,
            },
            "facility": {
                "hospital_name": self.hospital_name,
                "doctor_name": self.doctor_name,
                "visit_date": self.visit_date,
            },
            "metadata": {
                "source_type": self.source_type,
                "extraction_confidence": self.extraction_confidence,
            }
        }
    
    def has_patient_info(self) -> bool:
        """Check if we have minimum patient information."""
        return bool(self.name)
    
    def has_disease_info(self) -> bool:
        """Check if we have disease/diagnosis information."""
        return len(self.diseases) > 0


class BaseProcessingService(ABC):
    """Abstract base class for all processing services."""
    
    service_name: str = "base"
    
    @abstractmethod
    def process(self, content: Any, content_type: str, **kwargs) -> ProcessingResult:
        """
        Process the input content and return extracted data.
        
        Args:
            content: The content to process (bytes for files, str for text)
            content_type: MIME type or content type identifier
            **kwargs: Additional parameters
            
        Returns:
            ProcessingResult with extracted data
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this service is configured and available."""
        pass
    
    def get_service_name(self) -> str:
        return self.service_name
