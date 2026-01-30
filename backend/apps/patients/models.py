from django.db import models
import uuid


class Disease(models.Model):
    """Model to store disease/condition information."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    category = models.CharField(max_length=100, blank=True)  # e.g., "Chronic", "Infectious", etc.
    icd_code = models.CharField(max_length=20, blank=True)  # ICD-10 code if available
    description = models.TextField(blank=True)
    
    # Common abbreviations that map to this disease
    abbreviations = models.JSONField(default=list, blank=True)  # ["DM", "T2DM"] for Diabetes
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Disease'
        verbose_name_plural = 'Diseases'
    
    def __str__(self):
        return self.name


class Patient(models.Model):
    """Model to store structured patient information."""
    
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('unknown', 'Unknown'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Demographics
    name = models.CharField(max_length=255)
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='unknown')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True)
    
    # Location info (important for fund distribution)
    city = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    location = models.CharField(max_length=255, blank=True)  # General location string
    
    # Healthcare facility
    hospital_clinic = models.CharField(max_length=255, blank=True)
    doctor_name = models.CharField(max_length=255, blank=True)
    
    # Diseases (many-to-many)
    diseases = models.ManyToManyField(Disease, through='PatientDisease', related_name='patients')
    
    # Source tracking
    source_document = models.ForeignKey(
        'documents.Document',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='extracted_patients'
    )
    
    # Additional info
    notes = models.TextField(blank=True)
    economic_status = models.CharField(max_length=50, blank=True)  # BPL, APL, etc.
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Patient'
        verbose_name_plural = 'Patients'
    
    def __str__(self):
        return f"{self.name} ({self.age or 'Age unknown'})"
    
    @property
    def disease_list(self):
        """Return list of disease names."""
        return list(self.diseases.values_list('name', flat=True))
    
    @property
    def display_id(self):
        """Return a short display ID for the patient."""
        return f"P-{str(self.id)[:8].upper()}"
    
    @property
    def anonymized_name(self):
        """
        Return anonymized version of patient name for privacy.
        Shows first letter + asterisks + last letter, or display_id if no name.
        Examples: "John Doe" -> "J*** D**", "Anonymous" -> "P-ABC12345"
        """
        if not self.name or self.name.startswith('Unknown Patient'):
            return self.display_id
        
        parts = self.name.split()
        anonymized_parts = []
        for part in parts:
            if len(part) <= 2:
                anonymized_parts.append(part[0] + '*' if len(part) > 0 else '*')
            else:
                anonymized_parts.append(part[0] + '*' * (len(part) - 2) + part[-1])
        return ' '.join(anonymized_parts)
    
    @property
    def masked_phone(self):
        """
        Return masked phone number for privacy.
        Shows last 4 digits only. Example: "9876543210" -> "******3210"
        """
        if not self.phone_number:
            return None
        if len(self.phone_number) <= 4:
            return '*' * len(self.phone_number)
        return '*' * (len(self.phone_number) - 4) + self.phone_number[-4:]
    
    @property
    def age_group(self):
        """Return age group for analytics."""
        if self.age is None:
            return 'Unknown'
        if self.age < 18:
            return '0-17'
        elif self.age < 30:
            return '18-29'
        elif self.age < 45:
            return '30-44'
        elif self.age < 60:
            return '45-59'
        else:
            return '60+'


class PatientDisease(models.Model):
    """Through model for Patient-Disease relationship with additional metadata."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    disease = models.ForeignKey(Disease, on_delete=models.CASCADE)
    
    diagnosis_date = models.DateField(null=True, blank=True)
    severity = models.CharField(max_length=50, blank=True)  # mild, moderate, severe
    status = models.CharField(max_length=50, default='active')  # active, resolved, chronic
    
    source_document = models.ForeignKey(
        'documents.Document',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['patient', 'disease']
        verbose_name = 'Patient Disease'
        verbose_name_plural = 'Patient Diseases'
    
    def __str__(self):
        return f"{self.patient.name} - {self.disease.name}"
