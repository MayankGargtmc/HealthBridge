"""
Direct Parser Service - For processing structured data (CSV, JSON).
Handles batch imports from hospital database exports.
"""

import logging
import csv
import json
import io
from typing import Any, Dict, List, Optional
from .base import BaseProcessingService, ProcessingResult, ProcessingStatus

logger = logging.getLogger(__name__)


# Common column name mappings for CSV files
COLUMN_MAPPINGS = {
    'name': ['name', 'patient_name', 'patient name', 'full_name', 'fullname'],
    'age': ['age', 'patient_age', 'years'],
    'gender': ['gender', 'sex', 'patient_gender'],
    'phone': ['phone', 'mobile', 'contact', 'phone_number', 'mobile_number', 'contact_number'],
    'address': ['address', 'patient_address', 'location', 'addr'],
    'city': ['city', 'town'],
    'state': ['state', 'province'],
    'pincode': ['pincode', 'pin', 'zip', 'zipcode', 'postal_code'],
    'disease': ['disease', 'diagnosis', 'condition', 'diseases', 'diagnoses'],
    'hospital': ['hospital', 'clinic', 'facility', 'hospital_name', 'clinic_name'],
    'doctor': ['doctor', 'physician', 'doctor_name', 'treating_doctor'],
    'date': ['date', 'visit_date', 'admission_date', 'report_date'],
}


class DirectParserService(BaseProcessingService):
    """
    Service to parse structured data from CSV/JSON files.
    For batch imports from hospital database exports.
    """
    
    service_name = "direct_parser"
    
    def __init__(self):
        pass
    
    def is_available(self) -> bool:
        """Always available - no external API needed."""
        return True
    
    def process(self, content: Any, content_type: str, **kwargs) -> ProcessingResult:
        """
        Process structured data (CSV or JSON).
        
        Args:
            content: File content as bytes or string
            content_type: 'text/csv', 'application/json', etc.
            **kwargs:
                - column_mapping: Custom column mapping dict
                
        Returns:
            ProcessingResult with list of extracted records
        """
        custom_mapping = kwargs.get('column_mapping', {})
        
        try:
            if 'csv' in content_type.lower():
                return self._process_csv(content, custom_mapping)
            elif 'json' in content_type.lower():
                return self._process_json(content, custom_mapping)
            else:
                return ProcessingResult(
                    status=ProcessingStatus.FAILED,
                    error_message=f"Unsupported content type: {content_type}",
                    service_used=self.service_name
                )
                
        except Exception as e:
            logger.error(f"[DirectParser] Error: {str(e)}")
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                error_message=str(e),
                service_used=self.service_name
            )
    
    def _process_csv(self, content: Any, custom_mapping: Dict) -> ProcessingResult:
        """Process CSV file."""
        # Convert bytes to string if needed
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        
        # Parse CSV
        reader = csv.DictReader(io.StringIO(content))
        
        # Detect column mapping
        fieldnames = reader.fieldnames or []
        mapping = self._detect_column_mapping(fieldnames, custom_mapping)
        
        logger.info(f"[DirectParser] Processing CSV with {len(fieldnames)} columns")
        logger.info(f"[DirectParser] Detected mapping: {mapping}")
        
        records = []
        for row in reader:
            record = self._extract_record(row, mapping)
            if record.get('patient', {}).get('name'):  # Only add if has name
                records.append(record)
        
        logger.info(f"[DirectParser] Extracted {len(records)} records from CSV")
        
        return ProcessingResult(
            status=ProcessingStatus.SUCCESS,
            raw_response={"records_count": len(records)},
            extracted_data={"records": records, "is_batch": True},
            service_used=self.service_name,
            confidence_score=0.95  # Direct parsing is very reliable
        )
    
    def _process_json(self, content: Any, custom_mapping: Dict) -> ProcessingResult:
        """Process JSON file."""
        # Convert bytes to string if needed
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        
        data = json.loads(content)
        
        # Handle both array and object with records
        if isinstance(data, list):
            raw_records = data
        elif isinstance(data, dict):
            # Look for common array keys
            for key in ['records', 'patients', 'data', 'results']:
                if key in data and isinstance(data[key], list):
                    raw_records = data[key]
                    break
            else:
                raw_records = [data]  # Single record
        else:
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                error_message="Invalid JSON structure",
                service_used=self.service_name
            )
        
        logger.info(f"[DirectParser] Processing JSON with {len(raw_records)} records")
        
        # Detect column mapping from first record
        if raw_records:
            first_record = raw_records[0]
            if isinstance(first_record, dict):
                fieldnames = list(first_record.keys())
                mapping = self._detect_column_mapping(fieldnames, custom_mapping)
            else:
                mapping = {}
        else:
            mapping = {}
        
        records = []
        for raw in raw_records:
            if isinstance(raw, dict):
                record = self._extract_record(raw, mapping)
                if record.get('patient', {}).get('name'):
                    records.append(record)
        
        logger.info(f"[DirectParser] Extracted {len(records)} records from JSON")
        
        return ProcessingResult(
            status=ProcessingStatus.SUCCESS,
            raw_response={"records_count": len(records)},
            extracted_data={"records": records, "is_batch": True},
            service_used=self.service_name,
            confidence_score=0.95
        )
    
    def _detect_column_mapping(self, fieldnames: List[str], custom_mapping: Dict) -> Dict[str, str]:
        """
        Detect which columns map to which fields.
        Returns: {our_field: actual_column_name}
        """
        mapping = {}
        fieldnames_lower = {f.lower().strip(): f for f in fieldnames}
        
        # Apply custom mapping first
        for our_field, actual_col in custom_mapping.items():
            if actual_col.lower() in fieldnames_lower:
                mapping[our_field] = fieldnames_lower[actual_col.lower()]
        
        # Auto-detect remaining fields
        for our_field, possible_names in COLUMN_MAPPINGS.items():
            if our_field in mapping:
                continue
            for possible in possible_names:
                if possible.lower() in fieldnames_lower:
                    mapping[our_field] = fieldnames_lower[possible.lower()]
                    break
        
        return mapping
    
    def _extract_record(self, row: Dict, mapping: Dict) -> Dict[str, Any]:
        """Extract a single record using the column mapping."""
        record = {
            "patient": {
                "name": self._get_value(row, mapping, 'name'),
                "age": self._parse_age(self._get_value(row, mapping, 'age')),
                "gender": self._normalize_gender(self._get_value(row, mapping, 'gender')),
                "phone": self._get_value(row, mapping, 'phone'),
                "address": self._get_value(row, mapping, 'address'),
                "city": self._get_value(row, mapping, 'city'),
                "state": self._get_value(row, mapping, 'state'),
                "pincode": self._get_value(row, mapping, 'pincode'),
            },
            "diseases": [],
            "symptoms": [],
            "medications": [],
            "lab_results": [],
            "vitals": {},
            "facility": {
                "hospital_name": self._get_value(row, mapping, 'hospital'),
                "doctor_name": self._get_value(row, mapping, 'doctor'),
                "visit_date": self._get_value(row, mapping, 'date'),
            }
        }
        
        # Extract diseases - handle comma-separated values
        disease_value = self._get_value(row, mapping, 'disease')
        if disease_value:
            diseases = [d.strip() for d in disease_value.split(',') if d.strip()]
            record["diseases"] = [
                {"name": d, "icd_code": None, "severity": None}
                for d in diseases
            ]
        
        return record
    
    def _get_value(self, row: Dict, mapping: Dict, field: str) -> Optional[str]:
        """Get value from row using mapping."""
        if field not in mapping:
            return None
        col_name = mapping[field]
        value = row.get(col_name)
        if value and isinstance(value, str):
            return value.strip()
        return value
    
    def _parse_age(self, age_value: Any) -> Optional[int]:
        """Parse age from various formats."""
        if age_value is None:
            return None
        if isinstance(age_value, int):
            return age_value
        if isinstance(age_value, float):
            return int(age_value)
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
        elif gender in ['o', 'other']:
            return 'other'
        return None
