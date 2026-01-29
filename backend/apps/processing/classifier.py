"""
Document Classifier - Detects the type of uploaded document.
"""

import logging
import mimetypes
from typing import Tuple, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    LAB_REPORT = "lab_report"
    PRESCRIPTION = "prescription"
    CLINICAL_TEXT = "clinical_text"
    STRUCTURED_DATA = "structured_data"  # CSV/JSON
    UNKNOWN = "unknown"


class ContentCategory(Enum):
    IMAGE = "image"
    PDF = "pdf"
    TEXT = "text"
    STRUCTURED = "structured"


class DocumentClassifier:
    """
    Classifies documents based on file type, content, and metadata.
    """
    
    # Keywords that suggest lab reports
    LAB_REPORT_KEYWORDS = [
        'lab', 'laboratory', 'pathology', 'diagnostic', 'test result',
        'blood test', 'urine test', 'hemoglobin', 'creatinine', 'glucose',
        'cholesterol', 'hba1c', 'thyroid', 'liver function', 'kidney function',
        'cbc', 'complete blood count', 'lipid profile'
    ]
    
    # Keywords that suggest prescriptions
    PRESCRIPTION_KEYWORDS = [
        'rx', 'prescription', 'medicine', 'tablet', 'capsule', 'syrup',
        'mg', 'ml', 'dose', 'twice daily', 'once daily', 'before meal',
        'after meal', 'sos', 'prn', 'stat'
    ]
    
    # Keywords that suggest clinical notes
    CLINICAL_KEYWORDS = [
        'patient', 'chief complaint', 'diagnosis', 'history', 'examination',
        'vitals', 'blood pressure', 'pulse', 'treatment', 'advised',
        'follow up', 'referred'
    ]
    
    def classify(
        self, 
        filename: str, 
        content_type: str, 
        content: Optional[bytes] = None,
        user_hint: Optional[str] = None
    ) -> Tuple[DocumentType, ContentCategory]:
        """
        Classify a document based on available information.
        
        Args:
            filename: Original filename
            content_type: MIME type
            content: File content (optional, for deeper analysis)
            user_hint: User-provided hint about document type
            
        Returns:
            Tuple of (DocumentType, ContentCategory)
        """
        # First, determine content category from MIME type
        content_category = self._get_content_category(content_type, filename)
        
        # If user provided a hint, use it
        if user_hint:
            doc_type = self._parse_user_hint(user_hint)
            if doc_type != DocumentType.UNKNOWN:
                logger.info(f"[Classifier] Using user hint: {doc_type.value}")
                return doc_type, content_category
        
        # For structured data, classification is straightforward
        if content_category == ContentCategory.STRUCTURED:
            return DocumentType.STRUCTURED_DATA, content_category
        
        # For text content, analyze the text
        if content_category == ContentCategory.TEXT and content:
            text = content.decode('utf-8', errors='ignore').lower()
            doc_type = self._classify_from_text(text)
            return doc_type, content_category
        
        # For images/PDFs, use filename hints
        doc_type = self._classify_from_filename(filename)
        
        logger.info(f"[Classifier] Classified as: {doc_type.value}, {content_category.value}")
        return doc_type, content_category
    
    def _get_content_category(self, content_type: str, filename: str) -> ContentCategory:
        """Determine content category from MIME type."""
        content_type = content_type.lower()
        
        if 'image' in content_type:
            return ContentCategory.IMAGE
        elif 'pdf' in content_type:
            return ContentCategory.PDF
        elif 'csv' in content_type or filename.lower().endswith('.csv'):
            return ContentCategory.STRUCTURED
        elif 'json' in content_type or filename.lower().endswith('.json'):
            return ContentCategory.STRUCTURED
        elif 'text' in content_type:
            return ContentCategory.TEXT
        elif 'xml' in content_type:
            return ContentCategory.STRUCTURED
        
        # Fallback to extension
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff']:
            return ContentCategory.IMAGE
        elif ext == 'pdf':
            return ContentCategory.PDF
        elif ext in ['csv', 'json', 'xml', 'xlsx', 'xls']:
            return ContentCategory.STRUCTURED
        elif ext in ['txt', 'text']:
            return ContentCategory.TEXT
        
        return ContentCategory.PDF  # Default assumption
    
    def _parse_user_hint(self, hint: str) -> DocumentType:
        """Parse user-provided hint to document type."""
        hint = hint.lower().strip()
        
        mapping = {
            'lab_report': DocumentType.LAB_REPORT,
            'lab': DocumentType.LAB_REPORT,
            'laboratory': DocumentType.LAB_REPORT,
            'test_result': DocumentType.LAB_REPORT,
            'prescription': DocumentType.PRESCRIPTION,
            'rx': DocumentType.PRESCRIPTION,
            'medicine': DocumentType.PRESCRIPTION,
            'clinical': DocumentType.CLINICAL_TEXT,
            'clinical_text': DocumentType.CLINICAL_TEXT,
            'notes': DocumentType.CLINICAL_TEXT,
            'transcript': DocumentType.CLINICAL_TEXT,
            'csv': DocumentType.STRUCTURED_DATA,
            'json': DocumentType.STRUCTURED_DATA,
            'database': DocumentType.STRUCTURED_DATA,
            'export': DocumentType.STRUCTURED_DATA,
            'handwritten': DocumentType.PRESCRIPTION,
            'printed_lab': DocumentType.LAB_REPORT,
            'clinical_db': DocumentType.STRUCTURED_DATA,
        }
        
        return mapping.get(hint, DocumentType.UNKNOWN)
    
    def _classify_from_text(self, text: str) -> DocumentType:
        """Classify document type from text content."""
        text = text.lower()
        
        # Count keyword matches
        lab_score = sum(1 for kw in self.LAB_REPORT_KEYWORDS if kw in text)
        prescription_score = sum(1 for kw in self.PRESCRIPTION_KEYWORDS if kw in text)
        clinical_score = sum(1 for kw in self.CLINICAL_KEYWORDS if kw in text)
        
        # Determine type based on scores
        max_score = max(lab_score, prescription_score, clinical_score)
        
        if max_score == 0:
            return DocumentType.CLINICAL_TEXT  # Default for text
        
        if lab_score == max_score:
            return DocumentType.LAB_REPORT
        elif prescription_score == max_score:
            return DocumentType.PRESCRIPTION
        else:
            return DocumentType.CLINICAL_TEXT
    
    def _classify_from_filename(self, filename: str) -> DocumentType:
        """Classify based on filename patterns."""
        filename = filename.lower()
        
        # Check for lab report indicators
        lab_indicators = ['lab', 'report', 'test', 'pathology', 'diagnostic', 'result']
        if any(ind in filename for ind in lab_indicators):
            return DocumentType.LAB_REPORT
        
        # Check for prescription indicators
        rx_indicators = ['prescription', 'rx', 'medicine', 'drug']
        if any(ind in filename for ind in rx_indicators):
            return DocumentType.PRESCRIPTION
        
        # Check for clinical note indicators
        clinical_indicators = ['clinical', 'note', 'summary', 'discharge', 'opd', 'ipd']
        if any(ind in filename for ind in clinical_indicators):
            return DocumentType.CLINICAL_TEXT
        
        # Default based on common patterns
        # Most uploaded images/PDFs in medical context are likely prescriptions
        return DocumentType.PRESCRIPTION
